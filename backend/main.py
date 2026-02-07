from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from auth import validate_password, validate_username, get_user_from_token
import bleach
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="WDMMG")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise ValueError(f"Failed to initialize Supabase client: {str(e)}")


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS attacks"""
    return bleach.clean(text, tags=[], strip=True)

# Categories
CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Bills & Utilities",
    "Shopping",
    "Health",
    "Entertainment",
    "Savings / Investments",
    "Misc/others"
]


# Pydantic Models
class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str  # Added refresh token
    token_type: str
    user: dict


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    first_name: str
    last_name: str


class Transaction(BaseModel):
    amount: Decimal  # Changed from float to Decimal
    category: str
    description: Optional[str] = ""
    timestamp: Optional[datetime] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: Decimal  # Changed from float to Decimal
    category: str
    description: str
    timestamp: datetime


class Budget(BaseModel):
    category: str
    monthly_limit: Decimal


class BudgetResponse(BaseModel):
    id: str
    user_id: str
    category: str
    monthly_limit: Decimal
    created_at: datetime
    updated_at: datetime


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Auth Endpoints
@app.post("/auth/signup", response_model=AuthResponse)
@limiter.limit("5/minute")  # Rate limit: 5 signups per minute
def signup(request: Request, signup_request: SignupRequest):
    """Sign up a new user"""
    # Validate username
    valid_username, username_msg = validate_username(signup_request.username)
    if not valid_username:
        raise HTTPException(status_code=400, detail=username_msg)
    
    # Validate password
    valid_password, password_msg = validate_password(signup_request.password)
    if not valid_password:
        raise HTTPException(status_code=400, detail=password_msg)
    
    # Sanitize inputs
    username = sanitize_input(signup_request.username)
    first_name = sanitize_input(signup_request.first_name)
    last_name = sanitize_input(signup_request.last_name)
    
    # Check if username is unique
    try:
        username_check = supabase.rpc("check_username_unique", {"username_input": username}).execute()
        if not username_check.data:
            raise HTTPException(status_code=400, detail="Username already taken")
    except Exception as e:
        if "Database error" in str(e) or "connection" in str(e).lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise
    
    try:
        # Create user in Supabase Auth (auto-confirm to skip email)
        auth_response = supabase.auth.sign_up({
            "email": signup_request.email,
            "password": signup_request.password,
            "options": {
                "email_redirect_to": None
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        # Note: If email confirmation is enabled in Supabase and rate limit is hit,
        # user is created but session might be null. Handle accordingly.
        access_token = auth_response.session.access_token if auth_response.session else None
        refresh_token = auth_response.session.refresh_token if auth_response.session else None
        
        if not access_token:
            # User created but needs confirmation - for now, try to sign in
            try:
                login_response = supabase.auth.sign_in_with_password({
                    "email": signup_request.email,
                    "password": signup_request.password
                })
                if login_response.session:
                    access_token = login_response.session.access_token
                    refresh_token = login_response.session.refresh_token
            except:
                pass
        
        if not access_token:
            raise HTTPException(
                status_code=400, 
                detail="Account created but email confirmation required. Please check your email or contact admin to disable email confirmation in Supabase settings."
            )
        
        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
        
        supabase.table("user_profiles").insert(profile_data).execute()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=429, 
                detail="Email rate limit exceeded. Please disable email confirmations in Supabase (Authentication → Providers → Email → Turn off 'Confirm email') or wait a few minutes and try again."
            )
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/auth/login", response_model=AuthResponse)
@limiter.limit("10/minute")  # Rate limit: 10 logins per minute
def login(request: Request, login_request: LoginRequest):
    """Login user"""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": login_request.email,
            "password": login_request.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user profile
        profile = supabase.table("user_profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_profile = profile.data[0]
        
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "username": user_profile["username"],
                "first_name": user_profile["first_name"],
                "last_name": user_profile["last_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/refresh", response_model=AuthResponse)
@limiter.limit("20/minute")  # Rate limit for token refresh
def refresh_token(request: Request, refresh_request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        auth_response = supabase.auth.refresh_session(refresh_request.refresh_token)
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Get user profile
        profile = supabase.table("user_profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_profile = profile.data[0]
        
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "username": user_profile["username"],
                "first_name": user_profile["first_name"],
                "last_name": user_profile["last_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@app.post("/auth/google", response_model=AuthResponse)
def google_auth(request: GoogleAuthRequest):
    """Authenticate with Google OAuth"""
    try:
        # Sign in with Google ID token
        auth_response = supabase.auth.sign_in_with_id_token({
            "provider": "google",
            "token": request.id_token
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Google authentication failed")
        
        # Check if user profile exists
        profile = supabase.table("user_profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            # New Google user - create profile
            # Use Google profile data or provided data
            user_metadata = auth_response.user.user_metadata or {}
            
            username = request.username or user_metadata.get("preferred_username") or auth_response.user.email.split("@")[0]
            first_name = request.first_name or user_metadata.get("given_name") or ""
            last_name = request.last_name or user_metadata.get("family_name") or ""
            
            if not request.username:
                # Validate and make username unique if needed
                base_username = username
                counter = 1
                username_check = supabase.rpc("check_username_unique", {"username_input": username}).execute()
                while not username_check.data:
                    username = f"{base_username}{counter}"
                    counter += 1
                    username_check = supabase.rpc("check_username_unique", {"username_input": username}).execute()
            
            profile_data = {
                "id": auth_response.user.id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            }
            
            supabase.table("user_profiles").insert(profile_data).execute()
            profile_data["email"] = auth_response.user.email
        else:
            profile_data = profile.data[0]
            profile_data["email"] = auth_response.user.email
        
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": auth_response.user.id,
                "email": profile_data["email"],
                "username": profile_data["username"],
                "first_name": profile_data["first_name"],
                "last_name": profile_data["last_name"]
            }
        }
    except Exception as e:
        error_msg = str(e)
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=400, detail=error_msg)


@app.post("/auth/logout")
def logout(token: str = Depends(get_user_from_token)):
    """Logout user - client-side only, no backend action needed"""
    # Supabase JWT tokens are stateless, so we just return success
    # The client should discard the tokens
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=UserProfile)
def get_current_user(token: str = Depends(get_user_from_token)):
    """Get current user profile"""
    try:
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user profile
        profile = supabase.table("user_profiles").select("*").eq("id", user.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_profile = profile.data[0]
        
        return {
            "id": user.user.id,
            "email": user.user.email,
            "username": user_profile["username"],
            "first_name": user_profile["first_name"],
            "last_name": user_profile["last_name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def read_root():
    return {"message": "WDMMG", "status": "running"}


@app.get("/categories", response_model=List[str])
def get_categories():
    """Get all available categories"""
    return CATEGORIES


@app.post("/transactions", response_model=TransactionResponse)
@limiter.limit("30/minute")  # Rate limit for creating transactions
def create_transaction(request: Request, transaction: Transaction, token: str = Depends(get_user_from_token)):
    """Create a new transaction"""
    if transaction.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {CATEGORIES}")
    
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    # Sanitize description
    description = sanitize_input(transaction.description)
    
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        transaction_id = str(uuid.uuid4())
        timestamp = transaction.timestamp if transaction.timestamp else datetime.now()
        
        data = {
            "id": transaction_id,
            "user_id": user.user.id,
            "amount": float(transaction.amount),  # Convert Decimal to float for JSON
            "category": transaction.category,
            "description": description,
            "timestamp": timestamp.isoformat()
        }
        
        result = supabase.table("transactions").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create transaction")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions", response_model=List[TransactionResponse])
@limiter.limit("60/minute")  # Rate limit for reading transactions
def get_transactions(
    request: Request,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,  # Add search parameter
    token: str = Depends(get_user_from_token)
):
    """Get all transactions for the authenticated user with optional filters"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        query = supabase.table("transactions").select("*").eq("user_id", user.user.id)
        
        # Filter by category
        if category and category in CATEGORIES:
            query = query.eq("category", category)
        
        # Filter by date range
        if start_date:
            try:
                datetime.fromisoformat(start_date)
                query = query.gte("timestamp", start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
        
        if end_date:
            try:
                datetime.fromisoformat(end_date)
                query = query.lte("timestamp", end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
        
        # Sort by timestamp (newest first)
        query = query.order("timestamp", desc=True)
        
        result = query.execute()
        
        # Apply search filter on description (client-side since Supabase free tier doesn't have FTS)
        if search:
            result.data = [t for t in result.data if search.lower() in t["description"].lower()]
        
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str, token: str = Depends(get_user_from_token)):
    """Get a specific transaction for the authenticated user"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table("transactions").select("*").eq("id", transaction_id).eq("user_id", user.user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
@limiter.limit("30/minute")  # Rate limit for updating transactions
def update_transaction(request: Request, transaction_id: str, transaction: Transaction, token: str = Depends(get_user_from_token)):
    """Update an existing transaction for the authenticated user"""
    # Sanitize description
    description = sanitize_input(transaction.description)
    
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if transaction exists and belongs to user
        existing = supabase.table("transactions").select("*").eq("id", transaction_id).eq("user_id", user.user.id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        if transaction.category not in CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {CATEGORIES}")
        
        if transaction.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Use provided timestamp or keep original
        original_timestamp = existing.data[0]["timestamp"]
        timestamp = transaction.timestamp if transaction.timestamp else original_timestamp
        
        update_data = {
            "amount": float(transaction.amount),  # Convert Decimal to float
            "category": transaction.category,
            "description": description,
            "timestamp": timestamp if isinstance(timestamp, str) else timestamp.isoformat()
        }
        
        result = supabase.table("transactions").update(update_data).eq("id", transaction_id).eq("user_id", user.user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update transaction")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/transactions/{transaction_id}")
@limiter.limit("30/minute")  # Rate limit for deleting transactions
def delete_transaction(request: Request, transaction_id: str, token: str = Depends(get_user_from_token)):
    """Delete a transaction for the authenticated user"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table("transactions").delete().eq("id", transaction_id).eq("user_id", user.user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {"message": "Transaction deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transactions/bulk-delete")
@limiter.limit("10/minute")  # Rate limit for bulk operations
def bulk_delete_transactions(request: Request, transaction_ids: List[str], token: str = Depends(get_user_from_token)):
    """Delete multiple transactions for the authenticated user"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if not transaction_ids:
            raise HTTPException(status_code=400, detail="No transaction IDs provided")
        
        # Delete transactions that belong to the user
        deleted_count = 0
        for transaction_id in transaction_ids:
            result = supabase.table("transactions").delete().eq("id", transaction_id).eq("user_id", user.user.id).execute()
            if result.data:
                deleted_count += 1
        
        return {"message": f"Successfully deleted {deleted_count} transaction(s)", "deleted_count": deleted_count}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/by-category")
def get_stats_by_category(token: str = Depends(get_user_from_token)):
    """Get total spending by category for the authenticated user"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table("transactions").select("category, amount").eq("user_id", user.user.id).execute()
        
        stats = {category: 0 for category in CATEGORIES}
        
        for transaction in result.data:
            stats[transaction["category"]] += float(transaction["amount"])
        
        # Filter out categories with 0 spending
        stats = {k: v for k, v in stats.items() if v > 0}
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/trends")
def get_spending_trends(
    period: str = "monthly",  # "daily", "weekly", "monthly" or "yearly"
    token: str = Depends(get_user_from_token)
):
    """Get spending trends over time"""
    try:
        # Get user from token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get all transactions
        result = supabase.table("transactions").select("timestamp, amount, category").eq("user_id", user.user.id).order("timestamp", desc=False).execute()
        
        if not result.data:
            return {}
        
        trends = {}
        for transaction in result.data:
            dt = datetime.fromisoformat(transaction["timestamp"].replace('Z', '+00:00'))
            
            if period == "daily":
                key = dt.strftime("%Y-%m-%d")
            elif period == "weekly":
                # ISO week format: YYYY-Www (e.g., 2026-W05)
                year, week, _ = dt.isocalendar()
                key = f"{year}-W{week:02d}"
            elif period == "monthly":
                key = dt.strftime("%Y-%m")
            else:  # yearly
                key = dt.strftime("%Y")
            
            if key not in trends:
                trends[key] = 0
            trends[key] += float(transaction["amount"])
        
        return trends
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


# Budget Endpoints
@app.get("/budgets", response_model=List[BudgetResponse])
def get_budgets(token: str = Depends(get_user_from_token)):
    """Get all budgets for the authenticated user"""
    try:
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table("budgets").select("*").eq("user_id", user.user.id).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/budgets", response_model=BudgetResponse)
@limiter.limit("20/minute")  # Rate limit for creating budgets
def create_budget(request: Request, budget: Budget, token: str = Depends(get_user_from_token)):
    """Create or update a budget for a category"""
    if budget.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {CATEGORIES}")
    
    if budget.monthly_limit <= 0:
        raise HTTPException(status_code=400, detail="Budget limit must be greater than 0")
    
    try:
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if budget already exists for this category
        existing = supabase.table("budgets").select("*").eq("user_id", user.user.id).eq("category", budget.category).execute()
        
        if existing.data:
            # Update existing budget
            update_data = {
                "monthly_limit": float(budget.monthly_limit),
                "updated_at": datetime.now().isoformat()
            }
            result = supabase.table("budgets").update(update_data).eq("id", existing.data[0]["id"]).execute()
        else:
            # Create new budget
            budget_data = {
                "user_id": user.user.id,
                "category": budget.category,
                "monthly_limit": float(budget.monthly_limit)
            }
            result = supabase.table("budgets").insert(budget_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save budget")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/budgets/{budget_id}")
@limiter.limit("20/minute")  # Rate limit for deleting budgets
def delete_budget(request: Request, budget_id: str, token: str = Depends(get_user_from_token)):
    """Delete a budget"""
    try:
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = supabase.table("budgets").delete().eq("id", budget_id).eq("user_id", user.user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        return {"message": "Budget deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budgets/status")
def get_budget_status(token: str = Depends(get_user_from_token)):
    """Get budget status with current spending for the current month"""
    try:
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get all budgets
        budgets = supabase.table("budgets").select("*").eq("user_id", user.user.id).execute()
        
        # Get current month's transactions
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1).isoformat()
        
        transactions = supabase.table("transactions").select("category, amount").eq("user_id", user.user.id).gte("timestamp", start_of_month).execute()
        
        # Calculate current spending per category
        spending = {}
        for transaction in transactions.data:
            category = transaction["category"]
            spending[category] = spending.get(category, 0) + float(transaction["amount"])
        
        # Build budget status
        budget_status = []
        for budget in budgets.data:
            category = budget["category"]
            limit = float(budget["monthly_limit"])
            spent = spending.get(category, 0)
            remaining = limit - spent
            percentage = (spent / limit * 100) if limit > 0 else 0
            
            budget_status.append({
                "category": category,
                "limit": limit,
                "spent": spent,
                "remaining": remaining,
                "percentage": round(percentage, 2),
                "status": "exceeded" if spent > limit else "warning" if percentage >= 80 else "ok"
            })
        
        return budget_status
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid token" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if "Database error" in error_msg or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Database service temporarily unavailable. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

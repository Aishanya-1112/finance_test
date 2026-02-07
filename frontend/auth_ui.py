import streamlit as st
import requests
import time
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds


def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'refresh_token' not in st.session_state:
        st.session_state.refresh_token = None
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = None


def check_session_timeout():
    """Check if session has timed out"""
    if st.session_state.authenticated and st.session_state.last_activity:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > SESSION_TIMEOUT:
            logout()
            st.warning("Session expired. Please login again.")
            return True
    return False


def update_activity():
    """Update last activity timestamp and refresh token if needed"""
    st.session_state.last_activity = time.time()
    
    # Check if token needs refresh (refresh after 45 minutes to stay ahead of 1-hour expiry)
    if st.session_state.authenticated and st.session_state.refresh_token:
        # Store token refresh time
        if 'token_refreshed_at' not in st.session_state:
            st.session_state.token_refreshed_at = time.time()
        
        elapsed_since_refresh = time.time() - st.session_state.token_refreshed_at
        if elapsed_since_refresh > 45 * 60:  # 45 minutes
            try:
                response = requests.post(
                    f"{API_URL}/auth/refresh",
                    json={"refresh_token": st.session_state.refresh_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.access_token = data["access_token"]
                    st.session_state.refresh_token = data["refresh_token"]
                    st.session_state.token_refreshed_at = time.time()
            except:
                # If refresh fails, don't disrupt the user experience
                # They'll get logged out on next action if token is truly expired
                pass


def login(email, password):
    """Login user"""
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.access_token = data["access_token"]
            st.session_state.refresh_token = data["refresh_token"]
            st.session_state.user = data["user"]
            st.session_state.last_activity = time.time()
            st.session_state.token_refreshed_at = time.time()
            return True, "Login successful!"
        else:
            error_detail = response.json().get("detail", "Login failed")
            return False, error_detail
    except Exception as e:
        return False, f"Error: {str(e)}"


def signup(username, email, password, first_name, last_name):
    """Sign up new user"""
    try:
        response = requests.post(
            f"{API_URL}/auth/signup",
            json={
                "username": username,
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.access_token = data["access_token"]
            st.session_state.refresh_token = data["refresh_token"]
            st.session_state.user = data["user"]
            st.session_state.last_activity = time.time()
            st.session_state.token_refreshed_at = time.time()
            return True, "Account created successfully!"
        else:
            error_detail = response.json().get("detail", "Signup failed")
            return False, error_detail
    except Exception as e:
        return False, f"Error: {str(e)}"


def logout():
    """Logout user"""
    try:
        if st.session_state.access_token:
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
            requests.post(f"{API_URL}/auth/logout", headers=headers)
    except:
        pass
    
    # Clear all session state
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    st.session_state.last_activity = None
    if 'token_refreshed_at' in st.session_state:
        del st.session_state.token_refreshed_at


def get_auth_headers():
    """Get authorization headers for API requests"""
    if st.session_state.access_token:
        update_activity()
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


def validate_password(password):
    """Validate password requirements"""
    import re
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def show_login_page():
    """Display login page"""
    st.markdown('''
    <style>
        /* Mobile responsive styles for auth page */
        @media (max-width: 768px) {
            h1 {
                font-size: 1.8rem !important;
            }
            h2, h3 {
                font-size: 1.3rem !important;
            }
            .stTextInput input, .stSelectbox, .stTextArea textarea {
                font-size: 16px !important; /* Prevents zoom on mobile */
            }
            .stButton button {
                padding: 0.75rem !important;
                font-size: 1rem !important;
            }
        }
    </style>
    ''', unsafe_allow_html=True)
    
    st.markdown('<h1 style="text-align: center;">WDMMG</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: gray;">Where Does My Money Go</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            st.markdown('<p style="text-align: center; color: gray; margin-top: 1rem;">Google OAuth: Configure in Supabase</p>', unsafe_allow_html=True)
            
            if login_button:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    success, message = login(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    with tab2:
        st.subheader("Create New Account")
        
        with st.form("signup_form"):
            username = st.text_input("Username", help="3-30 characters, letters, numbers, and underscores only")
            email = st.text_input("Email", key="signup_email")
            
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name")
            with col2:
                last_name = st.text_input("Last Name")
            
            password = st.text_input("Password", type="password", key="signup_password", 
                                    help="Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            signup_button = st.form_submit_button("Sign Up", use_container_width=True)
            
            if signup_button:
                if not all([username, email, first_name, last_name, password, confirm_password]):
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Validate password
                    valid, msg = validate_password(password)
                    if not valid:
                        st.error(msg)
                    else:
                        success, message = signup(username, email, password, first_name, last_name)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

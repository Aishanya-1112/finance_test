# WDMMG - Where Does My Money Go

Personal finance tracker with user authentication and transaction management.

# WDMMG - Where Does My Money Go

Personal finance tracker with user authentication and transaction management.

## Features

### Authentication & Security
- User authentication (Email/Password + Google OAuth)
- Secure JWT token-based authentication with automatic refresh
- Auto-logout after 30 minutes of inactivity
- XSS protection with input sanitization
- Rate limiting on all API endpoints
- Data encryption at rest (Supabase default)

### Transaction Management
- Add, Edit, Delete transactions
- **NEW:** Edit transaction dates
- **NEW:** Bulk delete multiple transactions
- **NEW:** Search transactions by description
- **NEW:** Date range filters (This Month, Last Month, This Year, Custom Range)
- Category-based filtering
- Decimal precision for accurate money calculations

### Budgeting (NEW)
- Set monthly budgets per category
- Real-time budget status tracking
- Visual indicators (exceeded, warning, ok)
- Budget vs. actual spending comparison

### Analytics & Visualization
- Category-based spending analytics with interactive pie charts
- **NEW:** Monthly and yearly spending trends with line charts
- Real-time spending calculations
- Budget progress tracking

### Data Export (NEW)
- Export transactions to Excel (.xlsx)
- Formatted export with timestamp, category, amount, and description

### Error Handling
- Graceful handling of database connection issues
- User-friendly error messages
- Automatic token refresh to prevent session expiration

## Categories

- Food
- Transport
- Housing
- Bills & Utilities
- Shopping
- Health
- Entertainment
- Savings / Investments
- Misc/others

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth
- **Visualization**: Plotly

## Setup Instructions

### 1. Supabase Setup

1. Create a new Supabase project at https://supabase.com
2. Go to the SQL Editor and run the queries from `SUPABASE_SETUP.sql`
   - This will create tables for user_profiles, transactions, and budgets
   - Enables Row Level Security (RLS) for data protection
3. Enable Google OAuth (optional):
   - Go to Authentication > Providers
   - Enable Google provider
   - Add your Google OAuth credentials

**Important:** To avoid rate limiting issues during signup:
- Go to Authentication → Providers → Email
- Turn off "Confirm email" (for development/personal use)

### 2. Environment Configuration

1. Copy `backend/.env.example` to `backend/.env`
2. Update with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**

Open a **new terminal** and run:
```bash
streamlit run frontend/app.py
```

The app will open at `http://localhost:8501`

## What's New in v2.0

### Critical Fixes
- ✅ **Token Refresh**: Automatic JWT token refresh prevents unexpected logouts
- ✅ **Secure Token Handling**: Proper refresh token storage and management
- ✅ **Fixed Logout**: Client-side logout properly clears session
- ✅ **XSS Protection**: Input sanitization prevents malicious scripts
- ✅ **Rate Limiting**: API protection against request flooding
- ✅ **Decimal Precision**: Accurate money calculations (no more rounding errors)
- ✅ **Error Recovery**: Graceful handling when database is unavailable

### New Features
- 📅 **Date Range Filters**: Quick filters for This Month, Last Month, This Year, or Custom Range
- 🔍 **Search**: Find transactions by description
- 📊 **Budget Tracking**: Set monthly budgets per category and monitor spending
- 📈 **Spending Trends**: Visualize monthly/yearly spending patterns
- ✏️ **Edit Transaction Dates**: Change transaction dates and times
- 🗑️ **Bulk Delete**: Select and delete multiple transactions at once
- 📥 **Excel Export**: Download your transactions as Excel spreadsheet

## User Authentication

### Sign Up Requirements:
- **Username**: 3-30 characters, letters/numbers/underscores only, must be unique
- **Email**: Valid email address
- **Password**: 
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character
- **First Name & Last Name**: Required

### Login:
- Email and password
- Google OAuth (if configured in Supabase)

### Session:
- Auto-logout after 30 minutes of inactivity
- Manual logout available

## Security Features

- User-specific data isolation (RLS policies)
- Encrypted data at rest (Supabase)
- Secure password requirements
- JWT-based authentication
- Session management with timeout

## Usage

1. **Sign Up/Login**: Create an account or login to access your dashboard
2. **Add Transaction**: Enter amount (₹), select category, and add description (mandatory)
3. **View Spending**: Interactive pie chart shows spending breakdown by category
4. **Edit Transaction**: Click "Edit" button to modify amount, category, or description
5. **Delete Transaction**: Click "Delete" button to remove a transaction
6. **Filter**: Use category filter to view specific transaction types
7. **Track Total**: See your total spending displayed below the chart

## API Endpoints

### Auth
- `POST /auth/signup` - Create new account
- `POST /auth/login` - Login
- `POST /auth/google` - Google OAuth
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user

### Transactions (All require authentication)
- `GET /categories` - Get all categories
- `POST /transactions` - Create transaction
- `GET /transactions` - Get all user transactions
- `GET /transactions/{id}` - Get specific transaction
- `PUT /transactions/{id}` - Update transaction
- `DELETE /transactions/{id}` - Delete transaction
- `GET /stats/by-category` - Get spending stats

## Project Structure

```
Finance tracker/
├── backend/
│   ├── main.py          # FastAPI backend with auth
│   ├── auth.py          # Authentication utilities
│   ├── .env.example     # Environment template
│   └── .env            # Your credentials (create this)
├── frontend/
│   ├── app.py           # Main Streamlit app
│   └── auth_ui.py       # Authentication UI components
├── SUPABASE_SETUP.sql   # Database schema
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Notes

- All user data is isolated and encrypted
- Sessions expire after 30 minutes of inactivity
- Google OAuth requires configuration in Supabase
- Description field is mandatory for all transactions

- Add database persistence (SQLite/PostgreSQL)
- Export transactions to CSV/Excel
- Date range filtering
- Edit transaction functionality
- Income vs Expense tracking
- Monthly/yearly reports
- Budget setting and alerts

---

Made with ❤️ using Streamlit and FastAPI

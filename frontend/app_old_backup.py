import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from auth_ui import (
    init_session_state, 
    check_session_timeout, 
    show_login_page, 
    logout, 
    get_auth_headers,
    update_activity
)
from io import BytesIO

# Backend API URL
API_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="WDMMG",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
init_session_state()

# Check for session timeout
if check_session_timeout():
    st.rerun()

# Show login page if not authenticated
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .user-info {
        text-align: right;
        color: gray;
        padding: 10px;
    }
    
    /* Mobile Responsive Styles */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        .user-info {
            text-align: center;
            font-size: 0.9rem;
        }
        /* Make tables scrollable on mobile */
        .dataframe {
            font-size: 0.8rem;
        }
        /* Adjust spacing */
        .stButton button {
            width: 100%;
            padding: 0.5rem;
            font-size: 0.9rem;
        }
        /* Make form inputs full width */
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {
            width: 100%;
        }
        /* Adjust metric display */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
    }
    
    /* Improve transaction card display */
    .transaction-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    
    @media (max-width: 768px) {
        .transaction-card {
            padding: 0.75rem;
            font-size: 0.9rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# User info and logout button
if st.session_state.user:
    # Mobile-friendly header layout
    st.markdown('<h1 class="main-header">WDMMG</h1>', unsafe_allow_html=True)
    
    col_welcome, col_logout = st.columns([3, 1])
    with col_welcome:
        st.markdown(f'<div class="user-info" style="text-align: left;">Welcome, {st.session_state.user["first_name"]}!</div>', unsafe_allow_html=True)
    with col_logout:
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

# Main tabs for different sections
tab1, tab2, tab3 = st.tabs(["📊 Transactions", "💰 Budgets", "📈 Trends"])

# Helper functions (defined before tabs)
def get_categories():
    """Fetch categories from API"""
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_URL}/categories", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching categories: {e}")
    return []


def add_transaction(amount, category, description):
    """Add a new transaction"""
    try:
        headers = get_auth_headers()
        data = {
            "amount": amount,
            "category": category,
            "description": description
        }
        response = requests.post(f"{API_URL}/transactions", json=data, headers=headers)
        if response.status_code == 200:
            return True, "Transaction added successfully!"
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return False, f"Error: {e}"


def get_transactions():
    """Fetch all transactions"""
    try:
        headers = get_auth_headers()
        params = {}
        
        # Add filters if they exist in session state
        if 'filter_search' in st.session_state and st.session_state.filter_search:
            params['search'] = st.session_state.filter_search
        if 'filter_start_date' in st.session_state and st.session_state.filter_start_date:
            params['start_date'] = st.session_state.filter_start_date.isoformat()
        if 'filter_end_date' in st.session_state and st.session_state.filter_end_date:
            params['end_date'] = st.session_state.filter_end_date.isoformat()
        
        response = requests.get(f"{API_URL}/transactions", headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
    return []


def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        headers = get_auth_headers()
        response = requests.delete(f"{API_URL}/transactions/{transaction_id}", headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error deleting transaction: {e}")
        return False


def update_transaction(transaction_id, amount, category, description, timestamp):
    """Update a transaction"""
    try:
        headers = get_auth_headers()
        data = {
            "amount": amount,
            "category": category,
            "description": description,
            "timestamp": timestamp
        }
        response = requests.put(f"{API_URL}/transactions/{transaction_id}", json=data, headers=headers)
        if response.status_code == 200:
            return True, "Transaction updated successfully!"
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return False, f"Error: {e}"


def get_stats_by_category():
    """Fetch spending stats by category"""
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_URL}/stats/by-category", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
    return {}


def get_spending_trends(period="monthly"):
    """Fetch spending trends"""
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_URL}/stats/trends?period={period}", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching trends: {e}")
    return {}


def get_budgets():
    """Fetch all budgets"""
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_URL}/budgets", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching budgets: {e}")
    return []


def get_budget_status():
    """Fetch budget status"""
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_URL}/budgets/status", headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching budget status: {e}")
    return []


def create_budget(category, monthly_limit):
    """Create or update a budget"""
    try:
        headers = get_auth_headers()
        data = {"category": category, "monthly_limit": monthly_limit}
        response = requests.post(f"{API_URL}/budgets", json=data, headers=headers)
        if response.status_code == 200:
            return True, "Budget saved successfully!"
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return False, f"Error: {e}"


def delete_budget(budget_id):
    """Delete a budget"""
    try:
        headers = get_auth_headers()
        response = requests.delete(f"{API_URL}/budgets/{budget_id}", headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error deleting budget: {e}")
        return False


def bulk_delete_transactions(transaction_ids):
    """Delete multiple transactions"""
    try:
        headers = get_auth_headers()
        response = requests.post(f"{API_URL}/transactions/bulk-delete", json=transaction_ids, headers=headers)
        if response.status_code == 200:
            return True, response.json().get("message", "Transactions deleted")
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return False, f"Error: {e}"


def export_to_excel(transactions_df):
    """Export transactions to Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        transactions_df.to_excel(writer, index=False, sheet_name='Transactions')
    output.seek(0)
    return output


# Main layout - responsive
# On mobile, columns will stack automatically
col1, col2 = st.columns([1, 2] if st.session_state.get('is_desktop', True) else [1, 1])

# Left column: Add Transaction Form
with col1:
    st.subheader("Add Transaction")
    
    categories = get_categories()
    
    with st.form("add_transaction_form"):
        amount_input = st.text_input("Amount (₹)", placeholder="Enter amount")
        category = st.selectbox("Category", categories)
        description = st.text_area("Description", height=100, placeholder="Enter description")
        
        submitted = st.form_submit_button("Add Transaction", use_container_width=True)
        
        if submitted:
            if not description or description.strip() == "":
                st.error("Description is mandatory")
            else:
                try:
                    amount = float(amount_input)
                    if amount > 0:
                        success, message = add_transaction(amount, category, description)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Amount must be greater than 0")
                except ValueError:
                    st.error("Please enter a valid amount")

# Right column: Pie Chart
with col2:
    st.subheader("Spending by Category")
    
    stats = get_stats_by_category()
    
    if stats:
        # Create pie chart
        df_stats = pd.DataFrame(list(stats.items()), columns=['Category', 'Amount'])
        
        fig = px.pie(
            df_stats,
            values='Amount',
            names='Category',
            title='',
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>₹%{value:.2f}<br>%{percent}<extra></extra>'
        )
        
        fig.update_layout(
            showlegend=True,
            height=400,
            margin=dict(t=20, b=20, l=20, r=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display total
        total = sum(stats.values())
        st.metric("Total Spending", f"₹{total:.2f}")
    else:
        st.info("No transactions yet. Add your first transaction to see the chart!")

# Transactions table
st.markdown("---")
st.subheader("All Transactions")

# Filters
filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])

with filter_col1:
    filter_category = st.selectbox("Filter by Category", ["All"] + categories)

with filter_col3:
    if st.button("Refresh", use_container_width=True):
        st.rerun()

transactions = get_transactions()

if transactions:
    # Filter transactions
    if filter_category != "All":
        transactions = [t for t in transactions if t["category"] == filter_category]
    
    if transactions:
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Display transactions - mobile-friendly cards
        for idx, row in df.iterrows():
            # Use expandable card for better mobile UX
            with st.container():
                col_main, col_edit, col_del = st.columns([6, 1, 1])
                
                with col_main:
                    st.markdown(
                        f"""
                        <div class="transaction-card">
                            <strong style="font-size: 1.2rem; color: #1f77b4;">₹{row['amount']:.2f}</strong>
                            <span style="margin-left: 1rem; color: #666;">{row['category']}</span><br>
                            <small style="color: #888;">{row['description']}</small><br>
                            <small style="color: #aaa;">{row['date']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                with col_edit:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Edit", use_container_width=True):
                        st.session_state[f"editing_{row['id']}"] = True
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"delete_{row['id']}", help="Delete", use_container_width=True):
                        if delete_transaction(row['id']):
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete")
            
            # Edit form (shown when edit button is clicked)
            if st.session_state.get(f"editing_{row['id']}", False):
                with st.expander("✏️ Edit Transaction", expanded=True):
                    with st.form(key=f"edit_form_{row['id']}"):
                        new_amount_input = st.text_input(
                            "Amount (₹)",
                            value=str(row['amount']),
                            key=f"amt_{row['id']}"
                        )
                        new_category = st.selectbox(
                            "Category",
                            categories,
                            index=categories.index(row['category']) if row['category'] in categories else 0,
                            key=f"cat_{row['id']}"
                        )
                        new_description = st.text_area(
                            "Description",
                            value=row['description'],
                            height=100,
                            key=f"desc_{row['id']}"
                        )
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            save_clicked = st.form_submit_button("💾 Save", use_container_width=True)
                        
                        with col_cancel:
                            cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                        
                        if save_clicked:
                            if not new_description or new_description.strip() == "":
                                st.error("Description cannot be empty")
                            else:
                                try:
                                    new_amount = float(new_amount_input)
                                    if new_amount > 0:
                                        success, message = update_transaction(
                                            row['id'],
                                            new_amount,
                                            new_category,
                                            new_description,
                                            row['timestamp'].isoformat()
                                        )
                                        if success:
                                            st.success(message)
                                            st.session_state[f"editing_{row['id']}"] = False
                                            st.rerun()
                                        else:
                                            st.error(message)
                                    else:
                                        st.error("Amount must be greater than 0")
                                except ValueError:
                                    st.error("Please enter a valid amount")
                        
                        if cancel_clicked:
                            st.session_state[f"editing_{row['id']}"] = False
                            st.rerun()
    else:
        st.info(f"No transactions found for category: {filter_category}")
else:
    st.info("No transactions yet. Start by adding your first transaction!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>WDMMG v1.0 | Built with Streamlit & FastAPI</div>",
    unsafe_allow_html=True
)

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
        .dataframe {
            font-size: 0.8rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.5rem;
            font-size: 0.9rem;
        }
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {
            width: 100%;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
    }
    
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
    st.markdown('<h1 class="main-header">WDMMG</h1>', unsafe_allow_html=True)
    
    col_welcome, col_logout = st.columns([3, 1])
    with col_welcome:
        st.markdown(f'<div class="user-info" style="text-align: left;">Welcome, {st.session_state.user["first_name"]}!</div>', unsafe_allow_html=True)
    with col_logout:
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()


# Helper functions
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
        data = {"amount": amount, "category": category, "description": description}
        response = requests.post(f"{API_URL}/transactions", json=data, headers=headers)
        if response.status_code == 200:
            return True, "Transaction added successfully!"
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return False, f"Error: {e}"


def get_transactions(search=None, start_date=None, end_date=None):
    """Fetch all transactions with filters"""
    try:
        headers = get_auth_headers()
        params = {}
        if search:
            params['search'] = search
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
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
        data = {"amount": amount, "category": category, "description": description, "timestamp": timestamp}
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
    # Remove timezone info from datetime columns for Excel compatibility
    df_copy = transactions_df.copy()
    for col in df_copy.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
        df_copy[col] = df_copy[col].dt.tz_localize(None)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_copy.to_excel(writer, index=False, sheet_name='Transactions')
    output.seek(0)
    return output


# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Transactions", "💰 Budgets", "📈 Trends"])

# ============= TAB 1: TRANSACTIONS =============
with tab1:
    col1, col2 = st.columns([1, 2])
    
    # Left column: Add Transaction
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
            df_stats = pd.DataFrame(list(stats.items()), columns=['Category', 'Amount'])
            fig = px.pie(df_stats, values='Amount', names='Category', title='', hole=0.3, color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>₹%{value:.2f}<br>%{percent}<extra></extra>')
            fig.update_layout(showlegend=True, height=400, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
            
            total = sum(stats.values())
            st.metric("Total Spending", f"₹{total:.2f}")
        else:
            st.info("No transactions yet. Add your first transaction to see the chart!")
    
    st.markdown("---")
    st.subheader("All Transactions")
    
    # Enhanced Filters
    st.markdown("#### Filters")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        filter_category = st.selectbox("Category", ["All"] + categories, key="filter_cat")
    
    with filter_col2:
        date_presets = ["All Time", "This Month", "Last Month", "This Year", "Custom Range"]
        date_preset = st.selectbox("Date Range", date_presets, key="date_preset")
    
    # Calculate date range based on preset
    start_date, end_date = None, None
    if date_preset == "This Month":
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        end_date = now
    elif date_preset == "Last Month":
        now = datetime.now()
        first_of_this_month = datetime(now.year, now.month, 1)
        end_date = first_of_this_month - timedelta(days=1)
        start_date = datetime(end_date.year, end_date.month, 1)
    elif date_preset == "This Year":
        now = datetime.now()
        start_date = datetime(now.year, 1, 1)
        end_date = now
    elif date_preset == "Custom Range":
        with filter_col3:
            start_date = st.date_input("Start Date", key="custom_start")
            if start_date:
                start_date = datetime.combine(start_date, datetime.min.time())
        with filter_col4:
            end_date = st.date_input("End Date", key="custom_end")
            if end_date:
                end_date = datetime.combine(end_date, datetime.max.time())
    
    # Search and Export row
    search_col1, search_col2, search_col3 = st.columns([3, 1, 1])
    with search_col1:
        search_query = st.text_input("🔍 Search in descriptions", placeholder="Type to search...", key="search_input")
    
    with search_col2:
        if st.button("Refresh", use_container_width=True):
            st.rerun()
    
    # Fetch transactions with filters
    transactions = get_transactions(search=search_query, start_date=start_date, end_date=end_date)
    
    # Filter by category (client-side)
    if filter_category != "All":
        transactions = [t for t in transactions if t["category"] == filter_category]
    
    # Export button
    with search_col3:
        if transactions:
            df_export = pd.DataFrame(transactions)
            df_export['timestamp'] = pd.to_datetime(df_export['timestamp'], format='ISO8601')
            df_export = df_export.sort_values('timestamp', ascending=False)
            excel_data = export_to_excel(df_export[['timestamp', 'category', 'amount', 'description']])
            st.download_button(
                label="📥 Export",
                data=excel_data,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    if transactions:
        # Bulk selection
        st.markdown("##### Select transactions for bulk actions")
        selected_transactions = []
        
        df = pd.DataFrame(transactions)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
        df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        for idx, row in df.iterrows():
            col_check, col_main, col_edit, col_del = st.columns([0.5, 5.5, 1, 1])
            
            with col_check:
                if st.checkbox("", key=f"check_{row['id']}", label_visibility="collapsed"):
                    selected_transactions.append(row['id'])
            
            with col_main:
                amount_value = float(row['amount']) if isinstance(row['amount'], (int, float, str)) else row['amount']
                st.markdown(f"""
                    <div class="transaction-card">
                        <strong style="font-size: 1.2rem; color: #1f77b4;">₹{amount_value:.2f}</strong>
                        <span style="margin-left: 1rem; color: #666;">{row['category']}</span><br>
                        <small style="color: #888;">{row['description']}</small><br>
                        <small style="color: #aaa;">{row['date']}</small>
                    </div>
                """, unsafe_allow_html=True)
            
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
            
            # Edit form
            if st.session_state.get(f"editing_{row['id']}", False):
                with st.expander("✏️ Edit Transaction", expanded=True):
                    with st.form(key=f"edit_form_{row['id']}"):
                        new_amount_input = st.text_input("Amount (₹)", value=str(row['amount']), key=f"amt_{row['id']}")
                        new_category = st.selectbox("Category", categories, index=categories.index(row['category']) if row['category'] in categories else 0, key=f"cat_{row['id']}")
                        new_description = st.text_area("Description", value=row['description'], height=100, key=f"desc_{row['id']}")
                        new_date = st.date_input("Date", value=row['timestamp'].date(), key=f"date_{row['id']}")
                        new_time = st.time_input("Time", value=row['timestamp'].time(), key=f"time_{row['id']}")
                        
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
                                        new_timestamp = datetime.combine(new_date, new_time)
                                        success, message = update_transaction(row['id'], new_amount, new_category, new_description, new_timestamp.isoformat())
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
        
        # Bulk delete button
        if selected_transactions:
            st.markdown("---")
            col_bulk1, col_bulk2, col_bulk3 = st.columns([1, 1, 3])
            with col_bulk1:
                st.write(f"**{len(selected_transactions)} selected**")
            with col_bulk2:
                if st.button("🗑️ Delete Selected", use_container_width=True):
                    success, message = bulk_delete_transactions(selected_transactions)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("No transactions found.")


# ============= TAB 2: BUDGETS =============
with tab2:
    st.subheader("Budget Management")
    
    categories = get_categories()
    
    # Add/Update Budget
    col_budget1, col_budget2 = st.columns([1, 2])
    
    with col_budget1:
        st.markdown("#### Set Budget")
        with st.form("budget_form"):
            budget_category = st.selectbox("Category", categories)
            budget_limit = st.number_input("Monthly Limit (₹)", min_value=0.0, step=100.0)
            budget_submit = st.form_submit_button("Save Budget", use_container_width=True)
            
            if budget_submit:
                if budget_limit > 0:
                    success, message = create_budget(budget_category, budget_limit)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Budget limit must be greater than 0")
    
    with col_budget2:
        st.markdown("#### Budget Status (Current Month)")
        budget_status = get_budget_status()
        
        if budget_status:
            for budget in budget_status:
                status_color = "🔴" if budget["status"] == "exceeded" else "🟡" if budget["status"] == "warning" else "🟢"
                
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 0.5])
                    with col1:
                        st.write(f"{status_color} **{budget['category']}**")
                        progress = min(budget['percentage'] / 100, 1.0)
                        st.progress(progress)
                    with col2:
                        st.metric("Spent / Limit", f"₹{budget['spent']:.2f} / ₹{budget['limit']:.2f}")
                    with col3:
                        st.write(f"{budget['percentage']:.0f}%")
        else:
            st.info("No budgets set yet.")
    
    st.markdown("---")
    st.markdown("#### Your Budgets")
    
    budgets = get_budgets()
    if budgets:
        for budget in budgets:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**{budget['category']}**")
            with col2:
                st.write(f"₹{budget['monthly_limit']:.2f} / month")
            with col3:
                if st.button("🗑️", key=f"del_budget_{budget['id']}", help="Delete", use_container_width=True):
                    if delete_budget(budget['id']):
                        st.success("Budget deleted!")
                        st.rerun()
    else:
        st.info("No budgets created yet.")


# ============= TAB 3: TRENDS =============
with tab3:
    st.subheader("Spending Trends")
    
    trend_period = st.radio("Period", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
    period_param = trend_period.lower()
    
    trends = get_spending_trends(period=period_param)
    
    if trends:
        df_trends = pd.DataFrame(list(trends.items()), columns=['Period', 'Amount'])
        df_trends = df_trends.sort_values('Period')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_trends['Period'], y=df_trends['Amount'], mode='lines+markers', name='Spending', line=dict(color='#1f77b4', width=3), marker=dict(size=8)))
        fig.update_layout(title=f"{trend_period} Spending Trend", xaxis_title="Period", yaxis_title="Amount (₹)", height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary stats with peak period
        peak_amount = max(trends.values())
        peak_period = max(trends, key=trends.get)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", f"₹{sum(trends.values()):.2f}")
        with col2:
            st.metric("Average", f"₹{sum(trends.values()) / len(trends):.2f}")
        with col3:
            st.metric("Peak", f"₹{peak_amount:.2f}", delta=f"on {peak_period}")
    else:
        st.info("No transaction data available for trends.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>WDMMG v2.0 | Built with Streamlit & FastAPI</div>", unsafe_allow_html=True)

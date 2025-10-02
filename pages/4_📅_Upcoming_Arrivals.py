# -*- coding: utf-8 -*-
# pages/4_📅_Upcoming_Arrivals.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.holiday_niseko_api import HolidayNisekoAPI
from utils.normalize_upcoming_arrivals import normalize_upcoming_arrivals

st.set_page_config(page_title="Upcoming Arrivals", page_icon="🏂", layout="wide")

st.title("Upcoming Arrivals")

# Initialize API
try:
    api = HolidayNisekoAPI(
        username=st.secrets["hn_username"],
        password=st.secrets["hn_password"]
    )
except:
    try:
        api = HolidayNisekoAPI(
            username=st.secrets["username"],
            password=st.secrets["password"]
        )
    except:
        api = HolidayNisekoAPI(
            username=st.secrets["holidayniseko"]["USERNAME"],
            password=st.secrets["holidayniseko"]["PASSWORD"]
        )

# Date picker
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    arrival_date = st.date_input(
        "Arrivals on:",
        value=datetime.now().date(),
        key="arrival_date",
        label_visibility="collapsed"
    )

with col2:
    quick_options = {
        "Today": datetime.now().date(),
        "Tomorrow": datetime.now().date() + timedelta(days=1),
        "In 2 days": datetime.now().date() + timedelta(days=2),
        "In 3 days": datetime.now().date() + timedelta(days=3),
        "Next week": datetime.now().date() + timedelta(weeks=1),
    }
    
    quick_select = st.selectbox(
        "Quick Select",
        options=["— Quick Select —"] + list(quick_options.keys()),
        key="quick_select",
        label_visibility="collapsed"
    )
    
    if quick_select != "— Quick Select —":
        arrival_date = quick_options[quick_select]
        st.rerun()

with col3:
    find_button = st.button("Find arrivals", type="primary", use_container_width=True)

target_date_str = arrival_date.strftime("%Y-%m-%d")

if find_button:
    status_placeholder = st.empty()
    
    try:
        status_placeholder.info(f"Fetching bookings for {target_date_str}...")
        
        clean_date = target_date_str.replace("-", "")
        all_bookings = api.get_all_bookings(params={"date": clean_date})
        
        if all_bookings:
            df = normalize_upcoming_arrivals(all_bookings)
            
            if not df.empty:
                if "active" in df.columns:
                    df_active = df[df["active"] != 0].copy()
                else:
                    df_active = df.copy()
                
                st.session_state["arrivals_data"] = df_active
                st.session_state["arrivals_date"] = target_date_str
                status_placeholder.success(f"Found {len(df_active)} active arrivals")
            else:
                status_placeholder.warning("No bookings found.")
        else:
            status_placeholder.warning("No bookings found.")
            
    except Exception as e:
        status_placeholder.error(f"Error: {e}")
        st.exception(e)

if "arrivals_data" in st.session_state and st.session_state.get("arrivals_date") == target_date_str:
    df = st.session_state["arrivals_data"]
    
    # Select and reorder only the columns you want
    column_mapping = {
        "eid": "eid",
        "guest_name": "name",
        "nights": "nights",
        "property_name": "property_name",
        "room_type": "room_type",
        "guest_email": "email",
        "guest_phone": "phone",
        "arrival_date": "arrival_date",
        "departure_date": "departure_date",
        "invoices_total_amount": "invoices_total_amount",
        "payments_total_amount": "payments_total_amount",
        "source": "source"
    }
    
    # Check which columns exist and select them
    available_cols = [col for col in column_mapping.keys() if col in df.columns]
    
    if len(available_cols) < len(column_mapping):
        missing = set(column_mapping.keys()) - set(available_cols)
        st.warning(f"Missing columns: {missing}")
    
    df_display = df[available_cols].copy()
    
    # Rename for display
    df_display.columns = [column_mapping.get(col, col) for col in df_display.columns]
    
    st.success(f"Showing {len(df_display)} active arrivals for {target_date_str}")
    
    # Function to highlight rows where invoice != payment
    def highlight_payment_mismatch(row):
        if row['invoices_total_amount'] != row['payments_total_amount']:
            return ['background-color: #ffcccc'] * len(row)
        return [''] * len(row)
    
    # Apply styling
    styled_df = df_display.style.apply(highlight_payment_mismatch, axis=1)
    
    # Configure column widths
    column_config = {
        "eid": st.column_config.TextColumn("EID", width="small"),
        "name": st.column_config.TextColumn("Name", width="medium"),
        "nights": st.column_config.NumberColumn("Nights", width="small"),
        "property_name": st.column_config.TextColumn("Property", width="medium"),
        "room_type": st.column_config.TextColumn("Room Type", width="medium"),
        "email": st.column_config.TextColumn("Email", width="medium"),
        "phone": st.column_config.TextColumn("Phone", width="small"),
        "arrival_date": st.column_config.DateColumn("Arrival", width="small"),
        "departure_date": st.column_config.DateColumn("Departure", width="small"),
        "invoices_total_amount": st.column_config.NumberColumn("Invoice Total", width="small", format="%.0f"),
        "payments_total_amount": st.column_config.NumberColumn("Payment Total", width="small", format="%.0f"),
        "source": st.column_config.TextColumn("Source", width="small"),
    }
    
    # Display with styling
    st.dataframe(
        styled_df,
        use_container_width=True, 
        hide_index=True, 
        height=None,
        column_config=column_config
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"arrivals_{target_date_str}.csv",
            mime="text/csv"
        )
    
    # with col2:
    #     json_str = df_display.to_json(orient='records', indent=2)
    #     st.download_button(
    #         label="Download JSON",
    #         data=json_str,
    #         file_name=f"arrivals_{target_date_str}.json",
    #         mime="application/json"
    #     )
    
    # with st.expander("Summary by property", expanded=False):
    #     if "property_name" in df.columns:
    #         summary = df.groupby("property_name").size().reset_index(name="count")
    #         summary = summary.sort_values("count", ascending=False)
    #         st.dataframe(summary, use_container_width=True, hide_index=True)
    #     else:
    #         st.info("Property name column not available.")
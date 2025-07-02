# -*- coding: utf-8 -*-
# pages/2_📊_Recent_Bookings.py

import streamlit as st
import datetime
from ui.recent_bookings import RecentBookingsManager

# Page configuration
st.set_page_config(
    page_title="Recent Bookings",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize the recent bookings manager
def get_recent_bookings_manager():
    # Initialize session state first
    if "recent_bookings_data" not in st.session_state:
        st.session_state.recent_bookings_data = []
    
    if "recent_bookings_last_refresh" not in st.session_state:
        st.session_state.recent_bookings_last_refresh = None
        
    if "recent_bookings_filter" not in st.session_state:
        st.session_state.recent_bookings_filter = "today"
        
    if "recent_bookings_initialized" not in st.session_state:
        st.session_state.recent_bookings_initialized = False
        
    if "recent_bookings_parsed_cache" not in st.session_state:
        st.session_state.recent_bookings_parsed_cache = {}
        
    if "recent_bookings_last_filter_state" not in st.session_state:
        st.session_state.recent_bookings_last_filter_state = None
    
    return RecentBookingsManager()

def main():
    """Main function for the Recent Bookings page"""
    
    # Initialize manager
    manager = get_recent_bookings_manager()
    
    # Main recent bookings section with unpaid highlighting
    manager.display_recent_bookings_section(location="page")
    
    # Additional features section
    st.markdown("---")
    
    with st.expander("📈 Advanced Analytics", expanded=False):
        st.info("Advanced analytics features coming soon!")
        
        # Placeholder for future features
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Booking Sources Breakdown")
            st.write("Chart showing booking sources over time")
            
        with col2:
            st.subheader("Revenue Trends")
            st.write("Revenue trends by booking type")
    
    # Sidebar with additional controls
    with st.sidebar:
        st.header("🔧 Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox(
            "Auto-refresh every 5 minutes",
            value=False,
            help="Automatically refresh booking data"
        )
        
        if auto_refresh:
            st.info("Auto-refresh enabled")
            # You can implement auto-refresh logic here
        
        # Export options
        st.subheader("📤 Export Options")
        
        if st.button("Export to CSV", use_container_width=True):
            st.info("CSV export feature coming soon!")
        
        if st.button("Export to Excel", use_container_width=True):
            st.info("Excel export feature coming soon!")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("Refresh All Data", use_container_width=True):
            # Clear cache and force refresh
            st.cache_data.clear()
            st.rerun()
        
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

if __name__ == "__main__":
    main()
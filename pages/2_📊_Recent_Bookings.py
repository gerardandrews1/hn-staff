# -*- coding: utf-8 -*-
# pages/2_📊_Recent_Bookings.py - Enhanced with Check-in, Nights, and Country Information

import streamlit as st
import datetime
import pandas as pd
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

def create_enhanced_csv_export(bookings_data):
    """Create CSV export with enhanced booking data including new fields"""
    if not bookings_data:
        return None
    
    # Convert to DataFrame with all the enhanced fields
    export_data = []
    for booking in bookings_data:
        export_data.append({
            'eID': booking.get('e_id', ''),
            'Booking ID': booking.get('booking_id', ''),
            'Guest Name': booking.get('guest_name', ''),
            'Check-in Date': booking.get('checkin_date_raw', ''),  # Use raw date for export
            'Check-out Date': booking.get('checkout_date_raw', ''),
            'Nights': booking.get('nights', 0),
            'Country': booking.get('country', ''),
            'Guests': booking.get('guests', 0),
            'Vendor': booking.get('vendor', ''),
            'Booking Source': booking.get('booking_source', ''),
            'Sell Price': booking.get('sell_price_raw', 0),
            'Amount Invoiced': booking.get('amount_invoiced_raw', 0),
            'Amount Received': booking.get('amount_received_raw', 0),
            'Status': booking.get('status', ''),
            'Booking Type': booking.get('booking_type', ''),
            'Extent': booking.get('extent', ''),
            'Created Date': booking.get('created_date', ''),
            'Service Name': booking.get('service_name', ''),
            'Package ID': booking.get('package_id', '')
        })
    
    df = pd.DataFrame(export_data)
    return df.to_csv(index=False)

def main():
    """Main function for the Recent Bookings page"""
    
    # Initialize manager
    manager = get_recent_bookings_manager()
    
    # Main recent bookings section with unpaid highlighting
    manager.display_recent_bookings_section(location="page")
    
    # Additional features section
    st.markdown("---")
    
    with st.expander("📈 Advanced Analytics", expanded=False):
        st.info("Enhanced analytics with new booking fields!")
        
        # Show summary of new fields if data is available
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            bookings = st.session_state.filtered_bookings_data
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Country Breakdown")
                countries = [b.get('country', 'Unknown') for b in bookings if b.get('country') != 'N/A']
                if countries:
                    country_counts = pd.Series(countries).value_counts()
                    st.bar_chart(country_counts)
                    
                    # Show top countries as text
                    st.write("**Top Countries:**")
                    for country, count in country_counts.head(5).items():
                        percentage = (count / len(countries)) * 100
                        st.write(f"• {country}: {count} bookings ({percentage:.1f}%)")
                else:
                    st.write("No country data available")
                
            with col2:
                st.subheader("Nights Distribution")
                nights_data = [b.get('nights', 0) for b in bookings if b.get('nights', 0) > 0]
                if nights_data:
                    nights_df = pd.DataFrame({'Nights': nights_data})
                    night_counts = nights_df['Nights'].value_counts().sort_index()
                    st.bar_chart(night_counts)
                    
                    # Show nights statistics
                    avg_nights = sum(nights_data) / len(nights_data)
                    max_nights = max(nights_data)
                    min_nights = min(nights_data)
                    
                    st.write("**Nights Statistics:**")
                    st.write(f"• Average: {avg_nights:.1f} nights")
                    st.write(f"• Range: {min_nights} - {max_nights} nights")
                    st.write(f"• Total nights: {sum(nights_data)}")
                else:
                    st.write("No nights data available")
        
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Booking Sources Breakdown")
                st.write("Select bookings above to see analytics")
                
            with col2:
                st.subheader("Revenue Trends")
                st.write("Select bookings above to see analytics")
    
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
        
        # Export options
        st.subheader("📤 Export Options")
        
        # Enhanced CSV export with new fields
        if st.button("Export Enhanced CSV", use_container_width=True):
            if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
                csv_data = create_enhanced_csv_export(st.session_state.filtered_bookings_data)
                if csv_data:
                    st.download_button(
                        label="📥 Download Enhanced CSV",
                        data=csv_data,
                        file_name=f"enhanced_recent_bookings_{datetime.date.today()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success("✅ Enhanced CSV ready for download!")
                else:
                    st.error("Failed to create CSV")
            else:
                st.warning("No data to export. Please load some bookings first.")
        
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
        
        # Data preview for new fields
        st.subheader("📊 Enhanced Data Preview")
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            bookings = st.session_state.filtered_bookings_data
            
            # Show summary of new fields
            total_nights = sum(b.get('nights', 0) for b in bookings if b.get('nights', 0) > 0)
            unique_countries = len(set(b.get('country', 'N/A') for b in bookings if b.get('country') != 'N/A'))
            avg_nights = total_nights / len([b for b in bookings if b.get('nights', 0) > 0]) if any(b.get('nights', 0) > 0 for b in bookings) else 0
            
            st.metric("Total Nights", total_nights)
            st.metric("Unique Countries", unique_countries)
            st.metric("Avg Nights/Booking", f"{avg_nights:.1f}")
            
            # Show check-in date range
            checkin_dates = [b.get('checkin_date_raw', '') for b in bookings if b.get('checkin_date_raw')]
            if checkin_dates:
                try:
                    dates = [pd.to_datetime(d) for d in checkin_dates if d]
                    if dates:
                        earliest = min(dates).strftime('%Y-%m-%d')
                        latest = max(dates).strftime('%Y-%m-%d')
                        st.write(f"**Check-in Range:**")
                        st.write(f"{earliest} to {latest}")
                except:
                    st.write("**Check-in dates:** Available")
            
            # Country distribution pie chart
            countries = [b.get('country', 'Unknown') for b in bookings if b.get('country') != 'N/A']
            if len(set(countries)) > 1:
                st.write("**Country Distribution:**")
                country_counts = pd.Series(countries).value_counts()
                for country, count in country_counts.head(3).items():
                    st.write(f"• {country}: {count}")
                if len(country_counts) > 3:
                    st.write(f"• +{len(country_counts) - 3} more countries")
        else:
            st.info("Load booking data to see enhanced metrics")
            
        # Show what's new
        with st.expander("✨ What's New", expanded=False):
            st.markdown("""
            **Enhanced Recent Bookings now includes:**
            
            🗓️ **Check-in Date** - Guest arrival date  
            🌙 **Nights** - Calculated stay duration  
            🌍 **Country** - Guest nationality/country  
            📊 **Enhanced Analytics** - Country & nights charts  
            📥 **Enhanced Export** - CSV with all new fields  
            📈 **Smart Metrics** - Total nights, countries, averages  
            
            **Data Sources:**
            - Check-in: `items[0].checkIn`
            - Nights: Calculated from check-in/out dates
            - Country: `leadGuest.nationality`
            """)

if __name__ == "__main__":
    main()
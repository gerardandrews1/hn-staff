# -*- coding: utf-8 -*-
# pages/2_📊_Recent_Bookings.py - Enhanced with Check-in, Nights, and Country Information

import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

def calculate_booking_rate(bookings):
    """Calculate booking rate based on actual booking date range"""
    if not bookings:
        return 0
    
    # Try to get created dates first, then check-in dates as fallback
    booking_dates = []
    
    # First try created dates (when the booking was made)
    for booking in bookings:
        created_date = booking.get('created_date', '')
        if created_date:
            try:
                # Handle different date formats
                if 'T' in created_date:
                    # ISO format with time
                    date_obj = pd.to_datetime(created_date).date()
                else:
                    # Date only format
                    date_obj = pd.to_datetime(created_date).date()
                booking_dates.append(date_obj)
            except:
                continue
    
    # If no created dates, fallback to check-in dates
    if not booking_dates:
        for booking in bookings:
            checkin_date = booking.get('checkin_date_raw', '')
            if checkin_date:
                try:
                    date_obj = pd.to_datetime(checkin_date).date()
                    booking_dates.append(date_obj)
                except:
                    continue
    
    if not booking_dates:
        return 0
    
    # Calculate date range
    min_date = min(booking_dates)
    max_date = max(booking_dates)
    
    # If all bookings are on the same date
    if min_date == max_date:
        return len(bookings)  # All bookings in 1 day
    
    # Calculate days between min and max (inclusive)
    date_range_days = (max_date - min_date).days + 1
    
    # Return bookings per day
    return len(bookings) / date_range_days

def main():
    """Main function for the Recent Bookings page"""
    
    # Initialize manager
    manager = get_recent_bookings_manager()
    
    # Main recent bookings section with unpaid highlighting
    manager.display_recent_bookings_section(location="page")
    
    # Additional features section
    st.markdown("---")
    
    with st.expander("📈 Analytics", expanded=False):
        # Show summary of new fields if data is available
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            bookings = st.session_state.filtered_bookings_data
            st.write(len(bookings), "BOOKS")
            
            # Key Metrics Row
            st.subheader("Key Metrics")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Calculate totals
            total_gross = sum(b.get('sell_price_raw', 0) for b in bookings if b.get('sell_price_raw', 0) > 0)
            total_nights = sum(b.get('nights', 0) for b in bookings if b.get('nights', 0) > 0)
            total_bookings = len(bookings)
            avg_nights = total_nights / total_bookings if total_bookings > 0 else 0
            
            # Calculate booking rate using the fixed function
            filter_option = st.session_state.get("recent_filter_select_page", "7 days")
            start_date = st.session_state.get("recent_start_date_page", None)
            end_date = st.session_state.get("recent_end_date_page", None)

            # Calculate days in period (same logic as main UI)
            if filter_option == "Last 24 hours":
                days_in_period = 1
            elif filter_option == "2 days":
                days_in_period = 2
            elif filter_option == "3 days":
                days_in_period = 3
            elif filter_option == "5 days":
                days_in_period = 5
            elif filter_option == "7 days":
                days_in_period = 7
            elif filter_option == "14 days":
                days_in_period = 14
            elif filter_option == "Month to Date":
                today = datetime.date.today()
                month_start = today.replace(day=1)
                days_in_period = (today - month_start).days + 1
            elif filter_option == "Custom" and start_date and end_date:
                delta = end_date - start_date
                days_in_period = delta.days + 1
            else:
                days_in_period = 7  # Default fallback

            # Calculate booking rate using filter period (same as main UI)
            booking_rate = total_bookings / days_in_period if days_in_period > 0 else 0
            
            with col1:
                st.metric(
                    label="Total Gross Revenue",
                    value=f"${total_gross:,.2f}" if total_gross > 0 else "N/A",
                    help="Sum of all sell prices"
                )
            
            with col2:
                st.metric(
                    label="Total Nights",
                    value=f"{total_nights:,}" if total_nights > 0 else "N/A",
                    help="Sum of all booking nights"
                )
            
            with col3:
                st.metric(
                    label="Total Bookings",
                    value=f"{total_bookings:,}",
                    help="Number of bookings in current filter"
                )
            
            with col4:
                st.metric(
                    label="Avg Nights/Booking",
                    value=f"{avg_nights:.1f}" if avg_nights > 0 else "N/A",
                    help="Average nights per booking"
                )
            
            with col5:
                st.metric(
                    label="Booking Rate",
                    value=f"{booking_rate:.1f}/day" if booking_rate > 0 else "N/A",
                    help="Average bookings per day based on actual booking date range"
                )
            
            st.markdown("---")
            
            # Charts Row
            col1, col2 = st.columns(2)
            
            # 1. COUNTRY BREAKDOWN - Plotly version that actually sorts
            with col1:
                st.subheader("Country Breakdown")
                countries = [b.get('country', 'Unknown') for b in bookings if b.get('country') and b.get('country') != 'N/A']
                if countries:
                    country_counts = pd.Series(countries).value_counts()
                    
                    # Get top 8 countries
                    top_countries = country_counts.head(8)
                    
                    # Create properly sorted DataFrame for Plotly
                    chart_df = pd.DataFrame({
                        'Country': top_countries.index,
                        'Bookings': top_countries.values
                    })
                    
                    # Sort by bookings ascending (puts largest at top for horizontal bars)
                    chart_df = chart_df.sort_values('Bookings', ascending=True)
                    
                    # Create Plotly horizontal bar chart
                    fig = px.bar(
                        chart_df, 
                        x='Bookings', 
                        y='Country',
                        orientation='h',
                        height=220,
                        color_discrete_sequence=['#1f77b4']  # Streamlit blue
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        showlegend=False,
                        xaxis_title="",
                        yaxis_title=""
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary stats
                    total_countries = len(set(countries))
                    top_country = country_counts.index[0]
                    top_country_share = (country_counts.iloc[0] / len(countries)) * 100
                    st.write(f"**{total_countries} countries** • Top: {top_country} ({top_country_share:.0f}%)")
                else:
                    st.info("No country data available")
            
            # 2. BOOKING CHANNELS - Plotly version that actually sorts
            with col2:
                st.subheader("Booking Channels")
                booking_sources = [b.get('booking_source', 'Unknown') for b in bookings if b.get('booking_source')]
                if booking_sources:
                    # Group staff bookings together
                    grouped_sources = []
                    for source in booking_sources:
                        if 'staff' in source.lower() or source.lower().startswith('staff'):
                            grouped_sources.append('Staff')
                        else:
                            grouped_sources.append(source)
                    
                    source_counts = pd.Series(grouped_sources).value_counts()
                    
                    # Get top 6 channels
                    top_sources = source_counts.head(6)
                    
                    # Create properly sorted DataFrame for Plotly
                    chart_df = pd.DataFrame({
                        'Channel': top_sources.index,
                        'Bookings': top_sources.values
                    })
                    
                    # Sort by bookings ascending (puts largest at top for horizontal bars)
                    chart_df = chart_df.sort_values('Bookings', ascending=True)
                    
                    # Create Plotly horizontal bar chart
                    fig = px.bar(
                        chart_df, 
                        x='Bookings', 
                        y='Channel',
                        orientation='h',
                        height=220,
                        color_discrete_sequence=['#1f77b4']  # Streamlit blue
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        showlegend=False,
                        xaxis_title="",
                        yaxis_title=""
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary stats
                    total_channels = len(set(grouped_sources))
                    top_channel = source_counts.index[0]
                    top_channel_share = (source_counts.iloc[0] / len(grouped_sources)) * 100
                    st.write(f"**{total_channels} channels** • Top: {top_channel} ({top_channel_share:.0f}%)")
                else:
                    st.info("No booking channel data available")
            
            # Second row of charts
            col3, col4 = st.columns(2)
            
            # 3. NIGHTS DISTRIBUTION - Plotly version that actually sorts
            with col3:
                st.subheader("Nights Distribution")
                nights_data = [b.get('nights', 0) for b in bookings if b.get('nights', 0) > 0]
                if nights_data:
                    # Count nights and get top 10
                    night_counts = pd.Series(nights_data).value_counts().sort_index()
                    display_nights = night_counts.head(10)
                    
                    # Create properly sorted DataFrame for Plotly
                    chart_df = pd.DataFrame({
                        'Nights': display_nights.index.astype(str),  # Convert to string for proper display
                        'Bookings': display_nights.values
                    })
                    
                    # Sort by bookings ascending (puts largest at top for horizontal bars)
                    chart_df = chart_df.sort_values('Bookings', ascending=True)
                    
                    # Create Plotly horizontal bar chart
                    fig = px.bar(
                        chart_df, 
                        x='Bookings', 
                        y='Nights',
                        orientation='h',
                        height=220,
                        color_discrete_sequence=['#1f77b4']  # Streamlit blue
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        showlegend=False,
                        xaxis_title="",
                        yaxis_title=""
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary stats
                    avg_nights_calc = sum(nights_data) / len(nights_data)
                    most_common_nights = night_counts.idxmax()
                    st.write(f"**Avg: {avg_nights_calc:.1f} nights** • Most common: {most_common_nights} nights")
                else:
                    st.info("No nights data available")
            
            # 4. REVENUE BY CHANNEL - Plotly version that actually sorts
            with col4:
                st.subheader("Revenue by Channel")
                if booking_sources:
                    # Calculate revenue by booking source (with staff grouping)
                    revenue_by_source = {}
                    for booking in bookings:
                        source = booking.get('booking_source', 'Unknown')
                        revenue = booking.get('sell_price_raw', 0)
                        if source and revenue > 0:
                            # Group staff bookings together
                            if 'staff' in source.lower() or source.lower().startswith('staff'):
                                grouped_source = 'Staff'
                            else:
                                grouped_source = source
                            revenue_by_source[grouped_source] = revenue_by_source.get(grouped_source, 0) + revenue
                    
                    if revenue_by_source:
                        # Create series and get top 6
                        revenue_series = pd.Series(revenue_by_source)
                        top_revenue = revenue_series.nlargest(6)
                        
                        # Create properly sorted DataFrame for Plotly
                        chart_df = pd.DataFrame({
                            'Channel': top_revenue.index,
                            'Revenue': top_revenue.values
                        })
                        
                        # Sort by revenue ascending (puts largest at top for horizontal bars)
                        chart_df = chart_df.sort_values('Revenue', ascending=True)
                        
                        # Create Plotly horizontal bar chart
                        fig = px.bar(
                            chart_df, 
                            x='Revenue', 
                            y='Channel',
                            orientation='h',
                            height=220,
                            color_discrete_sequence=['#1f77b4']  # Streamlit blue
                        )
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            showlegend=False,
                            xaxis_title="",
                            yaxis_title="",
                            xaxis=dict(tickformat='$,.0f')  # Format x-axis to show currency
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary stats
                        top_revenue_channel = revenue_series.idxmax()
                        top_revenue_amount = revenue_series.max()
                        top_revenue_share = (top_revenue_amount / total_gross) * 100 if total_gross > 0 else 0
                        st.write(f"**Top: {top_revenue_channel}** • ${top_revenue_amount:,.0f} ({top_revenue_share:.0f}%)")
                    else:
                        st.info("No revenue data by channel available")
                else:
                    st.info("No booking channel data available")
            
            # Additional insights section
            st.markdown("---")
            st.subheader("Quick Insights")
            
            insights_col1, insights_col2 = st.columns(2)
            
            with insights_col1:
                # Top performing metrics
                if countries and booking_sources:
                    country_counts = pd.Series(countries).value_counts().sort_values(ascending=False)
                    grouped_sources = []
                    for source in booking_sources:
                        if 'staff' in source.lower() or source.lower().startswith('staff'):
                            grouped_sources.append('Staff')
                        else:
                            grouped_sources.append(source)
                    source_counts = pd.Series(grouped_sources).value_counts().sort_values(ascending=False)
                    
                    top_country = country_counts.index[0] if len(country_counts) > 0 else "N/A"
                    top_channel = source_counts.index[0] if len(source_counts) > 0 else "N/A"
                    
                    st.write("**Performance Highlights:**")
                    st.write(f"Top country: **{top_country}** ({country_counts.iloc[0]} bookings)")
                    st.write(f"Top channel: **{top_channel}** ({source_counts.iloc[0]} bookings)")
                    
                    if nights_data:
                        avg_revenue_per_night = (total_gross / total_nights) if total_nights > 0 else 0
                        st.write(f"Revenue per night: **${avg_revenue_per_night:.2f}**")
            
            with insights_col2:
                # Diversity metrics
                unique_countries = len(set(countries)) if countries else 0
                grouped_sources = []
                for source in booking_sources:
                    if 'staff' in source.lower() or source.lower().startswith('staff'):
                        grouped_sources.append('Staff')
                    else:
                        grouped_sources.append(source)
                unique_channels = len(set(grouped_sources)) if grouped_sources else 0
                
                st.write("**Market Diversity:**")
                st.write(f"Countries represented: **{unique_countries}**")
                st.write(f"Booking channels: **{unique_channels}**")
                
                if countries and len(country_counts) > 1:
                    # Calculate concentration (top country percentage)
                    top_country_concentration = (country_counts.iloc[0] / len(countries)) * 100
                    concentration_level = "High" if top_country_concentration > 50 else "Medium" if top_country_concentration > 30 else "Low"
                    st.write(f"Market concentration: **{concentration_level}** ({top_country_concentration:.1f}%)")
        
        else:
            # Show placeholder when no data
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Country Analytics")
                st.info("Select bookings above to see country breakdown")
                
            with col2:
                st.subheader("Channel Analytics")
                st.info("Select bookings above to see booking channels")
            
            st.subheader("Key Metrics")
            st.info("Load booking data to see total gross revenue, nights, and performance metrics")
    
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
            
            # Show booking rate calculation details
            filter_option = st.session_state.get("recent_filter_select_page", "7 days")
            start_date = st.session_state.get("recent_start_date_page", None)
            end_date = st.session_state.get("recent_end_date_page", None)

            if filter_option == "Month to Date":
                today = datetime.date.today()
                month_start = today.replace(day=1)
                days_in_period = (today - month_start).days + 1
                booking_rate = len(bookings) / days_in_period if days_in_period > 0 else 0
            else:
                booking_rate = calculate_booking_rate(bookings)

            st.metric("Booking Rate", f"{booking_rate:.1f}/day")
            
            # Show date range being used for booking rate
            booking_dates = []
            for booking in bookings:
                created_date = booking.get('created_date', '')
                if created_date:
                    try:
                        if 'T' in created_date:
                            date_obj = pd.to_datetime(created_date).date()
                        else:
                            date_obj = pd.to_datetime(created_date).date()
                        booking_dates.append(date_obj)
                    except:
                        continue
            
            if booking_dates:
                min_date = min(booking_dates)
                max_date = max(booking_dates)
                date_range_days = (max_date - min_date).days + 1
                st.write(f"**Rate Period:** {min_date} to {max_date} ({date_range_days} days)")
            
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
            ⚡ **Fixed Booking Rate** - Based on actual booking date range  
            📅 **Month to Date** - Filter for current month tracking  
            
            **Data Sources:**
            - Check-in: `items[0].checkIn`
            - Nights: Calculated from check-in/out dates
            - Country: `leadGuest.nationality`
            - Booking Rate: Uses `created_date` or `checkin_date_raw`
            """)

if __name__ == "__main__":
    main()
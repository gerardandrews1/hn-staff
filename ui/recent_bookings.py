# -*- coding: utf-8 -*-
# ui/recent_bookings.py - Updated with Internal Service Booking Debug

import streamlit as st
import pandas as pd
import datetime
from typing import List, Dict, Any, Optional

from services.api_list_recent_bookings import (
    get_today_bookings,
    get_last_n_days_bookings,
    get_recent_bookings_for_date_range
)

class RecentBookingsManager:
    """Manages the display and interaction with recent bookings"""
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables for recent bookings"""
        if "recent_bookings_data" not in st.session_state:
            st.session_state.recent_bookings_data = []
        
        if "recent_bookings_last_refresh" not in st.session_state:
            st.session_state.recent_bookings_last_refresh = None
            
        if "recent_bookings_filter" not in st.session_state:
            st.session_state.recent_bookings_filter = "today"
            
        # Add flag to prevent unnecessary API calls
        if "recent_bookings_initialized" not in st.session_state:
            st.session_state.recent_bookings_initialized = False
            
        # Add cache for parsed bookings to avoid re-parsing
        if "recent_bookings_parsed_cache" not in st.session_state:
            st.session_state.recent_bookings_parsed_cache = {}
            
        # Track last filter state to detect changes
        if "recent_bookings_last_filter_state" not in st.session_state:
            st.session_state.recent_bookings_last_filter_state = None
    
    def _should_refresh_data(self, filter_key: str) -> bool:
        """Check if data should be refreshed based on filter changes and time"""
        
        # Check if filter has changed
        if st.session_state.recent_bookings_last_filter_state != filter_key:
            return True
            
        # Check if enough time has passed (e.g., 5 minutes for auto-refresh)
        if st.session_state.recent_bookings_last_refresh:
            time_since_refresh = datetime.datetime.now() - st.session_state.recent_bookings_last_refresh
            if time_since_refresh.total_seconds() > 300:  # 5 minutes
                return True
                
        # Check if data is empty and we haven't initialized
        if not st.session_state.recent_bookings_data and not st.session_state.recent_bookings_initialized:
            return True
            
        return False
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def _fetch_bookings_cached(_self, filter_type: str, custom_days: int = 7, 
                              start_date: Optional[str] = None, end_date: Optional[str] = None):
        """Cached version of booking fetch to prevent duplicate API calls"""
        try:
            api_id = st.secrets["roomboss"]["api_id"]
            api_key = st.secrets["roomboss"]["api_key"]
            
            if filter_type == "today":
                result = get_today_bookings(api_id, api_key)
            elif filter_type == "last_n_days":
                result = get_last_n_days_bookings(custom_days, api_id, api_key)
            elif filter_type == "date_range" and start_date and end_date:
                result = get_recent_bookings_for_date_range(start_date, end_date, api_id, api_key)
            else:
                return {
                    'bookings': [],
                    'success': False,
                    'error': 'Invalid filter type or missing date parameters'
                }
            
            return result
            
        except Exception as e:
            return {
                'bookings': [],
                'success': False,
                'error': f"Error fetching recent bookings: {str(e)}"
            }
    
    def fetch_recent_bookings(
        self, 
        filter_type: str = "today",
        custom_days: int = 7,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch recent bookings with intelligent caching
        """
        
        # Create a unique filter key
        filter_key = f"{filter_type}_{custom_days}_{start_date}_{end_date}"
        
        # Check if we should refresh data
        if not force_refresh and not self._should_refresh_data(filter_key):
            # Return cached data if available
            if st.session_state.recent_bookings_data:
                return {
                    'bookings': st.session_state.recent_bookings_data,
                    'success': True,
                    'from_cache': True
                }
        
        try:
            # Use cached fetch method
            result = self._fetch_bookings_cached(
                filter_type, custom_days, start_date, end_date
            )
            
            # Debug: Show raw response data only if there's an error
            if not result.get('success', True):
                st.error(f"API Error: {result.get('error', 'Unknown error')}")
                return result
            
            if result.get('success', True):
                st.session_state.recent_bookings_data = result.get('bookings', [])
                st.session_state.recent_bookings_last_refresh = datetime.datetime.now()
                st.session_state.recent_bookings_filter = filter_type
                st.session_state.recent_bookings_initialized = True
                st.session_state.recent_bookings_last_filter_state = filter_key
                
                # Clear parsed cache when new data is loaded
                st.session_state.recent_bookings_parsed_cache = {}
                
                booking_count = len(result.get('bookings', []))
                if booking_count == 0:
                    st.info(f"No bookings found. {result.get('message', '')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching recent bookings: {str(e)}"
            st.error(error_msg)
            return {
                'bookings': [],
                'success': False,
                'error': error_msg
            }
    
    @st.cache_data(ttl=600)  # Cache parsed bookings for 10 minutes
    def _parse_bookings_cached(_self, bookings_data: str) -> List[Dict[str, Any]]:
        """Cache parsed bookings to avoid re-parsing the same data"""
        import json
        bookings = json.loads(bookings_data)
        return [_self.parse_booking_summary(booking) for booking in bookings]
    
    def get_parsed_bookings(self) -> List[Dict[str, Any]]:
        """Get parsed bookings with caching"""
        if not st.session_state.recent_bookings_data:
            return []
            
        # Create a cache key based on the data
        import json
        import hashlib
        data_str = json.dumps(st.session_state.recent_bookings_data, sort_keys=True)
        cache_key = hashlib.md5(data_str.encode()).hexdigest()
        
        # Check if we have cached parsed data
        if cache_key in st.session_state.recent_bookings_parsed_cache:
            return st.session_state.recent_bookings_parsed_cache[cache_key]
        
        # Parse and cache
        parsed_bookings = [self.parse_booking_summary(booking) for booking in st.session_state.recent_bookings_data]
        st.session_state.recent_bookings_parsed_cache[cache_key] = parsed_bookings
        
        return parsed_bookings

    def parse_booking_summary(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a booking from the recent bookings API into a summary format
        FIXED: Handle both nested and flat booking structures
        
        Args:
            booking_data: Raw booking data from API 
            
        Returns:
            Dictionary with parsed booking summary
        """
        
        # Handle different API response structures
        # Some APIs return nested structure with 'booking' key, others return flat
        if 'booking' in booking_data:
            # Nested structure from recent bookings API
            booking = booking_data.get('booking', {})
            invoice_payments = booking_data.get('invoicePayments', [])
        else:
            # Flat structure - the booking_data IS the booking
            booking = booking_data
            # For flat structure, invoice payments might be at the same level or missing
            invoice_payments = booking_data.get('invoicePayments', [])
        
        # Calculate invoice totals
        total_invoiced = 0
        total_received = 0

        for invoice_payment in invoice_payments:
            # Get invoice amount
            invoice_amount = invoice_payment.get('invoiceAmount', 0) or 0
            total_invoiced += invoice_amount
            
            # Get payment amount
            payment_amount = invoice_payment.get('paymentAmount', 0) or 0
            total_received += payment_amount
        
        # Extract basic info
        booking_id = booking.get('bookingId', '')
        e_id = booking.get('eId', '')
        package_id = booking.get('packageId', '')
        
        # Get vendor/property name based on booking type
        vendor = ""
        service_name = ""
        
        booking_type = booking.get('bookingType', '')
        
        if booking_type == 'ACCOMMODATION':
            hotel_info = booking.get('hotel', {})
            vendor = hotel_info.get('hotelName', '')
        elif booking_type == 'SERVICE':
            service_provider_info = booking.get('serviceProvider', {})
            vendor = service_provider_info.get('serviceProviderName', '')
            
            # Get service name from items
            items = booking.get('items', [])
            if items:
                first_item = items[0]
                service_info = first_item.get('service', {})
                service_name = service_info.get('serviceName', '') or service_info.get('name', '')
        
        # Extract guest info from leadGuest
        lead_guest = booking.get('leadGuest', {})
        guest_name = ""
        if lead_guest:
            given_name = lead_guest.get('givenName', '')
            family_name = lead_guest.get('familyName', '')
            guest_name = f"{given_name} {family_name}".strip()
        
        # Extract created date
        created_date = booking.get('createdDate', '')
        created_formatted = ""
        if created_date:
            try:
                created_dt = pd.to_datetime(created_date) + pd.offsets.Hour(9)  # JST
                created_formatted = created_dt.strftime("%m/%d %H:%M")
            except:
                created_formatted = created_date
        
        # Extract dates from items and calculate sell price
        checkin_date = ""
        checkin_formatted = ""
        nights = 0
        guests = 0
        sell_price = 0
        
        items = booking.get('items', [])
        if items:
            # Calculate total sell price from all items - prioritize priceSell
            for item in items:
                price_sell = item.get('priceSell', 0) or item.get('priceRetail', 0)
                sell_price += price_sell
            
            first_item = items[0]
            
            # For accommodation bookings
            if booking_type == 'ACCOMMODATION':
                checkin_date = first_item.get('checkIn', '')
                checkout_date = first_item.get('checkOut', '')
                guests = first_item.get('numberGuests', 0)
                
                if checkin_date and checkout_date:
                    try:
                        checkin_dt = pd.to_datetime(checkin_date)
                        checkout_dt = pd.to_datetime(checkout_date)
                        nights = (checkout_dt - checkin_dt).days
                        checkin_formatted = checkin_dt.strftime("%m/%d")
                    except:
                        checkin_formatted = checkin_date
            
            # For service bookings
            elif booking_type == 'SERVICE':
                start_date = first_item.get('startDate', '')
                end_date = first_item.get('endDate', '')
                
                if start_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        checkin_formatted = start_dt.strftime("%m/%d")
                        checkin_date = start_date
                    except:
                        checkin_formatted = start_date
                        checkin_date = start_date
                
                # For services, calculate duration
                if start_date and end_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        nights = (end_dt - start_dt).days
                        if nights == 0:  # Same day service
                            nights = 1
                    except:
                        nights = 1
                else:
                    nights = 1
        
        # Determine booking status
        is_active = booking.get('active', True)
        status = "Active" if is_active else "Cancelled"
        
        # Extract custom ID for source attribution  
        custom_id = booking.get('customId', '')
        booking_source_info = booking.get('bookingSource', '')
        booking_source = self._determine_booking_source(custom_id, booking_source_info)
        
        # Create display vendor name
        if booking_type == 'SERVICE' and service_name:
            display_vendor = f"{vendor} - {service_name}"
        else:
            display_vendor = vendor
        
        # Get extent information
        extent = booking.get('extent', '')
        
        return {
            'booking_id': booking_id,
            'e_id': str(e_id),
            'package_id': str(package_id),
            'vendor': display_vendor,
            'guest_name': guest_name,
            'created_date': created_formatted,
            'checkin_date': checkin_formatted,
            'nights': nights,
            'guests': guests,
            'sell_price': f"¥{sell_price:,.0f}" if sell_price > 0 else "",
            'sell_price_raw': sell_price,  # Keep raw number for totaling
            'status': status,
            'booking_source': booking_source,
            'is_active': is_active,
            'booking_type': booking_type,
            'extent': extent,  # This is crucial for Internal Requests filter
            'service_name': service_name,
            'amount_invoiced': f"¥{total_invoiced:,.0f}" if total_invoiced > 0 else "",
            'amount_received': f"¥{total_received:,.0f}" if total_received > 0 else "",
            'amount_invoiced_raw': total_invoiced,  # for calculations
            'amount_received_raw': total_received,  # for calculations
            'composite_key': f"{e_id}_{booking_id}",
            'raw_data': booking_data  # Store the original data for debugging
        }
    
    def _determine_booking_source(self, custom_id: str, booking_source: Any) -> str:
        """Determine booking source based on custom ID patterns"""
        
        if not custom_id:
            return "Book & Pay"
        
        custom_id = str(custom_id)
        booking_source_str = str(booking_source) if booking_source else ""
        
        # Check for OTAs based on custom_id patterns
        if custom_id:
            # Airbnb - look for 'H' prefix and RoomBoss Channel Manager
            if (custom_id[0] == 'H' and len(custom_id) == 10 and 
                "roomboss channel manager" in booking_source_str.lower()):
                return "Airbnb"
            
            # Booking.com
            elif len(custom_id) == 10 and custom_id[0] != 'H':
                return "Booking.com"
            
            # Expedia - multiple patterns
            elif ((len(custom_id) == 8 and custom_id[0] == '4') or
                (len(custom_id) == 9 and custom_id[0] == '3') or
                (len(custom_id) == 8 and custom_id[0] == '7') or
                (len(custom_id) == 9 and custom_id[0] == '2')):
                return "Expedia"
            
            # Jalan
            elif ((len(custom_id) == 8 and custom_id[0] == '0') or
                custom_id[:2] == '6X' or custom_id[:2] == '6J'):
                return "Jalan"
            
            # Staff bookings
            elif custom_id.lower() in ["d", "ryo", "as", "j", "jj", "ash", "t", "tom", "p", "li"]:
                return f"Staff ({custom_id})"
        
        return "Book & Pay"
    
    def _is_unpaid_book_and_pay(self, booking):
        """Check if this is an unpaid booking that needs attention (Book & Pay or Staff bookings)"""
        booking_source = booking.get('booking_source', '')
        
        # Check for Book & Pay or Staff bookings that are unpaid
        is_book_and_pay = booking_source == 'Book & Pay'
        is_staff_booking = booking_source.startswith('Staff (')
        
        return (
            (is_book_and_pay or is_staff_booking) and
            booking.get('is_active') == True and
            booking.get('amount_received_raw', 0) == 0 and
            booking.get('sell_price_raw', 0) > 0
        )
    
    def _filter_created_last_24_hours(self, parsed_bookings):
        """Filter bookings to only show those created in the last 24 hours"""
        # Get current time in JST
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        cutoff_time_jst = now_jst - datetime.timedelta(hours=24)
        filtered = []
        
        for booking in parsed_bookings:
            # Get the raw booking data - handle both nested and flat structures
            if 'booking' in booking['raw_data']:
                booking_info = booking['raw_data']['booking']
            else:
                booking_info = booking['raw_data']
                
            created_date = booking_info.get('createdDate', '')
            
            if created_date:
                try:
                    # Parse the creation date (API returns UTC like "2025-06-23T05:08:00.000+0000")
                    created_dt_utc = pd.to_datetime(created_date).tz_localize(None)
                    
                    # Convert UTC to JST (add 9 hours)
                    created_dt_jst = created_dt_utc + datetime.timedelta(hours=9)
                    
                    # Only include if created within last 24 hours in JST
                    if created_dt_jst >= cutoff_time_jst:
                        filtered.append(booking)
                            
                except Exception as e:
                    pass  # Skip bookings with invalid dates
        
        return filtered
    
    def _apply_content_filter(self, bookings, content_filter):
        """Apply content-based filtering to bookings"""
        if content_filter == "All":
            return bookings
        
        filtered = []
        
        for booking in bookings:
            include_booking = False
            
            if content_filter == "Unpaid":
                include_booking = self._is_unpaid_book_and_pay(booking)
            
            elif content_filter == "Book & Pay":
                include_booking = booking.get('booking_source') == 'Book & Pay'
            
            elif content_filter == "Staff":
                include_booking = booking.get('booking_source', '').startswith('Staff (')
            
            elif content_filter == "Airbnb":
                include_booking = booking.get('booking_source') == 'Airbnb'
            
            elif content_filter == "Booking.com":
                include_booking = booking.get('booking_source') == 'Booking.com'
            
            elif content_filter == "Expedia":
                include_booking = booking.get('booking_source') == 'Expedia'
            
            elif content_filter == "Jalan":
                include_booking = booking.get('booking_source') == 'Jalan'
            
            elif content_filter == "Internal Requests":
                extent = booking.get('extent', '')
                include_booking = extent == 'REQUEST_INTERNAL'
            
            if include_booking:
                filtered.append(booking)
        
        return filtered
    
    def _filter_created_today(self, parsed_bookings):
        """Filter bookings to only show those created today (in JST timezone)"""
        # Use JST for "today" since that's your business timezone
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        today_jst = now_jst.date()
        filtered = []
        
        for booking in parsed_bookings:
            # Handle both nested and flat structures
            if 'booking' in booking['raw_data']:
                booking_info = booking['raw_data']['booking']
            else:
                booking_info = booking['raw_data']
                
            created_date = booking_info.get('createdDate', '')
            
            if created_date:
                try:
                    # Parse the creation date (API returns UTC)
                    created_dt = pd.to_datetime(created_date)
                    
                    # Convert to timezone-naive UTC first
                    if created_dt.tz is not None:
                        created_dt_utc = created_dt.tz_convert('UTC').tz_localize(None)
                    else:
                        created_dt_utc = created_dt
                    
                    # Convert to JST and get just the date
                    created_dt_jst = created_dt_utc + datetime.timedelta(hours=9)
                    created_date_jst = created_dt_jst.date()
                    
                    if created_date_jst == today_jst:
                        filtered.append(booking)
                except Exception as e:
                    pass  # Skip bookings with invalid dates
        
        return filtered
    
    def _filter_created_last_n_days(self, parsed_bookings, days):
        """Filter bookings to only show those created in the last N days (in JST timezone)"""
        # Use JST for date calculations since that's your business timezone
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        cutoff_date_jst = (now_jst - datetime.timedelta(days=days-1)).date()
        filtered = []
        
        for booking in parsed_bookings:
            # Handle both nested and flat structures
            if 'booking' in booking['raw_data']:
                booking_info = booking['raw_data']['booking']
            else:
                booking_info = booking['raw_data']
                
            created_date = booking_info.get('createdDate', '')
            
            if created_date:
                try:
                    # Parse the creation date (API returns UTC)
                    created_dt = pd.to_datetime(created_date)
                    
                    # Convert to timezone-naive UTC first
                    if created_dt.tz is not None:
                        created_dt_utc = created_dt.tz_convert('UTC').tz_localize(None)
                    else:
                        created_dt_utc = created_dt
                    
                    # Convert to JST and get just the date
                    created_dt_jst = created_dt_utc + datetime.timedelta(hours=9)
                    created_date_jst = created_dt_jst.date()
                    
                    if created_date_jst >= cutoff_date_jst:
                        filtered.append(booking)
                except Exception as e:
                    pass  # Skip bookings with invalid dates
            
        return filtered
    
    def _filter_created_custom_date_range(self, parsed_bookings, start_date, end_date):
        """Filter bookings to only show those created within a custom date range (in JST timezone)"""
        # Convert start and end dates to JST datetime objects
        start_dt_jst = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt_jst = datetime.datetime.combine(end_date, datetime.time.max)
        
        filtered = []
        
        for booking in parsed_bookings:
            # Handle both nested and flat structures
            if 'booking' in booking['raw_data']:
                booking_info = booking['raw_data']['booking']
            else:
                booking_info = booking['raw_data']
                
            created_date = booking_info.get('createdDate', '')
            
            if created_date:
                try:
                    # Parse the creation date (API returns UTC)
                    created_dt = pd.to_datetime(created_date)
                    
                    # Convert to timezone-naive UTC first
                    if created_dt.tz is not None:
                        created_dt_utc = created_dt.tz_convert('UTC').tz_localize(None)
                    else:
                        created_dt_utc = created_dt
                    
                    # Convert to JST
                    created_dt_jst = created_dt_utc + datetime.timedelta(hours=9)
                    
                    # Check if creation date falls within the custom range
                    if start_dt_jst <= created_dt_jst <= end_dt_jst:
                        filtered.append(booking)
                except Exception as e:
                    pass  # Skip bookings with invalid dates
            
        return filtered
    
    def display_recent_bookings_section(self, location="main"):
        """
        Display the recent bookings section with optimized loading
        """
        
        # Use container to isolate this component
        with st.container():
            # Split into two rows for better organization
            
            # Row 1: Title and main controls
            col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
            
            with col1:
                st.markdown("### Recent Bookings")
            
            with col2:
                filter_option = st.selectbox(
                    "Period:",
                    ["Last 24 hours", "2 days", "3 days", "5 days", "7 days", "Custom"],
                    index=0,
                    key=f"recent_filter_select_{location}",
                    label_visibility="collapsed"
                )
            
            with col3:
                # Enhanced filter dropdown with Internal Requests highlighted
                content_filter = st.selectbox(
                    "Filter:",
                    ["All", "Unpaid", "Book & Pay", "Staff", "Airbnb", "Booking.com", "Expedia", "Jalan", "🔧 Internal Requests"],
                    index=0,
                    key=f"content_filter_{location}",
                    label_visibility="collapsed"
                )
            
            with col4:
                view_mode = st.selectbox(
                    "View:",
                    ["Buttons", "Table"],
                    index=0,
                    key=f"view_mode_{location}",
                    label_visibility="collapsed"
                )
            
            # Row 2: Custom date range (only if Custom selected)
            if filter_option == "Custom":
                date_col1, date_col2, date_col3, date_col4 = st.columns([1, 1, 1, 2])
                with date_col1:
                    start_date = st.date_input(
                        "Start date",
                        value=datetime.date.today() - datetime.timedelta(days=7),
                        key=f"recent_start_date_{location}"
                    )
                with date_col2:
                    end_date = st.date_input(
                        "End date", 
                        value=datetime.date.today(),
                        key=f"recent_end_date_{location}"
                    )
                with date_col3:
                    force_refresh = st.button(
                        "🔄 Refresh",
                        key=f"force_refresh_{location}",
                        help="Force refresh data"
                    )
                with date_col4:
                    # Empty space for better layout
                    pass
            else:
                start_date = end_date = None
                force_refresh = False
            
            # Create filter key to detect changes (include content filter)
            current_filter_key = f'{filter_option}_{start_date}_{end_date}_{content_filter}'
            last_filter_key = st.session_state.get(f'last_filter_key_{location}', '')
            
            # Only fetch data if filter changed or forced refresh
            if current_filter_key != last_filter_key or force_refresh:
                st.session_state[f'last_filter_key_{location}'] = current_filter_key
                
                with st.spinner("Loading recent bookings..."):
                    if filter_option == "Last 24 hours":
                        # Keep using 2 days to ensure we don't miss recent bookings from yesterday
                        result = self.fetch_recent_bookings("last_n_days", custom_days=2, force_refresh=True)
                    elif filter_option == "2 days":
                        result = self.fetch_recent_bookings("last_n_days", custom_days=2, force_refresh=True)
                    elif filter_option == "3 days":
                        result = self.fetch_recent_bookings("last_n_days", custom_days=3, force_refresh=True)
                    elif filter_option == "5 days":
                        result = self.fetch_recent_bookings("last_n_days", custom_days=5, force_refresh=True)
                    elif filter_option == "7 days":
                        result = self.fetch_recent_bookings("last_n_days", custom_days=7, force_refresh=True)
                    elif filter_option == "Custom" and start_date and end_date:
                        result = self.fetch_recent_bookings(
                            "date_range",
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d'),
                            force_refresh=True
                        )
                    else:
                        result = {'bookings': [], 'success': False, 'error': 'Invalid selection'}
                    
                    # Show API call summary
                    with st.expander("🔍 API Call Summary", expanded=False):
                        st.markdown("**Recent Bookings API Calls Made:**")
                        
                        # Get today's date for URL examples
                        today_str = datetime.datetime.now().strftime('%Y%m%d')
                        base_url = "https://api.roomboss.com/extws/hotel/v1/listBookings"
                        
                        if filter_option == "Last 24 hours":
                            st.write("• `get_last_n_days_bookings(days=2, booking_type='ALL')`")
                            yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
                            st.code(f"GET {base_url}?date={yesterday_str}&bookingType=ALL")
                            st.code(f"GET {base_url}?date={today_str}&bookingType=ALL")
                        elif filter_option in ["2 days", "3 days", "5 days", "7 days"]:
                            days = int(filter_option.split()[0])
                            st.write(f"• `get_last_n_days_bookings(days={days}, booking_type='ALL')`")
                            for i in range(days):
                                date_str = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y%m%d')
                                st.code(f"GET {base_url}?date={date_str}&bookingType=ALL")
                        elif filter_option == "Custom":
                            st.write(f"• `get_recent_bookings_for_date_range('{start_date}' to '{end_date}', booking_type='ALL')`")
                            if start_date and end_date:
                                current_date = start_date
                                while current_date <= end_date:
                                    date_str = current_date.strftime('%Y%m%d')
                                    st.code(f"GET {base_url}?date={date_str}&bookingType=ALL")
                                    current_date += datetime.timedelta(days=1)
                                    if current_date > start_date + datetime.timedelta(days=2):  # Limit display
                                        st.write("... (additional dates)")
                                        break
                        
                        st.markdown("**Authentication:**")
                        st.write("• Method: HTTP Basic Auth")
                        st.write("• Headers: `Authorization: Basic <base64(api_id:api_key)>`")
                        
                        if result.get('success', True):
                            total_bookings = len(result.get('bookings', []))
                            st.success(f"✅ API returned {total_bookings} bookings total")
                        else:
                            st.error(f"❌ API Error: {result.get('error', 'Unknown')}")
                    
                    # ADDITIONAL TEST: Also call NON_ACCOMMODATION specifically
                    with st.expander("🔧 NON_ACCOMMODATION Test Call", expanded=False):
                        st.markdown("**Testing NON_ACCOMMODATION specifically for internal service bookings:**")
                        
                        try:
                            api_id = st.secrets["roomboss"]["api_id"]
                            api_key = st.secrets["roomboss"]["api_key"]
                            
                            from services.api_list_recent_bookings import call_recent_bookings_api
                            
                            today_str = datetime.datetime.now().strftime('%Y%m%d')
                            
                            st.code(f"GET {base_url}?date={today_str}&bookingType=NON_ACCOMMODATION")
                            
                            non_accom_response = call_recent_bookings_api(
                                date=today_str,
                                api_id=api_id,
                                api_key=api_key,
                                booking_type="NON_ACCOMMODATION"
                            )
                            
                            if non_accom_response.ok:
                                import json
                                non_accom_data = json.loads(non_accom_response.text)
                                non_accom_bookings = non_accom_data.get('bookings', [])
                                
                                st.success(f"✅ Found {len(non_accom_bookings)} NON_ACCOMMODATION bookings today")
                                
                                # Check for internal requests in nested structure
                                internal_requests = []
                                all_extents = set()
                                
                                for booking in non_accom_bookings:
                                    if 'booking' in booking:
                                        nested_booking = booking['booking']
                                        extent = nested_booking.get('extent')
                                        if extent:
                                            all_extents.add(extent)
                                        if extent == 'REQUEST_INTERNAL':
                                            internal_requests.append(booking)
                                
                                if internal_requests:
                                    st.success(f"🎯 Found {len(internal_requests)} REQUEST_INTERNAL bookings!")
                                    for i, booking in enumerate(internal_requests):
                                        nested = booking['booking']
                                        st.write(f"• Internal Request {i+1}: eId {nested.get('eId')}, Type: {nested.get('bookingType')}")
                                else:
                                    st.warning("❌ No REQUEST_INTERNAL found")
                                    if all_extents:
                                        st.info(f"📋 Found these extents instead: {', '.join(sorted(all_extents))}")
                                
                            else:
                                st.error(f"❌ API Error: {non_accom_response.status_code}")
                                
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    
                    if not result.get('success', True):
                        st.error(f"Error loading bookings: {result.get('error', 'Unknown error')}")
                        return
            
                # Row 3: Stats section (separate row for better readability)
                if st.session_state.recent_bookings_data:
                    parsed_bookings = self.get_parsed_bookings()
                    
                    # Filter bookings based on time selection FIRST
                    if filter_option == "Last 24 hours":
                        time_filtered_bookings = self._filter_created_last_24_hours(parsed_bookings)
                    elif filter_option == "2 days":
                        time_filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 2)
                    elif filter_option == "3 days":
                        time_filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 3)
                    elif filter_option == "5 days":
                        time_filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 5)
                    elif filter_option == "7 days":
                        time_filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 7)
                    elif filter_option == "Custom" and start_date and end_date:
                        time_filtered_bookings = self._filter_created_custom_date_range(parsed_bookings, start_date, end_date)
                    else:
                        time_filtered_bookings = parsed_bookings
                    
                    # Clean up the content filter label for processing
                    clean_content_filter = content_filter.replace("🔧 ", "").strip()
                    
                    # Apply content filtering SECOND
                    content_filtered_bookings = self._apply_content_filter(time_filtered_bookings, clean_content_filter)
                    
                    # Remove duplicates AFTER all filtering
                    seen_composite_keys = set()
                    unique_filtered_bookings = []
                    
                    for booking in content_filtered_bookings:
                        composite_key = booking.get('composite_key', '')
                        if not composite_key:
                            e_id = booking.get('e_id', '')
                            booking_id = booking.get('booking_id', '')
                            composite_key = f"{e_id}_{booking_id}"
                        
                        if composite_key and composite_key not in seen_composite_keys:
                            seen_composite_keys.add(composite_key)
                            unique_filtered_bookings.append(booking)
                        elif not composite_key:
                            unique_filtered_bookings.append(booking)
                    
                    # Store filtered bookings for display
                    st.session_state.filtered_bookings_data = unique_filtered_bookings
                    
                    total = len(unique_filtered_bookings)
                    active = len([b for b in unique_filtered_bookings if b['is_active']])
                    cancelled = total - active
                    
                    # Calculate totals and counts for ACTIVE bookings only
                    active_bookings = [b for b in unique_filtered_bookings if b['is_active']]
                    accom_bookings = [b for b in active_bookings if b['booking_type'] == 'ACCOMMODATION']
                    service_bookings = [b for b in active_bookings if b['booking_type'] == 'SERVICE']
                    
                    accom_total = sum([b['sell_price_raw'] for b in accom_bookings])
                    service_total = sum([b['sell_price_raw'] for b in service_bookings])
                    accom_count = len(accom_bookings)
                    service_count = len(service_bookings)
                    
                    # Count unpaid bookings
                    unpaid_bookings = [b for b in unique_filtered_bookings if self._is_unpaid_book_and_pay(b)]
                    unpaid_count = len(unpaid_bookings)
                    
                    # Special handling for Internal Requests display
                    if clean_content_filter == "Internal Requests":
                        internal_accom = [b for b in unique_filtered_bookings if b['booking_type'] == 'ACCOMMODATION']
                        internal_service = [b for b in unique_filtered_bookings if b['booking_type'] == 'SERVICE']
                        
                        st.markdown("---")
                        st.markdown("#### 🔧 Internal Requests Summary")
                        
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        
                        with metrics_col1:
                            st.metric("Total Internal", f"{total}", f"{active} Active, {cancelled} Cancelled")
                        
                        with metrics_col2:
                            st.metric("Accommodation", len(internal_accom), f"¥{sum([b['sell_price_raw'] for b in internal_accom]):,.0f}")
                        
                        with metrics_col3:
                            st.metric("Services", len(internal_service), f"¥{sum([b['sell_price_raw'] for b in internal_service]):,.0f}")
                    
                    else:
                        # Display regular stats in a cleaner format
                        st.markdown("---")
                        stats_col1, stats_col2, stats_col3 = st.columns(3)
                        
                        with stats_col1:
                            st.metric("Total Bookings", f"{total}", f"{active} Active, {cancelled} Cancelled")
                        
                        with stats_col2:
                            total_revenue = accom_total + service_total
                            st.metric("Revenue", f"¥{total_revenue:,.0f}", f"{accom_count} ACCOM + {service_count} SVC")
                        
                        with stats_col3:
                            if unpaid_count > 0:
                                st.metric("⚠️ Unpaid", unpaid_count, "Need attention", delta_color="inverse")
                            else:
                                st.metric("✅ Payments", "All paid", "")
                else:
                    st.info("No data available")
            
            # Display bookings based on view mode
            if view_mode == "Table":
                self.display_sortable_table(location)
            else:
                self.display_bookings_list(location)
    
    def display_bookings_list(self, location="main"):
        """Display the list of recent bookings as a DataFrame with clickable buttons"""
        
        # Use filtered bookings if available, otherwise use all bookings
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            parsed_bookings = st.session_state.filtered_bookings_data
        else:
            parsed_bookings = self.get_parsed_bookings()
        
        if not parsed_bookings:
            st.info("No bookings found for the selected criteria.")
            return
        
        # Remove duplicates based on combination of eId and booking_id
        seen_composite_keys = set()
        unique_bookings = []
        
        for booking in parsed_bookings:
            # Use the composite key we created
            composite_key = booking.get('composite_key', '')
            
            # Also create fallback composite key if not present
            if not composite_key:
                e_id = booking.get('e_id', '')
                booking_id = booking.get('booking_id', '')
                composite_key = f"{e_id}_{booking_id}"
            
            if composite_key and composite_key not in seen_composite_keys:
                seen_composite_keys.add(composite_key)
                unique_bookings.append(booking)
            elif not composite_key:  # Keep bookings without composite key but don't dedupe them
                unique_bookings.append(booking)
                
        parsed_bookings = unique_bookings
        
        # Sort by created date (newest first) - use raw booking data for more reliable sorting
        def get_created_date_for_sort(booking):
            try:
                if 'booking' in booking['raw_data']:
                    booking_info = booking['raw_data']['booking']
                else:
                    booking_info = booking['raw_data']
                return booking_info.get('createdDate', '')
            except:
                return ''
        
        parsed_bookings.sort(key=get_created_date_for_sort, reverse=True)
        
        # Show count info to help debug any missing rows
        total_count = len(parsed_bookings)
        active_count = len([b for b in parsed_bookings if b['is_active']])
        cancelled_count = total_count - active_count
        st.write(f"**Displaying {total_count} booking(s): {active_count} active, {cancelled_count} cancelled**")
        
        # If there are many bookings, offer to limit display for performance
        display_limit = None
        if total_count > 50:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.warning(f"Large number of bookings ({total_count}). Showing first 50 for performance.")
            with col2:
                if st.button("Show All", key=f"show_all_{location}"):
                    display_limit = total_count
                else:
                    display_limit = 50
        else:
            display_limit = total_count
        
        # Create DataFrame with button column - no extra spacing
        # Add CSS styling
        st.markdown("""
            <style>
            .booking-header {
                font-weight: bold;
                background-color: #f0f2f6;
                padding: 0.25rem;
                border-radius: 0.25rem;
                margin-bottom: 0.25rem;
            }
            .internal-booking {
                background-color: #e3f2fd;
                border-left: 3px solid #2196f3;
                padding: 0.25rem;
                margin: 0.1rem 0;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Create header row FIRST
        if parsed_bookings:
            header_cols = st.columns([1.2, 1.2, 1.2, 1, 1, 1, 1.2, 1, 1, 1, 1])
            headers = ["Load", "Source", "Guest Name", "Sell Price", "Invoiced", "Received", "Vendor", "Created", "Status", "Type", "Extent"]
            
            for i, (col, header) in enumerate(zip(header_cols, headers)):
                with col:
                    st.markdown(f"**{header}**")
        
        # Create a container for the booking list with buttons
        bookings_to_display = parsed_bookings[:display_limit] if display_limit else parsed_bookings
        
        for i, booking in enumerate(bookings_to_display):
            booking_id = booking.get('e_id', '') or booking.get('booking_id', '')
            
            # Check if this is an unpaid Book & Pay booking
            is_unpaid = self._is_unpaid_book_and_pay(booking)
            
            # Check if this is an internal request
            is_internal = booking.get('extent', '') == 'REQUEST_INTERNAL'
            
            # Create columns for each booking row - updated to include invoice columns
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = st.columns([1.2, 1.2, 1.2, 1, 1, 1, 1.2, 1, 1, 1, 1])
            
            # Add visual highlighting for internal bookings
            if is_internal:
                for col in [col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11]:
                    with col:
                        st.markdown('<div class="internal-booking">', unsafe_allow_html=True)
            
            with col1:
                # Load button with special styling for internal bookings
                if booking_id and booking_id != 'unknown':
                    button_label = f"#{booking_id}"
                    if is_internal:
                        button_label = f"🔧 #{booking_id}"
                    
                    if st.button(
                        button_label,
                        key=f"load_{booking_id}_{location}_{i}",
                        help="Click to load this booking",
                        use_container_width=True
                    ):
                        st.session_state.last_search = booking_id
                        st.session_state.using_recent = True
                        st.rerun()
                else:
                    st.write(f"#{booking_id}")
            
            with col2:
                # Just show the source without warning icon
                source = booking.get('booking_source', '')
                st.write(source)
            
            with col3:
                st.write(booking.get('guest_name', ''))
            
            with col4:
                st.write(booking.get('sell_price', ''))

            with col5:
                st.write(booking.get('amount_invoiced', ''))

            with col6:
                # Highlight unpaid amounts
                received = booking.get('amount_received', '')
                if is_unpaid:
                    st.write(f"**{received}** ⚠️" if received else "**¥0** ⚠️")
                else:
                    st.write(received)
            
            with col7:
                st.write(booking.get('vendor', ''))
            
            with col8:
                st.write(booking.get('created_date', ''))
            
            with col9:
                status = booking.get('status', '')
                if status == 'Active':
                    st.write(f":green[{status}]")
                else:
                    st.write(f":red[{status}]")
            
            with col10:
                booking_type = booking.get('booking_type', '')
                if booking_type == 'ACCOMMODATION':
                    st.write("ACCOM")
                elif booking_type == 'SERVICE':
                    st.write("SVC")
                else:
                    st.write(booking_type)
            
            with col11:
                extent = booking.get('extent', '')
                # Add color coding for extent
                if extent == 'RESERVATION':
                    st.write(f":green[{extent}]")
                elif extent == 'REQUEST':
                    st.write(f":orange[{extent}]")
                elif extent == 'REQUEST_INTERNAL':
                    st.write(f":blue[🔧 {extent}]")
                else:
                    st.write(extent)
            
            # Close the internal booking div
            if is_internal:
                for col in [col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11]:
                    with col:
                        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_sortable_table(self, location="main"):
        """Display bookings as a sortable dataframe"""
        
        # Use filtered bookings if available, otherwise use all bookings
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            parsed_bookings = st.session_state.filtered_bookings_data
        else:
            parsed_bookings = self.get_parsed_bookings()
        
        if not parsed_bookings:
            st.info("No bookings found for the selected criteria.")
            return
        
        # Remove duplicates based on composite key
        seen_composite_keys = set()
        unique_bookings = []
        
        for booking in parsed_bookings:
            composite_key = booking.get('composite_key', '')
            if not composite_key:
                e_id = booking.get('e_id', '')
                booking_id = booking.get('booking_id', '')
                composite_key = f"{e_id}_{booking_id}"
            
            if composite_key and composite_key not in seen_composite_keys:
                seen_composite_keys.add(composite_key)
                unique_bookings.append(booking)
            elif not composite_key:
                unique_bookings.append(booking)
        
        # Create DataFrame
        df = pd.DataFrame(unique_bookings)
        
        # Select and rename columns for display
        display_columns = {
            'e_id': 'eID',
            'booking_source': 'Source',
            'guest_name': 'Guest Name',
            'sell_price': 'Sell Price',
            'amount_invoiced': 'Invoiced',
            'amount_received': 'Received',
            'vendor': 'Vendor',
            'created_date': 'Created',
            'status': 'Status',
            'booking_type': 'Type',
            'extent': 'Extent'
        }
        
        df_display = df[list(display_columns.keys())].rename(columns=display_columns)
        
        # Add visual indicators for internal requests
        def format_extent(extent):
            if extent == 'REQUEST_INTERNAL':
                return f"🔧 {extent}"
            return extent
        
        df_display['Extent'] = df_display['Extent'].apply(format_extent)
        
        # Show count
        total_count = len(df_display)
        active_count = len(df[df['is_active'] == True])
        cancelled_count = total_count - active_count
        st.write(f"**Displaying {total_count} booking(s): {active_count} active, {cancelled_count} cancelled**")
        
        # Make the table interactive with sorting
        selected_indices = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=600,  # Set fixed height in pixels
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle row selection - load the booking
        if selected_indices and hasattr(selected_indices, 'selection') and selected_indices.selection.rows:
            selected_idx = selected_indices.selection.rows[0]
            selected_booking = unique_bookings[selected_idx]
            
            # Load the selected booking
            booking_id = selected_booking['e_id'] or selected_booking['booking_id']
            st.session_state.last_search = booking_id
            st.session_state.using_recent = True
            st.rerun()

    def display_booking_summary_table(self):
        """Display bookings in a table format (alternative view)"""
        
        parsed_bookings = self.get_parsed_bookings()
        
        if not parsed_bookings:
            st.info("No recent bookings found.")
            return
        
        df = pd.DataFrame(parsed_bookings)
        
        # Select and rename columns for display
        display_columns = {
            'e_id': 'eID',
            'booking_id': 'Booking ID',
            'vendor': 'Property', 
            'guest_name': 'Guest',
            'amount_invoiced': 'Invoiced',
            'amount_received': 'Received',
            'checkin_date': 'Check-in',
            'nights': 'Nights',
            'guests': 'Guests',
            'booking_source': 'Source',
            'status': 'Status',
            'created_date': 'Created'
        }
        
        df_display = df[list(display_columns.keys())].rename(columns=display_columns)
        
        # Make the table interactive
        selected_indices = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle row selection
        if selected_indices and hasattr(selected_indices, 'selection') and selected_indices.selection.rows:
            selected_idx = selected_indices.selection.rows[0]
            selected_booking = parsed_bookings[selected_idx]
            
            # Load the selected booking
            st.session_state.last_search = selected_booking['e_id']
            st.session_state.using_recent = True
            st.rerun()
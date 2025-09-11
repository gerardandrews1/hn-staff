# -*- coding: utf-8 -*-
# ui/recent_bookings.py - Consolidated version with simplified filters

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
            
        # Default preset is "Today"
        if "current_preset_main" not in st.session_state:
            st.session_state.current_preset_main = {
                "period_type": "days",
                "period_value": 1,
                "content": "All",
                "property_type": "🏠 Accommodation",
                "season": "❄️ Winter",
                "view": "Buttons"
            }
            st.session_state.current_preset_name_main = "Today"
            
        if "recent_bookings_initialized" not in st.session_state:
            st.session_state.recent_bookings_initialized = False
            
        if "recent_bookings_parsed_cache" not in st.session_state:
            st.session_state.recent_bookings_parsed_cache = {}
            
        if "recent_bookings_last_filter_state" not in st.session_state:
            st.session_state.recent_bookings_last_filter_state = None

    def display_recent_bookings_section(self, location="main"):
        """Display the recent bookings section with simplified filters"""
        
        with st.container():
            # Title and Quick Filters Row
            col1, col2, col3 = st.columns([1.5, 3, 1])
            
            with col1:
                st.markdown("### Recent Bookings")
            
            with col2:
                # Quick time selector - UPDATED with new unpaid option
                time_filter = st.selectbox(
                    "Period:",
                    ["Today", "Last 2 Days", "Last 3 Days", "Last 7 Days", "Last 14 Days", 
                    "Last 21 Days", "Last 21 Days - Unpaid", "Month to Date", "Last Year MTD"],
                    index=0,
                    key=f"time_filter_{location}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if st.button("🔄 Refresh", key=f"refresh_{location}", help="Refresh data"):
                    st.session_state.recent_bookings_last_refresh = None
                    st.rerun()
            
            # Filter Controls Row
            filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1, 1.2, 1, 1, 1])
            
            with filter_col1:
                content_filter = st.selectbox(
                    "Content:",
                    ["All", "Unpaid", "Book & Pay", "Staff", "Direct", "OTA", 
                    "Airbnb", "Booking.com", "Expedia", "Jalan"],
                    index=0,
                    key=f"content_filter_{location}"
                )
                            
            with filter_col2:
                property_filter = st.selectbox(
                    "Property:",
                    ["🏠 Accommodation", "🏠 HN Managed", "🏢 Non-Managed", "🎿 Services", "All"],
                    index=0,
                    key=f"property_filter_{location}"
                )
            
            with filter_col3:
                season_filter = st.selectbox(
                    "Season:",
                    ["❄️ Winter", "☀️ Summer", "All Seasons"],
                    index=0,
                    key=f"season_filter_{location}"
                )
            
            with filter_col4:
                view_mode = st.selectbox(
                    "View:",
                    ["Buttons", "Table"],
                    index=0,
                    key=f"view_mode_{location}"
                )
            
            with filter_col5:
                use_custom = st.checkbox("Custom Dates", key=f"use_custom_{location}")
            
            # Custom date range (only if enabled)
            if use_custom:
                date_col1, date_col2 = st.columns([1, 1])
                with date_col1:
                    start_date = st.date_input(
                        "Start",
                        value=datetime.date.today() - datetime.timedelta(days=7),
                        key=f"start_date_{location}"
                    )
                with date_col2:
                    end_date = st.date_input(
                        "End", 
                        value=datetime.date.today(),
                        key=f"end_date_{location}"
                    )
                time_filter = "Custom"
            else:
                start_date = end_date = None
            
            # Show current period info - UPDATED to handle new unpaid option
            info_text = f"**Showing:** {time_filter}"
            
            if time_filter == "Month to Date":
                today = datetime.date.today()
                month_start = today.replace(day=1)
                info_text += f" ({month_start} to {today})"
            elif time_filter == "Last Year MTD":
                import calendar
                today = datetime.date.today()
                last_year = today.year - 1
                current_month = today.month
                month_start = datetime.date(last_year, current_month, 1)
                try:
                    month_end = datetime.date(last_year, current_month, today.day)
                except ValueError:
                    last_day = calendar.monthrange(last_year, current_month)[1]
                    month_end = datetime.date(last_year, current_month, last_day)
                info_text += f" ({month_start} to {month_end})"
            elif time_filter == "Last 21 Days - Unpaid":
                start_date_21 = datetime.date.today() - datetime.timedelta(days=20)
                info_text += f" ({start_date_21} to {datetime.date.today()}) - Unpaid Only"
            elif time_filter == "Custom" and start_date and end_date:
                info_text += f" ({start_date} to {end_date})"
            
            st.info(info_text)
            
            # Fetch data based on time filter - UPDATED to handle new unpaid option
            try:
                with st.spinner("Loading recent bookings..."):
                    api_id = st.secrets["roomboss"]["api_id"]
                    api_key = st.secrets["roomboss"]["api_key"]
                    
                    if time_filter == "Today":
                        result = get_last_n_days_bookings(1, api_id, api_key)
                    elif time_filter == "Last 2 Days":
                        result = get_last_n_days_bookings(2, api_id, api_key)
                    elif time_filter == "Last 3 Days":
                        result = get_last_n_days_bookings(3, api_id, api_key)
                    elif time_filter == "Last 7 Days":
                        result = get_last_n_days_bookings(7, api_id, api_key)
                    elif time_filter == "Last 14 Days":
                        result = get_last_n_days_bookings(14, api_id, api_key)
                    elif time_filter == "Last 21 Days":
                        result = get_last_n_days_bookings(21, api_id, api_key)
                    elif time_filter == "Last 21 Days - Unpaid":
                        # Get 21 days of data
                        result = get_last_n_days_bookings(21, api_id, api_key)
                        # Override content filter to "Unpaid" for this special case
                        content_filter = "Unpaid"
                    elif time_filter == "Month to Date":
                        today = datetime.date.today()
                        month_start = today.replace(day=1)
                        days = (today - month_start).days + 1
                        result = get_last_n_days_bookings(days, api_id, api_key)
                    elif time_filter == "Last Year MTD":
                        import calendar
                        today = datetime.date.today()
                        last_year = today.year - 1
                        current_month = today.month
                        month_start = datetime.date(last_year, current_month, 1)
                        try:
                            month_end = datetime.date(last_year, current_month, today.day)
                        except ValueError:
                            last_day = calendar.monthrange(last_year, current_month)[1]
                            month_end = datetime.date(last_year, current_month, last_day)
                        
                        result = get_recent_bookings_for_date_range(
                            month_start.strftime('%Y-%m-%d'),
                            month_end.strftime('%Y-%m-%d'),
                            api_id, api_key
                        )
                    elif time_filter == "Custom" and start_date and end_date:
                        result = get_recent_bookings_for_date_range(
                            start_date.strftime('%Y-%m-%d'),
                            end_date.strftime('%Y-%m-%d'),
                            api_id, api_key
                        )
                    else:
                        result = get_last_n_days_bookings(3, api_id, api_key)
                    
                    if result.get('success'):
                        st.session_state.recent_bookings_data = result.get('bookings', [])
                        st.session_state.recent_bookings_last_refresh = datetime.datetime.now()
                        
                        # Parse and filter bookings
                        parsed_bookings = [self.parse_booking_summary(b) for b in st.session_state.recent_bookings_data]
                        
                        # Apply filters
                        filtered = self.apply_filters(
                            parsed_bookings, 
                            time_filter,
                            content_filter,
                            property_filter,
                            season_filter,
                            start_date,
                            end_date
                        )
                        
                        # Store for display
                        st.session_state.filtered_bookings_data = filtered
                        
                        # Show stats
                        self.display_stats(filtered, time_filter, start_date, end_date)
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
                        return
                        
            except Exception as e:
                st.error(f"Error loading bookings: {str(e)}")
                return
            
            # Display bookings
            if view_mode == "Table":
                self.display_sortable_table(location)
            else:
                self.display_bookings_list(location)


    def apply_filters(self, bookings, time_filter, content_filter, property_filter, season_filter, start_date=None, end_date=None):
        """Apply all filters to bookings"""
        filtered = bookings.copy()
        
        # Time filtering - UPDATED to handle new unpaid option
        if time_filter == "Today":
            filtered = self._filter_created_last_n_days(filtered, 1)
        elif time_filter == "Last 2 Days":
            filtered = self._filter_created_last_n_days(filtered, 2)
        elif time_filter == "Last 3 Days":
            filtered = self._filter_created_last_n_days(filtered, 3)
        elif time_filter == "Last 7 Days":
            filtered = self._filter_created_last_n_days(filtered, 7)
        elif time_filter == "Last 14 Days":
            filtered = self._filter_created_last_n_days(filtered, 14)
        elif time_filter == "Last 21 Days":
            filtered = self._filter_created_last_n_days(filtered, 21)
        elif time_filter == "Last 21 Days - Unpaid":
            # First filter by 21 days, then by unpaid status
            filtered = self._filter_created_last_n_days(filtered, 21)
            # The content_filter is already set to "Unpaid" in the main method
        elif time_filter == "Month to Date":
            filtered = self._filter_created_month_to_date(filtered)
        elif time_filter == "Last Year MTD":
            filtered = self._filter_created_last_year_month_to_date(filtered)
        elif time_filter == "Custom" and start_date and end_date:
            filtered = self._filter_created_custom_date_range(filtered, start_date, end_date)
        
        # Content filtering
        if content_filter != "All":
            filtered = self._apply_content_filter(filtered, content_filter)
        
        # Property filtering
        if property_filter != "All":
            filtered = self._apply_management_type_filter(filtered, property_filter)
        
        # Season filtering
        if season_filter != "All Seasons":
            filtered = self._apply_season_filter(filtered, season_filter)
        
        # Remove duplicates
        seen = set()
        unique = []
        for b in filtered:
            key = f"{b.get('e_id', '')}_{b.get('booking_id', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(b)
        
        return unique
    

    def sort_bookings_by_date(self, bookings):
        """Sort bookings by creation date - most recent first"""
        def get_sort_date(booking):
            # Try to get created date from raw data first
            raw_data = booking.get('raw_data', {})
            if 'booking' in raw_data:
                created_date = raw_data['booking'].get('createdDate', '')
            else:
                created_date = raw_data.get('createdDate', '')
            
            if created_date:
                try:
                    # Convert to datetime object for proper sorting
                    created_dt = pd.to_datetime(created_date).tz_localize(None)
                    # Convert to JST
                    created_jst = created_dt + datetime.timedelta(hours=9)
                    return created_jst
                except:
                    pass
            
            # Fallback to check-in date if created date not available
            checkin_raw = booking.get('checkin_date_raw', '')
            if checkin_raw:
                try:
                    return pd.to_datetime(checkin_raw)
                except:
                    pass
            
            # Fallback to a very old date if no dates available
            return datetime.datetime(1900, 1, 1)
        
        # Sort by date descending (most recent first)
        return sorted(bookings, key=get_sort_date, reverse=True)


    def display_stats(self, bookings, time_filter, start_date=None, end_date=None):
        """Display booking statistics"""
        total = len(bookings)
        active = len([b for b in bookings if b.get('is_active', True)])
        cancelled = total - active
        
        active_bookings = [b for b in bookings if b.get('is_active', True)]
        accom = [b for b in active_bookings if b.get('booking_type') == 'ACCOMMODATION']
        services = [b for b in active_bookings if b.get('booking_type') == 'SERVICE']
        
        accom_revenue = sum([b.get('sell_price_raw', 0) for b in accom])
        service_revenue = sum([b.get('sell_price_raw', 0) for b in services])
        
        unpaid = len([b for b in bookings if self._is_unpaid_book_and_pay(b)])
        
        # Calculate days - UPDATED to handle new unpaid option
        if time_filter == "Today":
            days = 1
        elif time_filter == "Last 2 Days":
            days = 2
        elif time_filter == "Last 3 Days":
            days = 3
        elif time_filter == "Last 7 Days":
            days = 7
        elif time_filter == "Last 14 Days":
            days = 14
        elif time_filter == "Last 21 Days" or time_filter == "Last 21 Days - Unpaid":
            days = 21
        elif time_filter == "Month to Date":
            today = datetime.date.today()
            days = (today - today.replace(day=1)).days + 1
        elif time_filter == "Custom" and start_date and end_date:
            days = (end_date - start_date).days + 1
        else:
            days = 1
        
        per_day = active / days if days > 0 else 0
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total", f"{total}", f"{active} Active, {cancelled} Cancelled")
        
        with col2:
            total_revenue = accom_revenue + service_revenue
            st.metric("Revenue", f"¥{total_revenue:,.0f}", f"{len(accom)} Accom + {len(services)} Svc")
        
        with col3:
            if unpaid > 0:
                st.metric("⚠️ Unpaid", unpaid, "Need attention", delta_color="inverse")
            else:
                st.metric("✅ Payments", "All paid", "")
        
        with col4:
            st.metric("Per Day", f"{per_day:.1f}", f"Over {days} days")

    # Add this to your ui/recent_bookings.py file

    def get_country_from_phone(self, phone_number):
        """Extract country from phone number using country codes"""
        if not phone_number:
            return None
        
        # Clean phone number - remove spaces, dashes, parentheses
        clean_phone = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Remove leading + if present in original
        if str(phone_number).startswith('+'):
            clean_phone = clean_phone
        else:
            # If no +, might need to add logic for local vs international format
            pass
        
        # Common country codes mapping (add more as needed)
        country_codes = {
            # Major countries for your business
            '81': 'Japan',
            '1': 'United States',  # Also Canada, but US is more common
            '44': 'United Kingdom', 
            '61': 'Australia',
            '33': 'France',
            '49': 'Germany',
            '39': 'Italy',
            '34': 'Spain',
            '82': 'South Korea',
            '86': 'China',
            '852': 'Hong Kong',
            '65': 'Singapore',
            '66': 'Thailand',
            '60': 'Malaysia',
            '62': 'Indonesia',
            '63': 'Philippines',
            '84': 'Vietnam',
            '91': 'India',
            '7': 'Russia',
            '55': 'Brazil',
            '52': 'Mexico',
            '54': 'Argentina',
            '56': 'Chile',
            '64': 'New Zealand',
            '27': 'South Africa',
            '20': 'Egypt',
            '971': 'UAE',
            '966': 'Saudi Arabia',
            '972': 'Israel',
            '90': 'Turkey',
            '30': 'Greece',
            '31': 'Netherlands',
            '32': 'Belgium',
            '41': 'Switzerland',
            '43': 'Austria',
            '45': 'Denmark',
            '46': 'Sweden',
            '47': 'Norway',
            '48': 'Poland',
            '420': 'Czech Republic',
            '36': 'Hungary',
            '351': 'Portugal',
            '358': 'Finland',
            '372': 'Estonia',
            '371': 'Latvia',
            '370': 'Lithuania',
            '380': 'Ukraine',
            '374': 'Armenia',
            '995': 'Georgia',
            '994': 'Azerbaijan',
            '992': 'Tajikistan',
            '998': 'Uzbekistan',
            '996': 'Kyrgyzstan',
            '993': 'Turkmenistan',
            '7': 'Kazakhstan',  # Note: Kazakhstan also uses +7
        }
        
        # Try different length country codes (1-4 digits)
        for length in [4, 3, 2, 1]:
            if len(clean_phone) >= length:
                code = clean_phone[:length]
                if code in country_codes:
                    return country_codes[code]
        
        return None

    def parse_booking_summary(self, booking_data):
        """Parse booking data - enhanced with phone-based country detection"""
        # Handle nested structure
        if 'booking' in booking_data:
            booking = booking_data.get('booking', {})
            invoice_payments = booking_data.get('invoicePayments', [])
            lead_guest = booking_data.get('leadGuest', {}) or booking.get('leadGuest', {})
        else:
            booking = booking_data
            invoice_payments = booking_data.get('invoicePayments', [])
            lead_guest = booking_data.get('leadGuest', {})
        
        # Basic info
        booking_id = booking.get('bookingId', '')
        e_id = booking.get('eId', '')
        
        # Guest info with enhanced country detection
        guest_name = f"{lead_guest.get('givenName', '')} {lead_guest.get('familyName', '')}".strip()
        
        # Primary: Try to get country from nationality
        country = lead_guest.get('nationality', '')
        
        # Fallback: If no nationality, try phone number
        if not country or country in ['UNKNOWN', 'N/A', '']:
            phone_number = lead_guest.get('phoneNumber', '') or lead_guest.get('phone', '')
            if phone_number:
                phone_country = self.get_country_from_phone(phone_number)
                if phone_country:
                    country = phone_country
                    # Optional: Log this for debugging
                    # print(f"Derived country {phone_country} from phone {phone_number} for booking {e_id}")
        
        # Vendor info
        vendor = ""
        booking_type = booking.get('bookingType', '')
        if booking_type == 'ACCOMMODATION':
            hotel_info = booking.get('hotel', {})
            vendor = hotel_info.get('hotelName', '')
        elif booking_type == 'SERVICE':
            provider = booking.get('serviceProvider', {})
            vendor = provider.get('serviceProviderName', '')
        
        # Dates and pricing
        items = booking.get('items', [])
        checkin_date = ""
        checkout_date = ""
        nights = 0
        sell_price = 0
        
        if items:
            first_item = items[0]
            sell_price = sum([item.get('priceSell', 0) for item in items])
            
            if booking_type == 'ACCOMMODATION':
                checkin_date = first_item.get('checkIn', '')
                checkout_date = first_item.get('checkOut', '')
                if checkin_date and checkout_date:
                    try:
                        checkin_dt = pd.to_datetime(checkin_date)
                        checkout_dt = pd.to_datetime(checkout_date)
                        nights = (checkout_dt - checkin_dt).days
                        checkin_date = checkin_dt.strftime("%d %b %Y")
                        checkout_date = checkout_dt.strftime("%d %b %Y")
                    except:
                        pass
        
        # Payment info
        total_invoiced = sum([p.get('invoiceAmount', 0) for p in invoice_payments])
        total_received = sum([p.get('paymentAmount', 0) for p in invoice_payments])
        
        # Status
        is_active = booking.get('active', True)
        status = "Active" if is_active else "Cancelled"
        
        # Source
        custom_id = booking.get('customId', '')
        booking_source = self._determine_booking_source(custom_id, booking.get('bookingSource', ''))
        
        # Created date
        created_date = booking.get('createdDate', '')
        if created_date:
            try:
                created_dt = pd.to_datetime(created_date) + pd.offsets.Hour(9)
                created_date = created_dt.strftime("%d %b %H:%M")
            except:
                pass
        
        return {
            'booking_id': booking_id,
            'e_id': str(e_id),
            'vendor': vendor,
            'guest_name': guest_name,
            'created_date': created_date,
            'checkin_date': checkin_date,
            'checkin_date_raw': first_item.get('checkIn', '') if items else '',
            'checkout_date_raw': first_item.get('checkOut', '') if items else '',
            'nights': nights,
            'country': country if country and country not in ['UNKNOWN', 'N/A'] else '',
            'phone_number': lead_guest.get('guest_phone', '') or lead_guest.get('phoneNumber', '') or lead_guest.get('phone', ''),  # Store for debugging
            'sell_price': f"¥{sell_price:,.0f}" if sell_price > 0 else "",
            'sell_price_raw': sell_price,
            'price_per_night': f"¥{sell_price/nights:,.0f}" if nights > 0 else "",
            'status': status,
            'booking_source': booking_source,
            'is_active': is_active,
            'booking_type': booking_type,
            'extent': booking.get('extent', ''),
            'amount_invoiced': f"¥{total_invoiced:,.0f}" if total_invoiced > 0 else "",
            'amount_received': f"¥{total_received:,.0f}" if total_received > 0 else "",
            'amount_invoiced_raw': total_invoiced,
            'amount_received_raw': total_received,
            'is_hn_managed': self._is_holiday_niseko_managed(booking_data),
            'raw_data': booking_data
        }


    def _determine_booking_source(self, custom_id, booking_source):
        """Determine booking source from custom ID"""
        if not custom_id:
            return "Book & Pay"
        
        custom_id = str(custom_id)
        booking_source_str = str(booking_source).lower() if booking_source else ""
        
        # Airbnb
        if custom_id[0] == 'H' and len(custom_id) == 10 and "roomboss channel manager" in booking_source_str:
            return "Airbnb"
        # Booking.com
        elif (len(custom_id) == 10 and custom_id[0] != 'H') or "booking.com" in booking_source_str:
            return "Booking.com"
        # Expedia patterns
        elif len(custom_id) in [8, 9] and custom_id[0] in ['2', '3', '4', '7']:
            return "Expedia"
        # Jalan
        elif (len(custom_id) == 8 and custom_id[0] == '0') or custom_id[:2] in ['6X', '6J']:
            return "Jalan"
        # Staff
        elif custom_id.lower() in ["d", "ryo", "as", "j", "jj", "ash", "t", "tom", "p", "li"]:
            return f"Staff ({custom_id})"
        
        return "Book & Pay"

    def _is_unpaid_book_and_pay(self, booking):
        """Check if booking is unpaid"""
        source = booking.get('booking_source', '')
        is_direct = source == 'Book & Pay' or source.startswith('Staff (')
        
        return (is_direct and 
                booking.get('is_active', True) and 
                booking.get('amount_received_raw', 0) == 0 and 
                booking.get('sell_price_raw', 0) > 0)

    def _is_holiday_niseko_managed(self, booking_data):
        """Check if property is HN managed"""
        # Simplified check - you can expand this based on your property list
        if 'booking' in booking_data:
            booking = booking_data.get('booking', {})
        else:
            booking = booking_data
        
        hotel_name = booking.get('hotel', {}).get('hotelName', '').lower()
        
        # Add your managed property names here
        managed_properties = [
            'the maples niseko',
            'one niseko',
            'yukimi',
            # Add more as needed
        ]
        
        return any(prop in hotel_name for prop in managed_properties)

    def _filter_created_last_n_days(self, bookings, days):
        """Filter bookings created in last N days"""
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        cutoff = (now_jst - datetime.timedelta(days=days-1)).date()
        
        filtered = []
        for booking in bookings:
            raw_data = booking.get('raw_data', {})
            if 'booking' in raw_data:
                created_date = raw_data['booking'].get('createdDate', '')
            else:
                created_date = raw_data.get('createdDate', '')
            
            if created_date:
                try:
                    created_dt = pd.to_datetime(created_date).tz_localize(None)
                    created_jst = (created_dt + datetime.timedelta(hours=9)).date()
                    if created_jst >= cutoff:
                        filtered.append(booking)
                except:
                    pass
        
        return filtered

    def _filter_created_month_to_date(self, bookings):
        """Filter bookings created month to date"""
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        month_start = now_jst.replace(day=1, hour=0, minute=0, second=0)
        
        filtered = []
        for booking in bookings:
            raw_data = booking.get('raw_data', {})
            if 'booking' in raw_data:
                created_date = raw_data['booking'].get('createdDate', '')
            else:
                created_date = raw_data.get('createdDate', '')
            
            if created_date:
                try:
                    created_dt = pd.to_datetime(created_date).tz_localize(None)
                    created_jst = created_dt + datetime.timedelta(hours=9)
                    if created_jst >= month_start:
                        filtered.append(booking)
                except:
                    pass
        
        return filtered

    def _filter_created_last_year_month_to_date(self, bookings):
        """Filter bookings for last year's month to date"""
        import calendar
        today = datetime.date.today()
        last_year = today.year - 1
        
        month_start = datetime.datetime(last_year, today.month, 1)
        try:
            month_end = datetime.datetime(last_year, today.month, today.day, 23, 59, 59)
        except ValueError:
            last_day = calendar.monthrange(last_year, today.month)[1]
            month_end = datetime.datetime(last_year, today.month, last_day, 23, 59, 59)
        
        filtered = []
        for booking in bookings:
            raw_data = booking.get('raw_data', {})
            if 'booking' in raw_data:
                created_date = raw_data['booking'].get('createdDate', '')
            else:
                created_date = raw_data.get('createdDate', '')
            
            if created_date:
                try:
                    created_dt = pd.to_datetime(created_date).tz_localize(None)
                    created_jst = created_dt + datetime.timedelta(hours=9)
                    if month_start <= created_jst <= month_end:
                        filtered.append(booking)
                except:
                    pass
        
        return filtered

    def _filter_created_custom_date_range(self, bookings, start_date, end_date):
        """Filter bookings in custom date range"""
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max)
        
        filtered = []
        for booking in bookings:
            raw_data = booking.get('raw_data', {})
            if 'booking' in raw_data:
                created_date = raw_data['booking'].get('createdDate', '')
            else:
                created_date = raw_data.get('createdDate', '')
            
            if created_date:
                try:
                    created_dt = pd.to_datetime(created_date).tz_localize(None)
                    created_jst = created_dt + datetime.timedelta(hours=9)
                    if start_dt <= created_jst <= end_dt:
                        filtered.append(booking)
                except:
                    pass
        
        return filtered

    def _apply_content_filter(self, bookings, content_filter):
        """Apply content filtering"""
        if content_filter == "All":
            return bookings
        
        filtered = []
        for booking in bookings:
            source = booking.get('booking_source', '')
            
            if content_filter == "Unpaid" and self._is_unpaid_book_and_pay(booking):
                filtered.append(booking)
            elif content_filter == "Book & Pay" and source == "Book & Pay":
                filtered.append(booking)
            elif content_filter == "Staff" and source.startswith("Staff ("):
                filtered.append(booking)
            elif content_filter == "Direct" and (source == "Book & Pay" or source.startswith("Staff (")):
                filtered.append(booking)
            elif content_filter == "OTA" and source in ["Airbnb", "Booking.com", "Expedia", "Jalan"]:
                filtered.append(booking)
            elif content_filter == source:  # Direct match for specific OTAs
                filtered.append(booking)
        
        return filtered

    def _apply_management_type_filter(self, bookings, property_filter):
        """Apply property type filtering"""
        if property_filter == "All":
            return bookings
        
        filtered = []
        for booking in bookings:
            booking_type = booking.get('booking_type', '')
            is_managed = booking.get('is_hn_managed', False)
            
            if property_filter == "🏠 Accommodation" and booking_type == 'ACCOMMODATION':
                filtered.append(booking)
            elif property_filter == "🏠 HN Managed" and booking_type == 'ACCOMMODATION' and is_managed:
                filtered.append(booking)
            elif property_filter == "🏢 Non-Managed" and booking_type == 'ACCOMMODATION' and not is_managed:
                filtered.append(booking)
            elif property_filter == "🎿 Services" and booking_type == 'SERVICE':
                filtered.append(booking)
        
        return filtered

    def _apply_season_filter(self, bookings, season_filter):
        """Apply season filtering"""
        if season_filter == "All Seasons":
            return bookings
        
        filtered = []
        for booking in bookings:
            checkin_raw = booking.get('checkin_date_raw', '')
            
            if checkin_raw:
                try:
                    checkin_dt = pd.to_datetime(checkin_raw)
                    month = checkin_dt.month
                    day = checkin_dt.day
                    
                    # Winter: Nov 20 - Apr 30
                    is_winter = ((month == 11 and day >= 20) or 
                                month in [12, 1, 2, 3] or 
                                (month == 4 and day <= 30))
                    
                    if (season_filter == "❄️ Winter" and is_winter) or \
                       (season_filter == "☀️ Summer" and not is_winter):
                        filtered.append(booking)
                except:
                    pass
        
        return filtered

    def display_bookings_list(self, location="main"):
        """Display bookings as buttons"""
        bookings = st.session_state.get('filtered_bookings_data', [])
        
        if not bookings:
            st.info("No bookings found for the selected criteria.")
            return
        
        st.write(f"**Displaying {len(bookings)} booking(s)**")
        
        # Headers
        cols = st.columns([0.8, 0.9, 1.1, 1.1, 1.1, 1, 1, 1, 1, 0.8, 0.6, 0.8, 1, 1])
        headers = ["eID", "Created", "Source", "Guest", "Vendor", "Price", "Per Night", 
                  "Invoiced", "Received", "Check-in", "Nights", "Country", "Status", "Extent"]
        
        for col, header in zip(cols, headers):
            with col:
                st.markdown(f"**{header}**")
        
        # Display each booking
        for booking in bookings[:50]:  # Limit for performance
            cols = st.columns([0.8, 0.9, 1.1, 1.1, 1.1, 1, 1, 1, 1, 0.8, 0.6, 0.8, 1, 1])
            
            e_id = booking.get('e_id', '')
            booking_id = booking.get('booking_id', '')
            
            with cols[0]:
                if booking_id:
                    roomboss_url = f"https://app.roomboss.com/ui/booking/edit.jsf?bid={booking_id}"
                    st.markdown(
                        f'<a href="{roomboss_url}" target="_blank" style="'
                        f'display: inline-block; padding: 6px 12px; margin: 2px 0; '
                        f'border: 1px solid #ccc; border-radius: 6px; background-color: white; '
                        f'color: #262730; text-decoration: none; font-size: 13px; '
                        f'font-weight: 500; width: 100%; text-align: center;">'
                        f'#{e_id}</a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.write(f"#{e_id}")
            
            with cols[1]:
                st.write(booking.get('created_date', ''))
            
            with cols[2]:
                st.write(booking.get('booking_source', ''))
            
            with cols[3]:
                st.write(booking.get('guest_name', ''))
            
            with cols[4]:
                st.write(booking.get('vendor', ''))
            
            with cols[5]:
                st.write(booking.get('sell_price', ''))
            
            with cols[6]:
                st.write(booking.get('price_per_night', ''))
            
            with cols[7]:
                st.write(booking.get('amount_invoiced', ''))
            
            with cols[8]:
                received = booking.get('amount_received', '')
                if self._is_unpaid_book_and_pay(booking):
                    st.write(f"**{received}** ⚠️" if received else "**¥0** ⚠️")
                else:
                    st.write(received)
            
            with cols[9]:
                st.write(booking.get('checkin_date', 'N/A'))
            
            with cols[10]:
                nights = booking.get('nights', 0)
                st.write(str(nights) if nights > 0 else "N/A")
            
            with cols[11]:
                st.write(booking.get('country', ''))
            
            with cols[12]:
                status = booking.get('status', '')
                if status == 'Active':
                    st.write(f":green[{status}]")
                else:
                    st.write(f":red[{status}]")
            
            with cols[13]:
                extent = booking.get('extent', '')
                if extent == 'RESERVATION':
                    st.write(":green[RES]")
                elif extent == 'REQUEST':
                    st.write(":orange[RQST]")
                elif extent == 'REQUEST_INTERNAL':
                    st.write(":blue[🔧 INT]")
                else:
                    st.write(extent)

    def display_sortable_table(self, location="main"):
        """Display bookings as a sortable table"""
        bookings = st.session_state.get('filtered_bookings_data', [])
        
        if not bookings:
            st.info("No bookings found for the selected criteria.")
            return
        
        # Create DataFrame
        df = pd.DataFrame(bookings)
        
        # Select columns to display
        display_columns = {
            'e_id': 'eID',
            'created_date': 'Created',
            'booking_source': 'Source',
            'guest_name': 'Guest Name',
            'vendor': 'Vendor',
            'sell_price': 'Sell Price',
            'price_per_night': 'Per Night',
            'amount_invoiced': 'Invoiced',
            'amount_received': 'Received',
            'checkin_date': 'Check-in',
            'nights': 'Nights',
            'country': 'Country',
            'status': 'Status',
            'extent': 'Extent'
        }
        
        # Only include existing columns
        available_cols = {col: name for col, name in display_columns.items() if col in df.columns}
        df_display = df[list(available_cols.keys())].rename(columns=available_cols)
        
        st.write(f"**Displaying {len(df_display)} booking(s)**")
        
        # Display the dataframe
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=600
        )
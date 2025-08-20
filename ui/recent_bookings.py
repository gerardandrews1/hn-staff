# -*- coding: utf-8 -*-
# ui/recent_bookings.py - Updated with Enhanced Fields and Reordered Columns (Type column removed)

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

    def calculate_booking_rate(self, bookings, filter_option, start_date=None, end_date=None):
        """
        Calculate booking rate based on active bookings and selected filter period
        
        Args:
            bookings: List of booking dictionaries
            filter_option: Selected time period filter
            start_date: Start date for custom range
            end_date: End date for custom range
        
        Returns:
            Float: Active bookings per day
        """
        # Only count active bookings
        active_bookings = [b for b in bookings if b.get('is_active', True)]
        active_count = len(active_bookings)
        
        if active_count == 0:
            return 0
        
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
        
        # Calculate active bookings per day
        return active_count / days_in_period if days_in_period > 0 else 0

    def apply_quick_filter_preset(self, preset_name, location):
        """Apply a preset combination of filters"""
        
        presets = {
            "Unpaid Accom - 2 weeks": {  # ✅ Fixed to match dropdown exactly
                "period": "14 days",  # ✅ Use existing option
                "content": "Unpaid", 
                "property_type": "🏠 Accommodation",
                "season": "❄️ Winter",  # ✅ With emoji
                "view": "Buttons"
            },
            "OTA Bookings (7 days)": {
                "period": "7 days",
                "content": "OTA",
                "property_type": "🏠 Accommodation",
                "season": "❄️ Winter",
                "view": "Buttons"
            },
            "Direct Bookings (7 days)": {
                "period": "7 days",
                "content": "Direct",
                "property_type": "🏠 Accommodation",
                "season": "❄️ Winter",
                "view": "Buttons"
            },
            "Month to Date": {
                "period": "Month to Date",
                "content": "All",
                "property_type": "🏠 Accommodation",
                "season": "❄️ Winter",
                "view": "Buttons"
            }
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            
            # Update session state with preset values
            period_options = ["Last 24 hours", "2 days", "3 days", "5 days", "7 days", "14 days", "Month to Date", "Custom"]
            content_options = ["All", "Unpaid", "Book & Pay", "Staff", "Direct", "OTA", "Airbnb", "Booking.com", "Expedia", "Jalan"]
            property_options = ["All", "🏠 Accommodation", "🏠 HN Managed", "🏢 Non-Managed", "🎿 Services"]
            season_options = ["All Seasons", "❄️ Winter", "☀️ Summer"]
            view_options = ["Buttons", "Table"]
            
            # Map preset values to indices and verify they exist
            try:
                period_index = period_options.index(preset["period"])
                content_index = content_options.index(preset["content"])
                property_index = property_options.index(preset["property_type"])
                season_index = season_options.index(preset["season"])
                view_index = view_options.index(preset["view"])
                
                # Debug output
                print(f"🔧 Applying preset: {preset_name}")
                print(f"   Period: {preset['period']} (found at index {period_index})")
                print(f"   Content: {preset['content']} (found at index {content_index})")
                print(f"   Property: {preset['property_type']} (found at index {property_index})")
                print(f"   Season: {preset['season']} (found at index {season_index})")
                print(f"   View: {preset['view']} (found at index {view_index})")
                
                # Force update session state
                st.session_state[f"recent_filter_select_{location}"] = preset["period"]
                st.session_state[f"content_filter_{location}"] = preset["content"]
                st.session_state[f"management_type_filter_{location}"] = preset["property_type"]
                st.session_state[f"season_filter_{location}"] = preset["season"]
                st.session_state[f"view_mode_{location}"] = preset["view"]
                
                # Clear the last filter key to force data refresh
                if f'last_filter_key_{location}' in st.session_state:
                    del st.session_state[f'last_filter_key_{location}']
                
                # Show success message (optional - can remove to reduce noise)
                # st.success(f"✅ Applied preset: {preset_name}")
                
                # DON'T call st.rerun() here - it causes infinite loop!
                # The session state changes will trigger the UI update automatically
                
            except ValueError as e:
                st.error(f"❌ Error applying preset '{preset_name}': {e}")
                st.error(f"Check that all preset values exist in dropdown options:")
                st.write(f"Available periods: {period_options}")
                st.write(f"Available content: {content_options}")
                st.write(f"Available properties: {property_options}")
                st.write(f"Available seasons: {season_options}")
                st.write(f"Available views: {view_options}")
        else:
            st.error(f"❌ Preset '{preset_name}' not found in configuration")

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
        ENHANCED: Now includes check-in date, nights, and country information
        
        Args:
            booking_data: Raw booking data from API 
            
        Returns:
            Dictionary with parsed booking summary including new fields
        """
        
        # Handle different API response structures
        # Some APIs return nested structure with 'booking' key, others return flat
        if 'booking' in booking_data:
            # Nested structure from recent bookings API
            booking = booking_data.get('booking', {})
            invoice_payments = booking_data.get('invoicePayments', [])
            # For nested structure, look for leadGuest in the parent or booking level
            lead_guest = booking_data.get('leadGuest', {}) or booking.get('leadGuest', {})
        else:
            # Flat structure - the booking_data IS the booking
            booking = booking_data
            # For flat structure, invoice payments might be at the same level or missing
            invoice_payments = booking_data.get('invoicePayments', [])
            lead_guest = booking_data.get('leadGuest', {})
        
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
        
        # Extract custom ID for source attribution FIRST (moved up)
        custom_id = booking.get('customId', '')
        booking_source_info = booking.get('bookingSource', '')
        booking_source = self._determine_booking_source(custom_id, booking_source_info)
        
        # Extract guest info from leadGuest
        guest_name = ""
        country = ""  # Changed from "N/A" to blank
        
        if lead_guest:
            given_name = lead_guest.get('givenName', '')
            family_name = lead_guest.get('familyName', '')
            guest_name = f"{given_name} {family_name}".strip()
            
            # NEW: Extract country information - handle "UNKNOWN" from API
            raw_nationality = lead_guest.get('nationality', '')
            country = ''
            
            if raw_nationality and raw_nationality != 'UNKNOWN':
                country = raw_nationality
            else:
                # Try other country fields
                country = (
                    lead_guest.get('country', '') or
                    lead_guest.get('countryCode', '') or
                    ''
                )
            
            # NEW: If no country found, try to get country from phone number
            if not country:
                # Try multiple possible locations for phone number
                phone_number = (
                    lead_guest.get('phoneNumber', '') or
                    lead_guest.get('phone', '') or
                    lead_guest.get('telephone', '') or
                    lead_guest.get('mobile', '') or
                    ''
                )
                
                if phone_number:
                    country = self._phone_to_country_code(phone_number)
        
        # Extract created date
        created_date = booking.get('createdDate', '')
        created_formatted = ""
        if created_date:
            try:
                created_dt = pd.to_datetime(created_date) + pd.offsets.Hour(9)  # JST
                created_formatted = created_dt.strftime("%d %b %H:%M")  # Format: 04 Jul 10:25
            except:
                created_formatted = created_date
        
        # NEW: Extract dates from items and calculate nights
        checkin_date = ""
        checkin_formatted = ""
        checkout_date = ""
        nights = 0
        guests = 0
        sell_price = 0
        
        items = booking.get('items', [])
        if items:
            # Calculate total sell price from all items - prioritize priceSell
            for item in items:
                price_sell = item.get('priceSell', 0)
                sell_price += price_sell
            
            first_item = items[0]
            
            # For accommodation bookings
            if booking_type == 'ACCOMMODATION':
                checkin_date = first_item.get('checkIn', '')
                checkout_date = first_item.get('checkOut', '')
                guests = first_item.get('numberGuests', 0)
                
                # NEW: Calculate nights from check-in and check-out dates
                if checkin_date and checkout_date:
                    try:
                        checkin_dt = pd.to_datetime(checkin_date)
                        checkout_dt = pd.to_datetime(checkout_date)
                        nights = (checkout_dt - checkin_dt).days
                        checkin_formatted = checkin_dt.strftime("%d %b %Y")  # Format: 01 Jan 2026
                    except:
                        checkin_formatted = checkin_date
                        nights = 0
            
            # For service bookings
            elif booking_type == 'SERVICE':
                start_date = first_item.get('startDate', '')
                end_date = first_item.get('endDate', '')
                
                if start_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        checkin_formatted = start_dt.strftime("%d %b %Y")  # Format: 01 Jan 2026
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
        
        # Create display vendor name
        if booking_type == 'SERVICE' and service_name:
            display_vendor = f"{vendor} - {service_name}"
        else:
            display_vendor = vendor
        
        # Get extent information
        extent = booking.get('extent', '')
        
        # NEW: Determine if this is a Holiday Niseko managed property
        is_hn_managed = self._is_holiday_niseko_managed(booking_data)
        
        return {
            'booking_id': booking_id,
            'e_id': str(e_id),
            'package_id': str(package_id),
            'vendor': display_vendor,
            'guest_name': guest_name,
            'created_date': created_formatted,
            'checkin_date': checkin_formatted,
            'checkin_date_raw': checkin_date,  # NEW: Store raw check-in date
            'checkout_date_raw': checkout_date,  # NEW: Store raw check-out date
            'nights': nights,  # NEW: Number of nights
            'guests': guests,
            'country': country,  # NEW: Guest country
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
            'is_hn_managed': is_hn_managed,  # NEW: Holiday Niseko managed flag
            'raw_data': booking_data  # Store the original data for debugging
        }
    
    def _get_country_from_phone(self, booking):
        """Helper method to extract country from phone number in raw data"""
        country = booking.get('country', '')
        
        # Handle any legacy "UNKNOWN", "N/A", or similar values
        if country in ['UNKNOWN', 'N/A', 'Unknown', 'unknown', None]:
            country = ''
            
            # Try to extract country from phone if available in raw data
            raw_data = booking.get('raw_data', {})
            if raw_data:
                if 'leadGuest' in raw_data:
                    lead_guest = raw_data['leadGuest']
                elif 'booking' in raw_data and 'leadGuest' in raw_data['booking']:
                    lead_guest = raw_data['booking']['leadGuest']
                else:
                    lead_guest = raw_data.get('leadGuest', {})
                
                if lead_guest:
                    phone_number = lead_guest.get('phoneNumber', '')
                    if phone_number:
                        country = self._phone_to_country_code(phone_number)
        
        return country
    
    def _phone_to_country_code(self, phone_number: str) -> str:
        """Get the country code from phone number"""
        try:
            import phonenumbers
            from phonenumbers import region_code_for_number
            
            # Clean up the phone number (remove spaces, etc.)
            clean_phone = str(phone_number).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            parsed_number = phonenumbers.parse(clean_phone, None)
            country_code = region_code_for_number(parsed_number)
            
            return country_code if country_code else ""
            
        except Exception as e:
            # Silently handle errors
            return ""
    
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
            
            # Booking.com - multiple patterns
            elif (len(custom_id) == 10 and custom_id[0] != 'H') or "booking.com" in booking_source_str.lower():
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
        
        # Get payment status
        amount_received_raw = booking.get('amount_received_raw', 0)
        sell_price_raw = booking.get('sell_price_raw', 0)
        is_active = booking.get('is_active', True)
        
        # A booking is unpaid if:
        # 1. It's a Book & Pay or Staff booking
        # 2. It's still active (not cancelled)
        # 3. Amount received is 0
        # 4. Sell price is greater than 0 (has a value)
        is_unpaid = (
            (is_book_and_pay or is_staff_booking) and
            is_active == True and
            amount_received_raw == 0 and
            sell_price_raw > 0
        )
        
        # Debug output for troubleshooting (remove in production)
        booking_id = booking.get('e_id', booking.get('booking_id', 'unknown'))
        if booking_id in ['2447637', '2447618']:  # Debug specific bookings from screenshot
            print(f"🔍 Debug booking {booking_id}:")
            print(f"   Source: '{booking_source}'")
            print(f"   is_book_and_pay: {is_book_and_pay}")
            print(f"   is_staff_booking: {is_staff_booking}")
            print(f"   amount_received_raw: {amount_received_raw}")
            print(f"   sell_price_raw: {sell_price_raw}")
            print(f"   is_active: {is_active}")
            print(f"   Final result: is_unpaid = {is_unpaid}")
        
        return is_unpaid
    
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
    
    def _load_managed_properties(self) -> List[str]:
        """
        Load the list of Holiday Niseko managed properties from JSON file
        
        Returns:
            List of managed property names
        """
        try:
            import json
            import os
            
            # Path to the property management file
            file_path = os.path.join('data', 'property_management.json')
            
            # Check if file exists
            if not os.path.exists(file_path):
                st.warning(f"Property management file not found: {file_path}")
                return []
            
            # Load the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract Holiday Niseko managed properties specifically
            if isinstance(data, dict) and "Holiday Niseko" in data:
                managed_properties = data["Holiday Niseko"]
                # st.info(f"Loaded {len(managed_properties)} Holiday Niseko managed properties")
                return managed_properties
            else:
                st.warning("Could not find 'Holiday Niseko' key in property management file")
                return []
                
        except Exception as e:
            st.error(f"Error loading property management file: {str(e)}")
            return []

    def _is_holiday_niseko_managed(self, booking_data: Dict[str, Any]) -> bool:
        """
        Determine if a booking is for a Holiday Niseko managed property
        using the property management JSON file
        
        Args:
            booking_data: Raw booking data from API
            
        Returns:
            True if Holiday Niseko managed, False if not managed
        """
        
        # Handle different API response structures
        if 'booking' in booking_data:
            booking = booking_data.get('booking', {})
        else:
            booking = booking_data
        
        # Get hotel information
        hotel_info = booking.get('hotel', {})
        hotel_id = hotel_info.get('hotelId', '')
        hotel_name = hotel_info.get('hotelName', '')
        hotel_url = hotel_info.get('hotelUrl', '')
        
        # Load managed properties list (with caching)
        if not hasattr(self, '_managed_properties_cache'):
            self._managed_properties_cache = self._load_managed_properties()
        
        managed_properties = self._managed_properties_cache
        
        # If no managed properties loaded, default to not managed
        if not managed_properties:
            return False
        
        # Check exact matches first
        identifiers_to_check = [hotel_id, hotel_name, hotel_url]
        
        for identifier in identifiers_to_check:
            if identifier and identifier in managed_properties:
                return True
        
        # Check partial matches (property name contained in hotel name)
        for managed_prop in managed_properties:
            if managed_prop and hotel_name:
                if managed_prop.lower() in hotel_name.lower():
                    return True
        
        # If not found in the Holiday Niseko managed list, it's not managed
        return False
    
    def _apply_management_type_filter(self, bookings, management_type_filter):
        """Apply combined management and booking type filtering"""
        if management_type_filter == "All":
            return bookings
        
        filtered = []
        
        for booking in bookings:
            include_booking = False
            
            booking_type = booking.get('booking_type', '')
            is_hn_managed = booking.get('is_hn_managed', False)
            
            if management_type_filter == "🏠 Accommodation":
                # All accommodation regardless of management
                include_booking = (booking_type == 'ACCOMMODATION')
            elif management_type_filter == "🏠 HN Managed":
                # Only HN managed accommodation
                include_booking = (booking_type == 'ACCOMMODATION' and is_hn_managed)
            elif management_type_filter == "🏢 Non-Managed":
                # Only non-managed accommodation  
                include_booking = (booking_type == 'ACCOMMODATION' and not is_hn_managed)
            elif management_type_filter == "🎿 Services":
                # Only services (regardless of management)
                include_booking = (booking_type == 'SERVICE')
            
            if include_booking:
                filtered.append(booking)
        
        return filtered

    def _apply_booking_type_filter(self, bookings, booking_type_filter):
        """Apply booking type filtering to separate accommodation from services"""
        if booking_type_filter == "All Types":
            return bookings
        
        filtered = []
        
        for booking in bookings:
            include_booking = False
            
            booking_type = booking.get('booking_type', '')
            
            if booking_type_filter == "🏠 Accommodation":
                include_booking = booking_type == 'ACCOMMODATION'
            elif booking_type_filter == "🎿 Services":
                include_booking = booking_type == 'SERVICE'
            
            if include_booking:
                filtered.append(booking)
        
        return filtered
    
    def _apply_management_filter(self, bookings, management_filter):
        """Apply management-based filtering to bookings"""
        if management_filter == "All Properties":
            return bookings
        
        filtered = []
        
        for booking in bookings:
            include_booking = False
            
            is_hn_managed = booking.get('is_hn_managed', False)
            
            if management_filter == "🏠 HN Managed":
                include_booking = is_hn_managed
            elif management_filter == "🏢 Non-Managed":
                include_booking = not is_hn_managed
            
            if include_booking:
                filtered.append(booking)
        
        return filtered
    
    def _apply_season_filter(self, bookings, season_filter):
        """Apply season-based filtering to bookings based on check-in date"""
        if season_filter == "All Seasons":
            return bookings
        
        filtered = []
        
        for booking in bookings:
            include_booking = False
            
            # Get check-in date from booking
            checkin_date_raw = booking.get('checkin_date_raw', '')
            
            if checkin_date_raw:
                try:
                    # Parse the check-in date
                    checkin_dt = pd.to_datetime(checkin_date_raw)
                    
                    # Extract month and day for season comparison
                    month = checkin_dt.month
                    day = checkin_dt.day
                    
                    # Winter season: November 20 - April 30
                    # This spans across years, so we need to handle it carefully
                    is_winter = False
                    
                    if month == 11 and day >= 20:  # November 20 onwards
                        is_winter = True
                    elif month in [12, 1, 2, 3]:  # December, January, February, March
                        is_winter = True
                    elif month == 4 and day <= 30:  # April 1-30
                        is_winter = True
                    
                    # Summer season: May 1 - November 19
                    is_summer = not is_winter
                    
                    if season_filter == "❄️ Winter":
                        include_booking = is_winter
                    elif season_filter == "☀️ Summer":
                        include_booking = is_summer
                        
                except Exception as e:
                    # If we can't parse the date, skip this booking for season filtering
                    # but don't exclude it entirely - treat as "unknown season"
                    if season_filter == "All Seasons":
                        include_booking = True
                    else:
                        include_booking = False
            else:
                # No check-in date available
                # For "All Seasons", include it; for specific seasons, exclude it
                if season_filter == "All Seasons":
                    include_booking = True
                else:
                    include_booking = False
            
            if include_booking:
                filtered.append(booking)
        
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
            elif content_filter == "OTA":
                booking_source = booking.get('booking_source', '')
                include_booking = booking_source in ['Airbnb', 'Booking.com', 'Expedia', 'Jalan']
            elif content_filter == "Direct":
                booking_source = booking.get('booking_source', '')
                include_booking = booking_source == 'Book & Pay' or booking_source.startswith('Staff (')
            
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

    def _filter_created_month_to_date(self, parsed_bookings):
        """Filter bookings to only show those created from start of current month to today (in JST timezone)"""
        # Use JST for date calculations since that's your business timezone
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        
        # Get first day of current month
        first_day_of_month = now_jst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
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
                    
                    # Check if creation date is from start of month to now
                    if first_day_of_month <= created_dt_jst <= now_jst:
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
            
            # Quick Filter Presets Row
            # st.markdown("#### Quick Filters")
            quick_col1, quick_col2, quick_col3 = st.columns([2, 1, 3])

            # Replace the selectbox section in your display_recent_bookings_section method:

            with quick_col1:
                # Don't try to control the selectbox value - let Streamlit handle it
                quick_filter_preset = st.selectbox(
                    "Choose a preset:",
                    [
                        "-- Select Quick Filter --",
                        "Unpaid Accom - 2 weeks",
                        "OTA Bookings (7 days)",
                        "Direct Bookings (7 days)",
                        "Month to Date"
                    ],
                    index=0,
                    key=f"quick_filter_preset_{location}"
                )

                # Only apply preset if it's not the default and hasn't been applied yet
                if quick_filter_preset != "-- Select Quick Filter --":
                    # Check if this preset was already applied
                    last_applied = st.session_state.get(f"last_applied_preset_{location}", "")
                    
                    if last_applied != quick_filter_preset:
                        # Apply the preset
                        self.apply_quick_filter_preset(quick_filter_preset, location)
                        
                        # Remember what we applied
                        st.session_state[f"last_applied_preset_{location}"] = quick_filter_preset
                        
                        # Show a temporary success message
                        st.success(f"✅ Applied preset: {quick_filter_preset}")
                        
                        # Force a rerun to refresh the data with new filters
                        st.rerun()

            with quick_col2:
                if st.button("🔄 Reset All", key=f"reset_filters_{location}", help="Reset all filters to defaults"):
                    # Clear ALL session state for this location
                    keys_to_clear = [
                        f"recent_filter_select_{location}",
                        f"content_filter_{location}",
                        f"management_type_filter_{location}",
                        f"season_filter_{location}",
                        f"view_mode_{location}",
                        f"quick_filter_preset_{location}"
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

            with quick_col3:
                current_period = st.session_state.get(f"recent_filter_select_{location}", "3 days")
                current_content = st.session_state.get(f"content_filter_{location}", "All")
                current_property = st.session_state.get(f"management_type_filter_{location}", "🏠 Accommodation")
                current_season = st.session_state.get(f"season_filter_{location}", "❄️ Winter")

                
                with st.container():
                    st.info(f"""
                    🔍 **Currently Showing:**  
                    📅 **{current_period}** | **{current_content}** | **{current_property}** | **{current_season}**
                    """)

            # Row 1: Title and main controls
            col1, col2, col3, col4, col5, col6 = st.columns([1.3, 1, 1, 1.2, 1, 1])
            
            with col1:
                st.markdown("### Recent Bookings")
            
            with col2:
                filter_option = st.selectbox(
                    "Period:",
                    ["Last 24 hours", "2 days", "3 days", "5 days", "7 days", "14 days", "Month to Date", "Custom"],
                    # index=2,
                    key=f"recent_filter_select_{location}",
                    label_visibility="collapsed"
                )
            
            with col3:
                # Enhanced filter dropdown with Internal Requests highlighted
                content_filter = st.selectbox(
                    "Filter:",
                    ["All", "Unpaid", "Book & Pay", "Staff", "Direct", "OTA", "Airbnb", "Booking.com", "Expedia", "Jalan"],
                    index=0,
                    key=f"content_filter_{location}",
                    label_visibility="collapsed"
                )
                            
            with col4:
                # Combined Management/Type filter with Accommodation option added
                management_type_filter = st.selectbox(
                    "Property Type:",
                    ["All", "🏠 Accommodation", "🏠 HN Managed", "🏢 Non-Managed", "🎿 Services"],
                    index=1,
                    key=f"management_type_filter_{location}",
                    label_visibility="collapsed"
                )

            
            with col5:
                # Season filter dropdown
                season_filter = st.selectbox(
                    "Season:",
                    ["All Seasons", "❄️ Winter", "☀️ Summer"],
                    index=1,
                    key=f"season_filter_{location}",
                    label_visibility="collapsed"
                )
            
            with col6:
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
            elif filter_option == "Month to Date":
                # Show month to date info
                today = datetime.date.today()
                month_start = today.replace(day=1)
                
                date_col1, date_col2, date_col3 = st.columns([2, 1, 2])
                with date_col1:
                    st.info(f"📅 {month_start.strftime('%B %Y')}: {month_start} to {today}")
                with date_col2:
                    force_refresh = st.button(
                        "🔄 Refresh",
                        key=f"force_refresh_{location}",
                        help="Force refresh data"
                    )
                with date_col3:
                    pass
                    
                # Set dates for processing
                start_date = month_start
                end_date = today
            else:
                start_date = end_date = None
                force_refresh = False
            
            # Create filter key to detect changes (include all filters)
            current_filter_key = f'{filter_option}_{start_date}_{end_date}_{content_filter}_{management_type_filter}_{season_filter}'
            last_filter_key = st.session_state.get(f'last_filter_key_{location}', '')
            
            # Only fetch data if filter changed or forced refresh
            if (current_filter_key != last_filter_key or force_refresh) and not st.session_state.get('using_recent', False):
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
                    elif filter_option == "14 days":
                        result = self.fetch_recent_bookings("last_n_days", custom_days=14, force_refresh=True)
                    elif filter_option == "Month to Date":
                        # Calculate days from start of month to today
                        today = datetime.date.today()
                        month_start = today.replace(day=1)
                        days_in_month = (today - month_start).days + 1
                        result = self.fetch_recent_bookings("last_n_days", custom_days=days_in_month, force_refresh=True)
                    elif filter_option == "Custom" and start_date and end_date:
                        result = self.fetch_recent_bookings(
                            "date_range",
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d'),
                            force_refresh=True
                        )
                    else:
                        result = {'bookings': [], 'success': False, 'error': 'Invalid selection'}
                    
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
                    elif filter_option == "14 days":
                        time_filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 14)
                    elif filter_option == "Month to Date":
                        time_filtered_bookings = self._filter_created_month_to_date(parsed_bookings)
                    elif filter_option == "Custom" and start_date and end_date:
                        time_filtered_bookings = self._filter_created_custom_date_range(parsed_bookings, start_date, end_date)
                    else:
                        time_filtered_bookings = parsed_bookings
                    
                    # Clean up the content filter label for processing
                    clean_content_filter = content_filter.replace("🔧 ", "").strip()
                    
                    # Apply content filtering SECOND
                    content_filtered_bookings = self._apply_content_filter(time_filtered_bookings, clean_content_filter)
                    
                    # Apply combined management/type filtering THIRD
                    management_type_filtered_bookings = self._apply_management_type_filter(content_filtered_bookings, management_type_filter)
                    
                    # Apply season filtering FOURTH  
                    season_filtered_bookings = self._apply_season_filter(management_type_filtered_bookings, season_filter)
                    
                    # Remove duplicates AFTER all filtering
                    seen_composite_keys = set()
                    unique_filtered_bookings = []
                    
                    for booking in season_filtered_bookings:
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
                    
              
                    # Display regular stats in a cleaner format
                    # Calculate days in the selected period
                    if filter_option == "Last 24 hours":
                        days_in_period = 1
                    elif filter_option == "2 days":
                        days_in_period = 2
                    elif filter_option == "3 days":
                        days_in_period = 3
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
                        days_in_period = 1

                    # Calculate bookings per day using filtered data
                    # Calculate bookings per day using only active bookings
                    bookings_per_day = self.calculate_booking_rate(
                        unique_filtered_bookings, 
                        filter_option, 
                        start_date, 
                        end_date
                    )
                    
                    # Display stats
                    st.markdown("---")
                    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

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

                    with stats_col4:
                        st.metric("Per Day", f"{bookings_per_day:.1f}", f"Over {days_in_period} days")
                else:
                    st.info("No data available")
            
            # Display bookings based on view mode
            if view_mode == "Table":
                self.display_sortable_table(location)
            else:
                self.display_bookings_list(location)

    def display_bookings_list(self, location="main"):
            """Display the list of recent bookings with clickable buttons - FIXED column alignment"""

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
                    
            parsed_bookings = unique_bookings
            
            # Sort by created date (newest first)
            def get_created_date_for_sort(booking):
                try:
                    if 'raw_data' in booking and booking['raw_data']:
                        if 'booking' in booking['raw_data']:
                            booking_info = booking['raw_data']['booking']
                        else:
                            booking_info = booking['raw_data']
                        return booking_info.get('createdDate', '')
                    return ''
                except:
                    return ''
            
            parsed_bookings.sort(key=get_created_date_for_sort, reverse=True)
            
            # Show count info
            total_count = len(parsed_bookings)
            active_count = len([b for b in parsed_bookings if b.get('is_active')])
            cancelled_count = total_count - active_count
            st.write(f"**Displaying {total_count} booking(s): {active_count} active, {cancelled_count} cancelled**")
            
            # Performance limit for large datasets
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
                    /* Remove all button padding and sizing */
                    .stButton > button {
                        padding: 0px !important;
                        margin: 0px !important;
                        border: 1px solid #ccc !important;
                        font-size: 11px !important;
                        height: 28px !important;
                        white-space: nowrap !important;
                        overflow: hidden !important;
                        text-overflow: ellipsis !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
            
            # Create header row with FIXED COLUMN RATIOS to match data rows exactly
            if parsed_bookings:
                header_cols = st.columns([0.8, 0.9, 1.1, 1.1, 1.1, 1, 1, 1, 0.8, 0.6, 0.8, 1, 1])
                headers = ["eID", "Created", "Source", "Guest Name", "Vendor", "Sell Price", "Invoiced", "Received", "Check-in", "Nights", "Country", "Status", "Extent"]
                
                for i, (col, header) in enumerate(zip(header_cols, headers)):
                    with col:
                        st.markdown(f"**{header}**")
            
            # Display bookings with MATCHING COLUMN RATIOS
            bookings_to_display = parsed_bookings[:display_limit] if display_limit else parsed_bookings
            
            for i, booking in enumerate(bookings_to_display):
                booking_id = booking.get('e_id', '') or booking.get('booking_id', '')
                
                # Check if this is an unpaid Book & Pay booking
                is_unpaid = self._is_unpaid_book_and_pay(booking)
                
                # Check if this is an internal request
                is_internal = booking.get('extent', '') == 'REQUEST_INTERNAL'
                
                # Create columns for each booking row - EXACT SAME RATIOS AS HEADER
                col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13 = st.columns([0.8, 0.9, 1.1, 1.1, 1.1, 1, 1, 1, 0.8, 0.6, 0.8, 1, 1])
                
                # Visual highlighting for internal bookings
                if is_internal:
                    for col in [col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13]:
                        with col:
                            st.markdown('<div class="internal-booking">', unsafe_allow_html=True)
                
                with col1:
                    # eID (clickable button)
                    if booking_id and booking_id != 'unknown':
                        button_label = f"#{booking_id}"
                        if is_internal:
                            button_label = f"🔧{booking_id}"
                        
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
                    # Created date
                    st.write(booking.get('created_date', ''))
                
                with col3:
                    # Booking source
                    source = booking.get('booking_source', '')
                    st.write(source)
                
                with col4:
                    # Guest name
                    st.write(booking.get('guest_name', ''))
                
                with col5:
                    # Vendor
                    st.write(booking.get('vendor', ''))
                
                with col6:
                    # Sell price
                    st.write(booking.get('sell_price', ''))

                with col7:
                    # Amount invoiced
                    st.write(booking.get('amount_invoiced', ''))
                
                with col8:
                    # Amount received
                    received = booking.get('amount_received', '')
                    if is_unpaid:
                        st.write(f"**{received}** ⚠️" if received else "**¥0** ⚠️")
                    else:
                        st.write(received)
                
                with col9:
                    # Check-in date
                    checkin = booking.get('checkin_date', 'N/A')
                    st.write(checkin)
                
                with col10:
                    # Nights (WITHOUT "n" suffix)
                    nights = booking.get('nights', 0)
                    if nights > 0:
                        st.write(str(nights))
                    else:
                        st.write("N/A")
                
                with col11:
                    # Country - ensure truly blank for empty values and convert phone numbers
                    country = booking.get('country', '')
                    
                    # Handle any legacy "UNKNOWN", "N/A", or similar values
                    if country in ['UNKNOWN', 'N/A', 'Unknown', 'unknown', None]:
                        country = ''
                        
                        # Try to extract country from phone if available in raw data
                        raw_data = booking.get('raw_data', {})
                        if raw_data:
                            if 'leadGuest' in raw_data:
                                lead_guest = raw_data['leadGuest']
                            elif 'booking' in raw_data and 'leadGuest' in raw_data['booking']:
                                lead_guest = raw_data['booking']['leadGuest']
                            else:
                                lead_guest = raw_data.get('leadGuest', {})
                            
                            if lead_guest:
                                phone_number = lead_guest.get('phoneNumber', '')
                                if phone_number:
                                    country = self._phone_to_country_code(phone_number)
                    
                    st.write(country)
                
                with col12:
                    # Status
                    status = booking.get('status', '')
                    if status == 'Active':
                        st.write(f":green[{status}]")
                    else:
                        st.write(f":red[{status}]")
                
                with col13:
                    # Extent - shortened for space
                    extent = booking.get('extent', '')
                    if extent == 'RESERVATION':
                        st.write(f":green[RES]")
                    elif extent == 'REQUEST':
                        st.write(f":orange[RQST]")
                    elif extent == 'REQUEST_INTERNAL':
                        st.write(f":blue[🔧 INT]")
                    else:
                        st.write(extent)
                
                # Close the internal booking div
                if is_internal:
                    for col in [col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13]:
                        with col:
                            st.markdown('</div>', unsafe_allow_html=True)

    def display_sortable_table(self, location="main"):
        """Display bookings as a sortable dataframe with REORDERED COLUMNS (Type removed)"""

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
        
        if df.empty:
            st.info("No bookings to display.")
            return
        
        # REORDERED columns (Type removed, eID and Created swapped) - Order: eID, Created, Source, Guest Name, Vendor, Sell Price, Invoiced, Received, Check-in, Nights, Country, Status, Extent
        display_columns = {
            'e_id': 'eID',
            'created_date': 'Created', 
            'booking_source': 'Source',
            'guest_name': 'Guest Name',
            'vendor': 'Vendor',
            'sell_price': 'Sell Price',
            'amount_invoiced': 'Invoiced',
            'amount_received': 'Received',
            'checkin_date': 'Check-in',
            'nights': 'Nights',
            'country': 'Country',
            'status': 'Status',
            'extent': 'Extent'
        }
        
        # Only include columns that exist in the DataFrame
        available_columns = {col: name for col, name in display_columns.items() if col in df.columns}
        
        # If new columns are missing, show a warning and suggest refresh
        missing_columns = [name for col, name in display_columns.items() if col not in df.columns]
        if missing_columns:
            st.warning(f"Some enhanced fields are not available: {', '.join(missing_columns)}. Try refreshing the data to get enhanced fields.")
        
        # Create display dataframe with only available columns in the correct order
        df_display = df[list(available_columns.keys())].rename(columns=available_columns)
        
        # Add visual indicators for internal requests if extent column exists
        if 'Extent' in df_display.columns:
            def format_extent(extent):
                if extent == 'REQUEST_INTERNAL':
                    return f"🔧 {extent}"
                return extent
            
            df_display['Extent'] = df_display['Extent'].apply(format_extent)
        
        # Show count
        total_count = len(df_display)
        if 'is_active' in df.columns:
            active_count = len(df[df['is_active'] == True])
            cancelled_count = total_count - active_count
            st.write(f"**Displaying {total_count} booking(s): {active_count} active, {cancelled_count} cancelled**")
        else:
            st.write(f"**Displaying {total_count} booking(s)**")
        
        # Configure column display with proper formatting
        column_config = {}
        if 'Check-in' in df_display.columns:
            column_config['Check-in'] = st.column_config.TextColumn(
                "Check-in",
                help="Guest check-in date",
                width="small"
            )
        if 'Nights' in df_display.columns:
            column_config['Nights'] = st.column_config.NumberColumn(
                "Nights",
                help="Number of nights",
                format="%d",
                width="small"
            )
        if 'Country' in df_display.columns:
            column_config['Country'] = st.column_config.TextColumn(
                "Country",
                help="Guest country/nationality",
                width="small"
            )
        
        # Make the table interactive with sorting
        selected_indices = st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=600,
            on_select="rerun",
            selection_mode="single-row",
            column_config=column_config if column_config else None
        )
        
        # Handle row selection - load the booking
        if selected_indices and hasattr(selected_indices, 'selection') and selected_indices.selection.rows:
            selected_idx = selected_indices.selection.rows[0]
            selected_booking = unique_bookings[selected_idx]
            
            # Load the selected booking
            booking_id = selected_booking.get('e_id') or selected_booking.get('booking_id')
            if booking_id:
                st.session_state.last_search = booking_id
                st.session_state.using_recent = True
                st.rerun()

    def display_booking_summary_table(self):
        """Display bookings in a table format (alternative view) - Updated with reordered columns (Type removed)"""
        
        parsed_bookings = self.get_parsed_bookings()
        
        if not parsed_bookings:
            st.info("No recent bookings found.")
            return
        
        df = pd.DataFrame(parsed_bookings)
        
        # Select and rename columns for display - REORDERED (Type removed, eID and Created swapped)
        display_columns = {
            'e_id': 'eID',
            'created_date': 'Created',
            'booking_source': 'Source', 
            'guest_name': 'Guest Name',
            'vendor': 'Vendor',
            'sell_price': 'Sell Price',
            'amount_invoiced': 'Invoiced',
            'checkin_date': 'Check-in',
            'nights': 'Nights',
            'country': 'Country',
            'status': 'Status',
            'extent': 'Extent'
        }
        
        # Only include columns that exist
        available_columns = {col: name for col, name in display_columns.items() if col in df.columns}
        df_display = df[list(available_columns.keys())].rename(columns=available_columns)
        
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
# -*- coding: utf-8 -*-
# components/recent_bookings.py

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
    
    def fetch_recent_bookings(
        self, 
        filter_type: str = "today",
        custom_days: int = 7,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch recent bookings based on filter type
        
        Args:
            filter_type: "today", "last_n_days", or "date_range"
            custom_days: Number of days for "last_n_days" filter
            start_date: Start date for "date_range" filter (YYYY-MM-DD)
            end_date: End date for "date_range" filter (YYYY-MM-DD)
        
        Returns:
            Dictionary containing bookings data and metadata
        """
        
        try:
            api_id = st.secrets["roomboss"]["api_id"]
            api_key = st.secrets["roomboss"]["api_key"]
            
            if filter_type == "today":
                result = get_today_bookings(api_id, api_key)
                
            elif filter_type == "last_n_days":
                result = get_last_n_days_bookings(custom_days, api_id, api_key)
                
            elif filter_type == "date_range" and start_date and end_date:
                result = get_recent_bookings_for_date_range(
                    start_date, end_date, api_id, api_key
                )
            else:
                return {
                    'bookings': [],
                    'success': False,
                    'error': 'Invalid filter type or missing date parameters'
                }
            
            # Debug: Show raw response data
            if not result.get('success', True):
                st.error(f"API Error: {result.get('error', 'Unknown error')}")
                
                # Show debug info - simplified for main area display
                st.write("**Debug Information:**")
                if 'raw_text' in result:
                    st.code(result['raw_text'])
                if 'raw_response' in result:
                    st.json(result['raw_response'])
                
                return result
            
            # Update session state
            if result.get('success', True):  # Some return formats don't have 'success' key
                st.session_state.recent_bookings_data = result.get('bookings', [])
                st.session_state.recent_bookings_last_refresh = datetime.datetime.now()
                st.session_state.recent_bookings_filter = filter_type
                
                # Show success message with count AFTER filtering
                booking_count = len(result.get('bookings', []))
                if booking_count == 0:
                    st.info(f"No bookings found. {result.get('message', '')}")
                else:
                    # Don't show the raw API count, we'll show filtered count in stats instead
                    pass
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching recent bookings: {str(e)}"
            st.error(error_msg)
            
            # Show full error details - simplified
            st.write("**Error Details:**")
            import traceback
            st.code(traceback.format_exc())
            
            return {
                'bookings': [],
                'success': False,
                'error': error_msg
            }
    
    def parse_booking_summary(self, booking_wrapper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a booking from the recent bookings API into a summary format
        Based on the actual API response structure
        
        Args:
            booking_wrapper: Raw booking data from API (contains 'booking' and 'invoicePayments')
            
        Returns:
            Dictionary with parsed booking summary
        """
        
        # The actual booking data is nested under 'booking' key
        booking = booking_wrapper.get('booking', {})
        
        # Extract invoice and payment data - corrected structure
        invoice_payments = booking_wrapper.get('invoicePayments', [])
        total_invoiced = 0
        total_received = 0

        for invoice_payment in invoice_payments:
            # Get invoice amount (each item has both invoice and payment info)
            invoice_amount = invoice_payment.get('invoiceAmount', 0) or 0
            total_invoiced += invoice_amount
            
            # Get payment amount (it's at the same level, not nested)
            payment_amount = invoice_payment.get('paymentAmount', 0) or 0
            total_received += payment_amount
        
        # Extract basic info
        booking_id = booking.get('bookingId', '')
        e_id = booking.get('eId', '')
        package_id = booking.get('packageId', '')
        
        # Get vendor/property name based on booking type
        vendor = ""
        service_name = ""
        
        if booking.get('bookingType') == 'ACCOMMODATION':
            hotel_info = booking.get('hotel', {})
            vendor = hotel_info.get('hotelName', '')
        elif booking.get('bookingType') == 'SERVICE':
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
            if booking.get('bookingType') == 'ACCOMMODATION':
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
            elif booking.get('bookingType') == 'SERVICE':
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
                
                # For services, set nights to 1 by default
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
        if booking.get('bookingType') == 'SERVICE' and service_name:
            display_vendor = f"{vendor} - {service_name}"
        else:
            display_vendor = vendor
        
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
            'booking_type': booking.get('bookingType', ''),
            'extent': booking.get('extent', ''),  # Add extent
            'service_name': service_name,
            'amount_invoiced': f"¥{total_invoiced:,.0f}" if total_invoiced > 0 else "",
            'amount_received': f"¥{total_received:,.0f}" if total_received > 0 else "",
            'amount_invoiced_raw': total_invoiced,  # for calculations
            'amount_received_raw': total_received,  # for calculations
            'composite_key': f"{e_id}_{booking_id}",
            'raw_data': booking_wrapper
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
    
    def _filter_created_last_24_hours(self, parsed_bookings):
        """Filter bookings to only show those created in the last 24 hours"""
        # Get current time in JST
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        cutoff_time_jst = now_jst - datetime.timedelta(hours=24)
        filtered = []
        
        for booking in parsed_bookings:
            # Get the raw UTC date from the API data
            created_date = booking['raw_data'].get('booking', {}).get('createdDate', '')
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
    
    def _filter_created_today(self, parsed_bookings):
        """Filter bookings to only show those created today (in JST timezone)"""
        # Use JST for "today" since that's your business timezone
        now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        today_jst = now_jst.date()
        filtered = []
        
        for booking in parsed_bookings:
            created_date = booking['raw_data'].get('booking', {}).get('createdDate', '')
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
            created_date = booking['raw_data'].get('booking', {}).get('createdDate', '')
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
    
    def display_recent_bookings_section(self, location="main"):
        """Display the recent bookings section in the sidebar or main area"""
        
        # Compact header with controls in one row
        col1, col2, col3, col4 = st.columns([2, 1, 1.5, 1])
        
        with col1:
            st.markdown("### Recent Bookings")
        
        with col2:
            filter_option = st.selectbox(
                "Period:",
                ["Last 24 hours", "2 days", "3 days", "5 days", "7 days", "Custom"],
                index=0,  # Default to "Last 24 hours"
                key=f"recent_filter_select_{location}",
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
        
        # Custom date range if selected - only show when needed
        if filter_option == "Custom":
            date_col1, date_col2 = st.columns(2)
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
        else:
            start_date = end_date = None
        
        # ALWAYS fetch data when filter changes - removed refresh button logic
        current_filter_key = f'{filter_option}_{start_date}_{end_date}'
        last_filter_key = st.session_state.get(f'last_filter_key_{location}', '')
        
        if current_filter_key != last_filter_key:
            st.session_state[f'last_filter_key_{location}'] = current_filter_key
            
            with st.spinner("Loading recent bookings..."):
                if filter_option == "Last 24 hours":
                    result = self.fetch_recent_bookings("last_n_days", custom_days=2)  # Changed to get more data
                elif filter_option == "2 days":
                    result = self.fetch_recent_bookings("last_n_days", custom_days=2)
                elif filter_option == "3 days":
                    result = self.fetch_recent_bookings("last_n_days", custom_days=3)
                elif filter_option == "5 days":
                    result = self.fetch_recent_bookings("last_n_days", custom_days=5)
                elif filter_option == "7 days":
                    result = self.fetch_recent_bookings("last_n_days", custom_days=7)
                elif filter_option == "Custom" and start_date and end_date:
                    result = self.fetch_recent_bookings(
                        "date_range",
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                else:
                    result = {'bookings': [], 'success': False, 'error': 'Invalid selection'}
                
                if not result.get('success', True):
                    st.error(f"Error loading bookings: {result.get('error', 'Unknown error')}")
                    return
        
        # NOW calculate stats AFTER data is loaded
        with col3:
            # Show compact stats in the header including totals
            if st.session_state.recent_bookings_data:
                bookings = st.session_state.recent_bookings_data
                parsed_bookings = [self.parse_booking_summary(booking) for booking in bookings]
                
                # Filter bookings based on selection - all options now filter by creation date
                if filter_option == "Last 24 hours":
                    filtered_bookings = self._filter_created_last_24_hours(parsed_bookings)
                elif filter_option == "2 days":
                    filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 2)
                elif filter_option == "3 days":
                    filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 3)
                elif filter_option == "5 days":
                    filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 5)
                elif filter_option == "7 days":
                    filtered_bookings = self._filter_created_last_n_days(parsed_bookings, 7)
                else:
                    filtered_bookings = parsed_bookings
                
                # Store filtered bookings for display
                st.session_state.filtered_bookings_data = filtered_bookings
                
                total = len(filtered_bookings)
                active = len([b for b in filtered_bookings if b['is_active']])
                cancelled = total - active
                
                # Calculate totals and counts for ACTIVE bookings only
                active_bookings = [b for b in filtered_bookings if b['is_active']]
                accom_bookings = [b for b in active_bookings if b['booking_type'] == 'ACCOMMODATION']
                service_bookings = [b for b in active_bookings if b['booking_type'] == 'SERVICE']
                
                accom_total = sum([b['sell_price_raw'] for b in accom_bookings])
                service_total = sum([b['sell_price_raw'] for b in service_bookings])
                accom_count = len(accom_bookings)
                service_count = len(service_bookings)
                
                st.write(f"📊 {total} total ({active}A, {cancelled}C)")
                st.write(f"{accom_count} ACCOM (¥{accom_total:,.0f}) | {service_count} SVC (¥{service_total:,.0f})")
            else:
                st.write("📊 No data")
                st.write("")
        
        # Display bookings based on view mode
        if view_mode == "Sortable Table":
            self.display_sortable_table(location)
        else:
            self.display_bookings_list(location)
    
    def display_bookings_list(self, location="main"):
        """Display the list of recent bookings as a DataFrame with clickable buttons"""
        
        # Use filtered bookings if available, otherwise use all bookings
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            parsed_bookings = st.session_state.filtered_bookings_data
        else:
            bookings = st.session_state.recent_bookings_data
            if not bookings:
                st.info("No recent bookings found.")
                return
            parsed_bookings = [self.parse_booking_summary(booking) for booking in bookings]
        
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
        parsed_bookings.sort(key=lambda x: x['raw_data'].get('booking', {}).get('createdDate', ''), reverse=True)
        
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
            
            # Create columns for each booking row - updated to include invoice columns
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = st.columns([1.2, 1.2, 1.2, 1, 1, 1, 1.2, 1, 1, 1, 1])
            
            with col1:
                # Load button
                if booking_id and booking_id != 'unknown':
                    if st.button(
                        f"#{booking_id}",
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
                st.write(booking.get('booking_source', ''))
            
            with col3:
                st.write(booking.get('guest_name', ''))
            
            with col4:
                st.write(booking.get('sell_price', ''))

            with col5:
                st.write(booking.get('amount_invoiced', ''))

            with col6:
                st.write(booking.get('amount_received', ''))
            
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
                    st.write(f":blue[{extent}]")
                else:
                    st.write(extent)
    
    def display_sortable_table(self, location="main"):
        """Display bookings as a sortable dataframe"""
        
        # Use filtered bookings if available, otherwise use all bookings
        if hasattr(st.session_state, 'filtered_bookings_data') and st.session_state.filtered_bookings_data:
            parsed_bookings = st.session_state.filtered_bookings_data
        else:
            bookings = st.session_state.recent_bookings_data
            if not bookings:
                st.info("No recent bookings found.")
                return
            parsed_bookings = [self.parse_booking_summary(booking) for booking in bookings]
        
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
        
        bookings = st.session_state.recent_bookings_data
        
        if not bookings:
            st.info("No recent bookings found.")
            return
        
        # Parse bookings into DataFrame
        parsed_bookings = [self.parse_booking_summary(booking) for booking in bookings]
        
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
# -*- coding: utf-8 -*-
# pages/booking_viewer.py

import streamlit as st
import json
import datetime
import pandas as pd

from models.booking import Booking
from services.api_list_booking import call_api
from ui.recent_bookings import RecentBookingsManager

# Set page config
st.set_page_config(
    page_title="Booking Viewer",
    page_icon="📋",
    layout="wide"
)

def write_links_box():
    """Writes the expandable links box with useful reference links"""
    wine_dine_link = "https://www.winedineniseko.com/"
    rhythm_referral_link = "https://book.rhythmjapan.com/public/booking/order02.jsf?mv=1&vs=rhythmniseko&segment=HolidayNiseko"
    gsg_link = "https://holidayniseko.com/sites/default/files/services/2024-08/Holiday%20Niseko%20Guest%20Service%20Guide%202024_2025.pdf"

    with st.container():
        links_expander = st.expander("Links", expanded=False)
        with links_expander:
            st.markdown(f"[Niseko Wine and Dine link]({wine_dine_link})")
            st.markdown(f"[Rhythm Rentals Referral link]({rhythm_referral_link})")
            st.markdown(f"[Explore/Core Transfers-Lessons-Activities Referral link](https://book.explore-niseko.com/public/booking/order02.jsf?mv=1&vs=explore&i18n=en&i18n=en&segment=HolidayNiseko)")
            st.markdown(f"[Guest Service Guide link]({gsg_link})")

def apply_custom_styles():
    """Apply custom CSS styling to the page"""
    st.markdown(
        """
        <style>
        footer {display: none}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stButton button {
            width: 100%;
            white-space: pre-wrap !important;
        }
        
        /* New styles for better visual hierarchy */
        .section-header {
            font-size: 18px;
            font-weight: bold;
            color: #1E3A8A;
            margin-top: 15px;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #E5E7EB;
        }
        
        .booking-id {
            font-size: 22px;
            font-weight: bold;
            color: #1E3A8A;
            margin-bottom: 10px;
        }
        
        .booking-info {
            padding: 10px;
            background-color: #F9FAFB;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        
        .status-active {
            display: inline-block;
            color: white;
            background-color: #10B981;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .status-pending {
            display: inline-block;
            color: white;
            background-color: #F59E0B;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .action-button {
            margin-top: 5px;
            margin-bottom: 5px;
        }
        
        .info-label {
            font-weight: bold;
            color: #4B5563;
        }
        
        .highlight-box {
            background-color: #EFF6FF;
            border-left: 3px solid #3B82F6;
            padding: 10px;
            margin-bottom: 10px;
        }

        /* Invoice table specific styling */
        .invoice-table-container {
            max-width: 100%;
            overflow-x: auto;
        }
        
        .invoice-table-container table {
            width: auto !important;
            table-layout: auto !important;
        }
        
        .invoice-table-container th, .invoice-table-container td {
            white-space: nowrap;
            padding: 4px 8px;
            min-width: 60px;
            max-width: 120px;
        }
        
        /* Add these styles to fix text wrapping */
        .email-subject {
            white-space: normal;
            word-wrap: break-word;
            max-width: 100%;
            overflow-wrap: break-word;
        }
        
        /* Recent bookings card styling */
        .recent-booking-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            background-color: #fafafa;
        }
        
        .recent-booking-header {
            font-weight: bold;
            color: #1E3A8A;
            margin-bottom: 4px;
        }
        
        .recent-booking-details {
            font-size: 12px;
            color: #6B7280;
        }
        
        .source-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            color: white;
            display: inline-block;
            margin-left: 5px;
        }
        
        .source-airbnb { background-color: #FF5A5F; }
        .source-booking { background-color: #003580; }
        .source-expedia { background-color: #00355F; }
        .source-jalan { background-color: #FF0000; }
        .source-bookpay { background-color: #00A699; }
        .source-staff { background-color: #6B5B95; }
        
        /* Debug section styling */
        .debug-section {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
        }
        
        .debug-json {
            max-height: 400px;
            overflow-y: auto;
            background-color: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 3px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

def fetch_booking_data(booking_id):
    """
    Call the API and return the booking data
    
    Args:
        booking_id: The booking ID to fetch
    
    Returns:
        Booking object or None if API call failed
    """
    try:
        # Ensure booking_id is stripped of whitespace
        booking_id = booking_id.strip()
        
        with st.spinner("Fetching booking details..."):
            response = call_api(
                booking_id,
                st.secrets["roomboss"]["api_id"],
                st.secrets["roomboss"]["api_key"]
            )
        
        if response.ok:
            booking = Booking(json.loads(response.text), api_type="listBooking")
            
            # Update the property name and guest name in recent bookings if this is a valid booking
            if "recent_bookings" in st.session_state:
                # Convert any string IDs to tuples first
                recent_bookings_updated = []
                for item in st.session_state.recent_bookings:
                    if isinstance(item, tuple):
                        if len(item) == 2:
                            # Old format (id, property_name)
                            id_val, prop_name = item
                            recent_bookings_updated.append((id_val.strip(), prop_name, ""))
                        elif len(item) == 3:
                            # New format (id, property_name, guest_name)
                            recent_bookings_updated.append(item)
                        else:
                            # Unexpected format, create new tuple with defaults
                            recent_bookings_updated.append((str(item[0]).strip(), "", ""))
                    else:
                        # If it's just a string ID, convert to tuple with empty property and guest names
                        recent_bookings_updated.append((item.strip(), "", ""))
                
                st.session_state.recent_bookings = recent_bookings_updated
                
                # Find the index of the current booking ID
                for i, (id, prop_name, _) in enumerate(st.session_state.recent_bookings):
                    if id.strip() == booking_id.strip():
                        # Get property name - use vendor or a fallback property
                        property_name = getattr(booking, 'vendor', '') or getattr(booking, 'property_name', '')
                        
                        # Get guest name from the booking - specific to your data structure
                        guest_name = ""
                        
                        # Based on the debug output, we know these attributes are available
                        if hasattr(booking, 'full_name') and booking.full_name:
                            guest_name = booking.full_name
                        elif hasattr(booking, 'given_name') and hasattr(booking, 'family_name'):
                            if booking.given_name and booking.family_name:
                                guest_name = f"{booking.given_name} {booking.family_name}"
                            elif booking.given_name:
                                guest_name = booking.given_name
                            elif booking.family_name:
                                guest_name = booking.family_name
                        
                        # Update the tuple with the new property name and guest name
                        if guest_name:
                            st.session_state.recent_bookings[i] = (id, property_name, guest_name)
                        else:
                            st.session_state.recent_bookings[i] = (id, property_name, "")
                        
                        break
                        
            return booking
        else:
            st.error(f"Error fetching booking: {response.status_code} - {response.reason}")
            return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def display_json_debug(booking):
    """Display JSON response in a debug section"""
    with st.expander("🔍 Debug: Raw JSON Response", expanded=False):
        # Tab for different views of the JSON
        json_tab1, json_tab2, json_tab3 = st.tabs(["Pretty JSON", "Raw Text", "Key Structure"])
        
        with json_tab1:
            st.json(booking.json_response)
        
        with json_tab2:
            st.text_area(
                "Raw JSON Response", 
                value=json.dumps(booking.json_response, indent=2), 
                height=400,
                help="Raw JSON response from the API"
            )
        
        with json_tab3:
            # Show the structure of the JSON
            st.write("**Main Keys:**")
            if isinstance(booking.json_response, dict):
                for key, value in booking.json_response.items():
                    if isinstance(value, dict):
                        st.write(f"- **{key}** (dict with {len(value)} keys)")
                        for subkey in list(value.keys())[:5]:  # Show first 5 subkeys
                            st.write(f"  - {subkey}")
                        if len(value) > 5:
                            st.write(f"  - ... and {len(value) - 5} more")
                    elif isinstance(value, list):
                        st.write(f"- **{key}** (list with {len(value)} items)")
                    else:
                        st.write(f"- **{key}**: {type(value).__name__}")

def display_booking_details(booking):
    """Display booking details in a three-column layout with better spacing"""
    # Process room data first without displaying (just to set variables)
    process_room_data(booking)

    # Add JSON debug section at the top
    display_json_debug(booking)

    # Initialize cognito_data to None
    cognito_data = None
    
    # Cognito Check-in Section - only get data if managed by Holiday Niseko
    if booking.managed_by == "Holiday Niseko":
        cognito_data = booking.write_cognito()

    # Create three columns with adjusted ratios for better fit
    left_col, middle_col, right_col = st.columns([0.6, 0.8, 1.2])
    
    # Display booking info in left column
    with left_col:
        with st.container(border=True):
            booking.write_key_booking_info()
            booking.write_notes()
    
    # Display email subject and room info in middle column
    with middle_col:
        # Email subject at the top
        with st.container(border=True):
            st.markdown("##### Email Subject")
            st.markdown(f'<div class="email-subject">{booking.email_subject_line}</div>', unsafe_allow_html=True)
            st.write("---")
            # Room information
            booking.write_room_info(booking.room_list_todf)  
    
    # Display invoices, cognito, arrival/departure, and emails in right column
    with right_col:
        # Invoices container
        with st.expander(label="Invoices & Payments", expanded=True):
            booking.write_payment_df()
            st.markdown("[Flywire Login](https://app.flywire.com/#/app-login)")
        
        st.write("")
        
        # Cognito Check-in Section - only display if managed by Holiday Niseko AND we have data
        if booking.managed_by == "Holiday Niseko" and cognito_data:
            is_completed = cognito_data['completed']
            
            # Calculate days to check-in for the message
            try:
                date_checkin = pd.to_datetime(booking.accom_checkin).date()
                date_checkout = pd.to_datetime(booking.accom_checkout).date()
                today = datetime.datetime.now().date()
                
                days_to_checkin = (date_checkin - today).days
                days_to_checkout = (date_checkout - today).days
                
                # Determine the time status text
                if days_to_checkin > 0:
                    time_status = f"{days_to_checkin} days until check-in"
                elif days_to_checkin == 0:
                    time_status = "Check-in is today"
                elif days_to_checkout >= 0:
                    time_status = f"Currently staying: {days_to_checkout} days until check-out"
                else:
                    time_status = f"Checked out {abs(days_to_checkout)} days ago"
            except:
                time_status = ""
            
            if is_completed:
                # Show completion info with blue/green background
                message = f"✓ **Online Check-in Complete** • {time_status}\n\n"
                message += f"**Phone Number:** {cognito_data['phone']}\n\n"
                message += f"**Expected Arrival:** {cognito_data['arrival_time']}"
                st.info(message)
            else:
                # Show warning with yellow/orange background
                message = f"⚠ **Online Check-in Not Complete** • {time_status}\n\n"
                if cognito_data['check_in_link']:
                    message += f"[Click here to complete check-in]({cognito_data['check_in_link']})"
                else:
                    message += "Unable to generate check-in link - missing required information"
                st.warning(message)
        
        elif booking.managed_by != "Holiday Niseko":
            # Not Holiday Niseko managed - simple info message
            front_desk_manual_link = "https://docs.google.com/document/d/1-R1zBxcY9sBP_ULDc7D0qaResj9OTU2s/r/edit/edit#heading=h.rus25g7i893t"
            st.info(f"Not managed by Holiday Niseko - [check Front Desk Manual]({front_desk_manual_link})")
        
        # NEW: arrival / departure / method box directly under check-in section
        booking.write_arrival_departure_info()
        
        st.write("")
        
        # Emails container
        with st.container(border=True):
            st.write("Emails")
            
            # Create tabs for different email templates
            email_tabs = st.tabs([
                "Confirmation", 
                "Guest Services", 
                "OTA", 
                "Payment"
            ])
            
            with email_tabs[0]:  # Booking Confirmation
                booking.write_booking_confirmation()
            
            with email_tabs[1]:  # Guest Services
                booking.write_gsg_upsell()
                booking.write_alt_gsg_upsell()
                
                if booking.has_ski_rentals():
                    st.write("---")
                    booking.write_ski_rental_confirmation_emails()

                if booking.has_explore_transfers():
                    st.write("---")
                    booking.write_explore_transfer_confirmation_emails()
            
            with email_tabs[2]:  # OTA Emails
                booking.write_first_ota_email()
                booking.write_follow_up_email_verification()
                booking.write_second_OTA_email()
            
            with email_tabs[3]:  # Payment
                booking.write_invoice_sentences()
                booking.write_overdue_email()


def process_room_data(booking):
    """Process room data to set necessary attributes without displaying"""
    if not booking.room_list_todf or len(booking.room_list_todf) == 0:
        return
        
    # Track check-in and check-out dates
    all_checkins = []
    all_checkouts = []
    
    # Process each room
    for room in booking.room_list_todf:
        all_checkins.append(room[2])  # Check-in is third item
        all_checkouts.append(room[3])  # Check-out is fourth item
    
    # Set min check-in and max check-out dates
    if all_checkins:
        booking.accom_checkin = min(all_checkins)
    if all_checkouts:
        booking.accom_checkout = max(all_checkouts)
    
    # Generate email subject line
    booking.email_subject_line = (
        f"{booking.vendor} Booking #{booking.eId} ~ "
        f"{booking.accom_checkin} - {booking.accom_checkout} "
        f"({booking.nights} nights) {booking.guests} guests"
    )


def main():
    """Main function to run the booking viewer page"""
    st.title(" ")
    apply_custom_styles()
    
    # Initialize recent bookings manager
    recent_manager = RecentBookingsManager()
    
    # Create a search column layout
    search_col1, search_col2, blank_space = st.columns([1, 0.5, 3])

    # Initialize session state if not already there
    if "recent_bookings" not in st.session_state:
        st.session_state.recent_bookings = []
    
    # Track if we're using a recent booking selection
    if "using_recent" not in st.session_state:
        st.session_state.using_recent = False
    
    # Convert any existing IDs to new format tuples on startup and ensure all IDs are stripped
    recent_bookings_updated = []
    for item in st.session_state.recent_bookings:
        if isinstance(item, tuple):
            if len(item) == 3:
                # Already in new format (id, property_name, guest_name)
                id_val, prop_name, guest_name = item
                recent_bookings_updated.append((id_val.strip(), prop_name, guest_name))
            elif len(item) == 2:
                # Old format (id, property_name)
                id_val, prop_name = item
                recent_bookings_updated.append((id_val.strip(), prop_name, ""))
            else:
                # Unexpected format, create new tuple with defaults
                recent_bookings_updated.append((str(item[0]).strip(), "", ""))
        else:
            # If it's just a string ID, convert to tuple with empty property and guest names
            recent_bookings_updated.append((item.strip(), "", ""))
    
    st.session_state.recent_bookings = recent_bookings_updated
    
    with st.sidebar:
        # Get value for text input - use last_search if using_recent, otherwise empty
        initial_value = ""
        if st.session_state.using_recent and "last_search" in st.session_state:
            initial_value = st.session_state.last_search
            # Reset the flag after using it once
            st.session_state.using_recent = False
        
        # Create the booking ID input field
        booking_id = st.text_input(
            "Booking ID", 
            value=initial_value,
            help="Enter the booking ID number"
        )
    
    with st.sidebar:
        # Place clear button in the same column
        clear_button = st.button("Clear", use_container_width=True)
    
    # Create a sidebar for recent bookings (user searched bookings)
    with st.sidebar:
        st.header("Recent Searches")
        
        if not st.session_state.recent_bookings:
            st.info("No bookings searched")
        else:
            for idx, item in enumerate(st.session_state.recent_bookings):
                # Handle different tuple formats
                if isinstance(item, tuple):
                    if len(item) == 3:
                        recent_id, property_name, guest_name = item
                    elif len(item) == 2:
                        recent_id, property_name = item
                        guest_name = ""
                    else:
                        recent_id = str(item[0])
                        property_name = ""
                        guest_name = ""
                else:
                    recent_id = item
                    property_name = ""
                    guest_name = ""
                
                # Create button text with all available information
                if property_name and guest_name:
                    # Include both property name and guest name in button with a proper new line
                    button_text = f"#{recent_id} - {property_name}\n{guest_name}"
                elif property_name:
                    button_text = f"#{recent_id} - {property_name}"
                else:
                    button_text = f"#{recent_id}"
                
                # Create the button with the combined text
                if st.button(button_text, key=f"recent_{idx}"):
                    # Set the booking ID for the next run
                    st.session_state.last_search = recent_id
                    # Flag that we're using a recent booking selection
                    st.session_state.using_recent = True
                    st.rerun()
                
                # Add a small spacer between buttons
                st.write("")

    with st.sidebar:
        write_links_box()
    
    # If a search was executed (booking ID entered)
    if booking_id:
        # Clean the booking ID (remove any whitespace)
        clean_booking_id = booking_id.strip()

        if clean_booking_id:
            # Extract just the IDs from the list of tuples for comparison (stripping each ID)
            existing_ids = [id.strip() for id, _, _ in st.session_state.recent_bookings]
            
            if clean_booking_id not in existing_ids:
                # Add to the front of the list (most recent first) with empty property and guest names initially
                st.session_state.recent_bookings.insert(0, (clean_booking_id, "", ""))
                # Limit the list size (e.g., keep only the 10 most recent)
                st.session_state.recent_bookings = st.session_state.recent_bookings[:10]
    
            # Store the search in session state to maintain it on reruns
            st.session_state.last_search = clean_booking_id
    
    # If clear button pressed
    if clear_button:
        # Simply remove last_search from session state
        if "last_search" in st.session_state:
            del st.session_state.last_search
        # Rerun the app with a clean state
        st.rerun()
    
    # If we have a previous search in session state, execute it
    if "last_search" in st.session_state:
        booking = fetch_booking_data(st.session_state.last_search)
        
        if booking:
            # Display booking details
            display_booking_details(booking)
    
    # If no search history, display a welcome message with recent bookings
    if "last_search" not in st.session_state:
        st.write("Enter a booking ID to view details")
        
        # Display recent bookings from API in main area as a helpful starting point
        st.write("---")
        recent_manager.display_recent_bookings_section(location="main")
    

if __name__ == "__main__":
    main()

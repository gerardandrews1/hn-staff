# pages/booking_viewer.py

import streamlit as st
import json
import datetime
import pandas as pd

from models.booking import Booking
from services.api_list_booking import call_api

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
            st.markdown(f"[Rhythm referral link]({rhythm_referral_link})")
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

def display_booking_details(booking):
    """Display booking details in a three-column layout"""
    # Process room data first without displaying (just to set variables)
    # We'll use a separate function to avoid duplicate displays
    process_room_data(booking)
    
    # Create three columns
    left_col, middle_col, right_col = st.columns([1.5, 2, 1.7])
    
    # Display booking info in left column
    with left_col:
        with st.container(border=True):
            booking.write_key_booking_info()
            booking.write_notes()
    
    # Display email subject and room info in middle column
    with middle_col:
        # Email subject at the top
        st.markdown("##### Email Subject")
        st.markdown(booking.email_subject_line)
        
        # Room information
        # st.markdown("##### Room Information")
        booking.write_room_info(booking.room_list_todf)  
    
    # Display check-in info in right column
    with right_col:
        with st.container():
            booking.write_payment_df()
    
    # Add divider before email templates section
    st.write("---")
    
    # Create lower section for email templates
    email_col, spacer_col = st.columns([4, 1])
    
    # Display email templates
    with email_col:
        st.write("Emails")
        with st.container():
            # Create tabs for different email templates
            email_tabs = st.tabs([
                "Booking Confirmation", 
                "Guest Services", 
                "OTA Emails", 
                "Payment"
            ])
            
            with email_tabs[0]:  # Booking Confirmation
                booking.write_booking_confirmation()
            
            with email_tabs[1]:  # Guest Services
                booking.write_gsg_upsell()
            
            with email_tabs[2]:  # OTA Emails
                booking.write_first_ota_email()
                booking.write_second_OTA_email()
                booking.write_OTA_email()
            
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
    
    # Create a sidebar for recent bookings
    with st.sidebar:
        st.header("Recent Searches")
        
        if not st.session_state.recent_bookings:
            st.info("No bookings searched")
        else:
            # st.write("Click to view a recent booking:")
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
    if booking_id:  # Remove the .strip() check to always process any input
        # Clean the booking ID (remove any whitespace)
        clean_booking_id = booking_id.strip()

        if clean_booking_id:  # Only proceed if there's something after stripping
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
    
    # If no search history, display a welcome message
    if "last_search" not in st.session_state:
        st.write("Enter a booking ID to view details")
        
        # Add a sample/recent bookings section (could be populated from a database)
        with st.expander("Recent Bookings"):
            st.info("Recent bookings feature coming soon")

if __name__ == "__main__":
    main()
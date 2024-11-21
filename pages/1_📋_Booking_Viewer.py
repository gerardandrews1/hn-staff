import streamlit as st
from config import AppConfig, APP_SETTINGS
from services.roomboss import RoombossService
from utils.validation import validate_booking_id

# Initialize
config = AppConfig.from_secrets()
roomboss = RoombossService(config)

# Page config
st.set_page_config(**APP_SETTINGS)

def display_booking_card(booking_data):
    """Display a nicely formatted booking card"""
    formatted = roomboss.format_booking_display(booking_data)
    
    # Guest Information
    st.subheader("Guest Information")
    cols = st.columns([2, 2, 1, 1])
    with cols[0]:
        st.metric("Name", formatted["Guest Information"]["Name"])
    with cols[1]:
        st.metric("Email", formatted["Guest Information"]["Email"])
    with cols[2]:
        st.metric("Phone", formatted["Guest Information"]["Phone"])
    with cols[3]:
        st.metric("Nationality", formatted["Guest Information"]["Nationality"])
    
    # Bookings
    for booking in formatted["Bookings"]:
        with st.expander(f"🏨 {booking['Type']} Booking", expanded=True):
            for item in booking["Items"]:
                if booking["Type"] == "ACCOMMODATION":
                    cols = st.columns([1, 1, 1, 1])
                    with cols[0]:
                        st.metric("Room", item["Room"])
                    with cols[1]:
                        st.metric("Check-in", item["Check-in"])
                    with cols[2]:
                        st.metric("Check-out", item["Check-out"])
                    with cols[3]:
                        st.metric("Guests", str(item["Guests"]))
                else:  # SERVICE
                    cols = st.columns([2, 2])
                    with cols[0]:
                        st.metric("Service", item["Service"])
                    with cols[1]:
                        st.metric("Date", item["Date"])

def main():
    st.title("Booking Viewer")
    
    # Search box and button in the same line
    col1, col2 = st.columns([3, 1])
    with col1:
        booking_id = st.text_input(
            "Enter Booking ID",
            max_chars=7,
            placeholder="1234567",
            help="Enter the 7-digit booking reference number"
        )
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    if booking_id or search_button:
        # Validate booking ID
        is_valid, error_message = validate_booking_id(booking_id)
        if not is_valid:
            st.error(error_message)
            return
            
        with st.spinner("Fetching booking details..."):
            # Fetch booking data
            booking_data = roomboss.get_booking(booking_id)
            
            if not booking_data:
                st.error("Booking not found")
                return
            
            # Display booking information
            display_booking_card(booking_data)
            
            # Add action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📝 Edit Booking", use_container_width=True):
                    st.info("Editing functionality coming soon!")
            with col2:
                if st.button("📧 Email Guest", use_container_width=True):
                    st.info("Email functionality coming soon!")
            with col3:
                if st.button("🖨️ Print Details", use_container_width=True):
                    st.info("Print functionality coming soon!")

if __name__ == "__main__":
    main()
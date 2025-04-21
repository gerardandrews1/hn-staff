import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import datetime
from typing import Dict, Any

# Add root directory to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from config import AppConfig, APP_SETTINGS
from services.roomboss import RoombossService

# Initialize
st.set_page_config(page_title="Booking Viewer", page_icon="🔍", layout="wide")
config = AppConfig.from_secrets()
roomboss = RoombossService(config)

def write_key_booking_info(booking_data: Dict[str, Any]) -> None:
    """Writes key booking information in the sidebar"""
    # Get vendor and booking info with fallbacks
    vendor = booking_data.get('order', {}).get('bookings', [{}])[0].get('hotel', {}).get('hotelName', 'Unknown Property')
    eid = booking_data.get('order', {}).get('bookings', [{}])[0].get('eId', 'Unknown')
    booking_id = booking_data.get('order', {}).get('bookings', [{}])[0].get('bookingId', 'Unknown')
    
    # Get guest info
    lead_guest = booking_data.get('order', {}).get('leadGuest', {})
    guest_name = f"{lead_guest.get('givenName', '')} {lead_guest.get('familyName', '')}"
    guest_email = lead_guest.get('email', '')
    guest_phone = lead_guest.get('phoneNumber', '')
    
    # Get booking status
    booking_status = booking_data.get('order', {}).get('bookings', [{}])[0].get('active', False)
    created_date = booking_data.get('order', {}).get('bookings', [{}])[0].get('createdDate', '')
    if created_date:
        created_date = pd.to_datetime(created_date).strftime('%d-%b-%Y')

    # Display information
    st.markdown(f"##### {vendor} #{eid}")
    st.markdown(f"###### {guest_name}")
    if created_date:
        st.write(f"Created - {created_date}")
    
    # Management and status
    managed_by = get_management_company(vendor)
    if managed_by == 'Holiday Niseko':
        st.write("**:green[Managed by Holiday Niseko]**")
    else:
        st.write(f"**:red[Managed by {managed_by}]**")
    
    if booking_status:
        st.write("**:green[Booking is Active]**")
    else:
        st.write(":red[Booking is Cancelled]")
    
    # RoomBoss link
    rboss_link = f"https://app.roomboss.com/ui/booking/edit.jsf?bid={booking_id}"
    st.markdown(f"[Open #{eid} in RoomBoss]({rboss_link})")
    
    # Contact info
    if guest_phone:
        st.write(":telephone_receiver:", guest_phone)
    
    # Email handling
    if guest_email:
        if "booking.com" not in guest_email:
            st.write(f":email: {guest_email}")
            st.write("---")
            
            # Payment and services links
            if eid and guest_email:
                payment_link = f"https://holidayniseko.evoke.jp/public/yourbooking.jsf?id={eid}&em={guest_email}"
                gsg_link = f"https://holidayniseko2.evoke.jp/public/booking/order02.jsf?mv=1&vs=WinterGuestServices&bookingEid={eid}"
                
                st.markdown(f"[View booking details and make payments here]({payment_link})")
                st.markdown(f"[Book your guest services here]({gsg_link})")
        else:
            st.write(":red[Need to get guest email]")
            st.write("---")

def get_management_company(vendor: str) -> str:
    """Determine management company based on vendor/property name"""
    # This should be moved to a configuration file or database
    hn_props = ["Property1", "Property2"]  # Add actual HN properties
    vn_props = ["VNProperty1", "VNProperty2"]  # Add actual VN properties
    
    if vendor in hn_props:
        return "Holiday Niseko"
    elif vendor in vn_props:
        return "Vacation Niseko"
    else:
        return "Other Management"

# [Previous imports and setup code remains the same...]


def write_room_info(booking_data: Dict[str, Any]) -> None:
    """Display room information in a formatted table"""
    # Add custom CSS for the new table style
    st.markdown("""
        <style>
        .table-wrapper {
            width: 350px;
            border: 1px solid #e0e0e0;
            border-top: 4px solid #0C8C3C;
            background: white;
            padding: 0;
            margin: 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .header-row {
            background: white;
            border-bottom: 1px solid #e0e0e0;
        }

        .header-cell {
            padding: 15px;
            color: #333;
        }

        .header-title {
            font-size: 16px;
            font-weight: 500;
            margin: 0 0 5px 0;
        }

        .booking-id {
            color: #666;
            font-size: 14px;
            margin: 0 0 10px 0;
        }

        .login-button {
            display: inline-block;
            background-color: #FFB800;
            color: #000000;
            padding: 6px 12px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
            font-size: 13px;
        }

        th, td {
            padding: 10px;
            text-align: left;
            border: 1px solid #e0e0e0;
        }

        th {
            width: 100px;
            font-weight: 500;
            color: #333;
            background: white;
        }

        td {
            background: white;
        }
        </style>
    """, unsafe_allow_html=True)

    # [Rest of the function remains the same]

    # Get room data
    for booking in booking_data.get('order', {}).get('bookings', []):
        if booking.get('bookingType') == 'ACCOMMODATION':
            for room in booking.get('items', []):
                # Get room details
                property_name = booking.get('hotel', {}).get('hotelName', '')
                room_name = room.get('roomType', {}).get('roomTypeName', '')
                check_in = room.get('checkIn', '').replace('-', '/')
                check_out = room.get('checkOut', '').replace('-', '/')
                nights = (pd.to_datetime(check_out) - pd.to_datetime(check_in)).days
                guests = room.get('numberGuests', 0)
                rate = f"¥{room.get('priceRetail', 0):,.0f}"
                eid = booking.get('eId', '')

                # Create HTML table with header as part of the table
                table_html = f"""
                <table class="table-wrapper">
                    <tr class="header-row">
                        <td colspan="2" class="header-cell">
                            <div class="header-title">Booking Details</div>
                            <div class="booking-id">Booking ID: {eid}</div>
                            <a href="https://holidayniseko.com/my-booking" class="login-button">Login to MyBooking</a>
                        </td>
                    </tr>
                    <tr>
                        <th>Property</th>
                        <td>{property_name}</td>
                    </tr>
                    <tr>
                        <th>Room</th>
                        <td>{room_name}</td>
                    </tr>
                    <tr>
                        <th>Check-in</th>
                        <td>{check_in}</td>
                    </tr>
                    <tr>
                        <th>Check-out</th>
                        <td>{check_out}</td>
                    </tr>
                    <tr>
                        <th>Nights</th>
                        <td>{nights}</td>
                    </tr>
                    <tr>
                        <th>Guests</th>
                        <td>{guests}</td>
                    </tr>
                    <tr>
                        <th>Rate</th>
                        <td>{rate}</td>
                    </tr>
                </table>
                """
                st.markdown(table_html, unsafe_allow_html=True)


def write_payment_info(booking_data: Dict[str, Any]) -> None:
    """Display payment information in an expandable section"""
    payment_data = booking_data.get('order', {}).get('invoicePayments', [])
    
    if payment_data:
        payment_list = []
        for payment in payment_data:
            payment_info = {
                "Invoice": payment.get('invoiceNumber', ''),
                "Created": pd.to_datetime(payment.get('invoiceDate', '')),
                "Invoiced": payment.get('invoiceAmount', 0),
                "Due": pd.to_datetime(payment.get('invoiceDueDate', '')),
                "Paid": payment.get('paymentAmount', 0),
                "Date Paid": pd.to_datetime(payment.get('paymentDate')) if payment.get('paymentDate') else pd.NaT
            }
            payment_list.append(payment_info)
        
        if payment_list:
            df = pd.DataFrame(payment_list)
            st.markdown("###### Invoices and Payments")
            st.markdown(
                df.style.hide(axis="index")
                .format({
                    "Created": lambda x: x.strftime("%d %b %Y"),
                    "Due": lambda x: x.strftime("%d %b %Y"),
                    "Date Paid": lambda x: x.strftime("%d %b %Y") if pd.notnull(x) else '',
                    "Invoiced": "¥{:,.0f}",
                    "Paid": "¥{:,.0f}"
                })
                .set_table_styles([{
                    'selector': 'th',
                    'props': [('font-size', '10pt'), ('text-align', 'center')]
                }])
                .set_properties(**{
                    'font-size': '8pt',
                    'text-align': 'center'
                }).to_html(),
                unsafe_allow_html=True
            )

def write_days_to_checkin(booking_data: Dict[str, Any]) -> None:
    """Display countdown to check-in or check-out"""
    # Get check-in and check-out dates from first accommodation booking
    for booking in booking_data.get('order', {}).get('bookings', []):
        if booking.get('bookingType') == 'ACCOMMODATION':
            for room in booking.get('items', []):
                checkin = room.get('checkIn')
                checkout = room.get('checkOut')
                if checkin and checkout:
                    date_checkin = pd.to_datetime(checkin).normalize()
                    date_checkout = pd.to_datetime(checkout).normalize()
                    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    days_to_checkin = (date_checkin - today).days
                    days_after_checkout = (date_checkout - today).days
                    
                    if days_to_checkin > 0:
                        st.write(f"{days_to_checkin} days until check-in")
                    elif days_to_checkin == 0:
                        st.write("Check-in is today")
                    else:
                        if days_after_checkout < 0:
                            st.write(f"Checked out {abs(days_after_checkout)} days ago")
                        elif days_after_checkout == 0:
                            st.write("Check-out is today!")
                        else:
                            st.write(f"Currently staying: {days_after_checkout+1} days until check-out")
                    break
            break

def write_notes(booking_data: Dict[str, Any]) -> None:
    """Display booking notes if they exist"""
    notes = booking_data.get('order', {}).get('bookings', [{}])[0].get('notes')
    if notes:
        st.markdown("##### Notes")
        st.markdown(notes)

def main():
    st.title("Booking Viewer")
    
    # Get configuration from secrets
    gs_api_config = {
        'base_url': st.secrets["gs_api"]["base_url"],
        'api_id': st.secrets["gs_api"]["api_id"],
        'api_key': st.secrets["gs_api"]["api_key"],
    }
    
    col1, col2 = st.columns([3, 1])
    with col1:
        booking_id = st.text_input(
            "Enter Booking ID",
            max_chars=7,
            placeholder="1234567"
        )
    with col2:
        search = st.button("🔍 Search", use_container_width=True)

    if booking_id and search:
        with st.spinner("Fetching booking details..."):
            # First get basic booking info
            booking_data = roomboss.get_booking(booking_id)
            
            if booking_data:
                # Get the full booking ID
                full_booking_id = booking_data.get('order', {}).get('bookings', [{}])[0].get('bookingId')
                
                # Get additional package details if needed
                package_details = None
                if full_booking_id:
                    package_details = get_package_details(
                        base_url=gs_api_config['base_url'],
                        api_id=gs_api_config['api_id'],
                        api_key=gs_api_config['api_key'],
                        booking_id=full_booking_id
                    )
                
                # Create two-column layout
                left_col, right_col = st.columns([1, 2])
                
                with left_col:
                    write_key_booking_info(booking_data)
                    write_days_to_checkin(booking_data)
                    
                    # Add package details if available
                    if package_details and package_details.get('package'):
                        pkg = package_details['package']
                        with st.expander("Additional Package Details"):
                            if pkg.get('currencyCode'):
                                st.write(f"Currency: {pkg['currencyCode']}")
                            if pkg.get('totalAmount'):
                                st.write(f"Total Amount: ¥{pkg['totalAmount']:,}")
                            if pkg.get('receivedAmount'):
                                st.write(f"Received Amount: ¥{pkg['receivedAmount']:,}")
                
                with right_col:
                    write_room_info(booking_data)
                    write_notes(booking_data)
                    
                    # Payment information with combined data
                    with st.expander("Payment Information", expanded=True):
                        write_payment_info(booking_data)
                        if package_details and package_details.get('package', {}).get('invoicePayments'):
                            st.markdown("##### Additional Payment Details")
                            for payment in package_details['package']['invoicePayments']:
                                payment_id = payment.get('paymentId', 'N/A')
                                payment_method = payment.get('paymentMethod', 'N/A')
                                st.write(f"Payment ID: {payment_id}")
                                st.write(f"Method: {payment_method}")
                    
                    # Guest services section
                    with st.expander("Guest Services", expanded=False):
                        st.markdown("##### Available Services")
                        st.markdown("""
                        - Airport Transfers
                        - Equipment Rentals
                        - Lift Tickets
                        - Lessons
                        """)

if __name__ == "__main__":
    main()
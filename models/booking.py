# -*- coding: utf-8 -*-
# src/components/booking.py

import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union

from utils.booking_viewer_utils import (
    create_cognito_link,
    connect_to_gspread,
    get_cognito_sheet_data,
    get_cognito_info,
    build_css_table,
    # set_management_variable,
    highlight_unpaid,
    # and other functions as needed
)

# Import the CheckInInstructions class - we'll keep this separate
from models.check_in_instructions import CheckInInstructions

@dataclass
class Booking:
    """
    Parses and manages booking data from API response.
    Provides methods to display booking information in various formats.
    """
    def __init__(self, json_response, api_type):
        """Initialize booking with API response data"""
        self.json_response = json_response
        self.booking_id = ""
        self.eId = ""
        self.custom_id = ""
        self.package_gs_list = []
        self.service_guide = self._get_service_guide_url()
        
        # # Initialize property management lists
        # self.set_prop_management_lists()
        
        # Parse API response based on type
        if api_type == "listBooking":
            self._parse_list_booking_response()
        else:
            st.write("Incorrect API type")
    
    def _get_service_guide_url(self):
        """Return the URL for the service guide"""
        return ("https://holidayniseko.com/sites/default/files/2025-05/Holiday%20Niseko%20Guest%20Services%20Guide.pdf")
    
    def set_prop_management_lists(self):
        """Initialize property management lists from configuration files"""
        self.hn_props = set_management_variable([], "hn_props")
        self.vn_props = set_management_variable([], "vn_props")
        self.h2_props = set_management_variable([], "h2_props")
        self.nisade_props = set_management_variable([], "nisade_props")
        self.mnk_props = set_management_variable([], "mnk_props")
        self.hokkaido_travel_props = set_management_variable([], "hokkaido_travel_props")
    
    def _parse_list_booking_response(self):
        """Parse the 'listBooking' API response to extract booking details"""
        # Extract main dictionaries from the response
        self.booking_dict = self.json_response.get("order", {}).get("bookings")
        self.lead_guest_dict = self.json_response.get("order", {}).get("leadGuest", {})
        self.pay_inv_dict = self.json_response.get("order", {}).get("invoicePayments", {})
        
        # Parse guest and invoice dictionaries
        if self.booking_dict is not None:
            self.parse_book_dict()
        
        self.parse_lead_guest(self.lead_guest_dict)
        
        if self.pay_inv_dict:
            self.parse_payment_info(self.pay_inv_dict)

        # Look for ski rental bookings
        self.parse_ski_rental_bookings()

        # Look for Explore transfer bookings
        self.parse_explore_transfer_bookings()
        
        # Create links based on parsed data
        if self.booking_id:
            self._create_booking_links()
        
        # Attribute booking to determine sales channels
        self.attribute_booking()
    
    def _create_booking_links(self):
        """Create various links related to the booking"""
        # RoomBoss launch link
        self.rboss_launch = (
            "https://app.roomboss.com/ui/booking/edit.jsf?bid=" + self.booking_id
        )
        
        # Guest services link
        if hasattr(self, 'eId'):
            self.gsg_link = (
                "https://holidayniseko2.evoke.jp/public/booking/order02"
                ".jsf?mv=1&vs=allservices&bookingEid=" + str(self.eId)
            )
    
    def parse_lead_guest(self, lead_guest_dict):
        """Parse lead guest information from the guest dictionary"""
        self.guest_email = lead_guest_dict.get("email", None)
        self.guest_phone = lead_guest_dict.get("phoneNumber", None)
        self.given_name = lead_guest_dict.get("givenName", None)
        self.family_name = lead_guest_dict.get("familyName", None)
        self.full_name = f"{self.given_name} {self.family_name}"
        self.nationality = lead_guest_dict.get("nationality", None)
        
        # Create payment link if email and eId are available
        if self.guest_email and self.eId:
            self.payment_link = (
                "https://holidayniseko.evoke.jp/public/yourbooking"
                f".jsf?id={self.eId}&em={self.guest_email}"
            )
        else:
            self.payment_link = ""
    
    def parse_book_dict(self):
        """Parse booking dictionary to extract accommodation and service items"""
        for booking in self.booking_dict:
            # Get eId for the booking
            try:
                self.eId = self.json_response.get("order", {}).get("bookings", {})[0].get("eId")
            except Exception as e:
                st.write(e)
            
            # Parse accommodation and service bookings
            if booking.get("bookingType") == "ACCOMMODATION":
                self.parse_accom_item(booking)
            elif booking.get("bookingType") == "SERVICE":
                self.parse_service_item(booking, self.package_gs_list)
    
    def parse_accom_item(self, booking):
        """Parse accommodation item details"""
        # Parse basic booking information
        self.active_check = booking.get("active")
        self.booking_id = booking.get("bookingId")
        self.booking_source = booking.get("bookingSource", {})
        self.created_user = booking.get("createdUser", {})
        self.custom_id = booking.get("customId")
        self.notes = booking.get("notes")
        self.url = booking.get("url")
        
        # Format creation date to local time
        created_date = booking.get("createdDate", {})
        if created_date:
            created_date = pd.to_datetime(created_date) + pd.offsets.Hour(9)
            self.created_date = created_date.strftime("%d-%b-%Y")
        
        self.extent = booking.get("extent", {})
        self.vendor_url = booking.get("hotel", {}).get("hotelUrl", {})
        self.vendor = booking.get("hotel", {}).get("hotelName", {})
        
        # Determine management company
        self._determine_management_company()
        
        # Parse rooms booked
        self.rooms_booked = booking.get("items", {})
        self.room_list_todf = self.parse_room_list2(self.rooms_booked)
    
    def _determine_management_company(self):
        """Determine which company manages the property using property_utils"""
        from utils.property_utils import get_prop_management, match_property_management
        
        # Get property management dictionary
        property_management = get_prop_management()
        
        # Match property to management company
        self.managed_by = match_property_management(self.vendor, property_management)
        
        # If no match found, use a default message
        if self.managed_by == "None":
            self.managed_by = "~ not sure, check roomboss"

    
    def parse_room_list2(self, room_list):
        """
        Parse room details and calculate totals
        Returns a list of room details for display
        """
        rooms_list_todf = []
        self.booking_accom_total = 0
        self.guests = 0
        
        # Loop through each room and extract details
        for room in room_list:
            curr_room_list = []
            
            # Add vendor and room name
            curr_room_list.append(self.vendor)
            room_name = room.get("roomType", {}).get("roomTypeName", {})
            curr_room_list.append(room_name)
            
            # Add check-in and check-out dates
            room_checkin = room.get("checkIn", {}).replace("-", "/")
            curr_room_list.append(room_checkin)
            
            room_checkout = room.get("checkOut", {}).replace("-", "/")
            curr_room_list.append(room_checkout)
            
            # Calculate nights
            nights = (pd.to_datetime(room_checkout) - pd.to_datetime(room_checkin)).days
            curr_room_list.append(nights)
            self.nights = nights
            
            # Add guest count
            room_guests = room.get("numberGuests", {})
            curr_room_list.append(room_guests)
            self.guests += room_guests
            
            # Add room price
            price_retail = room.get("priceSell", {})
            curr_room_list.append(f"¥{price_retail:,.0f}")
            
            # Add to the master list
            rooms_list_todf.append(curr_room_list)
            
            # Add to the total
            self.booking_accom_total += price_retail
        
        # Set the total for the booking
        self.accom_total = self.booking_accom_total
        
        return rooms_list_todf
    
    def parse_service_item(self, booking, package_gs_list):
        """Parse service booking items"""
        gs_items = booking.get("items", {})
        
        for item in gs_items:
            provider = booking.get("serviceProvider", {}).get("serviceProviderName")
            service_name = item.get("service", {}).get("serviceName", {})
            
            start_date = item.get("startDate").replace("-", "/")
            end_date = item.get("endDate").replace("-", "/")
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
            
            price_sell = item.get("priceRetail", {})
            price_sell = f"¥{price_sell:,.0f}"
            
            # Add days to description for Rhythm items
            if provider == "Rhythm Niseko":
                service_name = f"{service_name} - {days} days"
    
    def parse_payment_info(self, pay_inv_dict):
        """Parse payment information into a DataFrame"""
        self.payment_info_df = pd.DataFrame(
            columns=["Invoice", "Created", "Invoiced", "Due", "Paid", 
                     "Date Paid", "Payment ID"]
        )
        
        for invoice in pay_inv_dict:
            invoice_number = invoice.get("invoiceNumber")
            amount = invoice.get("invoiceAmount", {})
            invoice_date = invoice.get("invoiceDate", {})
            invoice_due_date = invoice.get("invoiceDueDate", {})
            payment_amount = invoice.get("paymentAmount", {})
            payment_date = invoice.get("paymentDate", "")
            payment_id = invoice.get("paymentId", {})
            
            pay_line = [invoice_number, invoice_date, amount, invoice_due_date,
                        payment_amount, payment_date, payment_id]
            
            self.payment_info_df.loc[len(self.payment_info_df)] = pay_line
        
        # Calculate totals
        self.amount_invoiced = self.payment_info_df.Invoiced.sum()
        self.amount_received = self.payment_info_df.Paid.sum()
    
    def attribute_booking(self):
        """
        Determine booking source based on Custom ID patterns and booking_source
        Sets booking_source_1 and booking_source_2 attributes
        """
        # Default values
        self.booking_source_1 = "Unknown"
        self.booking_source_2 = "Unknown"
        
        # Make sure we have a custom_id to work with
        if not hasattr(self, 'custom_id'):
            self.custom_id = ""
        
        custom_id = str(self.custom_id) if self.custom_id is not None else ""
        
        # Get booking_source if available
        booking_source = ""
        if hasattr(self, 'booking_source'):
            booking_source = str(self.booking_source) if self.booking_source is not None else ""
        
        # Check for OTAs based on custom_id patterns
        if custom_id:
            # Airbnb - look for 'H' prefix in customId and RoomBoss Channel Manager
            if (custom_id[0] == 'H' and len(custom_id) == 10 and 
                booking_source and "roomboss channel manager" in booking_source.lower()):
                self.booking_source_2 = "Airbnb"
            
            # Booking.com
            elif len(custom_id) == 10 and custom_id[0] != 'H':
                self.booking_source_2 = "Booking.com"
            
            # Expedia - multiple patterns
            elif ((len(custom_id) == 8 and custom_id[0] == '4') or
                (len(custom_id) == 9 and custom_id[0] == '3') or
                (len(custom_id) == 8 and custom_id[0] == '7') or
                (len(custom_id) == 9 and custom_id[0] == '2')):
                self.booking_source_2 = "Expedia"
            
            # Jalan
            elif ((len(custom_id) == 8 and custom_id[0] == '0') or
                custom_id[:2] == '6X' or custom_id[:2] == '6J'):
                self.booking_source_2 = "Jalan"
            
            # Staff bookings
            elif custom_id.lower() in ["d", "ryo", "as", "j", "jj", "ash", "t", "tom", "p", "li"]:
                self.booking_source_1 = "HN Staff"
                self.booking_source_2 = custom_id
        
        # Book & Pay (Direct) - when custom_id is empty
        else:
            self.booking_source_1 = "Book & Pay"
            self.booking_source_2 = "Book & Pay"
        
        # Set Channel1 based on Channel2 for OTAs
        if self.booking_source_2 in ['Airbnb', 'Booking.com', 'Expedia', 'Jalan']:
            self.booking_source_1 = "OTA"
        
        return (self.booking_source_1, self.booking_source_2)
        # UI RENDERING METHODS
    
    def write_key_booking_info(self):
        """Display key booking information"""
        st.markdown(f"##### {self.vendor} #{self.eId}")
        st.markdown(f"###### {self.full_name}")
        st.write(f"Created - {self.created_date} ")

        # Display booking source right after creation date
        # Display booking source right after creation date with color coding
        if hasattr(self, 'booking_source_1') and self.booking_source_1 != "Unknown":
            # Define color mapping for different booking sources
            source_colors = {
                "Airbnb": "#FF5A5F",       # Airbnb red
                "Booking.com": "#003580",   # Booking.com blue
                "Expedia": "#00355F",       # Expedia blue
                "Jalan": "#FF0000",         # Jalan red
                "Book & Pay": "#00A699",    # Teal green
                "HN Staff": "#6B5B95",      # Purple
            }
            
            # Default color for unknown sources
            default_color = "#6B7280"  # Gray
            
            # Determine source text and color
            if hasattr(self, 'booking_source_2') and self.booking_source_2 and self.booking_source_2 != "Unknown" and self.booking_source_1 != self.booking_source_2:
                source_text = f"{self.booking_source_1} - {self.booking_source_2}"
                # Use the color for booking_source_2 if available, otherwise use default
                color = source_colors.get(self.booking_source_2, default_color)
            else:
                source_text = f"{self.booking_source_1}"
                # Use the color for booking_source_1 if available, otherwise use default
                color = source_colors.get(self.booking_source_1, default_color)
            
            # Display the booking source with color coding
            st.markdown(
                f'<div style="display: inline-flex; align-items: center;">'
                f'<strong>Booked via:</strong>&nbsp;'
                f'<span style="background-color: {color}; color: white; '
                f'padding: 2px 8px; border-radius: 10px; font-size: 14px;">{source_text}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.write("---")
        
        # Display management company
        if self.managed_by == 'Holiday Niseko':
            st.write(f"**:green[Managed by Holiday Niseko]**")
        else:
            st.write(f"**:red[Managed by {self.managed_by}]**")
        
        # Display booking status
        if self.active_check:
            st.write(f"**:green[Booking is Active]**")
        else:
            st.write(f":red[Booking is Cancelled]")


        
        
        # Display RoomBoss link
        st.markdown(f"[Open #{self.eId} in RoomBoss]({self.rboss_launch})")
        
        # Display phone number if available
        if self.guest_phone:
            st.write(f":telephone_receiver:", self.guest_phone)
        
        # Display email and payment links if not from booking.com
        try:
            if self.guest_email and "booking.com" not in self.guest_email:
                st.write(f":email: {self.guest_email}")
                st.write("---")
                
                if self.payment_link:
                    st.markdown(f"[View booking details and make payments here]({self.payment_link})")
                    st.markdown(f"[Book your guest services here]({self.gsg_link})")
            elif not self.guest_email or "booking.com" in self.guest_email:
                st.write(f":red[Need to get guest email]")
                st.write("---")
        except TypeError:
            st.write(self.guest_email)
    
    def write_payment_df(self):
        """Display payment information table"""
        # st.markdown("###### Invoices and Payments")
        
        if self.pay_inv_dict:
            # Format dates
            payment_info_df = self.payment_info_df.copy()
            payment_info_df["Created"] = pd.to_datetime(payment_info_df["Created"])
            payment_info_df["Due"] = pd.to_datetime(payment_info_df["Due"])
            payment_info_df["Date Paid"] = pd.to_datetime(payment_info_df["Date Paid"], errors="coerce")
            
            # Apply styling
            st.markdown(
                payment_info_df.style.hide(axis="index")
                .apply(self._highlight_unpaid, axis=1)
                .format({
                    "Created": lambda x: "{}".format(x.strftime("%d %b %Y")),
                    "Due": lambda x: "{}".format(x.strftime("%d %b %Y")),
                    "Date Paid": lambda x: "{}".format(x.strftime("%d %b %Y") if pd.notnull(x) else ''),
                    "Invoiced": "¥{:,.0f}",
                    "Paid": "¥{:,.0f}",
                })
                .set_table_styles([{'selector': 'th', 'props': [('font-size', '10pt'),('text-align','center')]}])
                .set_properties(**{'font-size': '8pt','text-align':'center'})
                .to_html(), 
                unsafe_allow_html=True
            )
    
    def _highlight_unpaid(self, s):
        """Style function for highlighting unpaid invoices"""
        # For non-managed unpaid
        if (s["Paid"] == 0) and (self.managed_by == "Non Managed") and (s.Invoiced > 0):
            return ['background-color: #ffb09c'] * len(s)
        
        # HN Managed not paid
        elif (s["Paid"] == 0) and (self.booking_source_1 != "OTA") and (s.Invoiced > 0):
            return ['background-color: #ffead5'] * len(s)    
        
        # Paid
        else:
            return ['background-color: white'] * len(s)
    
    def write_room_info(self, room_list_todf):
        """
        Display room information in a formatted table
        """
        # Return early if no room data
        if not room_list_todf or len(room_list_todf) == 0:
            st.warning("No room information available.")
            return None
        
        st.markdown(f"###### Room Information")
        
        # Apply CSS for the table
        st.markdown(self._get_room_table_css(), unsafe_allow_html=True)
        
        # Group rooms by property
        rooms_by_property = {}
        for room in room_list_todf:
            property_name = room[0]  # Property is first item
            if property_name not in rooms_by_property:
                rooms_by_property[property_name] = []
            rooms_by_property[property_name].append(room)
        
        # Track check-in and check-out dates for email subject
        all_checkins = []
        all_checkouts = []
        
        # For each property, create a table with all its rooms
        for property_name, rooms in rooms_by_property.items():
            table_html = self._build_room_table_html(property_name, rooms)
            
            # Collect dates for email subject
            for room in rooms:
                all_checkins.append(room[2])  # Check-in is third item
                all_checkouts.append(room[3])  # Check-out is fourth item
            
            # Output the table
            st.markdown(table_html, unsafe_allow_html=True)
        
        # Set min check-in and max check-out dates
        if all_checkins:
            self.accom_checkin = min(all_checkins)
        if all_checkouts:
            self.accom_checkout = max(all_checkouts)
        
        return None
    
    def _get_room_table_css(self):
        """Return CSS for room table styling"""
        return """
            <style>
            .table-wrapper {
                border: 1px solid #e0e0e0;
                border-top: 4px solid #0C8C3C;
                background: white;
                padding: 0;
                margin: 0 0 20px 0;
                white-space: nowrap;
                overflow-x: auto;
                max-width: 100%;
                display: inline-block;
            }
            .single-room-table {
                width: 350px;
                border-collapse: collapse;
                font-size: 14px;
            }
            .multi-room-table {
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
                text-align: left;
            }
            .booking-id {
                color: #000000;
                font-size: 14px;
                margin: 0 0 10px 0;
            }
            .property-row th {
                font-weight: 500;
                color: #333;
                background: #f8f8f8;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
            th {
                width: 130px;
                font-weight: 500;
                color: #333;
                background: #f8f8f8;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
            td {
                background: white;
                padding: 10px;
                border: 1px solid #e0e0e0;
                text-align: center;
            }
            </style>
        """
    
    def _build_room_table_html(self, property_name, rooms):
        """Build HTML for room table"""
        # Determine table class based on room count
        table_class = "single-room-table" if len(rooms) == 1 else "multi-room-table"
        
        # Start building the table
        table_html = f"""
        <div class="table-wrapper">
            <table class="{table_class}">
                <tr class="header-row">
                    <td colspan="{len(rooms) + 1}" class="header-cell" style="text-align: left; padding-left: 20px;">
                        <div class="booking-id"><strong>Booking ID: #{self.eId}</strong></div>
                    </td>
                </tr>
                <tr class="property-row">
                    <th>Property</th>
                    <th colspan="{len(rooms)}">{property_name}</th>
                </tr>
                <tr>
                    <th>Room</th>
        """
        
        # Add room names
        for room in rooms:
            table_html += f'<td>{room[1]}</td>'  # Room name is second item
        
        # Add check-in dates
        table_html += """
                </tr>
                <tr>
                    <th>Check-in</th>
        """
        for room in rooms:
            checkin_raw = room[2]  # Check-in is third item
            # Format date
            try:
                checkin_date = pd.to_datetime(checkin_raw)
                formatted_checkin = checkin_date.strftime('%b %d, %Y')
            except:
                formatted_checkin = checkin_raw  # Keep original if parsing fails
            table_html += f'<td>{formatted_checkin}</td>'
        
        # Add check-out dates
        table_html += """
                </tr>
                <tr>
                    <th>Check-out</th>
        """
        for room in rooms:
            checkout_raw = room[3]  # Check-out is fourth item
            # Format date
            try:
                checkout_date = pd.to_datetime(checkout_raw)
                formatted_checkout = checkout_date.strftime('%b %d, %Y')
            except:
                formatted_checkout = checkout_raw  # Keep original if parsing fails
            table_html += f'<td>{formatted_checkout}</td>'
        
        # Add nights
        table_html += """
                </tr>
                <tr>
                    <th>Nights</th>
        """
        for room in rooms:
            table_html += f'<td>{room[4]}</td>'  # Nights is fifth item
        
        # Add guests
        table_html += """
                </tr>
                <tr>
                    <th>Guests</th>
        """
        for room in rooms:
            table_html += f'<td>{room[5]}</td>'  # Guests is sixth item
        
        # Add rates only if managed by Holiday Niseko
        # if self.managed_by == "Holiday Niseko":
        table_html += """
                </tr>
                <tr>
                    <th>Rate</th>
        """
        for room in rooms:
            table_html += f'<td>{room[6]}</td>'  # Rate is seventh item
    
        # Close the table
        table_html += """
                </tr>
            </table>
        </div>
        """
        
        return table_html
    
    def write_email_subject(self):
        """Display the email subject line"""
        if hasattr(self, 'email_subject_line'):
            st.write(self.email_subject_line)
        else:
            # Fallback if email_subject_line hasn't been set
            subject_line = f"{self.vendor} Booking #{self.eId}"
            st.write(subject_line)

    
    def write_notes(self):
        """Display booking notes if available"""
        if self.notes:
            st.markdown(f"###### Notes")
            st.markdown(self.notes)
    
    def write_cognito(self):
        """
        Check and display if customer has completed Cognito online check-in
        """
        # Skip if not managed by Holiday Niseko
        if self.managed_by != "Holiday Niseko":
            front_desk_manual_link = "https://docs.google.com/document/d/1-R1zBxcY9sBP_ULDc7D0qaResj9OTU2s/r/edit/edit#heading=h.rus25g7i893t"
            st.markdown(f"**Don't send Holiday Niseko online check-in** [FD MANUAL]({front_desk_manual_link})")
            return
        
        # Get Cognito data
        df = get_cognito_sheet_data()
        cognito_entry = get_cognito_info(str(self.eId), df)
        
        # Initialize values
        eId = "-"
        phone = "-"
        arv = "-"
        
        # Extract data if available
        try:
            eId = cognito_entry["HolidayNisekoReservationNumber"].values[0]
        except Exception:
            pass
        
        try:
            phone = cognito_entry["Phone"].values[0]
        except Exception:
            pass
        
        try:
            arv = cognito_entry["ExpectedArrivalTimeInNiseko"].values[0] + " " + \
                  cognito_entry["ArrivingInNisekoBy"].values[0]
        except IndexError:
            pass
        
        # Determine if Cognito is completed
        if eId == "-":
            cognito_done = "No"
            # Create check-in link if not completed
            link = create_cognito_link(
                reservation_number=self.eId,
                check_in=self.accom_checkin,
                check_out=self.accom_checkout,
                accommodation=self.vendor,
                first_name=self.given_name,
                last_name=self.family_name,
                email=self.guest_email
            )
            st.write(f"[Online Check-in Link]({link})")
        else:
            cognito_done = "Yes"
        
        # Display Cognito info
        build_css_table(eId, phone, arv, cognito_done)
    
    def write_days_to_checkin(self):
        """Calculate and display days until check-in or until check-out"""
        try:
            date_checkin = pd.to_datetime(self.accom_checkin).normalize()  # Set to midnight
            date_checkout = pd.to_datetime(self.accom_checkout).normalize()
            today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # Set to midnight
            
            days_to_checkin = (date_checkin - today).days
            days_after_checkout = (date_checkout - today).days

            # Check-in scenarios
            if days_to_checkin > 0:
                st.write(f"{days_to_checkin} days until check-in")
            elif days_to_checkin == 0:
                st.write("Check-in is today")
            else:
                # Already checked in, handle check-out scenarios
                if days_after_checkout < 0:
                    st.write(f"Checked out {abs(days_after_checkout)} days ago")
                elif days_after_checkout == 0:
                    st.write("Check-out is today!")
                else:
                    st.write(f"Currently staying: {days_after_checkout+1} days until check-out")
        except Exception as e:
            st.error(f"Error calculating check-in days: {str(e)}")



    def write_invoice_sentences(self):
        """Write the invoices, due dates and payment link in a simple format"""
        invoices_expander = st.expander("Invoices", expanded=False)

        if self.payment_link and hasattr(self, 'pay_inv_dict'):
            for invoice in self.pay_inv_dict:
                if invoice["paymentAmount"] == 0:
                    with invoices_expander:
                        st.markdown(
                            f"Your payment of ¥{invoice['invoiceAmount']:,.0f} \
                            is due by \
                            {pd.to_datetime(invoice['invoiceDueDate']).strftime('%B %d, %Y')}.")
                        
                        st.markdown(
                            f"[You can view your booking details and make payments here]({self.payment_link})")

    def write_overdue_email(self):
        """Write a template for an overdue payment email"""
        invoices_expander = st.expander("Overdue Payment", expanded=False)

        with invoices_expander:
            st.write(
            f"""
            Holiday Niseko Payment Required - Reservation #{self.eId}

            Hi {self.given_name},  

            I hope this email finds you well. This is a friendly reminder that 
            we have not yet received payment for your upcoming accommodation at {self.vendor}.

            Please note that your reservation will be automatically canceled in 
            48 hours if payment is not received.  
            
            You can complete your payment securely through the following link:  
            <a href='{self.payment_link}'> View invoices and make payments here </a>   

            If you have already processed the payment or wish to cancel your 
            booking, please let us know immediately.  

            Should you have any questions or concerns, our team is here to help.
            
            """,
            unsafe_allow_html=True)

    def write_gsg_upsell(self):
        """Write template for guest service upsell"""
        try: 
            if not self.guest_email or "booking.com" in self.guest_email:
                return

            gs_upsell_expander = st.expander("GS Upsell", expanded=False)
            with gs_upsell_expander:
                st.write(f"""
Accommodation is booked - now add your extras!""") 
                
                st.write("""
- Equipment Rentals – Early bird rates available  
- Airport Transfers 
- Ski/Snowboard Lessons
- Lift Passes
""")
                
                st.write(f"""

<a href='{"https://holidayniseko.com/my-booking"}'> Book Your Extras Now **→** </a>  

**Login Details**  
Email: {self.guest_email}  
Booking ID: {self.eId} 

Check out our <a href='{self.service_guide}'> Guest Services Guide</a> for full pricing and service details.

*Book your extras early - popular services fill up fast!*
                """,
                    unsafe_allow_html=True)
        except TypeError:
            return

    def write_OTA_email(self):
        """Write the OTA email template after they contact us"""
        try:
            if not self.guest_email or "booking.com" in self.guest_email:
                return

            ota_email_expander = st.expander("OTA Email", expanded=False)
            with ota_email_expander:
                st.write(f"""
                
                Hi {self.given_name},  

                Thank you for getting back to us. We have linked your email and you can now book private transfers, rentals and more!

                <a href='{self.gsg_link}'> Book your guest services here</a>  

                For pricing and options, please see our <a href='{self.service_guide}'> Guest Services Guide</a>.

                View your booking details and make payments here:  
                <a href='{self.payment_link}'> View booking details</a>  
                
                What's Next? Our front desk team will contact you closer to your check-in date with:

                - Arrival instructions
                - Online check-in link
                - Guest registration forms  

                

                We look forward to welcoming you to Niseko soon!
                
                
                """,
                    unsafe_allow_html=True)
        except TypeError:
            return

    def write_first_ota_email(self):
        """Write the initial OTA email before guest registers email"""
        # Skip if email already registered
        if hasattr(self, 'guest_email') and (self.guest_email and "booking.com" not in self.guest_email):
            return

        try:
            ota_email_expander = st.expander(
                "First OTA message in app - Before guest registers email",
                expanded=False)
            
            with ota_email_expander:
                st.markdown(f"""
                
                Hi {self.given_name},  

                Thank you for your booking. We're Holiday Niseko, the local property manager for your accommodation.

                To receive your door codes and check-in details, please confirm your email address here:
                https://holidayniseko.com/email/{self.eId}

                By doing so, you'll unlock access to:  
                -- Your door codes and entry instructions  
                -- Online check-in  
                -- Our local support team  
                -- Book airport transfers, lift tickets, ski rentals, and more  

                This essential step is required for accessing your accommodation and our services.

                If you have any concerns, please contact us at res@holidayniseko.com
                    
                    
                """,
                        unsafe_allow_html=True)
        except TypeError:
            return

    def write_second_OTA_email(self):
        """Write the second OTA email after guest registers their email"""
        try:
            if not self.guest_email or "booking.com" in self.guest_email:
                return

            ota_email_expander = st.expander(
                "Second OTA Email - After guest registers email",
                expanded=False)
            
            with ota_email_expander:
                st.write(f"""
                        
                Access Your Holiday Niseko Booking - Reservation #{self.eId}
                
                Hi {self.given_name},  

                Thank you for registering your email. Your MyBooking page is now ready.

                Access MyBooking here: https://holidayniseko.com/my-booking/  
                Your Reservation ID: {self.eId}

                To log in, simply enter your email address and reservation ID shown above.

                On MyBooking, you can: 
                - View door codes and check-in instructions
                - Book guest services (airport transfers, lift tickets, etc) - Popular services book quickly
                - Complete online check-in 

                Questions? Contact us anytime. 

                We look forward to welcoming you to Niseko!

                """,
                    unsafe_allow_html=True)
        except TypeError:
            return



    def write_booking_confirmation(self):
        """Write the booking confirmation with multiple rooms in a single table with columns"""
        try: 
            if not self.guest_email or "booking.com" in self.guest_email:
                return
                
            bk_confirmation_expander = st.expander(
                f"Booking Confirmation #{self.eId}",
                expanded=False)
            
            with bk_confirmation_expander:
                # CSS styling - FIXED TEXT WRAPPING
                st.markdown("""
                    <style>
                    /* Remove the problematic nowrap rules that prevent text wrapping */
                    .streamlit-expanderContent {
                        white-space: normal !important;
                    }
                    .element-container {
                        white-space: normal !important;
                    }
                    
                    /* Add proper text wrapping for all text content */
                    .booking-text-content {
                        white-space: normal;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        max-width: 100%;
                        line-height: 1.5;
                    }
                    
                    /* Responsive table wrapper */
                    .table-wrapper {
                        border: 1px solid #e0e0e0;
                        border-top: 4px solid #0C8C3C;
                        background: white;
                        padding: 0;
                        margin: 0 0 1.25rem 0;
                        white-space: nowrap;
                        overflow-x: auto;
                        max-width: 100%;
                        display: inline-block;
                        width: auto;
                        -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
                    }
                    
                    /* Responsive table sizing */
                    .single-room-table {
                        width: 100%;
                        min-width: 350px;
                        max-width: 500px;
                        border-collapse: collapse;
                        font-size: 0.875rem;
                    }
                    
                    .multi-room-table {
                        width: 100%;
                        min-width: 600px;
                        border-collapse: collapse;
                        font-size: 0.875rem;
                    }
                    
                    .header-row {
                        background: white;
                        border-bottom: 1px solid #e0e0e0;
                    }
                    
                    .header-cell {
                        padding: 0.9375rem;
                        color: #333;
                        text-align: left;
                    }
                    
                    .booking-id {
                        color: #000000;
                        font-size: 0.875rem;
                        margin: 0 0 0.625rem 0;
                    }
                    
                    .login-button {
                        display: inline-block;
                        background-color: #FFB800;
                        color: #000000;
                        padding: 0.375rem 0.75rem;
                        text-decoration: none;
                        border-radius: 0.25rem;
                        font-weight: 600;
                        font-size: 0.8125rem;
                        min-height: 2.25rem; /* Touch target size */
                        line-height: 1.5;
                    }
                    
                    .property-row th {
                        font-weight: 500;
                        color: #333;
                        background: #f8f8f8;
                        padding: 0.625rem;
                        border: 1px solid #e0e0e0;
                    }
                    
                    .multi-room-table th {
                        width: 8.125rem;
                        min-width: 6rem;
                        font-weight: 500;
                        color: #333;
                        background: #f8f8f8;
                        padding: 0.625rem;
                        border: 1px solid #e0e0e0;
                    }
                    
                    .multi-room-table td {
                        background: white;
                        padding: 0.625rem;
                        border: 1px solid #e0e0e0;
                        text-align: center;
                    }
                    
                    /* Mobile responsive styles */
                    @media (max-width: 768px) {
                        .booking-text-content {
                            font-size: 0.9375rem;
                            line-height: 1.4;
                        }
                        
                        .table-wrapper {
                            margin: 0 0 1rem 0;
                            border-radius: 0.25rem;
                        }
                        
                        .single-room-table {
                            min-width: 320px;
                            font-size: 0.8125rem;
                        }
                        
                        .multi-room-table {
                            min-width: 480px;
                            font-size: 0.8125rem;
                        }
                        
                        .header-cell {
                            padding: 0.75rem;
                            font-size: 0.875rem;
                        }
                        
                        .booking-id {
                            font-size: 0.8125rem;
                        }
                        
                        .login-button {
                            padding: 0.5rem 0.875rem;
                            font-size: 0.75rem;
                            min-height: 2.75rem; /* Larger touch target on mobile */
                        }
                        
                        .property-row th,
                        .multi-room-table th,
                        .multi-room-table td {
                            padding: 0.5rem 0.375rem;
                            font-size: 0.75rem;
                        }
                        
                        .multi-room-table th {
                            min-width: 4.5rem;
                        }
                    }
                    
                    /* Extra small screens */
                    @media (max-width: 480px) {
                        .booking-text-content {
                            font-size: 0.875rem;
                        }
                        
                        .single-room-table {
                            min-width: 280px;
                            font-size: 0.75rem;
                        }
                        
                        .multi-room-table {
                            min-width: 400px;
                            font-size: 0.75rem;
                        }
                        
                        .header-cell {
                            padding: 0.625rem;
                            font-size: 0.8125rem;
                        }
                        
                        .login-button {
                            font-size: 0.6875rem;
                            padding: 0.5rem 0.75rem;
                        }
                        
                        .property-row th,
                        .multi-room-table th,
                        .multi-room-table td {
                            padding: 0.375rem 0.25rem;
                            font-size: 0.6875rem;
                        }
                        
                        .multi-room-table th {
                            min-width: 3.5rem;
                        }
                    }
                    </style>
                """, unsafe_allow_html=True)

                # Header section - WRAPPED IN TEXT CONTENT DIV
                st.markdown(f"""
                <div class="booking-text-content">
                            
                Booking Confirmation #{self.eId} - {self.vendor}<br>
                                    
                Hi {self.given_name},<br>

                Thank you for choosing Holiday Niseko! We're delighted to confirm your booking with us.<br>
                
                Please take a moment to review your booking confirmation below.<br>
                
                <strong>To secure your booking a 20% non-refundable deposit is required within 3 days</strong>
                </div>
                """, unsafe_allow_html=True)

                # Group rooms by booking to display them together
                self._render_booking_tables()
                
                # Footer section - WRAPPED IN TEXT CONTENT DIV
                st.markdown(f"""
                <div class="booking-text-content">
                <strong>Payment Information</strong>
                <ul>
                    <li>Initial deposit: 20% (due within 3 days)</li>
                    <li>Final balance: Due 60 days before check-in</li>
                </ul>
                
                <a href="https://holidayniseko.evoke.jp/public/yourbooking.jsf?id={self.eId}&em={self.guest_email}">Pay securely in your local currency here</a><br>

                <strong>Important Links</strong>
                <ul>
                    <li><a href="https://holidayniseko.com/terms-and-conditions"> Terms and Conditions</a></li>
                    <li><a href="https://holidayniseko.com/faq">Frequently Asked Questions</a></li>
                    <li><a href="https://holidayniseko.com/my-booking">Login to MyBooking - Check details, entry instructions, location and more </a></li>
                </ul>

                <em>We recommend securing travel insurance to protect your booking.</em>
                </div>
                """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"Error in write_booking_confirmation: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


    def _render_booking_tables(self):
        """Helper method to render booking tables for confirmation"""
        bookings_with_rooms = {}
        
        for booking in self.booking_dict:
            if booking.get('bookingType') == 'ACCOMMODATION':
                booking_id = booking.get('eId', '')
                vendor = booking.get('hotel', {}).get('hotelName', '')
                
                # Create URL-encoded parameters for the my-booking link
                from urllib.parse import urlencode
                params = {
                    'email': self.guest_email,
                    'reservation_eid': booking_id
                }
                
                # Create the URL with parameters
                my_booking_url = f"https://holidayniseko.com/my-booking"
                
                # Extract all rooms for this booking
                rooms = []
                for room in booking.get('items', []):
                    rooms.append({
                        'room_name': room.get('roomType', {}).get('roomTypeName', ''),
                        'check_in': pd.to_datetime(room.get('checkIn', '')).strftime('%b %d, %Y'),
                        'check_out': pd.to_datetime(room.get('checkOut', '')).strftime('%b %d, %Y'),
                        'nights': (pd.to_datetime(room.get('checkOut', '')) - pd.to_datetime(room.get('checkIn', ''))).days,
                        'guests': room.get('numberGuests', 0),
                        'rate': f"¥{room.get('priceSell', 0):,.0f}"
                    })
                
                bookings_with_rooms[booking_id] = {
                    'vendor': vendor,
                    'rooms': rooms,
                    'my_booking_url': my_booking_url
                }
        
        # Generate tables for each booking
        for booking_id, booking_data in bookings_with_rooms.items():
            rooms = booking_data['rooms']
            vendor = booking_data['vendor']
            my_booking_url = booking_data['my_booking_url']
            
            if not rooms:
                continue
            
            # Start table - use single-room-table class if only one room
            table_class = "single-room-table" if len(rooms) == 1 else "multi-room-table"
            table_html = f"""
            <div class="table-wrapper">
                <table class="{table_class}">
                    <tr class="header-row">
                        <td colspan="{len(rooms) + 1}" class="header-cell" style="text-align: left; padding-left: 20px;">
                            <div class="booking-id">Booking ID: {booking_id}</div>
                            <a href="{my_booking_url}" class="login-button">Login to MyBooking</a>
                        </td>
                    </tr>
                    <tr class="property-row">
                        <th>Property</th>
                        <th colspan="{len(rooms)}">{vendor}</th>
                    </tr>
                    <tr>
                        <th>Room</th>
            """
            
            # Add room name cells
            for room in rooms:
                table_html += f'<td>{room["room_name"]}</td>'
            
            # Continue with the rest of the rows
            table_html += """
                    </tr>
                    <tr>
                        <th>Check-in</th>
            """
            
            for room in rooms:
                table_html += f'<td>{room["check_in"]}</td>'
            
            table_html += """
                    </tr>
                    <tr>
                        <th>Check-out</th>
            """
            
            for room in rooms:
                table_html += f'<td>{room["check_out"]}</td>'
            
            table_html += """
                    </tr>
                    <tr>
                        <th>Nights</th>
            """
            
            for room in rooms:
                table_html += f'<td>{room["nights"]}</td>'
            
            table_html += """
                    </tr>
                    <tr>
                        <th>Guests</th>
            """
            
            for room in rooms:
                table_html += f'<td>{room["guests"]}</td>'
            
            # Only show rate row if it's Holiday Niseko managed
            # if self.managed_by == "Holiday Niseko":
            table_html += """
                    </tr>
                    <tr>
                        <th>Rate</th>
            """
            
            for room in rooms:
                table_html += f'<td>{room["rate"]}</td>'
        
            # Close the table
            table_html += """
                    </tr>
                </table>
            </div>
            """
            
            # Output the complete table
            st.markdown(table_html, unsafe_allow_html=True)

    def write_checkin_instructions(self):
        """Write check-in instructions for the accommodation"""
        try:
            if not hasattr(self, '_checkin_instructions'):
                from src.components.check_in_instructions import CheckInInstructions
                self._checkin_instructions = CheckInInstructions()
            
            if not hasattr(self, 'vendor'):
                st.warning("Unable to find property information for check-in instructions")
                return
            
            # Get the first room's name
            room_name = None
            if hasattr(self, 'rooms_booked') and self.rooms_booked:
                first_room = self.rooms_booked[0]
                if isinstance(first_room, dict) and 'roomType' in first_room:
                    room_type = first_room.get('roomType', {})
                    if isinstance(room_type, dict):
                        room_name = room_type.get('roomTypeName')
            
            # Write the instructions
            self._checkin_instructions.write_instructions(self.vendor, room_name)
            
        except Exception as e:
            st.error(f"Error in write_checkin_instructions: {str(e)}")
            import traceback
            st.write("Full error traceback:")
            st.code(traceback.format_exc())

    # In your Booking class, add this method:
    def get_email_subject(self):
        """Generate email subject line without writing to UI"""
        if hasattr(self, 'accom_checkin') and hasattr(self, 'accom_checkout'):
            return (
                f"{self.vendor} Booking #{self.eId} ~  "
                f"{self.accom_checkin} - {self.accom_checkout} "
                f"({self.nights} nights) {self.guests} guests"
            )
        else:
            # Fallback for when the check-in/out dates aren't available yet
            return f"{self.vendor} Booking #{self.eId}"
        
    def display_processed_rooms(self):
        """Display room tables without reprocessing data"""
        # Skip if no room data
        if not self.room_list_todf or len(self.room_list_todf) == 0:
            st.warning("No room information available.")
            return None
        
        # Apply CSS for the table
        st.markdown(self._get_room_table_css(), unsafe_allow_html=True)
        
        # Group rooms by property
        rooms_by_property = {}
        for room in self.room_list_todf:
            property_name = room[0]  # Property is first item
            if property_name not in rooms_by_property:
                rooms_by_property[property_name] = []
            rooms_by_property[property_name].append(room)
        
        # For each property, create a table with all its rooms
        for property_name, rooms in rooms_by_property.items():
            table_html = self._build_room_table_html(property_name, rooms)
            
            # Output the table
            st.markdown(table_html, unsafe_allow_html=True)
        
        return None
    
    # REPLACE the ski rental methods in your booking.py with these:

    def parse_ski_rental_bookings(self):
        """Parse ski rental bookings - one email per Rhythm booking"""
        self.ski_rentals = []
        
        for booking in self.booking_dict:
            if booking.get("bookingType") == "SERVICE":
                # Check if this is a Rhythm service provider (ski rental)
                service_provider = booking.get("serviceProvider", {}).get("serviceProviderName", "")
                
                if "rhythm" in service_provider.lower():
                    # Create one rental entry per Rhythm booking
                    rental_entry = {
                        'booking_id': booking.get("eId", ""),
                        'service_provider': service_provider,
                        'booking_notes': booking.get("notes", ""),
                        'items': [],
                        'start_date': None,
                        'end_date': None
                    }
                    
                    # Get all items and find date range
                    start_dates = []
                    end_dates = []
                    
                    for item in booking.get("items", []):
                        rental_item = {
                            'service_name': item.get("service", {}).get("serviceName", ""),
                            'category': item.get("category", ""),
                            'parent_category': item.get("parentCategory", ""),
                            'price': item.get("priceRetail", 0),
                            'start_date': item.get("startDate", ""),
                            'end_date': item.get("endDate", "")
                        }
                        rental_entry['items'].append(rental_item)
                        
                        if rental_item['start_date']:
                            start_dates.append(rental_item['start_date'])
                        if rental_item['end_date']:
                            end_dates.append(rental_item['end_date'])
                    
                    # Set overall date range for this rental booking
                    if start_dates:
                        rental_entry['start_date'] = min(start_dates)
                    if end_dates:
                        rental_entry['end_date'] = max(end_dates)
                    
                    # Calculate total price
                    rental_entry['total_price'] = sum(item['price'] for item in rental_entry['items'])
                    
                    self.ski_rentals.append(rental_entry)

    def has_ski_rentals(self):
        """Check if this booking includes ski rentals"""
        if not hasattr(self, 'ski_rentals'):
            self.parse_ski_rental_bookings()
        return len(self.ski_rentals) > 0
    
    def write_ski_rental_confirmation_emails(self):
        """Generate styled ski rental confirmation emails – one per Rhythm booking"""
        if not self.has_ski_rentals():
            return

        for rental in self.ski_rentals:
            with st.expander(f"Rhythm Rental Confirmation #{rental['booking_id']}", expanded=False):
                rental_id = rental['booking_id']
                payment_link = self.payment_link
                guest_name = self.given_name

                html_content = f"""
    <div style="max-width: 720px; margin: 0 auto; font-family: Arial, sans-serif; font-size: 14px; color: #333;">
    <p>Hi {guest_name},</p>
    <p>
    Thank you for booking your rentals through Holiday Niseko!<br><br>
    Your booking is confirmed – please review the details below.
    </p>

<!-- Booking Details -->
<div style="background-color: #eaf6ff; border-left: 4px solid #009645; padding: 16px; border-radius: 6px; width: 100%;">
    <h3 style="font-size: 16px; margin-bottom: 10px; color: #009645;">📋 Your Booking Details</h3>
    <div style="background-color: #009645; color: white; padding: 10px 16px; display: inline-block; border-radius: 4px;">
    <strong>Rental Booking Reference: {rental_id}</strong>
    </div>
    <p style="margin-top: 16px;">Please check your booking details in the attached PDF.</p>
    <p style="margin: 8px 0;"><strong>Pickup Time:</strong> From 1:00 PM the day before your rental start date</p>
    <p style="margin: 8px 0;"><strong>Location:</strong> <a href="https://maps.app.goo.gl/wix4MrqG4uYhSAkQ9" style="color: #009645;">Rhythm Niseko Rental Shop</a></p>
</div>

<!-- Payment Info -->
<div style="background-color: #fff3cd; border-radius: 6px; padding: 16px; margin-top: 24px; width: 100%;">
    <h3 style="font-size: 16px; margin-bottom: 10px;">💳 Payment Information</h3>
    <p><strong>Payment Due:</strong> 60 days before your check-in date</p>
    <p>
    <a href="{payment_link}" style="background-color: #ffc107; color: #000000; padding: 10px 20px; text-decoration: none; border-radius: 20px; font-weight: bold; display: inline-block; margin-top: 10px;">Complete Payment</a>
    </p>
    <p style="margin-top: 10px;">You can view your booking and make payments anytime using the link above.</p>
</div>

<!-- Cancellation Policy -->
<div style="background-color: #f8f9fa; border-radius: 6px; padding: 16px; margin-top: 24px; width: 100%;">
    <h3 style="font-size: 16px; margin-bottom: 10px;">Cancellation Policy</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <thead>
        <tr style="background-color: #f4f4f4;">
        <th style="border: 1px solid #ddd; padding: 10px; text-align: center;">Cancellation Timing</th>
        <th style="border: 1px solid #ddd; padding: 10px; text-align: center;">Refund Policy</th>
        </tr>
    </thead>
    <tbody>
        <tr>
        <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">More than 48 hours before rental</td>
        <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">Full refund provided</td>
        </tr>
        <tr>
        <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">Less than 48 hours before rental</td>
        <td style="border: 1px solid #ddd; padding: 10px; text-align: center;">No cash refund – store credit issued for equal value (valid at participating stores in Japan for current season only)</td>
        </tr>
    </tbody>
    </table>
</div>

<p style="margin-top: 20px;">We look forward to seeing you in Niseko!</p>
</div>
    """
                st.markdown(html_content, unsafe_allow_html=True)



    def _render_ski_rental_table(self, rental):
        """Render ski rental items in a properly formatted HTML table."""
        table_html = f"""
        <style>
            .ski-rental-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
                margin: 20px 0;
            }}
            .ski-rental-table th, .ski-rental-table td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: center;
            }}
            .ski-rental-table th {{
                background-color: #f4f4f4;
                font-weight: bold;
            }}
        </style>
        <table class="ski-rental-table">
            <thead>
                <tr>
                    <th>Equipment</th>
                    <th>Category</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
        """

        for item in rental['items']:
            table_html += f"""
                <tr>
                    <td>{item['service_name']}</td>
                    <td>{item['category']}</td>
                    <td>¥{item['price']:,.0f}</td>
                </tr>
            """

        table_html += """
            </tbody>
        </table>
        """

        st.markdown(table_html, unsafe_allow_html=True)




    def display_ski_rental_summary(self):
        """Display a summary of ski rentals in the main booking view"""
        # Remove this method entirely - we don't want the details in the left column
        pass


    def parse_explore_transfer_bookings(self):
        """Parse Explore transfer bookings - one email per transfer booking"""
        self.explore_transfers = []
        
        for booking in self.booking_dict:
            if booking.get("bookingType") == "SERVICE":
                # Check if this is an Explore Transfers & Tours service provider
                service_provider = booking.get("serviceProvider", {}).get("serviceProviderName", "")
                
                if "explore" in service_provider.lower():
                    # Create one transfer entry per Explore booking
                    transfer_entry = {
                        'booking_id': booking.get("eId", ""),
                        'service_provider': service_provider,
                        'booking_notes': booking.get("notes", ""),
                        'items': [],
                        'pickup_locations': []
                    }
                    
                    # Parse the notes to extract important information
                    notes = booking.get("notes", "")
                    if notes:
                        # Extract information from notes
                        lines = notes.split('\n')
                        transfer_entry['google_maps_link'] = ""
                        transfer_entry['contact_info'] = {}
                        
                        for line in lines:
                            if "google.com/maps" in line:
                                # Extract Google Maps link
                                import re
                                url_match = re.search(r'https://[^\s]+', line)
                                if url_match:
                                    transfer_entry['google_maps_link'] = url_match.group(0)
                            elif "LAST NAME:" in line:
                                transfer_entry['contact_info']['last_name'] = line.split(":", 1)[1].strip()
                            elif "FIRST NAME:" in line:
                                transfer_entry['contact_info']['first_name'] = line.split(":", 1)[1].strip()
                            elif "EMAIL:" in line:
                                transfer_entry['contact_info']['email'] = line.split(":", 1)[1].strip()
                            elif "TELEPHONE:" in line:
                                transfer_entry['contact_info']['phone'] = line.split(":", 1)[1].strip()
                    
                    # Get all transfer items
                    for item in booking.get("items", []):
                        transfer_item = {
                            'service_name': item.get("service", {}).get("serviceName", ""),
                            'category': item.get("category", ""),
                            'parent_category': item.get("parentCategory", ""),
                            'price': item.get("priceRetail", 0),
                            'start_date': item.get("startDate", ""),
                            'end_date': item.get("endDate", "")
                        }
                        
                        # Parse transfer type and route from service name
                        service_name = transfer_item['service_name']
                        if "Airport(CTS) to Niseko" in service_name:
                            transfer_item['route'] = "Airport → Niseko"
                            transfer_item['pickup_location'] = "New Chitose Airport"
                        elif "Niseko to Airport(CTS)" in service_name:
                            transfer_item['route'] = "Niseko → Airport"
                            transfer_item['pickup_location'] = "Your Accommodation"
                        else:
                            # Handle other routes
                            transfer_item['route'] = service_name.replace("Private Transfer - ", "")
                            transfer_item['pickup_location'] = "TBD"
                        
                        transfer_entry['items'].append(transfer_item)
                    
                    # Calculate total price
                    transfer_entry['total_price'] = sum(item['price'] for item in transfer_entry['items'])
                    
                    self.explore_transfers.append(transfer_entry)

    def has_explore_transfers(self):
        """Check if this booking includes Explore transfers"""
        if not hasattr(self, 'explore_transfers'):
            self.parse_explore_transfer_bookings()
        return len(self.explore_transfers) > 0

    def write_explore_transfer_confirmation_emails(self):
        """Generate styled transfer confirmation emails – one per Explore booking"""
        if not self.has_explore_transfers():
            return

        for transfer in self.explore_transfers:
            with st.expander(f"Explore Transfer Confirmation #{transfer['booking_id']}", expanded=False):
                transfer_id = transfer['booking_id']
                payment_link = self.payment_link if hasattr(self, 'payment_link') else "#"
                guest_name = self.given_name
                
                # Build the transfer details table
                transfer_table_html = self._build_explore_transfer_table(transfer)
                
                html_content = f"""
<div style="max-width: 720px; margin: 0 auto; font-family: Arial, sans-serif; font-size: 14px; color: #333;">

<!-- Header with Logo -->
<div style="margin-bottom: 40px; text-align: center;">
<div style="display: inline-block; background-color: #000; border-radius: 50%; padding: 20px;">
<div style="width: 80px; height: 80px; display: flex; align-items: center; justify-content: center;">
<svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="40" cy="40" r="30" fill="#87CEEB"/>
<ellipse cx="40" cy="50" rx="26" ry="12" fill="#90EE90"/>
<path d="M20 45 L30 30 L40 35 L50 25 L60 45 Z" fill="#2F4F2F"/>
<text x="40" y="65" font-family="Arial, sans-serif" font-size="8" font-weight="bold" fill="white" text-anchor="middle">EXPLORE</text>
<text x="40" y="73" font-family="Arial, sans-serif" font-size="6" font-weight="bold" fill="white" text-anchor="middle">NISEKO</text>
</svg>
</div>
</div>
<h1 style="color: #333; margin: 20px 0 0 0; font-size: 24px;">Explore Niseko Transfer Confirmation</h1>
</div>

<p>Hi {guest_name},</p>
<p>Thank you for booking your transfers with Explore Niseko through Holiday Niseko! Your booking is confirmed.</p>

<!-- Booking Details Table -->
<div style="margin: 20px 0 0 0; padding: 0 20px 0 25px; border-left: 8px solid #27ae60;">
<h3 style="color: #333; margin: 15px 0; font-size: 16px;">Transfer Details</h3>
{transfer_table_html}
</div>

<!-- Payment Section -->
<div style="margin: 35px 0; padding: 20px; background-color: #f8f9fa; border-radius: 6px;">
<h3 style="font-size: 16px; margin-bottom: 10px;">💳 Payment Information</h3>
<p><strong>Payment Due:</strong> 60 days before your check-in date</p>
<p>
<a href="{payment_link}" style="background: #1e90ff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-top: 10px;">Make a payment / View invoices</a>
</p>
</div>

<!-- Transfer Instructions -->
<div style="margin: 35px 0; padding: 20px 0 0 0; border-top: 1px solid #e9ecef;">
<h3 style="color: #333; margin-top: 0; font-size: 16px;">Transfer Instructions</h3>
<div style="display: flex; gap: 30px; margin-top: 20px;">
<div style="flex: 1;">
<h4 style="color: #333; margin: 0 0 8px 0; font-size: 14px;">✈️ Airport Pickup</h4>
<p style="margin: 0; font-size: 13px;">Your driver will be waiting at the arrival gate with a sign displaying your name. Can't find them?<br>Call <strong>(+81) 050-5309-6905</strong></p>
</div>
<div style="flex: 1;">
<h4 style="color: #333; margin: 0 0 8px 0; font-size: 14px;">🏠 From Your Accommodation</h4>
<p style="margin: 0; font-size: 13px;">Your driver will be waiting outside your accommodation at the scheduled pickup time.</p>
</div>
</div>
</div>

<!-- Cancellation Policy -->
<div style="margin: 35px 0 0 0; padding: 20px 0 0 0; border-top: 1px solid #e9ecef;">
<h3 style="color: #333; margin-top: 0; font-size: 16px;">📋 Cancellation Policy</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px;">
<tr>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333;">Time until Transfer</th>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333;">Policy</th>
</tr>
<tr>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">More than 72 hours prior</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">Full refund given</td>
</tr>
<tr>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">72 to 48 hours prior</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">50% refund - ¥5000 administration fee</td>
</tr>
<tr>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">Less than 48 hours prior</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; font-size: 12px;">No refund given</td>
</tr>
</table>
</div>

<!-- Footer -->
<div style="margin-top: 40px;">
<h4 style="color: #333; margin: 0 0 10px 0; font-size: 14px;">✈️ Flight Delays</h4>
<p style="margin: 0; font-size: 13px; color: #666;">Your driver will wait for delayed flights when possible. In cases where it is not, alternative transportation arrangements may be needed, as such travel insurance is recommended.</p>

<p style="margin: 20px 0; font-size: 13px; color: #666;">We look forward to seeing you in Niseko!</p>

<div style="margin-top: 30px;">
<p style="margin: 5px 0; font-size: 13px;">Kind regards,</p>
<p style="margin: 15px 0 5px 0; font-size: 14px; font-weight: bold;">The Explore Niseko Team</p>
<p style="margin: 0; font-size: 13px; color: #666;">Holiday Niseko Guest Services</p>
</div>
</div>
</div>
    """
                st.markdown(html_content, unsafe_allow_html=True)

    def _build_explore_transfer_table(self, transfer):
        """Build the HTML table for transfer details"""
        table_html = """
<table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px;">
<thead>
<tr>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333; width: 20%;">Date & Route</th>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333; width: 25%;">Pickup Location</th>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333; width: 20%;">Time</th>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333; width: 20%;">Vehicle</th>
<th style="color: #333; padding: 10px 8px; text-align: left; font-weight: bold; font-size: 12px; border-bottom: 2px solid #333; width: 15%;">Price</th>
</tr>
</thead>
<tbody>
        """
        
        for item in transfer['items']:
            # Format date
            try:
                transfer_date = pd.to_datetime(item['start_date'])
                formatted_date = transfer_date.strftime('%b %d')
            except:
                formatted_date = item['start_date']
            
            # Determine pickup time based on route (you may need to adjust this based on actual data)
            pickup_time = "TBD"  # This should come from the booking notes or another field
            
            table_html += f"""
<tr>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 12px;">
<span style="font-weight: bold; color: #333;">{formatted_date}</span>
<div style="font-size: 11px; color: #666; margin-top: 2px;">{item['route']}</div>
</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 12px;">
<span style="font-weight: bold; color: #333;">{item['pickup_location']}</span>
</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 12px;">
<span style="font-weight: bold; color: #333;">{pickup_time}</span>
</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 12px;">
<span style="font-weight: bold; color: #333;">Private Vehicle</span>
</td>
<td style="padding: 10px 8px; border-bottom: 1px solid #ecf0f1; vertical-align: top; font-size: 12px;">
<span style="font-weight: bold; color: #333;">¥{item['price']:,.0f}</span>
</td>
</tr>
            """
        
        table_html += """
</tbody>
</table>
        """
        
        return table_html
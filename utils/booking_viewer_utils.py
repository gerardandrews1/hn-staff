# utils/booking_viewer_utils.py

import datetime
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from urllib.parse import quote

def create_cognito_link(reservation_number, check_in, check_out, accommodation, first_name, last_name, email):
    """
    Create a pre-filled Cognito form URL with booking information.
    
    Args:
        reservation_number: Booking ID/reservation number
        check_in: Check-in date (string)
        check_out: Check-out date (string)
        accommodation: Property name
        first_name: Guest's first name
        last_name: Guest's last name
        email: Guest's email address
        
    Returns:
        Formatted URL string for Cognito form
    """
    # Replace special characters
    formatted_email = email.replace('@', '%40')
    formatted_accommodation = accommodation.replace(' ', '%20')
    formatted_first_name = first_name.replace(' ', '%20').strip()
    formatted_last_name = last_name.replace(' ', '%20').strip()
    
    # Format dates to ensure they use hyphens in the URL
    formatted_check_in = check_in.replace('/', '-')
    formatted_check_out = check_out.replace('/', '-')
    
    # Base Cognito form URL
    base_url = "https://www.cognitoforms.com/HolidayNiseko/HolidayNisekoOnlineCheckinGuestRegistration"
    
    # Create entry data dictionary
    entry_data = {
        "HolidayNisekoReservationNumber": reservation_number,
        "CheckinDate": formatted_check_in,
        "CheckoutDate": formatted_check_out,
        "Accommodation": formatted_accommodation,
        "LeadGuestFirstName": formatted_first_name,
        "LeadGuestLastName": formatted_last_name,
        "Email": formatted_email
    }
    
    # Create the entry parameter
    entry = "%7B"  # Opening curly brace in URL encoding
    for i, (key, value) in enumerate(entry_data.items()):
        if i > 0:
            entry += "%2C"  # Comma in URL encoding
        entry += f'%22{key}%22%3A%22{value}%22'  # Key and value with quotes
    entry += "%7D"  # Closing curly brace in URL encoding
    
    return f"{base_url}?entry={entry}"

def connect_to_gspread():
    """
    Connect to Google Sheets API using credentials from Streamlit secrets.
    
    Returns:
        Authorized gspread client
    """
    # Define scopes for Google APIs
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']

    # Get credentials from Streamlit secrets
    credentials_dict = {
        "type": st.secrets["general"]["type"],
        "project_id": st.secrets["general"]["project_id"],
        "private_key_id": st.secrets["general"]["private_key_id"],
        "private_key": st.secrets["general"]["private_key"],
        "client_email": st.secrets["general"]["client_email"],
        "client_id": st.secrets["general"]["client_id"],
        "auth_uri": st.secrets["general"]["auth_uri"],
        "token_uri": st.secrets["general"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["general"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["general"]["client_x509_cert_url"]
    }

    # Create credentials object
    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scope
    )

    # Return authorized client
    return gspread.authorize(credentials)

def get_cognito_sheet_data():
    """
    Fetch Cognito form submission data from Google Sheets.
    
    Returns:
        DataFrame with Cognito form data
    """
    try:
        # Connect to Google Sheets
        gc = connect_to_gspread()

        # Open spreadsheet and worksheet
        spreadsheet = gc.open("All Bookings")
        worksheet = spreadsheet.get_worksheet(2)
        
        # Read data
        data = worksheet.get_all_values()
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        
        return df
    except Exception as e:
        st.error(f"Error fetching Cognito data: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def get_cognito_info(ebook_id, df):
    """
    Find a specific booking's Cognito information.
    
    Args:
        ebook_id: Booking ID to search for
        df: DataFrame containing Cognito data
        
    Returns:
        Filtered DataFrame with matching booking
    """
    result = df.loc[df["HolidayNisekoReservationNumber"] == ebook_id]
    return result

def build_css_table(eId, phone, arv_time, cognito_done):
    """
    Build and display a styled HTML table with Cognito information.
    
    Args:
        eId: Booking ID
        phone: Guest phone number
        arv_time: Expected arrival time
        cognito_done: Whether Cognito form is completed
    """
    if phone == "":
        phone = "-"
    
    # Custom CSS for the table
    css = f"""
            <style>
            .booking-table {{
                width: 100%;
                border-collapse: collapse;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}

            .booking-table th {{
                background-color: #f8f8f8;
                padding: 12px 8px;
                text-align: left;
                border-bottom: 2px solid #2B7A33;
                width: 40%;
            }}

            .booking-table td {{
                padding: 12px 8px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}

            .status {{
                padding: 2px 8px;
                border-radius: 12px;
                background-color: #FFD700;
            }}

            .reference {{
                color: #2B7A33;
                font-weight: 500;
            }}
            </style>

            <table class="booking-table">
                <tr>
                    <th>Cognito Completed</th>
                    <td><span class="reference">{cognito_done}</span></td>
                </tr>
                <tr>
                    <th>&#128222</th>
                    <td>{phone}</td>
                </tr>
                <tr>
                    <th>Expected arrival time Niseko</th>
                    <td>{arv_time}</td>
                </tr>
            </table>    
            """
            
    st.markdown(css, unsafe_allow_html=True)

def highlight_unpaid(s):
    """
    Style function for highlighting unpaid invoices in DataFrames.
    Updated to use consistent red warning color.
    
    Args:
        s: DataFrame row
        
    Returns:
        List of CSS styles for each cell in the row
    """
    # For unpaid invoices - use consistent red warning color matching the updated system
    if (s["Paid"] == 0) and (s["Invoiced"] > 0):
        # Using red color that matches Streamlit error/warning styling with stronger visual impact
        return ['background-color: #fee2e2; border-left: 4px solid #dc2626; color: #7f1d1d; font-weight: 500'] * len(s)
    
    # Paid invoices - clean white background
    else:
        return ['background-color: white; color: #374151'] * len(s)

def format_currency(amount, currency="¥"):
    """Format a number as currency with thousands separators"""
    return f"{currency}{amount:,.0f}"

def format_date(date_str, output_format="%d %b %Y"):
    """Format a date string to a standardized format"""
    try:
        date_obj = pd.to_datetime(date_str)
        return date_obj.strftime(output_format)
    except:
        return date_str

def calculate_nights(check_in, check_out):
    """Calculate number of nights between check-in and check-out"""
    try:
        check_in_date = pd.to_datetime(check_in)
        check_out_date = pd.to_datetime(check_out)
        return (check_out_date - check_in_date).days
    except:
        return 0
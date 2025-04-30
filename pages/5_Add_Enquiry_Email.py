import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime, timedelta
import numpy as np

# Set up the page configuration
st.set_page_config(page_title="Add Enquiry Email", layout="wide")

# Define the scope and create credentials
def create_gsheet_connection():
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Create credentials from the service account JSON file
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["general"],
        scopes=scope
    )
    
    # Authorize the client
    client = gspread.authorize(credentials)
    
    return client

# Get all data from the Google Sheet
def get_sheet_data():
    client = create_gsheet_connection()
    sheet = client.open(st.secrets["gcp_service_account"]["form_sheet_name_enquiries"]).sheet1
    
    # Get all data including headers
    data = sheet.get_all_records()
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    return df

# Check if email exists in the sheet
def email_exists(email):
    if not email:  # Skip check if email is empty
        return False
        
    df = get_sheet_data()
    
    # If the DataFrame is empty or doesn't have an Email column
    if df.empty or 'Email' not in df.columns:
        return False
    
    # Check if email exists (case insensitive)
    return df['Email'].str.lower().isin([email.lower()]).any()

# Open the Google Sheet and append data
def append_to_gsheet(data_dict):
    # Connect to Google Sheets
    client = create_gsheet_connection()
    
    # Open the Google Sheet by its title
    sheet = client.open(st.secrets["gcp_service_account"]["form_sheet_name_enquiries"]).sheet1
    
    # Convert dictionary to a list of values
    row_data = list(data_dict.values())
    
    # Append the data to the sheet
    sheet.append_row(row_data)
    
    return True

# Calculate email statistics
def get_email_stats():
    df = get_sheet_data()
    
    # Handle empty DataFrame or one without required columns
    if df.empty or 'Email' not in df.columns or 'Timestamp' not in df.columns:
        return {
            'total_unique': 0,
            'last_7_days': 0,
            'month_to_date': 0
        }
    
    # Ensure Timestamp is datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    
    # Calculate total unique emails
    total_unique = df['Email'].dropna().str.strip().str.lower().nunique()
    
    # Last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    last_7_days = df[df['Timestamp'] >= seven_days_ago]['Email'].dropna().str.strip().str.lower().nunique()
    
    # Month to date
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1)
    month_to_date = df[df['Timestamp'] >= month_start]['Email'].dropna().str.strip().str.lower().nunique()
    
    return {
        'total_unique': total_unique,
        'last_7_days': last_7_days,
        'month_to_date': month_to_date
    }

# Display email statistics
def show_email_stats():
    stats = get_email_stats()
    
    st.subheader("Email Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Unique Emails", stats['total_unique'])
    
    with col2:
        st.metric("New Last 7 Days", stats['last_7_days'])
    
    with col3:
        st.metric("New This Month", stats['month_to_date'])

# Get the most recent entries
def get_recent_entries(n=10):
    df = get_sheet_data()
    
    if df.empty:
        return pd.DataFrame()
    
    # Try to convert timestamp to datetime for proper sorting
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df = df.sort_values('Timestamp', ascending=False)
    
    # Return the top n rows
    return df.head(n)

# Main title
st.title("Record enquiry email address information")

# Create two columns layout
left_col, right_col = st.columns([1, 1])

# Form in the left column
with left_col:
    st.write("Please fill out the form below and hit submit to send to Google Sheets.")
    
    # Use Streamlit's form container
    with st.form(key="data_form"):
        # Form fields - customize these based on your requirements
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        country = st.text_input("Country")
        comments = st.text_area("Comments")
        
        # Add a timestamp field (hidden from the user)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Submit button
        submit_button = st.form_submit_button(label="Submit Data")
    
    # Handle form submission outside the form but after the form is defined
    if submit_button:
        # Check if at least one field has data
        has_data = bool(first_name or last_name or email or phone or country or comments)
        
        if not has_data:
            st.error("Please fill in at least one field before submitting.")
        elif email and email_exists(email):
            st.warning(f"The email '{email}' already exists in the database. You can still submit to update the information.")
            
            # Create a dictionary with the form data
            form_data = {
                "Timestamp": timestamp,
                "First Name": first_name,
                "Last Name": last_name,
                "Email": email,
                "Phone": phone,
                "Country": country,
                "Comments": comments
            }
            
            # Add confirmation button for duplicate email
            if st.button("Submit Anyway"):
                with st.spinner("Submitting data..."):
                    try:
                        success = append_to_gsheet(form_data)
                        if success:
                            st.success("Thank you! Your data has been submitted successfully.")
                            st.write("Submitted data:")
                            st.write(pd.DataFrame([form_data]))
                            # Use st.rerun() instead of experimental_rerun
                            st.rerun()
                        else:
                            st.error("Something went wrong. Please try again.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.write("Please check your Google Sheets connection settings.")
        else:
            # Create a dictionary with the form data
            form_data = {
                "Timestamp": timestamp,
                "First Name": first_name,
                "Last Name": last_name,
                "Email": email,
                "Phone": phone,
                "Country": country,
                "Comments": comments
            }
            
            # Show a spinner while processing
            with st.spinner("Submitting data..."):
                try:
                    # Append the data to Google Sheets
                    success = append_to_gsheet(form_data)
                    
                    if success:
                        # Show success message
                        st.success("Thank you! Your data has been submitted successfully.")
                        
                        # Optional: Display the submitted data
                        st.write("Submitted data:")
                        st.write(pd.DataFrame([form_data]))
                    else:
                        st.error("Something went wrong. Please try again.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    st.write("Please check your Google Sheets connection settings.")

# Statistics and data display in the right column
with right_col:
    # Display stats at the top
    show_email_stats()
    
    # Add some space
    st.markdown("---")
    
    # Display recent entries
    st.subheader("Most Recent Entries")
    recent_df = get_recent_entries(5)
    if not recent_df.empty:
        st.dataframe(recent_df, use_container_width=True)
    else:
        st.info("No entries found in the sheet.")
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
from typing import Dict, List, Any
import requests
import json

# Add root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from models.hotel import RbAvailableHotel
from utils.property_utils import get_prop_management

# Page configuration
st.set_page_config(
    page_title="Search & Quote",
    page_icon="🔍",
    layout="wide"
)

class RoomBossAPI:
    """RoomBoss API client for hotel availability search"""
    def __init__(self):
        try:
            self.auth = (st.secrets["roomboss"]["api_id"], st.secrets["roomboss"]["api_key"])
        except KeyError:
            st.error("""
                Missing API credentials. Please set up your secrets.toml file with:
                [roomboss]
                api_id = "your_api_id"
                api_key = "your_api_key"
            """)
            st.stop()
            
        self.base_url = "https://api.roomboss.com/extws/hotel/v1"

    def get_hotel_list(self, country_code: str = "jp", location_code: str = "niseko") -> List[str]:
        """Get list of hotel IDs"""
        url = f"{self.base_url}/list?countryCode={country_code}&locationCode={location_code}"
        response = requests.get(url, auth=self.auth)
        json_data = json.loads(response.text)
        
        hotel_ids = [f"&hotelId={hotel['hotelId']}" for hotel in json_data.get("hotels", [])]
        
        # Split into chunks of 100 for API limit
        hotel_ids_one = hotel_ids[0:100]
        hotel_ids_two = hotel_ids[100:]
        
        # Convert list to string
        hotel_ids_string_one = "".join(hotel_ids_one)
        hotel_ids_string_two = "".join(hotel_ids_two)
        
        return [hotel_ids_string_one, hotel_ids_string_two]

    def get_available_stays(
        self,
        hotel_ids_list: List[str],
        checkin: str,
        checkout: str,
        guests: str
    ) -> List[Dict]:
        """Get available stays"""
        resp_lists = []
        for id_list in hotel_ids_list:
            api_list_avail = (
                f"{self.base_url}/listAvailable?1&"
                f"checkIn={checkin}&checkOut={checkout}&"
                f"numberGuests={guests}&excludeConditionsNotMet&"
                f"rate=ota&locationCode=NISEKO&countryCode=JP{id_list}"
            )
            
            avail_hotels = requests.get(api_list_avail, auth=self.auth)
            resp_dict = json.loads(avail_hotels.text)
            # Debug: Print raw response
            print("Raw API Response:", resp_dict)  # Add this line for debugging
            resp_lists.append(resp_dict)
            
        return resp_lists

    def get_rate_plan_descriptions(self, hotel_ids: List[str]) -> Dict:
        """Get rate plan descriptions for specified hotels"""
        # Filter out empty strings from hotel IDs
        hotel_ids = [hotel_id for hotel_id in hotel_ids if hotel_id]
        
        if not hotel_ids:
            return {}
        
        # Build the URL with multiple hotelId parameters
        params = "&".join([f"hotelId={hotel_id}" for hotel_id in hotel_ids])
        url = f"{self.base_url}/listRatePlanDescription?{params}"
        
        try:
            response = requests.get(url, auth=self.auth)
            
            if response.status_code != 200:
                st.warning(f"Failed to fetch rate plan descriptions: {response.status_code}")
                return {}
            
            # Parse response and organize by hotel ID
            rate_plans_data = json.loads(response.text)
            
            # Organize data by hotel ID for easier access
            organized_data = {}
            for hotel_data in rate_plans_data:
                vendor_id = hotel_data.get('vendorId')
                if vendor_id:
                    rate_plan_dict = {}
                    for rate_plan in hotel_data.get('ratePlanDescriptionList', []):
                        rate_plan_id = rate_plan.get('ratePlanId')
                        if rate_plan_id:
                            rate_plan_dict[rate_plan_id] = {
                                'name_en': rate_plan.get('names', {}).get('en', ''),
                                'name_ja': rate_plan.get('names', {}).get('ja', ''),
                                'desc_en': rate_plan.get('descriptions', {}).get('en', ''),
                                'desc_ja': rate_plan.get('descriptions', {}).get('ja', ''),
                                'long_desc_en': rate_plan.get('longDescriptions', {}).get('en', ''),
                                'long_desc_ja': rate_plan.get('longDescriptions', {}).get('ja', '')
                            }
                    organized_data[vendor_id] = rate_plan_dict
                    
            return organized_data
            
        except Exception as e:
            st.error(f"Error fetching rate plan descriptions: {str(e)}")
            return {}


def generate_booking_link(hotel_id, room_type_id, checkin_date, checkout_date, nights, guests):
    """
    Generate a booking link for the Holiday Niseko booking system
    
    Args:
        hotel_id (str): Hotel ID from the API
        room_type_id (str): Room Type ID from the API
        checkin_date (str): Check-in date in YYYYMMDD format
        checkout_date (str): Check-out date in YYYYMMDD format
        nights (int): Number of nights
        guests (str or int): Number of guests
    
    Returns:
        str: Complete booking URL
    """
    base_url = "https://holiday-niseko.evoke.jp/search/listing"
    
    # Build the URL
    booking_url = (
        f"{base_url}/{hotel_id}?"
        f"rtid={room_type_id}&"
        f"ci={checkin_date}&"
        f"co={checkout_date}&"
        f"n={nights}&"
        f"g={guests}&"
        f"sv=1&"
        f"utm_source=search_tool&utm_medium=internal&utm_campaign=booking"
    )
    
    return booking_url


def add_booking_links_to_dataframe(df, checkin_date, checkout_date, nights, guests_input):
    """
    Add booking links to the results dataframe
    
    Args:
        df (pd.DataFrame): Results dataframe
        checkin_date (str): Check-in date in YYYYMMDD format
        checkout_date (str): Check-out date in YYYYMMDD format
        nights (int): Number of nights
        guests_input (str): Number of guests
    
    Returns:
        pd.DataFrame: DataFrame with booking links added
    """
    df_with_links = df.copy()
    
    # Generate booking links for each row
    booking_links = []
    for idx, row in df_with_links.iterrows():
        hotel_id = row.get('Hotel ID', '')
        room_type_id = row.get('Room Type ID', '')
        
        if hotel_id and room_type_id and hotel_id != 'N/A' and room_type_id != 'N/A':
            link = generate_booking_link(
                hotel_id, 
                room_type_id, 
                checkin_date, 
                checkout_date, 
                nights, 
                guests_input
            )
            booking_links.append(link)
        else:
            booking_links.append('')
    
    df_with_links['Booking Link'] = booking_links
    
    return df_with_links


def init_session_state():
    """Initialize session state variables"""
    if "nights" not in st.session_state:
        st.session_state.nights = 0
        
    if "stays" not in st.session_state:
        st.session_state.stays = pd.DataFrame(
            columns=["Room ID", "Price", "Rate Plan", "Bedrooms", "Bathrooms",
                    "Max Guests", "Quant Avail", "Hotel Name",
                    "Room Name", "Managed By"]
        )
    
    if "checkin_dt" not in st.session_state:
        st.session_state.checkin_dt = None
        
    if "checkout_dt" not in st.session_state:
        st.session_state.checkout_dt = None

# This is a modification to make in your process_search_results function
# to ensure the Hotel ID is preserved when creating the stays_dict

def process_search_results(
    api: RoomBossAPI,
    checkin: str,
    checkout: str,
    guests: str,
    management_dict: Dict
) -> pd.DataFrame:
    """Process search results and return DataFrame"""
    # Get hotel list and available stays
    with st.spinner("Searching available properties..."):
        hotel_ids_list = api.get_hotel_list()
        resp_lists = api.get_available_stays(
            hotel_ids_list,
            checkin,
            checkout,
            guests
        )

    # Process results
    stays_dict = {}
    hotel_ids_used = set()  # New: Track unique hotel IDs
    
    for response in resp_lists:
        for hotel in response.get("availableHotels", []):
            # Store the Hotel ID for later reference
            hotel_id = hotel.get('hotelId', 'N/A')
            hotel_ids_used.add(hotel_id)  # New: Add to set of used hotel IDs
            
            avail_hotel = RbAvailableHotel(hotel, management_dict)
            for room_id, avail_room in avail_hotel.avail_rooms.items():
                # Add Hotel ID to each room's data
                room_data = {**avail_room, 'Room ID': room_id, 'Hotel ID': hotel_id}
                stays_dict[room_id] = room_data
    
    # New: Store the hotel IDs for later use
    st.session_state.hotel_ids_used = list(hotel_ids_used)
    
    return pd.DataFrame(stays_dict).T


def create_price_plot(df, x_jitter, x_positions, x_labels, grouped_data, primary_group, show_trends=True):
    """Create price distribution plot with trend lines"""
    above_threshold = df[df['Price'] > 2500000]
    above_count = len(above_threshold)
    above_text = f"{above_count} properties above ¥2,500,000" if above_count > 0 else ""
    
    fig = px.scatter(df,
                    x="Price",
                    title="Price Distribution " + above_text,
                    size=[8] * len(df),
                    opacity=0.7,
                    custom_data=['Room', 'Room ID', 'Price', 'Per Night', 'Rate Plan'])
    
    # Remove the capping of values - this is the key change
    # Instead of capping, we'll display all values at their true amount
    plot_df = df.copy()
    
    fig.update_traces(
        y=x_jitter,
        x=plot_df['Price'],
        marker=dict(
            size=8,
            line=dict(width=0.5, color='darkblue'),
        ),
        hovertemplate=(
            "%{customdata[0]}<br>" +
            "Room ID: %{customdata[1]}<br>" +
            "Rate Plan: %{customdata[4]}<br>" +
            "¥%{customdata[2]:,.0f} (¥%{customdata[3]:,.0f}/night)" +
            "<extra></extra>"
        )
    )
    
    # Calculate a better x-axis range that accommodates all prices
    max_price = df['Price'].max()
    x_axis_max = max_price * 1.1
    
    fig.update_layout(
        height=max(400, len(x_labels) * 35),
        yaxis_title=None,
        xaxis_title="Price (¥)",
        showlegend=True,
        plot_bgcolor='white',
        margin=dict(l=180, r=50, t=50, b=50),
        yaxis=dict(
            ticktext=x_labels,
            tickvals=x_positions,
            tickangle=0,
            gridcolor='lightgrey',
            automargin=True,
            dtick=1,
            showgrid=False,
            side='left',
            domain=[0, 0.95],
            position=0.02
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            tickformat=',.0f',
            range=[-20000, x_axis_max],  # Adjusted to accommodate all values
            showgrid=True
        )
    )
    
    fig.update_traces(
        marker=dict(
            size=10,
            line=dict(width=1, color='darkblue'),
            symbol='circle',
            opacity=0.7
        )
    )
    
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=False)
    
    return fig


def create_per_night_plot(df, x_jitter, x_positions, x_labels, grouped_data, primary_group, show_trends=True):
    """Create per night price distribution plot with trend lines"""
    per_night_threshold = 300000
    above_threshold_night = df[df['Per Night'] > per_night_threshold]
    above_count_night = len(above_threshold_night)
    above_text_night = f"{above_count_night} properties above ¥300,000/night" if above_count_night > 0 else ""
    
    fig2 = px.scatter(df,
                     x="Per Night",
                     title="Price per Night Distribution " + above_text_night,
                     size=[8] * len(df),
                     opacity=0.7,
                     custom_data=['Room', 'Room ID', 'Price', 'Per Night', 'Rate Plan'])
    
    # Remove the capping of values - show all values at their true amount
    plot_df_night = df.copy()
    
    fig2.update_traces(
        y=x_jitter,
        x=plot_df_night['Per Night'],
        marker=dict(
            size=8,
            line=dict(width=0.5, color='darkblue'),
        ),
        hovertemplate=(
            "%{customdata[0]}<br>" +
            "Room ID: %{customdata[1]}<br>" +
            "Rate Plan: %{customdata[4]}<br>" +
            "¥%{customdata[2]:,.0f} (¥%{customdata[3]:,.0f}/night)" +
            "<extra></extra>"
        )
    )
    
    # Calculate a better x-axis range that accommodates all prices
    max_per_night = df['Per Night'].max()
    x_axis_max = max_per_night * 1.1
    
    fig2.update_layout(
        height=max(400, len(x_labels) * 35),
        yaxis_title=None,
        xaxis_title="Price per Night (¥)",
        showlegend=True,
        plot_bgcolor='white',
        margin=dict(l=100, r=50, t=50, b=50),
        yaxis=dict(
            ticktext=x_labels,
            tickvals=x_positions,
            tickangle=0,
            gridcolor='lightgrey',
            automargin=True,
            dtick=1,
            showgrid=False,
            side='left'
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            tickformat=',.0f',
            range=[-2000, x_axis_max],  # Adjusted to accommodate all values
            showgrid=True
        )
    )
    
    fig2.update_xaxes(showgrid=True)
    fig2.update_yaxes(showgrid=False)
    
    return fig2



def handle_sidebar_inputs():
    """Handle all sidebar inputs and filtering options"""
    with st.sidebar:
        st.title("Search Options")
        
        checkin_input = st.text_input("Check-in").replace("-", "")
        checkout_input = st.text_input("Check-out").replace("-", "")
        guests_input = st.text_input("Number of guests")
        
        search_col = st.button("Search & Quote", type="primary")
        
        st.write("")
        st.write("---")
        st.write("")
        
        bed_bath_list = ["-All", 1, 2, 3, 4, 5, 6, 7, 8]
        bedrooms = st.multiselect(
            "Filter by bedrooms",
            options=bed_bath_list,
            default="-All"
        )
        
        # Management company selection
        if "stays" in st.session_state:
            management_list = sorted(list(set(st.session_state.stays["Managed By"].tolist())))
            if "None" in management_list:
                management_list.remove("None")
            management_list = ["-All"] + management_list + ["None"]
            
            management = st.multiselect(
                "Filter management company",
                options=management_list,
                default="-All"
            )
        else:
            management = []
        
        unbookable_list = [
            "SnowDog Village",
            "Suiboku",
            "Always Niseko",
            "Roku"
        ]
        
        exclude = st.multiselect(
            "Include all properties",
            options=["Yes", "No"],
            default=["No"]
        )
        
        exclude_list = [] if "Yes" in exclude else unbookable_list
        
        # Add the checkbox for showing only lowest prices
        show_lowest_prices = st.checkbox("Show only lowest price per accommodation")
        
        # Add a separator before the exclude rate plans option
        st.write("")
        st.write("---")
        
        # Add rate plan exclusion dropdown - moved to the bottom
        exclude_rate_plans = []
        if "stays" in st.session_state:
            try:
                # Convert all Rate Plan values to string first to avoid the .str accessor error
                rate_plan_strings = st.session_state.stays["Rate Plan"].astype(str)
                
                # Extract rate plan types (part after the dash)
                rate_plan_types = []
                for plan in rate_plan_strings:
                    if '-' in plan:
                        # Split on the first dash and take the second part
                        parts = plan.split('-', 1)
                        if len(parts) > 1:
                            rate_plan_types.append(parts[1].strip())
                    else:
                        # Handle cases with no dash
                        rate_plan_types.append(plan)
                
                # Create a list of unique rate plan types
                unique_rate_plans = ["-None"] + sorted(list(set(rate_plan_types)))
                
                exclude_rate_plans = st.multiselect(
                    "Exclude rate plans",
                    options=unique_rate_plans,
                    # default="HN Early Bird",
                    help="Select rate plans to exclude from results"
                )
                # Remove "-None" from the list if it's the only item
                if "-None" in exclude_rate_plans and len(exclude_rate_plans) > 1:
                    exclude_rate_plans.remove("-None")
                # If only "-None" is selected, make it an empty list
                if exclude_rate_plans == ["-None"]:
                    exclude_rate_plans = []
            except Exception as e:
                st.warning(f"Could not process rate plans: {str(e)}")
                exclude_rate_plans = []
        
        return checkin_input, checkout_input, guests_input, search_col, bedrooms, management, exclude_list, exclude_rate_plans, show_lowest_prices


def filter_results(
    df: pd.DataFrame,
    bedrooms: List[int],
    management: List[str],
    exclude_list: List[str],
    exclude_rate_plans: List[str]
) -> pd.DataFrame:
    """Filter results based on user selections"""
    # Apply filters
    if bedrooms and "-All" not in bedrooms:
        df = df[df["Bedrooms"].isin(bedrooms)]
    
    if management and "-All" not in management:
        df = df[df["Managed By"].isin(management)]
    
    # Exclude properties
    if exclude_list:
        df = df[~df["Hotel Name"].isin(exclude_list)]
    
    # Exclude rate plans - with safer filtering
    if exclude_rate_plans:
        # Make a copy of the DataFrame to avoid modification warnings
        df_filtered = df.copy()
        
        # Convert Rate Plan column to string for consistent filtering
        df_filtered["Rate Plan"] = df_filtered["Rate Plan"].astype(str)
        
        # Filter out entries that match any of the excluded rate plans
        for rate_plan in exclude_rate_plans:
            pattern = f"- {rate_plan}$|^{rate_plan}$|{rate_plan}$"
            df_filtered = df_filtered[~df_filtered["Rate Plan"].str.contains(pattern, regex=True, na=False)]
        
        df = df_filtered
    
    # Add additional columns
    df["hotel_room_name"] = df["Hotel Name"] + " " + df["Room Name"]
    
    # Calculate commission
    df["Commission"] = np.where(
        df["Managed By"] == "HN",
        df.Price * 0.25,
        df.Price * 0.2
    )
    df["Commission"] = df["Commission"].astype(int)
    
    # Calculate per night price
    if st.session_state.nights > 0:
        df["Per Night"] = (df["Price"] / st.session_state.nights).astype(int)
    
    # Make sure we have Hotel ID and Room Type ID columns preserved
    if "Hotel ID" not in df.columns and "hotelId" in df.columns:
        df["Hotel ID"] = df["hotelId"]
    
    df = df.reset_index(names=["Room"])
    return df.sort_values(by=["Price", "Room"])


def calculate_plot_positions(filtered_df, grouped, primary_group, secondary_group):
    x_positions = []
    x_labels = []
    current_pos = 0
    
    unique_management = filtered_df[primary_group].unique()
    single_company = len(unique_management) == 1
    
    for group in sorted(filtered_df[primary_group].unique()):
        group_data = grouped[grouped[primary_group] == group]
        num_subgroups = len(group_data)
        
        for i, row in enumerate(group_data.iterrows()):
            x_positions.append(current_pos + (i * 0.8))
            management = str(group).strip()
            rate_plan = row[1].iloc[1]
            rooms = int(row[1]['Quant Avail'])
            
            if single_company:
                property_name = rate_plan.split('-')[0].strip()
                x_labels.append(f"{property_name}\n({rooms} rooms)")
            else:
                x_labels.append(f"{management} - {rate_plan}\n({rooms} rooms)")
        
        current_pos += (num_subgroups * 0.8) + 1.5
    
    x_jitter = []
    for idx, row in filtered_df.iterrows():
        pos_idx = grouped[
            (grouped[primary_group] == row[primary_group]) & 
            (grouped[secondary_group] == row[secondary_group])
        ].index[0]
        base_pos = x_positions[pos_idx]
        x_jitter.append(base_pos + np.random.uniform(-0.05, 0.05))
    
    return x_positions, x_labels, x_jitter

def main():
    """Main function for Search & Quote page"""
    init_session_state()
    api = RoomBossAPI()
    management_dict = get_prop_management()
    
    header_container = st.container()
    results_container = st.container()
    
    # Get all inputs from sidebar (now including show_lowest_prices)
    checkin_input, checkout_input, guests_input, search_col, bedrooms, management, exclude_list, exclude_rate_plans, show_lowest_prices = handle_sidebar_inputs()
    
    if search_col:
        try:
            st.session_state.checkin_dt = datetime.strptime(checkin_input, "%Y%m%d")
            st.session_state.checkout_dt = datetime.strptime(checkout_input, "%Y%m%d")
            st.session_state.nights = (
                st.session_state.checkout_dt - st.session_state.checkin_dt
            ).days
            
            # Store the search parameters for booking links
            st.session_state.checkin_input = checkin_input
            st.session_state.checkout_input = checkout_input
            st.session_state.guests_input = guests_input
            
            results_df = process_search_results(
                api,
                checkin_input,
                checkout_input,
                guests_input,
                management_dict
            )
            
            st.session_state.stays = results_df
            
            # New: Fetch rate plan descriptions
            if "hotel_ids_used" in st.session_state:
                rate_plan_descs = api.get_rate_plan_descriptions(st.session_state.hotel_ids_used)
                st.session_state.rate_plan_descs = rate_plan_descs

        except Exception as e:
            st.error(f"Error during search: {str(e)}")
            return
        
    if "rate_plan_descs" not in st.session_state:
        st.session_state.rate_plan_descs = {}


    if "stays" in st.session_state:
        with results_container:
            filtered_df = filter_results(
                st.session_state.stays,
                bedrooms,
                management,
                exclude_list,
                exclude_rate_plans  # Pass the exclude_rate_plans to the filter function
            )
            
            if st.session_state.checkin_dt and st.session_state.checkout_dt:
                date_line = (
                    f"**Check in** - {st.session_state.checkin_dt.strftime('%B %d, %Y')} and "
                    f"**check out** - {st.session_state.checkout_dt.strftime('%B %d, %Y')} "
                    f"({st.session_state.nights} nights)"
                )
                header = st.container()
                header.write(" ")
                header.write(date_line)
                
                header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)
                
                st.markdown(
                    """
                    <style>
                        div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
                            position: sticky;
                            top: 2.875rem;
                            background-color: white;
                            z-index: 999;
                        }
                        .fixed-header {
                            border-bottom: 1px solid black;
                        }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
            
            if show_lowest_prices:
                # Step 1: Find the minimum price for each room
                min_price_idx = filtered_df.groupby(['Hotel Name', 'Room Name']).Price.transform(min) == filtered_df['Price']
                min_price_df = filtered_df[min_price_idx]
    
                # Step 2: When there are multiple rates with the same minimum price for a room,
                # keep only the first one for each room
                filtered_df = min_price_df.groupby(['Hotel Name', 'Room Name']).first().reset_index()
            
            # Adjust column ratio to give dataframe more screen space
            col1, col2 = st.columns([3, 1.5])

            with col1:
                st.write(f"###### {filtered_df.hotel_room_name.nunique()} Stays")
                
                # Add booking links to the dataframe
                if hasattr(st.session_state, 'checkin_input'):
                    display_df = add_booking_links_to_dataframe(
                        filtered_df,
                        st.session_state.checkin_input,
                        st.session_state.checkout_input,
                        st.session_state.nights,
                        st.session_state.guests_input
                    )
                else:
                    display_df = filtered_df.copy()
                
                # Rename columns for display
                display_df = display_df.rename(columns={
                    'Bedrooms': 'Beds',
                    'Bathrooms': 'Baths',
                    'Max Guests': 'Max PAX',
                    'Quant Avail': 'Available',
                    'Managed By': 'Management'
                })
                
                # Ensure the columns we want are available
                if "Hotel ID" not in display_df.columns:
                    display_df["Hotel ID"] = "N/A"
                
                # Define the columns to display, with booking link after management
                display_columns = [
                    "Room", "Price", "Per Night", "Beds", "Baths", "Max PAX", 
                    "Available", "Management"
                ]
                
                # Add booking link column after management if it exists
                if "Booking Link" in display_df.columns:
                    display_columns.append("Booking Link")
                
                # Add the ID columns at the end
                display_columns.extend(["Room Type ID", "Hotel ID"])
                
                # Make sure we only include columns that exist
                display_columns = [col for col in display_columns if col in display_df.columns]
                
                display_df = display_df[display_columns]
                
                styled_df = display_df.style.format({
                    'Price': '¥{:,.0f}',
                    'Per Night': '¥{:,.0f}'
                })
                
                st.dataframe(
                    styled_df,
                    width=1200,
                    height=800,
                    hide_index=True
                )
                
                st.write("Early Bird offer: ¥0 for X guests (requires full payment by May 31st)")

            with col2:
                # Create tabs for the right column
                tab1, tab2, tab3 = st.tabs(["Summary", "Graphs", "Rate Plans"])
                
                with tab1:
                                        
                    # Calculate summary metrics
                    total_properties = filtered_df.hotel_room_name.nunique()
                    avg_price = filtered_df['Price'].mean()
                    avg_price_per_night = filtered_df['Per Night'].mean() if 'Per Night' in filtered_df else 0
                    max_price = filtered_df['Price'].max()
                    min_price = filtered_df['Price'].min()

                    # Display metrics in a simple format
                    st.metric("Total Stays", f"{total_properties}")
                    st.metric("Average Price", f"¥{avg_price:,.0f}")
                    st.metric("Average Price/Night", f"¥{avg_price_per_night:,.0f}")
                    st.metric("Price Range", f"¥{min_price:,.0f} - ¥{max_price:,.0f}")
                    
                    if 'Per Night' in filtered_df:
                        min_price_per_night = filtered_df['Per Night'].min()
                        max_price_per_night = filtered_df['Per Night'].max()
                        st.metric("Price Range/Night", f"¥{min_price_per_night:,.0f} - ¥{max_price_per_night:,.0f}")
                    
                    # Management Company Breakdown
                    st.subheader("Management")
                    mgmt_counts = filtered_df.groupby('Managed By').size().reset_index(name='Count')
                    mgmt_counts['Percentage'] = (mgmt_counts['Count'] / mgmt_counts['Count'].sum() * 100).round(1)
                    
                    # Display as a small table
                    st.dataframe(
                        mgmt_counts.style.format({
                            'Percentage': '{:.1f}%'
                        }),
                        hide_index=True
                    )
                    
                    # Bedroom Distribution (without title and percentage)
                    bed_counts = filtered_df.groupby('Bedrooms').size().reset_index(name='Count')
                    
                    # Display as a small table without the percentage column
                    st.dataframe(
                        bed_counts,
                        hide_index=True
                    )
                
                with tab2:
                    primary_group = 'Managed By'
                    secondary_group = 'Rate Plan'
                    
                    grouped = filtered_df.groupby([primary_group, secondary_group]).agg({
                        'Quant Avail': 'sum',
                        'Price': ['min', 'max', 'mean']
                    }).reset_index()
                    
                    x_positions, x_labels, x_jitter = calculate_plot_positions(
                        filtered_df, grouped, primary_group, secondary_group
                    )
                    
                    fig = create_price_plot(
                        filtered_df,
                        x_jitter,
                        x_positions,
                        x_labels,
                        grouped,
                        primary_group,
                        show_trends=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if "Per Night" in filtered_df.columns:
                        fig2 = create_per_night_plot(
                            filtered_df,
                            x_jitter,
                            x_positions,
                            x_labels,
                            grouped,
                            primary_group,
                            show_trends=False
                        )
                        st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    st.subheader("Rate Plan Information")
                    
                    if st.session_state.get("rate_plan_descs"):
                        # Create a dropdown to select hotel
                        hotel_names_dict = {}
                        for idx, row in filtered_df.iterrows():
                            hotel_id = row.get("Hotel ID", "N/A")
                            hotel_name = row.get("Hotel Name", "Unknown Hotel")
                            if hotel_id != "N/A":
                                hotel_names_dict[hotel_id] = hotel_name
                        
                        selected_hotel = st.selectbox(
                            "Select a property to view rate plans:", 
                            options=list(hotel_names_dict.keys()),
                            format_func=lambda x: hotel_names_dict.get(x, "Unknown Hotel")
                        )
                        
                        if selected_hotel in st.session_state["rate_plan_descs"]:
                            rate_plans = st.session_state["rate_plan_descs"][selected_hotel]
                            
                            if rate_plans:
                                # Create a table of rate plans
                                rate_plan_data = []
                                for rp_id, info in rate_plans.items():
                                    rate_plan_data.append({
                                        "Rate Plan ID": rp_id,
                                        "Name": info.get('name_en', ''),
                                        "Description": info.get('desc_en', '')
                                    })
                                
                                if rate_plan_data:
                                    st.dataframe(
                                        pd.DataFrame(rate_plan_data),
                                        hide_index=True
                                    )
                                    
                                    # Add a section to view detailed info for a specific rate plan
                                    selected_rate_plan = st.selectbox(
                                        "Select a rate plan to view details:",
                                        options=[rp["Rate Plan ID"] for rp in rate_plan_data]
                                    )
                                    
                                    if selected_rate_plan:
                                        rp_info = rate_plans[selected_rate_plan]
                                        with st.expander("Rate Plan Details", expanded=True):
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                st.markdown("### English")
                                                st.markdown(f"**Name:** {rp_info.get('name_en', '')}")
                                                st.markdown(f"**Short Description:** {rp_info.get('desc_en', '')}")
                                                st.markdown(f"**Long Description:**")
                                                st.markdown(rp_info.get('long_desc_en', ''))
                                            
                                            with col2:
                                                st.markdown("### Japanese")
                                                st.markdown(f"**Name:** {rp_info.get('name_ja', '')}")
                                                st.markdown(f"**Short Description:** {rp_info.get('desc_ja', '')}")
                                                st.markdown(f"**Long Description:**")
                                                st.markdown(rp_info.get('long_desc_ja', ''))
                            else:
                                st.info("No rate plans found for this hotel.")
                        else:
                            st.info("No rate plan information available for the selected hotel.")
                    else:
                        st.info("Rate plan information will be shown after a search is performed.")
                                    

if __name__ == "__main__":
    main()
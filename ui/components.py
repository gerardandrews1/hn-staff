import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

def render_date_filters() -> tuple[str, str]:
    """Render date input filters for check-in and check-out
    
    Returns:
        tuple: (checkin_date, checkout_date) as formatted strings
    """
    col1, col2 = st.columns(2)
    
    with col1:
        checkin = st.date_input(
            "Check-in Date",
            min_value=datetime.now(),
            max_value=datetime.now() + timedelta(days=365),
            help="Select your check-in date"
        )
    
    with col2:
        checkout = st.date_input(
            "Check-out Date",
            value=checkin + timedelta(days=1) if checkin else None,
            min_value=checkin + timedelta(days=1) if checkin else datetime.now(),
            max_value=datetime.now() + timedelta(days=365),
            help="Select your check-out date"
        )
    
    return checkin.strftime("%Y%m%d"), checkout.strftime("%Y%m%d")

def render_guest_input() -> str:
    """Render guest number input
    
    Returns:
        str: Number of guests
    """
    return st.number_input(
        "Number of Guests",
        min_value=1,
        max_value=20,
        value=2,
        help="Enter the number of guests"
    )

def render_property_filters(df: pd.DataFrame) -> tuple[List[int], List[str]]:
    """Render property filters (bedrooms, management)
    
    Args:
        df: DataFrame containing property data
        
    Returns:
        tuple: (selected_bedrooms, selected_management)
    """
    # Bedroom filter
    bed_bath_list = ["-All", 1, 2, 3, 4, 5, 6, 7, 8]
    bedrooms = st.multiselect(
        "Filter by bedrooms",
        options=bed_bath_list,
        default="-All"
    )
    
    if "-All" in bedrooms:
        bedrooms = bed_bath_list[1:]  # Remove "-All" from the list
    
    # Management filter
    management_list = df["Managed By"].unique().tolist()
    management_list.insert(0, "-All")
    
    management = st.multiselect(
        "Filter management company",
        options=management_list,
        default="-All"
    )
    
    if "-All" in management:
        management = management_list[1:]  # Remove "-All" from the list
    
    return bedrooms, management

def render_exclusion_filters() -> List[str]:
    """Render filters for excluding certain properties
    
    Returns:
        List[str]: List of properties to exclude
    """
    unbookable_list = [
        "SnowDog Village",
        "Suiboku",
        "Always Niseko",
        "Roku"
    ]
    
    include_all = st.toggle(
        "Include all properties",
        value=False,
        help="Toggle to include typically unbookable properties"
    )
    
    return [] if include_all else unbookable_list

def display_property_card(
    property_data: Dict[str, Any],
    nights: int,
    container: Optional[st.container] = None
) -> None:
    """Display a single property card
    
    Args:
        property_data: Dictionary containing property information
        nights: Number of nights
        container: Optional Streamlit container to render in
    """
    target = container or st
    
    with target:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"{property_data['Hotel Name']} - {property_data['Room Name']}")
            st.write(f"**Management**: {property_data['Managed By']}")
            st.write(f"**Rate Plan**: {property_data['Rate Plan']}")
        
        with col2:
            st.metric(
                "Price per Night", 
                f"¥{property_data['Price'] / nights:,.0f}"
            )
            st.write(f"**Total**: ¥{property_data['Price']:,.0f}")
        
        with col3:
            st.write(f"**Bedrooms**: {property_data['Bedrooms']}")
            st.write(f"**Bathrooms**: {property_data['Bathrooms']}")
            st.write(f"**Max Guests**: {property_data['Max Guests']}")
            st.write(f"**Available Units**: {property_data['Quant Avail']}")
        
        st.divider()

def display_search_results(df: pd.DataFrame, container: Optional[st.container] = None) -> None:
    """Display search results in a formatted way
    
    Args:
        df: DataFrame containing search results
        container: Optional Streamlit container to render in
    """
    target = container or st
    
    with target:
        if "checkin_dt" in st.session_state and "checkout_dt" in st.session_state:
            # Display date information
            date_line = (
                f"**Check in** - {st.session_state.checkin_dt.strftime('%B %d, %Y')} and "
                f"**check out** - {st.session_state.checkout_dt.strftime('%B %d, %Y')} "
                f"({st.session_state.nights} nights)"
            )
            st.write(date_line)
            
            # Early bird pricing info
            st.info(
                "Early bird pricing requires full payment 60 days before check-in",
                icon="ℹ️"
            )
        
        # Display results count
        st.subheader(f"{df.hotel_room_name.nunique()} Available Rooms")
        
        # Calculate commission and per night prices
        df = calculate_pricing(df)
        
        # Display results in a sortable table
        st.dataframe(
            df[["Room", "Price", "Per Night", "Bedrooms", 
                "Bathrooms", "Max Guests", "Quant Avail", "Managed By"]],
            width=1100,
            height=700,
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn(
                    "Price",
                    help="Total price for stay",
                    format="¥%d"
                ),
                "Per Night": st.column_config.NumberColumn(
                    "Per Night",
                    help="Price per night",
                    format="¥%d"
                )
            }
        )

def calculate_pricing(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate commission and per night prices
    
    Args:
        df: DataFrame containing property data
        
    Returns:
        DataFrame with added pricing columns
    """
    # Add hotel_room_name column
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
    else:
        df["Per Night"] = df["Price"]
    
    return df.sort_values(by=["Price", "Room"])

def render_error_message(error: str) -> None:
    """Display an error message
    
    Args:
        error: Error message to display
    """
    st.error(
        f"An error occurred: {error}",
        icon="🚨"
    )

def render_loading_message(message: str = "Loading...") -> None:
    """Display a loading message
    
    Args:
        message: Loading message to display
    """
    with st.spinner(message):
        st.empty()
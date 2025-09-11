# -*- coding: utf-8 -*-
import json
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
from typing import Optional, Dict

from services.holiday_niseko_api import HolidayNisekoAPI
from services.api_list_booking import call_api
from models.booking import Booking

st.set_page_config(page_title="Upcoming Arrivals", page_icon="📅", layout="wide")


# ---------- Secrets / Client ----------
def _get_api():
    cfg = st.secrets.get("holidayniseko", {})
    missing = [k for k in ("USERNAME", "PASSWORD") if k not in cfg]
    if missing:
        st.error(f"Missing secrets in [holidayniseko]: {missing}")
        st.stop()
    base_url = cfg.get("BASE_URL", "https://holidayniseko.com/api")
    try:
        return HolidayNisekoAPI(cfg["USERNAME"], cfg["PASSWORD"], base_url=base_url)
    except Exception as e:
        st.exception(e)
        st.stop()


api = _get_api()


# ---------- Helper Functions ----------
def fetch_individual_booking_data(eid: str) -> Optional[Dict]:
    """
    Fetch individual booking using RoomBoss API (same as booking viewer).
    """
    try:
        response = call_api(
            eid,
            st.secrets["roomboss"]["api_id"], 
            st.secrets["roomboss"]["api_key"]
        )
        
        if response.ok:
            booking = Booking(json.loads(response.text), api_type="listBooking")
            # Ensure booking attribution is called (this should happen in __init__ but let's be sure)
            if not hasattr(booking, 'booking_source_1'):
                booking.attribute_booking()
            return extract_display_data_from_booking(booking)
        else:
            st.error(f"Error fetching booking {eid}: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching booking {eid}: {str(e)}")
        return None


def extract_display_data_from_booking(booking: Booking) -> Dict:
    """
    Extract the same data columns as the current dataframe from a Booking object.
    """
    # Process room data to set dates (same logic as booking viewer)
    process_room_data_for_display(booking)
    
    # Format invoice and payment amounts
    invoiced_formatted = ""
    if hasattr(booking, 'amount_invoiced') and booking.amount_invoiced > 0:
        invoiced_formatted = f"¥{booking.amount_invoiced:,.0f}"
    
    payment_formatted = ""
    if hasattr(booking, 'amount_received') and booking.amount_received > 0:
        payment_formatted = f"¥{booking.amount_received:,.0f}"
    
    # Extract room type from first room
    room_type = ""
    if hasattr(booking, 'room_list_todf') and booking.room_list_todf:
        room_type = booking.room_list_todf[0][1]  # Room name is second item
    
    # Format eID with commas (as string)
    eid_raw = getattr(booking, 'eId', '')
    # st.write(f"DEBUG: eid_raw = {eid_raw}, type = {type(eid_raw)}")
    try:
        if eid_raw and str(eid_raw).isdigit():
            eid_formatted = f"{int(eid_raw):,}"
    #         st.write(f"DEBUG: formatted eid = {eid_formatted}")
    #     else:
    #         eid_formatted = str(eid_raw)
    #         st.write(f"DEBUG: not digit, using raw = {eid_formatted}")
    except (ValueError, TypeError) as e:
        eid_formatted = str(eid_raw)
        # st.write(f"DEBUG: error formatting = {e}, using raw = {eid_formatted}")
    
    # Get booking source with fallback
    try:
        # Make sure attribution has been called
        if not hasattr(booking, 'booking_source_1'):
            booking.attribute_booking()
            
        booking_source_1 = getattr(booking, 'booking_source_1', 'Unknown')
        booking_source_2 = getattr(booking, 'booking_source_2', 'Unknown')
        
        # Format booking source for display
        if booking_source_1 != "Unknown" and booking_source_2 != "Unknown" and booking_source_1 != booking_source_2:
            booking_source = f"{booking_source_1} - {booking_source_2}"
        elif booking_source_1 != "Unknown":
            booking_source = booking_source_1
        elif booking_source_2 != "Unknown":
            booking_source = booking_source_2
        else:
            booking_source = "Unknown"
    except Exception as e:
        # Fallback if attribution fails
        booking_source = "Unknown"
        print(f"Attribution error for {eid_raw}: {str(e)}")
    
    return {
        'eid': eid_formatted,
        'arrival_date': getattr(booking, 'accom_checkin', ''),
        'departure_date': getattr(booking, 'accom_checkout', ''),
        'nights': getattr(booking, 'nights', ''),
        'property_name': getattr(booking, 'vendor', ''),
        'room_type': room_type,
        'guest_name': getattr(booking, 'full_name', ''),
        'guest_email': getattr(booking, 'guest_email', ''),
        'guest_phone': getattr(booking, 'guest_phone', ''),
        'booking_source': booking_source,
        'invoiced_formatted': invoiced_formatted,
        'payment_formatted': payment_formatted,
        'online_check_in': ""  # Placeholder as before
    }


def process_room_data_for_display(booking):
    """Process room data to set necessary attributes for display"""
    if not hasattr(booking, 'room_list_todf') or not booking.room_list_todf:
        return
        
    all_checkins = []
    all_checkouts = []
    
    for room in booking.room_list_todf:
        all_checkins.append(room[2])  # Check-in is third item
        all_checkouts.append(room[3])  # Check-out is fourth item
    
    if all_checkins:
        booking.accom_checkin = min(all_checkins)
    if all_checkouts:
        booking.accom_checkout = max(all_checkouts)


# ---------- UI ----------
st.subheader("📅 Upcoming Arrivals")

left, right = st.columns([2, 3], gap="large")

with left:
    st.subheader("Pick a date")
    manual_date = st.date_input("Arrivals on:", datetime.now().date() + timedelta(days=1))

with left:
    # st.subheader("Quick select")
    presets = {
        "— Quick Select —": None,
        "In 21 days": 21,
        "In 14 days": 14,
        "In 7 days": 7,
        "In 2 days": 2,
        "Tomorrow (1 day)": 1,
    }
    choice = st.selectbox(" ", list(presets.keys()), index=0, label_visibility="collapsed")
    qs = presets[choice]

target_date = manual_date if qs is None else (date.today() + timedelta(days=qs))
st.caption(f"Target arrival date: **{target_date:%Y-%m-%d}**")

# st.info("This calls Holiday Niseko API for booking IDs, then RoomBoss API for detailed data.")


# ---------- Actions ----------
if st.button("Find arrivals", type="primary"):
    compact = target_date.strftime("%Y%m%d")

    # Step 1: Get list of active eIDs from Holiday Niseko API
    with st.spinner(f"Fetching booking list for {compact}..."):
        try:
            active_eids = api.get_active_eids_by_checkin_date(compact)
        except Exception as e:
            st.error("Request failed.")
            st.exception(e)
            st.stop()

    if not active_eids:
        st.warning("No active arrivals found for that date.")
        st.stop()

    st.success(f"Found **{len(active_eids)}** active bookings. Fetching details...")
    
    # Step 2: Fetch detailed data for each booking using RoomBoss API
    booking_data = []
    progress_bar = st.progress(0)
    
    for i, eid in enumerate(active_eids):
        progress_bar.progress((i + 1) / len(active_eids), text=f"Fetching booking {eid} ({i+1}/{len(active_eids)})")
        booking_details = fetch_individual_booking_data(eid)
        if booking_details:
            booking_data.append(booking_details)
    
    progress_bar.empty()
    
    if not booking_data:
        st.warning("No booking details could be retrieved.")
        st.stop()
    
    # Step 3: Create DataFrame with the same structure as before
    df = pd.DataFrame(booking_data)
    

    # Apply the same date filter as before
    if 'arrival_date' in df.columns:
        df['arrival_date'] = pd.to_datetime(df['arrival_date'], errors='coerce').dt.date
        df = df[df['arrival_date'] == target_date]
    
    if df.empty:
        st.warning("No arrivals found for that exact date after processing.")
        st.stop()

    # Create the column mapping for display (same as before)
    column_mapping = {
        "eid": "eId",
        "arrival_date": "arrival",
        "departure_date": "departure",
        "nights": "nights",
        "property_name": "propertyname",
        "room_type": "room_type",
        "guest_name": "guest_name",
        "guest_email": "email",
        "guest_phone": "guest_phone",
        "booking_source": "source",
        "invoiced_formatted": "invoiced",
        "payment_formatted": "received",
        "online_check_in": "online check-in"
    }

    # Get the columns we can actually display
    display_columns = list(column_mapping.keys())
    
    # Rename for display
    df_display = df.copy()
    if 'eid' in df_display.columns:
        df_display['eid'] = df_display['eid'].astype(str)
    df_display = df_display.rename(columns=column_mapping)
    display_names = list(column_mapping.values())

    st.success(f"Retrieved details for **{len(df)}** arrivals.")

    st.dataframe(
    df_display[display_names], 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "eId": st.column_config.NumberColumn(
            "eId",
            format="%d"
        )
    }
)

    # Downloads (using original column names for data integrity)
    st.download_button(
        "Download CSV",
        df[display_columns].to_csv(index=False).encode("utf-8"),
        file_name=f"upcoming_arrivals_{target_date:%Y%m%d}.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download JSON",
        df[display_columns].to_json(orient="records").encode("utf-8"),
        file_name=f"upcoming_arrivals_{target_date:%Y%m%d}.json",
        mime="application/json",
    )

    # Optional quick summary by property
    with st.expander("Summary by property"):
        if 'property_name' in df.columns:
            grp = (
                df.groupby(["property_name"], dropna=False)
                  .agg(arrivals=("eid", "count"))
                  .sort_values("arrivals", ascending=False)
            )
            st.dataframe(grp, use_container_width=True)
        else:
            st.write("Property name data not available for summary.")
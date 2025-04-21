import streamlit as st
import requests
import json
from typing import List, Dict, Any, Optional
from config import AppConfig

class RoomBossAPI:
    """RoomBoss API client for hotel availability and booking management"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize RoomBoss API client"""
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
        
        self.base_url = "https://api.roomboss.com/extws"
        self.hotel_url = f"{self.base_url}/hotel/v1"
        
        # Set up session
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def _make_request(self, url: str, method: str = "GET", json_data: Dict = None) -> Dict[str, Any]:
        """Make an API request and handle errors"""
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method in ["POST", "PUT"]:
                response = self.session.request(method, url, json=json_data)
            
            # Try to parse JSON response
            try:
                json_response = response.json() if response.content else {}
                
                # Check for API error response
                if "error" in json_response:
                    st.error(json_response["error"])
                    return {}
                    
                return json_response
                
            except json.JSONDecodeError:
                st.error(f"Invalid JSON response: {response.text[:200]}")
                return {}
                
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {str(e)}")
            return {}
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return {}

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking details"""
        booking_id = str(booking_id).strip()
        if not booking_id:
            st.error("Invalid booking ID")
            return None
            
        url = f"{self.hotel_url}/listBooking?bookingId={booking_id}"
        return self._make_request(url)

    def get_hotel_list(self, country_code: str = "jp", location_code: str = "niseko") -> List[str]:
        """Get list of hotel IDs"""
        url = f"{self.hotel_url}/list?countryCode={country_code}&locationCode={location_code}"
        json_data = self._make_request(url)
        
        hotel_ids = []
        for hotel in json_data.get("hotels", []):
            hotel_id = hotel.get("hotelId")
            if hotel_id:
                hotel_ids.append(f"&hotelId={hotel_id}")
        
        return [
            "".join(hotel_ids[0:100]),
            "".join(hotel_ids[100:])
        ]

    def get_available_stays(
        self,
        hotel_ids_list: List[str],
        checkin: str,
        checkout: str,
        guests: str
    ) -> List[Dict[str, Any]]:
        """Get available stays"""
        resp_lists = []
        
        for id_list in hotel_ids_list:
            url = (
                f"{self.hotel_url}/listAvailable?1&"
                f"checkIn={checkin}&checkOut={checkout}&"
                f"numberGuests={guests}&excludeConditionsNotMet&"
                f"rate=ota&locationCode=NISEKO&countryCode=JP{id_list}"
            )
            
            response_data = self._make_request(url)
            if response_data:
                resp_lists.append(response_data)
        
        return resp_lists

# For backward compatibility
RoombossService = RoomBossAPI
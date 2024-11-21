import requests
from typing import Optional, Dict, Any
import streamlit as st
from datetime import datetime
from config import AppConfig

class RoombossService:
    def __init__(self, config: AppConfig):
        self.config = config.roomboss
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    @st.cache_data(ttl=300)
    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Fetch booking details"""
        try:
            response = requests.get(
                f"{self.config.api_url}/bookings/{booking_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching booking: {str(e)}")
            return None

    def format_booking_display(self, booking_data: Dict) -> Dict:
        """Format booking data for display"""
        try:
            order = booking_data.get('order', {})
            lead_guest = order.get('leadGuest', {})
            bookings = order.get('bookings', [])
            
            # Format for display
            formatted = {
                "Guest Information": {
                    "Name": f"{lead_guest.get('givenName', '')} {lead_guest.get('familyName', '')}",
                    "Email": lead_guest.get('email', ''),
                    "Phone": lead_guest.get('phoneNumber', ''),
                    "Nationality": lead_guest.get('nationality', '')
                },
                "Bookings": []
            }
            
            for booking in bookings:
                booking_info = {
                    "Type": booking.get('bookingType', ''),
                    "Items": []
                }
                
                for item in booking.get('items', []):
                    if booking.get('bookingType') == 'ACCOMMODATION':
                        booking_info["Items"].append({
                            "Room": item.get('roomNumber', ''),
                            "Check-in": item.get('checkIn', ''),
                            "Check-out": item.get('checkOut', ''),
                            "Guests": item.get('numberGuests', 0)
                        })
                    else:  # SERVICE
                        booking_info["Items"].append({
                            "Service": item.get('service', {}).get('name', ''),
                            "Date": item.get('startDate', '')
                        })
                        
                formatted["Bookings"].append(booking_info)
                
            return formatted
            
        except Exception as e:
            st.error(f"Error formatting booking data: {str(e)}")
            return {}
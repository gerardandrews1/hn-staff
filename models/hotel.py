from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
import streamlit as st
from utils.property_utils import match_property_management

@dataclass
class Room:
    """Room details model"""
    price: float
    rate_plan: str
    bedrooms: int
    bathrooms: int
    max_guests: int
    quantity_available: int
    room_name: str

class RbAvailableHotel:
    """RoomBoss Available Hotel Model"""
    
    RATE_PLAN_MAPPING = {
        487111: "WOW Standard",
        493448: "Aya Standard",
        479226: "H2 Standard",
        459248: "VN standard",
        459290: "VN AP",
        457905: "HN standard",
        444942: "HN OTA",
        444506: "Chat standard",
        460349: "NISADE Standard",
        460468: "NISADE EB",
        484750: "NISADE EB & 9+ nights",
        460411: "NISADE EB",
        460292: "NISADE Standard",
        485536: "MnK Stand",
        485566: "MnK EB",
        474983: "Hokkaido Travel EB",
        440650: "Hokkaido Travel stand",
        507323: "HN Early Bird",  # Add proper name
        511129: "HN Standard",   # Add proper name
        504401: "H2 Standard",
        506333: "MnK Promotion",
        502176: "Standard"

    }

    def __init__(self, dictionary_entry: Dict[str, Any], management_dict: Dict[str, str]):
        """
        Initialize RbAvailableHotel object
        
        Args:
            dictionary_entry: Raw hotel data from API
            management_dict: Dictionary mapping hotel names to management companies
        """
        self.dict = dictionary_entry
        self.hotel_name = self.dict.get("hotelName", "")
        self.hotel_url = self.dict.get("hotelUrl")
        self.pos_managed = self.dict.get("pos_managed")
        
        # Get management company using the matching function
        self.managed_by = match_property_management(self.hotel_name, management_dict)
        
        # Initialize rooms dictionary
        self.avail_rooms = {}
        self._parse_available_rooms()

    def _parse_available_rooms(self) -> None:
        """Parse available rooms from hotel data"""
        available_room_types = self.dict.get("availableRoomTypes", [])
        
        for room_type in available_room_types:
            room_name = room_type.get("roomTypeName")
            if room_name:
                self._parse_room_type(room_type, room_name)

    def _parse_room_type(self, room_type: Dict[str, Any], room_name: str) -> None:
        quantity = room_type.get("quantityAvailable", 0)
        if quantity == 0:
            return
            
        rate_plan_dict = room_type.get("ratePlan", {})
        price, rate_plan = self._parse_rate_plan(rate_plan_dict)

        management = self.managed_by
        # print(f"Management for {self.hotel_name}: {management}")  # Debug print

        entry = {
            "Room Type ID": room_type.get("roomTypeId", ""),  # Add this line
            "Price": price,
            "Rate Plan": rate_plan,
            "Bedrooms": room_type.get("numberBedrooms"),
            "Bathrooms": room_type.get("numberBathrooms"),
            "Max Guests": room_type.get("maxNumberGuests"),
            "Quant Avail": quantity,
            "Hotel Name": self.hotel_name,
            "Room Name": room_name,
            "Managed By": self.managed_by
        }
        
        # Include rate plan in the key to keep all rates
        key = f"{self.hotel_name} - {room_name} - {rate_plan}"
        self.avail_rooms[key] = entry



    def _parse_rate_plan(self, rate_plan_dict: Dict[str, Any]) -> tuple[float, str]:
        """
        Parse rate plan information
        
        Args:
            rate_plan_dict: Rate plan data from API
            
        Returns:
            tuple: (price, rate_plan_name)
        """
        price = rate_plan_dict.get("priceRetail", 0)
        rate_plan_id = rate_plan_dict.get("ratePlanId")
        # Instead of "Unknown Rate", show "Rate ID: {id}"
        rate_name = self.RATE_PLAN_MAPPING.get(rate_plan_id, f"Rate ID: {rate_plan_id}")
        
        return price, rate_name

    def to_dataframe(self) -> pd.DataFrame:
        """Convert available rooms to pandas DataFrame"""
        if not self.avail_rooms:
            return pd.DataFrame()
            
        return pd.DataFrame(self.avail_rooms).T

    @classmethod
    def get_rate_plan_name(cls, rate_plan_id: int) -> str:
        """Get rate plan name from ID"""
        return cls.RATE_PLAN_MAPPING.get(rate_plan_id, "Unknown Rate")
from typing import Optional
import re

def validate_booking_id(booking_id: str) -> tuple[bool, Optional[str]]:
    """Validate booking ID format"""
    if not booking_id:
        return False, "Booking ID is required"
    
    if not booking_id.isdigit():
        return False, "Booking ID must contain only numbers"
    
    if len(booking_id) != 7:
        return False, "Booking ID must be 7 digits"
    
    return True, None

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone format"""
    pattern = r'^\+?[0-9\s-]{8,}$'
    return bool(re.match(pattern, phone))
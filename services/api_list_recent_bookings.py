# -*- coding: utf-8 -*-
# services/api_list_recent_bookings.py

import requests
import json
import datetime
from typing import Optional, Dict, Any
import base64

def call_recent_bookings_api(
    date: str,
    api_id: str, 
    api_key: str,
    booking_type: str = "ALL"
) -> requests.Response:
    """
    Call the List Bookings Changed on Date API endpoint
    
    Args:
        date: Date in YYYYMMDD format (from docs)
        api_id: API ID from secrets
        api_key: API key from secrets  
        booking_type: "ACCOMMODATION", "NON_ACCOMMODATION", or "ALL"
    
    Returns:
        requests.Response object
    """
    
    # Correct API endpoint from documentation
    url = "https://api.roomboss.com/extws/hotel/v1/listBookings"
    
    # HTTP Basic Authentication (from docs)
    credentials = f"{api_id}:{api_key}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Accept': 'application/json'
    }
    
    # URL parameters (not JSON body)
    params = {
        "date": date,
        "bookingType": booking_type
    }
    
    try:
        # Make the API call with GET method and URL parameters
        response = requests.get(
            url, 
            headers=headers, 
            params=params,
            timeout=30
        )
        
        # Debug: Print response details
        print(f"DEBUG: API URL: {url}")
        print(f"DEBUG: API Params: {params}")
        print(f"DEBUG: Response Status: {response.status_code}")
        print(f"DEBUG: Response Headers: {dict(response.headers)}")
        print(f"DEBUG: Response Text (first 1000 chars): {response.text[:1000]}")
        
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Request Exception: {str(e)}")
        # Return a mock response object with error info
        class ErrorResponse:
            def __init__(self, error_msg):
                self.ok = False
                self.status_code = 500
                self.reason = str(error_msg)
                self.text = json.dumps({"error": str(error_msg)})
        
        return ErrorResponse(e)


def get_recent_bookings_for_date_range(
    start_date: str,
    end_date: str, 
    api_id: str,
    api_key: str,
    booking_type: str = "ALL"
) -> Dict[str, Any]:
    """
    Get recent bookings for a date range
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        api_id: API ID from secrets
        api_key: API key from secrets
        booking_type: "ACCOMMODATION", "NON_ACCOMMODATION", or "ALL"
        
    Returns:
        Dictionary with combined results and metadata
    """
    
    all_bookings = []
    errors = []
    
    # Convert date strings to datetime objects
    start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    
    # Iterate through each date in the range
    current_date = start_dt
    while current_date <= end_dt:
        # Convert to YYYYMMDD format as required by API
        date_str = current_date.strftime('%Y%m%d')
        
        # Call API for this date
        response = call_recent_bookings_api(
            date=date_str,
            api_id=api_id, 
            api_key=api_key,
            booking_type=booking_type
        )
        
        if response.ok:
            try:
                data = json.loads(response.text)
                
                # Check if API call was successful
                if data.get('success', True):
                    bookings = data.get('bookings', [])
                    
                    # Add date info to each booking
                    for booking in bookings:
                        booking['query_date'] = current_date.strftime('%Y-%m-%d')
                        all_bookings.append(booking)
                else:
                    errors.append(f"API returned failure for {date_str}: {data.get('failureMessage', 'Unknown error')}")
                    
            except json.JSONDecodeError as e:
                errors.append(f"JSON decode error for {date_str}: {str(e)}")
        else:
            errors.append(f"API error for {date_str}: {response.status_code} - {getattr(response, 'reason', 'Unknown')}")
        
        # Move to next day
        current_date += datetime.timedelta(days=1)
    
    return {
        'bookings': all_bookings,
        'total_count': len(all_bookings),
        'date_range': f"{start_date} to {end_date}",
        'errors': errors,
        'success': len(errors) == 0
    }


def get_today_bookings(api_id: str, api_key: str) -> Dict[str, Any]:
    """
    Get bookings changed today
    
    Args:
        api_id: API ID from secrets
        api_key: API key from secrets
        
    Returns:
        Dictionary with today's bookings
    """
    today = datetime.datetime.now()
    # Convert to YYYYMMDD format as required by API
    today_str = today.strftime('%Y%m%d')
    
    response = call_recent_bookings_api(
        date=today_str,
        api_id=api_id,
        api_key=api_key,
        booking_type="ALL"
    )
    
    if response.ok and "html" not in response.text.lower():
        try:
            # Check if response text is empty
            if not response.text.strip():
                return {
                    'bookings': [],
                    'date': today.strftime('%Y-%m-%d'),
                    'success': True,
                    'error': None,
                    'message': 'No bookings found for today'
                }
            
            # Try to parse JSON
            data = json.loads(response.text)
            
            # Check if API returned success
            if not data.get('success', True):
                return {
                    'bookings': [],
                    'date': today.strftime('%Y-%m-%d'),
                    'success': False,
                    'error': f"API returned failure: {data.get('failureMessage', 'Unknown error')}",
                    'raw_response': data
                }
            
            # Extract bookings from response
            bookings = data.get('bookings', [])
            
            return {
                'bookings': bookings,
                'date': today.strftime('%Y-%m-%d'),
                'success': True,
                'error': None,
                'raw_response': data  # Include raw response for debugging
            }
            
        except json.JSONDecodeError as e:
            return {
                'bookings': [],
                'date': today.strftime('%Y-%m-%d'), 
                'success': False,
                'error': f"JSON decode error: {str(e)}",
                'raw_text': response.text[:1000]  # Include raw text for debugging
            }
    else:
        # Check if it's an authentication issue
        if "login" in response.text.lower() or response.status_code == 401:
            error_msg = "Authentication failed - please check your API credentials"
        elif response.status_code == 404:
            error_msg = "API endpoint not found"
        else:
            error_msg = f"API error: {response.status_code} - {getattr(response, 'reason', 'Unknown error')}"
        
        return {
            'bookings': [],
            'date': today.strftime('%Y-%m-%d'),
            'success': False, 
            'error': error_msg,
            'raw_text': response.text[:1000] if hasattr(response, 'text') else 'No response text',
            'status_code': getattr(response, 'status_code', 'Unknown')
        }


def get_last_n_days_bookings(
    days: int, 
    api_id: str, 
    api_key: str
) -> Dict[str, Any]:
    """
    Get bookings changed in the last N days
    
    Args:
        days: Number of days to look back
        api_id: API ID from secrets
        api_key: API key from secrets
        
    Returns:
        Dictionary with recent bookings
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days-1)
    
    return get_recent_bookings_for_date_range(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        api_id=api_id,
        api_key=api_key,
        booking_type="ALL"
    )
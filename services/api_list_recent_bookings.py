# -*- coding: utf-8 -*-
# services/api_list_recent_bookings.py - Rate Limited Version

import requests
import json
import datetime
import time
from typing import Optional, Dict, Any
import base64

# Global variables to track API call timing
_api_call_times = []  # List of timestamps for recent API calls
_max_calls_per_minute = 60
_rate_limit_threshold = 40  # Start rate limiting when we hit this many calls per minute
_safety_buffer = 5  # Extra safety margin

def _smart_rate_limit():
    """
    Intelligent rate limiting that only kicks in when approaching the limit
    - Tracks calls in a rolling 60-second window
    - Only applies delays when approaching the rate limit
    - Uses adaptive delays based on current call frequency
    """
    global _api_call_times
    
    current_time = time.time()
    
    # Remove calls older than 60 seconds
    _api_call_times = [t for t in _api_call_times if current_time - t < 60.0]
    
    calls_in_last_minute = len(_api_call_times)
    
    # Only apply rate limiting if we're approaching the threshold
    if calls_in_last_minute >= _rate_limit_threshold:
        # Calculate how long to wait
        if calls_in_last_minute >= (_max_calls_per_minute - _safety_buffer):
            # Close to limit - wait longer
            sleep_time = 1.2
            print(f"DEBUG: Near rate limit ({calls_in_last_minute}/60 calls) - sleeping {sleep_time}s")
        else:
            # Approaching threshold - shorter delay
            sleep_time = 0.5
            print(f"DEBUG: Approaching rate limit ({calls_in_last_minute}/60 calls) - sleeping {sleep_time}s")
        
        time.sleep(sleep_time)
    
    # Record this call
    _api_call_times.append(current_time)

def call_recent_bookings_api(
    date: str,
    api_id: str, 
    api_key: str,
    booking_type: str = "ALL"
) -> requests.Response:
    """
    Call the List Bookings Changed on Date API endpoint with rate limiting
    
    Args:
        date: Date in YYYYMMDD format (from docs)
        api_id: API ID from secrets
        api_key: API key from secrets  
        booking_type: "ACCOMMODATION", "NON_ACCOMMODATION", or "ALL"
    
    Returns:
        requests.Response object
    """
    
    # Apply smart rate limiting before making the call
    _smart_rate_limit()
    
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
    Get recent bookings for a date range with rate limiting and progress tracking
    
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
    
    # Calculate total days for progress tracking
    total_days = (end_dt - start_dt).days + 1
    
    # Warn if this will take a long time
    if total_days > 30:
        print(f"WARNING: Fetching {total_days} days of data. This will take approximately {total_days} seconds due to rate limiting.")
    
    # Iterate through each date in the range
    current_date = start_dt
    day_count = 0
    
    while current_date <= end_dt:
        day_count += 1
        
        # Convert to YYYYMMDD format as required by API
        date_str = current_date.strftime('%Y%m%d')
        
        # Show progress for longer operations
        if total_days > 7:
            print(f"Progress: Fetching day {day_count}/{total_days} ({date_str})")
        
        # Call API for this date (with smart rate limiting)
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
    
    print(f"Completed fetching {total_days} days. Found {len(all_bookings)} total bookings.")
    
    return {
        'bookings': all_bookings,
        'total_count': len(all_bookings),
        'date_range': f"{start_date} to {end_date}",
        'days_processed': total_days,
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
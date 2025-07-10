# -*- coding: utf-8 -*-
# services/api_list_recent_bookings.py - ENHANCED Rate Limited Version

import requests
import json
import datetime
import time
from typing import Optional, Dict, Any
import base64
import threading

# Thread-safe global variables to track API call timing
_api_call_lock = threading.Lock()
_api_call_times = []  # List of timestamps for recent API calls
_max_calls_per_minute = 60
_rate_limit_threshold = 40  # Start rate limiting when we hit this many calls per minute
_safety_buffer = 10  # Increased safety margin
_hard_limit = _max_calls_per_minute - _safety_buffer  # Never exceed 50 calls per minute

def _smart_rate_limit():
    """
    ENHANCED intelligent rate limiting with thread safety and stricter controls
    - Thread-safe tracking of calls
    - Stricter safety margins
    - Exponential backoff for high call volumes
    - Hard limit enforcement
    """
    global _api_call_times
    
    with _api_call_lock:  # Thread-safe access
        current_time = time.time()
        
        # Remove calls older than 60 seconds
        _api_call_times = [t for t in _api_call_times if current_time - t < 60.0]
        
        calls_in_last_minute = len(_api_call_times)
        
        print(f"DEBUG: Current API calls in last minute: {calls_in_last_minute}/{_max_calls_per_minute}")
        
        # HARD LIMIT: Never allow more than 50 calls per minute
        if calls_in_last_minute >= _hard_limit:
            # Calculate time until oldest call expires
            if _api_call_times:
                oldest_call = min(_api_call_times)
                time_until_expire = 61.0 - (current_time - oldest_call)  # Add 1 second buffer
                if time_until_expire > 0:
                    print(f"CRITICAL: Hard limit reached ({calls_in_last_minute}/{_hard_limit}) - waiting {time_until_expire:.1f}s")
                    time.sleep(time_until_expire)
                    # Refresh the call times after waiting
                    current_time = time.time()
                    _api_call_times = [t for t in _api_call_times if current_time - t < 60.0]
                    calls_in_last_minute = len(_api_call_times)
        
        # Progressive rate limiting based on call volume
        if calls_in_last_minute >= 45:
            # Very close to limit - long delay with exponential backoff
            sleep_time = 2.0 + (calls_in_last_minute - 45) * 0.5
            print(f"WARNING: Very close to limit ({calls_in_last_minute}/60) - sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        elif calls_in_last_minute >= _rate_limit_threshold:
            # Approaching threshold - moderate delay
            sleep_time = 1.0 + (calls_in_last_minute - _rate_limit_threshold) * 0.1
            print(f"INFO: Approaching rate limit ({calls_in_last_minute}/60) - sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        elif calls_in_last_minute >= 30:
            # Moderate usage - small delay
            sleep_time = 0.5
            print(f"INFO: Moderate usage ({calls_in_last_minute}/60) - sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        # Record this call AFTER any delays
        _api_call_times.append(time.time())

def get_current_api_call_rate():
    """
    Get current API call rate for monitoring
    
    Returns:
        Dict with current call statistics
    """
    with _api_call_lock:
        current_time = time.time()
        recent_calls = [t for t in _api_call_times if current_time - t < 60.0]
        
        return {
            'calls_last_minute': len(recent_calls),
            'calls_last_30_seconds': len([t for t in recent_calls if current_time - t < 30.0]),
            'calls_last_10_seconds': len([t for t in recent_calls if current_time - t < 10.0]),
            'hard_limit': _hard_limit,
            'max_limit': _max_calls_per_minute,
            'time_until_oldest_expires': 60.0 - (current_time - min(recent_calls)) if recent_calls else 0
        }

def call_recent_bookings_api(
    date: str,
    api_id: str, 
    api_key: str,
    booking_type: str = "ALL"
) -> requests.Response:
    """
    Call the List Bookings Changed on Date API endpoint with ENHANCED rate limiting
    
    Args:
        date: Date in YYYYMMDD format (from docs)
        api_id: API ID from secrets
        api_key: API key from secrets  
        booking_type: "ACCOMMODATION", "NON_ACCOMMODATION", or "ALL"
    
    Returns:
        requests.Response object
    """
    
    # Apply enhanced smart rate limiting before making the call
    _smart_rate_limit()
    
    # Log the current rate for monitoring
    rate_stats = get_current_api_call_rate()
    print(f"DEBUG: Making API call with rate stats: {rate_stats}")
    
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
        print(f"DEBUG: Response Text (first 500 chars): {response.text[:500]}")
        
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
    Get recent bookings for a date range with ENHANCED rate limiting and progress tracking
    
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
    
    # Enhanced warning for large date ranges
    if total_days > 30:
        estimated_time = total_days * 2  # Conservative estimate with rate limiting
        print(f"WARNING: Fetching {total_days} days of data.")
        print(f"ESTIMATED TIME: {estimated_time} seconds ({estimated_time/60:.1f} minutes) due to rate limiting.")
        print(f"This will make {total_days} API calls with strict rate limiting to stay under 60 calls/minute.")
    
    # Check if this would exceed reasonable limits
    if total_days > 50:
        print(f"ERROR: Date range too large ({total_days} days). Maximum recommended: 50 days.")
        return {
            'bookings': [],
            'total_count': 0,
            'date_range': f"{start_date} to {end_date}",
            'days_processed': 0,
            'errors': [f"Date range too large: {total_days} days (max 50)"],
            'success': False
        }
    
    # Iterate through each date in the range
    current_date = start_dt
    day_count = 0
    
    while current_date <= end_dt:
        day_count += 1
        
        # Convert to YYYYMMDD format as required by API
        date_str = current_date.strftime('%Y%m%d')
        
        # Show progress for longer operations with rate limit info
        if total_days > 7:
            rate_stats = get_current_api_call_rate()
            print(f"Progress: Day {day_count}/{total_days} ({date_str}) - API calls: {rate_stats['calls_last_minute']}/60")
        
        # Call API for this date (with enhanced smart rate limiting)
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
    
    final_rate_stats = get_current_api_call_rate()
    print(f"Completed fetching {total_days} days. Found {len(all_bookings)} total bookings.")
    print(f"Final API rate: {final_rate_stats['calls_last_minute']}/60 calls in last minute")
    
    return {
        'bookings': all_bookings,
        'total_count': len(all_bookings),
        'date_range': f"{start_date} to {end_date}",
        'days_processed': total_days,
        'errors': errors,
        'success': len(errors) == 0,
        'rate_stats': final_rate_stats
    }


def get_today_bookings(api_id: str, api_key: str) -> Dict[str, Any]:
    """
    Get bookings changed today with enhanced rate limiting
    
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
    
    rate_stats = get_current_api_call_rate()
    
    if response.ok and "html" not in response.text.lower():
        try:
            # Check if response text is empty
            if not response.text.strip():
                return {
                    'bookings': [],
                    'date': today.strftime('%Y-%m-%d'),
                    'success': True,
                    'error': None,
                    'message': 'No bookings found for today',
                    'rate_stats': rate_stats
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
                    'raw_response': data,
                    'rate_stats': rate_stats
                }
            
            # Extract bookings from response
            bookings = data.get('bookings', [])
            
            return {
                'bookings': bookings,
                'date': today.strftime('%Y-%m-%d'),
                'success': True,
                'error': None,
                'raw_response': data,  # Include raw response for debugging
                'rate_stats': rate_stats
            }
            
        except json.JSONDecodeError as e:
            return {
                'bookings': [],
                'date': today.strftime('%Y-%m-%d'), 
                'success': False,
                'error': f"JSON decode error: {str(e)}",
                'raw_text': response.text[:1000],  # Include raw text for debugging
                'rate_stats': rate_stats
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
            'status_code': getattr(response, 'status_code', 'Unknown'),
            'rate_stats': rate_stats
        }


def get_last_n_days_bookings(
    days: int, 
    api_id: str, 
    api_key: str
) -> Dict[str, Any]:
    """
    Get bookings changed in the last N days with enhanced rate limiting
    
    Args:
        days: Number of days to look back
        api_id: API ID from secrets
        api_key: API key from secrets
        
    Returns:
        Dictionary with recent bookings
    """
    
    # Check for reasonable limits
    if days > 50:
        return {
            'bookings': [],
            'total_count': 0,
            'success': False,
            'error': f"Too many days requested: {days} (max 50 for rate limiting)"
        }
    
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days-1)
    
    return get_recent_bookings_for_date_range(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        api_id=api_id,
        api_key=api_key,
        booking_type="ALL"
    )
import requests
import json
import csv
import argparse
import sys
from typing import Optional, Dict, Any, List


class HolidayNisekoAPI:
    def __init__(self, username: str, password: str):
        """
        Initialize the Holiday Niseko API client
        
        Args:
            username (str): Your API username
            password (str): Your API password
        """
        self.base_url = "https://holidayniseko.com/api"
        self.username = "Andrew"
        self.password = "79J3QwKJ2fB5PRH"
        self.session = requests.Session()
        
        # Set up authentication headers - try multiple common formats
        self.session.headers.update({
            'Content-Type': 'application/json',
            'username': self.username,
            'password': self.password,
            'X-Username': self.username,
            'X-Password': self.password
        })
        
        # Also set up Basic Auth as fallback
        self.session.auth = (self.username, self.password)
    
    def get_bookings_by_checkin_date(self, date: str) -> Dict[str, Any]:
        """
        Get bookings from the API using query parameter ?date=yyyymmdd
        
        Args:
            date (str): Check-in date in YYYYMMDD or YYYY-MM-DD format
            
        Returns:
            dict: Exact API response without any filtering
            
        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            # Normalize the date format to YYYYMMDD
            if '-' in date:
                clean_date = date.replace('-', '')
            else:
                clean_date = date
            
            # Validate date format
            if len(clean_date) != 8 or not clean_date.isdigit():
                raise ValueError(f"Invalid date format: {date}. Use YYYYMMDD or YYYY-MM-DD")
            
            # Use query parameter approach: /api/bookings?date=yyyymmdd
            url = f"{self.base_url}/bookings"
            params = {'date': clean_date}
            
            print(f"Calling endpoint: {url}?date={clean_date}")
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting bookings for date {date}: {e}")
            raise
    
    def get_bookings(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get bookings from the API (single page, max 20 results)
        
        Args:
            params (dict, optional): Query parameters to filter bookings
            
        Returns:
            dict: API response containing booking data
            
        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            url = f"{self.base_url}/bookings"
            response = self.session.get(url, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            raise
    
    def get_all_bookings(self, params: Optional[Dict[str, Any]] = None) -> list:
        """
        Get ALL bookings from the API by handling pagination automatically
        
        Args:
            params (dict, optional): Query parameters to filter bookings
            
        Returns:
            list: All booking records combined from all pages
            
        Raises:
            requests.RequestException: If the API request fails
        """
        all_bookings = []
        page = 1
        
        # Set up parameters with pagination
        request_params = params.copy() if params else {}
        
        try:
            while True:
                # Add page parameter (common pagination patterns)
                request_params['page'] = page
                
                print(f"Fetching page {page}...")
                response_data = self.get_bookings(request_params)
                
                # Extract bookings from response
                if 'bookings' in response_data:
                    bookings = response_data['bookings']
                elif 'data' in response_data:
                    bookings = response_data['data']
                elif isinstance(response_data, list):
                    bookings = response_data
                else:
                    bookings = response_data
                
                # If no bookings returned, we've reached the end
                if not bookings or len(bookings) == 0:
                    break
                
                all_bookings.extend(bookings)
                
                # If we got less than 20 results, we're on the last page
                if len(bookings) < 20:
                    break
                    
                page += 1
            
            print(f"Retrieved {len(all_bookings)} total bookings across {page} pages")
            return all_bookings
            
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving all bookings: {e}")
            raise
    
    def export_bookings_to_csv(self, filename: str = "bookings.csv", params: Optional[Dict[str, Any]] = None) -> None:
        """
        Export all bookings to a CSV file with all fields as columns
        
        Args:
            filename (str): Name of the CSV file to create
            params (dict, optional): Query parameters to filter bookings
        """
        try:
            # Get all bookings
            print("Retrieving all bookings...")
            all_bookings = self.get_all_bookings(params)
            
            if not all_bookings:
                print("No bookings found to export.")
                return
            
            # Flatten nested dictionaries and collect all possible field names
            flattened_bookings = []
            all_fields = set()
            
            for booking in all_bookings:
                flattened_booking = self._flatten_dict(booking)
                flattened_bookings.append(flattened_booking)
                all_fields.update(flattened_booking.keys())
            
            # Sort field names for consistent column order
            fieldnames = sorted(list(all_fields))
            
            # Write to CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for booking in flattened_bookings:
                    # Fill missing fields with empty strings
                    row = {field: booking.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            print(f"Successfully exported {len(all_bookings)} bookings to {filename}")
            print(f"CSV contains {len(fieldnames)} columns: {', '.join(fieldnames[:10])}{'...' if len(fieldnames) > 10 else ''}")
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            raise
    
    def export_checkin_bookings_to_csv(self, date: str, filename: Optional[str] = None) -> None:
        """
        Export bookings for a specific date to CSV using query parameter
        
        Args:
            date (str): Check-in date in YYYYMMDD or YYYY-MM-DD format
            filename (str, optional): CSV filename. If not provided, uses date in filename
        """
        if filename is None:
            clean_date = date.replace('-', '') if '-' in date else date
            filename = f"bookings_checkin_{clean_date}.csv"
        
        try:
            print(f"Retrieving bookings for date {date}...")
            response_data = self.get_bookings_by_checkin_date(date)
            
            # Extract bookings from response (adjust based on API structure)
            if 'bookings' in response_data:
                bookings = response_data['bookings']
            elif 'data' in response_data:
                bookings = response_data['data']
            elif isinstance(response_data, list):
                bookings = response_data
            else:
                bookings = [response_data] if response_data else []
            
            if not bookings:
                print(f"No bookings found for date {date}")
                return
            
            # Flatten and export to CSV
            flattened_bookings = []
            all_fields = set()
            
            for booking in bookings:
                flattened_booking = self._flatten_dict(booking)
                flattened_bookings.append(flattened_booking)
                all_fields.update(flattened_booking.keys())
            
            # Sort field names for consistent column order
            fieldnames = sorted(list(all_fields))
            
            # Write to CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for booking in flattened_bookings:
                    row = {field: booking.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            print(f"Successfully exported {len(bookings)} bookings for date {date} to {filename}")
            print(f"CSV contains {len(fieldnames)} columns")
            
        except Exception as e:
            print(f"Error exporting bookings to CSV: {e}")
            raise
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """
        Flatten a nested dictionary to create column names for CSV
        
        Args:
            d (dict): Dictionary to flatten
            parent_key (str): Prefix for keys
            sep (str): Separator for nested keys
            
        Returns:
            dict: Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Handle lists by converting to string or flattening if list of dicts
                if v and isinstance(v[0], dict):
                    for i, item in enumerate(v):
                        items.extend(self._flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((new_key, ', '.join(map(str, v)) if v else ''))
            else:
                items.append((new_key, v))
        return dict(items)


# Example usage
if __name__ == "__main__":
    # Set your credentials here
    USERNAME = "your_username_here"
    PASSWORD = "your_password_here"
    
    parser = argparse.ArgumentParser(description='Holiday Niseko Bookings API Client')
    parser.add_argument('--date', help='Check-in date in YYYYMMDD format (e.g., 20251218)')
    parser.add_argument('--output', '-o', help='Output CSV filename')
    parser.add_argument('--all', action='store_true', help='Export all bookings (with pagination)')
    parser.add_argument('--test-auth', action='store_true', help='Test authentication methods only')
    
    args = parser.parse_args()
    
    # Initialize the API client with hardcoded credentials
    api = HolidayNisekoAPI(USERNAME, PASSWORD)
    
    try:
        # Export bookings for specific date using query parameter
        if args.date:
            filename = args.output or f"bookings_checkin_{args.date.replace('-', '')}.csv"
            print(f"Getting bookings for {args.date}...")
            api.export_checkin_bookings_to_csv(args.date, filename)
        
        # Export all bookings
        elif args.all:
            filename = args.output or "all_holiday_niseko_bookings.csv"
            print("Getting all bookings...")
            api.export_bookings_to_csv(filename)
        
        # Test authentication if requested
        elif args.test_auth:
            print("Testing authentication methods...")
            # Simple auth test for query parameter approach
            try:
                response = api.session.get(f"{api.base_url}/bookings", params={'date': '20251218'})
                print(f"Query parameter test: {response.status_code}")
            except Exception as e:
                print(f"Query parameter test failed: {e}")
            sys.exit(0)
        
        else:
            print("Please specify either --date YYYYMMDD or --all")
            print("Use --help for more options")
            print("\nExample commands:")
            print("  python list_bookings.py --date 20251218")
            print("  python list_bookings.py --all")
        
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
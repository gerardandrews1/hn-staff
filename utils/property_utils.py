from pathlib import Path
import json

def get_prop_management():
    """
    Load property management mappings from JSON file.
    Returns a dictionary mapping property names to their management companies.
    """
    try:
        # Print current working directory
        import os
        print(f"Current working directory: {os.getcwd()}")
        
        # Get the path to the data file
        data_path = Path(__file__).parent.parent / "data" / "property_management.json"
        print(f"Attempting to load from: {data_path}")
        print(f"Does file exist? {data_path.exists()}")
        
        if not data_path.exists():
            raise FileNotFoundError(f"JSON file not found at {data_path}")
            
        # Load the JSON file
        with open(data_path, "r", encoding='utf-8') as f:
            management_by_company = json.load(f)
            print("Successfully loaded JSON:")
            print(json.dumps(management_by_company, indent=2)[:500])  # Print first 500 chars
            
            # Create flat dictionary
            property_management = {}
            for company, properties in management_by_company.items():
                print(f"Processing company: {company} with {len(properties)} properties")
                for prop in properties:
                    property_management[prop] = company
                    
            print("Final mapping created with keys:", len(property_management))
            return property_management
            
    except Exception as e:
        import traceback
        print(f"Error loading property management data:")
        print(traceback.format_exc())
        return {}

def match_property_management(hotel_name: str, management_dict: dict) -> str:
    """Match hotel name with management company using partial matching"""
    if not hotel_name or not management_dict:
        print(f"Invalid input - hotel_name: {hotel_name}, dict size: {len(management_dict)}")
        return "None"
    
    print(f"\nTrying to match: {hotel_name}")
    
    # Get base name without room numbers or types
    base_name = hotel_name.split(' - ')[0].split(' (')[0].strip()
    print(f"Base name: {base_name}")
    
    # Exact match first
    if hotel_name in management_dict:
        print(f"Exact match found: {management_dict[hotel_name]}")
        return management_dict[hotel_name]
        
    if base_name in management_dict:
        print(f"Base name match found: {management_dict[base_name]}")
        return management_dict[base_name]
    
    # Then try partial matching
    hotel_lower = base_name.lower()
    for prop_name, company in management_dict.items():
        prop_lower = prop_name.lower()
        
        # Try both directions of partial matching
        if hotel_lower in prop_lower or prop_lower in hotel_lower:
            print(f"Partial match found: {company} via {prop_name}")
            return company
            
    print(f"No match found for: {hotel_name}")
    return "None"
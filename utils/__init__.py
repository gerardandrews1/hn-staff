# utils/__init__.py
import os
import glob
from pathlib import Path
from typing import Dict, List

def get_prop_management() -> Dict[str, List[str]]:
    """
    Get the management dictionaries for properties.
    Returns a dictionary mapping management company codes to their property lists.
    
    Returns:
        Dict[str, List[str]]: Management dictionary
    """
    try:
        # First try the streamlit cloud path
        props_directory = "data/"
        if not os.path.exists(props_directory):
            # If not found, try the local development path
            props_directory = os.path.join(
                Path(__file__).parent.parent,
                "data"
            )
        
        management_dict = {}
        
        # Default property lists if files don't exist
        default_properties = {
            "hn_props": [
                "Mountain Side",
                "The Orchards",
                "Yasushi"
            ],
            "h2_props": [
                "Aspect",
                "Haven",
                "Koa"
            ],
            "wow_props": [
                "Landmark View",
                "Ezo Views"
            ],
            "nisade_props": [
                "Aspect Niseko",
                "Skyline",
                "The Maples"
            ],
            "vn_props": [
                "The Vale Niseko"
            ],
            "mnk_props": [
                "Niseko Landmark"
            ],
            "hokkaido_travel_props": [
                "Niseko Central"
            ]
        }
        
        # Try to read from files first
        file_list = glob.glob(os.path.join(props_directory, "*.txt"))
        
        if file_list:  # If we found property files
            for file_path in file_list:
                try:
                    with open(file_path, 'r', encoding='utf-8') as text_file:
                        content = text_file.read().strip()
                        if content:  # If file has content
                            prop_list = [x.strip() for x in content.split(",")]
                            key = Path(file_path).stem  # Get filename without extension
                            management_dict[key] = prop_list
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    # Use default if file read fails
                    key = Path(file_path).stem
                    management_dict[key] = default_properties.get(key, [])
        else:
            # If no files found, use default properties
            management_dict = default_properties
        
        return management_dict
    
    except Exception as e:
        print(f"Error in get_prop_management: {e}")
        # Return default properties if everything fails
        return default_properties
# models/check_in_instructions.py

import streamlit as st
from dataclasses import dataclass
from typing import Dict, Optional, Any, Union, List

@dataclass
class CheckInInstructions:
    """
    Class to manage and display property check-in instructions.
    Loads instructions from config and formats them for different outputs.
    """
    
    def __init__(self):
        """Initialize with instructions from Streamlit secrets"""
        self.instructions = st.secrets.get("property_instructions", {})
        
    def write_instructions(self, vendor_name: str, room_name: Optional[str] = None) -> None:
        """
        Write minimal check-in instructions UI with copy button
        
        Args:
            vendor_name: Name of the property vendor
            room_name: Optional specific room name
        """
        try:
            instructions = self._find_instructions(vendor_name, room_name)
            
            if not instructions:
                st.warning(f"No check-in instructions found for {vendor_name} - {room_name}")
                return
            
            plain_text = self._prepare_clipboard_text(instructions)
            sanitized_text = plain_text.split("Kind regards")[0].strip()
            
            container = st.container()
            
            with container:
                if st.button("Check-in Instructions", help="Copy check-in instructions"):
                    with st.expander("Instructions", expanded=True):
                        st.code(sanitized_text)
                        
        except Exception as e:
            st.error(f"Error with check-in instructions: {str(e)}")

    def _format_code_instructions(self, code: Union[str, List[str]]) -> str:
        """Format door code instructions, handling both string and list inputs"""
        if isinstance(code, list):
            return "\n".join(code)
        return str(code)

    def _format_address(self, address: str) -> str:
        """Format address into two lines based on common patterns"""
        if not address:
            return ""
            
        parts = address.split(", ")
        if "Hokkaido" in address:
            street_parts = []
            prefecture_parts = []
            found_hokkaido = False
            
            for part in parts:
                if "Hokkaido" in part or found_hokkaido:
                    found_hokkaido = True
                    prefecture_parts.append(part)
                else:
                    street_parts.append(part)
                    
            line1 = ", ".join(street_parts)
            line2 = ", ".join(prefecture_parts)
            
            return f"{line1}\n{line2}"
            
        if len(parts) > 1:
            return f"{', '.join(parts[:-1])}\n{parts[-1]}"
            
        return address

    def _format_access_instructions_html(self, instructions: Dict[str, Any]) -> str:
        """Format access instructions section based on available information"""
        check_in = instructions.get('checkInInstructions')
        check_out = instructions.get('checkOutInstructions')
        
        if check_in or check_out:
            instructions_html = []
            if check_in:
                instructions_html.append(
                    "<p><strong>Check-in Instructions:</strong><br>"
                    f"{check_in}</p>"
                )
            if check_out:
                instructions_html.append(
                    "<p><strong>Check-out Instructions:</strong><br>"
                    f"{check_out}</p>"
                )
            return ''.join(instructions_html)
        
        exterior_code = instructions.get('exteriorDoorCode')
        unit_code = instructions.get('doorCode')
        
        if not unit_code and not exterior_code:
            return ""
            
        if exterior_code:
            formatted_exterior = self._format_code_instructions(exterior_code)
            formatted_unit = self._format_code_instructions(unit_code)
            return (
                "<p><strong>Entry Instructions:</strong><br>"
                f"Building Entry:<br>{formatted_exterior.replace(chr(10), '<br>')}<br>"
                f"Unit Entry:<br>{formatted_unit.replace(chr(10), '<br>')}</p>"
            )
        else:
            formatted_code = self._format_code_instructions(unit_code)
            return (
                "<p><strong>Entry Instructions:</strong><br>"
                f"{formatted_code.replace(chr(10), '<br>')}</p>"
            )

    def _format_access_instructions_text(self, instructions: Dict[str, Any]) -> str:
        """Format access instructions section for plain text"""
        check_in = instructions.get('checkInInstructions')
        check_out = instructions.get('checkOutInstructions')
        
        if check_in or check_out:
            instructions_text = []
            if check_in:
                instructions_text.append(f"Check-in Instructions:\n{check_in}")
            if check_out:
                instructions_text.append(f"\nCheck-out Instructions:\n{check_out}")
            return '\n'.join(instructions_text)
        
        exterior_code = instructions.get('exteriorDoorCode')
        unit_code = instructions.get('doorCode')
        
        if not unit_code and not exterior_code:
            return ""
            
        if exterior_code:
            formatted_exterior = self._format_code_instructions(exterior_code)
            formatted_unit = self._format_code_instructions(unit_code)
            return (
                f"Entry Instructions:\n"
                f"Building Entry:\n{formatted_exterior}\n"
                f"Unit Entry:\n{formatted_unit}"
            )
        else:
            formatted_code = self._format_code_instructions(unit_code)
            return f"Entry Instructions:\n{formatted_code}"

    def _prepare_clipboard_html(self, instructions: Dict[str, Any]) -> str:
        """Format instructions as HTML for rich clipboard content"""
        access_instructions = self._format_access_instructions_html(instructions)
        formatted_address = self._format_address(instructions.get('address', ''))
        
        html_parts = [
            "<div style='font-family: Arial, sans-serif; line-height: 1.6;'>",
            f"<p><strong>Please see the entry details for</strong> {instructions.get('name')} - {instructions.get('description', '')}</p>",
            access_instructions,
            "<p><strong>Address:</strong><br>",
            formatted_address.replace('\n', '<br>'),
            "</p>",
            f"<p><strong>Map Code:</strong><br>",
            f"{instructions.get('mapCode', '')}</p>",
            "<p><strong>Google Maps:</strong><br>",
            f"<a href='{instructions.get('googleMaps', '')}'>{instructions.get('googleMaps', '')}</a></p>",
            "<p><strong>Parking:</strong><br>",
            f"{instructions.get('parking', '')}</p>",
            "If you're arriving after 11pm this must be communicated in advance.</p>",
            "<p><strong>Please Note:</strong><br>",
            "If you have not already completed the online check-in please do so here:<br>",
            "<a href='https://holidayniseko.com/welcome'>https://holidayniseko.com/welcome</a></p>",
            "<p><strong>Contact Information:</strong><br>",
            "Email: <a href='mailto:frontdesk@holidayniseko.com'>frontdesk@holidayniseko.com</a><br>",
            "Tel: +81-136-21-6221 (08:30 - 18:30)<br>",
            "Tel: +81-80-6910-7502 (18:30 - 23:00)<br>",
            "Emergency Only: +81-80-6066-6891 (charges apply for non-emergency calls)</p>",
            "<p><strong>Check-in/Check-out Times:</strong><br>",
            "Check in is at 15:00 or after and Check out at 10:00am<br>",
            "Late check outs are not possible and charges may apply.</p>",
            "</div>"
        ]
        
        return ''.join(html_parts)

    def _prepare_clipboard_text(self, instructions: Dict[str, Any]) -> str:
        """Format instructions for plain text clipboard"""
        access_instructions = self._format_access_instructions_text(instructions)
        formatted_address = self._format_address(instructions.get('address', ''))
        
        text_parts = [
            f"Please see the entry details for {instructions.get('name')} - {instructions.get('description', '')}",
            "",
            access_instructions,
            "",
            "Address:",
            formatted_address,
            "",
            "Map Code:",
            instructions.get('mapCode', ''),
            "",
            "Google Maps:",
            instructions.get('googleMaps', ''),
            "",
            "Parking:",
            instructions.get('parking', ''),
            "",
            "If you're arriving after 11pm this must be communicated in advance.",
            "",
            "Please Note:",
            "If you have not already completed the online check-in please do so here:",
            "https://holidayniseko.com/welcome",
            "",
            "Contact Information:",
            "Email: frontdesk@holidayniseko.com",
            "Tel: +81-136-21-6221 (08:30 - 18:30)",
            "Tel: +81-80-6910-7502 (18:30 - 23:00)",
            "",
            "Emergency Only: +81-80-6066-6891 (charges apply for non-emergency calls)",
            "",
            "Check-in/Check-out Times:",
            "Check-in is at 15:00 or after and check-out at 10:00am",
            "Late check outs are not possible and charges may apply."
        ]
        
        return '\n'.join(text_parts)

    def _find_instructions(self, vendor_name: str, room_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Find instructions by matching vendor and room to TOML key"""
        try:
            vendor_key = vendor_name.upper().replace(" ", "_")
            
            if room_name and "#" in room_name:
                base_name, room_number = room_name.split("#")
                room_number = f"#{room_number.strip()}"
                base_name = base_name.strip()
                room_key = base_name.upper().replace(" ", "_") + "_" + room_number
            else:
                room_key = room_name.upper().replace(" ", "_") if room_name else ""
                
            search_key = f"{vendor_key}_{room_key}"
            
            return next((value for key, value in self.instructions.items() 
                        if search_key in key), None)
        except Exception as e:
            st.error(f"Error finding instructions: {str(e)}")
            return None
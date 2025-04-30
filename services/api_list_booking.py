# module to call the API list booking functionality
import os
import json
import requests
import streamlit as st

from ratelimit import limits

# decorator to throttle api calls 
@limits(calls = 15, period = 120)
def call_api(ebook_id, api_id, api_key):
    
    """
    Call API with wrapper only 15 calls
    per 2 min limit imposed
    Using API credentials

    """

    url = \
    f"https://api.roomboss.com/extws/hotel/v1/listBooking?bookingEid={ebook_id}"
    
    
    auth = (api_id, api_key)
    
    response = requests.get(url, auth = auth)

    if response.status_code != 200:
        st.write(f"{response.reason}\
                 {response.status_code}, check input")

    return response


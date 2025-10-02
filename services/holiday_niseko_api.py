# -*- coding: utf-8 -*-
# holiday_niseko_api.py
import requests
import streamlit as st
from typing import Optional, Dict, Any, List

class HolidayNisekoAPI:
    """
    Thin client for Holiday Niseko public API.
    Credentials are supplied by the caller (e.g., from st.secrets) — nothing hardcoded here.
    """

    def __init__(self, username: str, password: str, base_url: str = "https://holidayniseko.com/api"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "username": self.username,
            "password": self.password,
            "X-Username": self.username,
            "X-Password": self.password,
        })
        self.session.auth = (self.username, self.password)

    def get_bookings(self, params=None):
        url = f"{self.base_url}/bookings"
        r = self.session.get(url, params=params, timeout=30)
        if not r.ok:
            snippet = (r.text or "")[:300]
            raise requests.HTTPError(
                f"{r.status_code} {getattr(r,'reason','')} • URL={r.url} • Body={snippet}"
            )
        return r.json()

    def get_bookings_by_checkin_date(self, date: str) -> Dict[str, Any]:
        clean_date = date.replace("-", "")
        if len(clean_date) != 8 or not clean_date.isdigit():
            raise ValueError(f"Invalid date format: {date}. Use YYYYMMDD or YYYY-MM-DD")
        params = {"date>=": clean_date}  # Changed from "date" to "date>="
        return self.get_bookings(params=params)

    def get_all_bookings(self, params: Optional[Dict[str, Any]] = None, page_param: str = "page") -> List[Dict[str, Any]]:
        page = 0
        out: List[Dict[str, Any]] = []
        base_params = dict(params or {})

        while True:
            current_params = base_params.copy()
            current_params[page_param] = page
            
            try:
                payload = self.get_bookings(params=current_params)
            except Exception as e:
                break

            # Extract bookings
            if isinstance(payload, list):
                bookings = payload
            elif "bookings" in payload:
                bookings = payload["bookings"]
            elif "data" in payload:
                bookings = payload["data"]
            else:
                bookings = [payload] if payload else []

            if not bookings:
                break

            out.extend(bookings)

            # Stop if we got fewer than 20 bookings (last page)
            if len(bookings) < 20:
                break

            page += 1
            
            # Safety limit
            if page > 100:
                break
        
        return out
        


    def get_active_eids_by_checkin_date(self, date: str) -> List[str]:
        clean_date = date.replace("-", "")
        if len(clean_date) != 8 or not clean_date.isdigit():
            raise ValueError(f"Invalid date format: {date}. Use YYYYMMDD or YYYY-MM-DD")
        
        all_bookings = self.get_all_bookings(params={"date": clean_date})
        
        from utils.normalize_upcoming_arrivals import normalize_upcoming_arrivals
        df = normalize_upcoming_arrivals(all_bookings)
        
        if df.empty:
            return []
        
        if "active" in df.columns:
            df = df[df["active"] != 0]
        
        if "eid" in df.columns:
            return df["eid"].astype(str).tolist()
        else:
            return []

    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(HolidayNisekoAPI.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                if v and isinstance(v[0], dict):
                    for i, item in enumerate(v):
                        items.extend(HolidayNisekoAPI.flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((new_key, ", ".join(map(str, v)) if v else ""))
            else:
                items.append((new_key, v))
        return dict(items)
# -*- coding: utf-8 -*-
import requests
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
            # Send multiple common header variants in case the API expects them
            "username": self.username,
            "password": self.password,
            "X-Username": self.username,
            "X-Password": self.password,
        })
        # Also set HTTP Basic as a fallback
        self.session.auth = (self.username, self.password)

    # ---------------- Core fetchers ----------------

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
        """
        Bookings filtered by check-in date via query param ?date=YYYYMMDD (or YYYY-MM-DD).
        Returns the raw JSON payload (dict/list).
        """
        clean_date = date.replace("-", "")
        if len(clean_date) != 8 or not clean_date.isdigit():
            raise ValueError(f"Invalid date format: {date}. Use YYYYMMDD or YYYY-MM-DD")

        params = {"date": clean_date}
        return self.get_bookings(params=params)

    def get_all_bookings(self, params: Optional[Dict[str, Any]] = None, page_param: str = "page") -> List[Dict[str, Any]]:
        """
        Auto-pagination: keeps calling /bookings?page=N until no results or < 20 results.
        Returns a flat list of booking dicts.
        """
        page = 1
        out: List[Dict[str, Any]] = []
        base_params = dict(params or {})

        while True:
            base_params[page_param] = page
            payload = self.get_bookings(params=base_params)

            # Extract bookings from varied payload shapes
            if isinstance(payload, list):
                bookings = payload
            elif "bookings" in payload:
                bookings = payload["bookings"]
            elif "data" in payload:
                bookings = payload["data"]
            else:
                # Fallback: unknown shape; try to treat as single booking
                bookings = [payload] if payload else []

            if not bookings:
                break

            out.extend(bookings)

            if len(bookings) < 20:
                break

            page += 1

        return out
    
    def get_active_eids_by_checkin_date(self, date: str) -> List[str]:
        """
        Get only the eIDs for active bookings on a specific check-in date.
        Returns a list of eID strings.
        """
        payload = self.get_bookings_by_checkin_date(date)
        
        # Use your existing normalize function to get the data in a consistent format
        from utils.normalize_upcoming_arrivals import normalize_upcoming_arrivals
        df = normalize_upcoming_arrivals(payload)
        
        if df.empty:
            return []
        
        # Filter for active bookings only
        if "active" in df.columns:
            df = df[df["active"] != 0]
        
        # Extract eIds
        if "eid" in df.columns:
            return df["eid"].astype(str).tolist()
        else:
            return []

    # ---------------- Utilities ----------------

    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        """
        Flatten nested dicts/lists for CSV/DF convenience.
        """
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

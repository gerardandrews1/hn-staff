from dataclasses import dataclass
import streamlit as st
from typing import Optional

@dataclass
class RoombossConfig:
    api_url: str
    api_key: str

@dataclass
class DatabaseConfig:
    host: str
    port: str
    database: str
    user: str
    password: str

@dataclass
class SentryConfig:
    dsn: str
    environment: str

@dataclass
class AppConfig:
    roomboss: RoombossConfig
    database: DatabaseConfig
    sentry: SentryConfig
    
    @classmethod
    def from_secrets(cls) -> 'AppConfig':
        """Create config from Streamlit secrets"""
        return cls(
            roomboss=RoombossConfig(
                api_url=st.secrets["roomboss"]["api_url"],
                api_key=st.secrets["roomboss"]["api_key"]
            ),
            database=DatabaseConfig(
                host=st.secrets["staff_portal_db"]["host"],
                port=st.secrets["staff_portal_db"]["port"],
                database=st.secrets["staff_portal_db"]["database"],
                user=st.secrets["staff_portal_db"]["user"],
                password=st.secrets["staff_portal_db"]["password"]
            ),
            sentry=SentryConfig(
                dsn=st.secrets["sentry"]["dsn"],
                environment=st.secrets["sentry"]["environment"]
            )
        )

# App Settings
APP_SETTINGS = {
    "page_title": "HN Staff Portal",
    "page_icon": "🏂",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Feature flags
FEATURES = {
    "enable_booking_modification": False,
    "enable_monitoring": True,
    "enable_error_reporting": True
}

# Constants
CACHE_TTL = 300  # 5 minutes
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
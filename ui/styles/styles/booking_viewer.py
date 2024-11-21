import streamlit as st

def apply_booking_viewer_styles():
    st.markdown("""
        <style>
        .metric-card {
            border: 1px solid #f0f2f6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .booking-header {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .stButton button {
            width: 100%;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
        }
        
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .status-confirmed {
            background-color: #dcfce7;
            color: #166534;
        }
        
        .status-pending {
            background-color: #fef9c3;
            color: #854d0e;
        }
        </style>
    """, unsafe_allow_html=True)
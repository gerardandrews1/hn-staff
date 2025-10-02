import streamlit as st

# Page config
st.set_page_config(
    page_title="Reservations Portal",
    page_icon="🏨",
    layout="centered"
)

# Header
st.subheader("Holiday Niseko")
st.markdown("---")

# Main Navigation - Internal Pages
st.subheader("Streamlit Pages")

col1, col2 = st.columns(2)

with col1:
    if st.button("Booking Viewer", use_container_width=True):
        st.switch_page("pages/1_📋_Booking_Viewer.py")
    if st.button("Recent Bookings", use_container_width=True):
        st.switch_page("pages/2_📊_Recent_Bookings.py")
    if st.button("Search & Quote", use_container_width=True):
        st.switch_page("pages/4_🔎_Search_&_Quote.py")
    

with col2:
    if st.button("Sales Dashboard", use_container_width=True):
        st.switch_page("pages/3_📈_Sales_Dashboard.py")
    if st.button("Upcoming Arrivals", use_container_width=True):
        st.switch_page("pages/4_📅_Upcoming_Arrivals.py")
    if st.button("Add Enquiry Email", use_container_width=True):
        st.switch_page("pages/5_Add_Enquiry_Email.py")        
    
st.markdown("---")

# External Resources
st.subheader("Resources & Guides")

col1, col2 = st.columns(2)

with col1:
    st.markdown("📝 [Door Codes](https://docs.google.com/spreadsheets/d/1zIkN35Z-3xUrD1rm4ru2ssC6h-cpTTgs0LNptnjmZms/edit?gid=1335146139#gid=1335146139)")
    st.markdown("📄 [Operations Report](https://docs.google.com/spreadsheets/d/1ePhxMrYe-KG1dknVvfh7_J0-8t8iD0_5ApUd0O5GGRs/edit?gid=0#gid=0)")
    st.markdown("📄 [Front Desk Manual](https://docs.google.com/document/d/1-R1zBxcY9sBP_ULDc7D0qaResj9OTU2s/r/edit/edit?tab=t.0)")
    st.markdown("📖 [Guest Services Guide (PDF)](https://holidayniseko.com/sites/default/files/2025-05/Holiday%20Niseko%20Guest%20Services%20Guide.pdf)")

with col2:
    st.markdown("📄 [Check-in Instructions](https://docs.google.com/document/d/1wRDuk0MsDjbPXvxvfxYVa_3sWPfbWvNs6xtJj3llMjU/edit?tab=t.0)")
    st.markdown("🍷 [Wine Dine Niseko](https://www.winedineniseko.com/)")
    st.markdown("🚌 [Hirafu Free Shuttle Information](https://hirafufreebus.com/top#about)")
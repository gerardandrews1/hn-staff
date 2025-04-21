import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

# Load the data from the Excel file
df = pd.read_excel('pages/properties_20241123_195644-1.xlsx')

# Set the page configuration
st.set_page_config(page_title="Property Dashboard", layout="wide")

# Add a title and description
st.header("Property Dashboard")
st.write("This dashboard allows you to explore and filter properties.")

# Add filters in the sidebar
with st.sidebar:
    st.subheader("Filters")

    # Filter by property type
    property_types = df['property_type'].unique()
    property_type = st.multiselect("Select property type(s)", property_types, default=property_types)
    if property_type:
        df = df[df['property_type'].isin(property_type)]

    # Filter by location
    location_options = df['location'].unique()
    location = st.multiselect("Select location(s)", location_options, default=location_options)
    if location:
        df = df[df['location'].isin(location)]

    # Filter by price range
    min_price = st.number_input("Minimum Price", min_value=0.0, step=1000.0, value=df['price'].min())
    max_price = st.number_input("Maximum Price", min_value=0.0, step=1000.0, value=df['price'].max())
    df = df[(df['price'] >= min_price) & (df['price'] <= max_price)]

# Display the filtered data
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_columns("price", type="numericColumn", precision=0)
gb.configure_columns("size_tsubo", type="numericColumn", precision=2)
gb.configure_columns("price_per_tsubo", type="numericColumn", precision=0)
gb.configure_linked_rich_data(df, "url", "title")
grid_options = gb.build()

grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    fit_columns_on_grid_load=True,
    use_container_width=True,
)
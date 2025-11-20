import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Bookings",
    page_icon="📊",
    layout="wide"
)

@st.cache_resource  # Use cache_resource for connections
def create_gsheet_connection():
    """Create connection to Google Sheets - cached"""
    # Define the scope
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Create credentials from the service account JSON info in secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["general"],
        scopes=scope
    )
    
    # Authorize the client
    client = gspread.authorize(credentials)
    return client

@st.cache_data(ttl=300, hash_funcs={gspread.client.Client: lambda x: None})  # Cache for 5 minutes, ignore gspread client
def get_booking_data(sheet_tab="accommodation"):
    """Get booking data from Google Sheet - cached to prevent repeated API calls"""
    try:
        client = create_gsheet_connection()
        
        # Open the Google Sheet by name
        sheet_name = st.secrets["gcp_service_account"]["bookings_sheet_name"]
        spreadsheet = client.open(sheet_name)
        
        # Select the specific worksheet (tab)
        if sheet_tab == "accommodation":
            worksheet = spreadsheet.worksheet("accommodation")
        elif sheet_tab == "guest_services":
            worksheet = spreadsheet.worksheet("Guest Services")
        elif sheet_tab == "accommodation_last_winter":
            worksheet = spreadsheet.worksheet("accommodation_last_winter")
        elif sheet_tab == "guest_services_last_winter":
            worksheet = spreadsheet.worksheet("guest_services_last_winter")
        else:
            worksheet = spreadsheet.sheet1  # fallback to first sheet
        
        # Get all data
        data = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info(f"Make sure the sheet '{sheet_tab}' exists in your Google Sheet")
        return pd.DataFrame()

@st.cache_data
def process_booking_data(df):
    """Process booking data with common transformations - cached"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # Convert Package ID to string
    if 'Package ID' in df.columns:
        df['Package ID'] = df['Package ID'].astype(str)
    
    # Convert other numeric columns
    numeric_columns = ['Item Sell Price', 'Nights/Days', 'Zero Stay']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Parse dates
    if 'Created (Japan Standard Time)' in df.columns:
        df['Created_Date'] = pd.to_datetime(df['Created (Japan Standard Time)'], errors='coerce')
    
    return df

@st.cache_data
def get_filtered_data(df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True):
    """Apply filters to data - cached based on filter combinations"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply vendor filter
    if selected_vendors and 'Vendor' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Vendor'].isin(selected_vendors)]
    
    # Apply product filter
    if selected_products and 'Product' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Product'].isin(selected_products)]
    
    # Apply vendor company filter
    if selected_vendor_companies and 'Vendor Company' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Vendor Company'].isin(selected_vendor_companies)]
    
    # Filter out zero stays if requested
    if exclude_zero_stays and 'Zero Stay' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Zero Stay'] != 1]
    
    return filtered_df

@st.cache_data
def calculate_metrics(df):
    """Calculate key metrics - cached"""
    if df.empty:
        return {'total_bookings': 0, 'total_revenue': 0, 'total_nights': 0}
    
    total_bookings = df['Package ID'].nunique() if 'Package ID' in df.columns else len(df)
    
    total_revenue = 0
    if 'Item Sell Price' in df.columns:
        total_revenue = df['Item Sell Price'].sum()
    
    total_nights = 0
    if 'Nights/Days' in df.columns:
        total_nights = df['Nights/Days'].sum()
    
    return {
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_nights': total_nights
    }

def get_last_winter_totals(sheet_type, selected_vendors=None, selected_products=None, selected_vendor_companies=None):
    """Get totals from last winter for comparison, filtered by vendor/product/vendor company if specified"""
    try:
        last_winter_df = get_booking_data(f"{sheet_type}_last_winter")
        if last_winter_df.empty:
            return None
        
        # Process the data
        last_winter_df = process_booking_data(last_winter_df)
        
        # Apply filters and get metrics
        filtered_df = get_filtered_data(last_winter_df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
        return calculate_metrics(filtered_df)
        
    except:
        return None

def get_same_date_last_year_totals(sheet_type, selected_vendors=None, selected_products=None, selected_vendor_companies=None):
    """Get totals from same date last year (bookings created by this date last year), filtered by vendor/product/vendor company"""
    try:
        last_winter_df = get_booking_data(f"{sheet_type}_last_winter")
        if last_winter_df.empty:
            return None
        
        # Process the data
        last_winter_df = process_booking_data(last_winter_df)
        
        # Get current date and calculate same date last year
        today = datetime.now()
        same_date_last_year = today.replace(year=today.year - 1)
        
        # Filter for bookings created by this date last year
        if 'Created_Date' in last_winter_df.columns:
            filtered_df = last_winter_df[last_winter_df['Created_Date'] <= same_date_last_year]
        else:
            return None
        
        # Apply other filters and get metrics
        filtered_df = get_filtered_data(filtered_df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
        return calculate_metrics(filtered_df)
        
    except:
        return None

def main():
    st.title("📊 Bookings Dashboard")
    
    # Add a manual refresh button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    
    # Add the data source picker at the top
    sheet_type = st.selectbox(
        "Select Data Source:",
        options=["accommodation", "guest_services"],
        format_func=lambda x: "🏨 Accommodation" if x == "accommodation" else "🛎️ Guest Services"
    )
    
    # Load and process the main data (this will be cached)
    with st.spinner('Loading data...'):
        df = get_booking_data(sheet_type)
        if not df.empty:
            df = process_booking_data(df)
    
    if not df.empty:
        # Create sidebar for filters
        with st.sidebar:
            st.subheader("🔍 Filters")
            
            # Get unique values for filters (from cached data)
            vendors = sorted(df['Vendor'].dropna().unique()) if 'Vendor' in df.columns else []
            
            # Vendor filter
            selected_vendors = st.multiselect(
                "Select Vendors:",
                options=vendors
            )
            
            # Product filter - CASCADE based on selected vendors
            if selected_vendors and 'Vendor' in df.columns and 'Product' in df.columns:
                # Filter products to only show those from selected vendors
                vendor_filtered_df = df[df['Vendor'].isin(selected_vendors)]
                products = sorted(vendor_filtered_df['Product'].dropna().unique())
            else:
                # Show all products if no vendor selected
                products = sorted(df['Product'].dropna().unique()) if 'Product' in df.columns else []
            
            selected_products = st.multiselect(
                "Select Products:", 
                options=products
            )
            
            # Vendor Company filter
            vendor_companies = sorted(df['Vendor Company'].dropna().unique()) if 'Vendor Company' in df.columns else []
            vendor_company_options = ["All except Holiday Niseko"] + vendor_companies
            selected_vendor_companies_raw = st.multiselect(
                "Select Vendor Companies:",
                options=vendor_company_options
            )
            
            # Process the vendor company selection
            if "All except Holiday Niseko" in selected_vendor_companies_raw:
                selected_vendor_companies = [vc for vc in vendor_companies if vc != "Holiday Niseko"]
            else:
                selected_vendor_companies = [vc for vc in selected_vendor_companies_raw if vc in vendor_companies]
            
            # Column selection
            st.markdown("---")
            st.subheader("📋 Column Display")
            
            # Show available columns
            all_columns = list(df.columns)
            st.write("**Available columns:**")
            st.write(all_columns)
            
            # Default columns to show
            default_columns = ['Package ID', 'Vendor', 'Product', 'Item Sell Price', 'Nights/Days', 'Created (Japan Standard Time)']
            available_default_columns = [col for col in default_columns if col in all_columns]
            
            selected_columns = st.multiselect(
                "Select columns to display:",
                options=all_columns,
                default=available_default_columns
            )
            
            if not selected_columns:
                selected_columns = all_columns  # Show all if none selected
        
        # Apply filters using cached function
        regular_bookings_df = get_filtered_data(df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
        all_filtered_df = get_filtered_data(df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=False)
        
        st.markdown("---")
        
        # Calculate metrics using cached function
        current_metrics = calculate_metrics(regular_bookings_df)
        
        # Calculate owner stays count
        owner_stays_df = all_filtered_df[all_filtered_df['Zero Stay'] == 1] if 'Zero Stay' in all_filtered_df.columns else pd.DataFrame()
        owner_stays_count = owner_stays_df['Package ID'].nunique() if not owner_stays_df.empty and 'Package ID' in owner_stays_df.columns else 0
        
        # Get comparison data (these functions use cached data internally)
        last_winter_totals = get_last_winter_totals(sheet_type, selected_vendors, selected_products, selected_vendor_companies)
        same_date_totals = get_same_date_last_year_totals(sheet_type, selected_vendors, selected_products, selected_vendor_companies)
        
        # Enhanced metrics with comparisons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Bookings", f"{current_metrics['total_bookings']:,}")
            
            if last_winter_totals:
                delta_total = current_metrics['total_bookings'] - last_winter_totals['total_bookings']
                st.caption(f"Last winter complete: {last_winter_totals['total_bookings']:,} ({delta_total:+,})")
            else:
                st.caption("Last winter complete: No data")
            
            if same_date_totals:
                same_date_delta = current_metrics['total_bookings'] - same_date_totals['total_bookings']
                st.caption(f"Oct 23, 2024: {same_date_totals['total_bookings']:,} ({same_date_delta:+,})")
            else:
                st.caption("Oct 23, 2024: No data")
        
        with col2:
            st.metric("Owner Stays", f"{owner_stays_count:,}")
            st.caption("Zero stay bookings")
        
        with col3:
            st.metric("Total Revenue", f"¥{current_metrics['total_revenue']:,.0f}")
            
            if last_winter_totals and last_winter_totals['total_revenue'] > 0:
                delta_revenue = current_metrics['total_revenue'] - last_winter_totals['total_revenue']
                st.caption(f"Last winter complete: ¥{last_winter_totals['total_revenue']:,.0f} (¥{delta_revenue:+,.0f})")
            else:
                st.caption("Last winter complete: No revenue data")
            
            if same_date_totals and same_date_totals['total_revenue'] > 0:
                same_date_revenue_delta = current_metrics['total_revenue'] - same_date_totals['total_revenue']
                st.caption(f"Oct 23, 2024: ¥{same_date_totals['total_revenue']:,.0f} (¥{same_date_revenue_delta:+,.0f})")
            else:
                st.caption("Oct 23, 2024: No revenue data")
        
        with col4:
            st.metric("Total Nights", f"{current_metrics['total_nights']:,.0f}")
            
            if last_winter_totals and last_winter_totals['total_nights'] > 0:
                delta_nights = current_metrics['total_nights'] - last_winter_totals['total_nights']
                st.caption(f"Last winter complete: {last_winter_totals['total_nights']:,.0f} ({delta_nights:+,.0f})")
            else:
                st.caption("Last winter complete: No nights data")
            
            if same_date_totals and same_date_totals['total_nights'] > 0:
                same_date_nights_delta = current_metrics['total_nights'] - same_date_totals['total_nights']
                st.caption(f"Oct 23, 2024: {same_date_totals['total_nights']:,.0f} ({same_date_nights_delta:+,.0f})")
            else:
                st.caption("Oct 23, 2024: No nights data")
        
        # Add explanation of calculations
        st.info("📊 Bookings = Unique Package IDs (excluding Zero Stays) | 💰 Revenue = Item Sell Price | 🏠 Owner Stays = Zero Stay bookings")
        
        # Display the filtered data with selected columns only
        display_df = all_filtered_df[selected_columns] if selected_columns else all_filtered_df
        st.dataframe(display_df, use_container_width=True, height=500, hide_index=True)
        
        # Half-monthly nights analysis
        st.markdown("---")
        st.subheader("📅 Half-Monthly Nights Analysis")
        
        # Define the half-month columns for current season (25/26)
        half_month_columns = [
            'Nights Early Dec 25', 'Nights Late Dec 25',
            'Nights Early Jan 26', 'Nights Late Jan 26', 
            'Nights Early Feb 26', 'Nights Late Feb 26',
            'Nights Early Mar 26', 'Nights Late Mar 26',
            'Nights Early Apr 26', 'Nights Late Apr 26'
        ]
        
        # Calculate current season half-monthly totals from REGULAR BOOKINGS (excluding zero stays)
        current_half_monthly = {}
        for col in half_month_columns:
            if col in regular_bookings_df.columns:
                try:
                    col_total = pd.to_numeric(regular_bookings_df[col], errors='coerce').sum()
                    # Clean up the column name for display
                    period_name = col.replace('Nights ', '').replace(' 25', '').replace(' 26', '')
                    current_half_monthly[period_name] = col_total
                except:
                    pass
        
        # Get last winter data with same filters (including vendor company filter)
        last_winter_half_monthly = {}
        same_date_half_monthly = {}
        
        try:
            last_winter_df = get_booking_data(f"{sheet_type}_last_winter")
            if not last_winter_df.empty:
                last_winter_df = process_booking_data(last_winter_df)
                
                # Apply same filters as current data (including vendor company filter)
                filtered_last_winter = get_filtered_data(last_winter_df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
                
                # Calculate last winter half-monthly totals
                # Map to equivalent columns for last winter (24/25 season)
                last_winter_columns = [
                    'Nights Early Dec 24', 'Nights Late Dec 24',
                    'Nights Early Jan 25', 'Nights Late Jan 25', 
                    'Nights Early Feb 25', 'Nights Late Feb 25',
                    'Nights Early Mar 25', 'Nights Late Mar 25',
                    'Nights Early Apr 25', 'Nights Late Apr 25'
                ]
                
                for i, col in enumerate(last_winter_columns):
                    if col in filtered_last_winter.columns:
                        try:
                            col_total = pd.to_numeric(filtered_last_winter[col], errors='coerce').sum()
                            # Use same period name as current
                            period_name = half_month_columns[i].replace('Nights ', '').replace(' 25', '').replace(' 26', '')
                            last_winter_half_monthly[period_name] = col_total
                        except:
                            pass
                
                # Calculate same date last year data
                try:
                    today = datetime.now()
                    same_date_last_year = today.replace(year=today.year - 1)
                    
                    if 'Created_Date' in last_winter_df.columns:
                        same_date_df = last_winter_df[last_winter_df['Created_Date'] <= same_date_last_year]
                        same_date_df = get_filtered_data(same_date_df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
                    
                        for i, col in enumerate(last_winter_columns):
                            if col in same_date_df.columns:
                                try:
                                    col_total = pd.to_numeric(same_date_df[col], errors='coerce').sum()
                                    period_name = half_month_columns[i].replace('Nights ', '').replace(' 25', '').replace(' 26', '')
                                    same_date_half_monthly[period_name] = col_total
                                except:
                                    pass
                except:
                    pass
        except:
            pass
        
        # Create comparison chart
        if current_half_monthly:
            import plotly.graph_objects as go
            
            periods = list(current_half_monthly.keys())
            
            chart_data = []
            for period in periods:
                chart_data.append({
                    'Period': period,
                    'Current Season': current_half_monthly.get(period, 0),
                    'Last Winter Complete': last_winter_half_monthly.get(period, 0),
                    'Oct 23, 2024': same_date_half_monthly.get(period, 0)
                })
            
            chart_df = pd.DataFrame(chart_data)
            
            # Create side-by-side bar chart with horizontal line
            fig = go.Figure()
            
            # Add current season bars
            fig.add_trace(go.Bar(
                name='Current Season',
                x=chart_df['Period'],
                y=chart_df['Current Season'],
                marker_color='#1f77b4'
            ))
            
            # Add "Oct 23, 2024" bars  
            fig.add_trace(go.Bar(
                name='Oct 23, 2024',
                x=chart_df['Period'],
                y=chart_df['Oct 23, 2024'],
                marker_color='#808080'  # Grey color instead of red
            ))
            
            # Add horizontal reference lines using annotations
            annotations = []
            for i, (period, last_winter_value) in enumerate(zip(chart_df['Period'], chart_df['Last Winter Complete'])):
                # Create a horizontal line annotation for each period
                annotations.append(
                    dict(
                        x=period,
                        y=last_winter_value,
                        text="—————————",  # Em dash line
                        showarrow=False,
                        font=dict(color="#808080", size=16),
                        xanchor="center",
                        yanchor="middle"
                    )
                )
            
            # Add a dummy trace for the legend (reference line)
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='lines',
                line=dict(color='#808080', width=3),  # Grey color
                name='Last Winter Complete',
                showlegend=True
            ))
            
            # Dynamic title based on what's selected (updated to include vendor company)
            title_parts = []
            if selected_vendors:
                title_parts.append(', '.join(selected_vendors))
            if selected_products:
                title_parts.append(', '.join(selected_products))
            if selected_vendor_companies:
                title_parts.append(', '.join(selected_vendor_companies))
            
            if title_parts:
                chart_title = f"📅 Half-Monthly Nights Comparison - {' - '.join(title_parts)}"
            else:
                chart_title = "📅 Half-Monthly Nights Comparison - All Data"
            
            fig.update_layout(
                title=chart_title,
                xaxis_title="Period",
                yaxis_title="Nights",
                height=400,
                barmode='group',  # Ensure bars are grouped side by side
                bargap=0.2,  # Gap between bar groups
                # Remove unnecessary gridlines for cleaner SWD-style design
                xaxis_showgrid=False,
                yaxis_showgrid=True,
                yaxis_gridcolor='#f0f0f0',
                plot_bgcolor='white',
                annotations=annotations
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show summary table
            with st.expander("📊 View Data Table", expanded=False):
                st.dataframe(chart_df, use_container_width=True, hide_index=True)
        else:
            st.info("No half-monthly data available for the current selection")
        
        # Sales Channel Breakdown Analysis
        st.markdown("---")
        st.subheader("📈 Sales Channel Breakdown")
        
        if 'ChannelAS2' in regular_bookings_df.columns:
            # Calculate sales channel metrics
            sales_channel_data = []
            
            for channel in regular_bookings_df['ChannelAS2'].dropna().unique():
                channel_df = regular_bookings_df[regular_bookings_df['ChannelAS2'] == channel]
                
                # Calculate metrics for this channel
                channel_bookings = channel_df['Package ID'].nunique() if 'Package ID' in channel_df.columns else len(channel_df)
                
                channel_revenue = 0
                if 'Item Sell Price' in channel_df.columns:
                    try:
                        channel_revenue = pd.to_numeric(channel_df['Item Sell Price'], errors='coerce').sum()
                    except:
                        pass
                
                channel_nights = 0
                if 'Nights/Days' in channel_df.columns:
                    try:
                        channel_nights = pd.to_numeric(channel_df['Nights/Days'], errors='coerce').sum()
                    except:
                        pass
                
                sales_channel_data.append({
                    'Sales Channel': channel,
                    'Bookings': channel_bookings,
                    'Revenue (¥)': channel_revenue,
                    'Nights': channel_nights,
                    'Avg Revenue per Booking': channel_revenue / channel_bookings if channel_bookings > 0 else 0
                })
            
            if sales_channel_data:
                # Create DataFrame and sort by revenue, keep only top 4
                sales_df = pd.DataFrame(sales_channel_data)
                sales_df = sales_df.sort_values('Revenue (¥)', ascending=False).head(4)
                
                # Display metrics in columns
                col1, col2 = st.columns(2)
                
                with col1:
                    # Sales channel breakdown chart (bookings) - top 4 only
                    import plotly.express as px
                    
                    fig_bookings = px.bar(
                        sales_df, 
                        x='Sales Channel', 
                        y='Bookings',
                        title='Top 4 Sales Channels by Bookings'
                    )
                    fig_bookings.update_layout(
                        height=400,
                        xaxis_title="Sales Channel",
                        yaxis_title="Number of Bookings",
                        showlegend=False
                    )
                    fig_bookings.update_traces(marker_color='#1f77b4')
                    st.plotly_chart(fig_bookings, use_container_width=True)
                
                with col2:
                    # Sales channel revenue bar chart - top 4 only
                    fig_revenue = px.bar(
                        sales_df, 
                        x='Sales Channel', 
                        y='Revenue (¥)',
                        title='Top 4 Sales Channels by Revenue'
                    )
                    fig_revenue.update_layout(
                        height=400,
                        xaxis_title="Sales Channel",
                        yaxis_title="Revenue (¥)",
                        showlegend=False
                    )
                    fig_revenue.update_traces(marker_color='#2ca02c')
                    st.plotly_chart(fig_revenue, use_container_width=True)
                
                # Display summary table
                st.subheader("📊 Sales Channel Summary")
                
                # Format the dataframe for display
                display_df = sales_df.copy()
                display_df['Revenue (¥)'] = display_df['Revenue (¥)'].apply(lambda x: f"¥{x:,.0f}")
                display_df['Avg Revenue per Booking'] = display_df['Avg Revenue per Booking'].apply(lambda x: f"¥{x:,.0f}")
                display_df['Bookings'] = display_df['Bookings'].apply(lambda x: f"{x:,}")
                display_df['Nights'] = display_df['Nights'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No ChannelAS2 data available in the dataset")
        
        # Booking Creation Date Analysis (2024 vs 2025 by Calendar Month)
        st.markdown("---")
        st.subheader("📅 Bookings Created: 2024 vs 2025 by Month")
        
        if 'Created_Date' in regular_bookings_df.columns:
            try:
                # Get current year data (2025)
                current_df = regular_bookings_df.copy()
                current_df = current_df.dropna(subset=['Created_Date'])
                
                # Filter for 2025 data only
                current_2025 = current_df[current_df['Created_Date'].dt.year == 2025]
                
                # Get last year data with same filters
                last_winter_df = get_booking_data(f"{sheet_type}_last_winter")
                if not last_winter_df.empty:
                    last_winter_df = process_booking_data(last_winter_df)
                    
                    # Apply same filters to last year data
                    filtered_last_winter = get_filtered_data(last_winter_df, selected_vendors, selected_products, selected_vendor_companies, exclude_zero_stays=True)
                    filtered_last_winter = filtered_last_winter.dropna(subset=['Created_Date'])
                    
                    # Filter for 2024 data only
                    last_2024 = filtered_last_winter[filtered_last_winter['Created_Date'].dt.year == 2024]
                    
                    # Group by calendar month (1-12)
                    current_2025_monthly = current_2025.groupby(current_2025['Created_Date'].dt.month).size()
                    last_2024_monthly = last_2024.groupby(last_2024['Created_Date'].dt.month).size()
                    
                    # Calculate revenue by month for annotations
                    current_2025_revenue = current_2025.groupby(current_2025['Created_Date'].dt.month)['Item Sell Price'].apply(
                        lambda x: pd.to_numeric(x, errors='coerce').sum()
                    ) if 'Item Sell Price' in current_2025.columns else None
                    
                    last_2024_revenue = last_2024.groupby(last_2024['Created_Date'].dt.month)['Item Sell Price'].apply(
                        lambda x: pd.to_numeric(x, errors='coerce').sum()
                    ) if 'Item Sell Price' in last_2024.columns else None
                    
                    # Create month labels
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    
                    # Prepare aligned data for all 12 months
                    months_2025 = []
                    months_2024 = []
                    revenue_2025 = []
                    revenue_2024 = []
                    
                    for month in range(1, 13):
                        months_2025.append(current_2025_monthly.get(month, 0))
                        months_2024.append(last_2024_monthly.get(month, 0))
                        
                        if current_2025_revenue is not None:
                            revenue_2025.append(current_2025_revenue.get(month, 0))
                        else:
                            revenue_2025.append(0)
                            
                        if last_2024_revenue is not None:
                            revenue_2024.append(last_2024_revenue.get(month, 0))
                        else:
                            revenue_2024.append(0)
                    
                    # Create comparison chart
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    
                    # Add 2024 bars FIRST (grey color) - Revenue on Y-axis
                    fig.add_trace(go.Bar(
                        name='2024',
                        x=month_names,
                        y=revenue_2024,
                        marker_color='#808080',  # Grey color
                        text=[f"¥{r/1000000:.1f}M" if r > 0 else "" for r in revenue_2024],  # Revenue in millions
                        textposition="outside"
                    ))
                    
                    # Add 2025 bars SECOND - Revenue on Y-axis
                    fig.add_trace(go.Bar(
                        name='2025',
                        x=month_names,
                        y=revenue_2025,
                        marker_color='#1f77b4',  # Blue color
                        text=[f"¥{r/1000000:.1f}M" if r > 0 else "" for r in revenue_2025],  # Revenue in millions
                        textposition="outside"
                    ))
                    
                    fig.update_layout(
                        title='Revenue from Bookings Created by Month: 2024 vs 2025',
                        xaxis_title="Month",
                        height=400,
                        barmode='group',
                        bargap=0.2,
                        xaxis_showgrid=False,
                        yaxis_showgrid=True,
                        yaxis_gridcolor='#f0f0f0',
                        yaxis=dict(
                            showticklabels=False,
                            title=""
                        ),  # Hide y-axis labels but keep gridlines
                        plot_bgcolor='white'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show summary table
                    chart_data = []
                    for i, month in enumerate(month_names):
                        chart_data.append({
                            'Month': month,
                            '2025 Bookings': months_2025[i],
                            '2024 Bookings': months_2024[i],
                            '2025 Revenue': f"¥{revenue_2025[i]:,.0f}",
                            '2024 Revenue': f"¥{revenue_2024[i]:,.0f}"
                        })
                    
                    chart_df = pd.DataFrame(chart_data)
                    
                    with st.expander("📊 View Booking Creation Data", expanded=False):
                        st.dataframe(chart_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No 2024 data available for comparison")
            except Exception as e:
                st.error(f"Error processing booking creation dates: {e}")
        else:
            st.info("No booking creation date data available")
        
        # Add cache status info
        st.sidebar.markdown("---")
        st.sidebar.info("💡 Data is cached for 5 minutes to improve performance. Use the 'Refresh Data' button to force reload.")
        
    else:
        st.warning(f"No {sheet_type} data found or failed to load data")
        st.info("Make sure your Google Sheet has the correct tab names: 'accommodation' and 'Guest Services'")
        
        # Still show the sidebar even when no data
        with st.sidebar:
            st.subheader("🔍 Filters")
            st.info("Load data to see filter options")

if __name__ == "__main__":
    main()
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Set page config FIRST (required for multi-page apps)
st.set_page_config(page_title="Holiday Niseko Analytics Dashboard", layout="wide")

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

# Initialize variables
ga4_prop_id = None
GA4_CREDENTIALS = None

# Handle credentials for both local and Streamlit Cloud
try:
    # Try Streamlit secrets first (works both locally with secrets.toml and in production)
    ga4_prop_id = st.secrets["ga4_prop_id"]
    
    # Create credentials from Streamlit secrets
    from google.oauth2 import service_account
    
    if "ga4_credentials" in st.secrets:
        credentials_info = dict(st.secrets["ga4_credentials"])
        GA4_CREDENTIALS = service_account.Credentials.from_service_account_info(credentials_info)
    else:
        GA4_CREDENTIALS = None
    
except Exception as e:
    # Fallback to local .env file (for development)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        ga4_prop_id = os.getenv("ga4_prop_id")
        
        # Handle local JSON file credentials - ONLY if the variable exists and is not None
        ga4_creds_path = os.getenv("ga4_json_creds")
        if ga4_creds_path and ga4_creds_path.strip():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ga4_creds_path
    except Exception as env_error:
        pass

def get_weekly_data_with_comparison(property_id=ga4_prop_id, weeks_back=12):
    """Get extended period of data with year-over-year comparison"""
    
    if not property_id:
        raise Exception("GA4 property ID not configured.")
    
    if GA4_CREDENTIALS:
        client = BetaAnalyticsDataClient(credentials=GA4_CREDENTIALS)
    else:
        client = BetaAnalyticsDataClient()
    
    # Calculate extended period - current year
    today = datetime.now()
    current_start = (today - timedelta(days=weeks_back * 7)).strftime("%Y-%m-%d")
    current_end = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Same period last year
    last_year_start = (today - timedelta(days=(weeks_back * 7) + 365)).strftime("%Y-%m-%d")
    last_year_end = (today - timedelta(days=1 + 365)).strftime("%Y-%m-%d")
    
    def get_period_data(start_date, end_date, period_name):
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="engagementRate")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        response = client.run_report(request)
        
        data = []
        for row in response.rows:
            date = datetime.strptime(row.dimension_values[0].value, "%Y%m%d")
            
            data.append({
                'date': date,
                'period': period_name,
                'users': int(row.metric_values[0].value),
                'pageviews': int(row.metric_values[1].value),
                'sessions': int(row.metric_values[2].value),
                'duration': float(row.metric_values[3].value),
                'engagement': float(row.metric_values[4].value) * 100
            })
        
        return data
    
    # Get both periods
    current_data = get_period_data(current_start, current_end, "This Year")
    last_year_data = get_period_data(last_year_start, last_year_end, "Last Year")
    
    # Combine data
    all_data = current_data + last_year_data
    df = pd.DataFrame(all_data)
    
    return df, current_start, current_end

def get_traffic_sources(property_id=ga4_prop_id, weeks_back=12):
    """Get traffic sources for the specified period"""
    
    if GA4_CREDENTIALS:
        client = BetaAnalyticsDataClient(credentials=GA4_CREDENTIALS)
    else:
        client = BetaAnalyticsDataClient()
    
    today = datetime.now()
    start_date = (today - timedelta(days=weeks_back * 7)).strftime("%Y-%m-%d")
    end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
    )
    
    response = client.run_report(request)
    
    traffic_data = []
    for row in response.rows:
        source = row.dimension_values[0].value
        # Clean up source names
        if source == "(direct) / (none)":
            source = "Direct"
        elif source == "google / organic":
            source = "Google Search"
        elif source == "google / cpc":
            source = "Google Ads"
        
        traffic_data.append({
            'source': source,
            'users': int(row.metric_values[0].value),
            'sessions': int(row.metric_values[1].value)
        })
    
    return pd.DataFrame(traffic_data)

def main():
    st.title("Holiday Niseko Analytics")
    
    if not ga4_prop_id:
        st.error("GA4 not configured")
        return
    
    # Time period selector - compact
    period_options = {
        "4 weeks": 4,
        "8 weeks": 8, 
        "12 weeks": 12,
        "24 weeks": 24,
        "52 weeks": 52
    }
    
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_period = st.selectbox(
            "Period:",
            options=list(period_options.keys()),
            index=2  # Default to 12 weeks
        )
    
    weeks_back = period_options[selected_period]
    
    try:
        # Get data
        with st.spinner("Loading..."):
            df, start_date, end_date = get_weekly_data_with_comparison(weeks_back=weeks_back)
            traffic_df = get_traffic_sources(weeks_back=weeks_back)
        
        # Create proper date labels for overlaid comparison
        df_current = df[df['period'] == 'This Year'].copy()
        df_last_year = df[df['period'] == 'Last Year'].copy()
        
        # Group by week and get the actual calendar dates for this year
        df_current['week_start'] = df_current['date'].dt.to_period('W').dt.start_time
        df_last_year['week_start'] = df_last_year['date'].dt.to_period('W').dt.start_time
        
        # Aggregate by week and filter out incomplete weeks
        current_weekly = df_current.groupby('week_start').agg({
            'users': 'sum',
            'pageviews': 'sum',
            'sessions': 'sum',
            'engagement': 'mean',
            'date': 'count'
        }).reset_index()
        current_weekly.rename(columns={'date': 'days_in_week'}, inplace=True)
        current_weekly = current_weekly[current_weekly['days_in_week'] >= 6]
        
        last_year_weekly = df_last_year.groupby('week_start').agg({
            'users': 'sum',
            'pageviews': 'sum',
            'sessions': 'sum',
            'engagement': 'mean',
            'date': 'count'
        }).reset_index()
        last_year_weekly.rename(columns={'date': 'days_in_week'}, inplace=True)
        last_year_weekly = last_year_weekly[last_year_weekly['days_in_week'] >= 6]
        
        # Shift last year dates forward by 365 days to overlay on same timeline
        last_year_weekly['week_start'] = last_year_weekly['week_start'] + pd.DateOffset(days=365)
        
        # Weekly trends with proper overlay
        from plotly.subplots import make_subplots
        
        fig_trends = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Weekly Users', 'Weekly Page Views', 'Weekly Sessions', 'Weekly Engagement Rate (%)'),
            vertical_spacing=0.15,
            horizontal_spacing=0.12
        )
        
        metrics_data = [
            ('users', 1, 1),
            ('pageviews', 1, 2), 
            ('sessions', 2, 1),
            ('engagement', 2, 2)
        ]
        
        # Get the last data points for annotations
        current_last_point = current_weekly.iloc[-1] if not current_weekly.empty else None
        last_year_last_point = last_year_weekly.iloc[-1] if not last_year_weekly.empty else None
        
        for metric, row, col in metrics_data:
            # This year data
            fig_trends.add_trace(
                go.Scatter(
                    x=current_weekly['week_start'],
                    y=current_weekly[metric],
                    mode='lines+markers',
                    name='This Year' if metric == 'users' else None,
                    showlegend=True if metric == 'users' else False,
                    line=dict(color='black', width=2),
                    marker=dict(color='black', size=3)
                ),
                row=row, col=col
            )
            
            # Last year data (shifted to overlay)
            fig_trends.add_trace(
                go.Scatter(
                    x=last_year_weekly['week_start'],
                    y=last_year_weekly[metric],
                    mode='lines+markers',
                    name='Last Year' if metric == 'users' else None,
                    showlegend=True if metric == 'users' else False,
                    line=dict(color='lightgray', width=2, dash='dash'),
                    marker=dict(color='lightgray', size=3)
                ),
                row=row, col=col
            )
            
            # Add end point annotations for current year
            if current_last_point is not None:
                fig_trends.add_annotation(
                    x=current_last_point['week_start'],
                    y=current_last_point[metric],
                    text=f"{current_last_point['week_start'].strftime('%b %d')}<br>{current_last_point[metric]:,.0f}" if metric != 'engagement' else f"{current_last_point['week_start'].strftime('%b %d')}<br>{current_last_point[metric]:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor='black',
                    arrowsize=1,
                    ax=20,
                    ay=-20,
                    bgcolor='white',
                    bordercolor='black',
                    borderwidth=1,
                    font=dict(size=10, color='black'),
                    row=row, col=col
                )
            
            # Add end point annotations for last year
            if last_year_last_point is not None:
                fig_trends.add_annotation(
                    x=last_year_last_point['week_start'],
                    y=last_year_last_point[metric],
                    text=f"{last_year_last_point['week_start'].strftime('%b %d')}<br>{last_year_last_point[metric]:,.0f}" if metric != 'engagement' else f"{last_year_last_point['week_start'].strftime('%b %d')}<br>{last_year_last_point[metric]:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor='gray',
                    arrowsize=1,
                    ax=-20,
                    ay=-20,
                    bgcolor='white',
                    bordercolor='gray',
                    borderwidth=1,
                    font=dict(size=10, color='gray'),
                    row=row, col=col
                )
        
        fig_trends.update_layout(
            height=550,
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=40, r=40, t=80, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            )
        )
        
        # Update all subplot axes with clean look and better date formatting
        fig_trends.update_xaxes(
            showgrid=False,
            zeroline=True, 
            zerolinecolor='black',
            zerolinewidth=1,
            tickformat='%b %d',  # Show both month and day
            dtick='M1'
        )
        fig_trends.update_yaxes(
            showgrid=False,
            zeroline=True, 
            zerolinecolor='black',
            zerolinewidth=1,
            rangemode='tozero'
        )
        
        st.plotly_chart(fig_trends, use_container_width=True, config={'displayModeBar': False})
        
        # Add a data range indicator below the chart
        if current_last_point is not None:
            st.caption(f"📅 Data range: {start_date} to {end_date} | Latest data point: {current_last_point['week_start'].strftime('%B %d, %Y')}")
        
        # Summary metrics
        current_totals = current_weekly.agg({
            'users': 'sum',
            'pageviews': 'sum', 
            'sessions': 'sum',
            'engagement': 'mean'
        })
        
        last_year_totals = last_year_weekly.agg({
            'users': 'sum',
            'pageviews': 'sum', 
            'sessions': 'sum',
            'engagement': 'mean'
        })
        
        def calculate_change(current, last_year):
            if last_year == 0:
                return 0
            return ((current - last_year) / last_year) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            change = calculate_change(current_totals['users'], last_year_totals['users'])
            st.metric("Users", f"{current_totals['users']:,.0f}", f"{change:+.1f}%")
        
        with col2:
            change = calculate_change(current_totals['pageviews'], last_year_totals['pageviews'])
            st.metric("Page Views", f"{current_totals['pageviews']:,.0f}", f"{change:+.1f}%")
        
        with col3:
            change = calculate_change(current_totals['sessions'], last_year_totals['sessions'])
            st.metric("Sessions", f"{current_totals['sessions']:,.0f}", f"{change:+.1f}%")
        
        with col4:
            change = calculate_change(current_totals['engagement'], last_year_totals['engagement'])
            st.metric("Engagement", f"{current_totals['engagement']:.1f}%", f"{change:+.1f}%")
        
        # Traffic Sources
        st.subheader("Traffic Sources")
        
        if not traffic_df.empty:
            # Get top 5 sources
            traffic_summary = traffic_df.nlargest(10, 'users')
            traffic_summary['Users %'] = (traffic_summary['users'] / traffic_summary['users'].sum() * 100).round(1)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                display_df = traffic_summary[['source', 'users', 'sessions', 'Users %']].reset_index(drop=True)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            with col2:
                # Simple pie chart
                fig_pie = go.Figure(data=[go.Pie(
                    labels=traffic_summary['source'],
                    values=traffic_summary['users'],
                    hole=0.3,
                    showlegend=False
                )])
                
                fig_pie.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No traffic source data available")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
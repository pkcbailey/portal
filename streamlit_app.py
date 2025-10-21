"""
Streamlit Dashboard for DCV Certificate Validation
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="DCV Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("🔐 DCV Dashboard")
tab = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Akamai DCV"],
    label_visibility="collapsed"
)

# Helper functions
def parse_expiration_date(exp_str):
    """Parse expiration date in ISO 8601 or MM-DD-YY format."""
    if not exp_str:
        return None
    # Remove trailing 'z' or 'Z'
    exp_str = exp_str.rstrip('zZ')
    try:
        # Try ISO 8601 first (for Akamai data)
        return datetime.fromisoformat(exp_str)
    except ValueError:
        pass
    try:
        # Try MM-DD-YY format (for combined_certs.json)
        dt = datetime.strptime(exp_str, "%m-%d-%y")
        # If year is in the past, assume it's in the next century
        if dt.year < 2000:
            dt = dt.replace(year=dt.year + 100)
        return dt
    except Exception:
        return None

def calculate_days_remaining(exp_str):
    """Calculate days remaining until expiration"""
    exp_date = parse_expiration_date(exp_str)
    if exp_date:
        delta = exp_date - datetime.now()
        return delta.days
    return None

def load_combined_certs():
    """Load combined certificates data from JSON"""
    json_path = os.path.join('data', 'combined_certs.json')
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return json.load(f)
    return []

def load_akamai_sans():
    """Load Akamai SANs data from CSV in the data directory"""
    csv_path = os.path.join('data', 'akamai_san.csv')
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None

# Dashboard Tab
if tab == "Dashboard":
    st.title("📊 DCV Certificate Dashboard")
    st.markdown("---")

    # Load data
    data = load_combined_certs()

    if data:
        # Add filter
        col1, col2 = st.columns([3, 1])
        with col1:
            filter_text = st.text_input("🔍 Filter domains", placeholder="Enter domain name...")
        with col2:
            sort_by_expiry = st.checkbox("Sort by expiry", value=False)

        # Process data
        processed_data = []
        for item in data:
            domain = item.get('domain', '')

            # Apply filter
            if filter_text and filter_text.lower() not in domain.lower():
                continue

            digicert = item.get('digicert', {})
            sectigo = item.get('sectigo', {})

            digicert_status = digicert.get('status', 'unknown')
            digicert_exp = digicert.get('expiration')
            digicert_days = calculate_days_remaining(digicert_exp) if digicert_exp else None

            sectigo_status = sectigo.get('status', 'unknown')
            sectigo_exp = sectigo.get('expiration')
            sectigo_days = calculate_days_remaining(sectigo_exp) if sectigo_exp else None

            # Suppress negative hundreds of days for display
            def expiry_display(exp, days):
                if not exp or days is None:
                    return '—'
                elif days < 0:
                    return f"{exp} (Expired)"
                else:
                    return f"{exp} ({days}d)"

            # Calculate min days for sorting (non-negative values only)
            days_list = [d for d in [digicert_days, sectigo_days] if d is not None and d >= 0]
            min_days = min(days_list) if days_list else float('inf')

            processed_data.append({
                'Domain': domain,
                'DigiCert Status': digicert_status,
                'DigiCert Expiry': expiry_display(digicert_exp, digicert_days),
                'DigiCert Days': digicert_days if digicert_days is not None and digicert_days >= 0 else None,
                'Sectigo Status': sectigo_status,
                'Sectigo Expiry': expiry_display(sectigo_exp, sectigo_days),
                'Sectigo Days': sectigo_days if sectigo_days is not None and sectigo_days >= 0 else None,
                'min_days': min_days
            })

        # Sort if requested
        if sort_by_expiry:
            processed_data.sort(key=lambda x: x['min_days'])

        # Remove the sorting helper column
        for item in processed_data:
            del item['min_days']

        # Display stats
        total_domains = len(processed_data)
        validated_digicert = sum(1 for item in processed_data if item['DigiCert Status'] == 'validated')
        validated_sectigo = sum(1 for item in processed_data if item['Sectigo Status'] == 'validated')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Domains", total_domains)
        with col2:
            st.metric("DigiCert Validated", validated_digicert)
        with col3:
            st.metric("Sectigo Validated", validated_sectigo)

        st.markdown("---")

        # Display table
        if processed_data:
            df = pd.DataFrame(processed_data)

            # Style the dataframe with colors for expiry columns (font color only)
            def color_expiry_text(val, days):
                if days is None or val in ['—', None]:
                    return ''
                elif days < 0:
                    return 'color: red; font-weight: bold;'
                elif days <= 30:
                    return 'color: red; font-weight: bold;'
                elif days <= 60:
                    return 'color: orange; font-weight: bold;'
                else:
                    return 'color: green; font-weight: bold;'

            def style_expiry_cols(row):
                styles = [''] * len(row)
                if 'DigiCert Expiry' in row and 'DigiCert Days' in row:
                    idx = row.index.get_loc('DigiCert Expiry')
                    styles[idx] = color_expiry_text(row['DigiCert Expiry'], row['DigiCert Days'])
                if 'Sectigo Expiry' in row and 'Sectigo Days' in row:
                    idx = row.index.get_loc('Sectigo Expiry')
                    styles[idx] = color_expiry_text(row['Sectigo Expiry'], row['Sectigo Days'])
                return styles

            # Remove helper columns from display
            display_df = df.drop(columns=['DigiCert Days', 'Sectigo Days'])

            styled_df = display_df.style.apply(style_expiry_cols, axis=1)

            st.dataframe(
                styled_df,
                use_container_width=True,
                height=600
            )

            # Legend
            st.markdown("---")
            st.markdown("**Expiry Color Legend:**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("🔴 <span style='color:red;'>Red</span>: Expired or ≤30 days", unsafe_allow_html=True)
            with col2:
                st.markdown("🟠 <span style='color:orange;'>Orange</span>: ≤60 days", unsafe_allow_html=True)
            with col3:
                st.markdown("🟢 <span style='color:green;'>Green</span>: >90 days", unsafe_allow_html=True)
            with col4:
                st.markdown("", unsafe_allow_html=True)
        else:
            st.info("No domains match the filter criteria.")
    else:
        st.warning("No certificate data available. Please run the DCV pipeline first.")
        st.code("python run_dcv_pipeline.py")

# Akamai DCV Tab
elif tab == "Akamai DCV":
    st.title("🌐 Akamai DCV Certificate Management")
    st.markdown("---")

    # Load Akamai SANs data
    akamai_df = load_akamai_sans()

    if akamai_df is not None:
        # Display summary stats
        total_sans = len(akamai_df)

        # Parse expiration dates and calculate stats
        akamai_df['Parsed_Date'] = pd.to_datetime(akamai_df['Expiration Date'], format='%Y-%m-%d', errors='coerce')
        today = pd.Timestamp.now()
        akamai_df['Days_Remaining'] = (akamai_df['Parsed_Date'] - today).dt.days

        expiring_soon = len(akamai_df[akamai_df['Days_Remaining'] <= 30])
        expired = len(akamai_df[akamai_df['Days_Remaining'] < 0])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total SANs", total_sans)
        with col2:
            st.metric("Expiring Soon (≤30d)", expiring_soon)
        with col3:
            st.metric("Expired", expired)
        with col4:
            unique_issuers = akamai_df['Issuer'].nunique()
            st.metric("Unique Issuers", unique_issuers)

        st.markdown("---")

        # Add filters
        col1, col2 = st.columns([2, 2])
        with col1:
            search_text = st.text_input("🔍 Search SANs", placeholder="Enter SAN, issuer, or deployment...")
        with col2:
            issuer_filter = st.multiselect(
                "Filter by Issuer",
                options=akamai_df['Issuer'].unique().tolist(),
                default=[]
            )

        # Apply filters
        filtered_df = akamai_df.copy()

        if search_text:
            mask = (
                filtered_df['SAN'].str.contains(search_text, case=False, na=False) |
                filtered_df['Issuer'].str.contains(search_text, case=False, na=False) |
                filtered_df['Certificate Deployments'].str.contains(search_text, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        if issuer_filter:
            filtered_df = filtered_df[filtered_df['Issuer'].isin(issuer_filter)]

        # Format the display dataframe
        display_df = filtered_df[['SAN', 'Expiration Date', 'Issuer', 'Certificate Deployments', 'Days_Remaining']].copy()
        display_df['Days Remaining'] = display_df['Days_Remaining'].apply(
            lambda x: f"{int(x)} days" if pd.notna(x) else "N/A"
        )
        display_df = display_df.drop(columns=['Days_Remaining'])

        # Sort by expiration date (soonest first)
        display_df = display_df.sort_values('Expiration Date')

        # Style the dataframe: color only the Expiration Date and Days Remaining columns
        def color_expiry_text(val, days):
            if pd.isna(days):
                return ''
            elif days < 0:
                return 'color: red; font-weight: bold;'
            elif days <= 30:
                return 'color: red; font-weight: bold;'
            elif days <= 60:
                return 'color: orange; font-weight: bold;'
            else:
                return 'color: green; font-weight: bold;'

        def style_expiry_cols(row):
            styles = [''] * len(row)
            # Expiry date
            if 'Expiration Date' in row and 'Days Remaining' in row:
                idx_exp = row.index.get_loc('Expiration Date')
                try:
                    days = int(str(row['Days Remaining']).split()[0])
                except Exception:
                    days = None
                styles[idx_exp] = color_expiry_text(row['Expiration Date'], days)
                idx_days = row.index.get_loc('Days Remaining')
                styles[idx_days] = color_expiry_text(row['Expiration Date'], days)
            return styles

        styled_df = display_df.style.apply(style_expiry_cols, axis=1)

        # Display table
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600
        )

        # Legend
        st.markdown("---")
        st.markdown("**Color Legend:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("🔴 <span style='color:red;'>Red</span>: Expired or ≤30 days", unsafe_allow_html=True)
        with col2:
            st.markdown("🟠 <span style='color:orange;'>Orange</span>: ≤60 days", unsafe_allow_html=True)
        with col3:
            st.markdown("🟢 <span style='color:green;'>Green</span>: >90 days", unsafe_allow_html=True)
        with col4:
            st.markdown("", unsafe_allow_html=True)

    else:
        st.warning("⚠️ Akamai SANs data not found.")
        st.info("Please ensure the file `akamai_san.csv` exists in the data directory with the following columns:")
        st.code("SAN,Expiration Date,Issuer,Certificate Deployments")
        st.markdown("""
        **Example format:**
        ```
        SAN,Expiration Date,Issuer,Certificate Deployments
        *.example.com,2026-03-15,DigiCert Inc,Production|Staging|Development
        ```
        """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**DCV Dashboard v2.0**")
st.sidebar.caption("Certificate validation and monitoring")
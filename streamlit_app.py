import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# Configure Streamlit page
st.set_page_config(
    page_title="DNS Issues Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:5001/api"

@st.cache_data
def fetch_data(endpoint):
    """Fetch data from Flask API with caching"""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

def main():
    st.title("🌐 DNS Issues Dashboard")
    st.markdown("---")
    
    # Fetch business unit data for sidebar
    bu_data = fetch_data("business-units")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    
    # Main page selector
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Issues Identified", "System Details", "Issues Analysis"]
    )
    
    # Business Units in sidebar
    if bu_data:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏢 Business Units")
        
        # Create clickable business unit buttons
        selected_bu = None
        for bu_name, data in bu_data.items():
            if st.sidebar.button(f"{bu_name} ({data['total_systems']} systems)", key=f"bu_{bu_name}"):
                selected_bu = bu_name
        
        # If a business unit is selected, show its details
        if selected_bu:
            show_business_unit_details(selected_bu)
            return
    
    # Main page routing
    if page == "Issues Identified":
        show_overview()
    elif page == "System Details":
        show_system_details()
    elif page == "Issues Analysis":
        show_issues_analysis()

def show_overview():
    st.header("📊 Issues Identified")
    
    # Fetch summary data
    summary_data = fetch_data("summary")
    if not summary_data:
        st.error("Unable to load summary data")
        return
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Systems with Host Files",
            value=f"{summary_data['total_hosts_with_populated_entries']:,}",
            help="Systems that have populated hostsFileEntries"
        )
    
    with col2:
        st.metric(
            label="Total Hosts with MS DNS Primary",
            value=f"{summary_data['combined_hosts_empty_dns']:,}",
            help="Hosts with empty dnsServers or only '168.63.129.16'"
        )
    
    with col3:
        st.metric(
            label="Hosts Using External DNS Resolvers",
            value=f"{summary_data['hosts_using_internet_routable_ips']:,}",
            help="Hosts using Internet-routable IPs in DNS settings"
        )
    
    with col4:
        st.metric(
            label="Percentage of Host Files due to MS DNS Primary",
            value=f"{summary_data['percentage_with_populated_entries']:.2f}%",
            help="Percentage of MS DNS Primary hosts that have populated entries"
        )
    
    # Additional metrics - moved BigFix to bottom as less important
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric(
            label="Total Systems with BigFix in Hosts File",
            value=f"{summary_data['hosts_with_bigfix']:,}",
            help="Systems that have 'bigfix' in hostsFileEntries"
        )
    
    with col6:
        st.metric(
            label="",
            value="",
            help=""
        )
    
    # Fetch business unit data for charts
    bu_data = fetch_data("business-units")
    if bu_data:
        st.subheader("📈 Business Unit Distribution")
        
        # Create DataFrame for visualization
        bu_df = pd.DataFrame([
            {
                "Business Unit": bu,
                "Hosts with Populated Entries": data["hosts_with_populated_entries"],
                "Internet-Routable DNS": data["hosts_with_internet_routable_dns"],
                "Total Systems": data["total_systems"]
            }
            for bu, data in bu_data.items()
        ])
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Hosts with Populated Entries", "Internet-Routable DNS", 
                          "Total Systems", "Issues by Business Unit"),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "pie"}]]
        )
        
        # Populated entries chart
        fig.add_trace(
            go.Bar(x=bu_df["Business Unit"], y=bu_df["Hosts with Populated Entries"], 
                   name="Populated Entries", marker_color="lightblue"),
            row=1, col=1
        )
        
        # Internet-routable DNS chart
        fig.add_trace(
            go.Bar(x=bu_df["Business Unit"], y=bu_df["Internet-Routable DNS"], 
                   name="Internet-Routable DNS", marker_color="orange"),
            row=1, col=2
        )
        
        # Total systems chart
        fig.add_trace(
            go.Bar(x=bu_df["Business Unit"], y=bu_df["Total Systems"], 
                   name="Total Systems", marker_color="green"),
            row=2, col=1
        )
        
        # Issues pie chart (using internet-routable DNS as proxy for issues)
        fig.add_trace(
            go.Pie(labels=bu_df["Business Unit"], values=bu_df["Internet-Routable DNS"], 
                   name="Issues Distribution"),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False, title_text="Business Unit Analysis")
        fig.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig, use_container_width=True)

def show_business_unit_details(bu_name):
    """Show detailed business unit information with tabs and downloadable lists"""
    st.header(f"🏢 {bu_name}")
    
    # Fetch detailed data for the business unit
    bu_details = fetch_data(f"business-units/{bu_name}")
    if not bu_details:
        st.error(f"Unable to load data for {bu_name}")
        return
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Systems",
            len(bu_details["systems"])
        )
    
    with col2:
        st.metric(
            "Systems with Host Files",
            bu_details["hosts_with_populated_entries"]
        )
    
    with col3:
        st.metric(
            "External DNS Resolvers",
            bu_details["hosts_with_internet_routable_dns"]
        )
    
    with col4:
        systems_with_issues = len([s for s in bu_details["systems"] if s["issues"]])
        st.metric(
            "Systems with Issues",
            systems_with_issues
        )
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Systems", "⚠️ Systems with Issues", "🌐 External DNS", "📥 Downloads"])
    
    # Prepare systems data
    systems_df = pd.DataFrame(bu_details["systems"])
    if not systems_df.empty:
        systems_df["Issue Count"] = systems_df["issues"].apply(len)
        systems_df["Issues"] = systems_df["issues"].apply(lambda x: ", ".join(x) if x else "None")
        systems_df["BigFix Status"] = systems_df["bigfix"].apply(lambda x: "✅ Yes" if x else "❌ No")
        systems_df["DNS Servers"] = systems_df["dns_servers"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    
    with tab1:
        st.subheader("All Systems")
        if not systems_df.empty:
            display_df = systems_df[["hostname", "ip", "DNS Servers", "BigFix Status", "Issue Count", "Issues"]]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No systems found for this business unit.")
    
    with tab2:
        st.subheader("Systems with Issues")
        issues_df = systems_df[systems_df["Issue Count"] > 0]
        if not issues_df.empty:
            display_df = issues_df[["hostname", "ip", "DNS Servers", "BigFix Status", "Issue Count", "Issues"]]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No systems with issues found for this business unit.")
    
    with tab3:
        st.subheader("Systems Using External DNS Resolvers")
        external_dns_df = systems_df[systems_df["DNS Servers"].str.contains("8\.8\.8\.8|8\.8\.4\.4|1\.1\.1\.1|9\.9\.9\.9", na=False)]
        if not external_dns_df.empty:
            display_df = external_dns_df[["hostname", "ip", "DNS Servers", "BigFix Status", "Issue Count", "Issues"]]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No systems using external DNS resolvers found for this business unit.")
    
    with tab4:
        st.subheader("Download Lists")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download All Systems", key=f"download_all_{bu_name}"):
                csv = systems_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{bu_name}_all_systems.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📥 Download Systems with Issues", key=f"download_issues_{bu_name}"):
                issues_df = systems_df[systems_df["Issue Count"] > 0]
                if not issues_df.empty:
                    csv = issues_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{bu_name}_systems_with_issues.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No systems with issues to download.")
        
        with col3:
            if st.button("📥 Download External DNS Systems", key=f"download_external_{bu_name}"):
                external_dns_df = systems_df[systems_df["DNS Servers"].str.contains("8\.8\.8\.8|8\.8\.4\.4|1\.1\.1\.1|9\.9\.9\.9", na=False)]
                if not external_dns_df.empty:
                    csv = external_dns_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{bu_name}_external_dns_systems.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No systems with external DNS to download.")
        
        # Summary statistics
        st.subheader("Summary Statistics")
        summary_stats = {
            "Metric": [
                "Total Systems",
                "Systems with Host Files", 
                "Systems with External DNS",
                "Systems with Issues",
                "Systems with BigFix"
            ],
            "Count": [
                len(systems_df),
                bu_details["hosts_with_populated_entries"],
                len(systems_df[systems_df["DNS Servers"].str.contains("8\.8\.8\.8|8\.8\.4\.4|1\.1\.1\.1|9\.9\.9\.9", na=False)]),
                len(systems_df[systems_df["Issue Count"] > 0]),
                len(systems_df[systems_df["bigfix"] == True])
            ]
        }
        summary_df = pd.DataFrame(summary_stats)
        st.dataframe(summary_df, use_container_width=True)

def show_system_details():
    st.header("🖥️ System Details")
    
    # Fetch all systems
    all_systems = fetch_data("systems")
    if not all_systems:
        st.error("Unable to load system data")
        return
    
    # Create DataFrame
    systems_df = pd.DataFrame(all_systems)
    systems_df["Issue Count"] = systems_df["issues"].apply(len)
    systems_df["Issues"] = systems_df["issues"].apply(lambda x: ", ".join(x) if x else "None")
    systems_df["BigFix Status"] = systems_df["bigfix"].apply(lambda x: "✅ Yes" if x else "❌ No")
    
    # Filters
    st.subheader("🔍 Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_bu = st.selectbox(
            "Business Unit:",
            ["All"] + list(systems_df["business_unit"].unique())
        )
    
    with col2:
        bigfix_filter = st.selectbox(
            "BigFix Status:",
            ["All", "Yes", "No"]
        )
    
    with col3:
        issues_filter = st.selectbox(
            "Issues:",
            ["All", "Has Issues", "No Issues"]
        )
    
    # Apply filters
    filtered_df = systems_df.copy()
    
    if selected_bu != "All":
        filtered_df = filtered_df[filtered_df["business_unit"] == selected_bu]
    
    if bigfix_filter != "All":
        bigfix_bool = bigfix_filter == "Yes"
        filtered_df = filtered_df[filtered_df["bigfix"] == bigfix_bool]
    
    if issues_filter != "All":
        if issues_filter == "Has Issues":
            filtered_df = filtered_df[filtered_df["Issue Count"] > 0]
        else:
            filtered_df = filtered_df[filtered_df["Issue Count"] == 0]
    
    # Display results
    st.subheader(f"📊 Filtered Results ({len(filtered_df)} systems)")
    
    if not filtered_df.empty:
        # Display table
        display_df = filtered_df[["hostname", "business_unit", "ip", "dns_servers", 
                                 "BigFix Status", "Issue Count", "Issues"]]
        st.dataframe(display_df, use_container_width=True)
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Systems", len(filtered_df))
        
        with col2:
            st.metric("Systems with BigFix", len(filtered_df[filtered_df["bigfix"] == True]))
        
        with col3:
            st.metric("Systems with Issues", len(filtered_df[filtered_df["Issue Count"] > 0]))
        
        with col4:
            st.metric("Systems without Issues", len(filtered_df[filtered_df["Issue Count"] == 0]))
    else:
        st.info("No systems match the selected filters.")

def show_issues_analysis():
    st.header("⚠️ Issues Analysis")
    
    # Fetch systems with issues
    systems_with_issues = fetch_data("systems/issues")
    if not systems_with_issues:
        st.error("Unable to load issues data")
        return
    
    if not systems_with_issues:
        st.info("No systems with issues found.")
        return
    
    # Create DataFrame for analysis
    issues_df = pd.DataFrame(systems_with_issues)
    issues_df["Issue Count"] = issues_df["issues"].apply(len)
    issues_df["Issues"] = issues_df["issues"].apply(lambda x: ", ".join(x) if x else "None")
    
    # Summary metrics
    st.subheader("📊 Issues Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Systems with Issues", len(issues_df))
    
    with col2:
        st.metric("Total Issues", issues_df["Issue Count"].sum())
    
    with col3:
        st.metric("Business Units Affected", issues_df["business_unit"].nunique())
    
    with col4:
        st.metric("Avg Issues per System", f"{issues_df['Issue Count'].mean():.1f}")
    
    # Business unit breakdown summary
    st.subheader("🏢 Business Units with Issues")
    bu_summary = issues_df.groupby("business_unit").agg({
        "Issue Count": ["count", "sum"]
    }).round(0)
    bu_summary.columns = ["Systems", "Total Issues"]
    bu_summary = bu_summary.sort_values("Total Issues", ascending=False)
    bu_summary_display = bu_summary.reset_index()
    bu_summary_display = bu_summary_display.rename(columns={"business_unit": "Business Unit"})
    
    st.dataframe(bu_summary_display, use_container_width=True)
    
    # Issue type analysis
    st.subheader("📊 Issue Type Distribution")
    
    # Flatten all issues
    all_issues = []
    for issues_list in issues_df["issues"]:
        all_issues.extend(issues_list)
    
    if all_issues:
        issue_counts = pd.Series(all_issues).value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart
            fig_bar = px.bar(
                x=issue_counts.index,
                y=issue_counts.values,
                title="Issue Types",
                labels={"x": "Issue Type", "y": "Count"}
            )
            fig_bar.update_xaxes(tickangle=45)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            # Add legend below title
            st.markdown("**Issue Types:**")
            issue_legend = pd.DataFrame([
                {"Issue Type": issue_type, "Count": count, "Percentage": f"{count/issue_counts.sum()*100:.1f}%"}
                for issue_type, count in issue_counts.items()
            ])
            st.dataframe(issue_legend, use_container_width=True)
            
            # Pie chart without labels on slices
            fig_pie = px.pie(
                values=issue_counts.values,
                names=issue_counts.index,
                title="Issue Distribution by Type",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
                textfont_size=14
            )
            fig_pie.update_layout(
                showlegend=False,  # Hide legend since we have the table above
                margin=dict(t=50, b=50, l=50, r=50)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Business unit issues analysis
    st.subheader("🏢 Issues by Business Unit")
    
    bu_issues = issues_df.groupby("business_unit").agg({
        "Issue Count": ["count", "sum", "mean"]
    }).round(2)
    
    bu_issues.columns = ["Systems with Issues", "Total Issues", "Avg Issues per System"]
    bu_issues = bu_issues.sort_values("Total Issues", ascending=False)
    
    # Reset index to make business unit a column
    bu_issues_display = bu_issues.reset_index()
    bu_issues_display = bu_issues_display.rename(columns={"business_unit": "Business Unit"})
    
    st.dataframe(bu_issues_display, use_container_width=True)
    
    # Add a visual chart for better understanding
    if not bu_issues_display.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart showing total issues by business unit with distinct colors
            fig_issues = px.bar(
                bu_issues_display,
                x="Business Unit",
                y="Total Issues",
                title="Total Issues by Business Unit",
                color="Business Unit",
                color_discrete_sequence=px.colors.qualitative.Set3,
                text="Total Issues"
            )
            fig_issues.update_xaxes(tickangle=45)
            fig_issues.update_traces(texttemplate='%{text}', textposition='outside')
            fig_issues.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.01
                )
            )
            st.plotly_chart(fig_issues, use_container_width=True)
        
        with col2:
            # Bar chart showing systems with issues by business unit with distinct colors
            fig_systems = px.bar(
                bu_issues_display,
                x="Business Unit", 
                y="Systems with Issues",
                title="Systems with Issues by Business Unit",
                color="Business Unit",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                text="Systems with Issues"
            )
            fig_systems.update_xaxes(tickangle=45)
            fig_systems.update_traces(texttemplate='%{text}', textposition='outside')
            fig_systems.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.01
                )
            )
            st.plotly_chart(fig_systems, use_container_width=True)
    
    
    # Detailed issues table
    st.subheader("📋 Detailed Issues")
    
    # Add expandable rows for DNS servers
    def format_dns_servers(dns_list):
        if isinstance(dns_list, list):
            return ", ".join(dns_list)
        return str(dns_list)
    
    issues_df["DNS Servers"] = issues_df["dns_servers"].apply(format_dns_servers)
    issues_df["BigFix Status"] = issues_df["bigfix"].apply(lambda x: "✅ Yes" if x else "❌ No")
    
    # Reorder columns to make business unit more prominent
    display_df = issues_df[["business_unit", "hostname", "ip", "DNS Servers", 
                           "BigFix Status", "Issue Count", "Issues"]]
    
    # Rename columns for better display
    display_df = display_df.rename(columns={
        "business_unit": "Business Unit",
        "hostname": "Hostname", 
        "ip": "IP Address"
    })
    
    st.dataframe(display_df, use_container_width=True)
    
    # Export functionality
    st.subheader("📥 Export Data")
    
    if st.button("Download Issues Report as CSV"):
        csv = issues_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="inventory_issues_report.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()

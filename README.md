# DNS Issues Dashboard

A web-based dashboard for visualizing DNS issues and IT inventory data with business unit breakdowns and issue tracking.

## Features

- **Issues Identified**: High-level statistics and metrics
- **Business Unit Analysis**: Detailed breakdown by business unit
- **System Details**: Comprehensive system information with filtering
- **Issues Analysis**: Track and analyze system issues
- **Interactive Visualizations**: Charts and graphs using Plotly
- **Export Functionality**: Download reports as CSV

## Architecture

- **Backend**: Flask API serving inventory data
- **Frontend**: Streamlit web application
- **Data Format**: JSON structure with business unit and system details

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the Flask API Server

```bash
python app.py
```

The API will be available at `http://localhost:5001`

### 2. Start the Streamlit Application

In a new terminal window:

```bash
streamlit run streamlit_app.py
```

The dashboard will be available at `http://localhost:8501`

## Data Structure

The application expects a `parsed_inventory.json` file with the following structure:

```json
{
  "summary": {
    "total_hosts_with_populated_entries": 6977,
    "hosts_with_bigfix": 2969,
    "combined_hosts_empty_dns": 13422,
    "hosts_with_populated_entries_from_empty_dns": 1086,
    "percentage_with_populated_entries": 8.09,
    "hosts_using_internet_routable_ips": 1821
  },
  "business_units": {
    "Business Unit Name": {
      "hosts_with_populated_entries": 123,
      "hosts_with_internet_routable_dns": 45,
      "systems": [
        {
          "hostname": "system-name",
          "ip": "10.1.1.1",
          "dns_servers": ["8.8.8.8", "8.8.4.4"],
          "bigfix": true,
          "issues": ["Internet-routable DNS"]
        }
      ]
    }
  }
}
```

## API Endpoints

- `GET /api/summary` - Get overall inventory summary
- `GET /api/business-units` - Get all business units with statistics
- `GET /api/business-units/<bu_name>` - Get detailed information for a specific business unit
- `GET /api/systems` - Get all systems across all business units
- `GET /api/systems/issues` - Get all systems that have issues
- `POST /api/load-data` - Load data from parsed_inventory.json file

## Dashboard Pages

### Issues Identified
- High-level metrics and KPIs
- Business unit distribution charts
- Summary statistics

### Business Units
- Business unit comparison table
- Drill-down to individual business unit details
- System listings per business unit

### System Details
- Comprehensive system information
- Advanced filtering options
- BigFix status tracking

### Issues Analysis
- Issue type distribution
- Business unit issue analysis
- Detailed issues report with export functionality

## Customization

### Adding New Issue Types
Update the `issues` array in your JSON data to include new issue types:
- "Internet-routable DNS"
- "Empty DNS servers"
- "Missing BigFix"
- "Outdated Software"

### Modifying Business Units
Add or remove business units by updating the `business_units` section in your JSON file.

### Styling
The Streamlit app uses default styling but can be customized by modifying the CSS in the `streamlit_app.py` file.

## Troubleshooting

### API Connection Issues
- Ensure Flask server is running on port 5001
- Check firewall settings
- Verify API_BASE_URL in streamlit_app.py

### Data Loading Issues
- Ensure `parsed_inventory.json` exists in the project directory
- Validate JSON format
- Check file permissions

### Performance Issues
- Use data caching (already implemented with @st.cache_data)
- Consider pagination for large datasets
- Optimize database queries if using a database backend

## Development

### Adding New Features
1. Update the Flask API with new endpoints
2. Modify the Streamlit frontend to consume new data
3. Update the JSON data structure if needed
4. Test with sample data

### Data Integration
To integrate with your existing Python script that generates `parsed_inventory.json`:

1. Ensure your script outputs the correct JSON format
2. Place the generated file in the project directory
3. Use the `/api/load-data` endpoint to refresh data
4. Or restart the Flask server to pick up new data

## License

This project is provided as-is for internal use.

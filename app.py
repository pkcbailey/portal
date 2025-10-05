from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Sample data structure based on your stats
INVENTORY_DATA = {
    "summary": {
        "total_hosts_with_populated_entries": 6977,
        "hosts_with_bigfix": 2969,
        "combined_hosts_empty_dns": 13422,
        "hosts_with_populated_entries_from_empty_dns": 1086,
        "percentage_with_populated_entries": 8.09,
        "hosts_using_internet_routable_ips": 1821
    },
    "business_units": {
        "CTIO": {
            "hosts_with_populated_entries": 809,
            "hosts_with_internet_routable_dns": 223,
            "systems": [
                {"hostname": "ctio-web-01", "ip": "10.1.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "ctio-db-01", "ip": "10.1.1.11", "dns_servers": ["168.63.129.16"], "bigfix": False, "issues": ["Empty DNS servers"]},
                {"hostname": "ctio-app-01", "ip": "10.1.1.12", "dns_servers": ["10.1.1.1", "10.1.1.2"], "bigfix": True, "issues": []}
            ]
        },
        "CornerStone": {
            "hosts_with_populated_entries": 620,
            "hosts_with_internet_routable_dns": 12,
            "systems": [
                {"hostname": "cornerstone-web-01", "ip": "10.2.1.10", "dns_servers": ["168.63.129.16"], "bigfix": True, "issues": ["Empty DNS servers"]},
                {"hostname": "cornerstone-db-01", "ip": "10.2.1.11", "dns_servers": ["8.8.8.8", "8.8.4.4"], "bigfix": False, "issues": ["Internet-routable DNS"]}
            ]
        },
        "SES Core": {
            "hosts_with_populated_entries": 109,
            "hosts_with_internet_routable_dns": 0,
            "systems": [
                {"hostname": "ses-core-01", "ip": "10.3.1.10", "dns_servers": ["10.3.1.1"], "bigfix": True, "issues": []}
            ]
        },
        "Treasury & Capital Markets": {
            "hosts_with_populated_entries": 1140,
            "hosts_with_internet_routable_dns": 140,
            "systems": [
                {"hostname": "treasury-web-01", "ip": "10.4.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "treasury-db-01", "ip": "10.4.1.11", "dns_servers": ["168.63.129.16"], "bigfix": False, "issues": ["Empty DNS servers"]}
            ]
        },
        "Universal Banking Enterprise": {
            "hosts_with_populated_entries": 709,
            "hosts_with_internet_routable_dns": 280,
            "systems": [
                {"hostname": "ube-web-01", "ip": "10.5.1.10", "dns_servers": ["8.8.8.8", "8.8.4.4"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "ube-app-01", "ip": "10.5.1.11", "dns_servers": ["10.5.1.1"], "bigfix": True, "issues": []}
            ]
        },
        "Payments": {
            "hosts_with_populated_entries": 1557,
            "hosts_with_internet_routable_dns": 713,
            "systems": [
                {"hostname": "payments-web-01", "ip": "10.6.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "payments-api-01", "ip": "10.6.1.11", "dns_servers": ["8.8.4.4"], "bigfix": False, "issues": ["Internet-routable DNS"]},
                {"hostname": "payments-db-01", "ip": "10.6.1.12", "dns_servers": ["168.63.129.16"], "bigfix": True, "issues": ["Empty DNS servers"]}
            ]
        },
        "USMM Digital & Core Banking": {
            "hosts_with_populated_entries": 584,
            "hosts_with_internet_routable_dns": 197,
            "systems": [
                {"hostname": "usmm-web-01", "ip": "10.7.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "usmm-core-01", "ip": "10.7.1.11", "dns_servers": ["10.7.1.1"], "bigfix": True, "issues": []}
            ]
        },
        "Lending": {
            "hosts_with_populated_entries": 1300,
            "hosts_with_internet_routable_dns": 142,
            "systems": [
                {"hostname": "lending-web-01", "ip": "10.8.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]},
                {"hostname": "lending-db-01", "ip": "10.8.1.11", "dns_servers": ["168.63.129.16"], "bigfix": False, "issues": ["Empty DNS servers"]}
            ]
        },
        "CISO": {
            "hosts_with_populated_entries": 43,
            "hosts_with_internet_routable_dns": 16,
            "systems": [
                {"hostname": "ciso-monitor-01", "ip": "10.9.1.10", "dns_servers": ["8.8.8.8"], "bigfix": True, "issues": ["Internet-routable DNS"]}
            ]
        },
        "UNKNOWN": {
            "hosts_with_populated_entries": 102,
            "hosts_with_internet_routable_dns": 98,
            "systems": [
                {"hostname": "unknown-host-01", "ip": "10.10.1.10", "dns_servers": ["8.8.8.8"], "bigfix": False, "issues": ["Internet-routable DNS"]}
            ]
        },
        "CFO": {
            "hosts_with_populated_entries": 2,
            "hosts_with_internet_routable_dns": 0,
            "systems": [
                {"hostname": "cfo-report-01", "ip": "10.11.1.10", "dns_servers": ["10.11.1.1"], "bigfix": True, "issues": []}
            ]
        },
        "CTO": {
            "hosts_with_populated_entries": 1,
            "hosts_with_internet_routable_dns": 0,
            "systems": [
                {"hostname": "cto-dev-01", "ip": "10.12.1.10", "dns_servers": ["10.12.1.1"], "bigfix": True, "issues": []}
            ]
        }
    }
}

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get overall inventory summary statistics"""
    return jsonify(INVENTORY_DATA["summary"])

@app.route('/api/business-units', methods=['GET'])
def get_business_units():
    """Get all business units with their statistics"""
    bu_data = {}
    for bu_name, data in INVENTORY_DATA["business_units"].items():
        bu_data[bu_name] = {
            "hosts_with_populated_entries": data["hosts_with_populated_entries"],
            "hosts_with_internet_routable_dns": data["hosts_with_internet_routable_dns"],
            "total_systems": len(data["systems"])
        }
    return jsonify(bu_data)

@app.route('/api/business-units/<bu_name>', methods=['GET'])
def get_business_unit_details(bu_name):
    """Get detailed information for a specific business unit"""
    if bu_name not in INVENTORY_DATA["business_units"]:
        return jsonify({"error": "Business unit not found"}), 404
    
    return jsonify(INVENTORY_DATA["business_units"][bu_name])

@app.route('/api/systems', methods=['GET'])
def get_all_systems():
    """Get all systems across all business units"""
    all_systems = []
    for bu_name, data in INVENTORY_DATA["business_units"].items():
        for system in data["systems"]:
            system_with_bu = system.copy()
            system_with_bu["business_unit"] = bu_name
            all_systems.append(system_with_bu)
    
    return jsonify(all_systems)

@app.route('/api/systems/issues', methods=['GET'])
def get_systems_with_issues():
    """Get all systems that have issues"""
    systems_with_issues = []
    for bu_name, data in INVENTORY_DATA["business_units"].items():
        for system in data["systems"]:
            if system["issues"]:
                system_with_bu = system.copy()
                system_with_bu["business_unit"] = bu_name
                systems_with_issues.append(system_with_bu)
    
    return jsonify(systems_with_issues)

@app.route('/api/load-data', methods=['POST'])
def load_data():
    """Load data from parsed_inventory.json file"""
    try:
        if os.path.exists('parsed_inventory.json'):
            with open('parsed_inventory.json', 'r') as f:
                global INVENTORY_DATA
                INVENTORY_DATA = json.load(f)
            return jsonify({"message": "Data loaded successfully"})
        else:
            return jsonify({"error": "parsed_inventory.json not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

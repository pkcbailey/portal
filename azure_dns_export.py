#!/usr/bin/env python3

"""
Azure DNS Zone Record Export Script

This script uses Service Principal (SPN) credentials to authenticate with Azure,
then enumerates all subscriptions, resource groups, DNS zones (public and private),
and exports all record sets to a CSV file.

Usage:
    ./azure_dns_export.py --output dns_records.csv

Environment Variables (or command-line arguments):
    AZURE_CLIENT_ID       - Service Principal Client ID
    AZURE_CLIENT_SECRET   - Service Principal Client Secret
    AZURE_TENANT_ID       - Azure Tenant ID
    AZURE_SUBSCRIPTION_ID - (Optional) Specific subscription ID to limit scope
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.dns import DnsManagementClient
    from azure.mgmt.privatedns import PrivateDnsManagementClient
    from azure.core.exceptions import AzureError, HttpResponseError
except ImportError as e:
    print(f"Error: Missing required Azure SDK packages. Please install:")
    print(f"  pip install azure-identity azure-mgmt-resource azure-mgmt-dns azure-mgmt-privatedns")
    sys.exit(1)


@dataclass
class DNSRecord:
    """Represents a DNS record for CSV export"""
    subscription_id: str
    subscription_name: str
    resource_group: str
    zone_name: str
    zone_type: str  # "Public" or "Private"
    record_name: str
    record_type: str
    ttl: int
    rdata: str
    fqdn: str = field(default="")

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for CSV export"""
        return {
            "Subscription ID": self.subscription_id,
            "Subscription Name": self.subscription_name,
            "Resource Group": self.resource_group,
            "Zone Name": self.zone_name,
            "Zone Type": self.zone_type,
            "Record Name": self.record_name,
            "Record Type": self.record_type,
            "TTL": str(self.ttl),
            "RDATA": self.rdata,
            "FQDN": self.fqdn,
        }


class AzureDNSExporter:
    """Main class for exporting Azure DNS records"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        subscription_id: Optional[str] = None,
    ):
        """
        Initialize Azure DNS Exporter with SPN credentials

        Args:
            client_id: Service Principal Client ID
            client_secret: Service Principal Client Secret
            tenant_id: Azure Tenant ID
            subscription_id: Optional specific subscription ID to limit scope
        """
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.resource_client: Optional[ResourceManagementClient] = None
        self.dns_client: Optional[DnsManagementClient] = None
        self.private_dns_client: Optional[PrivateDnsManagementClient] = None

    def _get_resource_client(self) -> ResourceManagementClient:
        """Get or create ResourceManagementClient"""
        if self.resource_client is None:
            # Use first available subscription for resource client initialization
            # We'll switch contexts per subscription as needed
            subs = self._list_subscriptions()
            if not subs:
                raise ValueError("No subscriptions found for the provided credentials")
            sub_id = self.subscription_id or subs[0]["subscription_id"]
            self.resource_client = ResourceManagementClient(
                self.credential, sub_id
            )
        return self.resource_client

    def _get_dns_client(self, subscription_id: str) -> DnsManagementClient:
        """Get DNS client for a specific subscription"""
        return DnsManagementClient(self.credential, subscription_id)

    def _get_private_dns_client(
        self, subscription_id: str
    ) -> PrivateDnsManagementClient:
        """Get Private DNS client for a specific subscription"""
        return PrivateDnsManagementClient(self.credential, subscription_id)

    def _list_subscriptions(self) -> List[Dict[str, str]]:
        """List all accessible subscriptions"""
        try:
            from azure.mgmt.resource.subscriptions import SubscriptionClient

            sub_client = SubscriptionClient(self.credential)
            subscriptions = []
            for sub in sub_client.subscriptions.list():
                subscriptions.append(
                    {
                        "subscription_id": sub.subscription_id,
                        "subscription_name": sub.display_name or sub.subscription_id,
                    }
                )
            return subscriptions
        except Exception as e:
            print(f"Error listing subscriptions: {e}")
            return []

    def _list_resource_groups(
        self, subscription_id: str
    ) -> List[str]:
        """List all resource groups in a subscription"""
        try:
            resource_client = ResourceManagementClient(
                self.credential, subscription_id
            )
            resource_groups = []
            for rg in resource_client.resource_groups.list():
                resource_groups.append(rg.name)
            return resource_groups
        except Exception as e:
            print(f"Error listing resource groups in {subscription_id}: {e}")
            return []

    def _list_public_dns_zones(
        self, subscription_id: str, resource_group: str
    ) -> List[str]:
        """List all public DNS zones in a resource group"""
        try:
            dns_client = self._get_dns_client(subscription_id)
            zones = []
            for zone in dns_client.zones.list_by_resource_group(resource_group):
                zones.append(zone.name)
            return zones
        except HttpResponseError as e:
            if e.status_code == 404:
                return []
            print(f"Error listing public DNS zones in {resource_group}: {e}")
            return []
        except Exception as e:
            print(f"Error listing public DNS zones in {resource_group}: {e}")
            return []

    def _list_private_dns_zones(
        self, subscription_id: str, resource_group: str
    ) -> List[str]:
        """List all private DNS zones in a resource group"""
        try:
            private_dns_client = self._get_private_dns_client(subscription_id)
            zones = []
            for zone in private_dns_client.private_zones.list_by_resource_group(
                resource_group
            ):
                zones.append(zone.name)
            return zones
        except HttpResponseError as e:
            if e.status_code == 404:
                return []
            print(f"Error listing private DNS zones in {resource_group}: {e}")
            return []
        except Exception as e:
            print(f"Error listing private DNS zones in {resource_group}: {e}")
            return []

    def _get_record_sets_public(
        self,
        subscription_id: str,
        subscription_name: str,
        resource_group: str,
        zone_name: str,
    ) -> List[DNSRecord]:
        """Get all record sets from a public DNS zone"""
        records: List[DNSRecord] = []
        try:
            dns_client = self._get_dns_client(subscription_id)

            # Get all record types
            record_types = [
                "A",
                "AAAA",
                "CNAME",
                "MX",
                "NS",
                "PTR",
                "SOA",
                "SRV",
                "TXT",
                "CAA",
            ]

            for record_type in record_types:
                try:
                    record_sets = dns_client.record_sets.list_by_type(
                        resource_group_name=resource_group,
                        zone_name=zone_name,
                        record_type=record_type,
                    )

                    for record_set in record_sets:
                        # Skip SOA and NS records at zone apex (these are zone-level)
                        if record_type in ("SOA", "NS") and record_set.name == "@":
                            continue

                        # Format RDATA based on record type
                        rdata = self._format_rdata(record_set, record_type)

                        record_name = record_set.name.rstrip(".")
                        if record_name == "@":
                            record_name = zone_name
                        else:
                            # Remove zone name suffix if present
                            if record_name.endswith(f".{zone_name}"):
                                record_name = record_name[: -len(f".{zone_name}")]
                            record_name = f"{record_name}.{zone_name}"

                        fqdn = record_set.fqdn.rstrip(".") if hasattr(record_set, "fqdn") else record_name

                        records.append(
                            DNSRecord(
                                subscription_id=subscription_id,
                                subscription_name=subscription_name,
                                resource_group=resource_group,
                                zone_name=zone_name,
                                zone_type="Public",
                                record_name=record_name,
                                record_type=record_type,
                                ttl=record_set.ttl or 3600,
                                rdata=rdata,
                                fqdn=fqdn,
                            )
                        )
                except HttpResponseError as e:
                    if e.status_code != 404:
                        print(
                            f"Warning: Could not list {record_type} records in {zone_name}: {e}"
                        )
                    continue
        except Exception as e:
            print(
                f"Error getting record sets from public zone {zone_name} in {resource_group}: {e}"
            )

        return records

    def _get_record_sets_private(
        self,
        subscription_id: str,
        subscription_name: str,
        resource_group: str,
        zone_name: str,
    ) -> List[DNSRecord]:
        """Get all record sets from a private DNS zone"""
        records: List[DNSRecord] = []
        try:
            private_dns_client = self._get_private_dns_client(subscription_id)

            record_types = [
                "A",
                "AAAA",
                "CNAME",
                "MX",
                "PTR",
                "SOA",
                "SRV",
                "TXT",
            ]

            for record_type in record_types:
                try:
                    record_sets = private_dns_client.record_sets.list_by_type(
                        resource_group_name=resource_group,
                        private_zone_name=zone_name,
                        record_type=record_type,
                    )

                    for record_set in record_sets:
                        # Skip SOA records at zone apex
                        if record_type == "SOA" and record_set.name == "@":
                            continue

                        rdata = self._format_rdata(record_set, record_type)

                        record_name = record_set.name.rstrip(".")
                        if record_name == "@":
                            record_name = zone_name
                        else:
                            if record_name.endswith(f".{zone_name}"):
                                record_name = record_name[: -len(f".{zone_name}")]
                            record_name = f"{record_name}.{zone_name}"

                        fqdn = record_set.fqdn.rstrip(".") if hasattr(record_set, "fqdn") else record_name

                        records.append(
                            DNSRecord(
                                subscription_id=subscription_id,
                                subscription_name=subscription_name,
                                resource_group=resource_group,
                                zone_name=zone_name,
                                zone_type="Private",
                                record_name=record_name,
                                record_type=record_type,
                                ttl=record_set.ttl or 3600,
                                rdata=rdata,
                                fqdn=fqdn,
                            )
                        )
                except HttpResponseError as e:
                    if e.status_code != 404:
                        print(
                            f"Warning: Could not list {record_type} records in private zone {zone_name}: {e}"
                        )
                    continue
        except Exception as e:
            print(
                f"Error getting record sets from private zone {zone_name} in {resource_group}: {e}"
            )

        return records

    def _format_rdata(self, record_set, record_type: str) -> str:
        """Format RDATA based on record type"""
        rdata_parts = []

        if record_type == "A" and hasattr(record_set, "a_records"):
            rdata_parts = [str(rec.ipv4_address) for rec in record_set.a_records or []]
        elif record_type == "AAAA" and hasattr(record_set, "aaaa_records"):
            rdata_parts = [
                str(rec.ipv6_address) for rec in record_set.aaaa_records or []
            ]
        elif record_type == "CNAME" and hasattr(record_set, "cname_record"):
            if record_set.cname_record:
                rdata_parts = [record_set.cname_record.cname or ""]
        elif record_type == "MX" and hasattr(record_set, "mx_records"):
            rdata_parts = [
                f"{rec.preference} {rec.exchange.rstrip('.')}"
                for rec in record_set.mx_records or []
            ]
        elif record_type == "NS" and hasattr(record_set, "ns_records"):
            rdata_parts = [rec.nsdname.rstrip(".") for rec in record_set.ns_records or []]
        elif record_type == "PTR" and hasattr(record_set, "ptr_records"):
            rdata_parts = [rec.ptrdname.rstrip(".") for rec in record_set.ptr_records or []]
        elif record_type == "SRV" and hasattr(record_set, "srv_records"):
            rdata_parts = [
                f"{rec.priority} {rec.weight} {rec.port} {rec.target.rstrip('.')}"
                for rec in record_set.srv_records or []
            ]
        elif record_type == "TXT" and hasattr(record_set, "txt_records"):
            # TXT records can have multiple strings per record
            rdata_parts = [
                " ".join(f'"{val}"' for val in rec.value or [])
                for rec in record_set.txt_records or []
            ]
        elif record_type == "CAA" and hasattr(record_set, "caa_records"):
            rdata_parts = [
                f'{rec.flags} {rec.tag} "{rec.value}"'
                for rec in record_set.caa_records or []
            ]
        elif record_type == "SOA" and hasattr(record_set, "soa_record"):
            if record_set.soa_record:
                soa = record_set.soa_record
                rdata_parts = [
                    f"{soa.host.rstrip('.')} {soa.email.rstrip('.')} {soa.serial_number} "
                    f"{soa.refresh_time} {soa.retry_time} {soa.expire_time} {soa.minimum_ttl}"
                ]

        return ", ".join(rdata_parts) if rdata_parts else ""

    def export_all_records(self, output_path: Path) -> int:
        """
        Export all DNS records from all subscriptions to CSV

        Returns:
            Number of records exported
        """
        print("Starting Azure DNS export...")
        print(f"Tenant ID: {self.tenant_id}")

        # Get subscriptions
        subscriptions = self._list_subscriptions()
        if not subscriptions:
            print("No subscriptions found. Check your credentials and permissions.")
            return 0

        if self.subscription_id:
            subscriptions = [
                s
                for s in subscriptions
                if s["subscription_id"] == self.subscription_id
            ]
            if not subscriptions:
                print(
                    f"Subscription {self.subscription_id} not found or not accessible."
                )
                return 0

        print(f"Found {len(subscriptions)} subscription(s)")

        all_records: List[DNSRecord] = []

        # Iterate through subscriptions
        for sub_info in subscriptions:
            sub_id = sub_info["subscription_id"]
            sub_name = sub_info["subscription_name"]
            print(f"\nProcessing subscription: {sub_name} ({sub_id})")

            # Get resource groups
            resource_groups = self._list_resource_groups(sub_id)
            print(f"  Found {len(resource_groups)} resource group(s)")

            # Iterate through resource groups
            for rg in resource_groups:
                print(f"  Processing resource group: {rg}")

                # Get public DNS zones
                public_zones = self._list_public_dns_zones(sub_id, rg)
                for zone in public_zones:
                    print(f"    Processing public DNS zone: {zone}")
                    records = self._get_record_sets_public(
                        sub_id, sub_name, rg, zone
                    )
                    all_records.extend(records)
                    print(f"      Found {len(records)} record(s)")

                # Get private DNS zones
                private_zones = self._list_private_dns_zones(sub_id, rg)
                for zone in private_zones:
                    print(f"    Processing private DNS zone: {zone}")
                    records = self._get_record_sets_private(
                        sub_id, sub_name, rg, zone
                    )
                    all_records.extend(records)
                    print(f"      Found {len(records)} record(s)")

        # Write to CSV
        print(f"\nWriting {len(all_records)} record(s) to {output_path}")
        if all_records:
            fieldnames = [
                "Subscription ID",
                "Subscription Name",
                "Resource Group",
                "Zone Name",
                "Zone Type",
                "Record Name",
                "Record Type",
                "TTL",
                "RDATA",
                "FQDN",
            ]

            with output_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for record in all_records:
                    writer.writerow(record.to_dict())

            print(f"Export complete! Records written to {output_path}")
        else:
            print("No records found to export.")

        return len(all_records)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Export all Azure DNS records to CSV using Service Principal authentication"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("azure_dns_records.csv"),
        help="Output CSV file path (default: azure_dns_records.csv)",
    )
    parser.add_argument(
        "--client-id",
        help="Service Principal Client ID (or set AZURE_CLIENT_ID env var)",
    )
    parser.add_argument(
        "--client-secret",
        help="Service Principal Client Secret (or set AZURE_CLIENT_SECRET env var)",
    )
    parser.add_argument(
        "--tenant-id",
        help="Azure Tenant ID (or set AZURE_TENANT_ID env var)",
    )
    parser.add_argument(
        "--subscription-id",
        help="Optional: Limit to specific subscription ID (or set AZURE_SUBSCRIPTION_ID env var)",
    )
    return parser.parse_args()


def get_credentials(args: argparse.Namespace) -> tuple[str, str, str, Optional[str]]:
    """Get credentials from args or environment variables"""
    client_id = args.client_id or os.getenv("AZURE_CLIENT_ID")
    client_secret = args.client_secret or os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = args.tenant_id or os.getenv("AZURE_TENANT_ID")
    subscription_id = args.subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")

    if not client_id:
        raise ValueError(
            "Client ID required. Set --client-id or AZURE_CLIENT_ID environment variable."
        )
    if not client_secret:
        raise ValueError(
            "Client Secret required. Set --client-secret or AZURE_CLIENT_SECRET environment variable."
        )
    if not tenant_id:
        raise ValueError(
            "Tenant ID required. Set --tenant-id or AZURE_TENANT_ID environment variable."
        )

    return client_id, client_secret, tenant_id, subscription_id


def main() -> None:
    """Main entry point"""
    try:
        args = parse_args()
        client_id, client_secret, tenant_id, subscription_id = get_credentials(args)

        exporter = AzureDNSExporter(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            subscription_id=subscription_id,
        )

        record_count = exporter.export_all_records(args.output)
        sys.exit(0 if record_count > 0 else 1)

    except KeyboardInterrupt:
        print("\n\nExport cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


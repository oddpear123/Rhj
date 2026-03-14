#!/usr/bin/env python3
"""
oci_free_tier_provision.py

Pseudocode / Template script for provisioning Oracle Cloud Infrastructure
Always Free resources (Autonomous DB + ARM Compute) via the OCI Python SDK.

Tenant: brooksRoley

PREREQUISITES:
    1. pip install oci
    2. OCI config file at ~/.oci/config with API signing key
    3. Update the CONFIG section below with your OCIDs

USAGE:
    python3 oci_free_tier_provision.py

NOTE: This is a pseudocode template. Replace all placeholder values
      with your actual OCIDs and credentials before running.
"""

import sys
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# -----------------------------------------------
# PSEUDOCODE: Import OCI SDK
# In a real environment, uncomment the line below:
# import oci
# -----------------------------------------------

# -----------------------------------------------
# CONFIGURATION
# -----------------------------------------------
@dataclass
class OCIFreeTierConfig:
    """All configuration for the brooksRoley tenant provisioning."""

    # Tenant identity
    tenant_name: str = "brooksRoley"
    config_profile: str = "DEFAULT"             # Profile name in ~/.oci/config

    # Compartment — use tenancy root OCID or a sub-compartment
    compartment_id: str = "<YOUR_COMPARTMENT_OCID>"

    # Region — Always Free resources only work in your home region
    home_region: str = "us-phoenix-1"

    # Availability domain(s) to try — list multiple for fallback
    availability_domains: list = field(default_factory=lambda: [
        "<YOUR_AD_1>",   # e.g. "Ualh:PHX-AD-1"
        "<YOUR_AD_2>",   # optional fallback AD
    ])

    # ---- Autonomous Database ----
    db_name: str = "brooksdb"                   # Max 14 alphanumeric chars
    db_display_name: str = "brooksRoley_FreeTierDB"
    db_admin_password: str = "<STRONG_PASSWORD>"  # 12-30 chars, mixed case + number
    db_workload: str = "OLTP"                   # "OLTP" or "DW"

    # ---- Compute Instance ----
    compute_display_name: str = "brooksRoley_FreeTierVM"
    compute_shape: str = "VM.Standard.A1.Flex"  # ARM-based Always Free shape
    compute_ocpus: float = 1.0                  # Up to 4 free total across A1 instances
    compute_memory_gb: float = 6.0              # Up to 24 GB free total
    boot_volume_size_gb: int = 50               # 50-200 GB (200 GB free total)
    image_id: str = "<ORACLE_LINUX_AARCH64_IMAGE_OCID>"
    ssh_public_key_file: str = str(Path.home() / ".ssh" / "id_rsa.pub")

    # ---- Networking ----
    subnet_id: str = "<YOUR_SUBNET_OCID>"

    # ---- Retry behavior (for "out of capacity" errors) ----
    max_retries: int = 60
    retry_interval_secs: int = 60


# -----------------------------------------------
# LOGGING SETUP
# -----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"/tmp/oci_provision_{OCIFreeTierConfig.tenant_name}_{int(time.time())}.log"),
    ],
)
log = logging.getLogger(__name__)


# -----------------------------------------------
# OCI CLIENT INITIALIZATION
# -----------------------------------------------
class OCIClients:
    """
    PSEUDOCODE: Initialize all required OCI service clients.

    In a real implementation, this loads ~/.oci/config and creates
    typed clients for each OCI service we need.
    """

    def __init__(self, config_profile: str = "DEFAULT"):
        log.info("Initializing OCI clients (profile: %s)...", config_profile)

        # PSEUDOCODE:
        # self.config = oci.config.from_file(profile_name=config_profile)
        # oci.config.validate_config(self.config)
        #
        # self.identity   = oci.identity.IdentityClient(self.config)
        # self.compute    = oci.core.ComputeClient(self.config)
        # self.network    = oci.core.VirtualNetworkClient(self.config)
        # self.database   = oci.database.DatabaseClient(self.config)
        # self.block_storage = oci.core.BlockstorageClient(self.config)
        #
        # # Composite clients for wait-for-state operations
        # self.compute_composite = oci.core.ComputeClientCompositeOperations(self.compute)
        # self.database_composite = oci.database.DatabaseClientCompositeOperations(self.database)
        # self.network_composite = oci.core.VirtualNetworkClientCompositeOperations(self.network)

        log.info("OCI clients initialized.")


# -----------------------------------------------
# STEP 0: DISCOVER OR CREATE NETWORKING
# -----------------------------------------------
def ensure_networking(clients: OCIClients, cfg: OCIFreeTierConfig) -> str:
    """
    PSEUDOCODE: Check if a VCN and public subnet exist.
    If not, create them with internet gateway and route rules.

    Returns the subnet OCID to use for the compute instance.
    """
    log.info("=== Step 0: Ensuring network infrastructure ===")

    if cfg.subnet_id and not cfg.subnet_id.startswith("<"):
        log.info("Using pre-configured subnet: %s", cfg.subnet_id)
        return cfg.subnet_id

    log.info("No subnet configured — creating VCN + subnet...")

    # PSEUDOCODE: Create VCN
    # vcn_response = clients.network_composite.create_vcn_and_wait_for_state(
    #     oci.core.models.CreateVcnDetails(
    #         compartment_id=cfg.compartment_id,
    #         display_name=f"{cfg.tenant_name}_VCN",
    #         cidr_blocks=["10.0.0.0/16"],
    #     ),
    #     wait_for_states=[oci.core.models.Vcn.LIFECYCLE_STATE_AVAILABLE],
    # )
    # vcn = vcn_response.data
    # log.info("VCN created: %s", vcn.id)

    # PSEUDOCODE: Create Internet Gateway
    # igw_response = clients.network_composite.create_internet_gateway_and_wait_for_state(
    #     oci.core.models.CreateInternetGatewayDetails(
    #         compartment_id=cfg.compartment_id,
    #         vcn_id=vcn.id,
    #         display_name=f"{cfg.tenant_name}_IGW",
    #         is_enabled=True,
    #     ),
    #     wait_for_states=[oci.core.models.InternetGateway.LIFECYCLE_STATE_AVAILABLE],
    # )
    # igw = igw_response.data

    # PSEUDOCODE: Add route rule for 0.0.0.0/0 -> IGW
    # clients.network.update_route_table(
    #     vcn.default_route_table_id,
    #     oci.core.models.UpdateRouteTableDetails(
    #         route_rules=[
    #             oci.core.models.RouteRule(
    #                 destination="0.0.0.0/0",
    #                 destination_type="CIDR_BLOCK",
    #                 network_entity_id=igw.id,
    #             )
    #         ]
    #     ),
    # )

    # PSEUDOCODE: Update default security list to allow SSH (port 22) ingress
    # security_list = clients.network.get_security_list(vcn.default_security_list_id).data
    # ingress_rules = security_list.ingress_security_rules + [
    #     oci.core.models.IngressSecurityRule(
    #         protocol="6",  # TCP
    #         source="0.0.0.0/0",
    #         tcp_options=oci.core.models.TcpOptions(
    #             destination_port_range=oci.core.models.PortRange(min=22, max=22)
    #         ),
    #     )
    # ]
    # clients.network.update_security_list(
    #     vcn.default_security_list_id,
    #     oci.core.models.UpdateSecurityListDetails(ingress_security_rules=ingress_rules),
    # )

    # PSEUDOCODE: Create public subnet
    # subnet_response = clients.network_composite.create_subnet_and_wait_for_state(
    #     oci.core.models.CreateSubnetDetails(
    #         compartment_id=cfg.compartment_id,
    #         vcn_id=vcn.id,
    #         cidr_block="10.0.0.0/24",
    #         display_name=f"{cfg.tenant_name}_Subnet",
    #         route_table_id=vcn.default_route_table_id,
    #         security_list_ids=[vcn.default_security_list_id],
    #     ),
    #     wait_for_states=[oci.core.models.Subnet.LIFECYCLE_STATE_AVAILABLE],
    # )
    # subnet = subnet_response.data
    # log.info("Subnet created: %s", subnet.id)
    # return subnet.id

    return "<CREATED_SUBNET_OCID>"


# -----------------------------------------------
# STEP 1: CREATE AUTONOMOUS DATABASE
# -----------------------------------------------
def create_autonomous_database(clients: OCIClients, cfg: OCIFreeTierConfig) -> str:
    """
    PSEUDOCODE: Provision an Always Free Autonomous Database.

    Key flags:
      - is_free_tier=True  → constrains to 1 OCPU, 20 GB storage
      - db_workload="OLTP" → Autonomous Transaction Processing
      - db_workload="DW"   → Autonomous Data Warehouse

    Returns the database OCID.
    """
    log.info("=== Step 1: Creating Always Free Autonomous Database ===")
    log.info("  DB Name:   %s", cfg.db_name)
    log.info("  Workload:  %s", cfg.db_workload)
    log.info("  Free Tier: True")

    # PSEUDOCODE: Create the database
    # db_response = clients.database_composite.create_autonomous_database_and_wait_for_state(
    #     oci.database.models.CreateAutonomousDatabaseDetails(
    #         compartment_id=cfg.compartment_id,
    #         db_name=cfg.db_name,
    #         display_name=cfg.db_display_name,
    #         admin_password=cfg.db_admin_password,
    #         cpu_core_count=1,
    #         data_storage_size_in_tbs=1,       # Requested 1 TB, free tier auto-scales to 20 GB
    #         db_workload=cfg.db_workload,
    #         is_free_tier=True,
    #         license_model="LICENSE_INCLUDED",
    #         is_auto_scaling_enabled=False,
    #     ),
    #     wait_for_states=[
    #         oci.database.models.AutonomousDatabase.LIFECYCLE_STATE_AVAILABLE
    #     ],
    # )
    # db = db_response.data
    #
    # log.info("Autonomous DB created!")
    # log.info("  OCID:    %s", db.id)
    # log.info("  State:   %s", db.lifecycle_state)
    # log.info("  Console: %s", db.service_console_url)
    #
    # # Extract connection strings
    # conn = db.connection_strings
    # log.info("  Connection (HIGH):   %s", conn.high)
    # log.info("  Connection (MEDIUM): %s", conn.medium)
    # log.info("  Connection (LOW):    %s", conn.low)
    #
    # return db.id

    log.info("[PSEUDOCODE] Database creation would happen here.")
    return "<DB_OCID_PLACEHOLDER>"


# -----------------------------------------------
# STEP 2: DOWNLOAD DATABASE WALLET
# -----------------------------------------------
def download_wallet(clients: OCIClients, db_ocid: str, cfg: OCIFreeTierConfig) -> Path:
    """
    PSEUDOCODE: Download the connection wallet for the Autonomous Database.
    Required for secure connections via SQL*Net, JDBC, etc.
    """
    log.info("=== Step 2: Downloading Database Wallet ===")

    wallet_dir = Path.home() / "oracle_wallet" / cfg.db_name
    wallet_zip = wallet_dir / "wallet.zip"

    # PSEUDOCODE:
    # wallet_dir.mkdir(parents=True, exist_ok=True)
    #
    # wallet_response = clients.database.generate_autonomous_database_wallet(
    #     autonomous_database_id=db_ocid,
    #     generate_autonomous_database_wallet_details=(
    #         oci.database.models.GenerateAutonomousDatabaseWalletDetails(
    #             password=cfg.db_admin_password,
    #         )
    #     ),
    # )
    #
    # with open(wallet_zip, "wb") as f:
    #     for chunk in wallet_response.data.raw.stream(1024 * 1024):
    #         f.write(chunk)
    #
    # # Extract the wallet
    # import zipfile
    # with zipfile.ZipFile(wallet_zip, 'r') as z:
    #     z.extractall(wallet_dir)
    #
    # log.info("Wallet saved to: %s", wallet_dir)

    log.info("[PSEUDOCODE] Wallet download would happen here → %s", wallet_dir)
    return wallet_dir


# -----------------------------------------------
# STEP 3: LAUNCH COMPUTE INSTANCE (with retry)
# -----------------------------------------------
def launch_compute_instance(
    clients: OCIClients,
    subnet_id: str,
    cfg: OCIFreeTierConfig,
) -> Optional[str]:
    """
    PSEUDOCODE: Launch an Always Free ARM (A1.Flex) compute instance.

    Because ARM capacity is often constrained, this retries on
    "Out of host capacity" errors across multiple availability domains.

    Returns the instance OCID on success, or None on failure.
    """
    log.info("=== Step 3: Launching Always Free Compute Instance ===")
    log.info("  Shape:   %s", cfg.compute_shape)
    log.info("  OCPUs:   %s", cfg.compute_ocpus)
    log.info("  Memory:  %s GB", cfg.compute_memory_gb)
    log.info("  Max retries: %d (every %ds)", cfg.max_retries, cfg.retry_interval_secs)

    # PSEUDOCODE: Read SSH public key
    # ssh_key = Path(cfg.ssh_public_key_file).read_text().strip()

    # PSEUDOCODE: Build launch details
    # launch_details = oci.core.models.LaunchInstanceDetails(
    #     compartment_id=cfg.compartment_id,
    #     display_name=cfg.compute_display_name,
    #     shape=cfg.compute_shape,
    #     shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
    #         ocpus=cfg.compute_ocpus,
    #         memory_in_gbs=cfg.compute_memory_gb,
    #     ),
    #     source_details=oci.core.models.InstanceSourceViaImageDetails(
    #         image_id=cfg.image_id,
    #         boot_volume_size_in_gbs=cfg.boot_volume_size_gb,
    #     ),
    #     create_vnic_details=oci.core.models.CreateVnicDetails(
    #         subnet_id=subnet_id,
    #         assign_public_ip=True,
    #     ),
    #     metadata={
    #         "ssh_authorized_keys": ssh_key,
    #     },
    #     # availability_domain is set per-attempt below
    # )

    for attempt in range(1, cfg.max_retries + 1):
        # Cycle through availability domains
        ad = cfg.availability_domains[(attempt - 1) % len(cfg.availability_domains)]
        log.info("  Attempt %d/%d — AD: %s", attempt, cfg.max_retries, ad)

        # PSEUDOCODE: Try launching
        # try:
        #     launch_details.availability_domain = ad
        #     response = clients.compute_composite.launch_instance_and_wait_for_state(
        #         launch_details,
        #         wait_for_states=[
        #             oci.core.models.Instance.LIFECYCLE_STATE_RUNNING,
        #         ],
        #     )
        #     instance = response.data
        #     log.info("Instance created: %s", instance.id)
        #     return instance.id
        #
        # except oci.exceptions.ServiceError as e:
        #     if e.status == 500 and "Out of host capacity" in str(e.message):
        #         log.warning("    Out of capacity in %s — retrying in %ds...",
        #                     ad, cfg.retry_interval_secs)
        #         time.sleep(cfg.retry_interval_secs)
        #     elif e.status == 400 and "LimitExceeded" in str(e.code):
        #         log.error("    Free tier limit reached — you may already have instances.")
        #         return None
        #     else:
        #         log.error("    Unexpected error: %s (status=%d)", e.message, e.status)
        #         time.sleep(cfg.retry_interval_secs)

        log.info("    [PSEUDOCODE] Would attempt launch here...")
        break  # Remove this break in real usage

    log.error("FAILED: Could not create instance after %d attempts.", cfg.max_retries)
    log.error("TIP: Try during off-peak hours (early morning UTC) or change home region.")
    return None


# -----------------------------------------------
# STEP 4: GET INSTANCE PUBLIC IP
# -----------------------------------------------
def get_instance_public_ip(clients: OCIClients, instance_id: str, cfg: OCIFreeTierConfig) -> Optional[str]:
    """
    PSEUDOCODE: Retrieve the public IP address of the launched instance.
    """
    log.info("=== Step 4: Retrieving Public IP ===")

    # PSEUDOCODE:
    # vnic_attachments = oci.pagination.list_call_get_all_results(
    #     clients.compute.list_vnic_attachments,
    #     compartment_id=cfg.compartment_id,
    #     instance_id=instance_id,
    # ).data
    #
    # if not vnic_attachments:
    #     log.error("No VNIC attachments found for instance.")
    #     return None
    #
    # vnic = clients.network.get_vnic(vnic_attachments[0].vnic_id).data
    # log.info("Public IP: %s", vnic.public_ip)
    # return vnic.public_ip

    log.info("[PSEUDOCODE] Would retrieve public IP here.")
    return "<PUBLIC_IP_PLACEHOLDER>"


# -----------------------------------------------
# MAIN ORCHESTRATOR
# -----------------------------------------------
def main():
    cfg = OCIFreeTierConfig()

    log.info("=" * 60)
    log.info(" OCI Free Tier Provisioning — Tenant: %s", cfg.tenant_name)
    log.info("=" * 60)

    # Initialize OCI SDK clients
    clients = OCIClients(config_profile=cfg.config_profile)

    # Step 0: Networking
    subnet_id = ensure_networking(clients, cfg)

    # Step 1: Autonomous Database
    db_ocid = create_autonomous_database(clients, cfg)

    # Step 2: Wallet download
    wallet_path = download_wallet(clients, db_ocid, cfg)

    # Step 3: Compute instance (with retry loop)
    instance_id = launch_compute_instance(clients, subnet_id, cfg)

    # Step 4: Get public IP
    public_ip = None
    if instance_id:
        public_ip = get_instance_public_ip(clients, instance_id, cfg)

    # Summary
    log.info("")
    log.info("=" * 60)
    log.info(" PROVISIONING SUMMARY — Tenant: %s", cfg.tenant_name)
    log.info("=" * 60)
    log.info(" Autonomous Database:")
    log.info("   OCID:       %s", db_ocid)
    log.info("   Name:       %s", cfg.db_name)
    log.info("   Workload:   %s", cfg.db_workload)
    log.info("   Wallet:     %s", wallet_path)
    log.info("")
    log.info(" Compute Instance:")
    log.info("   OCID:       %s", instance_id or "FAILED")
    log.info("   Shape:      %s (%s OCPU, %s GB RAM)",
             cfg.compute_shape, cfg.compute_ocpus, cfg.compute_memory_gb)
    log.info("   Public IP:  %s", public_ip or "N/A")
    if public_ip:
        ssh_key_path = cfg.ssh_public_key_file.replace(".pub", "")
        log.info("   SSH:        ssh -i %s opc@%s", ssh_key_path, public_ip)
    log.info("")
    log.info(" Next steps:")
    log.info("   1. Connect to DB:  Use wallet at %s with SQL Developer or sqlcl", wallet_path)
    log.info("   2. SSH to VM:      ssh opc@%s", public_ip or "<IP>")
    log.info("   3. Install stack:  sudo dnf install -y python3 nginx docker ...")
    log.info("   4. Deploy app and connect to your Autonomous DB")
    log.info("=" * 60)


if __name__ == "__main__":
    main()

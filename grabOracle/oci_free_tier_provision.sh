#!/usr/bin/env bash
#===============================================================================
# oci_free_tier_provision.sh
#
# Robust, comprehensive provisioning of OCI Always Free resources.
# Covers: Autonomous Database (ATP) + ARM Compute (A1.Flex)
#===============================================================================

set -euo pipefail

#---------------------------------------
# CONFIGURATION
#---------------------------------------
COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaaawle4df6xwunmftvdix72dgcourorz3bd52xyejsjk3cmvo5goia"
REGION="us-sanjose-1"  # Home region
DISPLAY_NAME_PREFIX="rhj-core"

# Database config
DB_NAME="brooksdb"
DB_ADMIN_PASSWORD="StrongPassword123!"  # Change this after first login if possible
DB_WORKLOAD="OLTP"                      # Autonomous Transaction Processing

# Compute config
COMPUTE_SHAPE="VM.Standard.A1.Flex"     # ARM-based Always Free
COMPUTE_OCPUS=4                         # Max Always Free
COMPUTE_MEMORY_GB=24                    # Max Always Free
BOOT_VOLUME_SIZE_GB=100
SSH_PUBLIC_KEY_FILE="$HOME/.ssh/id_ed25519.pub"

# Retry settings
MAX_RETRIES=120
RETRY_INTERVAL=60

# Output tracking
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/oci_provision_${TIMESTAMP}.log"

#---------------------------------------
# HELPER FUNCTIONS
#---------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_prereqs() {
    log "=== Checking Prerequisites ==="
    if ! command -v oci &>/dev/null; then
        log "ERROR: OCI CLI not found. Please install it first."
        exit 1
    fi
    if [[ ! -f "$SSH_PUBLIC_KEY_FILE" ]]; then
        log "ERROR: SSH public key not found at $SSH_PUBLIC_KEY_FILE"
        exit 1
    fi
    log "OCI CLI and SSH key verified."
}

wait_for_resource() {
    local cmd=$1
    local id_param=$2
    local id=$3
    local target_state=$4
    local interval=${5:-20}
    local max_wait=${6:-1800} # Default 30 minutes
    
    log "  Waiting for $id to become $target_state..."
    local start_time=$(date +%s)
    while true; do
        local state=$($cmd $id_param "$id" --region "$REGION" --query 'data."lifecycle-state"' --raw-output 2>/dev/null)
        if [[ "$state" == "$target_state" ]]; then
            log "  $id is now $state."
            return 0
        fi
        if [[ "$(($(date +%s) - start_time))" -gt "$max_wait" ]]; then
            log "  Timed out waiting for $id to reach $target_state."
            return 1
        fi
        sleep "$interval"
    done
}

discover_resources() {
    log "=== Discovering Existing Resources in $REGION ==="
    
    AD=$(oci iam availability-domain list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
        --query 'data[0].name' --raw-output 2>/dev/null) || true
    if [[ -z "$AD" || "$AD" == "null" ]]; then
        log "ERROR: Could not find AD in $REGION."
        exit 1
    fi
    log "  AD: $AD"

    SUBNET_ID=$(oci network subnet list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
        --query 'data[?contains("display-name", `RHJ-subnet`)].id | [0]' --raw-output 2>/dev/null) || true
    if [[ -z "$SUBNET_ID" || "$SUBNET_ID" == "null" ]]; then
        SUBNET_ID=$(oci network subnet list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
            --query 'data[0].id' --raw-output 2>/dev/null) || true
    fi
    
    if [[ -z "$SUBNET_ID" || "$SUBNET_ID" == "null" ]]; then
        log "ERROR: No subnet found. Please create a VCN and Subnet first."
        exit 1
    fi
    log "  Subnet ID: $SUBNET_ID"

    IMAGE_ID=$(oci compute image list \
        --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
        --operating-system "Canonical Ubuntu" --operating-system-version "22.04 Minimal aarch64" \
        --shape "$COMPUTE_SHAPE" --sort-by TIMECREATED --sort-order DESC \
        --query 'data[0].id' --raw-output 2>/dev/null) || true
    
    if [[ -z "$IMAGE_ID" || "$IMAGE_ID" == "null" ]]; then
        log "ERROR: Could not find suitable ARM image."
        exit 1
    fi
    log "  Image ID: $IMAGE_ID"
}

provision_database() {
    log "=== Step 1: Provisioning Autonomous Database ==="
    
    EXISTING_DB=$(oci db autonomous-database list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
        --query "data[?\"db-name\"=='$DB_NAME'].id | [0]" --raw-output 2>/dev/null) || true
    
    if [[ -n "$EXISTING_DB" && "$EXISTING_DB" != "null" ]]; then
        log "  Database '$DB_NAME' already exists: $EXISTING_DB"
        DB_OCID=$EXISTING_DB
    else
        log "  Creating Always Free Autonomous Database '$DB_NAME'..."
        DB_OCID=$(oci db autonomous-database create \
            --compartment-id "$COMPARTMENT_ID" \
            --db-name "$DB_NAME" \
            --display-name "${DB_NAME}_FreeTier" \
            --admin-password "$DB_ADMIN_PASSWORD" \
            --cpu-core-count 1 \
            --data-storage-size-in-tbs 1 \
            --db-workload "$DB_WORKLOAD" \
            --is-free-tier TRUE \
            --license-model "LICENSE_INCLUDED" \
            --region "$REGION" \
            --query 'data.id' --raw-output)
    fi

    wait_for_resource "oci db autonomous-database get" "--autonomous-database-id" "$DB_OCID" "AVAILABLE"
}

provision_compute() {
    log "=== Step 2: Provisioning Compute Instance (ARM) ==="
    log "  Shape: $COMPUTE_SHAPE ($COMPUTE_OCPUS OCPU, $COMPUTE_MEMORY_GB GB RAM)"
    log "  Capacity retry loop active (max $MAX_RETRIES attempts)..."

    # Check if instance already exists
    EXISTING_INSTANCE=$(oci compute instance list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
        --query "data[?contains(\"display-name\", \`$DISPLAY_NAME_PREFIX\`) && \"lifecycle-state\"=='RUNNING'].id | [0]" --raw-output 2>/dev/null) || true
    
    if [[ -n "$EXISTING_INSTANCE" && "$EXISTING_INSTANCE" != "null" ]]; then
        log "  Running instance already exists: $EXISTING_INSTANCE"
        INSTANCE_ID=$EXISTING_INSTANCE
    else
        local attempt=0
        local user_data_file="$(dirname "$0")/cloud-init.sh"
        while [[ $attempt -lt $MAX_RETRIES ]]; do
            attempt=$((attempt + 1))
            log "  Attempt #$attempt..."

            RESULT=$(oci compute instance launch \
                --region "$REGION" \
                --availability-domain "$AD" \
                --compartment-id "$COMPARTMENT_ID" \
                --shape "$COMPUTE_SHAPE" \
                --shape-config "{\"ocpus\":$COMPUTE_OCPUS,\"memoryInGBs\":$COMPUTE_MEMORY_GB}" \
                --subnet-id "$SUBNET_ID" \
                --image-id "$IMAGE_ID" \
                --display-name "${DISPLAY_NAME_PREFIX}-$(date +%s)" \
                --assign-public-ip true \
                --ssh-authorized-keys-file "$SSH_PUBLIC_KEY_FILE" \
                --boot-volume-size-in-gbs "$BOOT_VOLUME_SIZE_GB" \
                --user-data-file "$user_data_file" \
                2>&1) && {
                    log "  SUCCESS! Instance launched."
                    INSTANCE_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null) || true
                    break
                }

            if echo "$RESULT" | grep -qi "out of.*capacity"; then
                log "    Out of capacity in $REGION. Retrying in ${RETRY_INTERVAL}s..."
                sleep "$RETRY_INTERVAL"
            else
                log "    ERROR: $(echo "$RESULT" | head -n 3)"
                if echo "$RESULT" | grep -qi "LimitExceeded"; then
                    log "    Limit exceeded. You might already have an instance."
                    INSTANCE_ID=$(oci compute instance list --compartment-id "$COMPARTMENT_ID" --region "$REGION" \
                        --query "data[?contains(\"display-name\", \`$DISPLAY_NAME_PREFIX\`)].id | [0]" --raw-output 2>/dev/null) || true
                    break
                fi
                sleep "$RETRY_INTERVAL"
            fi
        done
    fi

    if [[ -n "${INSTANCE_ID:-}" && "$INSTANCE_ID" != "null" ]]; then
        wait_for_resource "oci compute instance get" "--instance-id" "$INSTANCE_ID" "RUNNING" 10
        
        PUBLIC_IP=$(oci compute instance list-vnics --instance-id "$INSTANCE_ID" --region "$REGION" \
            --query 'data[0]."public-ip"' --raw-output)
        log "  Instance READY. Public IP: $PUBLIC_IP"
        log "  SSH command: ssh -i ${SSH_PUBLIC_KEY_FILE%.pub} opc@$PUBLIC_IP"
        
        # Output summary for user
        echo "===================================================="
        echo "COMPUTE PROVISIONED SUCCESSFULLY"
        echo "Public IP: $PUBLIC_IP"
        echo "Login: ssh -i ${SSH_PUBLIC_KEY_FILE%.pub} ubuntu@$PUBLIC_IP"
        echo "===================================================="
    else
        log "FAILED: Could not provision compute instance."
    fi
}

main() {
    log "Starting OCI Provisioning Process..."
    check_prereqs
    discover_resources
    provision_database
    provision_compute
    log "=== Provisioning Complete ==="
    log "Check the log file for details: $LOG_FILE"
}

main "$@"

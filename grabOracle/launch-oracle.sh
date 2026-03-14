#!/usr/bin/env bash
# Retry loop to launch Oracle Cloud A1 instance (free tier)
# Tries us-phoenix-1 first, falls back to us-sanjose-1
# Retries on capacity errors, timeouts, and transient failures

set -euo pipefail

COMPARTMENT="ocid1.tenancy.oc1..aaaaaaaaawle4df6xwunmftvdix72dgcourorz3bd52xyejsjk3cmvo5goia"
SSH_KEY_FILE="$HOME/.ssh/id_ed25519.pub"
SHAPE="VM.Standard.A1.Flex"
DISPLAY_NAME="rhj-core-01"
RETRY_INTERVAL=60

# San Jose — known working config (fallback)
SJ_AD="pEiw:US-SANJOSE-1-AD-1"
SJ_SUBNET="ocid1.subnet.oc1.us-sanjose-1.aaaaaaaad5qf7matk4p32qll2rvmbztgdnffbjeoalkdl32e25nzf462gvuq"
SJ_IMAGE="ocid1.image.oc1.us-sanjose-1.aaaaaaaamlydq2va6jhpvilgioaidj6nh2mt23kzuma5cuf7l3w5jb27v3aq"

# Phoenix — discovered at startup
PHX_AD=""
PHX_SUBNET=""
PHX_IMAGE=""
PHX_READY=false

echo "=== Launching $DISPLAY_NAME ==="
echo "Shape: $SHAPE (4 OCPU, 24 GB)"
echo "Primary: us-phoenix-1 | Fallback: us-sanjose-1"
echo "================================"
echo ""

# --- Discover Phoenix resources ---
echo "Discovering Phoenix resources..."
PHX_AD=$(oci iam availability-domain list \
  --compartment-id "$COMPARTMENT" --region "us-phoenix-1" \
  --query 'data[0].name' --raw-output 2>/dev/null) || true

if [[ -n "$PHX_AD" && "$PHX_AD" != "null" ]]; then
  echo "  AD: $PHX_AD"

  PHX_IMAGE=$(oci compute image list \
    --compartment-id "$COMPARTMENT" --region "us-phoenix-1" \
    --operating-system "Canonical Ubuntu" \
    --operating-system-version "22.04 Minimal aarch64" \
    --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
    --query 'data[0].id' --raw-output 2>/dev/null) || true
  echo "  Image: ${PHX_IMAGE:-(not found)}"

  PHX_SUBNET=$(oci network subnet list \
    --compartment-id "$COMPARTMENT" --region "us-phoenix-1" \
    --query 'data[0].id' --raw-output 2>/dev/null) || true
  echo "  Subnet: ${PHX_SUBNET:-(not found)}"

  if [[ -n "$PHX_IMAGE" && "$PHX_IMAGE" != "null" && \
        -n "$PHX_SUBNET" && "$PHX_SUBNET" != "null" ]]; then
    PHX_READY=true
    echo "  -> Phoenix READY"
  else
    echo "  -> Phoenix INCOMPLETE (missing image or subnet) — will skip"
  fi
else
  echo "  -> Could not reach Phoenix — will skip"
fi
echo ""

# --- Launch attempt function ---
try_launch() {
  local region=$1 ad=$2 subnet=$3 image=$4
  oci compute instance launch \
    --region "$region" \
    --availability-domain "$ad" \
    --compartment-id "$COMPARTMENT" \
    --shape "$SHAPE" \
    --shape-config '{"ocpus":4,"memoryInGBs":24}' \
    --subnet-id "$subnet" \
    --image-id "$image" \
    --display-name "$DISPLAY_NAME" \
    --assign-public-ip true \
    --ssh-authorized-keys-file "$SSH_KEY_FILE" \
    --boot-volume-size-in-gbs 100 \
    2>&1
}

is_retryable() {
  echo "$1" | grep -qi \
    "out of host capacity\|out of capacity\|InternalError\|too many requests\|timed out\|RequestException\|ConnectTimeout\|ReadTimeout\|connection.*reset\|connection.*refused"
}

handle_success() {
  local region=$1 result=$2
  echo ""
  echo "=== SUCCESS! Instance launched in $region ==="
  echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"

  INSTANCE_ID=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null) || true
  if [[ -n "$INSTANCE_ID" ]]; then
    echo "Instance ID: $INSTANCE_ID"
    echo "Waiting 30s for public IP..."
    sleep 30
    oci compute instance list-vnics --instance-id "$INSTANCE_ID" --region "$region" \
      --query 'data[0]."public-ip"' --raw-output 2>/dev/null || true
    echo ""
  fi
}

# --- Main retry loop ---
ATTEMPT=0
while true; do
  # Try Phoenix first
  if $PHX_READY; then
    ATTEMPT=$((ATTEMPT + 1))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attempt #$ATTEMPT — us-phoenix-1 / $PHX_AD"

    RESULT=$(try_launch "us-phoenix-1" "$PHX_AD" "$PHX_SUBNET" "$PHX_IMAGE") && {
      handle_success "us-phoenix-1" "$RESULT"
      exit 0
    }

    if is_retryable "$RESULT"; then
      echo "  -> Transient error (Phoenix). Trying San Jose..."
    else
      echo "  -> Error (Phoenix): $(echo "$RESULT" | head -3)"
    fi
  fi

  # Try San Jose (fallback)
  ATTEMPT=$((ATTEMPT + 1))
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attempt #$ATTEMPT — us-sanjose-1 / $SJ_AD"

  RESULT=$(try_launch "us-sanjose-1" "$SJ_AD" "$SJ_SUBNET" "$SJ_IMAGE") && {
    handle_success "us-sanjose-1" "$RESULT"
    exit 0
  }

  if is_retryable "$RESULT"; then
    echo "  -> Transient error (San Jose). Retrying both in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
  else
    echo ""
    echo "=== FAILED (non-retryable error) ==="
    echo "$RESULT"
    exit 1
  fi
done

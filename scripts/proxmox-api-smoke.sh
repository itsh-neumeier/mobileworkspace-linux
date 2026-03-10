#!/usr/bin/env sh
set -eu

: "${MWC_PROXMOX_API_URL:?Missing MWC_PROXMOX_API_URL}"
: "${MWC_PROXMOX_TOKEN_ID:?Missing MWC_PROXMOX_TOKEN_ID}"
: "${MWC_PROXMOX_TOKEN_SECRET:?Missing MWC_PROXMOX_TOKEN_SECRET}"
: "${MWC_PROXMOX_NODE:?Missing MWC_PROXMOX_NODE}"
: "${MWC_PROXMOX_TEMPLATE_VMID:?Missing MWC_PROXMOX_TEMPLATE_VMID}"

AUTH="Authorization: PVEAPIToken=${MWC_PROXMOX_TOKEN_ID}=${MWC_PROXMOX_TOKEN_SECRET}"
BASE="${MWC_PROXMOX_API_URL%/}/api2/json"

echo "Checking /cluster/nextid ..."
curl -fsS -H "${AUTH}" "${BASE}/cluster/nextid" >/dev/null
echo "OK"

echo "Checking template VM ${MWC_PROXMOX_TEMPLATE_VMID} on node ${MWC_PROXMOX_NODE} ..."
curl -fsS -H "${AUTH}" "${BASE}/nodes/${MWC_PROXMOX_NODE}/qemu/${MWC_PROXMOX_TEMPLATE_VMID}/status/current" >/dev/null
echo "OK"

echo "Proxmox API smoke test passed."

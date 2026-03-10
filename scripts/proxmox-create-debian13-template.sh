#!/usr/bin/env sh
set -eu

# Create a Debian 13 cloud-init template VM on a Proxmox host.
# Run this script directly on the Proxmox node as root.
#
# Example:
#   sh scripts/proxmox-create-debian13-template.sh \
#     --vmid 9000 \
#     --name debian13-desktop-base \
#     --storage local-lvm \
#     --ci-storage local-lvm \
#     --bridge vmbr0 \
#     --cores 2 \
#     --memory 4096 \
#     --ci-user admin

VMID=9000
NAME="debian13-cloud-template"
STORAGE="local-lvm"
CI_STORAGE=""
BRIDGE="vmbr0"
CORES=2
MEMORY=4096
DISK_GB=32
IMAGE_URL="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"
CI_USER="admin"
CI_PASSWORD=""
SSH_KEY_FILE=""
IPCONFIG0="ip=dhcp"
FORCE=0

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --vmid <id>               Template VMID (default: ${VMID})
  --name <name>             VM name (default: ${NAME})
  --storage <id>            Target disk storage for VM disk (default: ${STORAGE})
  --ci-storage <id>         Storage for cloud-init drive (default: same as --storage)
  --bridge <name>           Network bridge (default: ${BRIDGE})
  --cores <n>               vCPU cores (default: ${CORES})
  --memory <mb>             RAM in MB (default: ${MEMORY})
  --disk-gb <gb>            Resize imported disk to GB (default: ${DISK_GB})
  --image-url <url>         Debian 13 cloud image URL
  --ci-user <name>          cloud-init user (default: ${CI_USER})
  --ci-password <password>  cloud-init password (optional)
  --ssh-key-file <path>     Inject SSH public key file (optional)
  --ipconfig0 <value>       cloud-init ipconfig0 (default: ${IPCONFIG0})
  --force                   Destroy existing VMID if present
  -h, --help                Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vmid) VMID="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --storage) STORAGE="$2"; shift 2 ;;
    --ci-storage) CI_STORAGE="$2"; shift 2 ;;
    --bridge) BRIDGE="$2"; shift 2 ;;
    --cores) CORES="$2"; shift 2 ;;
    --memory) MEMORY="$2"; shift 2 ;;
    --disk-gb) DISK_GB="$2"; shift 2 ;;
    --image-url) IMAGE_URL="$2"; shift 2 ;;
    --ci-user) CI_USER="$2"; shift 2 ;;
    --ci-password) CI_PASSWORD="$2"; shift 2 ;;
    --ssh-key-file) SSH_KEY_FILE="$2"; shift 2 ;;
    --ipconfig0) IPCONFIG0="$2"; shift 2 ;;
    --force) FORCE=1; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [ -z "${CI_STORAGE}" ]; then
  CI_STORAGE="${STORAGE}"
fi

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd qm
need_cmd pvesm
need_cmd awk
need_cmd sed
need_cmd grep
need_cmd mktemp

if command -v wget >/dev/null 2>&1; then
  FETCH_CMD="wget"
elif command -v curl >/dev/null 2>&1; then
  FETCH_CMD="curl"
else
  echo "Need wget or curl to download cloud image." >&2
  exit 1
fi

if qm status "${VMID}" >/dev/null 2>&1; then
  if [ "${FORCE}" -eq 1 ]; then
    echo "VMID ${VMID} exists, removing because --force was set..."
    qm stop "${VMID}" >/dev/null 2>&1 || true
    qm destroy "${VMID}" --destroy-unreferenced-disks 1 --purge 1
  else
    echo "VMID ${VMID} already exists. Use --force to replace it." >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT INT TERM

IMG_PATH="${TMP_DIR}/debian13-cloud.qcow2"

echo "Downloading Debian 13 cloud image..."
if [ "${FETCH_CMD}" = "wget" ]; then
  wget -O "${IMG_PATH}" "${IMAGE_URL}"
else
  curl -fL -o "${IMG_PATH}" "${IMAGE_URL}"
fi

echo "Creating VM ${VMID} (${NAME})..."
qm create "${VMID}" \
  --name "${NAME}" \
  --memory "${MEMORY}" \
  --cores "${CORES}" \
  --net0 "virtio,bridge=${BRIDGE}" \
  --agent 1 \
  --ostype l26 \
  --scsihw virtio-scsi-pci \
  --serial0 socket \
  --vga serial0

echo "Importing disk to storage ${STORAGE}..."
qm importdisk "${VMID}" "${IMG_PATH}" "${STORAGE}"

DISK_REF="$(qm config "${VMID}" | awk -F': ' '/^unused[0-9]+: /{print $2; exit}' | sed 's/,.*$//')"
if [ -z "${DISK_REF}" ]; then
  echo "Failed to detect imported disk reference." >&2
  exit 1
fi

qm set "${VMID}" --scsi0 "${DISK_REF}"
qm set "${VMID}" --boot "order=scsi0"
qm resize "${VMID}" scsi0 "${DISK_GB}G"

echo "Configuring cloud-init drive on ${CI_STORAGE}..."
qm set "${VMID}" --ide2 "${CI_STORAGE}:cloudinit"
qm set "${VMID}" --ciuser "${CI_USER}"
qm set "${VMID}" --ipconfig0 "${IPCONFIG0}"

if [ -n "${CI_PASSWORD}" ]; then
  qm set "${VMID}" --cipassword "${CI_PASSWORD}"
fi

if [ -n "${SSH_KEY_FILE}" ]; then
  if [ ! -f "${SSH_KEY_FILE}" ]; then
    echo "SSH key file not found: ${SSH_KEY_FILE}" >&2
    exit 1
  fi
  qm set "${VMID}" --sshkeys "${SSH_KEY_FILE}"
fi

echo "Converting VM ${VMID} to template..."
qm template "${VMID}"

echo "Done."
echo "Template created:"
echo "  VMID: ${VMID}"
echo "  Name: ${NAME}"
echo "Use this VMID in MobileWorkspace Admin UI -> Proxmox Backend Settings -> Template VMID."

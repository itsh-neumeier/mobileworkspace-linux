#!/usr/bin/env sh
set -eu

# Create a Debian 13 cloud-init template VM on a Proxmox host.
# Run this script directly on the Proxmox node as root.
#
# Guided mode:
#   sh scripts/proxmox-create-debian13-template.sh --tui
#
# Non-interactive example:
#   sh scripts/proxmox-create-debian13-template.sh \
#     --vmid 9000 \
#     --name debian13-cloud-template \
#     --storage local-lvm \
#     --bridge vmbr0 \
#     --cores 2 \
#     --memory 4096 \
#     --disk-gb 32 \
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
DESKTOP_PROFILE="xfce"  # xfce|none
LOCALE="de_DE.UTF-8"
KEYBOARD_LAYOUT="de"
KEYBOARD_VARIANT=""
FORCE=0
TUI_MODE="auto"  # auto|on|off
EXPLICIT_ARGS=0

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --tui                    Start guided TUI wizard
  --no-tui                 Disable wizard mode
  --vmid <id>              Template VMID (default: ${VMID})
  --name <name>            VM name (default: ${NAME})
  --storage <id>           Target disk storage for VM disk (default: ${STORAGE})
  --ci-storage <id>        Storage for cloud-init drive (default: same as --storage)
  --bridge <name>          Network bridge (default: ${BRIDGE})
  --cores <n>              vCPU cores (default: ${CORES})
  --memory <mb>            RAM in MB (default: ${MEMORY})
  --disk-gb <gb>           Resize imported disk to GB (default: ${DISK_GB})
  --image-url <url>        Debian 13 cloud image URL
  --ci-user <name>         cloud-init user (default: ${CI_USER})
  --ci-password <password> cloud-init password (optional)
  --ssh-key-file <path>    Inject SSH public key file (optional)
  --ipconfig0 <value>      cloud-init ipconfig0 (default: ${IPCONFIG0})
  --desktop-profile <id>   Desktop profile: xfce or none (default: ${DESKTOP_PROFILE})
  --locale <locale>        System locale (default: ${LOCALE})
  --keyboard-layout <id>   Keyboard layout (default: ${KEYBOARD_LAYOUT})
  --keyboard-variant <id>  Keyboard variant (optional)
  --force                  Destroy existing VMID if present
  -h, --help               Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tui) TUI_MODE="on"; shift 1 ;;
    --no-tui) TUI_MODE="off"; shift 1 ;;
    --vmid) VMID="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --name) NAME="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --storage) STORAGE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --ci-storage) CI_STORAGE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --bridge) BRIDGE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --cores) CORES="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --memory) MEMORY="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --disk-gb) DISK_GB="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --image-url) IMAGE_URL="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --ci-user) CI_USER="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --ci-password) CI_PASSWORD="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --ssh-key-file) SSH_KEY_FILE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --ipconfig0) IPCONFIG0="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --desktop-profile) DESKTOP_PROFILE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --locale) LOCALE="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --keyboard-layout) KEYBOARD_LAYOUT="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --keyboard-variant) KEYBOARD_VARIANT="$2"; EXPLICIT_ARGS=1; shift 2 ;;
    --force) FORCE=1; EXPLICIT_ARGS=1; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

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

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root on the Proxmox host." >&2
  exit 1
fi

UI_BACKEND="plain"
if [ -t 0 ] && [ -t 1 ]; then
  if command -v whiptail >/dev/null 2>&1; then
    UI_BACKEND="whiptail"
  elif command -v dialog >/dev/null 2>&1; then
    UI_BACKEND="dialog"
  fi
fi

ui_input() {
  prompt="$1"
  default="$2"
  case "$UI_BACKEND" in
    whiptail)
      result="$(whiptail --title "Debian 13 Template Wizard" --inputbox "$prompt" 10 78 "$default" 3>&1 1>&2 2>&3)" || exit 1
      ;;
    dialog)
      result="$(dialog --stdout --title "Debian 13 Template Wizard" --inputbox "$prompt" 10 78 "$default")" || exit 1
      ;;
    *)
      printf "%s [%s]: " "$prompt" "$default"
      read -r result
      ;;
  esac
  if [ -z "$result" ]; then
    result="$default"
  fi
  printf "%s" "$result"
}

ui_password() {
  prompt="$1"
  case "$UI_BACKEND" in
    whiptail)
      result="$(whiptail --title "Debian 13 Template Wizard" --passwordbox "$prompt" 10 78 3>&1 1>&2 2>&3)" || exit 1
      ;;
    dialog)
      result="$(dialog --stdout --title "Debian 13 Template Wizard" --passwordbox "$prompt" 10 78)" || exit 1
      ;;
    *)
      printf "%s (leave empty to skip): " "$prompt"
      stty -echo
      read -r result
      stty echo
      printf "\n"
      ;;
  esac
  printf "%s" "$result"
}

ui_confirm() {
  prompt="$1"
  case "$UI_BACKEND" in
    whiptail)
      whiptail --title "Debian 13 Template Wizard" --yesno "$prompt" 10 78
      return $?
      ;;
    dialog)
      dialog --stdout --title "Debian 13 Template Wizard" --yesno "$prompt" 10 78
      return $?
      ;;
    *)
      printf "%s [y/N]: " "$prompt"
      read -r ans
      case "${ans:-n}" in
        y|Y|yes|YES) return 0 ;;
        *) return 1 ;;
      esac
      ;;
  esac
}

run_wizard() {
  VMID="$(ui_input "Template VMID" "$VMID")"
  NAME="$(ui_input "Template VM name" "$NAME")"
  STORAGE="$(ui_input "Target storage (disk import)" "$STORAGE")"
  CI_STORAGE="$(ui_input "Cloud-init storage (empty = same as target storage)" "$CI_STORAGE")"
  BRIDGE="$(ui_input "Network bridge" "$BRIDGE")"
  CORES="$(ui_input "vCPU cores" "$CORES")"
  MEMORY="$(ui_input "Memory in MB" "$MEMORY")"
  DISK_GB="$(ui_input "Disk size in GB after resize" "$DISK_GB")"
  IMAGE_URL="$(ui_input "Debian 13 image URL" "$IMAGE_URL")"
  CI_USER="$(ui_input "Cloud-init user" "$CI_USER")"
  CI_PASSWORD="$(ui_password "Cloud-init password")"
  SSH_KEY_FILE="$(ui_input "SSH public key file path (optional)" "$SSH_KEY_FILE")"
  IPCONFIG0="$(ui_input "Cloud-init ipconfig0" "$IPCONFIG0")"
  DESKTOP_PROFILE="$(ui_input "Desktop profile (xfce/none)" "$DESKTOP_PROFILE")"
  LOCALE="$(ui_input "System locale" "$LOCALE")"
  KEYBOARD_LAYOUT="$(ui_input "Keyboard layout" "$KEYBOARD_LAYOUT")"
  KEYBOARD_VARIANT="$(ui_input "Keyboard variant (optional)" "$KEYBOARD_VARIANT")"

  if ui_confirm "Replace an existing VM with same VMID if present?"; then
    FORCE=1
  else
    FORCE=0
  fi
}

if [ "$TUI_MODE" = "on" ] || { [ "$TUI_MODE" = "auto" ] && [ "$EXPLICIT_ARGS" -eq 0 ] && [ -t 0 ] && [ -t 1 ]; }; then
  run_wizard
fi

if [ -z "${CI_STORAGE}" ]; then
  CI_STORAGE="${STORAGE}"
fi

case "${DESKTOP_PROFILE}" in
  xfce|none)
    ;;
  *)
    echo "Unsupported --desktop-profile '${DESKTOP_PROFILE}'. Allowed: xfce, none." >&2
    exit 1
    ;;
esac

if qm status "${VMID}" >/dev/null 2>&1; then
  if [ "${FORCE}" -eq 1 ]; then
    echo "VMID ${VMID} exists, removing because force was enabled..."
    qm stop "${VMID}" >/dev/null 2>&1 || true
    qm destroy "${VMID}" --destroy-unreferenced-disks 1 --purge 1
  else
    echo "VMID ${VMID} already exists. Use --force or --tui and enable replace mode." >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT INT TERM

IMG_PATH="${TMP_DIR}/debian13-cloud.qcow2"

ensure_virt_customize() {
  if command -v virt-customize >/dev/null 2>&1; then
    return 0
  fi
  echo "virt-customize not found. Installing libguestfs-tools..."
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y libguestfs-tools
  if ! command -v virt-customize >/dev/null 2>&1; then
    echo "virt-customize is still missing after install. Aborting." >&2
    exit 1
  fi
}

customize_image_for_desktop() {
  ensure_virt_customize
  echo "Applying locale (${LOCALE}) and keyboard (${KEYBOARD_LAYOUT}) defaults..."
  virt-customize -a "${IMG_PATH}" \
    --run-command "export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get install -y --no-install-recommends locales keyboard-configuration console-setup; apt-get clean; rm -rf /var/lib/apt/lists/*" \
    --run-command "if ! grep -q '^${LOCALE} UTF-8' /etc/locale.gen; then echo '${LOCALE} UTF-8' >> /etc/locale.gen; fi; locale-gen '${LOCALE}'; update-locale LANG='${LOCALE}' LC_ALL='${LOCALE}'" \
    --run-command "printf 'XKBMODEL=\"pc105\"\\nXKBLAYOUT=\"${KEYBOARD_LAYOUT}\"\\nXKBVARIANT=\"${KEYBOARD_VARIANT}\"\\nXKBOPTIONS=\"\"\\nBACKSPACE=\"guess\"\\n' > /etc/default/keyboard" \
    --run-command "printf 'LANG=${LOCALE}\\nLC_ALL=${LOCALE}\\n' > /etc/default/locale"

  if [ "${DESKTOP_PROFILE}" = "none" ]; then
    echo "Desktop profile disabled (none). Continuing with headless cloud image."
    return 0
  fi
  echo "Customizing image with desktop profile '${DESKTOP_PROFILE}' (this can take several minutes)..."
  virt-customize -a "${IMG_PATH}" \
    --run-command "printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d; chmod +x /usr/sbin/policy-rc.d" \
    --run-command "export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get install -y --no-install-recommends xfce4 xfce4-goodies lightdm lightdm-gtk-greeter xorg dbus-x11 xrdp xorgxrdp xserver-xorg-video-qxl; apt-get clean; rm -rf /var/lib/apt/lists/*" \
    --run-command "rm -f /usr/sbin/policy-rc.d" \
    --run-command "mkdir -p /etc/systemd/system/graphical.target.wants /etc/systemd/system/multi-user.target.wants /etc/skel" \
    --run-command "ln -sf /lib/systemd/system/graphical.target /etc/systemd/system/default.target" \
    --run-command "ln -sf /lib/systemd/system/lightdm.service /etc/systemd/system/graphical.target.wants/lightdm.service" \
    --run-command "ln -sf /lib/systemd/system/lightdm.service /etc/systemd/system/display-manager.service" \
    --run-command "printf '/usr/sbin/lightdm\n' > /etc/X11/default-display-manager" \
    --run-command "mkdir -p /etc/lightdm/lightdm.conf.d; printf '[Seat:*]\nuser-session=xfce\ngreeter-session=lightdm-gtk-greeter\n' > /etc/lightdm/lightdm.conf.d/50-mwc-xfce.conf" \
    --run-command "ln -sf /dev/null /etc/systemd/system/getty@tty1.service" \
    --run-command "printf '#!/bin/sh\nset -eu\nPRIMARY_USER=\"$(awk -F: '\''$3 >= 1000 && $3 < 65000 && $1 != \"nobody\" { print $1; exit }'\'' /etc/passwd || true)\"\nif command -v apt-get >/dev/null 2>&1; then export DEBIAN_FRONTEND=noninteractive; apt-get update || true; apt-get install -y sudo || true; fi\nif [ -n \"$PRIMARY_USER\" ]; then usermod -aG sudo \"$PRIMARY_USER\" || true; printf \"%s ALL=(ALL) NOPASSWD:ALL\\n\" \"$PRIMARY_USER\" > /etc/sudoers.d/90-mwc-primary || true; chmod 440 /etc/sudoers.d/90-mwc-primary || true; mkdir -p /etc/lightdm/lightdm.conf.d; printf \"[Seat:*]\\nuser-session=xfce\\ngreeter-session=lightdm-gtk-greeter\\nautologin-user=%s\\nautologin-user-timeout=0\\n\" \"$PRIMARY_USER\" > /etc/lightdm/lightdm.conf.d/51-mwc-autologin.conf || true; fi\nsystemctl set-default graphical.target || true\nsystemctl enable lightdm.service || true\nsystemctl restart lightdm.service || true\nsystemctl disable mwc-firstboot-desktop.service || true\n' > /usr/local/sbin/mwc-firstboot-desktop.sh; chmod +x /usr/local/sbin/mwc-firstboot-desktop.sh" \
    --run-command "printf '[Unit]\nDescription=Ensure desktop stack starts on first boot\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=oneshot\nExecStart=/usr/local/sbin/mwc-firstboot-desktop.sh\nRemainAfterExit=no\n\n[Install]\nWantedBy=multi-user.target\n' > /etc/systemd/system/mwc-firstboot-desktop.service" \
    --run-command "ln -sf /etc/systemd/system/mwc-firstboot-desktop.service /etc/systemd/system/multi-user.target.wants/mwc-firstboot-desktop.service" \
    --run-command "ln -sf /lib/systemd/system/xrdp.service /etc/systemd/system/multi-user.target.wants/xrdp.service" \
    --run-command "echo xfce4-session > /etc/skel/.xsession"
}

echo "Downloading Debian 13 cloud image..."
if [ "${FETCH_CMD}" = "wget" ]; then
  wget -O "${IMG_PATH}" "${IMAGE_URL}"
else
  curl -fL -o "${IMG_PATH}" "${IMAGE_URL}"
fi

customize_image_for_desktop

echo "Creating VM ${VMID} (${NAME})..."
qm create "${VMID}" \
  --name "${NAME}" \
  --memory "${MEMORY}" \
  --cores "${CORES}" \
  --net0 "virtio,bridge=${BRIDGE}" \
  --agent 1 \
  --ostype l26 \
  --scsihw virtio-scsi-pci

if [ "${DESKTOP_PROFILE}" = "none" ]; then
  qm set "${VMID}" --serial0 socket --vga serial0
else
  qm set "${VMID}" --vga qxl
fi

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
echo "  Desktop profile: ${DESKTOP_PROFILE}"
echo "Use this VMID in MobileWorkspace Admin UI -> Proxmox Backend Settings -> Template VMID."

# Proxmox Deployment Guide

This project is intended to run well on Proxmox, but the recommended deployment target is a dedicated Linux VM, not an LXC container.

## Recommended Option: Proxmox VM

Use a small Debian or Ubuntu VM in Proxmox and run Docker inside that VM.

Reasons:

- Better compatibility with Docker networking
- Fewer privilege edge cases than Docker inside LXC
- Easier upgrades, backups, and rollback
- Better isolation for multi-user admin workloads
- More predictable behavior for WebVNC desktop containers
- Cleaner operation for a web-based admin panel that provisions containers dynamically

## Suggested VM Sizing

Minimum for terminal-only usage:

- 2 vCPU
- 4 GB RAM
- 30 GB disk

Recommended when using WebVNC desktops:

- 4 vCPU
- 8 GB RAM
- 60 GB disk

Increase RAM if several desktop users will be active at the same time.

## Base VM Setup

1. Create a Debian 12 or Ubuntu 24.04 VM in Proxmox.
2. Enable the QEMU guest agent.
3. Assign a static IP or a DHCP reservation.
4. Install Docker Engine and Docker Compose plugin.
5. Clone this repository into the VM.
6. Copy `.env.example` to `.env` and configure the admin credentials.
7. Start the stack with `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d`.
8. Open `/admin/` and create user workspaces from the web UI.

If you prefer Portainer, use `docker-compose.portainer.yml` in the stack editor instead of the repo-oriented Compose file. That variant is designed to avoid relative file mounts and uses nginx as the internal reverse proxy.

If you want to pin a specific published image version:

```bash
ADMIN_UI_IMAGE_TAG=0.3.0 docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

## Networking in Proxmox

Typical setup:

- Proxmox bridge: `vmbr0`
- VM NIC attached to `vmbr0`
- nginx exposed on port `80`
- Optional TLS reverse proxy or firewall rules in front

For internet-exposed access:

- Forward ports from your router or firewall to the VM
- Prefer HTTPS with a public DNS name
- Restrict source IPs where possible

For internal-only access:

- Do not publish the service externally
- Route access through VPN, Tailscale, WireGuard, or a jump network

## Storage

Persisted user data is stored under:

- `/path/to/repo/users/users.json`
- `/path/to/repo/generated/docker-compose.users.yml`
- `/path/to/repo/generated/nginx.users.conf`

For the Portainer-compatible stack, state lives primarily in Docker named volumes instead of repo-relative paths.

In Proxmox, you can protect these with:

- VM snapshots
- scheduled backups
- ZFS-backed storage if available

## LXC Option

Running Docker inside a Proxmox LXC container is possible, but it is not the default recommendation.

You will usually need:

- nesting enabled
- keyctl enabled
- a sufficiently permissive AppArmor profile
- cgroup and mount compatibility for Docker

Typical downsides:

- more troubleshooting around Docker networking
- more breakage risk after host or kernel updates
- more friction with WebVNC desktop containers

If you want the simplest stable path, use a VM.

## Proxmox Operations

Recommended maintenance practices:

- snapshot before upgrades
- back up the VM regularly
- pin or deliberately update container image tags
- keep `.env` out of Git
- monitor RAM usage if running multiple desktop sessions
- restrict access to the admin UI because it controls the Docker socket

## Native Proxmox VM Provisioning Mode

Mobile Web Console Hub can also create and manage desktop workspaces as real Proxmox VMs through the Proxmox API.

Enable `Proxmox VM` as provisioner mode in the Admin UI settings panel.

Notes:

- Configure Proxmox API URL, node, token, template VMID, and TLS behavior in the admin UI backend settings panel.
- You can create a Debian 13 cloud-init template on the Proxmox host with:
  - `sh scripts/proxmox-create-debian13-template.sh --vmid 9000 --name debian13-cloud-template`
  - `curl -fsSL https://raw.githubusercontent.com/itsh-neumeier/mobileworkspace-linux/main/scripts/proxmox-create-debian13-template.sh | sh -s -- --vmid 9000 --name debian13-cloud-template`
- In this mode, desktop workspaces are created as Proxmox VMs (clone + config + optional start).
- User actions in the web UI map to Proxmox VM actions:
  - enable -> start
  - disable -> stop
  - redeploy -> stop/start
  - delete -> stop/delete
- The admin UI includes a `Test Proxmox API` action for live validation.

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
6. Copy `.env.example` to `.env` and configure credentials.
7. Start the stack with `docker compose up -d`.

## Networking in Proxmox

Typical setup:

- Proxmox bridge: `vmbr0`
- VM NIC attached to `vmbr0`
- Caddy exposed on port `80`
- Optional TLS reverse proxy or firewall rules in front

For internet-exposed access:

- Forward ports from your router or firewall to the VM
- Prefer HTTPS with a public DNS name
- Restrict source IPs where possible

For internal-only access:

- Do not publish the service externally
- Route access through VPN, Tailscale, WireGuard, or a jump network

## Storage

Persisted user data is stored in:

- `/path/to/repo/data/public`
- `/path/to/repo/data/internal`
- `/path/to/repo/data/desktop-public`
- `/path/to/repo/data/desktop-internal`

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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.6.16] - 2026-03-10

### Changed
- Client interface promoted to dedicated `/client/*` portal routes with normal login/logout and password change flow
- Workspace creation now uses **Workspace Name** as source of truth for URL route generation (separate Route field removed to avoid confusion)
- Workspace cards now display workspace name primarily and use current computed public URL for links

### Fixed
- Embedded nginx now proxies `/client/*` paths to the Flask app

## [0.6.15] - 2026-03-10

### Added
- Admin navigation split into dedicated submenus/pages:
  - `/admin/` dashboard overview
  - `/admin/workspaces/` workspace provisioning and operations
  - `/admin/users/` user overview and password reset across assigned workspaces
  - `/admin/proxmox/` Proxmox backend settings
- Proxmox workspace insights in workspace cards:
  - current VM CPU/RAM stats
  - recent Proxmox task status snippets

### Changed
- Workspace drift detection now marks stale resources as `corrupt` in UI (for missing Proxmox VMs and missing Docker containers)
- Dashboard/user pages trigger automatic reconcile so deleted VMs are visible as broken state instead of silently stale

## [0.6.14] - 2026-03-10

### Fixed
- Proxmox VM delete now handles already-missing VMs gracefully (HTTP 404 no longer blocks workspace cleanup)
- Proxmox API request builder no longer sends form content headers on payload-less requests (prevents DELETE method errors)

### Added
- Automatic workspace reconciliation on dashboard load:
  - Proxmox VM existence/status sync
  - Docker container existence sync
  - user-facing sync note when drift is detected

## [0.6.13] - 2026-03-10

### Fixed
- Proxmox template desktop customization now uses safer noninteractive install settings (`policy-rc.d`, `--no-install-recommends`) to reduce hangs during `virt-customize`
- Added explicit README examples for custom `--storage` / `--ci-storage` usage and guidance about expected `virt-customize` warnings

## [0.6.12] - 2026-03-10

### Fixed
- GHCR publish flow now builds SemVer image tags from `main` using the `VERSION` file (reliable container publish even when tag-login workflows are restricted)

## [0.6.11] - 2026-03-10

### Added
- New user area (`/user/login/`, `/user/`) so workspace users can sign in via WebUI and open their own workspaces
- Dedicated Proxmox settings page (`/admin/proxmox/`) with grouped backend configuration and live node utilization cards (CPU/RAM/Disk)
- Proxmox template script desktop profile support (`--desktop-profile xfce|none`) with XFCE/LightDM/XRDP image customization

### Changed
- GHCR image naming switched to `ghcr.io/itsh-neumeier/mwc`
- Workspace links in admin/user UI now open in a new tab
- Proxmox workspace URLs now target tunneled `/pve/` path through Mobile Workspace

### Removed
- nginx basic-auth workspace gate; replaced with session-based WebUI auth (`/user/auth/<route>/`)

## [0.6.9] - 2026-03-10

### Added
- Configurable Proxmox VMID range (`VMID Min` / `VMID Max`) in Admin UI settings

### Fixed
- Proxmox clone flow now waits for async clone task completion before applying VM config/start
- Added lock-timeout retries for Proxmox VM config/start/stop/delete actions

## [0.6.8] - 2026-03-10

### Added
- Guided TUI wizard mode (`--tui`) for `proxmox-create-debian13-template.sh` with `whiptail/dialog` and plain prompt fallback

### Changed
- Proxmox template script now supports both interactive and non-interactive creation workflows

## [0.6.7] - 2026-03-10

### Added
- Proxmox cloud-init guest user/password fields per workspace in the Admin UI
- Proxmox clone provisioning now sends cloud-init user/password and DHCP config to guest VMs
- README and Proxmox docs now include direct GitHub `curl | sh` command template for template VM creation

## [0.6.6] - 2026-03-10

### Added
- New Proxmox host script `scripts/proxmox-create-debian13-template.sh` to create a Debian 13 cloud-init template VM automatically

## [0.6.5] - 2026-03-10

### Fixed
- Stabilized admin bootstrap repair logic to avoid repeated manual initial credential resets after first deploy
- Fixed workspace URL rendering to use the active request host/scheme and avoid malformed `http://:` links

### Changed
- Proxmox backend configuration is now always visible and editable in the Admin UI (including provisioner mode)
- Proxmox mode selection now persists in UI settings storage

## [0.6.4] - 2026-03-10

### Changed
- Moved Proxmox backend configuration from environment variables to persisted Admin UI settings
- Added Proxmox settings form in the dashboard (API URL, node, token, template VMID, TLS verify)

### Removed
- Proxmox backend env configuration requirements from docs and compose examples

## [0.6.3] - 2026-03-10

### Fixed
- Added admin bootstrap auto-repair for invalid/corrupted password-hash files to avoid repeated manual `admin/admin` resets

### Added
- New `ADMIN_AUTO_REPAIR` environment switch (default `true`)

## [0.6.2] - 2026-03-10

### Fixed
- In `proxmox_vm` mode, generated nginx/docker files are now auto-cleared to avoid restart loops from stale Docker workspace upstreams

## [0.6.1] - 2026-03-10

### Added
- Proxmox API end-to-end self-test action in the admin UI
- Per-user Proxmox VM overrides in workspace creation (vCPU, RAM, bridge, disk, start-on-create)
- Manual Proxmox API smoke test script at `scripts/proxmox-api-smoke.sh`

### Changed
- Exposed `MWC_PROXMOX_DESKTOP_URL_TEMPLATE` in environment examples and Compose files

## [0.6.0] - 2026-03-10

### Added
- Optional `proxmox_vm` provisioner mode to create desktop workspaces as Proxmox VMs via API (clone/config/start)
- Proxmox VM lifecycle actions from the admin UI (start/stop/restart/delete)
- New Proxmox environment variables in Compose and `.env.example`

### Changed
- Workspace cards now display Proxmox VM details and access URL when a user is provisioned as `proxmox_vm`

## [0.5.13] - 2026-03-10

### Fixed
- Changed generated workspace nginx routes to use runtime-resolved upstream variables, preventing container restart loops when a workspace container is temporarily not resolvable

## [0.5.12] - 2026-03-10

### Fixed
- Added startup readiness check so nginx starts only after Gunicorn responds, preventing intermittent `/admin/` smoke-test failures

## [0.5.11] - 2026-03-10

### Changed
- Updated footer branding to `ITSH Neumeier` with `neumeier.cloud` and GitHub links
- Applied consistent footer metadata to login, password-change, and admin dashboard pages

## [0.5.10] - 2026-03-10

### Changed
- Merged internal nginx reverse proxy into the `admin-ui` image so deployment runs as a single container
- Simplified standard and Portainer Compose files by removing the separate `nginx` service
- Updated CI override to expose port `18080` directly from `admin-ui` for smoke tests

## [0.5.9] - 2026-03-10

### Added
- Configurable initial admin password (`ADMIN_INITIAL_PASSWORD`, default `admin`) for first bootstrap
- Mandatory admin password change flow after first login before dashboard access

## [0.5.8] - 2026-03-10

### Fixed
- Added explicit nginx redirects and `^~` route blocks for `/admin`, `/login`, and `/logout` to make admin login routing robust across trailing-slash variants

## [0.5.7] - 2026-03-10

### Fixed
- Added nginx proxy routes for `/login/` and `/logout/` so the admin UI redirect flow no longer falls back to nginx 404 pages

## [0.5.6] - 2026-03-10

### Added
- Automated container smoke test workflow for push, tag, and pull request events
- CI compose override file for reproducible stack startup checks in GitHub Actions

### Changed
- Release workflow now requires a successful container smoke run before creating a release

## [0.5.5] - 2026-03-10

### Fixed
- Escaped `$admin_upstream` in embedded nginx config so Portainer/Compose does not strip it before runtime
- Removed direct bcrypt usage in app code and pinned a compatible bcrypt version to avoid passlib backend warnings

## [0.5.4] - 2026-03-10

### Fixed
- Prevented Gunicorn worker boot failures by ensuring the session secret directory exists before writing
- Updated generated nginx user route blocks to use `Connection "upgrade"` without depending on a map variable

## [0.5.3] - 2026-03-10

### Fixed
- Switched nginx admin upstream handling to Docker DNS runtime resolution to avoid startup failures when the admin UI container is not yet resolvable

## [0.5.2] - 2026-03-10

### Fixed
- Removed the embedded nginx `map` directive from Compose-generated configs to avoid Portainer interpolation issues

## [0.5.1] - 2026-03-10

### Fixed
- Escaped nginx `$...` variables in embedded Compose configs so Portainer does not strip them before container startup

## [0.5.0] - 2026-03-10

### Added
- Built-in admin login flow in the web UI instead of proxy-level basic auth
- nginx-based internal reverse proxy for standard and Portainer deployments
- Optional guidance for placing Zoraxy in front of the stack for external publishing

### Changed
- Replaced internal Caddy routing with nginx route generation and htpasswd files
- Admin bootstrap credentials are now generated and handled by the admin application

## [0.4.3] - 2026-03-10

### Fixed
- Portainer first-run credential bootstrap now stores admin username and hash in separate files instead of a sourced shell env file
- Prevented Caddy bcrypt hashes from being corrupted by shell expansion during restart

## [0.4.2] - 2026-03-10

### Added
- Portainer first-run bootstrap that auto-generates admin credentials when no hash is configured
- Persistent storage of the generated admin hash and initial password in the Portainer state volume

### Changed
- Portainer examples now default to `DOMAIN_OR_HOST=:80` for HTTP-first local deployment

## [0.4.1] - 2026-03-10

### Changed
- Switched the admin UI container from the Flask development server to Gunicorn
- Fixed Portainer Caddy placeholder escaping and updated `basic_auth` syntax

## [0.4.0] - 2026-03-10

### Added
- Portainer-compatible stack file without host file bind mounts
- Named-volume based provisioning for user workspace data
- Portainer deployment documentation and environment guidance

### Changed
- User workspace provisioning now uses generated named Docker volumes instead of relative host paths
- Admin-generated user stacks now rely on external named networks and explicit Caddy reloads

## [0.3.1] - 2026-03-10

### Changed
- Redesigned the admin UI with a Bootstrap-based layout
- Added light and dark theme switching with header icons
- Added footer metadata with application name, version, GitHub link, and copyright

## [0.3.0] - 2026-03-10

### Added
- GitHub Actions workflow to publish the admin UI container image to GHCR
- `docker-compose.ghcr.yml` for deployments that pull the published admin UI image
- Configurable `ADMIN_UI_IMAGE_TAG` for pinning image versions

### Changed
- Updated deployment documentation to cover GHCR-based Compose usage on Proxmox

## [0.2.0] - 2026-03-10

### Added
- Browser-based admin panel for user management
- Web UI workflow to create per-user terminal or desktop workspaces
- Dynamic generation of Docker Compose services and Caddy routes
- User enable, disable, redeploy, and delete actions from the admin panel
- Docker-based admin service for self-provisioning on Proxmox VMs

### Changed
- Replaced the static example-user stack with a dynamic admin-managed provisioning model
- Updated English and German documentation for the new web-based workflow

## [0.1.0] - 2026-03-10

### Added
- Initial public project structure
- Multi-user Docker Compose stack with isolated web console environments
- Optional WebVNC desktop environments via LinuxServer Webtop
- Caddy reverse proxy for a single mobile-friendly entrypoint
- Sample user provisioning script
- English and German documentation
- Proxmox deployment guide with VM-first recommendation
- MIT license and GitHub release workflow

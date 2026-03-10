# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

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

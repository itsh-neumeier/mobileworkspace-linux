# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

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

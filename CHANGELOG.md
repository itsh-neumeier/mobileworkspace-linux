# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

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

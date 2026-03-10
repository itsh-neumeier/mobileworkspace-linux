# Mobile Web Console Hub

Mobile Web Console Hub is a self-hosted multi-user platform for Proxmox environments. It gives you a browser-based admin panel where you can create users and provision their own Linux workspaces as Docker containers.

Each workspace can be created as either:

- a terminal-focused Linux web console
- a full Linux desktop over WebVNC/noVNC

Each user environment can also be assigned to either:

- an internet-enabled network
- an internal-only Docker network

The project is designed for situations where you work from managed notebooks or mobile devices and still need a practical web UI for SSH, shell commands, light operations work, or a temporary Linux desktop.

## Features

- Admin web UI for user management
- User creation directly from the browser
- Automatic provisioning of per-user Docker containers
- Terminal workspaces with `code-server`
- Desktop workspaces with `webtop` over WebVNC
- Per-user route generation in nginx
- Public or internal-only network placement per workspace
- Persistent storage per user
- Proxmox-friendly VM deployment model
- MIT licensed
- Semantic versioning and GitHub release flow

## Architecture

- `nginx`: reverse proxy and entrypoint
- `admin-ui`: browser-based admin panel with built-in admin login and workspace provisioning
- `generated/docker-compose.users.yml`: generated service definitions for enabled users
- `generated/nginx.users.conf`: generated reverse proxy routes for enabled users
- `users/users.json`: local user registry created by the admin UI at runtime

The admin UI writes the generated files and then runs:

```bash
docker compose -f docker-compose.yml -f generated/docker-compose.users.yml up -d --remove-orphans
```

This means user containers are created, updated, disabled, or deleted directly from the browser.

## Quick Start

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`

3. Start the stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

4. Open the admin panel:

- `http://YOUR_HOST/admin/`

5. Sign in with the generated bootstrap admin credentials from the `admin-ui` container logs, then create users from the web UI.

## Compose Files

- `docker-compose.yml`: standard Docker Compose deployment from a checked-out repo
- `docker-compose.ghcr.yml`: explicit GHCR deployment variant
- `docker-compose.build.yml`: local build override for development
- `docker-compose.portainer.yml`: Portainer-compatible stack without local file bind mounts

For Proxmox or other server deployments, the GHCR variant is usually the better fit:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

To pin a specific version:

```bash
ADMIN_UI_IMAGE_TAG=0.3.0 docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

Published image path:

```text
ghcr.io/itsh-neumeier/mobileworkspace-linux/admin-ui
```

For local development builds instead of GHCR:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## Portainer Deployment

If you want to deploy this through the Portainer stack editor, use:

- `docker-compose.portainer.yml`

This variant avoids the local bind mounts that fail in Portainer when stack editor deployments expect repo files to exist on the Docker host.

Recommended Portainer environment variables:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`
- `ADMIN_UI_IMAGE_TAG`
- `MWC_EDGE_NETWORK`
- `MWC_PUBLIC_NETWORK`
- `MWC_INTERNAL_NETWORK`

Portainer stack behavior:

- nginx builds its base config inside the container at startup
- the admin UI generates a bootstrap admin account on first run and logs the initial password once
- user registry and generated config are stored in a named volume
- the admin UI provisions user containers through the Docker socket
- user workspaces use named Docker volumes instead of relative host paths

Recommended for first boot:

- `DOMAIN_OR_HOST=:80`
- `ADMIN_USER_NAME=admin`

After the first start, read the generated password from the `mobileworkspace-admin-ui` container logs in Portainer.

The admin panel will then create routes such as:

- `http://YOUR_HOST/workspaces/ops/`
- `http://YOUR_HOST/workspaces/internal-admin/`

## User Management in the Web UI

The admin panel supports:

- creating a user workspace
- choosing terminal or desktop mode
- choosing public or internal-only network placement
- enabling and disabling a workspace
- redeploying a workspace
- deleting a workspace and removing its generated container definition

Each created user gets:

- an isolated container
- a generated nginx route
- persistent Docker volumes for config and workspace data
- access protection through per-workspace nginx basic auth

For terminal workspaces, the same password is also used for the internal `code-server` login.

## Proxmox

This project is intended to run on Proxmox. The recommended deployment model is:

- Proxmox host
- one dedicated Debian or Ubuntu VM
- Docker and Docker Compose inside that VM

That model is more reliable than running Docker inside an LXC container, especially when you want dynamic user provisioning and desktop containers.

Detailed guidance: `docs/proxmox.md`

## Optional External Proxy

If you want to publish the service externally, you can place another reverse proxy such as Zoraxy in front of this stack.

Recommended setup:

- Mobile Web Console Hub runs internally on plain HTTP
- nginx inside this project handles `/admin/` and `/workspaces/...`
- Zoraxy optionally handles public DNS, TLS certificates, and internet exposure

## Default Network Model

- `edge`: network shared by nginx, admin UI, and user workspaces
- `public_net`: Docker bridge network with outbound internet access
- `internal_net`: Docker internal network without outbound internet access

The admin UI assigns each workspace to one of these network profiles during creation.

## Security Notes

- Put the service behind TLS before exposing it publicly
- The admin UI mounts the Docker socket and therefore has full control over the Docker host
- Replace basic auth with SSO or an identity-aware proxy if this will be used broadly
- Store sensitive values outside Git and restrict filesystem permissions on the VM
- Desktop workspaces need more CPU and RAM than terminal-only workspaces
- Review Docker images and mounted paths before production use

## Versioning and Releases

- Project version is stored in `VERSION`
- Update `CHANGELOG.md` for every release
- Use Semantic Versioning tags such as `v0.2.0`
- GitHub Actions creates a release artifact for pushed version tags
- GitHub Actions also publishes the admin UI image to GHCR

Example release flow:

```bash
git add .
git commit -m "release: v0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Documentation

- English: this file
- German: `README.de.md`
- Proxmox deployment: `docs/proxmox.md`
- Changes: `CHANGELOG.md`

## License

MIT. See `LICENSE`.

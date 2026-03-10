# Mobile Web Console Hub

Mobile Web Console Hub is a Docker-based self-hosted platform that provides browser-accessible Linux workspaces for multiple users. Each user gets an isolated environment with either a browser terminal or a full Linux desktop in the browser, persistent storage, and controlled network access for either internet-facing administration tasks or internal-network operations.

This project is designed for situations where you are working from managed devices without local admin rights and still need a practical, mobile-friendly web UI to run shell commands, SSH into infrastructure, or perform lightweight operational tasks.

## Features

- Web UI accessible from phones, tablets, and notebooks
- One isolated Linux environment per user
- Optional full Linux desktop through WebVNC/noVNC
- Persistent home directories
- Optional internet access or internal-only network access per environment
- Built-in terminal through `code-server`
- Reverse proxy with per-user entry paths
- MIT licensed
- Semantic versioning ready

## Architecture

- `caddy`: single HTTPS-ready entrypoint and reverse proxy
- `workspace-public`: example user environment with internet access
- `workspace-internal`: example user environment on internal-only network
- `desktop-public`: example internet-enabled Linux desktop via WebVNC
- `desktop-internal`: example internal-only Linux desktop via WebVNC
- `code-server`: provides a browser UI and integrated terminal for each user
- `webtop`: provides a full desktop session over the browser

`code-server` is used for terminal-first workspaces because it works well on mobile browsers and includes a terminal, file browser, and optional editor. `webtop` adds a complete Linux desktop over WebVNC/noVNC for users who need GUI tools or a more traditional desktop workflow.

## Quick Start

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Generate password hashes for Caddy basic auth:

```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext "replace-me"
```

3. Edit `.env` and set:

- `DOMAIN_OR_HOST`
- `PUBLIC_USER_PASSWORD_HASH`
- `INTERNAL_USER_PASSWORD_HASH`
- `PUBLIC_WORKSPACE_PASSWORD`
- `INTERNAL_WORKSPACE_PASSWORD`
- `PUBLIC_DESKTOP_USER_PASSWORD_HASH`
- `INTERNAL_DESKTOP_USER_PASSWORD_HASH`

4. Start the stack:

```bash
docker compose up -d
```

5. Open the service:

- `http://YOUR_HOST/public/`
- `http://YOUR_HOST/desktop-public/`
- `http://YOUR_HOST/internal/`
- `http://YOUR_HOST/desktop-internal/`

## Proxmox

This project is intended to run on Proxmox. The recommended deployment model is:

- Proxmox host
- one dedicated Debian or Ubuntu VM
- Docker and Docker Compose inside that VM

That approach is more reliable than running Docker inside an LXC container, especially for multi-user networking and WebVNC desktops.

Detailed guidance: `docs/proxmox.md`

## Default Network Model

- `edge`: exposed to the reverse proxy
- `public_net`: internet-enabled Docker bridge network
- `internal_net`: internal Docker network without outbound internet access

The included examples show two user profiles:

- `workspace-public`: can reach the internet
- `workspace-internal`: can only communicate on the internal Docker network unless you deliberately connect it elsewhere
- `desktop-public`: full browser desktop with internet access
- `desktop-internal`: full browser desktop on an internal-only network

## Add More Users

Use the helper script to scaffold a new user block:

```powershell
pwsh ./scripts/New-WorkspaceUser.ps1 -UserName ops -Route ops -Mode public
```

Desktop example:

```powershell
pwsh ./scripts/New-WorkspaceUser.ps1 -UserName ops-desktop -Route desktop-ops -Mode internal -WorkspaceType desktop
```

The script prints:

- a Docker Compose service snippet
- a Caddy route snippet
- the env variables you need to add to `.env`

## Security Notes

- Put this behind TLS before exposing it to the internet
- Replace basic auth with SSO or an identity-aware proxy if this will be used broadly
- Store secrets in a secure secret manager for production use
- Restrict SSH keys and outbound network reach per user role
- Review Docker bind mounts and never mount host-sensitive paths
- WebVNC desktops need more RAM and CPU than terminal-only workspaces

## Versioning and Releases

- Project version is stored in `VERSION`
- Update `CHANGELOG.md` for every release
- Create Git tags using Semantic Versioning, for example `v0.2.0`
- GitHub Actions will validate the tag and publish a release archive

Example release flow:

```bash
git add .
git commit -m "release: v0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Publish to GitHub

Create a public repository on GitHub and connect this folder:

```bash
git init
git branch -M main
git add .
git commit -m "feat: initial release"
git remote add origin https://github.com/YOUR-USER/YOUR-REPO.git
git push -u origin main
```

## Documentation

- English: this file
- German: `README.de.md`
- Proxmox deployment: `docs/proxmox.md`
- Changes: `CHANGELOG.md`

## License

MIT. See `LICENSE`.

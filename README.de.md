# Mobile Web Console Hub

Mobile Web Console Hub ist eine selbst gehostete Multi-User-Plattform für Proxmox-Umgebungen. Sie stellt eine browserbasierte Admin-WebUI bereit, über die Benutzer angelegt und ihre eigenen Linux-Arbeitsumgebungen als Docker-Container bereitgestellt werden können.

Jede Arbeitsumgebung kann erstellt werden als:

- terminalorientierte Linux-Webkonsole
- vollständiger Linux-Desktop über WebVNC/noVNC

Jede Benutzerumgebung kann außerdem in eines von zwei Netzprofilen gelegt werden:

- internetfähig
- nur internes Docker-Netz

Das Projekt ist für Situationen gedacht, in denen du mit verwalteten Notebooks oder mobil arbeitest und trotzdem eine praktikable Weboberfläche für SSH, Shell-Befehle, leichte Betriebsaufgaben oder einen temporären Linux-Desktop brauchst.

## Funktionen

- Admin-WebUI für Benutzerverwaltung
- Benutzeranlage direkt im Browser
- Automatische Bereitstellung der Container pro Benutzer
- Terminal-Workspaces mit `code-server`
- Desktop-Workspaces mit `webtop` über WebVNC
- Automatische Caddy-Routen pro Benutzer
- Internet- oder Internal-only-Netz pro Workspace
- Persistenter Speicher pro Benutzer
- Für Proxmox-VMs ausgelegt
- MIT-Lizenz
- Semantic Versioning und GitHub-Release-Flow

## Architektur

- `caddy`: Reverse Proxy und Einstiegspunkt
- `admin-ui`: browserbasierte Verwaltungsoberfläche, die Benutzer und Konfiguration erzeugt
- `generated/docker-compose.users.yml`: generierte Service-Definitionen für aktive Benutzer
- `generated/Caddy.users`: generierte Reverse-Proxy-Routen für aktive Benutzer
- `users/users.json`: lokale Benutzerregistrierung, die zur Laufzeit von der Admin-WebUI erzeugt wird

Die Admin-WebUI schreibt die generierten Dateien und führt danach aus:

```bash
docker compose -f docker-compose.yml -f generated/docker-compose.users.yml up -d --remove-orphans
```

Damit werden Benutzercontainer direkt über den Browser erstellt, aktualisiert, deaktiviert oder entfernt.

## Schnellstart

1. Umgebungsdatei kopieren:

```bash
cp .env.example .env
```

2. Passwort-Hash für den Admin-Zugang in Caddy erzeugen:

```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext "ersetzen"
```

3. `.env` bearbeiten und folgende Werte setzen:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`
- `ADMIN_USER_PASSWORD_HASH`

4. Stack starten:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

5. Admin-WebUI öffnen:

- `http://DEIN_HOST/admin/`

6. Benutzer und Workspaces in der WebUI anlegen.

## Compose-Dateien

- `docker-compose.yml`: Standard-Deployment per Docker Compose aus einem ausgecheckten Repo
- `docker-compose.ghcr.yml`: explizite GHCR-Variante für die Admin-WebUI
- `docker-compose.build.yml`: Build-Override für lokale Entwicklung
- `docker-compose.portainer.yml`: Portainer-kompatibler Stack ohne lokale Datei-Bind-Mounts

Für Proxmox oder andere Server-Deployments ist die GHCR-Variante in der Regel die bessere Wahl:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

Um eine feste Version zu pinnen:

```bash
ADMIN_UI_IMAGE_TAG=0.3.0 docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

Veröffentlichter Image-Pfad:

```text
ghcr.io/itsh-neumeier/mobileworkspace-linux/admin-ui
```

Für lokale Entwicklungs-Builds statt GHCR:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

## Portainer-Deployment

Wenn du das Projekt über den Portainer-Stack-Editor deployen willst, verwende:

- `docker-compose.portainer.yml`

Diese Variante vermeidet die lokalen Bind-Mounts, die in Portainer scheitern, wenn Dateien wie `Caddyfile` auf dem vom Stack-Editor verwendeten Host-Pfad nicht vorhanden sind.

Empfohlene Portainer-Umgebungsvariablen:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`
- `ADMIN_USER_PASSWORD_HASH`
- `ADMIN_UI_IMAGE_TAG`
- `MWC_EDGE_NETWORK`
- `MWC_PUBLIC_NETWORK`
- `MWC_INTERNAL_NETWORK`

Verhalten des Portainer-Stacks:

- Caddy erzeugt seine Basiskonfiguration beim Start im Container selbst
- beim ersten Start erzeugt Caddy ein zufälliges Admin-Passwort und schreibt es einmal in die Logs, wenn `ADMIN_USER_PASSWORD_HASH` leer ist
- Benutzerregister und generierte Konfiguration liegen in einem benannten Docker-Volume
- die Admin-WebUI provisioniert Benutzercontainer über den Docker-Socket
- Benutzer-Workspaces verwenden benannte Docker-Volumes statt relativer Host-Pfade

Empfohlen für den ersten Start:

- `DOMAIN_OR_HOST=:80`
- `ADMIN_USER_NAME=admin`
- `ADMIN_USER_PASSWORD_HASH` leer lassen

Nach dem ersten Start liest du das generierte Passwort in Portainer aus den Logs des Containers `mobileworkspace-caddy`.

Die Admin-WebUI erzeugt anschließend Routen wie:

- `http://DEIN_HOST/workspaces/ops/`
- `http://DEIN_HOST/workspaces/internal-admin/`

## Benutzerverwaltung in der WebUI

Die Admin-WebUI unterstützt:

- Benutzer-Workspace anlegen
- zwischen Terminal und Desktop wählen
- zwischen Public und Internal-only Netzwerk wählen
- Workspace aktivieren und deaktivieren
- Workspace neu bereitstellen
- Workspace löschen und die generierte Container-Definition entfernen

Jeder angelegte Benutzer erhält:

- einen isolierten Container
- eine generierte Caddy-Route
- persistente Docker-Volumes für Konfiguration und Workspace-Daten
- Zugriffsschutz per Caddy Basic Auth

Bei Terminal-Workspaces wird dasselbe Passwort zusätzlich für den internen `code-server`-Login verwendet.

## Proxmox

Das Projekt ist für den Betrieb auf Proxmox vorgesehen. Das empfohlene Deployment-Modell ist:

- Proxmox-Host
- eine dedizierte Debian- oder Ubuntu-VM
- Docker und Docker Compose innerhalb dieser VM

Das ist robuster als Docker in einem LXC-Container, besonders wenn Benutzer dynamisch erzeugt und Desktop-Container bereitgestellt werden sollen.

Detaillierte Anleitung: `docs/proxmox.md`

## Standard-Netzwerkmodell

- `edge`: gemeinsames Netz für Caddy, Admin-WebUI und Benutzer-Workspaces
- `public_net`: Docker-Bridge-Netz mit ausgehendem Internetzugang
- `internal_net`: internes Docker-Netz ohne ausgehenden Internetzugang

Die Admin-WebUI ordnet jeden Workspace beim Anlegen einem dieser Profile zu.

## Sicherheitshinweise

- Vor einer öffentlichen Freigabe unbedingt TLS aktivieren
- Die Admin-WebUI mountet den Docker-Socket und hat damit volle Kontrolle über den Docker-Host
- Für breiteren Einsatz besser SSO oder einen Identity-Aware-Proxy statt Basic Auth verwenden
- Sensible Werte nicht in Git speichern und Dateirechte in der VM einschränken
- Desktop-Workspaces benötigen mehr CPU und RAM als reine Terminal-Umgebungen
- Docker-Images und gemountete Pfade vor produktivem Einsatz prüfen

## Versionierung und Releases

- Die Projektversion steht in `VERSION`
- `CHANGELOG.md` wird bei jedem Release gepflegt
- Git-Tags nach Semantic Versioning verwenden, zum Beispiel `v0.2.0`
- GitHub Actions erstellt für gepushte Versionstags ein Release-Artefakt
- GitHub Actions veröffentlicht zusätzlich das Admin-UI-Image nach GHCR

Beispiel für einen Release-Ablauf:

```bash
git add .
git commit -m "release: v0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Dokumentation

- Englisch: `README.md`
- Deutsch: `README.de.md`
- Proxmox-Deployment: `docs/proxmox.md`
- Änderungen: `CHANGELOG.md`

## Lizenz

MIT. Siehe `LICENSE`.

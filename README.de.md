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
- Optionale Proxmox-VM-Bereitstellung pro Benutzer für Desktop-Workspaces
- Terminal-Workspaces mit `code-server`
- Desktop-Workspaces mit `webtop` über WebVNC
- Automatische nginx-Routen pro Benutzer
- Internet- oder Internal-only-Netz pro Workspace
- Persistenter Speicher pro Benutzer
- Für Proxmox-VMs ausgelegt
- MIT-Lizenz
- Semantic Versioning und GitHub-Release-Flow

## Architektur

- `admin-ui`: browserbasierte Verwaltungsoberfläche mit eingebautem Admin-Login, Workspace-Provisionierung und integriertem nginx-Reverse-Proxy
- `generated/docker-compose.users.yml`: generierte Service-Definitionen für aktive Benutzer
- `generated/nginx.users.conf`: generierte Reverse-Proxy-Routen für aktive Benutzer
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

2. `.env` bearbeiten und folgende Werte setzen:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`
- `ADMIN_INITIAL_PASSWORD` (Standard: `admin`)
- `ADMIN_AUTO_REPAIR` (Standard: `true`, repariert defekte Bootstrap-Hashdateien automatisch)

3. Stack starten:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

4. Admin-WebUI öffnen:

- `http://DEIN_HOST/admin/`

5. Mit `ADMIN_USER_NAME` und `ADMIN_INITIAL_PASSWORD` anmelden (Standard: `admin` / `admin`). Beim ersten Login ist eine Passwortänderung verpflichtend.

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

Diese Variante vermeidet die lokalen Bind-Mounts, die in Portainer scheitern, wenn Stack-Editor-Deployments Projektdateien auf dem Docker-Host erwarten.

Empfohlene Portainer-Umgebungsvariablen:

- `DOMAIN_OR_HOST`
- `TIMEZONE`
- `ADMIN_USER_NAME`
- `ADMIN_INITIAL_PASSWORD`
- `ADMIN_UI_IMAGE_TAG`
- `MWC_EDGE_NETWORK`
- `MWC_PUBLIC_NETWORK`
- `MWC_INTERNAL_NETWORK`
- `MWC_PROVISIONER_MODE`

Verhalten des Portainer-Stacks:

- der admin-ui Container erzeugt seine nginx-Basiskonfiguration beim Start selbst
- die Admin-WebUI erzeugt den Bootstrap-Admin aus `ADMIN_USER_NAME` und `ADMIN_INITIAL_PASSWORD`
- Benutzerregister und generierte Konfiguration liegen in einem benannten Docker-Volume
- die Admin-WebUI provisioniert Benutzercontainer über den Docker-Socket
- Benutzer-Workspaces verwenden benannte Docker-Volumes statt relativer Host-Pfade

Empfohlen für den ersten Start:

- `DOMAIN_OR_HOST=:80`
- `ADMIN_USER_NAME=admin`

Nach dem ersten Start meldest du dich mit `ADMIN_USER_NAME` und `ADMIN_INITIAL_PASSWORD` an und setzt sofort ein neues Admin-Passwort.

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
- eine generierte nginx-Route
- persistente Docker-Volumes für Konfiguration und Workspace-Daten
- Zugriffsschutz per nginx Basic Auth

Bei Terminal-Workspaces wird dasselbe Passwort zusätzlich für den internen `code-server`-Login verwendet.

## Proxmox

Das Projekt ist für den Betrieb auf Proxmox vorgesehen. Das empfohlene Deployment-Modell ist:

- Proxmox-Host
- eine dedizierte Debian- oder Ubuntu-VM
- Docker und Docker Compose innerhalb dieser VM

Das ist robuster als Docker in einem LXC-Container, besonders wenn Benutzer dynamisch erzeugt und Desktop-Container bereitgestellt werden sollen.

Detaillierte Anleitung: `docs/proxmox.md`

### Proxmox-VM-Modus

Wenn Mobile Web Console Hub Desktop-Umgebungen als echte Proxmox-VMs (statt Docker-webtop-Containern) anlegen soll, setze:

- `Provisioner Modus = Proxmox VM` im Admin-UI Einstellungsbereich

Im Proxmox-VM-Modus bietet die Admin-WebUI zusätzlich:

- Proxmox-Backend-Einstellungen (API URL, Node, Token, Template-VMID, TLS-Prüfung)
- VMID-Range-Steuerung (z. B. `8001` bis `8999`)
- VM-Overrides pro Benutzer (vCPU, RAM, Bridge, Disk, Auto-Start)
- einen integrierten `Proxmox API testen`-Button für einen End-to-End-API-Check
- VM-Löschen direkt über die Workspace-Aktionen (führt echtes Proxmox-Delete aus)

Wenn du eine fertige Debian-13-Cloud-Init-Template-VM in Proxmox brauchst, nutze:

```bash
sh scripts/proxmox-create-debian13-template.sh --vmid 9000 --name debian13-cloud-template
```

Direkt von GitHub auf dem Proxmox-Host:

```bash
curl -fsSL https://raw.githubusercontent.com/itsh-neumeier/mobileworkspace-linux/main/scripts/proxmox-create-debian13-template.sh | sh -s -- --vmid 9000 --name debian13-cloud-template
```

Geführter TUI-Wizard:

```bash
curl -fsSL https://raw.githubusercontent.com/itsh-neumeier/mobileworkspace-linux/main/scripts/proxmox-create-debian13-template.sh | sh -s -- --tui
```

## Optionaler Externer Proxy

Wenn du den Dienst extern veröffentlichen willst, kannst du zusätzlich einen Reverse Proxy wie Zoraxy vor diesen Stack setzen.

Empfohlenes Modell:

- Mobile Web Console Hub läuft intern per HTTP
- das integrierte nginx in diesem Projekt übernimmt `/admin/` und `/workspaces/...`
- Zoraxy übernimmt optional öffentliche Domain, TLS und den externen Zugriff

## Standard-Netzwerkmodell

- `edge`: gemeinsames Netz für den admin-ui Container und Benutzer-Workspaces
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

# Mobile Web Console Hub

Mobile Web Console Hub ist eine Docker-basierte, selbst gehostete Plattform für browserbasierte Linux-Arbeitsumgebungen. Jeder Benutzer erhält eine isolierte Umgebung, entweder als Browser-Terminal oder als vollständigen Linux-Desktop im Browser, mit persistentem Speicher und kontrolliertem Netzwerkzugriff für internetfähige oder interne Administrationsaufgaben.

Das Projekt ist für Situationen gedacht, in denen du an verwalteten Geräten ohne lokale Administratorrechte arbeitest und trotzdem eine praktikable, mobil nutzbare Weboberfläche benötigst, um Shell-Befehle auszuführen, per SSH Systeme zu verwalten oder leichte Betriebsaufgaben zu erledigen.

## Funktionen

- Weboberfläche für Smartphone, Tablet und Notebook
- Eine isolierte Linux-Umgebung pro Benutzer
- Optional vollständiger Linux-Desktop per WebVNC/noVNC
- Persistente Home-Verzeichnisse
- Optionaler Internetzugang oder nur internes Netzwerk pro Umgebung
- Integriertes Terminal über `code-server`
- Reverse Proxy mit eigener URL pro Benutzer
- MIT-Lizenz
- Für Semantic Versioning vorbereitet

## Architektur

- `caddy`: zentraler Einstiegspunkt und Reverse Proxy
- `workspace-public`: Beispielumgebung mit Internetzugang
- `workspace-internal`: Beispielumgebung für internes Netz
- `desktop-public`: Beispiel-Desktop mit Internetzugang per WebVNC
- `desktop-internal`: Beispiel-Desktop nur für internes Netz per WebVNC
- `code-server`: liefert die Weboberfläche mit Terminal, Dateiübersicht und optionalem Editor
- `webtop`: liefert eine vollständige Desktop-Sitzung im Browser

`code-server` wird für terminalorientierte Umgebungen verwendet, weil es auf mobilen Browsern gut funktioniert und direkt ein Terminal mitbringt. `webtop` ergänzt das Projekt um vollständige Linux-Desktops per WebVNC/noVNC, wenn GUI-Werkzeuge oder ein klassischer Desktop-Workflow benötigt werden.

## Schnellstart

1. Beispieldatei für Umgebungsvariablen kopieren:

```bash
cp .env.example .env
```

2. Passwort-Hashes für Caddy Basic Auth erzeugen:

```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext "ersetzen"
```

3. `.env` bearbeiten und folgende Werte setzen:

- `DOMAIN_OR_HOST`
- `PUBLIC_USER_PASSWORD_HASH`
- `INTERNAL_USER_PASSWORD_HASH`
- `PUBLIC_WORKSPACE_PASSWORD`
- `INTERNAL_WORKSPACE_PASSWORD`
- `PUBLIC_DESKTOP_USER_PASSWORD_HASH`
- `INTERNAL_DESKTOP_USER_PASSWORD_HASH`

4. Stack starten:

```bash
docker compose up -d
```

5. Service aufrufen:

- `http://DEIN_HOST/public/`
- `http://DEIN_HOST/desktop-public/`
- `http://DEIN_HOST/internal/`
- `http://DEIN_HOST/desktop-internal/`

## Proxmox

Das Projekt ist für den Betrieb auf Proxmox vorgesehen. Das empfohlene Deployment-Modell ist:

- Proxmox-Host
- eine dedizierte Debian- oder Ubuntu-VM
- Docker und Docker Compose innerhalb dieser VM

Das ist im Alltag stabiler als Docker innerhalb eines LXC-Containers, besonders bei Multi-User-Netzwerken und WebVNC-Desktops.

Detaillierte Anleitung: `docs/proxmox.md`

## Standard-Netzwerkmodell

- `edge`: an den Reverse Proxy angebunden
- `public_net`: Docker-Bridge-Netz mit Internetzugang
- `internal_net`: internes Docker-Netz ohne ausgehenden Internetzugang

Die enthaltenen Beispiele zeigen zwei Benutzerprofile:

- `workspace-public`: kann ins Internet
- `workspace-internal`: kann nur mit dem internen Docker-Netz kommunizieren, solange du keine weiteren Netze verbindest
- `desktop-public`: vollständiger Browser-Desktop mit Internetzugang
- `desktop-internal`: vollständiger Browser-Desktop nur im internen Netz

## Weitere Benutzer hinzufügen

Mit dem Hilfsskript kannst du neue Benutzerkonfigurationen vorbereiten:

```powershell
pwsh ./scripts/New-WorkspaceUser.ps1 -UserName ops -Route ops -Mode public
```

Desktop-Beispiel:

```powershell
pwsh ./scripts/New-WorkspaceUser.ps1 -UserName ops-desktop -Route desktop-ops -Mode internal -WorkspaceType desktop
```

Das Skript gibt Folgendes aus:

- einen Docker-Compose-Service-Block
- einen Caddy-Routen-Block
- die benötigten `.env`-Variablen

## Sicherheitshinweise

- Vor einer Internetfreigabe unbedingt TLS aktivieren
- Für breiteren Einsatz besser SSO oder einen Identity-Aware-Proxy statt Basic Auth nutzen
- Geheimnisse in produktiven Umgebungen in einem Secret Manager speichern
- SSH-Schlüssel und ausgehende Netzverbindungen pro Rolle begrenzen
- Docker-Mounts prüfen und keine sensiblen Host-Pfade einhängen
- WebVNC-Desktops benötigen mehr RAM und CPU als reine Terminal-Umgebungen

## Versionierung und Releases

- Die Projektversion steht in `VERSION`
- `CHANGELOG.md` wird bei jedem Release gepflegt
- Git-Tags nach Semantic Versioning verwenden, zum Beispiel `v0.2.0`
- GitHub Actions validiert das Tag und veröffentlicht ein Release-Archiv

Beispiel für einen Release-Ablauf:

```bash
git add .
git commit -m "release: v0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Auf GitHub veröffentlichen

Lege ein öffentliches Repository auf GitHub an und verbinde diesen Ordner damit:

```bash
git init
git branch -M main
git add .
git commit -m "feat: initial release"
git remote add origin https://github.com/DEIN-USER/DEIN-REPO.git
git push -u origin main
```

## Dokumentation

- Englisch: `README.md`
- Deutsch: `README.de.md`
- Proxmox-Deployment: `docs/proxmox.md`
- Änderungen: `CHANGELOG.md`

## Lizenz

MIT. Siehe `LICENSE`.

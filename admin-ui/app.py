import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import bcrypt
from flask import Flask, redirect, render_template_string, request, url_for


PROJECT_ROOT = Path(os.environ.get("MWC_PROJECT_ROOT", "/workspace"))
USERS_FILE = Path(os.environ.get("MWC_USERS_FILE", PROJECT_ROOT / "users" / "users.json"))
GENERATED_COMPOSE = Path(
    os.environ.get("MWC_GENERATED_COMPOSE", PROJECT_ROOT / "generated" / "docker-compose.users.yml")
)
GENERATED_CADDY = Path(os.environ.get("MWC_GENERATED_CADDY", PROJECT_ROOT / "generated" / "Caddy.users"))
DOMAIN_OR_HOST = os.environ.get("MWC_DOMAIN_OR_HOST", "localhost")
TIMEZONE = os.environ.get("MWC_TIMEZONE", "Europe/Berlin")
BASE_COMPOSE = PROJECT_ROOT / "docker-compose.yml"
VERSION_FILE = PROJECT_ROOT / "VERSION"
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "dev"
GITHUB_URL = "https://github.com/itsh-neumeier/mobileworkspace-linux"

APP = Flask(__name__)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mobile Web Console Hub Admin</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    :root {
      --mwc-bg: radial-gradient(circle at top left, rgba(29, 78, 216, 0.18), transparent 26%), linear-gradient(180deg, #f4f7fb 0%, #e8eef8 100%);
      --mwc-surface: rgba(255, 255, 255, 0.9);
      --mwc-surface-strong: rgba(255, 255, 255, 0.97);
      --mwc-border: rgba(148, 163, 184, 0.28);
      --mwc-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
      --mwc-accent: #0f62fe;
      --mwc-accent-soft: rgba(15, 98, 254, 0.12);
      --mwc-success-soft: rgba(34, 197, 94, 0.14);
      --mwc-danger-soft: rgba(239, 68, 68, 0.14);
      --mwc-warning-soft: rgba(245, 158, 11, 0.16);
    }
    [data-bs-theme="dark"] {
      --mwc-bg: radial-gradient(circle at top left, rgba(96, 165, 250, 0.16), transparent 28%), linear-gradient(180deg, #020817 0%, #0f172a 100%);
      --mwc-surface: rgba(15, 23, 42, 0.82);
      --mwc-surface-strong: rgba(15, 23, 42, 0.96);
      --mwc-border: rgba(148, 163, 184, 0.18);
      --mwc-shadow: 0 24px 60px rgba(2, 6, 23, 0.45);
      --mwc-accent: #7cc4ff;
      --mwc-accent-soft: rgba(124, 196, 255, 0.14);
      --mwc-success-soft: rgba(34, 197, 94, 0.18);
      --mwc-danger-soft: rgba(248, 113, 113, 0.16);
      --mwc-warning-soft: rgba(251, 191, 36, 0.18);
    }
    body {
      background: var(--mwc-bg);
      color: var(--bs-body-color);
      min-height: 100vh;
      font-family: "Segoe UI", sans-serif;
    }
    .app-shell {
      min-height: 100vh;
    }
    .glass-panel {
      background: var(--mwc-surface);
      border: 1px solid var(--mwc-border);
      box-shadow: var(--mwc-shadow);
      backdrop-filter: blur(14px);
    }
    .hero-card {
      border-radius: 2rem;
      overflow: hidden;
      position: relative;
    }
    .hero-card::after {
      content: "";
      position: absolute;
      inset: auto -10% -35% auto;
      width: 22rem;
      height: 22rem;
      background: radial-gradient(circle, var(--mwc-accent-soft) 0%, transparent 68%);
      pointer-events: none;
    }
    .hero-title {
      font-size: clamp(2.2rem, 3vw, 3.4rem);
      letter-spacing: -0.04em;
    }
    .metric-chip {
      background: var(--mwc-surface-strong);
      border: 1px solid var(--mwc-border);
      border-radius: 999px;
      padding: 0.55rem 0.9rem;
      font-size: 0.92rem;
    }
    .section-card {
      border-radius: 1.75rem;
    }
    .form-control,
    .form-select {
      border-radius: 1rem;
      padding-top: 0.8rem;
      padding-bottom: 0.8rem;
    }
    .form-control:focus,
    .form-select:focus,
    .btn:focus {
      box-shadow: 0 0 0 0.25rem var(--mwc-accent-soft);
    }
    .btn {
      border-radius: 999px;
    }
    .btn-primary {
      background: var(--mwc-accent);
      border-color: var(--mwc-accent);
    }
    .btn-outline-secondary {
      border-color: var(--mwc-border);
    }
    .theme-toggle {
      width: 2.75rem;
      height: 2.75rem;
    }
    .workspace-card {
      border-radius: 1.5rem;
      background: var(--mwc-surface-strong);
      border: 1px solid var(--mwc-border);
      transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .workspace-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--mwc-shadow);
    }
    .soft-badge {
      border-radius: 999px;
      border: 1px solid var(--mwc-border);
      padding: 0.45rem 0.8rem;
      background: var(--mwc-surface);
      font-size: 0.85rem;
    }
    .status-active {
      background: var(--mwc-success-soft);
      color: var(--bs-success-text-emphasis);
    }
    .status-disabled {
      background: var(--mwc-warning-soft);
      color: var(--bs-warning-text-emphasis);
    }
    .url-pill {
      border-radius: 1rem;
      background: var(--mwc-accent-soft);
      color: var(--bs-body-color);
      word-break: break-all;
    }
    .empty-state {
      border: 1px dashed var(--mwc-border);
      border-radius: 1.5rem;
      background: color-mix(in srgb, var(--mwc-surface) 78%, transparent);
    }
    .footer-shell {
      border-top: 1px solid var(--mwc-border);
      color: var(--bs-secondary-color);
    }
  </style>
</head>
<body data-bs-theme="light">
  <div class="app-shell d-flex flex-column">
    <div class="container py-4 py-lg-5 flex-grow-1">
      <header class="d-flex flex-column flex-lg-row align-items-start align-items-lg-center justify-content-between gap-3 mb-4">
        <div>
          <div class="text-uppercase small fw-semibold text-primary mb-2">Mobile Workspace</div>
          <h1 class="display-6 fw-bold mb-1">Admin Console</h1>
          <p class="text-body-secondary mb-0">Create isolated Linux workspaces with terminal or WebVNC desktop access directly from the browser.</p>
        </div>
        <div class="d-flex align-items-center gap-2">
          <button class="btn btn-outline-secondary theme-toggle" type="button" id="themeToggle" aria-label="Toggle theme">
            <i class="bi bi-moon-stars-fill" id="themeIcon"></i>
          </button>
        </div>
      </header>

      <section class="glass-panel hero-card p-4 p-lg-5 mb-4">
        <div class="row g-4 align-items-center">
          <div class="col-lg-8">
            <div class="hero-title fw-bold mb-3">Provision users, routes, and containers from one place.</div>
            <p class="lead text-body-secondary mb-0">Choose terminal or desktop mode, assign a network policy, and let the panel regenerate Docker Compose and Caddy configuration automatically.</p>
          </div>
          <div class="col-lg-4">
            <div class="d-flex flex-wrap gap-2 justify-content-lg-end">
              <span class="metric-chip fw-semibold">Host: {{ domain }}</span>
              <span class="metric-chip fw-semibold">Timezone: {{ timezone }}</span>
              <span class="metric-chip fw-semibold">Users: {{ users|length }}</span>
            </div>
          </div>
        </div>
      </section>

      <div class="row g-4">
        <div class="col-12 col-xl-4">
          <section class="glass-panel section-card p-4 h-100">
            <div class="d-flex align-items-center gap-2 mb-3">
              <div class="rounded-circle d-inline-flex align-items-center justify-content-center bg-primary-subtle text-primary" style="width: 2.5rem; height: 2.5rem;">
                <i class="bi bi-person-plus-fill"></i>
              </div>
              <div>
                <h2 class="h4 mb-0">Create Workspace</h2>
                <p class="text-body-secondary mb-0 small">Add a new user container and publish its route.</p>
              </div>
            </div>
            {% if flash %}
            <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
            {% endif %}
            <form method="post" action="{{ url_for('create_user') }}">
              <div class="mb-3">
                <label class="form-label fw-semibold" for="username">User Name</label>
                <input class="form-control" id="username" name="username" placeholder="ops-team" required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="route">Route</label>
                <input class="form-control" id="route" name="route" placeholder="ops-team" required>
                <div class="form-text">This becomes the URL segment, for example <code>/workspaces/ops-team/</code>.</div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="workspace_type">Workspace Type</label>
                <select class="form-select" id="workspace_type" name="workspace_type">
                  <option value="terminal">Terminal Workspace</option>
                  <option value="desktop">Desktop Workspace (WebVNC)</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="network_mode">Network Mode</label>
                <select class="form-select" id="network_mode" name="network_mode">
                  <option value="public">Internet Enabled</option>
                  <option value="internal">Internal Only</option>
                </select>
              </div>

              <div class="mb-4">
                <label class="form-label fw-semibold" for="password">User Password</label>
                <input class="form-control" id="password" name="password" type="password" required>
                <div class="form-text">Used for Caddy access protection and, for terminal workspaces, for the internal code-server login.</div>
              </div>

              <button class="btn btn-primary w-100 py-3 fw-semibold" type="submit">
                <i class="bi bi-rocket-takeoff-fill me-2"></i>Create User Workspace
              </button>
            </form>
          </section>
        </div>

        <div class="col-12 col-xl-8">
          <section class="glass-panel section-card p-4 h-100">
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-3">
              <div>
                <h2 class="h4 mb-1">Provisioned Users</h2>
                <p class="text-body-secondary mb-0">Manage active workspaces, redeploy them, or disable them without editing files manually.</p>
              </div>
              <div class="soft-badge fw-semibold">
                <i class="bi bi-hdd-stack-fill me-2"></i>{{ users|length }} managed workspace{{ '' if users|length == 1 else 's' }}
              </div>
            </div>
            {% if users %}
            <div class="row g-3">
              {% for user in users %}
              <div class="col-12">
                <article class="workspace-card p-4">
                  <div class="d-flex flex-column flex-lg-row justify-content-between gap-3">
                    <div>
                      <div class="d-flex align-items-center gap-2 flex-wrap mb-2">
                        <h3 class="h5 mb-0">{{ user.username }}</h3>
                        <span class="soft-badge">{{ user.workspace_type }}</span>
                        <span class="soft-badge">{{ user.network_mode }}</span>
                        <span class="soft-badge {{ 'status-active' if user.enabled else 'status-disabled' }}">{{ 'active' if user.enabled else 'disabled' }}</span>
                      </div>
                      <div class="text-body-secondary small mb-3">Created {{ user.created_at }}</div>
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-box-seam-fill me-2"></i>{{ user.container_name }}
                      </div>
                      <div class="url-pill px-3 py-2 d-inline-flex align-items-center">
                        <i class="bi bi-link-45deg me-2"></i>http://{{ domain }}{{ user.route_path }}
                      </div>
                    </div>
                    <div class="d-flex flex-wrap align-items-start justify-content-lg-end gap-2">
                      {% if user.enabled %}
                      <form method="post" action="{{ url_for('toggle_user', user_id=user.id, action='disable') }}">
                        <button class="btn btn-outline-secondary" type="submit">
                          <i class="bi bi-pause-circle me-2"></i>Disable
                        </button>
                      </form>
                      {% else %}
                      <form method="post" action="{{ url_for('toggle_user', user_id=user.id, action='enable') }}">
                        <button class="btn btn-primary" type="submit">
                          <i class="bi bi-play-circle me-2"></i>Enable
                        </button>
                      </form>
                      {% endif %}
                      <form method="post" action="{{ url_for('redeploy_user', user_id=user.id) }}">
                        <button class="btn btn-outline-secondary" type="submit">
                          <i class="bi bi-arrow-repeat me-2"></i>Redeploy
                        </button>
                      </form>
                      <form method="post" action="{{ url_for('delete_user', user_id=user.id) }}">
                        <button class="btn btn-outline-danger" type="submit">
                          <i class="bi bi-trash3 me-2"></i>Delete
                        </button>
                      </form>
                    </div>
                  </div>
                </article>
              </div>
              {% endfor %}
            </div>
            {% else %}
            <div class="empty-state p-5 text-center">
              <div class="display-6 mb-3"><i class="bi bi-inboxes-fill"></i></div>
              <h3 class="h5">No workspaces yet</h3>
              <p class="text-body-secondary mb-0">Create the first user on the left to generate a route, storage path, and Docker container automatically.</p>
            </div>
            {% endif %}
          </section>
        </div>
      </div>
    </div>

    <footer class="footer-shell py-3">
      <div class="container d-flex flex-column flex-md-row justify-content-between align-items-center gap-2 small">
        <div>Mobile Web Console Hub v{{ version }}</div>
        <div class="d-flex align-items-center gap-3">
          <a class="link-secondary link-offset-2 link-underline-opacity-0 link-underline-opacity-75-hover" href="{{ github_url }}" target="_blank" rel="noopener">GitHub</a>
          <span>&copy; {{ copyright_year }} Mobile Web Console Hub</span>
        </div>
      </div>
    </footer>
  </div>
  <script>
    const root = document.documentElement;
    const body = document.body;
    const storageKey = "mwc-theme";
    const themeIcon = document.getElementById("themeIcon");
    const applyTheme = (theme) => {
      body.setAttribute("data-bs-theme", theme);
      themeIcon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
      localStorage.setItem(storageKey, theme);
    };
    const preferredTheme = localStorage.getItem(storageKey) || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    applyTheme(preferredTheme);
    document.getElementById("themeToggle").addEventListener("click", () => {
      applyTheme(body.getAttribute("data-bs-theme") === "dark" ? "light" : "dark");
    });
  </script>
</body>
</html>
"""


def ensure_storage() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_COMPOSE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]\n", encoding="utf-8")
    if not GENERATED_COMPOSE.exists():
        GENERATED_COMPOSE.write_text("services: {}\n", encoding="utf-8")
    if not GENERATED_CADDY.exists():
        GENERATED_CADDY.write_text("# Generated routes for user workspaces will be written here by the admin UI.\n", encoding="utf-8")


def load_users():
    ensure_storage()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_users(users) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValueError("Route must contain at least one letter or number.")
    return slug


def validate_username(value: str) -> str:
    candidate = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,32}", candidate):
        raise ValueError("User name must be 3-32 characters and use only letters, numbers, dot, underscore, or dash.")
    return candidate


def make_id(route: str, workspace_type: str) -> str:
    return f"{workspace_type}-{route}"


def compose_service_block(user: dict) -> str:
    if user["workspace_type"] == "desktop":
        return f"""  {user["service_name"]}:
    image: lscr.io/linuxserver/webtop:ubuntu-kde
    container_name: {user["container_name"]}
    restart: unless-stopped
    shm_size: "1gb"
    environment:
      PUID: 1000
      PGID: 1000
      TZ: {TIMEZONE}
      SUBFOLDER: {yaml_safe(user["route_path"])}
      TITLE: {yaml_safe(f"{user['username']} Desktop")}
    volumes:
      - ./data/{user["route"]}/config:/config
    networks:
      - edge
      - {network_name(user)}
"""

    return f"""  {user["service_name"]}:
    image: codercom/code-server:4.104.2
    container_name: {user["container_name"]}
    restart: unless-stopped
    environment:
      PASSWORD: {yaml_safe(user["password"])}
    command:
      - code-server
      - --bind-addr
      - 0.0.0.0:8080
      - --auth
      - password
      - --disable-telemetry
      - --disable-update-check
      - --base-path
      - {user["route_path"]}
      - /home/coder/project
    volumes:
      - ./data/{user["route"]}/project:/home/coder/project
      - ./data/{user["route"]}/config:/home/coder/.local/share/code-server
    networks:
      - edge
      - {network_name(user)}
"""


def yaml_safe(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def network_name(user: dict) -> str:
    return "internal_net" if user["network_mode"] == "internal" else "public_net"


def caddy_block(user: dict) -> str:
    return f"""handle_path {user["route_path"]}* {{
\tbasicauth {{
\t\t{user["username"]} {user["password_hash"]}
\t}}
\treverse_proxy {user["service_name"]}:{upstream_port(user)}
}}
"""


def upstream_port(user: dict) -> int:
    return 3000 if user["workspace_type"] == "desktop" else 8080


def write_generated_files(users) -> None:
    enabled = [user for user in users if user.get("enabled", True)]

    if enabled:
        compose_text = "services:\n" + "".join(compose_service_block(user) for user in enabled)
        caddy_text = "".join(caddy_block(user) for user in enabled)
    else:
        compose_text = "services: {}\n"
        caddy_text = "# Generated routes for user workspaces will be written here by the admin UI.\n"

    GENERATED_COMPOSE.write_text(compose_text, encoding="utf-8")
    GENERATED_CADDY.write_text(caddy_text, encoding="utf-8")


def deploy_stack(users) -> tuple[bool, str]:
    enabled_services = [user["service_name"] for user in users if user.get("enabled", True)]
    command = [
        "docker",
        "compose",
        "-f",
        str(BASE_COMPOSE),
        "-f",
        str(GENERATED_COMPOSE),
        "up",
        "-d",
        "--remove-orphans",
        "caddy",
    ]
    command.extend(enabled_services)
    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, output or "Stack updated."


def provision(users) -> tuple[bool, str]:
    write_generated_files(users)
    return deploy_stack(users)


def password_hash(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def current_flash():
    return {
        "flash": request.args.get("message", ""),
        "flash_error": request.args.get("error") == "1",
    }


def redirect_with_message(message: str, error: bool = False):
    return redirect(url_for("index", message=message, error="1" if error else "0"))


@APP.route("/")
def root():
    return redirect("/admin/")


@APP.route("/admin/")
def index():
    users = load_users()
    flash_data = current_flash()
    return render_template_string(
        PAGE_TEMPLATE,
        users=users,
        domain=DOMAIN_OR_HOST,
        timezone=TIMEZONE,
        version=APP_VERSION,
        github_url=GITHUB_URL,
        copyright_year=datetime.utcnow().year,
        **flash_data,
    )


@APP.post("/admin/users")
def create_user():
    users = load_users()
    try:
        username = validate_username(request.form["username"])
        route = slugify(request.form["route"])
        workspace_type = request.form["workspace_type"]
        network_mode = request.form["network_mode"]
        password = request.form["password"]
    except KeyError:
        return redirect_with_message("Required form field missing.", error=True)
    except ValueError as exc:
        return redirect_with_message(str(exc), error=True)

    if workspace_type not in {"terminal", "desktop"}:
        return redirect_with_message("Unsupported workspace type.", error=True)
    if network_mode not in {"public", "internal"}:
        return redirect_with_message("Unsupported network mode.", error=True)
    if any(user["route"] == route for user in users):
        return redirect_with_message(f"Route '{route}' already exists.", error=True)
    if not password:
        return redirect_with_message("User password is required.", error=True)

    user = {
        "id": make_id(route, workspace_type),
        "username": username,
        "route": route,
        "route_path": f"/workspaces/{route}/",
        "workspace_type": workspace_type,
        "network_mode": network_mode,
        "password": password,
        "password_hash": password_hash(password),
        "enabled": True,
        "service_name": make_id(route, workspace_type),
        "container_name": f"mwc-{make_id(route, workspace_type)}",
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    users.append(user)
    save_users(users)
    ok, output = provision(users)
    if not ok:
        return redirect_with_message(f"User saved, but deploy failed: {trim_output(output)}", error=True)
    return redirect_with_message(f"Workspace '{username}' created and deployed.")


def find_user(users, user_id: str):
    return next((user for user in users if user["id"] == user_id), None)


@APP.post("/admin/users/<user_id>/<action>")
def toggle_user(user_id: str, action: str):
    users = load_users()
    user = find_user(users, user_id)
    if not user:
        return redirect_with_message("User not found.", error=True)
    if action not in {"enable", "disable"}:
        return redirect_with_message("Unsupported action.", error=True)
    user["enabled"] = action == "enable"
    save_users(users)
    ok, output = provision(users)
    if not ok:
        return redirect_with_message(f"State updated, but deploy failed: {trim_output(output)}", error=True)
    return redirect_with_message(f"Workspace '{user['username']}' {action}d.")


@APP.post("/admin/users/<user_id>/redeploy")
def redeploy_user(user_id: str):
    users = load_users()
    user = find_user(users, user_id)
    if not user:
        return redirect_with_message("User not found.", error=True)
    ok, output = provision(users)
    if not ok:
        return redirect_with_message(f"Redeploy failed: {trim_output(output)}", error=True)
    return redirect_with_message(f"Workspace '{user['username']}' redeployed.")


@APP.post("/admin/users/<user_id>/delete")
def delete_user(user_id: str):
    users = load_users()
    user = find_user(users, user_id)
    if not user:
        return redirect_with_message("User not found.", error=True)
    remaining = [item for item in users if item["id"] != user_id]
    save_users(remaining)
    ok, output = provision(remaining)
    if not ok:
        return redirect_with_message(f"User removed from config, but deploy failed: {trim_output(output)}", error=True)
    return redirect_with_message(f"Workspace '{user['username']}' deleted.")


def trim_output(output: str, limit: int = 220) -> str:
    compact = " ".join(output.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


if __name__ == "__main__":
    ensure_storage()
    APP.run(host="0.0.0.0", port=8080)

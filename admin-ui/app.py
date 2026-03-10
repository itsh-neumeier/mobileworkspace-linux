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

APP = Flask(__name__)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mobile Web Console Hub Admin</title>
  <style>
    :root {
      --bg: #f3f7f8;
      --paper: #ffffff;
      --paper-soft: #eef5f3;
      --line: #d6e2de;
      --text: #10211d;
      --muted: #4b615b;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --shadow: 0 24px 60px rgba(16, 33, 29, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 24%),
        linear-gradient(180deg, #f3f7f8 0%, #e6efec 100%);
      color: var(--text);
      font-family: "Segoe UI", sans-serif;
      min-height: 100vh;
      padding: 24px;
    }
    .shell {
      width: min(1200px, 100%);
      margin: 0 auto;
    }
    .hero, .panel, .card {
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 28px;
      margin-bottom: 24px;
    }
    .hero h1 { margin: 0 0 10px; font-size: clamp(2rem, 3vw, 3rem); }
    .hero p { margin: 0; color: var(--muted); line-height: 1.6; max-width: 800px; }
    .grid {
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }
    .panel, .card { padding: 24px; }
    h2, h3 { margin-top: 0; }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .badge {
      background: var(--paper-soft);
      color: var(--accent-dark);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.9rem;
      font-weight: 600;
    }
    .flash {
      margin: 0 0 18px;
      padding: 14px 16px;
      border-radius: 16px;
      background: #ecfdf3;
      border: 1px solid #a7f3d0;
      color: #0f5132;
    }
    .flash.error {
      background: #fff3f2;
      border-color: #fecdca;
      color: #7a271a;
    }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 6px;
    }
    input, select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: white;
      margin-bottom: 16px;
      font: inherit;
    }
    .hint { color: var(--muted); font-size: 0.92rem; margin-top: -8px; margin-bottom: 16px; }
    button, .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      font-weight: 700;
      cursor: pointer;
      font: inherit;
      text-decoration: none;
    }
    .button-primary { background: var(--accent); color: white; }
    .button-secondary { background: var(--paper-soft); color: var(--accent-dark); }
    .button-danger { background: #fee4e2; color: var(--danger); }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }
    .list {
      display: grid;
      gap: 16px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }
    .user-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 12px 0;
    }
    .status-active { color: #027a48; }
    .status-disabled { color: #b54708; }
    code {
      background: #eff7f6;
      padding: 2px 8px;
      border-radius: 999px;
      font-family: Consolas, monospace;
    }
    .url-box {
      display: inline-flex;
      padding: 10px 12px;
      border-radius: 14px;
      background: #f5fbfa;
      border: 1px dashed var(--line);
      word-break: break-all;
    }
    .empty {
      color: var(--muted);
      padding: 30px;
      text-align: center;
      border: 1px dashed var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.6);
    }
    @media (max-width: 960px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Admin Panel</h1>
      <p>Create isolated terminal or desktop environments for your users, choose whether they belong on an internet-enabled or internal-only network, and let the panel regenerate the Docker and Caddy configuration for you.</p>
      <div class="meta">
        <span class="badge">Host: {{ domain }}</span>
        <span class="badge">Timezone: {{ timezone }}</span>
        <span class="badge">Users: {{ users|length }}</span>
      </div>
    </section>

    <div class="grid">
      <section class="panel">
        <h2>Create Workspace</h2>
        {% if flash %}
        <div class="flash {{ 'error' if flash_error else '' }}">{{ flash }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('create_user') }}">
          <label for="username">User Name</label>
          <input id="username" name="username" placeholder="ops-team" required>

          <label for="route">Route</label>
          <input id="route" name="route" placeholder="ops-team" required>
          <div class="hint">Will become the URL segment, for example <code>/workspaces/ops-team/</code>.</div>

          <label for="workspace_type">Workspace Type</label>
          <select id="workspace_type" name="workspace_type">
            <option value="terminal">Terminal Workspace</option>
            <option value="desktop">Desktop Workspace (WebVNC)</option>
          </select>

          <label for="network_mode">Network Mode</label>
          <select id="network_mode" name="network_mode">
            <option value="public">Internet Enabled</option>
            <option value="internal">Internal Only</option>
          </select>

          <label for="password">User Password</label>
          <input id="password" name="password" type="password" required>
          <div class="hint">Used for Caddy access protection and, for terminal workspaces, for the internal code-server login.</div>

          <button class="button button-primary" type="submit">Create User Workspace</button>
        </form>
      </section>

      <section class="panel">
        <h2>Provisioned Users</h2>
        {% if users %}
        <div class="list">
          {% for user in users %}
          <article class="card">
            <div class="card-header">
              <div>
                <h3>{{ user.username }}</h3>
                <div class="user-meta">
                  <span class="badge">{{ user.workspace_type }}</span>
                  <span class="badge">{{ user.network_mode }}</span>
                  <span class="badge {{ 'status-active' if user.enabled else 'status-disabled' }}">{{ 'active' if user.enabled else 'disabled' }}</span>
                </div>
              </div>
              <div class="badge">{{ user.container_name }}</div>
            </div>
            <p>Created {{ user.created_at }} and reachable at:</p>
            <div class="url-box">http://{{ domain }}{{ user.route_path }}</div>
            <div class="button-row">
              {% if user.enabled %}
              <form method="post" action="{{ url_for('toggle_user', user_id=user.id, action='disable') }}">
                <button class="button button-secondary" type="submit">Disable</button>
              </form>
              {% else %}
              <form method="post" action="{{ url_for('toggle_user', user_id=user.id, action='enable') }}">
                <button class="button button-primary" type="submit">Enable</button>
              </form>
              {% endif %}
              <form method="post" action="{{ url_for('redeploy_user', user_id=user.id) }}">
                <button class="button button-secondary" type="submit">Redeploy</button>
              </form>
              <form method="post" action="{{ url_for('delete_user', user_id=user.id) }}">
                <button class="button button-danger" type="submit">Delete</button>
              </form>
            </div>
          </article>
          {% endfor %}
        </div>
        {% else %}
        <div class="empty">No workspaces have been created yet.</div>
        {% endif %}
      </section>
    </div>
  </div>
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

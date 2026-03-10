import json
import os
import re
import secrets
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, redirect, render_template_string, request, session, url_for
from passlib.apache import HtpasswdFile
from passlib.hash import bcrypt as passlib_bcrypt


PROJECT_ROOT = Path(os.environ.get("MWC_PROJECT_ROOT", "/workspace"))
USERS_FILE = Path(os.environ.get("MWC_USERS_FILE", PROJECT_ROOT / "users" / "users.json"))
GENERATED_COMPOSE = Path(
    os.environ.get("MWC_GENERATED_COMPOSE", PROJECT_ROOT / "generated" / "docker-compose.users.yml")
)
GENERATED_PROXY = Path(os.environ.get("MWC_GENERATED_PROXY", PROJECT_ROOT / "generated" / "nginx.users.conf"))
GENERATED_AUTH_DIR = Path(os.environ.get("MWC_GENERATED_AUTH_DIR", PROJECT_ROOT / "generated" / "auth"))
BASE_COMPOSE = Path(os.environ.get("MWC_BASE_COMPOSE", PROJECT_ROOT / "base" / "docker-compose.base.yml"))
DOMAIN_OR_HOST = os.environ.get("MWC_DOMAIN_OR_HOST", "localhost")
TIMEZONE = os.environ.get("MWC_TIMEZONE", "Europe/Berlin")
VERSION_FILE = PROJECT_ROOT / "VERSION"
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "dev"
GITHUB_URL = "https://github.com/itsh-neumeier/mobileworkspace-linux"
COMPANY_NAME = "ITSH Neumeier"
COMPANY_URL = "https://neumeier.cloud"
EDGE_NETWORK = os.environ.get("MWC_EDGE_NETWORK", "mobileworkspace_edge")
PUBLIC_NETWORK = os.environ.get("MWC_PUBLIC_NETWORK", "mobileworkspace_public_net")
INTERNAL_NETWORK = os.environ.get("MWC_INTERNAL_NETWORK", "mobileworkspace_internal_net")
USER_PROJECT = os.environ.get("MWC_USER_PROJECT", "mobileworkspace-users")
PROXY_CONTAINER_NAME = os.environ.get("MWC_PROXY_CONTAINER_NAME", "mobileworkspace-admin-ui")
ADMIN_USER_FILE = Path(os.environ.get("MWC_ADMIN_USER_FILE", PROJECT_ROOT / "bootstrap" / "admin-user-name"))
ADMIN_HASH_FILE = Path(os.environ.get("MWC_ADMIN_HASH_FILE", PROJECT_ROOT / "bootstrap" / "admin-password-hash"))
ADMIN_PLAIN_FILE = Path(os.environ.get("MWC_ADMIN_PLAIN_FILE", PROJECT_ROOT / "bootstrap" / "admin-password-plain"))
ADMIN_FORCE_CHANGE_FILE = Path(os.environ.get("MWC_ADMIN_FORCE_CHANGE_FILE", PROJECT_ROOT / "bootstrap" / "admin-force-change"))
ADMIN_INITIAL_PASSWORD = os.environ.get("ADMIN_INITIAL_PASSWORD", "admin")
SESSION_SECRET_FILE = Path(os.environ.get("MWC_SESSION_SECRET_FILE", PROJECT_ROOT / "bootstrap" / "session-secret"))

APP = Flask(__name__)
SUPPORTED_LANGS = ("en", "de")
DEFAULT_LANG = "en"

TRANSLATIONS = {
    "en": {
        "product_name": "Mobile Web Console Hub",
        "admin_console": "Admin Console",
        "subtitle": "Create isolated Linux workspaces with terminal or WebVNC desktop access directly from the browser.",
        "open_admin_panel": "Open Admin Panel",
        "admin_login": "Admin Login",
        "login_help": "Sign in to manage workspaces, user containers, and generated routes.",
        "username": "User name",
        "password": "Password",
        "sign_in": "Sign In",
        "logout": "Logout",
        "create_workspace": "Create Workspace",
        "create_workspace_help": "Add a new user container and publish its route.",
        "route": "Route",
        "route_help": "This becomes the URL segment, for example /workspaces/ops-team/.",
        "workspace_type": "Workspace Type",
        "terminal_workspace": "Terminal Workspace",
        "desktop_workspace": "Desktop Workspace (WebVNC)",
        "network_mode": "Network Mode",
        "internet_enabled": "Internet Enabled",
        "internal_only": "Internal Only",
        "workspace_password": "User Password",
        "workspace_password_help": "Used for workspace access protection and, for terminal workspaces, for the internal code-server login.",
        "create_user_workspace": "Create User Workspace",
        "provisioned_users": "Provisioned Users",
        "managed_workspaces": "managed workspace(s)",
        "created": "Created",
        "disable": "Disable",
        "enable": "Enable",
        "redeploy": "Redeploy",
        "delete": "Delete",
        "no_workspaces": "No workspaces yet",
        "no_workspaces_help": "Create the first user to generate route, storage path, and Docker container automatically.",
        "change_initial_password": "Change Initial Password",
        "change_initial_password_help": "For security reasons, you must set a new admin password before using the dashboard.",
        "current_password": "Current password",
        "new_password": "New password",
        "confirm_new_password": "Confirm new password",
        "update_password": "Update Password",
        "language": "Language",
    },
    "de": {
        "product_name": "Mobile Web Console Hub",
        "admin_console": "Admin Konsole",
        "subtitle": "Erstelle isolierte Linux-Workspaces mit Terminal oder WebVNC-Desktop direkt im Browser.",
        "open_admin_panel": "Admin Panel öffnen",
        "admin_login": "Admin Anmeldung",
        "login_help": "Melde dich an, um Workspaces, Container und Routen zu verwalten.",
        "username": "Benutzername",
        "password": "Passwort",
        "sign_in": "Anmelden",
        "logout": "Abmelden",
        "create_workspace": "Workspace erstellen",
        "create_workspace_help": "Lege einen neuen Benutzercontainer an und veröffentliche seine Route.",
        "route": "Route",
        "route_help": "Wird zum URL-Segment, z. B. /workspaces/ops-team/.",
        "workspace_type": "Workspace-Typ",
        "terminal_workspace": "Terminal Workspace",
        "desktop_workspace": "Desktop Workspace (WebVNC)",
        "network_mode": "Netzwerkmodus",
        "internet_enabled": "Internet verfügbar",
        "internal_only": "Nur intern",
        "workspace_password": "Benutzerpasswort",
        "workspace_password_help": "Wird für den Workspace-Zugriff genutzt und bei Terminal-Workspaces zusätzlich für den internen code-server Login.",
        "create_user_workspace": "Benutzer-Workspace erstellen",
        "provisioned_users": "Bereitgestellte Benutzer",
        "managed_workspaces": "verwaltete Workspaces",
        "created": "Erstellt",
        "disable": "Deaktivieren",
        "enable": "Aktivieren",
        "redeploy": "Neu bereitstellen",
        "delete": "Löschen",
        "no_workspaces": "Noch keine Workspaces",
        "no_workspaces_help": "Erstelle den ersten Benutzer, um Route, Speicher und Container automatisch zu erzeugen.",
        "change_initial_password": "Initiales Passwort ändern",
        "change_initial_password_help": "Aus Sicherheitsgründen musst du zuerst ein neues Admin-Passwort setzen.",
        "current_password": "Aktuelles Passwort",
        "new_password": "Neues Passwort",
        "confirm_new_password": "Neues Passwort bestätigen",
        "update_password": "Passwort aktualisieren",
        "language": "Sprache",
    },
}


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
          <div class="text-uppercase small fw-semibold text-primary mb-2">{{ tr.product_name }}</div>
          <h1 class="display-6 fw-bold mb-1">{{ tr.admin_console }}</h1>
          <p class="text-body-secondary mb-0">{{ tr.subtitle }}</p>
        </div>
        <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
          <select class="form-select form-select-sm rounded-pill" id="langSelect" style="width:auto">
            <option value="en" {{ 'selected' if lang == 'en' else '' }}>🇬🇧 English</option>
            <option value="de" {{ 'selected' if lang == 'de' else '' }}>🇩🇪 Deutsch</option>
          </select>
          <span class="soft-badge"><i class="bi bi-person-badge me-2"></i>{{ admin_username }}</span>
          <button class="btn btn-outline-secondary theme-toggle" type="button" id="themeToggle" aria-label="Toggle theme">
            <i class="bi bi-moon-stars-fill" id="themeIcon"></i>
          </button>
          <form method="post" action="{{ url_for('logout') }}">
            <button class="btn btn-outline-secondary" type="submit">
              <i class="bi bi-box-arrow-right me-2"></i>Logout
            </button>
          </form>
        </div>
      </header>

      <section class="glass-panel hero-card p-4 p-lg-5 mb-4">
        <div class="row g-4 align-items-center">
          <div class="col-lg-8">
            <div class="hero-title fw-bold mb-3">Provision users, routes, and containers from one place.</div>
            <p class="lead text-body-secondary mb-0">Choose terminal or desktop mode, assign a network policy, and let the panel regenerate Docker Compose and nginx routing automatically.</p>
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
                <h2 class="h4 mb-0">{{ tr.create_workspace }}</h2>
                <p class="text-body-secondary mb-0 small">{{ tr.create_workspace_help }}</p>
              </div>
            </div>
            {% if flash %}
            <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
            {% endif %}
            <form method="post" action="{{ url_for('create_user') }}">
              <div class="mb-3">
                <label class="form-label fw-semibold" for="username">{{ tr.username }}</label>
                <input class="form-control" id="username" name="username" placeholder="ops-team" required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="route">{{ tr.route }}</label>
                <input class="form-control" id="route" name="route" placeholder="ops-team" required>
                <div class="form-text">{{ tr.route_help }}</div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="workspace_type">{{ tr.workspace_type }}</label>
                <select class="form-select" id="workspace_type" name="workspace_type">
                  <option value="terminal">{{ tr.terminal_workspace }}</option>
                  <option value="desktop">{{ tr.desktop_workspace }}</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="network_mode">{{ tr.network_mode }}</label>
                <select class="form-select" id="network_mode" name="network_mode">
                  <option value="public">{{ tr.internet_enabled }}</option>
                  <option value="internal">{{ tr.internal_only }}</option>
                </select>
              </div>

              <div class="mb-4">
                <label class="form-label fw-semibold" for="password">{{ tr.workspace_password }}</label>
                <input class="form-control" id="password" name="password" type="password" required>
                <div class="form-text">{{ tr.workspace_password_help }}</div>
              </div>

              <button class="btn btn-primary w-100 py-3 fw-semibold" type="submit">
                <i class="bi bi-rocket-takeoff-fill me-2"></i>{{ tr.create_user_workspace }}
              </button>
            </form>
          </section>
        </div>

        <div class="col-12 col-xl-8">
          <section class="glass-panel section-card p-4 h-100">
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-3">
              <div>
                <h2 class="h4 mb-1">{{ tr.provisioned_users }}</h2>
                <p class="text-body-secondary mb-0">Manage active workspaces, redeploy them, or disable them without editing files manually.</p>
              </div>
              <div class="soft-badge fw-semibold">
                <i class="bi bi-hdd-stack-fill me-2"></i>{{ users|length }} {{ tr.managed_workspaces }}
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
                      <div class="text-body-secondary small mb-3">{{ tr.created }} {{ user.created_at }}</div>
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
                          <i class="bi bi-pause-circle me-2"></i>{{ tr.disable }}
                        </button>
                      </form>
                      {% else %}
                      <form method="post" action="{{ url_for('toggle_user', user_id=user.id, action='enable') }}">
                        <button class="btn btn-primary" type="submit">
                          <i class="bi bi-play-circle me-2"></i>{{ tr.enable }}
                        </button>
                      </form>
                      {% endif %}
                      <form method="post" action="{{ url_for('redeploy_user', user_id=user.id) }}">
                        <button class="btn btn-outline-secondary" type="submit">
                          <i class="bi bi-arrow-repeat me-2"></i>{{ tr.redeploy }}
                        </button>
                      </form>
                      <form method="post" action="{{ url_for('delete_user', user_id=user.id) }}">
                        <button class="btn btn-outline-danger" type="submit">
                          <i class="bi bi-trash3 me-2"></i>{{ tr.delete }}
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
              <h3 class="h5">{{ tr.no_workspaces }}</h3>
              <p class="text-body-secondary mb-0">{{ tr.no_workspaces_help }}</p>
            </div>
            {% endif %}
          </section>
        </div>
      </div>
    </div>

    <footer class="footer-shell py-3">
      <div class="container d-flex flex-column flex-md-row justify-content-between align-items-center gap-2 small">
        <div>{{ tr.product_name }} v{{ version }}</div>
        <div class="d-flex align-items-center gap-3">
          <a class="link-secondary link-offset-2 link-underline-opacity-0 link-underline-opacity-75-hover" href="{{ company_url }}" target="_blank" rel="noopener">neumeier.cloud</a>
          <a class="link-secondary link-offset-2 link-underline-opacity-0 link-underline-opacity-75-hover" href="{{ github_url }}" target="_blank" rel="noopener">GitHub</a>
          <span>&copy; {{ copyright_year }} {{ company_name }}</span>
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
    document.getElementById("langSelect").addEventListener("change", (e) => {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", e.target.value);
      window.location.href = url.toString();
    });
  </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.admin_login }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    body {
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: radial-gradient(circle at top left, rgba(59,130,246,.18), transparent 26%), linear-gradient(180deg, #eef4ff 0%, #dfe9f8 100%);
      font-family: "Segoe UI", sans-serif;
    }
    .login-card {
      width: min(460px, calc(100vw - 2rem));
      border: 0;
      border-radius: 1.75rem;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
      overflow: hidden;
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(14px);
    }
    .brand-badge {
      width: 3rem;
      height: 3rem;
    }
  </style>
</head>
<body>
  <div class="card login-card p-4 p-lg-5">
    <div class="d-flex align-items-center gap-3 mb-4">
      <div class="brand-badge rounded-circle bg-primary-subtle text-primary d-inline-flex align-items-center justify-content-center">
        <i class="bi bi-shield-lock-fill"></i>
      </div>
      <div>
    <div class="text-uppercase small fw-semibold text-primary">{{ tr.product_name }}</div>
        <h1 class="h3 mb-0">{{ tr.admin_login }}</h1>
      </div>
    </div>
    <p class="text-body-secondary mb-4">{{ tr.login_help }}</p>
    <div class="mb-3">
      <label class="form-label fw-semibold">{{ tr.language }}</label>
      <select class="form-select rounded-4" id="langSelect">
        <option value="en" {{ 'selected' if lang == 'en' else '' }}>🇬🇧 English</option>
        <option value="de" {{ 'selected' if lang == 'de' else '' }}>🇩🇪 Deutsch</option>
      </select>
    </div>
    {% if error %}
    <div class="alert alert-danger rounded-4" role="alert">{{ error }}</div>
    {% endif %}
    <form method="post" action="{{ url_for('login') }}">
      <div class="mb-3">
        <label class="form-label fw-semibold" for="username">{{ tr.username }}</label>
        <input class="form-control form-control-lg rounded-4" id="username" name="username" required autofocus>
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold" for="password">{{ tr.password }}</label>
        <input class="form-control form-control-lg rounded-4" id="password" name="password" type="password" required>
      </div>
      <button class="btn btn-primary btn-lg w-100 rounded-pill" type="submit">
        <i class="bi bi-box-arrow-in-right me-2"></i>{{ tr.sign_in }}
      </button>
    </form>
    <div class="mt-4 text-center text-body-secondary small">
      {{ tr.product_name }} v{{ version }} ·
      <a class="link-secondary text-decoration-none" href="{{ company_url }}" target="_blank" rel="noopener">neumeier.cloud</a> ·
      <a class="link-secondary text-decoration-none" href="{{ github_url }}" target="_blank" rel="noopener">GitHub</a> ·
      &copy; {{ copyright_year }} {{ company_name }}
    </div>
  </div>
  <script>
    document.getElementById("langSelect").addEventListener("change", (e) => {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", e.target.value);
      window.location.href = url.toString();
    });
  </script>
</body>
</html>
"""

CHANGE_PASSWORD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.change_initial_password }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: radial-gradient(circle at top left, rgba(59,130,246,.18), transparent 26%), linear-gradient(180deg, #eef4ff 0%, #dfe9f8 100%);
      font-family: "Segoe UI", sans-serif;
    }
    .panel {
      width: min(520px, calc(100vw - 2rem));
      border-radius: 1.5rem;
      border: 0;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
      background: rgba(255,255,255,.95);
    }
  </style>
</head>
<body>
  <div class="card panel p-4 p-lg-5">
    <h1 class="h3 mb-2">{{ tr.change_initial_password }}</h1>
    <p class="text-body-secondary mb-4">{{ tr.change_initial_password_help }}</p>
    <div class="mb-3">
      <label class="form-label fw-semibold">{{ tr.language }}</label>
      <select class="form-select rounded-4" id="langSelect">
        <option value="en" {{ 'selected' if lang == 'en' else '' }}>🇬🇧 English</option>
        <option value="de" {{ 'selected' if lang == 'de' else '' }}>🇩🇪 Deutsch</option>
      </select>
    </div>
    {% if error %}
    <div class="alert alert-danger rounded-4" role="alert">{{ error }}</div>
    {% endif %}
    <form method="post" action="{{ url_for('change_password') }}">
      <div class="mb-3">
        <label class="form-label fw-semibold" for="current_password">{{ tr.current_password }}</label>
        <input class="form-control form-control-lg rounded-4" id="current_password" name="current_password" type="password" required>
      </div>
      <div class="mb-3">
        <label class="form-label fw-semibold" for="new_password">{{ tr.new_password }}</label>
        <input class="form-control form-control-lg rounded-4" id="new_password" name="new_password" type="password" required minlength="10">
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold" for="confirm_password">{{ tr.confirm_new_password }}</label>
        <input class="form-control form-control-lg rounded-4" id="confirm_password" name="confirm_password" type="password" required minlength="10">
      </div>
      <button class="btn btn-primary btn-lg w-100 rounded-pill" type="submit">{{ tr.update_password }}</button>
    </form>
    <div class="mt-4 text-center text-body-secondary small">
      {{ tr.product_name }} v{{ version }} ·
      <a class="link-secondary text-decoration-none" href="{{ company_url }}" target="_blank" rel="noopener">neumeier.cloud</a> ·
      <a class="link-secondary text-decoration-none" href="{{ github_url }}" target="_blank" rel="noopener">GitHub</a> ·
      &copy; {{ copyright_year }} {{ company_name }}
    </div>
  </div>
  <script>
    document.getElementById("langSelect").addEventListener("change", (e) => {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", e.target.value);
      window.location.href = url.toString();
    });
  </script>
</body>
</html>
"""


def ensure_storage() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_COMPOSE.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_AUTH_DIR.mkdir(parents=True, exist_ok=True)
    BASE_COMPOSE.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]\n", encoding="utf-8")
    if not GENERATED_COMPOSE.exists():
        GENERATED_COMPOSE.write_text("services: {}\nvolumes: {}\n", encoding="utf-8")
    if not GENERATED_PROXY.exists():
        GENERATED_PROXY.write_text("# Generated routes for user workspaces will be written here by the admin UI.\n", encoding="utf-8")
    if not BASE_COMPOSE.exists():
        BASE_COMPOSE.write_text(render_base_compose(), encoding="utf-8")
    ensure_admin_credentials()


def ensure_admin_credentials() -> None:
    existing_user = ADMIN_USER_FILE.read_text(encoding="utf-8").strip() if ADMIN_USER_FILE.exists() else ""
    existing_hash = ADMIN_HASH_FILE.read_text(encoding="utf-8").strip() if ADMIN_HASH_FILE.exists() else ""
    if existing_user and existing_hash:
        return

    username = os.environ.get("ADMIN_USER_NAME", "admin").strip() or "admin"
    plain = ADMIN_INITIAL_PASSWORD
    hashed = passlib_bcrypt.using(rounds=12).hash(plain)
    ADMIN_USER_FILE.write_text(username, encoding="utf-8")
    ADMIN_HASH_FILE.write_text(hashed, encoding="utf-8")
    ADMIN_PLAIN_FILE.write_text(plain, encoding="utf-8")
    ADMIN_FORCE_CHANGE_FILE.write_text("1", encoding="utf-8")
    print("==================================================")
    print("Mobile Web Console Hub initial admin credentials")
    print(f"Username: {username}")
    print(f"Password: {plain}")
    print(f"Open: http://{DOMAIN_OR_HOST}/admin/" if DOMAIN_OR_HOST not in {":80", ""} else "Open: http://HOST/admin/")
    print("These credentials were generated on first start.")
    print("Password change is required after the first login.")
    print("==================================================")


def password_change_required() -> bool:
    if not ADMIN_FORCE_CHANGE_FILE.exists():
        return False
    return ADMIN_FORCE_CHANGE_FILE.read_text(encoding="utf-8").strip() == "1"


def current_lang() -> str:
    requested = request.args.get("lang", "").strip().lower()
    if requested in SUPPORTED_LANGS:
        session["lang"] = requested
        return requested
    session_lang = str(session.get("lang", DEFAULT_LANG)).lower()
    if session_lang in SUPPORTED_LANGS:
        return session_lang
    return DEFAULT_LANG


def ensure_session_secret() -> str:
    SESSION_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_SECRET_FILE.exists():
        return SESSION_SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    SESSION_SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


APP.secret_key = ensure_session_secret()


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


def volume_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


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
      - {user["volumes"]["config"]}:/config
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
      - {user["volumes"]["project"]}:/home/coder/project
      - {user["volumes"]["config"]}:/home/coder/.local/share/code-server
    networks:
      - edge
      - {network_name(user)}
"""


def yaml_safe(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def network_name(user: dict) -> str:
    return "internal_net" if user["network_mode"] == "internal" else "public_net"


def actual_network_name(network: str) -> str:
    return {
        "edge": EDGE_NETWORK,
        "public_net": PUBLIC_NETWORK,
        "internal_net": INTERNAL_NETWORK,
    }[network]


def auth_file_for_user(user: dict) -> Path:
    return GENERATED_AUTH_DIR / f"{user['route']}.htpasswd"


def nginx_block(user: dict) -> str:
    auth_file = auth_file_for_user(user)
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    ht = HtpasswdFile(str(auth_file), new=True)
    ht.set_password(user["username"], user["password"])
    ht.save()
    route = user["route_path"].rstrip("/")
    return f"""
location ^~ {route}/ {{
    auth_basic "Mobile Web Console Hub";
    auth_basic_user_file {auth_file.as_posix()};
    proxy_pass http://{user["container_name"]}:{upstream_port(user)};
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}}
"""


def upstream_port(user: dict) -> int:
    return 3000 if user["workspace_type"] == "desktop" else 8080


def write_generated_files(users) -> None:
    enabled = [user for user in users if user.get("enabled", True)]

    if enabled:
        compose_text = "services:\n" + "".join(compose_service_block(user) for user in enabled)
        volume_names = sorted(
            {
                volume_name
                for user in enabled
                for volume_name in user["volumes"].values()
            }
        )
        compose_text += "volumes:\n" + "".join(f"  {volume_name}: {{}}\n" for volume_name in volume_names)
        proxy_text = "".join(nginx_block(user) for user in enabled)
    else:
        compose_text = "services: {}\nvolumes: {}\n"
        proxy_text = "# Generated routes for user workspaces will be written here by the admin UI.\n"

    GENERATED_COMPOSE.write_text(compose_text, encoding="utf-8")
    GENERATED_PROXY.write_text(proxy_text, encoding="utf-8")


def render_base_compose() -> str:
    return (
        "services: {}\n"
        "networks:\n"
        f"  edge:\n    external: true\n    name: {EDGE_NETWORK}\n"
        f"  public_net:\n    external: true\n    name: {PUBLIC_NETWORK}\n"
        f"  internal_net:\n    external: true\n    name: {INTERNAL_NETWORK}\n"
    )


def deploy_stack(users) -> tuple[bool, str]:
    command = [
        "docker",
        "compose",
        "-p",
        USER_PROJECT,
        "-f",
        str(BASE_COMPOSE),
        "-f",
        str(GENERATED_COMPOSE),
        "up",
        "-d",
        "--remove-orphans",
    ]
    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    if result.returncode != 0:
        return False, output or "Stack update failed."

    reload_ok, reload_output = reload_proxy()
    merged_output = "\n".join(part for part in [output, reload_output] if part).strip()
    return reload_ok, merged_output or "Stack updated."


def reload_proxy() -> tuple[bool, str]:
    command = [
        "docker",
        "exec",
        PROXY_CONTAINER_NAME,
        "nginx",
        "-s",
        "reload",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, output or "Proxy reloaded."


def provision(users) -> tuple[bool, str]:
    write_generated_files(users)
    return deploy_stack(users)


def password_hash(plaintext: str) -> str:
    return passlib_bcrypt.using(rounds=12).hash(plaintext)


def verify_admin_auth(username: str, password: str) -> bool:
    if not ADMIN_USER_FILE.exists() or not ADMIN_HASH_FILE.exists():
        return False
    expected_user = ADMIN_USER_FILE.read_text(encoding="utf-8").strip()
    expected_hash = ADMIN_HASH_FILE.read_text(encoding="utf-8").strip()
    return username == expected_user and passlib_bcrypt.verify(password, expected_hash)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin_authenticated"):
            if password_change_required() and request.path != "/admin/change-password/":
                return redirect(url_for("change_password", lang=current_lang()))
            return view(*args, **kwargs)
        query = {"next": request.path, "lang": current_lang()}
        return redirect(url_for("login") + "?" + urlencode(query))

    return wrapped


def current_flash():
    return {
        "flash": request.args.get("message", ""),
        "flash_error": request.args.get("error") == "1",
    }


def redirect_with_message(message: str, error: bool = False):
    return redirect(url_for("index", message=message, error="1" if error else "0", lang=current_lang()))


@APP.route("/")
def root():
    return redirect("/admin/")


@APP.route("/login/", methods=["GET", "POST"])
def login():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if verify_admin_auth(username, password):
            session["admin_authenticated"] = True
            session["admin_username"] = username
            if password_change_required():
                return redirect(url_for("change_password", lang=lang))
            next_url = request.args.get("next") or url_for("index", lang=lang)
            return redirect(next_url)
        error = "Invalid credentials."
    return render_template_string(
        LOGIN_TEMPLATE,
        error=error,
        version=APP_VERSION,
        tr=tr,
        lang=lang,
        github_url=GITHUB_URL,
        company_name=COMPANY_NAME,
        company_url=COMPANY_URL,
        copyright_year=datetime.utcnow().year,
    )


@APP.post("/logout/")
def logout():
    session.clear()
    return redirect(url_for("login", lang=DEFAULT_LANG))


@APP.route("/admin/change-password/", methods=["GET", "POST"])
@login_required
def change_password():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    error = ""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        username = session.get("admin_username", "")
        if not verify_admin_auth(username, current_password):
            error = "Current password is incorrect."
        elif len(new_password) < 10:
            error = "New password must be at least 10 characters."
        elif new_password != confirm_password:
            error = "New passwords do not match."
        else:
            ADMIN_HASH_FILE.write_text(passlib_bcrypt.using(rounds=12).hash(new_password), encoding="utf-8")
            ADMIN_PLAIN_FILE.write_text("", encoding="utf-8")
            ADMIN_FORCE_CHANGE_FILE.write_text("0", encoding="utf-8")
            return redirect_with_message("Admin password changed successfully.")
    return render_template_string(
        CHANGE_PASSWORD_TEMPLATE,
        error=error,
        tr=tr,
        lang=lang,
        version=APP_VERSION,
        github_url=GITHUB_URL,
        company_name=COMPANY_NAME,
        company_url=COMPANY_URL,
        copyright_year=datetime.utcnow().year,
    )


@APP.route("/admin/")
@login_required
def index():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    users = load_users()
    flash_data = current_flash()
    return render_template_string(
        PAGE_TEMPLATE,
        users=users,
        tr=tr,
        lang=lang,
        domain=DOMAIN_OR_HOST,
        timezone=TIMEZONE,
        version=APP_VERSION,
        github_url=GITHUB_URL,
        company_name=COMPANY_NAME,
        company_url=COMPANY_URL,
        admin_username=session.get("admin_username", "admin"),
        copyright_year=datetime.utcnow().year,
        **flash_data,
    )


@APP.post("/admin/users")
@login_required
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
        "volumes": build_volume_map(route, workspace_type),
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
@login_required
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
@login_required
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
@login_required
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


def build_volume_map(route: str, workspace_type: str) -> dict:
    suffix = volume_slug(route)
    volumes = {
        "config": f"mwc-{suffix}-config",
    }
    if workspace_type == "terminal":
        volumes["project"] = f"mwc-{suffix}-project"
    return volumes


if __name__ == "__main__":
    ensure_storage()
    APP.run(host="0.0.0.0", port=8080)

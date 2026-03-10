import json
import os
import re
import secrets
import ssl
import subprocess
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, redirect, render_template_string, request, session, url_for
from passlib.hash import bcrypt as passlib_bcrypt


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def parse_int_or_default(raw: str, default: int, minimum: int, maximum: int, field_name: str) -> int:
    text = (raw or "").strip()
    if not text:
        return default
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
    return value


PROJECT_ROOT = Path(os.environ.get("MWC_PROJECT_ROOT", "/workspace"))
USERS_FILE = Path(os.environ.get("MWC_USERS_FILE", PROJECT_ROOT / "users" / "users.json"))
GENERATED_COMPOSE = Path(
    os.environ.get("MWC_GENERATED_COMPOSE", PROJECT_ROOT / "generated" / "docker-compose.users.yml")
)
GENERATED_PROXY = Path(os.environ.get("MWC_GENERATED_PROXY", PROJECT_ROOT / "generated" / "nginx.users.conf"))
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
ADMIN_AUTO_REPAIR = os.environ.get("ADMIN_AUTO_REPAIR", "true").strip().lower() in {"1", "true", "yes"}
SESSION_SECRET_FILE = Path(os.environ.get("MWC_SESSION_SECRET_FILE", PROJECT_ROOT / "bootstrap" / "session-secret"))
PROXMOX_SETTINGS_FILE = Path(os.environ.get("MWC_PROXMOX_SETTINGS_FILE", PROJECT_ROOT / "bootstrap" / "proxmox-settings.json"))
PROVISIONER_MODE_ENV = os.environ.get("MWC_PROVISIONER_MODE", "docker").strip().lower()
PROXMOX_API_URL = os.environ.get("MWC_PROXMOX_API_URL", "").strip().rstrip("/")
PROXMOX_NODE = os.environ.get("MWC_PROXMOX_NODE", "").strip()
PROXMOX_TOKEN_ID = os.environ.get("MWC_PROXMOX_TOKEN_ID", "").strip()
PROXMOX_TOKEN_SECRET = os.environ.get("MWC_PROXMOX_TOKEN_SECRET", "").strip()
PROXMOX_TEMPLATE_VMID = os.environ.get("MWC_PROXMOX_TEMPLATE_VMID", "").strip()
PROXMOX_VM_CORES = env_int("MWC_PROXMOX_VM_CORES", 2)
PROXMOX_VM_MEMORY_MB = env_int("MWC_PROXMOX_VM_MEMORY_MB", 4096)
PROXMOX_VM_DISK = os.environ.get("MWC_PROXMOX_VM_DISK", "").strip()
PROXMOX_NET_BRIDGE = os.environ.get("MWC_PROXMOX_NET_BRIDGE", "vmbr0").strip()
PROXMOX_VM_START_ON_CREATE = os.environ.get("MWC_PROXMOX_VM_START_ON_CREATE", "true").strip().lower() in {"1", "true", "yes"}
PROXMOX_VERIFY_TLS = os.environ.get("MWC_PROXMOX_VERIFY_TLS", "true").strip().lower() in {"1", "true", "yes"}
PROXMOX_DESKTOP_URL_TEMPLATE = os.environ.get(
    "MWC_PROXMOX_DESKTOP_URL_TEMPLATE",
    "{api_url}/?console=kvm&novnc=1&node={node}&vmid={vmid}",
).strip()

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
        "workspace_name": "Workspace Name",
        "workspace_name_help": "Used for display and URL path. The route is generated automatically.",
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
        "proxmox_api_test": "Test Proxmox API",
        "proxmox_vm_settings": "Proxmox VM Settings",
        "vm_cores": "vCPU Cores",
        "vm_memory_mb": "Memory (MB)",
        "vm_bridge": "Network Bridge",
        "vm_disk": "Disk Override",
        "vm_disk_help": "Optional Proxmox disk config value (for example local-lvm:32).",
        "vm_start_on_create": "Start VM after create",
        "vm_guest_user": "Guest OS User",
        "vm_guest_password": "Guest OS Password",
        "vm_guest_password_help": "If empty, the workspace password is used for cloud-init.",
        "proxmox_backend_settings": "Proxmox Backend Settings",
        "proxmox_api_url": "API URL",
        "proxmox_node": "Node",
        "proxmox_token_id": "Token ID",
        "proxmox_token_secret": "Token Secret",
        "proxmox_template_vmid": "Template VMID",
        "proxmox_verify_tls": "Verify TLS",
        "save_proxmox_settings": "Save Proxmox Settings",
        "provisioner_mode": "Provisioner Mode",
        "docker_mode": "Docker",
        "proxmox_vm_mode": "Proxmox VM",
        "vmid_min": "VMID Min",
        "vmid_max": "VMID Max",
        "dashboard": "Dashboard",
        "settings": "Settings",
        "open_workspace": "Open Workspace",
        "workspace_login": "Workspace Login",
        "workspace_login_help": "Sign in with the workspace user credentials to access this workspace.",
        "invalid_workspace_credentials": "Invalid workspace credentials.",
        "workspace_not_found": "Workspace was not found or is disabled.",
        "menu_dashboard": "Dashboard",
        "menu_workspaces": "Workspaces",
        "menu_users": "Users",
        "menu_proxmox": "Proxmox",
        "health_ok": "healthy",
        "health_corrupt": "corrupt",
        "vm_stats": "VM Stats",
        "proxmox_tasks": "Recent Proxmox Tasks",
        "user_overview": "User Overview",
        "workspace_count": "Workspace Count",
        "reset_user_password": "Reset User Password",
        "workspace_list": "Workspace List",
        "create_workspace_form": "Create Workspace",
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
        "workspace_name": "Workspace Name",
        "workspace_name_help": "Wird für Anzeige und URL verwendet. Die Route wird automatisch erzeugt.",
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
        "proxmox_api_test": "Proxmox API testen",
        "proxmox_vm_settings": "Proxmox VM Einstellungen",
        "vm_cores": "vCPU Kerne",
        "vm_memory_mb": "RAM (MB)",
        "vm_bridge": "Netzwerk-Bridge",
        "vm_disk": "Disk Override",
        "vm_disk_help": "Optionaler Proxmox-Disk-Wert (z. B. local-lvm:32).",
        "vm_start_on_create": "VM nach Erstellung starten",
        "vm_guest_user": "Gast-OS Benutzer",
        "vm_guest_password": "Gast-OS Passwort",
        "vm_guest_password_help": "Wenn leer, wird das Workspace-Passwort für cloud-init genutzt.",
        "proxmox_backend_settings": "Proxmox Backend Einstellungen",
        "proxmox_api_url": "API URL",
        "proxmox_node": "Node",
        "proxmox_token_id": "Token ID",
        "proxmox_token_secret": "Token Secret",
        "proxmox_template_vmid": "Template VMID",
        "proxmox_verify_tls": "TLS prüfen",
        "save_proxmox_settings": "Proxmox Einstellungen speichern",
        "provisioner_mode": "Provisioner Modus",
        "docker_mode": "Docker",
        "proxmox_vm_mode": "Proxmox VM",
        "vmid_min": "VMID Min",
        "vmid_max": "VMID Max",
        "dashboard": "Dashboard",
        "settings": "Einstellungen",
        "open_workspace": "Workspace öffnen",
        "workspace_login": "Workspace Anmeldung",
        "workspace_login_help": "Melde dich mit den Workspace-Benutzerdaten an, um den Workspace zu öffnen.",
        "invalid_workspace_credentials": "Ungültige Workspace-Anmeldedaten.",
        "workspace_not_found": "Workspace wurde nicht gefunden oder ist deaktiviert.",
        "menu_dashboard": "Dashboard",
        "menu_workspaces": "Workspaces",
        "menu_users": "Benutzer",
        "menu_proxmox": "Proxmox",
        "health_ok": "gesund",
        "health_corrupt": "fehlerhaft",
        "vm_stats": "VM Statistik",
        "proxmox_tasks": "Letzte Proxmox Tasks",
        "user_overview": "Benutzerübersicht",
        "workspace_count": "Workspace Anzahl",
        "reset_user_password": "Benutzerpasswort zurücksetzen",
        "workspace_list": "Workspace Liste",
        "create_workspace_form": "Workspace erstellen",
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
        </div>
        <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
          <select class="form-select form-select-sm rounded-pill" id="langSelect" style="width:auto">
            <option value="en" {{ 'selected' if lang == 'en' else '' }}>&#127468;&#127463;</option>
            <option value="de" {{ 'selected' if lang == 'de' else '' }}>&#127465;&#127466;</option>
          </select>
          <a class="btn btn-outline-secondary" href="{{ url_for('index', lang=lang) }}"><i class="bi bi-grid-1x2-fill me-2"></i>{{ tr.menu_dashboard }}</a>
          <a class="btn btn-outline-secondary" href="{{ url_for('workspaces_page', lang=lang) }}"><i class="bi bi-hdd-stack me-2"></i>{{ tr.menu_workspaces }}</a>
          <a class="btn btn-outline-secondary" href="{{ url_for('admin_users_page', lang=lang) }}"><i class="bi bi-people me-2"></i>{{ tr.menu_users }}</a>
          <a class="btn btn-outline-secondary" href="{{ url_for('proxmox_settings_page', lang=lang) }}"><i class="bi bi-hdd-network me-2"></i>{{ tr.menu_proxmox }}</a>
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

      <div class="d-flex flex-wrap gap-2 justify-content-end mb-4">
        <span class="metric-chip fw-semibold">Host: {{ public_host }}</span>
        <span class="metric-chip fw-semibold">Timezone: {{ timezone }}</span>
        <span class="metric-chip fw-semibold">Users: {{ users|length }}</span>
      </div>

      <div class="d-flex justify-content-end mb-3">
        <select class="form-select rounded-pill" id="workspaceViewSelect" style="max-width: 260px;">
          <option value="list" {{ 'selected' if workspace_view == 'list' else '' }}>{{ tr.workspace_list }}</option>
          <option value="create" {{ 'selected' if workspace_view == 'create' else '' }}>{{ tr.create_workspace_form }}</option>
        </select>
      </div>

      <div class="row g-4">
        <div class="col-12" {{ 'style=display:none;' if workspace_view != 'create' else '' }}>
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
            <div class="border rounded-4 p-3 mb-3">
              <div class="fw-semibold mb-2">Proxmox</div>
              <p class="text-body-secondary small mb-3">Backend mode, VM template, VMID range, and server details are now grouped on a dedicated settings page.</p>
              <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('proxmox_settings_page', lang=lang) }}">
                <i class="bi bi-sliders me-2"></i>Proxmox {{ tr.settings }}
              </a>
            </div>
            {% if proxmox_mode %}
            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
              <span class="soft-badge {{ 'status-active' if proxmox_ready_ok else 'status-disabled' }}">
                <i class="bi bi-hdd-network me-2"></i>{{ 'Proxmox API ready' if proxmox_ready_ok else proxmox_ready_message }}
              </span>
              <form method="post" action="{{ url_for('proxmox_test') }}">
                <button class="btn btn-outline-secondary btn-sm" type="submit">
                  <i class="bi bi-plug me-2"></i>{{ tr.proxmox_api_test }}
                </button>
              </form>
            </div>
            {% endif %}
            <form method="post" action="{{ url_for('create_user') }}">
              <div class="mb-3">
                <label class="form-label fw-semibold" for="username">{{ tr.username }}</label>
                <input class="form-control" id="username" name="username" placeholder="ops-team" required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold" for="workspace_name">{{ tr.workspace_name }}</label>
                <input class="form-control" id="workspace_name" name="workspace_name" placeholder="Operations Team" required>
                <div class="form-text">{{ tr.workspace_name_help }}</div>
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

              {% if proxmox_mode %}
              <div class="border rounded-4 p-3 mb-4">
                <div class="fw-semibold mb-3">{{ tr.proxmox_vm_settings }}</div>
                <div class="row g-3">
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_cores">{{ tr.vm_cores }}</label>
                    <input class="form-control" id="proxmox_cores" name="proxmox_cores" type="number" min="1" max="32" value="{{ proxmox_default_cores }}">
                  </div>
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_memory_mb">{{ tr.vm_memory_mb }}</label>
                    <input class="form-control" id="proxmox_memory_mb" name="proxmox_memory_mb" type="number" min="1024" max="262144" value="{{ proxmox_default_memory_mb }}">
                  </div>
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_bridge">{{ tr.vm_bridge }}</label>
                    <input class="form-control" id="proxmox_bridge" name="proxmox_bridge" value="{{ proxmox_default_bridge }}">
                  </div>
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_disk">{{ tr.vm_disk }}</label>
                    <input class="form-control" id="proxmox_disk" name="proxmox_disk" value="{{ proxmox_default_disk }}">
                    <div class="form-text">{{ tr.vm_disk_help }}</div>
                  </div>
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_guest_user">{{ tr.vm_guest_user }}</label>
                    <input class="form-control" id="proxmox_guest_user" name="proxmox_guest_user" placeholder="opsuser">
                  </div>
                  <div class="col-6">
                    <label class="form-label fw-semibold" for="proxmox_guest_password">{{ tr.vm_guest_password }}</label>
                    <input class="form-control" id="proxmox_guest_password" name="proxmox_guest_password" type="password">
                    <div class="form-text">{{ tr.vm_guest_password_help }}</div>
                  </div>
                </div>
                <div class="form-check mt-3">
                  <input class="form-check-input" type="checkbox" value="1" id="proxmox_start_on_create" name="proxmox_start_on_create" {{ 'checked' if proxmox_default_start_on_create else '' }}>
                  <label class="form-check-label" for="proxmox_start_on_create">{{ tr.vm_start_on_create }}</label>
                </div>
              </div>
              {% endif %}

              <button class="btn btn-primary w-100 py-3 fw-semibold" type="submit">
                <i class="bi bi-rocket-takeoff-fill me-2"></i>{{ tr.create_user_workspace }}
              </button>
            </form>
          </section>
        </div>

        <div class="col-12" {{ 'style=display:none;' if workspace_view != 'list' else '' }}>
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
                        <h3 class="h5 mb-0">{{ user.workspace_name or user.username }}</h3>
                        <span class="soft-badge">{{ user.workspace_type }}</span>
                        <span class="soft-badge">{{ user.network_mode }}</span>
                        <span class="soft-badge {{ 'status-active' if user.enabled else 'status-disabled' }}">{{ 'active' if user.enabled else 'disabled' }}</span>
                      </div>
                      <div class="text-body-secondary small mb-3">{{ tr.created }} {{ user.created_at }}</div>
                      {% if user.provider == 'proxmox_vm' %}
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-pc-display me-2"></i>VM {{ user.proxmox.vmid }} @ {{ user.proxmox.node }}
                      </div>
                      <div class="soft-badge mb-3 d-inline-flex align-items-center {{ 'status-disabled' if user.workspace_health == 'corrupt' else 'status-active' }}">
                        <i class="bi bi-heart-pulse me-2"></i>{{ tr.health_corrupt if user.workspace_health == 'corrupt' else tr.health_ok }}
                      </div>
                      {% if user.proxmox_profile %}
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-cpu me-2"></i>{{ user.proxmox_profile.cores }} vCPU · {{ user.proxmox_profile.memory_mb }} MB · {{ user.proxmox_profile.bridge }}
                      </div>
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-person-circle me-2"></i>{{ user.proxmox_profile.guest_user or user.username }}
                      </div>
                      {% endif %}
                      {% if user.proxmox_stats %}
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-speedometer2 me-2"></i>{{ tr.vm_stats }}: CPU {{ user.proxmox_stats.cpu_percent }}% · RAM {{ user.proxmox_stats.mem_used_mb }}/{{ user.proxmox_stats.mem_total_mb }} MB
                      </div>
                      {% endif %}
                      {% if user.proxmox_tasks %}
                      <div class="mt-2 mb-3 small text-body-secondary">{{ tr.proxmox_tasks }}</div>
                      <div class="d-flex flex-wrap gap-2 mb-3">
                        {% for task in user.proxmox_tasks %}
                        <span class="soft-badge">{{ task.type }}: {{ task.status }}</span>
                        {% endfor %}
                      </div>
                      {% endif %}
                      <a class="url-pill px-3 py-2 d-inline-flex align-items-center text-decoration-none" href="{{ user.proxmox.access_url }}" target="_blank" rel="noopener noreferrer">
                        <i class="bi bi-link-45deg me-2"></i>{{ user.proxmox.access_url }}
                      </a>
                      {% else %}
                      <div class="soft-badge mb-3 d-inline-flex align-items-center">
                        <i class="bi bi-box-seam-fill me-2"></i>{{ user.container_name }}
                      </div>
                      <a class="url-pill px-3 py-2 d-inline-flex align-items-center text-decoration-none" href="{{ user.public_url }}" target="_blank" rel="noopener noreferrer">
                        <i class="bi bi-link-45deg me-2"></i>{{ user.public_url }}
                      </a>
                      {% endif %}
                    </div>
                    <div class="d-flex flex-wrap align-items-start justify-content-lg-end gap-2">
                      <a class="btn btn-primary" href="{{ user.public_url }}" target="_blank" rel="noopener noreferrer">
                        <i class="bi bi-box-arrow-up-right me-2"></i>{{ tr.open_workspace }}
                      </a>
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
    const workspaceViewSelect = document.getElementById("workspaceViewSelect");
    if (workspaceViewSelect) {
      workspaceViewSelect.addEventListener("change", (e) => {
        const url = new URL(window.location.href);
        url.searchParams.set("view", e.target.value);
        window.location.href = url.toString();
      });
    }
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
        <option value="en" {{ 'selected' if lang == 'en' else '' }}>&#127468;&#127463;</option>
        <option value="de" {{ 'selected' if lang == 'de' else '' }}>&#127465;&#127466;</option>
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
        <option value="en" {{ 'selected' if lang == 'en' else '' }}>&#127468;&#127463;</option>
        <option value="de" {{ 'selected' if lang == 'de' else '' }}>&#127465;&#127466;</option>
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

USER_LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.workspace_login }}</title>
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
    <h1 class="h3 mb-2">{{ tr.workspace_login }}</h1>
    <p class="text-body-secondary mb-4">{{ tr.workspace_login_help }}</p>
    {% if error %}
    <div class="alert alert-danger rounded-4" role="alert">{{ error }}</div>
    {% endif %}
    <form method="post" action="{{ url_for('user_login', lang=lang) }}">
      <div class="mb-3">
        <label class="form-label fw-semibold" for="username">{{ tr.username }}</label>
        <input class="form-control form-control-lg rounded-4" id="username" name="username" required autofocus>
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold" for="password">{{ tr.password }}</label>
        <input class="form-control form-control-lg rounded-4" id="password" name="password" type="password" required>
      </div>
      <button class="btn btn-primary btn-lg w-100 rounded-pill" type="submit">{{ tr.sign_in }}</button>
    </form>
  </div>
</body>
</html>
"""

USER_DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - Workspaces</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-5">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div>
        <div class="text-uppercase small fw-semibold text-primary">{{ tr.product_name }}</div>
        <h1 class="h3 mb-0">Client Portal · {{ session_user }}</h1>
      </div>
      <div class="d-flex gap-2">
        <a class="btn btn-outline-secondary" href="{{ url_for('user_change_password', lang=lang) }}">{{ tr.update_password }}</a>
        <form method="post" action="{{ url_for('user_logout', lang=lang) }}">
          <button class="btn btn-outline-secondary" type="submit">{{ tr.logout }}</button>
        </form>
      </div>
    </div>
    {% if flash %}
    <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
    {% endif %}
    <div class="row g-3">
      {% for user in users %}
      <div class="col-12">
        <div class="card border-0 shadow-sm rounded-4">
          <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div>
              <div class="fw-semibold">{{ user.workspace_name or user.route_path }}</div>
              <div class="text-body-secondary small">{{ user.workspace_type }} · {{ user.network_mode }}</div>
            </div>
            <a class="btn btn-primary" href="{{ user.public_url }}" target="_blank" rel="noopener noreferrer">{{ tr.open_workspace }}</a>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
</body>
</html>
"""

USER_CHANGE_PASSWORD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.update_password }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-5">
    <div class="card border-0 shadow-sm rounded-4 mx-auto" style="max-width: 620px;">
      <div class="card-body p-4 p-lg-5">
        <h1 class="h4 mb-3">{{ tr.update_password }}</h1>
        {% if error %}
        <div class="alert alert-danger rounded-4" role="alert">{{ error }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('user_change_password', lang=lang) }}">
          <div class="mb-3">
            <label class="form-label fw-semibold">{{ tr.current_password }}</label>
            <input class="form-control" name="current_password" type="password" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-semibold">{{ tr.new_password }}</label>
            <input class="form-control" name="new_password" type="password" required minlength="8">
          </div>
          <div class="mb-4">
            <label class="form-label fw-semibold">{{ tr.confirm_new_password }}</label>
            <input class="form-control" name="confirm_password" type="password" required minlength="8">
          </div>
          <div class="d-flex gap-2">
            <button class="btn btn-primary" type="submit">{{ tr.update_password }}</button>
            <a class="btn btn-outline-secondary" href="{{ url_for('user_dashboard', lang=lang) }}">{{ tr.menu_workspaces }}</a>
          </div>
        </form>
      </div>
    </div>
  </div>
</body>
</html>
"""

PROXMOX_SETTINGS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - Proxmox {{ tr.settings }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-4 py-lg-5">
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-4">
      <div>
        <div class="text-uppercase small fw-semibold text-primary">{{ tr.product_name }}</div>
        <h1 class="h3 mb-0">Proxmox {{ tr.settings }}</h1>
      </div>
      <div class="d-flex gap-2">
        <a class="btn btn-outline-secondary" href="{{ url_for('index', lang=lang) }}"><i class="bi bi-grid-1x2-fill me-2"></i>{{ tr.menu_dashboard }}</a>
        <a class="btn btn-outline-secondary" href="{{ url_for('workspaces_page', lang=lang) }}"><i class="bi bi-hdd-stack me-2"></i>{{ tr.menu_workspaces }}</a>
        <a class="btn btn-outline-secondary" href="{{ url_for('admin_users_page', lang=lang) }}"><i class="bi bi-people me-2"></i>{{ tr.menu_users }}</a>
        <form method="post" action="{{ url_for('logout') }}">
          <button class="btn btn-outline-secondary" type="submit"><i class="bi bi-box-arrow-right me-2"></i>{{ tr.logout }}</button>
        </form>
      </div>
    </div>
    {% if flash %}
    <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
    {% endif %}
    <div class="row g-3 mb-4">
      <div class="col-12 col-md-4"><div class="card border-0 shadow-sm rounded-4"><div class="card-body"><div class="text-body-secondary small">CPU</div><div class="h4 mb-0">{{ usage.cpu_percent if usage else 0 }}%</div></div></div></div>
      <div class="col-12 col-md-4"><div class="card border-0 shadow-sm rounded-4"><div class="card-body"><div class="text-body-secondary small">RAM</div><div class="h4 mb-0">{{ usage.memory_used_gb if usage else 0 }} / {{ usage.memory_total_gb if usage else 0 }} GB</div></div></div></div>
      <div class="col-12 col-md-4"><div class="card border-0 shadow-sm rounded-4"><div class="card-body"><div class="text-body-secondary small">Disk</div><div class="h4 mb-0">{{ usage.disk_used_gb if usage else 0 }} / {{ usage.disk_total_gb if usage else 0 }} GB</div></div></div></div>
    </div>
    <div class="card border-0 shadow-sm rounded-4">
      <div class="card-body p-4">
        <form method="post" action="{{ url_for('save_proxmox_settings_route') }}">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label fw-semibold" for="cfg_provisioner_mode">{{ tr.provisioner_mode }}</label>
              <select class="form-select" id="cfg_provisioner_mode" name="cfg_provisioner_mode">
                <option value="docker" {{ 'selected' if proxmox_cfg.provisioner_mode == 'docker' else '' }}>{{ tr.docker_mode }}</option>
                <option value="proxmox_vm" {{ 'selected' if proxmox_cfg.provisioner_mode == 'proxmox_vm' else '' }}>{{ tr.proxmox_vm_mode }}</option>
              </select>
            </div>
            <div class="col-12"><label class="form-label fw-semibold" for="cfg_api_url">{{ tr.proxmox_api_url }}</label><input class="form-control" id="cfg_api_url" name="cfg_api_url" value="{{ proxmox_cfg.api_url }}" placeholder="https://proxmox.local:8006"></div>
            <div class="col-6"><label class="form-label fw-semibold" for="cfg_node">{{ tr.proxmox_node }}</label><input class="form-control" id="cfg_node" name="cfg_node" value="{{ proxmox_cfg.node }}"></div>
            <div class="col-6"><label class="form-label fw-semibold" for="cfg_template_vmid">{{ tr.proxmox_template_vmid }}</label><input class="form-control" id="cfg_template_vmid" name="cfg_template_vmid" value="{{ proxmox_cfg.template_vmid }}"></div>
            <div class="col-6"><label class="form-label fw-semibold" for="cfg_vmid_min">{{ tr.vmid_min }}</label><input class="form-control" id="cfg_vmid_min" name="cfg_vmid_min" value="{{ proxmox_cfg.vmid_min }}"></div>
            <div class="col-6"><label class="form-label fw-semibold" for="cfg_vmid_max">{{ tr.vmid_max }}</label><input class="form-control" id="cfg_vmid_max" name="cfg_vmid_max" value="{{ proxmox_cfg.vmid_max }}"></div>
            <div class="col-12"><label class="form-label fw-semibold" for="cfg_token_id">{{ tr.proxmox_token_id }}</label><input class="form-control" id="cfg_token_id" name="cfg_token_id" value="{{ proxmox_cfg.token_id }}"></div>
            <div class="col-12"><label class="form-label fw-semibold" for="cfg_token_secret">{{ tr.proxmox_token_secret }}</label><input class="form-control" id="cfg_token_secret" name="cfg_token_secret" type="password" value="{{ proxmox_cfg.token_secret }}"></div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="cfg_verify_tls" name="cfg_verify_tls" value="1" {{ 'checked' if proxmox_cfg.verify_tls else '' }}>
                <label class="form-check-label" for="cfg_verify_tls">{{ tr.proxmox_verify_tls }}</label>
              </div>
            </div>
          </div>
          <div class="d-flex gap-2 mt-3">
            <button class="btn btn-primary" type="submit"><i class="bi bi-save me-2"></i>{{ tr.save_proxmox_settings }}</button>
            <button class="btn btn-outline-secondary" formaction="{{ url_for('proxmox_test') }}" formmethod="post" type="submit"><i class="bi bi-plug me-2"></i>{{ tr.proxmox_api_test }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.menu_dashboard }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-4 py-lg-5">
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-4">
      <div>
        <div class="text-uppercase small fw-semibold text-primary">{{ tr.product_name }}</div>
        <h1 class="h3 mb-0">{{ tr.menu_dashboard }}</h1>
      </div>
      <form method="post" action="{{ url_for('logout') }}">
        <button class="btn btn-outline-secondary" type="submit"><i class="bi bi-box-arrow-right me-2"></i>{{ tr.logout }}</button>
      </form>
    </div>
    {% if flash %}
    <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
    {% endif %}
    <div class="row g-3">
      <div class="col-12 col-md-4">
        <a class="card border-0 shadow-sm rounded-4 text-decoration-none text-body" href="{{ url_for('workspaces_page', lang=lang) }}">
          <div class="card-body">
            <div class="text-body-secondary small">{{ tr.menu_workspaces }}</div>
            <div class="h4 mb-0">{{ users|length }}</div>
          </div>
        </a>
      </div>
      <div class="col-12 col-md-4">
        <a class="card border-0 shadow-sm rounded-4 text-decoration-none text-body" href="{{ url_for('admin_users_page', lang=lang) }}">
          <div class="card-body">
            <div class="text-body-secondary small">{{ tr.menu_users }}</div>
            <div class="h4 mb-0">{{ unique_user_count }}</div>
          </div>
        </a>
      </div>
      <div class="col-12 col-md-4">
        <a class="card border-0 shadow-sm rounded-4 text-decoration-none text-body" href="{{ url_for('proxmox_settings_page', lang=lang) }}">
          <div class="card-body">
            <div class="text-body-secondary small">{{ tr.menu_proxmox }}</div>
            <div class="h4 mb-1 {{ 'text-success' if proxmox_mode else 'text-danger' }}">{{ '✓' if proxmox_mode else '✕' }}</div>
            {% if proxmox_summary %}
            <div class="small text-body-secondary">
              CPU {{ proxmox_summary.cpu_percent }}% · RAM {{ proxmox_summary.memory_used_gb }}/{{ proxmox_summary.memory_total_gb }} GB · Disk {{ proxmox_summary.disk_used_gb }}/{{ proxmox_summary.disk_total_gb }} GB
            </div>
            {% endif %}
          </div>
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""

ADMIN_USERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ tr.product_name }} - {{ tr.menu_users }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-4 py-lg-5">
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-4">
      <div>
        <div class="text-uppercase small fw-semibold text-primary">{{ tr.product_name }}</div>
        <h1 class="h3 mb-0">{{ tr.menu_users }}</h1>
      </div>
      <div class="d-flex gap-2">
        <a class="btn btn-outline-secondary" href="{{ url_for('index', lang=lang) }}"><i class="bi bi-grid-1x2-fill me-2"></i>{{ tr.menu_dashboard }}</a>
        <a class="btn btn-outline-secondary" href="{{ url_for('workspaces_page', lang=lang) }}"><i class="bi bi-hdd-stack me-2"></i>{{ tr.menu_workspaces }}</a>
      </div>
    </div>
    {% if flash %}
    <div class="alert {{ 'alert-danger' if flash_error else 'alert-success' }} rounded-4" role="alert">{{ flash }}</div>
    {% endif %}
    <div class="card border-0 shadow-sm rounded-4 mb-4">
      <div class="card-body p-4">
        <h2 class="h5 mb-3">{{ tr.reset_user_password }}</h2>
        <form method="post" action="{{ url_for('admin_reset_user_password') }}">
          <div class="row g-3">
            <div class="col-12 col-md-6">
              <label class="form-label fw-semibold">{{ tr.username }}</label>
              <input class="form-control" name="username" required>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-semibold">{{ tr.password }}</label>
              <input class="form-control" name="password" type="password" required>
            </div>
          </div>
          <button class="btn btn-primary mt-3" type="submit">{{ tr.reset_user_password }}</button>
        </form>
      </div>
    </div>
    <div class="card border-0 shadow-sm rounded-4">
      <div class="card-body p-4">
        <h2 class="h5 mb-3">{{ tr.user_overview }}</h2>
        <div class="table-responsive">
          <table class="table align-middle">
            <thead>
              <tr>
                <th>{{ tr.username }}</th>
                <th>{{ tr.workspace_count }}</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {% for item in user_rows %}
              <tr>
                <td>{{ item.username }}</td>
                <td>{{ item.workspace_count }}</td>
                <td>{{ item.status_text }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


def ensure_storage() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_COMPOSE.parent.mkdir(parents=True, exist_ok=True)
    BASE_COMPOSE.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROXMOX_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]\n", encoding="utf-8")
    if not GENERATED_COMPOSE.exists():
        GENERATED_COMPOSE.write_text("services: {}\nvolumes: {}\n", encoding="utf-8")
    if not GENERATED_PROXY.exists():
        GENERATED_PROXY.write_text("# Generated routes for user workspaces will be written here by the admin UI.\n", encoding="utf-8")
    if not BASE_COMPOSE.exists():
        BASE_COMPOSE.write_text(render_base_compose(), encoding="utf-8")
    if not PROXMOX_SETTINGS_FILE.exists():
        PROXMOX_SETTINGS_FILE.write_text("{}\n", encoding="utf-8")
    if proxmox_enabled():
        clear_generated_proxy_files()
    ensure_admin_credentials()


def ensure_admin_credentials() -> None:
    existing_user = ADMIN_USER_FILE.read_text(encoding="utf-8").strip() if ADMIN_USER_FILE.exists() else ""
    existing_hash = ADMIN_HASH_FILE.read_text(encoding="utf-8").strip() if ADMIN_HASH_FILE.exists() else ""
    bootstrap_plain = ADMIN_PLAIN_FILE.read_text(encoding="utf-8").strip() if ADMIN_PLAIN_FILE.exists() else ""
    force_change = ADMIN_FORCE_CHANGE_FILE.read_text(encoding="utf-8").strip() if ADMIN_FORCE_CHANGE_FILE.exists() else "0"
    if existing_user and existing_hash:
        if not ADMIN_AUTO_REPAIR:
            return
        hash_valid = passlib_bcrypt.identify(existing_hash)
        if hash_valid and bootstrap_plain:
            if passlib_bcrypt.verify(bootstrap_plain, existing_hash):
                return
            print("Detected mismatch between bootstrap plain password and hash, auto-repairing.")
        elif hash_valid and force_change != "1":
            return
        elif hash_valid and force_change == "1" and not bootstrap_plain:
            print("Detected bootstrap state without plain password, restoring initial admin credentials.")
        else:
            print("Detected invalid admin hash, auto-repairing bootstrap credentials.")

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


def docker_container_names() -> set[str]:
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def reconcile_workspace_state(users: list[dict]) -> tuple[list[dict], str]:
    if not users:
        return users, ""
    changed = False
    notes: list[str] = []

    proxmox_users = [user for user in users if user.get("provider") == "proxmox_vm"]
    if proxmox_users:
        settings = proxmox_settings()
        ok, message = proxmox_ready(settings)
        if ok:
            try:
                vm_items = proxmox_request("GET", "/cluster/resources", settings, {"type": "vm"})
                vm_map: dict[int, str] = {}
                if isinstance(vm_items, list):
                    for item in vm_items:
                        try:
                            vm_map[int(item.get("vmid"))] = str(item.get("status", "unknown"))
                        except Exception:
                            continue
                missing_count = 0
                for user in proxmox_users:
                    info = user.setdefault("proxmox", {})
                    vmid_raw = info.get("vmid")
                    node = str(info.get("node") or settings.get("node", "")).strip()
                    try:
                        vmid = int(vmid_raw)
                    except Exception:
                        continue
                    exists = vmid in vm_map
                    status = vm_map.get(vmid, "missing")
                    if info.get("exists") != exists or info.get("status") != status:
                        info["exists"] = exists
                        info["status"] = status
                        changed = True
                    desired_health = "ok" if exists else "corrupt"
                    if user.get("workspace_health") != desired_health:
                        user["workspace_health"] = desired_health
                        changed = True
                    if exists:
                        access_url = proxmox_vm_access_url(vmid, node)
                        if info.get("access_url") != access_url:
                            info["access_url"] = access_url
                            changed = True
                    else:
                        missing_count += 1
                if missing_count:
                    notes.append(f"Detected {missing_count} Proxmox workspace VM(s) that no longer exist.")
            except Exception as exc:
                notes.append(f"Proxmox sync failed: {trim_output(str(exc))}")
        else:
            notes.append(message)

    docker_users = [user for user in users if user.get("provider", "docker") == "docker"]
    if docker_users:
        names = docker_container_names()
        if names:
            missing_count = 0
            for user in docker_users:
                exists = user.get("container_name") in names
                if user.get("container_exists") != exists:
                    user["container_exists"] = exists
                    changed = True
                desired_health = "ok" if exists else "corrupt"
                if user.get("workspace_health") != desired_health:
                    user["workspace_health"] = desired_health
                    changed = True
                if not exists:
                    missing_count += 1
            if missing_count:
                notes.append(f"Detected {missing_count} Docker workspace container(s) missing.")

    if changed:
        save_users(users)
    return users, " ".join(notes)


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


def guest_username(value: str, fallback: str) -> str:
    candidate = (value or "").strip().lower()
    if not candidate:
        candidate = re.sub(r"[^a-z0-9_-]+", "-", fallback.strip().lower()).strip("-")
    if not candidate:
        candidate = "admin"
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", candidate):
        raise ValueError("Guest OS user must be 1-32 chars and match Linux naming rules.")
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


def nginx_block(user: dict) -> str:
    route = user["route_path"].rstrip("/")
    return f"""
location ^~ {route}/ {{
    auth_request /user/auth/{user["route"]}/;
    error_page 401 =302 /client/login/?next=$request_uri;
    set $workspace_upstream http://{user["container_name"]}:{upstream_port(user)};
    proxy_pass $workspace_upstream;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}}
"""


def proxmox_tunnel_block(settings: dict) -> str:
    api_url = str(settings.get("api_url", "")).strip()
    if not api_url:
        return ""
    parsed = urlparse(api_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    verify_tls = "on" if settings.get("verify_tls", True) else "off"
    upstream = api_url.rstrip("/") + "/"
    host_header = parsed.netloc
    return f"""
location ^~ /pve/ {{
    proxy_pass {upstream};
    proxy_http_version 1.1;
    proxy_ssl_server_name on;
    proxy_ssl_verify {verify_tls};
    proxy_set_header Host {host_header};
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
    docker_users = [user for user in enabled if user.get("provider", "docker") == "docker"]
    proxy_parts = []
    tunnel = proxmox_tunnel_block(proxmox_settings())
    if tunnel:
        proxy_parts.append(tunnel)

    if docker_users:
        compose_text = "services:\n" + "".join(compose_service_block(user) for user in docker_users)
        volume_names = sorted(
            {
                volume_name
                for user in docker_users
                for volume_name in user["volumes"].values()
            }
        )
        compose_text += "volumes:\n" + "".join(f"  {volume_name}: {{}}\n" for volume_name in volume_names)
        proxy_parts.append("".join(nginx_block(user) for user in docker_users))
    else:
        compose_text = "services: {}\nvolumes: {}\n"
        if not tunnel:
            proxy_parts.append("# Generated routes for user workspaces will be written here by the admin UI.\n")

    proxy_text = "".join(proxy_parts)

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
    if proxmox_enabled():
        clear_generated_proxy_files()
        return True, "Proxmox VM mode active."
    write_generated_files(users)
    return deploy_stack(users)


def clear_generated_proxy_files() -> None:
    tunnel = proxmox_tunnel_block(proxmox_settings())
    content = tunnel or "# Generated routes for user workspaces will be written here by the admin UI.\n"
    GENERATED_PROXY.write_text(content, encoding="utf-8")
    GENERATED_COMPOSE.write_text("services: {}\nvolumes: {}\n", encoding="utf-8")


def proxmox_enabled() -> bool:
    return current_provisioner_mode() == "proxmox_vm"


def proxmox_default_settings() -> dict:
    return {
        "provisioner_mode": PROVISIONER_MODE_ENV if PROVISIONER_MODE_ENV in {"docker", "proxmox_vm"} else "docker",
        "api_url": PROXMOX_API_URL,
        "node": PROXMOX_NODE,
        "token_id": PROXMOX_TOKEN_ID,
        "token_secret": PROXMOX_TOKEN_SECRET,
        "template_vmid": PROXMOX_TEMPLATE_VMID,
        "vm_cores": PROXMOX_VM_CORES,
        "vm_memory_mb": PROXMOX_VM_MEMORY_MB,
        "vm_disk": PROXMOX_VM_DISK,
        "net_bridge": PROXMOX_NET_BRIDGE,
        "vm_start_on_create": PROXMOX_VM_START_ON_CREATE,
        "verify_tls": PROXMOX_VERIFY_TLS,
        "desktop_url_template": PROXMOX_DESKTOP_URL_TEMPLATE,
        "vmid_min": "",
        "vmid_max": "",
    }


def proxmox_settings() -> dict:
    defaults = proxmox_default_settings()
    try:
        stored = json.loads(PROXMOX_SETTINGS_FILE.read_text(encoding="utf-8")) if PROXMOX_SETTINGS_FILE.exists() else {}
    except json.JSONDecodeError:
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    merged = defaults.copy()
    merged.update(stored)
    merged["provisioner_mode"] = str(merged.get("provisioner_mode", "docker")).strip().lower()
    if merged["provisioner_mode"] not in {"docker", "proxmox_vm"}:
        merged["provisioner_mode"] = "docker"
    merged["api_url"] = str(merged.get("api_url", "")).strip().rstrip("/")
    merged["node"] = str(merged.get("node", "")).strip()
    merged["token_id"] = str(merged.get("token_id", "")).strip()
    merged["token_secret"] = str(merged.get("token_secret", "")).strip()
    merged["template_vmid"] = str(merged.get("template_vmid", "")).strip()
    merged["vm_cores"] = parse_int_or_default(str(merged.get("vm_cores", PROXMOX_VM_CORES)), PROXMOX_VM_CORES, 1, 128, "VM cores")
    merged["vm_memory_mb"] = parse_int_or_default(
        str(merged.get("vm_memory_mb", PROXMOX_VM_MEMORY_MB)),
        PROXMOX_VM_MEMORY_MB,
        512,
        1048576,
        "VM memory",
    )
    merged["vm_disk"] = str(merged.get("vm_disk", "")).strip()
    merged["net_bridge"] = str(merged.get("net_bridge", PROXMOX_NET_BRIDGE)).strip() or PROXMOX_NET_BRIDGE
    merged["vm_start_on_create"] = str(merged.get("vm_start_on_create", "true")).strip().lower() in {"1", "true", "yes"}
    merged["verify_tls"] = str(merged.get("verify_tls", "true")).strip().lower() in {"1", "true", "yes"}
    merged["desktop_url_template"] = str(merged.get("desktop_url_template", PROXMOX_DESKTOP_URL_TEMPLATE)).strip()
    merged["vmid_min"] = str(merged.get("vmid_min", "")).strip()
    merged["vmid_max"] = str(merged.get("vmid_max", "")).strip()
    return merged


def save_proxmox_settings(values: dict) -> None:
    PROXMOX_SETTINGS_FILE.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")


def current_provisioner_mode() -> str:
    return proxmox_settings().get("provisioner_mode", "docker")


def proxmox_ready(settings: dict | None = None) -> tuple[bool, str]:
    config = settings or proxmox_settings()
    required = {
        "api_url": config.get("api_url", ""),
        "node": config.get("node", ""),
        "token_id": config.get("token_id", ""),
        "token_secret": config.get("token_secret", ""),
        "template_vmid": config.get("template_vmid", ""),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        return False, f"Missing Proxmox configuration: {', '.join(missing)}"
    return True, ""


def proxmox_headers(settings: dict, has_payload: bool = False) -> dict:
    headers = {
        "Authorization": f"PVEAPIToken={settings['token_id']}={settings['token_secret']}",
    }
    if has_payload:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    return headers


def proxmox_request(method: str, path: str, settings: dict, data: dict | None = None) -> dict:
    method_upper = method.upper()
    query = ""
    payload = None
    if data is not None and method_upper in {"GET", "DELETE"}:
        query = "?" + urlencode(data)
    elif data is not None:
        payload = urlencode(data).encode("utf-8")
    req = Request(
        url=f"{settings['api_url']}/api2/json{path}{query}",
        data=payload,
        method=method,
        headers=proxmox_headers(settings, has_payload=payload is not None),
    )
    context = ssl.create_default_context()
    if not settings.get("verify_tls", True):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with urlopen(req, timeout=30, context=context) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Connection failed for {path}: {exc.reason}") from exc
    parsed = json.loads(body)
    return parsed.get("data", {})


def proxmox_request_retry(method: str, path: str, settings: dict, data: dict | None = None, attempts: int = 12) -> dict:
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            return proxmox_request(method, path, settings, data)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            msg = str(exc)
            if "can't lock file" not in msg and "got timeout" not in msg:
                raise
            time.sleep(5)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Proxmox request retry failed without explicit error.")


def proxmox_wait_task(settings: dict, node: str, upid: str, timeout_seconds: int = 600) -> tuple[bool, str]:
    start = time.time()
    while (time.time() - start) < timeout_seconds:
        data = proxmox_request("GET", f"/nodes/{node}/tasks/{upid}/status", settings)
        status = str(data.get("status", "")).lower()
        if status == "stopped":
            exitstatus = str(data.get("exitstatus", ""))
            if exitstatus == "OK":
                return True, "OK"
            return False, exitstatus or "Task failed"
        time.sleep(2)
    return False, "timeout"


def proxmox_next_vmid(settings: dict) -> int:
    value = proxmox_request("GET", "/cluster/nextid", settings)
    return int(value)


def proxmox_used_vmids(settings: dict) -> set[int]:
    items = proxmox_request("GET", "/cluster/resources", settings, {"type": "vm"})
    used: set[int] = set()
    if isinstance(items, list):
        for item in items:
            try:
                used.add(int(item.get("vmid")))
            except Exception:
                continue
    return used


def proxmox_pick_vmid(settings: dict) -> int:
    min_raw = str(settings.get("vmid_min", "")).strip()
    max_raw = str(settings.get("vmid_max", "")).strip()
    if not min_raw and not max_raw:
        return proxmox_next_vmid(settings)

    vmid_min = parse_int_or_default(min_raw, 100, 1, 999999999, "VMID Min")
    vmid_max = parse_int_or_default(max_raw, 999999999, 1, 999999999, "VMID Max")
    if vmid_max < vmid_min:
        raise ValueError("VMID Max must be greater than or equal to VMID Min.")

    used = proxmox_used_vmids(settings)
    for candidate in range(vmid_min, vmid_max + 1):
        if candidate not in used:
            return candidate
    raise RuntimeError(f"No free VMID available in range {vmid_min}-{vmid_max}.")


def proxmox_vm_access_url(vmid: int, node: str) -> str:
    return f"{public_scheme()}://{public_host_display()}/pve/?console=kvm&novnc=1&node={node}&vmid={vmid}"


def proxmox_health_check() -> tuple[bool, str]:
    settings = proxmox_settings()
    ok, message = proxmox_ready(settings)
    if not ok:
        return False, message
    try:
        next_id = proxmox_next_vmid(settings)
        proxmox_request("GET", f"/nodes/{settings['node']}/qemu/{settings['template_vmid']}/status/current", settings)
        return True, f"Proxmox API reachable (next VMID {next_id}, template {settings['template_vmid']} accessible)."
    except Exception as exc:
        return False, f"Proxmox API test failed: {exc}"


def proxmox_node_usage() -> dict:
    settings = proxmox_settings()
    ok, _ = proxmox_ready(settings)
    if not ok:
        return {}
    try:
        raw = proxmox_request("GET", f"/nodes/{settings['node']}/status", settings)
    except Exception:
        return {}
    memory = raw.get("memory", {}) if isinstance(raw, dict) else {}
    rootfs = raw.get("rootfs", {}) if isinstance(raw, dict) else {}
    cpu_used = float(raw.get("cpu", 0.0)) * 100.0
    mem_total = int(memory.get("total", 0))
    mem_used = int(memory.get("used", 0))
    disk_total = int(rootfs.get("total", 0))
    disk_used = int(rootfs.get("used", 0))
    return {
        "cpu_percent": round(cpu_used, 1),
        "memory_used_gb": round(mem_used / (1024**3), 2),
        "memory_total_gb": round(mem_total / (1024**3), 2),
        "disk_used_gb": round(disk_used / (1024**3), 2),
        "disk_total_gb": round(disk_total / (1024**3), 2),
    }


def proxmox_vm_stats(settings: dict, node: str, vmid: int) -> dict:
    try:
        raw = proxmox_request("GET", f"/nodes/{node}/qemu/{vmid}/status/current", settings)
    except Exception:
        return {}
    cpu = float(raw.get("cpu", 0.0)) * 100.0
    mem = int(raw.get("mem", 0))
    maxmem = int(raw.get("maxmem", 0))
    return {
        "cpu_percent": round(cpu, 1),
        "mem_used_mb": int(mem / (1024 * 1024)),
        "mem_total_mb": int(maxmem / (1024 * 1024)),
    }


def proxmox_vm_recent_tasks(settings: dict, node: str, vmid: int, limit: int = 5) -> list[dict]:
    try:
        raw = proxmox_request("GET", f"/nodes/{node}/tasks", settings, {"limit": limit, "vmid": vmid})
    except Exception:
        return []
    items: list[dict] = []
    if isinstance(raw, list):
        for task in raw[:limit]:
            if not isinstance(task, dict):
                continue
            items.append(
                {
                    "type": str(task.get("type", "task")),
                    "status": str(task.get("status", "unknown")),
                }
            )
    return items


def enrich_proxmox_workspace_insights(users: list[dict]) -> list[dict]:
    if not users:
        return users
    settings = proxmox_settings()
    ok, _ = proxmox_ready(settings)
    if not ok:
        return users
    for user in users:
        if user.get("provider") != "proxmox_vm":
            continue
        info = user.get("proxmox", {})
        try:
            vmid = int(info.get("vmid"))
        except Exception:
            continue
        node = str(info.get("node") or settings.get("node", "")).strip()
        user["proxmox_stats"] = proxmox_vm_stats(settings, node, vmid)
        user["proxmox_tasks"] = proxmox_vm_recent_tasks(settings, node, vmid)
        if info.get("exists") is False:
            user["workspace_health"] = "corrupt"
        else:
            user["workspace_health"] = "ok"
    return users


def proxmox_create_vm_for_user(user: dict) -> tuple[bool, str]:
    settings = proxmox_settings()
    ok, message = proxmox_ready(settings)
    if not ok:
        return False, message
    try:
        vmid = proxmox_pick_vmid(settings)
        node = settings["node"]
        clone_task = proxmox_request(
            "POST",
            f"/nodes/{node}/qemu/{settings['template_vmid']}/clone",
            settings,
            {
                "newid": vmid,
                "name": f"mwc-{user['route']}",
                "target": node,
                "full": 1,
            },
        )
        if not clone_task:
            return False, "Proxmox clone did not return a task identifier."
        task_ok, task_status = proxmox_wait_task(settings, node, str(clone_task), timeout_seconds=900)
        if not task_ok:
            return False, f"Proxmox clone task failed: {task_status}"
        profile = user.get("proxmox_profile", {})
        cores = int(profile.get("cores", settings["vm_cores"]))
        memory_mb = int(profile.get("memory_mb", settings["vm_memory_mb"]))
        bridge = profile.get("bridge", settings["net_bridge"])
        disk_override = profile.get("disk", settings["vm_disk"])
        start_on_create = bool(profile.get("start_on_create", settings["vm_start_on_create"]))
        guest_user = guest_username(str(profile.get("guest_user", "")), user.get("username", "admin"))
        guest_password = str(profile.get("guest_password", "")).strip() or user.get("password", "admin")

        config_payload = {
            "cores": cores,
            "memory": memory_mb,
            "net0": f"virtio,bridge={bridge}",
            "ciuser": guest_user,
            "cipassword": guest_password,
            "ipconfig0": "ip=dhcp",
            "tags": "mobileworkspace",
        }
        if disk_override:
            config_payload["scsi0"] = disk_override
        proxmox_request_retry(
            "POST",
            f"/nodes/{node}/qemu/{vmid}/config",
            settings,
            config_payload,
        )
        if user.get("enabled", True) and start_on_create:
            proxmox_request_retry("POST", f"/nodes/{node}/qemu/{vmid}/status/start", settings, {})
        user["provider"] = "proxmox_vm"
        user["proxmox"] = {
            "vmid": vmid,
            "node": node,
            "name": f"mwc-{user['route']}",
            "access_url": proxmox_vm_access_url(vmid, node),
            "guest_user": guest_user,
        }
        return True, f"Proxmox VM {vmid} created."
    except Exception as exc:
        return False, f"Proxmox VM creation failed: {exc}"


def proxmox_vm_action(user: dict, action: str) -> tuple[bool, str]:
    settings = proxmox_settings()
    info = user.get("proxmox", {})
    vmid = info.get("vmid")
    node = info.get("node") or settings.get("node", "")
    if not vmid:
        return False, "User has no linked Proxmox VM."
    try:
        proxmox_request_retry("POST", f"/nodes/{node}/qemu/{vmid}/status/{action}", settings, {})
        return True, f"VM {vmid} {action} requested."
    except Exception as exc:
        return False, f"Proxmox action '{action}' failed: {exc}"


def proxmox_delete_vm(user: dict) -> tuple[bool, str]:
    settings = proxmox_settings()
    info = user.get("proxmox", {})
    vmid = info.get("vmid")
    node = info.get("node") or settings.get("node", "")
    if not vmid:
        return True, "No Proxmox VM linked."
    def vm_missing_error(message: str) -> bool:
        lowered = message.lower()
        return "http 404" in lowered or "does not exist" in lowered or "not exist" in lowered

    try:
        proxmox_request("GET", f"/nodes/{node}/qemu/{vmid}/status/current", settings)
    except Exception as exc:
        if vm_missing_error(str(exc)):
            return True, f"VM {vmid} already absent."
        return False, f"Proxmox VM pre-delete check failed: {exc}"
    try:
        proxmox_request_retry("POST", f"/nodes/{node}/qemu/{vmid}/status/stop", settings, {"timeout": 30})
    except Exception:
        pass
    try:
        proxmox_request_retry("DELETE", f"/nodes/{node}/qemu/{vmid}", settings, None)
        return True, f"VM {vmid} deleted."
    except Exception as exc:
        if vm_missing_error(str(exc)):
            return True, f"VM {vmid} already absent."
        return False, f"Proxmox VM delete failed: {exc}"


def password_hash(plaintext: str) -> str:
    return passlib_bcrypt.using(rounds=12).hash(plaintext)


def verify_admin_auth(username: str, password: str) -> bool:
    if not ADMIN_USER_FILE.exists() or not ADMIN_HASH_FILE.exists():
        return False
    expected_user = ADMIN_USER_FILE.read_text(encoding="utf-8").strip()
    expected_hash = ADMIN_HASH_FILE.read_text(encoding="utf-8").strip()
    return username == expected_user and passlib_bcrypt.verify(password, expected_hash)


def workspace_session_key(route: str) -> str:
    return f"workspace_auth_{route}"


def verify_workspace_auth(user: dict, username: str, password: str) -> bool:
    if username.strip() != str(user.get("username", "")).strip():
        return False
    stored_hash = str(user.get("password_hash", "")).strip()
    if stored_hash and passlib_bcrypt.identify(stored_hash):
        return passlib_bcrypt.verify(password, stored_hash)
    return password == str(user.get("password", ""))


def find_user_by_route(users, route: str):
    return next((user for user in users if user.get("route") == route), None)


def user_workspaces_by_name(users, username: str):
    expected = username.strip()
    return [user for user in users if user.get("enabled", True) and user.get("username", "").strip() == expected]


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


def redirect_with_message(message: str, error: bool = False, endpoint: str = "workspaces_page"):
    return redirect(url_for(endpoint, message=message, error="1" if error else "0", lang=current_lang()))


def public_host_display() -> str:
    raw = (DOMAIN_OR_HOST or "").strip()
    host = request.host
    if not raw or raw in {"localhost", ":80"}:
        return host
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.lstrip(":")
    return raw or host


def public_scheme() -> str:
    forwarded = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.scheme or "http"


def workspace_public_url(user: dict) -> str:
    if user.get("provider") == "proxmox_vm":
        info = user.get("proxmox", {})
        vmid = info.get("vmid")
        node = info.get("node")
        if vmid and node:
            return proxmox_vm_access_url(int(vmid), str(node))
        return info.get("access_url", "")
    return f"{public_scheme()}://{public_host_display()}{user.get('route_path', '/')}"


@APP.route("/")
def root():
    return redirect("/client/login/")


@APP.route("/client/login/", methods=["GET", "POST"])
@APP.route("/user/login/", methods=["GET", "POST"])
def user_login():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    error = ""
    users = load_users()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        matches = user_workspaces_by_name(users, username)
        if not matches:
            error = tr["workspace_not_found"]
        else:
            valid = any(verify_workspace_auth(user, username, password) for user in matches)
            if valid:
                session["user_authenticated"] = True
                session["workspace_username"] = username
                for user in matches:
                    session[workspace_session_key(user["route"])] = True
                next_url = request.args.get("next") or url_for("user_dashboard", lang=lang)
                return redirect(next_url)
            error = tr["invalid_workspace_credentials"]
    return render_template_string(USER_LOGIN_TEMPLATE, tr=tr, lang=lang, error=error)


@APP.post("/client/logout/")
@APP.post("/user/logout/")
def user_logout():
    workspace_keys = [key for key in session.keys() if key.startswith("workspace_auth_")]
    for key in workspace_keys:
        session.pop(key, None)
    session.pop("user_authenticated", None)
    session.pop("workspace_username", None)
    return redirect(url_for("user_login", lang=current_lang()))


@APP.route("/client/")
@APP.route("/user/")
def user_dashboard():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    if not session.get("user_authenticated"):
        return redirect(url_for("user_login", lang=lang, next=request.path))
    username = str(session.get("workspace_username", "")).strip()
    all_users, _ = reconcile_workspace_state(load_users())
    users = user_workspaces_by_name(all_users, username)
    users_view = []
    for user in users:
        user_copy = dict(user)
        user_copy["public_url"] = workspace_public_url(user)
        users_view.append(user_copy)
    return render_template_string(USER_DASHBOARD_TEMPLATE, tr=tr, lang=lang, users=users_view, session_user=username)


@APP.route("/client/change-password/", methods=["GET", "POST"])
@APP.route("/user/change-password/", methods=["GET", "POST"])
def user_change_password():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    if not session.get("user_authenticated"):
        return redirect(url_for("user_login", lang=lang, next=request.path))
    username = str(session.get("workspace_username", "")).strip()
    error = ""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        users = user_workspaces_by_name(load_users(), username)
        if not users:
            return redirect(url_for("user_login", lang=lang))
        if not any(verify_workspace_auth(user, username, current_password) for user in users):
            error = "Current password is incorrect."
        elif len(new_password) < 8:
            error = "New password must be at least 8 characters."
        elif new_password != confirm_password:
            error = "New passwords do not match."
        else:
            all_users = load_users()
            changed = 0
            for user in all_users:
                if str(user.get("username", "")).strip() == username:
                    user["password"] = new_password
                    user["password_hash"] = password_hash(new_password)
                    changed += 1
            save_users(all_users)
            return redirect_with_message(
                f"Password updated for {changed} workspace(s).",
                endpoint="user_dashboard",
            )
    return render_template_string(USER_CHANGE_PASSWORD_TEMPLATE, tr=tr, lang=lang, error=error)


@APP.route("/user/auth/<route>/")
def user_workspace_auth(route: str):
    users = load_users()
    user = find_user_by_route(users, route)
    if not user or not user.get("enabled", True):
        return "workspace not found", 401
    if session.get(workspace_session_key(route)):
        return "ok", 200
    return "unauthorized", 401


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
    users, sync_message = reconcile_workspace_state(load_users())
    flash_data = current_flash()
    if sync_message and not flash_data.get("flash"):
        flash_data["flash"] = sync_message
        flash_data["flash_error"] = False
    unique_users = len({str(user.get("username", "")).strip() for user in users if str(user.get("username", "")).strip()})
    proxmox_summary = proxmox_node_usage() if proxmox_enabled() else {}
    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE,
        users=users,
        unique_user_count=unique_users,
        proxmox_summary=proxmox_summary,
        tr=tr,
        lang=lang,
        proxmox_mode=proxmox_enabled(),
        **flash_data,
    )


@APP.route("/admin/workspaces/")
@login_required
def workspaces_page():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    workspace_view = request.args.get("view", "list").strip().lower()
    if workspace_view not in {"list", "create"}:
        workspace_view = "list"
    users, sync_message = reconcile_workspace_state(load_users())
    users = enrich_proxmox_workspace_insights(users)
    users_view = []
    for user in users:
        user_copy = dict(user)
        user_copy["public_url"] = workspace_public_url(user)
        users_view.append(user_copy)
    flash_data = current_flash()
    if sync_message and not flash_data.get("flash"):
        flash_data["flash"] = sync_message
        flash_data["flash_error"] = False
    cfg = proxmox_settings()
    ready_ok, ready_message = proxmox_health_check() if proxmox_enabled() else (False, "")
    return render_template_string(
        PAGE_TEMPLATE,
        users=users_view,
        tr=tr,
        lang=lang,
        domain=DOMAIN_OR_HOST,
        public_host=public_host_display(),
        timezone=TIMEZONE,
        version=APP_VERSION,
        github_url=GITHUB_URL,
        company_name=COMPANY_NAME,
        company_url=COMPANY_URL,
        admin_username=session.get("admin_username", "admin"),
        proxmox_mode=proxmox_enabled(),
        proxmox_cfg=cfg,
        proxmox_ready_ok=ready_ok,
        proxmox_ready_message=ready_message,
        proxmox_default_cores=cfg["vm_cores"],
        proxmox_default_memory_mb=cfg["vm_memory_mb"],
        proxmox_default_bridge=cfg["net_bridge"],
        proxmox_default_disk=cfg["vm_disk"],
        proxmox_default_start_on_create=cfg["vm_start_on_create"],
        workspace_view=workspace_view,
        copyright_year=datetime.utcnow().year,
        **flash_data,
    )


@APP.route("/admin/users/")
@login_required
def admin_users_page():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    users, sync_message = reconcile_workspace_state(load_users())
    grouped: dict[str, list[dict]] = {}
    for user in users:
        key = str(user.get("username", "")).strip()
        if not key:
            continue
        grouped.setdefault(key, []).append(user)
    rows = []
    for username, items in sorted(grouped.items(), key=lambda item: item[0]):
        corrupt = any(item.get("workspace_health") == "corrupt" for item in items)
        rows.append(
            {
                "username": username,
                "workspace_count": len(items),
                "status_text": tr["health_corrupt"] if corrupt else tr["health_ok"],
            }
        )
    flash_data = current_flash()
    if sync_message and not flash_data.get("flash"):
        flash_data["flash"] = sync_message
        flash_data["flash_error"] = False
    return render_template_string(ADMIN_USERS_TEMPLATE, tr=tr, lang=lang, user_rows=rows, **flash_data)


@APP.post("/admin/users/password")
@login_required
def admin_reset_user_password():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return redirect_with_message("Username and password are required.", error=True, endpoint="admin_users_page")
    users = load_users()
    changed = 0
    for user in users:
        if str(user.get("username", "")).strip() == username:
            user["password"] = password
            user["password_hash"] = password_hash(password)
            changed += 1
    if changed == 0:
        return redirect_with_message("User not found.", error=True, endpoint="admin_users_page")
    save_users(users)
    return redirect_with_message(f"Updated password for {changed} workspace(s).", endpoint="admin_users_page")


@APP.route("/admin/proxmox/")
@login_required
def proxmox_settings_page():
    lang = current_lang()
    tr = TRANSLATIONS[lang]
    flash_data = current_flash()
    cfg = proxmox_settings()
    usage = proxmox_node_usage() if proxmox_enabled() else {}
    return render_template_string(
        PROXMOX_SETTINGS_TEMPLATE,
        tr=tr,
        lang=lang,
        proxmox_cfg=cfg,
        usage=usage,
        **flash_data,
    )


@APP.post("/admin/proxmox/test")
@login_required
def proxmox_test():
    if not proxmox_enabled():
        return redirect_with_message("Proxmox VM mode is not enabled.", error=True, endpoint="proxmox_settings_page")
    ok, message = proxmox_health_check()
    return redirect_with_message(message, error=not ok, endpoint="proxmox_settings_page")


@APP.post("/admin/proxmox/settings")
@login_required
def save_proxmox_settings_route():
    try:
        cfg = proxmox_settings()
        mode = request.form.get("cfg_provisioner_mode", "").strip().lower()
        cfg["provisioner_mode"] = mode if mode in {"docker", "proxmox_vm"} else "docker"
        cfg["api_url"] = request.form.get("cfg_api_url", "").strip().rstrip("/")
        cfg["node"] = request.form.get("cfg_node", "").strip()
        cfg["template_vmid"] = request.form.get("cfg_template_vmid", "").strip()
        cfg["vmid_min"] = request.form.get("cfg_vmid_min", "").strip()
        cfg["vmid_max"] = request.form.get("cfg_vmid_max", "").strip()
        cfg["token_id"] = request.form.get("cfg_token_id", "").strip()
        cfg["token_secret"] = request.form.get("cfg_token_secret", "").strip()
        cfg["verify_tls"] = request.form.get("cfg_verify_tls") == "1"
        if cfg["vmid_min"] or cfg["vmid_max"]:
            vmid_min = parse_int_or_default(cfg["vmid_min"] or "1", 1, 1, 999999999, "VMID Min")
            vmid_max = parse_int_or_default(cfg["vmid_max"] or "999999999", 999999999, 1, 999999999, "VMID Max")
            if vmid_max < vmid_min:
                return redirect_with_message(
                    "VMID Max must be greater than or equal to VMID Min.",
                    error=True,
                    endpoint="proxmox_settings_page",
                )
        save_proxmox_settings(cfg)
        if cfg["provisioner_mode"] == "proxmox_vm":
            clear_generated_proxy_files()
            reload_proxy()
    except Exception as exc:
        return redirect_with_message(
            f"Saving Proxmox settings failed: {trim_output(str(exc))}",
            error=True,
            endpoint="proxmox_settings_page",
        )
    return redirect_with_message("Proxmox settings saved.", endpoint="proxmox_settings_page")


@APP.post("/admin/users")
@login_required
def create_user():
    users = load_users()
    cfg = proxmox_settings()
    try:
        username = validate_username(request.form["username"])
        workspace_name = request.form.get("workspace_name", "").strip() or request.form.get("route", "").strip()
        route = slugify(workspace_name)
        workspace_type = request.form["workspace_type"]
        network_mode = request.form["network_mode"]
        password = request.form["password"]
        proxmox_cores = parse_int_or_default(request.form.get("proxmox_cores", ""), cfg["vm_cores"], 1, 64, "vCPU cores")
        proxmox_memory_mb = parse_int_or_default(
            request.form.get("proxmox_memory_mb", ""),
            cfg["vm_memory_mb"],
            512,
            1048576,
            "VM memory",
        )
        proxmox_bridge = (request.form.get("proxmox_bridge", "") or cfg["net_bridge"]).strip() or cfg["net_bridge"]
        proxmox_disk = (request.form.get("proxmox_disk", "") or "").strip()
        proxmox_start_on_create = request.form.get("proxmox_start_on_create") == "1"
        proxmox_guest_user = guest_username(request.form.get("proxmox_guest_user", ""), username)
        proxmox_guest_password = (request.form.get("proxmox_guest_password", "") or "").strip()
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
    if proxmox_enabled() and workspace_type != "desktop":
        return redirect_with_message("In Proxmox VM mode only desktop workspaces are supported.", error=True)

    user = {
        "id": make_id(route, workspace_type),
        "username": username,
        "workspace_name": workspace_name,
        "route": route,
        "route_path": f"/workspaces/{route}/",
        "workspace_type": workspace_type,
        "network_mode": network_mode,
        "password": password,
        "password_hash": password_hash(password),
        "enabled": True,
        "provider": "proxmox_vm" if proxmox_enabled() else "docker",
        "proxmox_profile": (
            {
                "cores": proxmox_cores,
                "memory_mb": proxmox_memory_mb,
                "bridge": proxmox_bridge,
                "disk": proxmox_disk,
                "start_on_create": proxmox_start_on_create,
                "guest_user": proxmox_guest_user,
                "guest_password": proxmox_guest_password,
            }
            if proxmox_enabled()
            else {}
        ),
        "service_name": make_id(route, workspace_type),
        "container_name": f"mwc-{make_id(route, workspace_type)}",
        "volumes": build_volume_map(route, workspace_type),
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    if proxmox_enabled():
        ok, output = proxmox_create_vm_for_user(user)
        if not ok:
            return redirect_with_message(trim_output(output), error=True)
        users.append(user)
        save_users(users)
        return redirect_with_message(f"Workspace '{username}' created as Proxmox VM.")

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
    if user.get("provider") == "proxmox_vm":
        vm_action = "start" if user["enabled"] else "stop"
        ok, output = proxmox_vm_action(user, vm_action)
        if not ok:
            return redirect_with_message(trim_output(output), error=True)
        return redirect_with_message(f"Workspace '{user['username']}' {action}d.")
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
    if user.get("provider") == "proxmox_vm":
        ok_stop, out_stop = proxmox_vm_action(user, "stop")
        ok_start, out_start = proxmox_vm_action(user, "start")
        if not ok_stop and not ok_start:
            return redirect_with_message(f"Redeploy failed: {trim_output(out_stop)}", error=True)
        return redirect_with_message(f"Workspace '{user['username']}' VM restarted.")
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
    if user.get("provider") == "proxmox_vm":
        ok, output = proxmox_delete_vm(user)
        if not ok:
            return redirect_with_message(trim_output(output), error=True)
        save_users(remaining)
        return redirect_with_message(f"Workspace '{user['username']}' deleted.")
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

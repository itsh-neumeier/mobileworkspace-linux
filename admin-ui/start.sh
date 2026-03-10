#!/bin/sh
set -eu

PROXY_FILE="${MWC_GENERATED_PROXY:-/workspace/generated/nginx.users.conf}"
NGINX_PORT="${MWC_NGINX_PORT:-80}"

mkdir -p "$(dirname "${PROXY_FILE}")" /etc/nginx
if [ ! -f "${PROXY_FILE}" ]; then
  printf '# Generated routes for user workspaces will be written here by the admin UI.\n' > "${PROXY_FILE}"
fi

cat <<EOF >/etc/nginx/nginx.conf
worker_processes auto;

events {
  worker_connections 1024;
}

http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  sendfile on;
  tcp_nopush on;
  tcp_nodelay on;
  keepalive_timeout 65;
  resolver 127.0.0.11 valid=10s ipv6=off;

  server {
    listen ${NGINX_PORT} default_server;
    server_name _;

    location = / {
      default_type text/html;
      return 200 '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Mobile Web Console Hub</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(160deg,#081222 0%,#12213a 100%);color:#f8fafc;font-family:"Segoe UI",sans-serif;padding:24px}main{width:min(720px,100%);padding:32px;border-radius:24px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(14px)}a{display:inline-flex;margin-top:18px;padding:12px 18px;border-radius:999px;background:#7cc4ff;color:#081222;text-decoration:none;font-weight:700}</style></head><body><main><h1>Mobile Web Console Hub</h1><p>This instance is managed through the admin panel. Use the web UI to create terminal or desktop workspaces for your users.</p><a href="/admin/">Open Admin Panel</a></main></body></html>';
    }

    location = /admin {
      return 302 /admin/;
    }

    location ^~ /admin/ {
      proxy_pass http://127.0.0.1:8080;
      proxy_http_version 1.1;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
    }

    location = /login {
      return 302 /login/;
    }

    location ^~ /login/ {
      proxy_pass http://127.0.0.1:8080;
      proxy_http_version 1.1;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
    }

    location = /logout {
      return 302 /logout/;
    }

    location ^~ /logout/ {
      proxy_pass http://127.0.0.1:8080;
      proxy_http_version 1.1;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
    }

    include ${PROXY_FILE};
  }
}
EOF

gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 app:APP &
GUNICORN_PID=$!

READY=0
for i in $(seq 1 60); do
  if wget -q -O /dev/null http://127.0.0.1:8080/login/; then
    READY=1
    break
  fi
  sleep 1
done

if [ "${READY}" -ne 1 ]; then
  echo "Gunicorn did not become ready in time" >&2
  kill "${GUNICORN_PID}" 2>/dev/null || true
  wait "${GUNICORN_PID}" 2>/dev/null || true
  exit 1
fi

nginx -g 'daemon off;' &
NGINX_PID=$!

while kill -0 "${GUNICORN_PID}" 2>/dev/null && kill -0 "${NGINX_PID}" 2>/dev/null; do
  sleep 1
done

kill "${GUNICORN_PID}" "${NGINX_PID}" 2>/dev/null || true
wait "${GUNICORN_PID}" 2>/dev/null || true
wait "${NGINX_PID}" 2>/dev/null || true

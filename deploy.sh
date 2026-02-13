#!/bin/bash
# =============================================================
# Loving - CentOS 7.6 Deployment Script
# =============================================================
# Usage: sudo bash deploy.sh
#
# This script will:
# 1. Install Python 3.6+ and pip
# 2. Install dependencies
# 3. Set up the app as a systemd service
# 4. Configure existing nginx as reverse proxy on port 8090
# 5. Configure firewall
# =============================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="loving"
INTERNAL_PORT=5000   # gunicorn listens here (internal only)
PUBLIC_PORT=8090     # nginx exposes the site on this port

echo "========================================="
echo "  Loving - Deployment for CentOS 7.6"
echo "========================================="

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash deploy.sh"
    exit 1
fi

# ---- Step 1: Install system dependencies ----
echo ""
echo "[1/6] Installing system dependencies..."
yum install -y epel-release
yum install -y python3 python3-pip python3-devel gcc

# ---- Step 2: Create app user ----
echo ""
echo "[2/6] Setting up app user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false "$APP_USER"
fi

# ---- Step 3: Install Python dependencies ----
echo ""
echo "[3/6] Installing Python dependencies..."
cd "$APP_DIR"
pip3 install --upgrade pip
pip3 install -r requirements.txt
pip3 install 'gunicorn==20.1.0'

# ---- Step 4: Initialize database ----
echo ""
echo "[4/6] Initializing database..."
python3 database.py

# Set permissions
mkdir -p "$APP_DIR/static/uploads/thumbnails"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
chmod -R 755 "$APP_DIR"

# ---- Step 5: Create systemd service ----
echo ""
echo "[5/6] Creating systemd service..."

cat > /etc/systemd/system/loving.service << EOF
[Unit]
Description=Loving - Valentine's Day Website
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/gunicorn --workers 2 --bind 127.0.0.1:$INTERNAL_PORT --timeout 300 app:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ---- Step 6: Configure nginx reverse proxy ----
echo ""
echo "[6/6] Configuring nginx reverse proxy on port $PUBLIC_PORT..."

# Find nginx config directory (works with BT Panel and standard installs)
NGINX_CONF_DIR=""
if [ -d /www/server/panel/vhost/nginx ]; then
    NGINX_CONF_DIR="/www/server/panel/vhost/nginx"
elif [ -d /etc/nginx/conf.d ]; then
    NGINX_CONF_DIR="/etc/nginx/conf.d"
elif [ -d /www/server/nginx/conf/vhost ]; then
    NGINX_CONF_DIR="/www/server/nginx/conf/vhost"
fi

if [ -n "$NGINX_CONF_DIR" ]; then
    cat > "$NGINX_CONF_DIR/loving.conf" << EOF
server {
    listen $PUBLIC_PORT;
    server_name _;
    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:$INTERNAL_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /static {
        alias $APP_DIR/static;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    echo "  -> Nginx config written to $NGINX_CONF_DIR/loving.conf"
else
    echo "  -> WARNING: Could not find nginx config directory."
    echo "     You may need to manually add an nginx config."
fi

# ---- Start services ----
echo ""
echo "Starting services..."
systemctl daemon-reload
systemctl enable loving
systemctl restart loving

# Reload nginx (try common service names)
nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || \
    /www/server/nginx/sbin/nginx -s reload 2>/dev/null || \
    echo "  -> Please reload nginx manually: nginx -s reload"

# ---- Firewall ----
echo ""
echo "Configuring firewall..."
firewall-cmd --permanent --add-port=$PUBLIC_PORT/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

# ---- Done ----
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "========================================="
echo "  Loving is now running!"
echo "========================================="
echo ""
echo "  URL: http://$IP:$PUBLIC_PORT"
echo "  Password: (set in config.py)"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status loving"
echo "    sudo systemctl restart loving"
echo "    sudo journalctl -u loving -f"
echo ""
echo "  To change settings, edit: $APP_DIR/config.py"
echo "  Then restart: sudo systemctl restart loving"
echo ""
echo "  IMPORTANT: Change the password in config.py!"
echo "========================================="

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
# 4. Configure firewall
# 5. (Optional) Set up nginx as reverse proxy
# =============================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="loving"
APP_PORT=5000
DOMAIN=""  # Set to your domain if you have one, or leave empty for IP access

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

# Add official nginx repo for CentOS 7
if [ ! -f /etc/yum.repos.d/nginx.repo ]; then
    cat > /etc/yum.repos.d/nginx.repo << 'REPOEOF'
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
REPOEOF
fi

yum install -y python3 python3-pip python3-devel gcc nginx

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
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/gunicorn --workers 2 --bind 127.0.0.1:$APP_PORT app:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ---- Step 6: Configure nginx ----
echo ""
echo "[6/6] Configuring nginx..."
cat > /etc/nginx/conf.d/loving.conf << EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # For large file uploads
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

# ---- Start services ----
echo ""
echo "Starting services..."
systemctl daemon-reload
systemctl enable loving
systemctl start loving
systemctl enable nginx
systemctl restart nginx

# ---- Firewall ----
echo ""
echo "Configuring firewall..."
firewall-cmd --permanent --add-service=http 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

# ---- Done ----
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "========================================="
echo "  Loving is now running!"
echo "========================================="
echo ""
echo "  URL: http://$IP"
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

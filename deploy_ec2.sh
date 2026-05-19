#!/bin/bash
# Smart Notes Vault - EC2 Deployment Script
# Run this script on your EC2 instance (Amazon Linux 2023 or Ubuntu)

set -e

echo "=========================================="
echo " Starting Smart Notes Vault Deployment... "
echo "=========================================="

# 1. Update system and install dependencies
echo "=> Installing dependencies..."
if [ -x "$(command -v dnf)" ]; then
    # Amazon Linux 2023 / RHEL
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip python3-devel gcc nginx git
elif [ -x "$(command -v apt-get)" ]; then
    # Ubuntu / Debian
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential nginx git
else
    echo "Unsupported OS. Please install python3, pip, and nginx manually."
    exit 1
fi

# 2. Setup Application Directory
APP_DIR="/home/$(whoami)/smart-notes-vault"
if [ ! -d "$APP_DIR" ]; then
    echo "=> Application directory not found at $APP_DIR."
    echo "Please clone your repository here or copy your files before running this script."
    exit 1
fi

cd "$APP_DIR"

# 3. Setup Virtual Environment
echo "=> Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python Requirements
echo "=> Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn pymysql cryptography  # Ensure production WSGI and DB drivers are installed

# 5. Configure Nginx
echo "=> Configuring Nginx..."
NGINX_CONF="/etc/nginx/conf.d/smart-notes-vault.conf"
if [ -x "$(command -v apt-get)" ]; then
    NGINX_CONF="/etc/nginx/sites-available/smart-notes-vault"
fi

sudo bash -c "cat > $NGINX_CONF << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"

if [ -x "$(command -v apt-get)" ]; then
    sudo ln -sf /etc/nginx/sites-available/smart-notes-vault /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# 6. Setup Systemd Service
echo "=> Setting up Systemd Service..."
SERVICE_PATH="/etc/systemd/system/smart-notes-vault.service"
sudo bash -c "cat > $SERVICE_PATH << EOF
[Unit]
Description=Gunicorn instance to serve Smart Notes Vault
After=network.target

[Service]
User=$(whoami)
Group=www-data
WorkingDirectory=$APP_DIR
Environment=\"PATH=$APP_DIR/venv/bin\"
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn.conf.py app:app

[Install]
WantedBy=multi-user.target
EOF"

# 7. Start and Enable Services
echo "=> Starting Services..."
sudo systemctl daemon-reload
sudo systemctl start smart-notes-vault
sudo systemctl enable smart-notes-vault

sudo systemctl restart nginx
sudo systemctl enable nginx

echo "=========================================="
echo " Deployment Complete! "
echo " Your application should now be accessible"
echo " via the Public IP of this EC2 instance."
echo "=========================================="

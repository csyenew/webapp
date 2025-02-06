#!/bin/bash

set -e  # Exit on error
LOG_FILE="/var/log/health_check_setup.log"

# Log function
log() {
    echo "$(date) : $1" | tee -a $LOG_FILE
}

log "Starting Health Check Setup Script"

# ----------------------
# Update & Upgrade System
# ----------------------
log "Updating package lists and upgrading packages..."
sudo apt update -y && sudo apt upgrade -y

# ----------------------
# Install MySQL (or change to PostgreSQL/MariaDB)
# ----------------------
log "Installing MySQL Server..."
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql

# ----------------------
# Configure Database
# ----------------------
DB_NAME="csye6225"
DB_USER="appuser"
DB_PASS="AppPassword123!"

log "Creating MySQL database and user..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
sudo mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';"
sudo mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# ----------------------
# Create Linux Group & User
# ----------------------
APP_GROUP="appgroup"
APP_USER="appuser"

log "Creating Linux group ($APP_GROUP) and user ($APP_USER)..."
sudo groupadd -f $APP_GROUP
sudo useradd -m -g $APP_GROUP -s /bin/bash $APP_USER

# ----------------------
# Deploy Application
# ----------------------
APP_DIR="/opt/csye6225"
APP_ZIP="webapp.zip"  # Change this to the actual zip file name

log "Deploying application..."
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_GROUP $APP_DIR
sudo chmod 750 $APP_DIR

# Assuming app zip is uploaded to /tmp
if [ -f "/tmp/$APP_ZIP" ]; then
    sudo -u $APP_USER unzip /tmp/$APP_ZIP -d $APP_DIR
else
    log "Application zip not found! Please upload it to /tmp/$APP_ZIP"
    exit 1
fi

# ----------------------
# Set Permissions
# ----------------------
log "Updating permissions for $APP_DIR..."
sudo chown -R $APP_USER:$APP_GROUP $APP_DIR
sudo chmod -R 750 $APP_DIR

# ----------------------
# Final Steps
# ----------------------
log "Health Check Setup Completed Successfully!"


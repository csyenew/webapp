#!/usr/bin/env bash

set -eo pipefail  # Exit on error

export DEBIAN_FRONTEND=noninteractive  # Prevent interactive prompts

# ✅ Update and install required system libraries
sudo apt-get update
sudo apt-get -y install python3 python3-pip libpq-dev python3-venv wget

# ✅ Install PostgreSQL
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install postgresql-14

# ✅ Install CloudWatch Agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# ✅ Create a new user (if needed)
sudo adduser --disabled-password --gecos "" ds

# ✅ Ensure the webapp directory exists
sudo mkdir -p /home/admin/webapp

# ✅ Set correct ownership for webapp directory
sudo chown -R ds:ds /home/admin/webapp

# ✅ Copy user.csv if it exists
if [ -f "/home/admin/webapp/user.csv" ]; then
    sudo cp /home/admin/webapp/user.csv /opt/
    sudo chmod 755 /opt/user.csv
else
    echo "Warning: user.csv not found in /home/admin/webapp/"
fi

# ✅ Grant sudo privileges to admin (if needed)
echo "admin ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers

# ✅ Install application dependencies inside a NEW virtual environment
sudo -i -u ds bash << EOF
cd /home/admin/webapp

# Remove any existing virtual environment
rm -rf venv  

# Create a fresh virtual environment
python3 -m venv venv
source venv/bin/activate
export PIP_BREAK_SYSTEM_PACKAGES=1

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt
EOF

# ✅ Setup WebApp as a Systemd Service
sudo cp /home/admin/webapp/packer/webapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webapp.service
sudo systemctl start webapp.service

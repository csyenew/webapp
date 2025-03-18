#!/usr/bin/env bash

set -eo pipefail  # Exit on error

export DEBIAN_FRONTEND=noninteractive  # Prevent interactive prompts

# ✅ Update and install required system libraries
sudo apt-get update
sudo apt-get -y install python3 python3-pip python3-venv wget

# ✅ Create the webapp user if it doesn't exist
if ! id -u webapp > /dev/null 2>&1; then
  sudo useradd -m -d /home/webapp webapp
fi

# ✅ Ensure the webapp directory exists with correct permissions
sudo mkdir -p /home/admin/webapp
sudo chown -R admin:admin /home/admin/webapp

# ✅ Install CloudWatch Agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
sudo rm -f ./amazon-cloudwatch-agent.deb

# ✅ Install application dependencies inside a virtual environment
sudo -i -u admin bash << EOF
cd /home/admin/webapp

# Remove any existing virtual environment
rm -rf venv  


# Install PostgreSQL development libraries
sudo apt-get -y install libpq-dev postgresql-server-dev-all


# Create a fresh virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
# If requirements.txt is in the webapp directory
pip install -r /home/admin/webapp/requirements.txt
EOF

# ✅ Setup WebApp as a Systemd Service
sudo cp /home/admin/webapp/webapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webapp.service
sudo systemctl start webapp.service
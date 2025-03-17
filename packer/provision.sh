#!/usr/bin/env bash

set -eo pipefail  # Exit on error

export DEBIAN_FRONTEND=noninteractive  # Prevent interactive prompts

# ✅ Update and install required system libraries
sudo apt-get update
sudo apt-get -y install python3 python3-pip python3-venv wget

# ✅ Install CloudWatch Agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
sudo rm -f ./amazon-cloudwatch-agent.deb

# ✅ Create a non-privileged user for running the application
sudo useradd -m -d /home/webapp webapp

# ✅ Ensure the webapp directory exists
sudo mkdir -p /home/admin/webapp

# ✅ Set correct ownership for webapp directory
sudo chown -R webapp:webapp /home/admin/webapp

# ✅ Install application dependencies inside a virtual environment
sudo -i -u webapp bash << EOF
cd /home/admin/webapp

# Create a fresh virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt
EOF

# ✅ Setup WebApp as a Systemd Service
sudo cp /home/admin/webapp/webapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webapp.service

# Don't start the service here - let user_data do that with proper environment variables
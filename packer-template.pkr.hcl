packer {
  required_version = ">= 1.8.0"

  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.0.0"
    }
    googlecompute = {
      source  = "github.com/hashicorp/googlecompute"
      version = ">= 1.0.0"
    }
  }
}

# Define variables for AWS and GCP
variable "aws_region" {
  default = "us-east-1"
}

variable "gcp_project_id" {
  default = "csye-dev-451921-452108"
}

# AWS Source Configuration (Ubuntu Custom for AWS)
source "amazon-ebs" "ubuntu_custom_aws" {
  region = var.aws_region
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/*ubuntu-jammy-22.04-amd64-server-*"
      virtualization-type = "hvm"
      root-device-type    = "ebs"
    }
    most_recent = true
    owners      = ["099720109477"]
  }
  ssh_username    = "ubuntu"
  instance_type   = "t2.micro"
  ami_name        = "ubuntu-custom-{{timestamp}}"
  ami_description = "Custom Ubuntu 22.04 with MySQL and Flask"
  encrypt_boot    = true
}

# GCP Source Configuration (Ubuntu Custom for GCP)
source "googlecompute" "ubuntu_custom_gcp" {
  project_id          = var.gcp_project_id
  source_image_family = "ubuntu-2404-lts-amd64"
  zone                = "us-central1-a"
  machine_type        = "e2-micro"
  image_name          = "custom-ubuntu-24-{{timestamp}}"
  image_family        = "custom-ubuntu"
  image_description   = "Custom Ubuntu 24.04 LTS with MySQL and Flask"
  ssh_username        = "ubuntu"
}

# Build Configuration for AWS and GCP
build {
  sources = [
    "source.amazon-ebs.ubuntu_custom_aws",
    "source.googlecompute.ubuntu_custom_gcp"
  ]

  # Provisioning with shell script for MySQL setup, Flask app deployment, and systemd service setup
  provisioner "shell" {
    inline = [
      "echo 'export DEBIAN_FRONTEND=noninteractive' | sudo tee -a /etc/environment",
      "export DEBIAN_FRONTEND=noninteractive",

      # Update package list and upgrade all packages
      "echo 'Upgrading all packages...'",
      "sudo apt-get update -y",
      "sudo apt-get upgrade -y",

      # Install MySQL Server and Client
      "echo 'Installing MySQL server and client...'",
      "sudo apt-get install -y mysql-server mysql-client || { echo 'MySQL installation failed'; exit 1; }",

      # Install pip3 and virtual environment
      "echo 'Installing pip3 and setting up virtual environment...'",
      "sudo apt-get install -y python3-pip python3-venv || { echo 'Python installation failed'; exit 1; }",

      # Start and Enable MySQL Service
      "echo 'Starting MySQL service...'",
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql",

      # Create the csye6225 group and user
      "echo 'Creating user csye6225 with no login shell...'",
      "sudo groupadd csye6225 || { echo 'Group creation failed'; exit 1; }",
      "sudo useradd -r -m -s /usr/sbin/nologin -g csye6225 csye6225 || { echo 'User creation failed'; exit 1; }",

      # Create WebApp Directory & Virtual Environment
      "echo 'Setting up Flask web application...'",
      "sudo mkdir -p /home/csye6225/webapp",
      "sudo chown -R csye6225:csye6225 /home/csye6225/webapp",
      "sudo -u csye6225 python3 -m venv /home/csye6225/webapp/venv",

      # Install Python Dependencies
      "echo 'Installing Flask dependencies...'",
      "sudo -u csye6225 /home/csye6225/webapp/venv/bin/pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv mysql-connector-python werkzeug pytest",

      # Create systemd service file using heredoc
      "echo 'Creating systemd service file...'",
      "cat <<EOF | sudo tee /etc/systemd/system/webapp.service",
      "[Unit]",
      "Description=Flask Web Application",
      "After=network.target",
      "",
      "[Service]",
      "User=csye6225",
      "Group=csye6225",
      "WorkingDirectory=/home/csye6225/webapp",
      "ExecStart=/home/csye6225/webapp/venv/bin/python /home/csye6225/webapp/app.py",
      "Restart=always",
      "Environment=FLASK_APP=app.py",
      "Environment=FLASK_ENV=production",
      "Environment=PATH=/home/csye6225/webapp/venv/bin:$PATH",
      "",
      "[Install]",
      "WantedBy=multi-user.target",
      "EOF",

      # Reload systemd and enable service
      "echo 'Reloading systemd daemon...'",
      "sudo systemctl daemon-reload || { echo 'Daemon reload failed'; exit 1; }",
      "echo 'Enabling webapp service...'",
      "sudo systemctl enable webapp || { echo 'Service enable failed'; exit 1; }",
      "echo 'Starting webapp service...'",
      "sudo systemctl start webapp || { echo 'Service start failed'; exit 1; }"
    ]
  }
}

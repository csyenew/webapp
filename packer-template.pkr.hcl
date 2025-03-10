packer {
  required_version = ">= 1.8.0"

  required_plugins {
    amazon = {
      source  = "hashicorp/amazon"
      version = ">= 1.0.0"
    }
    googlecompute = {
      source  = "hashicorp/googlecompute"
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

# AWS Source Configuration
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

# GCP Source Configuration
source "googlecompute" "ubuntu_custom_gcp" {
  project_id          = var.gcp_project_id
  source_image_family = "ubuntu-2204-lts"
  zone                = "us-central1-a"
  machine_type        = "e2-micro"
  image_name          = "custom-ubuntu-24-{{timestamp}}"
  image_family        = "custom-ubuntu"
  image_description   = "Custom Ubuntu 24.04 LTS with MySQL and Flask"
  ssh_username        = "ubuntu"
}

# Build Configuration
build {
  sources = [
    "source.amazon-ebs.ubuntu_custom_aws",
    "source.googlecompute.ubuntu_custom_gcp"
  ]

  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo apt-get update -y && sudo apt-get upgrade -y",
      "sudo apt-get install -y mysql-server mysql-client python3-pip python3-venv",

      # MySQL Setup
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql",

      # Create user csye6225
      "sudo groupadd csye6225 || true",
      "sudo useradd -r -m -s /usr/sbin/nologin -g csye6225 csye6225 || true",

      # Setup Flask App
      "sudo mkdir -p /home/csye6225/webapp",
      "sudo chown -R csye6225:csye6225 /home/csye6225/webapp",
      "sudo -u csye6225 python3 -m venv /home/csye6225/webapp/venv",
      "sudo -u csye6225 /home/csye6225/webapp/venv/bin/pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv mysql-connector-python werkzeug pytest",

      # Create systemd service file using heredoc (✅ Corrected version)
      "cat <<EOF | sudo tee /etc/systemd/system/webapp.service >/dev/null
[Unit]
Description=Flask Web Application
After=network.target

[Service]
User=csye6225
Group=csye6225
WorkingDirectory=/home/csye6225/webapp
ExecStart=/home/csye6225/webapp/venv/bin/python /home/csye6225/webapp/app.py
Restart=always
Environment=FLASK_APP=app.py
Environment=FLASK_ENV=production
Environment=PATH=/home/csye6225/webapp/venv/bin:$PATH

[Install]
WantedBy=multi-user.target
EOF",

      # Enable and start the service
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp",
      "sudo systemctl start webapp"
    ]
  }
}

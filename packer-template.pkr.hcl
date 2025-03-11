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

# AWS Variables
variable "ami_users" {
  type    = list(string)
  default = ["434369415270", "610018956402"]
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "source_ami" {
  type    = string
  default = "ami-06db4d78cb1d3bbf9"  # Ubuntu AMI
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "ssh_username" {
  type    = string
  default = "admin"  # Ubuntu default user
}

variable "subnet_id" {
  type    = string
  default = "subnet-0d0c161f44f4f4ae8"
}

variable "vpc_id" {
  type    = string
  default = "vpc-0edcd255c0595a650"
}

variable "ami_name" {
  type    = string
  default = "webapp-ami"
}

variable "environment" {
  type    = string
  default = "dev"
}

# GCP Variables
variable "gcp_project_id" {
  type    = string
  default = "csye-dev-451921-452108"
}

variable "gcp_credentials_file" {
  type    = string
  default = "gcp-key.json"
}

variable "artifact_path" {
  type    = string
  default = "app_artifact.zip"
}

locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
}

# AWS Source Configuration
source "amazon-ebs" "ubuntu_custom_aws" {
  region        = var.region
  ami_name      = "${var.ami_name}-${local.timestamp}"
  ami_users     = var.ami_users
  instance_type = var.instance_type
  source_ami    = var.source_ami
  ssh_username  = var.ssh_username
  subnet_id     = var.subnet_id
  vpc_id        = var.vpc_id

  encrypt_boot = false

  tags = {
    Name        = "${var.ami_name}-${local.timestamp}"
    Environment = var.environment
  }

  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    delete_on_termination = true
  }
}

# GCP Source Configuration
source "googlecompute" "ubuntu_custom_gcp" {
  project_id          = var.gcp_project_id
  source_image_family = "ubuntu-2204-lts"
  zone                = "us-central1-a"
  machine_type        = "e2-micro"
  image_name          = "custom-ubuntu-24-${local.timestamp}"
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
      # Set non-interactive mode to avoid prompts
      "echo 'export DEBIAN_FRONTEND=noninteractive' | sudo tee -a /etc/environment",
      "export DEBIAN_FRONTEND=noninteractive",
      
      # Update package lists
      "sudo apt-get update -y",

      # Install required dependencies
      "sudo apt-get install -y wget lsb-release gnupg curl",

      # Add MySQL's official public GPG key (Fixes NO_PUBKEY error)
      "wget -qO - https://repo.mysql.com/RPM-GPG-KEY-mysql-2022 | sudo tee /usr/share/keyrings/mysql-archive-keyring.gpg",

      # Manually configure MySQL APT repository (Use Debian Bullseye as Bookworm is not supported)
      "echo 'deb [signed-by=/usr/share/keyrings/mysql-archive-keyring.gpg] http://repo.mysql.com/apt/debian bullseye mysql-8.0' | sudo tee /etc/apt/sources.list.d/mysql.list",

      # Update package lists after adding MySQL repository
      "sudo apt-get update -y",

      # Install MySQL Server and Client
      "sudo apt-get install -y mysql-server mysql-client",

      # Enable and start MySQL service
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql",

      # Secure MySQL Installation - Change root password
      "echo \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password'; FLUSH PRIVILEGES;\" | sudo mysql",

      # Setup Flask App
      "sudo groupadd csye6225 || true",
      "sudo useradd -r -m -s /usr/sbin/nologin -g csye6225 csye6225 || true",
      "sudo mkdir -p /home/csye6225/webapp",
      "sudo chown -R csye6225:csye6225 /home/csye6225/webapp",
      "sudo -u csye6225 python3 -m venv /home/csye6225/webapp/venv",
      "sudo -u csye6225 /home/csye6225/webapp/venv/bin/pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv mysql-connector-python werkzeug pytest",

      # Create systemd service for Flask app
      "echo '[Unit]' | sudo tee /etc/systemd/system/webapp.service",
      "echo 'Description=Flask Web Application' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'After=network.target' | sudo tee -a /etc/systemd/system/webapp.service",
      "",
      "echo '[Service]' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'User=csye6225' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'Group=csye6225' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'WorkingDirectory=/home/csye6225/webapp' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'ExecStart=/home/csye6225/webapp/venv/bin/python /home/csye6225/webapp/app.py' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'Restart=always' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'Environment=FLASK_APP=app.py' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'Environment=FLASK_ENV=production' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'Environment=PATH=/home/csye6225/webapp/venv/bin:$PATH' | sudo tee -a /etc/systemd/system/webapp.service",
      "",
      "echo '[Install]' | sudo tee -a /etc/systemd/system/webapp.service",
      "echo 'WantedBy=multi-user.target' | sudo tee -a /etc/systemd/system/webapp.service",

      # Enable and start Flask service
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp",
      "sudo systemctl start webapp"
    ]
  }
}

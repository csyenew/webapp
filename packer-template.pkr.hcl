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
  default = "ami-06db4d78cb1d3bbf9"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
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

  # Provisioning step to install system dependencies, fix MySQL installation issues
  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo apt-get update -y",
      "sudo apt-get upgrade -y",

      # Ensure non-interactive package installation
      "sudo apt-get install -yq software-properties-common gnupg",

      # Add MySQL repository manually
      "wget https://dev.mysql.com/get/mysql-apt-config_0.8.20-1_all.deb",
      "sudo DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.20-1_all.deb",
      "sudo apt-get update -y",

      # Preconfigure MySQL root password
      "echo 'mysql-server mysql-server/root_password password root' | sudo debconf-set-selections",
      "echo 'mysql-server mysql-server/root_password_again password root' | sudo debconf-set-selections",

      # Install MySQL Server & Client
      "sudo apt-get install -yq mysql-server mysql-client python3-pip python3-venv",

      # Fix for MySQL installation issues
      "sudo apt-get install -f -y", 

      # Ensure MySQL starts properly
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql",

      # Create user for Flask app
      "sudo groupadd csye6225 || true",
      "sudo useradd -r -m -s /usr/sbin/nologin -g csye6225 csye6225 || true",

      # Setup Flask App directory
      "sudo mkdir -p /home/csye6225/webapp",
      "sudo chown -R csye6225:csye6225 /home/csye6225/webapp",
      "sudo -u csye6225 python3 -m venv /home/csye6225/webapp/venv",
      "sudo -u csye6225 /home/csye6225/webapp/venv/bin/pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv mysql-connector-python werkzeug pytest"
    ]
  }

  # Create systemd service for Flask app
  provisioner "shell" {
    inline = [
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
      "EOF"
    ]
  }

  # Enable and start Flask service
  provisioner "shell" {
    inline = [
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp.service",
      "sudo systemctl start webapp.service"
    ]
  }

  # Cleanup provisioner
  provisioner "shell" {
    inline = [
      "sudo apt-get autoremove -y",
      "sudo apt-get clean"
    ]
  }
}

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
  default = "subnet-046f10d11e4a68ac0"
}

variable "vpc_id" {
  type    = string
  default = "vpc-0f93b32042daa6131"
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

  encrypt_boot  = false  # ✅ FIX: Disable encryption to allow sharing

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
      "sudo -u csye6225 /home/csye6225/webapp/venv/bin/pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv mysql-connector-python werkzeug pytest"
    ]
  }

  # Create systemd service file using heredoc
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

  # Enable and start the service
  provisioner "shell" {
    inline = [
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp",
      "sudo systemctl start webapp"
    ]
  }
}
 
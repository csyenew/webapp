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

      # Install necessary dependencies
      "sudo apt-get install -y wget lsb-release gnupg",

      # Import MySQL GPG Key (Fixes missing key issue)
      "wget -qO - https://repo.mysql.com/RPM-GPG-KEY-mysql | sudo apt-key add -",

      # Download and install MySQL APT repository package
      "wget https://dev.mysql.com/get/mysql-apt-config_0.8.22-1_all.deb",
      "sudo dpkg -i mysql-apt-config_0.8.22-1_all.deb",
      "sudo apt-get update -y",

      # Install MySQL Server & Client
      "sudo apt-get install -y mysql-server mysql-client",

      # Start MySQL service
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql",

      # Secure MySQL installation (Set root password)
      "echo \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password'; FLUSH PRIVILEGES;\" | sudo mysql"
    ]
  }

  # Install Python 3 and required dependencies
  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo apt-get install -y python3 python3-pip python3-venv",
      "python3 --version",
      "pip3 --version"
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
      "User=ubuntu",
      "WorkingDirectory=/home/ubuntu/webapp",
      "ExecStart=/home/ubuntu/webapp/venv/bin/python /home/ubuntu/webapp/app.py",
      "Restart=always",
      "Environment=FLASK_APP=app.py",
      "Environment=FLASK_ENV=production",
      "Environment=PATH=/home/ubuntu/webapp/venv/bin:$PATH",
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

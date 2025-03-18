packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

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
  default = "admin"
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

locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
}

source "amazon-ebs" "debian" {
  profile       = "packer"
  ami_name      = "${var.ami_name}-${local.timestamp}"
  ami_users     = "${var.ami_users}"
  instance_type = "${var.instance_type}"
  region        = "${var.region}"
  source_ami    = "${var.source_ami}"
  ssh_username  = "${var.ssh_username}"
  subnet_id     = "${var.subnet_id}"
  tags = {
    Name        = "${var.ami_name}-${local.timestamp}"
    Environment = "${var.environment}"
  }
  vpc_id = "${var.vpc_id}"
  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    delete_on_termination = true
  }
}

build {
  sources = [
    "source.amazon-ebs.debian"
  ]

  # First create the directory
  provisioner "shell" {
    inline = [
      "sudo mkdir -p /home/admin/webapp",
      "sudo chown -R admin:admin /home/admin/webapp"
    ]
  }

  # Then upload files
  provisioner "file" {
    source      = "./"
    destination = "/home/admin/webapp"
  }

  # Run the provision commands directly
  provisioner "shell" {
    inline = [
      "#!/usr/bin/env bash",
      "set -eo pipefail",
      "export DEBIAN_FRONTEND=noninteractive",
      "echo 'Updating and installing required packages...'",
      "sudo apt-get update",
      "sudo apt-get -y install python3 python3-pip python3-venv wget",
      "echo 'Creating webapp user...'",
      "if ! id -u webapp > /dev/null 2>&1; then",
      "  sudo useradd -m -d /home/webapp webapp",
      "fi",
      "echo 'Installing CloudWatch Agent...'",
      "sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb",
      "sudo dpkg -i -E ./amazon-cloudwatch-agent.deb",
      "sudo rm -f ./amazon-cloudwatch-agent.deb",
      "echo 'Setting up Python virtual environment...'",
      "cd /home/admin/webapp",
      "python3 -m venv venv",
      "source venv/bin/activate",
      "pip install --upgrade pip",
      "pip install -r requirements.txt",
      "echo 'Setting up systemd service...'",
      "sudo cp /home/admin/webapp/webapp.service /etc/systemd/system/",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp.service",
      "sudo systemctl start webapp.service",
      "echo 'Provisioning complete!'"
    ]
  }
}
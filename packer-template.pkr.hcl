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
  default = "admin"  # Confirmed username for Ubuntu AMIs
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

# Build Configuration
build {
  sources = [
    "source.amazon-ebs.ubuntu_custom_aws"
  ]

  # Install MySQL 8.0 from Ubuntu’s official repository
  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",

      # Ensure Universe Repository is Enabled
      "sudo add-apt-repository universe -y",
      "sudo apt-get update -y",

      # Install MySQL
      "sudo apt-get install -y mysql-server mysql-client",

      # Ensure MySQL starts properly
      "sudo systemctl enable mysql",
      "sudo systemctl start mysql"
    ]
  }

  # Secure MySQL installation
  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo mysql -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';\"",
      "sudo mysql -e \"FLUSH PRIVILEGES;\""
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

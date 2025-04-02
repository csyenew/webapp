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
  default = ["241533134224", "891612581932"]
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
  ami_users     = var.ami_users
  instance_type = var.instance_type
  region        = var.region
  source_ami    = var.source_ami
  ssh_username  = var.ssh_username
  subnet_id     = var.subnet_id
  tags = {
    Name        = "${var.ami_name}-${local.timestamp}"
    Environment = var.environment
  }
  vpc_id = var.vpc_id
  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = 30
    volume_type           = "gp2"
    delete_on_termination = true
  }
}

build { 
  sources = ["source.amazon-ebs.debian"]

  # Create the app directory
  provisioner "shell" {
    inline = [
      "sudo mkdir -p /home/admin/webapp",
      "sudo chown -R admin:admin /home/admin/webapp"
    ]
  }

  # Upload app files
  provisioner "file" {
    source      = "../"
    destination = "/home/admin/webapp"
  }

  provisioner "file" {
    source      = "./requirements.txt"
    destination = "/home/admin/webapp/requirements.txt"
  }

  provisioner "file" {
    source      = "packer/webapp.service"
    destination = "/home/admin/webapp/webapp.service"
  }

  # Install the CloudWatch Agent
  provisioner "shell" {
    inline = [
      "echo Installing Unified CloudWatch Agent...",
      "wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb -O amazon-cloudwatch-agent.deb",
      "sudo dpkg -i amazon-cloudwatch-agent.deb",
      "rm amazon-cloudwatch-agent.deb"
    ]
  }

  # Upload CloudWatch config to /tmp
  provisioner "file" {
    source      = "packer/cloudwatch-config.json"
    destination = "/tmp/cloudwatch-config.json"
  }

  # Move CloudWatch config to correct location with sudo
  provisioner "shell" {
    inline = [
      "sudo mv /tmp/cloudwatch-config.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
      "sudo chown root:root /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
    ]
  }

  # Start CloudWatch Agent
  provisioner "shell" {
    inline = [
      "echo Starting CloudWatch Agent...",
      "sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s",
      "sudo systemctl enable amazon-cloudwatch-agent"
    ]
  }

  # Custom provision script
  provisioner "shell" {
    script = "packer/provision.sh"
  }
}

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
# Build Configuration for AWS and GCP
build {
  sources = [
    "source.amazon-ebs.ubuntu_custom_aws",  # Un-commented AWS source
    "source.googlecompute.ubuntu_custom_gcp"
  ]

  # Provisioning with shell script for MySQL setup and Flask app deployment
  provisioner "shell" {
  inline = [
    "echo 'export DEBIAN_FRONTEND=noninteractive' | sudo tee -a /etc/environment",
    "export DEBIAN_FRONTEND=noninteractive",

    # Update package list and upgrade all packages
    "echo 'Upgrading all packages...'",
    "sudo apt-get update -y",
    "sudo apt-get upgrade -y",

    # Add MySQL repository and install required dependencies
    "echo 'Installing MySQL dependencies...'",
    "sudo apt-get install -y wget lsb-release gnupg",
    "wget -c https://repo.mysql.com//mysql-apt-config_0.8.22-1_all.deb",
    "sudo apt-get update -y",

    # Install MySQL Server and MySQL Client
    "echo 'Installing MySQL server and client...'",
    "sudo apt-get install -y mysql-server mysql-client || { echo 'MySQL installation failed'; exit 1; }",

    # Install pip3 (needed for Python package installations)
    "echo 'Installing pip3...'",
    "sudo apt-get install -y python3-pip python3-venv || { echo 'Python installation failed'; exit 1; }",

    # Start and Enable MySQL Service
    "echo 'Starting MySQL service...'",
    "sudo systemctl enable mysql",
    "sudo systemctl start mysql",

    # Create the csye6225 group
    "echo 'Creating group csye6225...'",
    "sudo groupadd csye6225 || { echo 'Group creation failed'; exit 1; }",

    # Create a Python virtual environment
    "echo 'Creating Python virtual environment...'",
    "python3 -m venv /home/ubuntu/webapp/venv",

    # Activate the virtual environment and install dependencies
    "echo 'Activating virtual environment and installing dependencies...'",
    ". /home/ubuntu/webapp/venv/bin/activate && pip install --upgrade pip && pip install Flask==2.2.2 Flask-SQLAlchemy==3.0.2 Flask-Migrate==3.1.0 python-dotenv==0.21.0 mysql-connector-python==8.0.31 werkzeug==2.2.2 pytest==8.3.4 || exit 1",

    # Create user csye6225 with no login shell
    "echo 'Creating user csye6225 with no login shell...'",
    "sudo useradd -r -m -s /usr/sbin/nologin -g csye6225 csye6225 || { echo 'User creation failed'; exit 1; }",

    # Restart MySQL service to apply changes
    "echo 'Restarting MySQL service...'",
    "sudo systemctl restart mysql || exit 1",

    # Check MySQL installation
    "echo 'Checking MySQL installation...'",
    "mysql --version || { echo 'MySQL installation failed'; exit 1; }",

    # Check virtual environment
    "echo 'Checking virtual environment...'",
    "which python || { echo 'Virtual environment activation failed'; exit 1; }"
  ]
}






  // Create systemd service file using heredoc
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

  // Enable and start the service
  provisioner "shell" {
    inline = [
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp.service",
      "sudo systemctl start webapp.service"
    ]
  }

  // Fix broken packages and clean up
  provisioner "shell" {
    inline = [
      "sudo apt-get install -f -y",  // Fix any missing dependencies
      "sudo apt-get autoremove -y",  // Clean up unused packages
      "sudo apt-get clean"
    ]
  }
}

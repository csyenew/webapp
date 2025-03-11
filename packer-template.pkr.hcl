# Define required Packer version
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
    "which python || { echo 'Virtual environment activation failed'; exit 1; }",

    # Install Python & Dependencies
      "sudo apt-get install -y python3-pip python3-venv",
      
      # Setup Flask App
      "sudo mkdir -p /home/csye6225/webapp",
      "sudo chown -R csye6225:csye6225 /home/csye6225/webapp",
      "python3 -m venv /home/csye6225/webapp/venv"

]
  }
  # Copy Application Files
  provisioner "file" {
    source      = "app.py"
    destination = "/home/csye6225/webapp/app.py"
  }

  provisioner "file" {
    source      = "config.py"
    destination = "/home/csye6225/webapp/config.py"
  }

  provisioner "file" {
    source      = "requirements.txt"
    destination = "/home/csye6225/webapp/requirements.txt"
  }

    # Create systemd service for Flask app using a script file
  provisioner "file" {
    content = <<EOF
[Unit]
Description=Flask Web Application
After=network.target

[Service]
User=csye6225
Group=csye6225
WorkingDirectory=/home/csye6225/webapp
ExecStart=/home/csye6225/webapp/venv/bin/python /home/csye6225/webapp/app.py
Restart=always
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
Environment="PATH=/home/csye6225/webapp/venv/bin:$PATH"

[Install]
WantedBy=multi-user.target
EOF
    destination = "/tmp/webapp.service"
  }

  provisioner "shell" {
    inline = [
      "sudo mv /tmp/webapp.service /etc/systemd/system/webapp.service",
      "sudo chmod 644 /etc/systemd/system/webapp.service",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable webapp",
      "sudo systemctl start webapp"
    ]
  }
}
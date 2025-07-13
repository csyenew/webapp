# 🧩 WebApp – FastAPI-Based Cloud-Native Deployment

This project is designed to revolutionize the way software applications are managed and deployed, with a focus on zero-downtime continuous deployment on AWS. It uses a powerful combination of tools including **FastAPI**, **Packer**, **GitHub Actions**, **PostgreSQL**, and **AWS**, and demonstrates modern DevOps principles in action. The application is designed to handle asynchronous user data processing and integrates tightly with Infrastructure as Code (IaC) workflows.

---

## 🚀 Project Overview

This is a FastAPI-based web application for managing user data in **asynchronous mode**. It is tightly integrated with a CI/CD pipeline and AWS infrastructure to enable zero-downtime deployments using instance refresh strategies.

The goal was to test how distributed systems can scale across major cloud platforms (AWS, GCP, Azure), and to prove the performance capability of FastAPI by processing **2 million (20 lakh) API requests in under 5 minutes**.

---

## 🎯 Objective

- Demonstrate highly scalable REST API development using FastAPI.
- Ensure continuous deployment with no service interruption.
- Automate infrastructure creation using Packer and GitHub Actions.
- Handle millions of concurrent requests with async architecture.
- Show compatibility across AWS, Azure, and GCP for distributed systems.

---

## ⚙️ Technologies and Tools

| Category | Tools |
|---------|-------|
| **Language & Framework** | Python 3.x, FastAPI |
| **Database** | PostgreSQL |
| **Infrastructure** | AWS (EC2, SNS, AMI), Packer |
| **CI/CD** | GitHub, GitHub Actions |
| **Testing** | pytest |
| **Editor & Scripts** | Visual Studio Code, Shell Script |

---

## 🔁 Continuous Deployment & Scalability

This project uses GitHub Actions and Packer to automate the entire deployment process:

1. A pull request triggers the CI/CD pipeline.
2. GitHub Actions builds a new **Debian-based machine image** using Packer.
3. The AMI is deployed on AWS EC2.
4. An **instance refresh strategy** is used to redirect traffic to the new version without downtime.

This ensures smooth rollout and rollback of application updates in production.

---

## 🛠 Installation

### Requirements

- Python 3.x
- FastAPI (with Uvicorn)
- PostgreSQL
- `make`

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-username/webapp-fastapi.git
cd webapp-fastapi

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
make install
Environment Variables
Set your PostgreSQL configuration:

export DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
Replace placeholders with your actual database values.
▶️ Running the FastAPI Server

make runserver
This launches the FastAPI server using Uvicorn in asynchronous mode.

✅ Running Tests with pytest

pytest
This command runs all unit and integration tests to validate API functionality and database operations.

📬 API Usage

You can test the API endpoints using any REST client such as:

Postman
curl from the terminal
Example endpoints:

POST /users – Create a new user
GET /users – Get user data
PUT /users/{id} – Update a user
DELETE /users/{id} – Remove a user
(All requests and responses are in JSON format.)

📈 Deployment Process Overview

Code pushed or a pull request is raised
GitHub Actions triggers the CI pipeline
Packer creates a new AMI image
Image is deployed to AWS EC2
Existing instances are refreshed with zero downtime
🧪 Integration and Unit Testing

Unit tests for API logic and response validation
Integration tests for database interactions
Test coverage includes both typical and edge-case scenarios
📌 Conclusion

This project demonstrates how to build and deploy highly available, cloud-native applications using FastAPI, PostgreSQL, and modern DevOps tools. Through automated CI/CD, infrastructure-as-code, and asynchronous API architecture, it ensures scalability, reliability, and efficient delivery across cloud environments.

📄 License

This project is licensed under the MIT License.

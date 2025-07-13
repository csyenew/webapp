# webapp  
 
WebApp - Fast API's

Python Packer FastAPI Postgres GitHub GitHub Actions AWS SNS Visual Studio Code Shell Script

Project Overview

This project is designed to revolutionize the way software applications are managed and deployed, focusing on continuous deployment to AWS without disrupting the currently running application. It harnesses a suite of technologies including Packer for virtual machine image creation, GitHub Actions for CI/CD pipelines, FastAPI for building performant APIs, PostgreSQL for database management, and AWS for cloud infrastructure, alongside integration and unit testing to ensure a robust development lifecycle of an enterprise application.

Objective

Our primary aim is to demonstrate the efficacy of distributed systems across major cloud network providers such as AWS, GCP, and Azure, ensuring the application's ability to handle millions of concurrent requests—evidenced by our tests of 20 lakh API requests in under 5 minutes using FastAPI.
This is a Fast API based web application for managing user data in Asynchronous Mode. This application is tighly coupled with Infrastructure as code

Continuous Deployment and Scalability

By leveraging GitHub for version control and GitHub Actions for CI/CD, we ensure efficient, secure software delivery. The process starts when a pull request is raised; a Debian-based machine image is automatically created and stored in AWS. This facilitates an instance refresh that seamlessly migrates incoming traffic to the updated application version, ensuring zero downtime.

Technologies and Skills

GitHub & GitHub Actions: Utilized for version control and to automate the CI/CD pipeline, enhancing software delivery and facilitating early bug detection.

Packer: Employs Packer for creating immutable virtual machine images, simplifying deployments and updates on AWS.

FastAPI: Chosen for its ability to handle asynchronous tasks and manage millions of concurrent requests, proving critical for enterprise-level applications.

PostgreSQL: Offers robust data management capabilities, ensuring data integrity and performance.

AWS: Provides a scalable and reliable cloud platform, essential for deploying and managing our application across global regions.

Integration and Unit Testing: Ensures the application's reliability and performance through comprehensive testing strategies.

Deployment Process

The deployment process is meticulously designed to minimize disruptions. When a pull request is initiated, it triggers the CI/CD pipeline. A new machine image is created using Packer, reflecting the latest application version. This image is then deployed to AWS, where an instance refresh strategy is implemented to smoothly transition traffic to the new version, ensuring continuous availability.

Requirements

Python 3.x
Fast API : Uvicorn
Installation

Clone the repository to your local machine and cd into cloud.
Create a virtual environment in the project directory.
Activate the virtual environment.
Install the required packages using the following command:
make install
Export the database configurations to the environment.
export DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
NOTE: replace the POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB with your database configurations.
Run FastAPI server

 make runserver
Running tests with pytest

 pytest
Usage

You can test the API's using any REST client such as Postman.

Conclusion

Our project stands as a testament to the capabilities of modern DevOps practices, demonstrating how cloud technologies can be leveraged to achieve high availability, scalability, and efficient software delivery. It's a hands-on exploration into managing software applications through continuous deployment, leveraging the best practices in software development and cloud infrastructure management.

License

This project is licensed under the MIT License.

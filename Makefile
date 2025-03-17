SHELL := /bin/bash
VENV_NAME=venv

#
.EXPORT_ALL_VARIABLES:

POSTGRES_USER ?= cloud
POSTGRES_PASSWORD ?= cloud
POSTGRES_HOST ?= 127.0.0.1
POSTGRES_PORT ?= 5432
POSTGRES_DB ?= cloud
DATABASE_URL?= postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)
AWS_REGION ?= us-east-1
SNS_TOPIC_ARN ?= arn
# =============================================================================

install:
	( \
       python3 -m venv venv; \
       venv/bin/pip install -r requirements.txt; \
    )

runserver: 
	( \
	   source venv/bin/activate; \
	   uvicorn main:app --reload --host 0.0.0.0 --port 8000; \
    )

server:
	$(dir $(abspath $(firstword $(MAKEFILE_LIST))))venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

test: 
	( \
	   source venv/bin//activate; \
	   pytest; \
    )

init:
	packer init packer

fmt:
	packer fmt packer
	
validate: fmt
	packer validate packer

build: init validate
	packer build packer/debian.pkr.hcl
	
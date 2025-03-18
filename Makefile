SHELL := /bin/bash
VENV_NAME=venv
#
.EXPORT_ALL_VARIABLES:
POSTGRES_USER ?= csye6225
POSTGRES_PASSWORD ?= csye6225
POSTGRES_HOST ?= 127.0.0.1
POSTGRES_PORT ?= 5432
POSTGRES_DB ?= csye6225
S3_BUCKET ?= test-bucket
AWS_REGION ?= us-east-1
DATABASE_URL?= postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)
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
	source venv/bin/activate; \
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
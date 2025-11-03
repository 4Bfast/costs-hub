# Makefile for Lambda Cost Reporting System

.PHONY: help install install-dev test test-unit test-integration lint format clean setup-local test-local cleanup-local deploy-dev deploy-staging deploy-prod

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit -v

test-integration: ## Run integration tests only
	pytest tests/integration -v

lint: ## Run code linting
	flake8 src tests
	mypy src

format: ## Format code
	black src tests
	isort src tests

clean: ## Clean up build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

setup-local: ## Set up local development environment
	./scripts/setup-local.sh

test-local: ## Test local development environment
	./scripts/test-local.sh

cleanup-local: ## Clean up local development environment
	./scripts/cleanup-local.sh

# CDK deployment targets
deploy-dev: ## Deploy to development environment
	cd infrastructure && ./deploy.sh --environment dev

deploy-staging: ## Deploy to staging environment
	cd infrastructure && ./deploy.sh --environment staging

deploy-prod: ## Deploy to production environment
	cd infrastructure && ./deploy.sh --environment prod --require-approval any-change

# Validation targets
validate-dev: ## Validate development deployment
	cd infrastructure && ./validate-deployment.sh dev

validate-staging: ## Validate staging deployment
	cd infrastructure && ./validate-deployment.sh staging

validate-prod: ## Validate production deployment
	cd infrastructure && ./validate-deployment.sh prod

# Development workflow
dev-setup: install-dev setup-local ## Complete development setup

dev-test: test-local test ## Test local environment and run tests

dev-clean: cleanup-local clean ## Clean up everything
export PROJECTNAME=$(shell basename "$(PWD)")

.PHONY: $(shell grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk -F: '{print $$1}')

install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Running ruff check"
	@uv run ruff check .
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@mob next

check-tool: ## Manually run a single pre-commit hook
	@echo "🚀 Running pre-commit hook: $(TOOL)"
	@uv run pre-commit run $(TOOL) --all-files

upgrade: ## Upgrade all dependencies to their latest versions
	@echo "🚀 Upgrading all dependencies"
	@uv lock --upgrade

test: ## Run all unit tests
	@echo "🚀 Running unit tests"
	@PYTHONPATH=. uv run pytest -v

test-single: ## Run a single test file (usage: make test-single TEST=test_config.py)
	@echo "🚀 Running single test: $(TEST)"
	@PYTHONPATH=. uv run pytest -v tests/$(TEST)

run: ## Run the application
	@echo "🚀 Running $(PROJECTNAME)"
	@uv run python -m activity_beacon

viewer: ## Run the viewer application
	@echo "🚀 Running viewer"
	@uv run python -m activity_beacon.viewer.main

clean: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -delete
	@rm -rf build/ dist/

context: clean ## Build context file from application sources
	llm-context-builder.py --extensions .py --ignored_dirs build dist generated venv .venv .idea .aider.tags.cache.v3 --print_contents --temp_file

package: clean ## Run installer
	@uv run pyinstaller main.spec --clean

install-macosx: package ## Installs application in users Application folder
	./scripts/install-macosx.sh ActivityBeacon.app

setup: ## One command setup
	@make install-macosx
	@echo "Installation completed"

ICON_PNG ?= assets/$(PROJECTNAME)-icon.png
BASE_DIR ?= $(HOME)/Documents/Screenshots
FORCE ?= false

icons: ## Generate ICNS and ICO files from the PNG logo
	@bash assets/generate-icons.sh $(ICON_PNG)

ocr-day: ## Run Vision OCR for one day (usage: make ocr-day DATE=YYYY-MM-DD [BASE_DIR=...] [FORCE=true])
	@if [ -z "$(DATE)" ]; then echo "DATE is required (YYYY-MM-DD)"; exit 1; fi
	@./scripts/generate_ocr.sh --base-dir "$(BASE_DIR)" --date "$(DATE)" $(if $(filter true,$(FORCE)),--force,)

ocr-all: ## Run Vision OCR for all videos under BASE_DIR (usage: make ocr-all [BASE_DIR=...] [FORCE=true])
	@./scripts/generate_ocr.sh --base-dir "$(BASE_DIR)" $(if $(filter true,$(FORCE)),--force,)

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help

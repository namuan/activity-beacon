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
	@echo "🚀 Running basedpyright strict"
	@uv run basedpyright --level error
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
	@uv run python -m delta_spread

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
	./scripts/install-macosx.sh DeltaSpread.app

setup: ## One command setup
	@make install-macosx
	@echo "Installation completed"

ICON_PNG ?= assets/$(PROJECTNAME)-icon.png

icons: ## Generate ICNS and ICO files from the PNG logo
	@bash assets/generate-icons.sh $(ICON_PNG)

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help

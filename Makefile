.PHONY: install start stop status logs clean setup test

# Python virtual environment
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Application settings
APP_NAME = linkedin-job-agent
PID_FILE = ./linkedin-job-agent.pid

# Install dependencies and setup project
install: $(VENV)/bin/activate
	$(PIP) install -r requirements.txt
	$(PYTHON) -m playwright install chromium
	@echo "Installation complete. Copy .env.example to .env and configure your settings."

# Create virtual environment
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

# Setup initial configuration
setup: install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit it with your credentials."; \
	fi
	@mkdir -p data/db logs
	$(PYTHON) -c "from src.database.models import init_db; init_db()"
	@echo "Database initialized."

# Start the application in background
start:
	@if [ -f $(PID_FILE) ]; then \
		echo "Application is already running (PID: $$(cat $(PID_FILE)))"; \
		exit 1; \
	fi
	@echo "Starting $(APP_NAME)..."
	$(PYTHON) src/main.py & echo $$! > $(PID_FILE)
	@echo "Application started (PID: $$(cat $(PID_FILE)))"
	@echo "Use 'make logs' to view output or 'make stop' to stop"

# Stop the application
stop:
	@if [ ! -f $(PID_FILE) ]; then \
		echo "Application is not running"; \
		exit 1; \
	fi
	@echo "Stopping $(APP_NAME)..."
	@kill $$(cat $(PID_FILE)) && rm $(PID_FILE)
	@echo "Application stopped"

# Check application status
status:
	@if [ -f $(PID_FILE) ]; then \
		if ps -p $$(cat $(PID_FILE)) > /dev/null 2>&1; then \
			echo "Application is running (PID: $$(cat $(PID_FILE)))"; \
		else \
			echo "PID file exists but process is not running"; \
			rm $(PID_FILE); \
		fi \
	else \
		echo "Application is not running"; \
	fi

# View application logs
logs:
	@if [ -f logs/app.log ]; then \
		tail -f logs/app.log; \
	else \
		echo "No log file found. Is the application running?"; \
	fi

# View recent logs
logs-recent:
	@if [ -f logs/app.log ]; then \
		tail -50 logs/app.log; \
	else \
		echo "No log file found."; \
	fi

# Restart the application
restart: stop start

# Clean data and logs
clean:
	@read -p "This will delete all job data and logs. Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		rm -rf data/db/* logs/* *.pid; \
		echo "Data and logs cleaned"; \
	else \
		echo "Cancelled"; \
	fi

# Run tests
test:
	$(PYTHON) -m pytest tests/ -v

# Interactive mode (foreground)
run:
	$(PYTHON) src/main.py --interactive

# Show help
help:
	@echo "LinkedIn Job Agent - Available Commands:"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make setup       - Initial setup (run after install)"
	@echo "  make start       - Start application in background"
	@echo "  make stop        - Stop application"
	@echo "  make restart     - Restart application"
	@echo "  make status      - Check if application is running"
	@echo "  make logs        - View live logs"
	@echo "  make logs-recent - View recent logs"
	@echo "  make run         - Run in interactive mode"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean data and logs"
	@echo "  make help        - Show this help"
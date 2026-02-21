.PHONY: help test coverage run clean install

help:
	@echo "PicoRouter Makefile"
	@echo ""
	@echo "  make install      Install dependencies"
	@echo "  make test         Run tests"
	@echo "  make coverage     Run tests with coverage"
	@echo "  make run          Start server"
	@echo "  make tui          Start TUI"
	@echo "  make web          Start Web UI"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run Docker container"
	@echo "  make clean        Clean cache files"

install:
	pip install -r requirements.txt
	pip install flask requests textual 2>/dev/null || true

test:
	pytest tests/ -v

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=picorouter --cov-report=term-missing --cov-report=html -v
	@echo ""
	@echo "📊 Open htmlcov/index.html to view coverage report"

run:
	python picorouter.py serve

tui:
	python tui/picorouter_tui.py

web:
	python web/app.py

docker-build:
	docker build -t picorouter .

docker-run:
	docker run -p 8080:8080 picorouter

docker-compose:
	docker-compose up -d

clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage coverage.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

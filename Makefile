.PHONY: help test coverage run clean install

help:
	@echo "PicoRouter Makefile"
	@echo ""
	@echo "  make install    Install dependencies"
	@echo "  make test      Run tests"
	@echo "  make coverage  Run tests with coverage"
	@echo "  make run       Start server"
	@echo "  make clean     Clean cache files"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=picorouter --cov-report=term-missing --cov-report=html -v
	@echo ""
	@echo "📊 Open htmlcov/index.html to view coverage report"

run:
	python picorouter.py serve

clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage coverage.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

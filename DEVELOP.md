# Development

## Setup

```bash
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter
pip install -r requirements.txt
python picorouter.py config --example
python picorouter.py serve
```

## Testing

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=picorouter --cov-report=term-missing

# Integration tests (requires Ollama)
docker run -d -p 11434:11434 ollama/ollama
docker exec ollama ollama pull llama3
pytest tests/ -v --run-integration
```

## Code Style

```bash
# Syntax check
python -m py_compile picorouter/__main__.py picorouter/*.py

# Lint
pip install flake8
flake8 picorouter/ --max-line-length=100
```

## Contributing

```bash
git fork https://github.com/CCAgentOrg/picorouter
git clone https://github.com/YOUR_NAME/picorouter
git checkout -b feature/my-feature
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

Open PR at https://github.com/CCAgentOrg/picorouter/pulls

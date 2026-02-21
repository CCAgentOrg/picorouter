# Development

## Local Development Setup

### Prerequisites

- Python 3.9+
- Git
- Docker (optional)

### Clone & Install

```bash
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run Locally

```bash
# Generate config
python picorouter.py config --example

# Edit config
vim picorouter.yaml

# Start server
python picorouter.py serve
```

### Test API

```bash
# Health check
curl http://localhost:8080/health

# Chat
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'

# List models
curl http://localhost:8080/v1/models

# Stats
curl http://localhost:8080/stats
```

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=picorouter --cov-report=term-missing

# Specific test
pytest tests/test_router.py -v
```

### Integration Tests

```bash
# Start Ollama (required)
docker run -d --name ollama -p 11434:11434 ollama/ollama
ollama pull llama3

# Run integration tests
pytest tests/ -v --run-integration

# Stop Ollama
docker stop ollama
```

### Test Providers

```bash
# Test with specific profile
python picorouter.py serve --profile chat

# Test with specific provider
curl -H "X-PicoRouter-Provider: kilo" \
  -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hi"}]}'

# Test YOLO mode
curl -H "X-PicoRouter-Yolo: true" \
  -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hi"}]}'
```

---

## Docker Development

### Build Image

```bash
docker build -t picorouter:dev .
```

### Run with Hot Reload

```bash
# Mount source for development
docker run -p 8080:8080 \
  -v $(pwd):/app \
  picorouter:dev \
  python picorouter.py serve
```

### Test Docker

```bash
# Build
docker build -t picorouter:dev .

# Run
docker run -p 8080:8080 picorouter:dev

# Test
curl http://localhost:8080/health

# View logs
docker logs -f <container_id>
```

---

## Code Style

### Format

```bash
# Check syntax
python -m py_compile picorouter/__main__.py picorouter/*.py

# Lint
pip install flake8
flake8 picorouter/ --max-line-length=100
```

---

## Debugging

### Enable Verbose Logging

```bash
# Run with debug
python picorouter.py serve 2>&1 | tee debug.log
```

### Check Logs

```bash
# View request logs
python picorouter.py logs -n 20

# View stats
python picorouter.py logs -s
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Ollama not connecting | Check endpoint in config |
| Provider 429 errors | Add more providers to config |
| Key auth failing | Check key format in config |
| Port in use | Change port with `--port 8081` |

---

## Contributing

### Fork & Clone

```bash
git fork https://github.com/CCAgentOrg/picorouter
git clone https://github.com/YOUR_NAME/picorouter
```

### Create Branch

```bash
git checkout -b feature/my-feature
```

### Commit & Push

```bash
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

### Pull Request

Open a PR at https://github.com/CCAgentOrg/picorouter/pulls

---

## Release

```bash
# Update version
# Edit pyproject.toml, picorouter/__init__.py

# Create tag
git tag -a v0.0.3 -m "Release v0.0.3"
git push origin v0.0.3
```

GitHub Actions will build and release automatically.

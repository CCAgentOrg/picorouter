# Install

## Humans

### Quick Install

```bash
curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash
```

### Options

**Docker (recommended)**
```bash
docker run -p 8080:8080 ccagentorg/picorouter
```

**pip**
```bash
pip install picorouter
```

**Binary**
```bash
curl -L -o picorouter https://github.com/CCAgentOrg/picorouter/releases/latest/picorouter-linux-amd64
chmod +x picorouter
./picorouter serve
```

### Manual

```bash
git clone https://github.com/CCAgentOrg/picorouter
cd picorouter
pip install -r requirements.txt
cp config.example.yaml picorouter.yaml
python picorouter.py serve
```

---

## AI Agents / LLMs

### Endpoint
```
http://localhost:8080/v1/chat/completions
```

### Authentication
```bash
# With key
curl -H "Authorization: Bearer pico_xxx" \
  -X POST http://localhost:8080/v1/chat/completions \
  -d '{"messages":[{"role":"user","content":"Hi"}]}'

# Without key (if configured)
curl -X POST http://localhost:8080/v1/chat/completions \
  -d '{"messages":[{"role":"user","content":"Hi"}]}'
```

### Headers for Control
```bash
# Force provider
-H "X-PicoRouter-Provider: openai"

# Force profile
-H "X-PicoRouter-Profile: coding"

# Force local only
-H "X-PicoRouter-Local: true"

# Enable YOLO mode
-H "X-PicoRouter-Yolo: true"
```

### Environment for PicoRouter
```bash
# Provider keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
KILO_API_KEY=...

# PicoRouter config
PICOROUTER_API_KEY=your-secret
PICOROUTER_SECRETS_BACKEND=env
```

### Example: OpenAI-Compatible Client
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="pico_xxx"  # optional
)

response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Example: cURL
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pico_xxx" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7
  }'
```

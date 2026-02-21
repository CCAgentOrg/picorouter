# PicoRouter Setup

## One-Command Setup

```bash
# Clone & run
git clone https://github.com/CCAgentOrg/picorouter.git && \
cd picorouter && \
pip install -r requirements.txt && \
python picorouter.py serve
```

Server starts at `http://localhost:8080/v1`

---

## Step-by-Step

### 1. Clone
```bash
git clone https://github.com/CCAgentOrg/picorouter.git
cd picorouter
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. Configure
```bash
# Generate config
python picorouter.py config --example

# Edit picorouter.yaml with your API keys
```

### 4. Run
```bash
python picorouter.py serve
```

---

## Connect Your App

| App | Setting |
|-----|---------|
| OpenClaw | `baseUrl: http://localhost:8080/v1` |
| VSCode | `openai.apiBaseUrl: http://localhost:8080/v1` |
| Continue | `apiBaseUrl: http://localhost:8080/v1` |
| Claude Code | `export OPENAI_API_BASE=http://localhost:8080/v1` |

---

## Usage

```bash
# Chat
python picorouter.py chat -m "Hello"

# Logs
python picorouter.py logs -s
```

---

## Done!

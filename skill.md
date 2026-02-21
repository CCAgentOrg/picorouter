# PicoRouter Skill

This skill provides integration with PicoRouter for OpenClaw.

## Overview

PicoRouter is a minimal AI model router — local-first with intelligent cloud fallback. It's part of the Pico family (PicoClaw, PicoLM).

## Prerequisites

1. Install PicoRouter:
   ```bash
   cd /path/to/picorouter
   pip install -r requirements.txt
   ```

2. Configure PicoRouter:
   ```bash
   cp config.example.yaml picorouter.yaml
   # Edit picorouter.yaml with your settings
   ```

3. Set API keys as environment variables:
   ```bash
   export KILO_API_KEY="sk-..."
   export GROQ_API_KEY="gsk_..."
   export OPENROUTER_API_KEY="sk-or-..."
   ```

## Usage

### Start PicoRouter Server

Start the PicoRouter server in the background:

```bash
cd /root/.openclaw/workspace/picorouter
python picorouter.py serve --profile coding --port 8080
```

### Configure OpenClaw

Add to your OpenClaw config:

```json
{
  "models": {
    "providers": {
      "picorouter": {
        "baseUrl": "http://localhost:8080/v1",
        "apiKey": "any",
        "api": "openai-completions",
        "models": [
          {
            "id": "llama3",
            "name": "Local: Llama3"
          },
          {
            "id": "codellama", 
            "name": "Local: CodeLlama"
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "picorouter/llama3"
      }
    }
  }
}
```

### Profiles

Available profiles in PicoRouter:
- `chat` - General conversation
- `coding` - Code-focused tasks
- `yolo` - Aggressive (all providers)
- `claw` - OpenClaw default

### Commands

- Generate config: `python picorouter.py config`
- Example config: `python picorouter.py config --example`
- Chat directly: `python picorouter.py chat --message "Hello"`

## Benefits

- **Private**: Local models keep data on your machine
- **Free**: Ollama is unlimited and free
- **Resilient**: Cloud fallback when local isn't available  
- **Intelligent**: Content-aware routing based on prompt analysis
- **OpenAI-compatible**: Works with any LLM application

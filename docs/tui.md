# PicoRouter TUI

Terminal User Interface for PicoRouter.

## Installation

```bash
# Install textual (recommended)
pip install textual

# Or use without it (basic mode)
pip install requests
```

---

## Running TUI

```bash
# Basic
python tui/picorouter_tui.py

# With custom URL
python tui/picorouter_tui.py --url http://192.168.1.100:8080

# With API key
python tui/picorouter_tui.py --url http://localhost:8080 --api-key your_key
```

---

## Controls

| Key | Action |
|-----|--------|
| Enter | Send message |
| Ctrl+C | Quit |
| q | Quit |
| c | Clear chat |
| m | Show models |
| s | Show stats |

---

## Features

- 💬 Chat with your models
- 📊 View usage stats
- 📋 List available models
- 🧹 Clear chat history
- 🎨 Syntax highlighted messages

---

## Docker

Run TUI in Docker:

```bash
# Build
docker build -t picorouter .

# Run
docker run -it picorouter python tui/picorouter_tui.py
```

Or use docker-compose:
```bash
docker-compose run tui
```

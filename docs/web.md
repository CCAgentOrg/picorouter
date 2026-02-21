# PicoRouter Web UI

Browser-based interface for PicoRouter.

## Installation

```bash
# Install Flask
pip install flask requests
```

---

## Running

```bash
# Basic (connects to local PicoRouter)
python web/app.py

# With custom backend
PICOROUTER_URL=http://192.168.1.100:8080 python web/app.py

# With API key
PICOROUTER_KEY=your_key python web/app.py
```

Then open: **http://localhost:5000**

---

## Docker

```bash
# Using docker-compose (recommended)
docker-compose up web
```

Then open: **http://localhost:5000**

---

## Features

- 💬 Chat interface
- 📊 Real-time stats
- 🌙 Dark theme
- ⌨️ Enter to send

---

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PICOROUTER_URL` | Backend URL | http://localhost:8080 |
| `PICOROUTER_KEY` | API key | (none) |
| `PORT` | Web server port | 5000 |

---

## Embedding

You can embed the chat in your own site:

```html
<iframe 
  src="http://localhost:5000" 
  width="100%" 
  height="600px"
  style="border: none;"
></iframe>
```

---

## Customization

Edit `web/app.py` to customize:

- Colors (CSS in HTML variable)
- Default temperature
- System prompt

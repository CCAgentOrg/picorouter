# PicoRouter CLI

Command-line interface for PicoRouter.

## Installation

```bash
# Clone and install
git clone https://github.com/CCAgentOrg/picorouter.git
cd picorouter
pip install -r requirements.txt

# Or use the install script
curl -sL https://raw.githubusercontent.com/CCAgentOrg/picorouter/main/install.sh | bash
```

---

## Commands

### serve
Start the API server.

```bash
python picorouter.py serve [options]
```

**Options:**
| Flag | Description | Default |
|------|-------------|---------|
| `-p, --profile` | Profile to use | chat |
| `--host` | Bind host | 0.0.0.0 |
| `-P, --port` | Bind port | 8080 |
| `-r, --rate-limit` | Requests/min (0=off) | 60 |

**Example:**
```bash
# Basic
python picorouter.py serve

# Production
python picorouter.py serve \
  --host 127.0.0.1 \
  --port 8080 \
  --profile coding \
  --rate-limit 60
```

---

### chat
Interactive chat in terminal.

```bash
python picorouter.py chat -m "Your message"
```

**Options:**
| Flag | Description |
|------|-------------|
| `-m, --message` | Message to send (required) |
| `-p, --profile` | Profile to use |

**Example:**
```bash
python picorouter.py chat -m "Hello, how are you?"
```

---

### config
Manage configuration.

```bash
# Generate example config
python picorouter.py config --example

# Interactive config creator
python picorouter.py config
```

---

### logs
View request logs.

```bash
python picorouter.py logs [options]
```

**Options:**
| Flag | Description |
|------|-------------|
| `-s, --stats` | Show statistics |
| `-n, --limit` | Number of logs (default 20) |

**Example:**
```bash
# Show recent logs
python picorouter.py logs -n 50

# Show stats
python picorouter.py logs -s
```

---

### key
Manage API keys.

```bash
# Add new key
python picorouter.py key add -n mykey --rate-limit 60 --profiles chat,coding

# List keys
python picorouter.py key list

# Remove key
python picorouter.py key remove oldkey
```

**Options for `key add`:**
| Flag | Description |
|------|-------------|
| `-n, --name` | Key name (required) |
| `-r, --rate-limit` | Requests/min |
| `-p, --profiles` | Allowed profiles (comma) |
| `--readonly` | Chat disabled |
| `--expires` | Expiration (ISO date) |

---

## Environment Variables

```bash
# API Keys for providers
export KILO_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export OPENROUTER_API_KEY="sk-or-..."

# PicoRouter own key (optional)
export PICOROUTER_API_KEY="your-secret-key"
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start server | `python picorouter.py serve` |
| Chat | `python picorouter.py chat -m "hi"` |
| View logs | `python picorouter.py logs -s` |
| Add key | `python picorouter.py key add -n claw` |
| Generate config | `python picorouter.py config --example` |

# CLI Commands

## serve
Start the API server.

```bash
python picorouter.py serve [options]

Options:
  -p, --profile NAME    Profile to use (default: chat)
  -H, --host HOST       Host to bind (default: 0.0.0.0)
                        Use: localhost, all, tailscale, lan, or IP
  -P, --port PORT       Port to bind (default: 8080)
  -r, --rate-limit N    Requests per minute (default: 60, 0 to disable)
  -i, --show-ips        Show available network IPs
```

Examples:
```bash
# Default
python picorouter.py serve

# Specific profile
python picorouter.py serve --profile coding

# Tailscale
python picorouter.py serve --host tailscale

# Show IPs
python picorouter.py serve --show-ips
```

## chat
Interactive chat.

```bash
python picorouter.py chat -m "message" [options]

Options:
  -m, --message TEXT   Message to send (required)
  -p, --profile NAME   Profile to use
```

## config
Configuration management.

```bash
python picorouter.py config [options]

Options:
  -e, --example        Generate example config
  -o, --output FILE    Output file (default: picorouter.yaml)
```

## logs
View request logs.

```bash
python picorouter.py logs [options]

Options:
  -s, --stats         Show statistics only
  -n, --limit N       Number of logs to show (default: 20)
```

## key
API key management.

```bash
# Add key
python picorouter.py key add -n NAME [options]

Options:
  -n, --name NAME           Key name (required)
  -r, --rate-limit N        Requests per minute (default: 60)
  -p, --profiles LIST      Allowed profiles (comma-separated)
  -r, --readonly           Read-only key
  -e, --expires DATE       Expiration date (ISO format)

# List keys
python picorouter.py key list

# Remove key
python picorouter.py key remove NAME
```

## secrets
Provider API key management.

```bash
# List configured keys
python picorouter.py secrets list

# Set key
python picorouter.py secrets set -p PROVIDER -k KEY

Options:
  -p, --provider NAME   Provider name (openai, anthropic, etc.)
  -k, --key VALUE      API key value

# Show backends
python picorouter.py secrets show
```

## models
Model discovery from models.dev.

```bash
# Search models
python picorouter.py models search [options]

Options:
  --free              Free models only
  --context N         Min context length
  -p, --provider NAME Filter by provider
  -n, --limit N       Max results (default: 20)

# Sync to config
python picorouter.py models sync -o OUTPUT

# List providers
python picorouter.py models providers
```

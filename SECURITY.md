# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.0.3a  | ✅ Current        |

---

## Red Team Analysis (2026-02-21)

### Security Review Findings

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| Weak key hashing | Medium | ⚠️ Known | Only 16 chars of SHA256 used |
| No auth when keys absent | Low | By Design | Explicitly allows open access |
| Local provider SSRF | Low | ⚠️ Known | Users can configure local endpoints |
| No shell injection | ✅ Pass | Fixed | No `shell=True` calls found |
| YAML safe_load | ✅ Pass | Fixed | Uses `yaml.safe_load` |
| No secrets in logs | ✅ Pass | Fixed | Keys/tokens not logged |
| Generic errors | ✅ Pass | Fixed | Internal details hidden |

### Known Limitations

**1. Weak Key Hashing**
```python
# Current (weak)
hashlib.sha256(key.encode()).hexdigest()[:16]
```
Only 16 characters of SHA256 used for key verification. Consider migrating to bcrypt or Argon2 in future.

**2. Open Access Without Keys**
When no API keys are configured, the server allows unauthenticated access. This is by design for local development but must be secured in production.

**3. Local Provider Endpoints**
Users can configure arbitrary endpoints for local providers (Ollama, LM Studio). Ensure only trusted local services are configured.

###Mitigations in Place

- ✅ Rate limiting (60 req/min default)
- ✅ API key authentication
- ✅ Input validation (1MB request, 50 messages, 32k tokens)
- ✅ Generic error messages
- ✅ httpx timeout (120s)
- ✅ SQLite parameterized queries

---

## Reporting a Vulnerability

Found a security issue? Please report responsibly.

1. **Do NOT** open a public GitHub issue
2. Email: security@cashlessconsumer.in
3. Include: Description, Steps to reproduce, Potential impact
4. We aim to respond within 48 hours

---

## Security Features

### ✅ Authentication (Added)

Protect your API with a key:

```bash
# Via CLI
python picorouter.py serve --api-key "your-secret-key"

# Or environment variable
export PICOROUTER_API_KEY="your-secret-key"
```

Client usage:
```bash
curl -H "Authorization: Bearer your-secret-key" \
  http://localhost:8080/v1/chat/completions
```

---

### ✅ Rate Limiting (Added)

Built-in rate limiting (60 req/min by default):

```bash
# Custom rate limit
python picorouter.py serve --rate-limit 100

# Disable rate limiting
python picorouter.py serve --rate-limit 0
```

---

### ✅ Input Validation (Added)

- Request size limited to 1MB
- Messages array limited to 50 items
- `max_tokens` limited to 32000
- Whitelisted parameters only

---

### ✅ Generic Error Messages (Added)

Internal errors not exposed to clients. Detailed errors logged server-side.

---

## Best Practices

### Development
```bash
# Local only, no auth needed
python picorouter.py serve
```

### Production
```bash
# Secure: localhost only + auth + rate limit
python picorouter.py serve \
  --host 127.0.0.1 \
  --port 8080 \
  --api-key "your-secret-key" \
  --rate-limit 60
```

### Network Security

| Environment | Recommendation |
|-------------|----------------|
| Local only  | Bind to 127.0.0.1 |
| Local network | Add auth + firewall |
| Production  | Use docs/production-nginx.conf |

---

## Dependencies

Minimal attack surface:

- `pyyaml` — Config parsing
- `httpx` — HTTP client

No known CVEs in current dependencies.

---

## Changelog

-02-21** — Red- **2026 team analysis + security findings documented
- **2025-02-21** — Security policy + rate limiting + auth added

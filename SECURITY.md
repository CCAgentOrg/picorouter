# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Current        |

---

## Reporting a Vulnerability

Found a security issue? Please report responsibly.

1. **Do NOT** open a public GitHub issue
2. Email: security@cashlessconsumer.in
3. Include: Description, Steps to reproduce, Potential impact
4. We aim to respond within 48 hours

---

## Security Considerations

### 🔴 Critical — You Must Address

**1. No Authentication**
The API server has no built-in authentication. By default, anyone who can reach the server can use it.

**Mitigation:**
- Bind to `localhost` only: `--host 127.0.0.1`
- Use firewall to restrict access
- Or put behind a reverse proxy with auth (nginx, Caddy)

**2. No HTTPS**
Server runs plain HTTP. API keys and data sent in plain text.

**Mitigation:**
- Run behind a reverse proxy with TLS
- Use SSH tunneling for remote access
- Never expose to public internet directly

---

### 🟠 High — Should Address

**3. API Keys in Config**
API keys stored in plain text in `picorouter.yaml`.

**Mitigation:**
- Use environment variables instead:
  ```bash
  export KILO_API_KEY="sk-..."
  export GROQ_API_KEY="gsk_..."
  ```
- Restrict file permissions: `chmod 600 picorouter.yaml`

**4. No Rate Limiting**
No built-in rate limiting. Vulnerable to abuse/cost spikes.

**Mitigation:**
- Add rate limiting at reverse proxy level
- Use cloud provider's rate limits
- Monitor `/stats` endpoint

---

### 🟡 Medium — Consider

**5. Verbose Error Messages**
Errors may leak internal details in production.

**Mitigation:**
- Catch exceptions and return generic messages
- Log detailed errors server-side only

**6. No Input Validation**
Some endpoints don't validate input thoroughly.

**Current behavior:**
- `/logs?limit=N` accepts any integer
- `messages` field accepts any JSON

**Mitigation:**
- Add input sanitization
- Limit request sizes

---

## Best Practices

### Production Deployment

```bash
# 1. Don't expose to internet
python picorouter.py serve --host 127.0.0.1 --port 8080

# 2. Use environment variables for secrets
export KILO_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."

# 3. Secure config file
chmod 600 picorouter.yaml

# 4. Run behind nginx with auth
# See: docs/production-nginx.conf
```

### Network Security

| Environment | Recommendation |
|-------------|----------------|
| Local only  | Bind to 127.0.0.1 |
| Local network | Firewall rules |
| Production  | Reverse proxy + HTTPS + auth |

---

## Security Audit Findings

Last audit: February 2025

| Issue | Severity | Status |
|-------|----------|--------|
| No authentication | Critical | Mitigated via docs |
| No HTTPS | Critical | Mitigated via docs |
| API keys in config | High | Use env vars |
| No rate limiting | High | Manual mitigation |
| Error message leaks | Medium | Accepted risk |
| Input validation | Medium | Accepted risk |

---

## Dependencies

We aim to keep dependencies minimal and secure:

- `pyyaml` — Config parsing
- `httpx` — HTTP client

No known CVEs in current dependencies.

---

## Changelog

- **2025-02-21** — Initial security policy

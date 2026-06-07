# ⚠️ EDUCATIONAL & SECURITY TESTING PURPOSE ONLY

**This repository is intended for:**

- 🛡️ **Security awareness training** - Teaching users to recognize social engineering attacks
- 🔬 **Penetration testing** - Authorized security assessments in controlled environments
- 📚 **Educational research** - Learning about phishing techniques and defense
- 🏢 **Internal corporate security testing** - With proper authorization

---

## 🚨 WARNING

**DO NOT use this code for:**
- ❌ Malicious purposes
- ❌ Unauthorized access to systems
- ❌ Attacking systems without explicit permission
- ❌ Any illegal activities

This project demonstrates common social engineering techniques used by attackers. Only use in environments where you have **explicit written authorization** to conduct security testing.

---

## 📖 What This Project Demonstrates

This is a phishing awareness simulation tool that demonstrates:

1. **Clipboard Injection** - How attackers can trick users into copying malicious commands
2. **WebDAV Exploitation** - Abusing Windows file handling protocols
3. **Social Engineering** - Creating convincing fake login pages to steal credentials
4. **Search-MS Attacks** - Leveraging Windows search protocol for file-based attacks

## 🛡️ How to Defend Against These Attacks

- **Never paste commands** from websites into terminals
- **Verify URLs** before entering credentials
- **Check file sources** before downloading
- **Report suspicious** pages to IT security
- **Enable 2FA** on all accounts

---

## 🔧 Setup for Authorized Testing

```bash
# Install dependencies
uv sync

# Run the server (requires port 80)
uv run python server.py

# Access the phishing page
http://localhost/claude
```

---

## 🌐 Cloudflare VPS Deployment

### Mode 1: Cloudflare Flexible (Recommended for testing)
- Server runs HTTP on port 80
- Cloudflare auto-encrypts traffic
- No cert needed on server

```yaml
# config/config.yaml
server:
  port: 80
  ssl: false

cloudflare:
  enabled: true
  ssl_mode: "flexible"
```

### Mode 2: Cloudflare Full (with self-signed cert)
- Server runs HTTPS on port 443 with self-signed cert
- Cloudflare accepts self-signed cert
- Better security than Flexible

**1. Generate self-signed certificate:**
```bash
bash generate_cert.sh yourdomain.com
```

**2. Update config:**
```yaml
# config/config.yaml
server:
  port: 443
  ssl: true
  cert_file: "cert.pem"
  key_file: "key.pem"

cloudflare:
  enabled: true
  ssl_mode: "full"
```

**3. Run server:**
```bash
uv run python server.py
```

### Cloudflare SSL Settings:
| Mode | Server SSL | Cert Required |
|------|-----------|---------------|
| Flexible | No | No |
| Full | Yes | Self-signed OK |
| Full (Strict) | Yes | Let's Encrypt recommended |

---

## 📋 Files Overview

| File | Purpose |
|------|---------|
| `server.py` | Python server with WebDAV support |
| `payload/payload.txt` | Test payload for clipboard demonstration |
| `dav/` | WebDAV directory with test files |
| `templates/` | Phishing page templates |
| `config/config.yaml` | Server configuration |

---

## ✅ Legal Disclaimer

By using this project, you agree that:

1. You have proper authorization to test the target environment
2. You understand the legal implications of security testing
3. You will not hold the developer responsible for misuse
4. You will use this knowledge to improve security, not exploit vulnerabilities

**Unauthorized access to computer systems is illegal. Always get written permission before security testing.**
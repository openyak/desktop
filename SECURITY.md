# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OpenYak, please report it responsibly.

**Email:** [support@waxis.org](mailto:support@waxis.org)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Do not** open a public GitHub issue for security vulnerabilities.

## Response Timeline

- **Acknowledgment:** within 48 hours
- **Initial assessment:** within 7 days
- **Fix or mitigation:** depends on severity, typically within 30 days

## How OpenYak Handles Your Data

OpenYak is designed with local-first privacy:

- **Files, conversations, and memory** are stored on your device. Nothing is uploaded to any server.
- **Cloud model usage** sends only your prompt text directly to the model provider's API (OpenAI, Anthropic, etc.). OpenYak does not proxy, log, or store these requests.
- **Local model usage** (via Ollama) keeps everything on your machine. No network requests are made.
- **No telemetry, no analytics, no tracking.** OpenYak does not collect usage data.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release | ✅ |
| Previous minor | Best effort |
| Older | ❌ |

We recommend always using the [latest release](https://github.com/openyak/desktop/releases/latest).

## Scope

The following are in scope for security reports:

- Local file access vulnerabilities (unauthorized read/write)
- Data leakage to unintended third parties
- Code execution vulnerabilities in tool/bash execution
- MCP connector security issues
- Authentication/authorization bypass in remote access feature

Out of scope:

- Vulnerabilities in third-party model provider APIs
- Social engineering attacks
- Denial of service against local application

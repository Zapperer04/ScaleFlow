# Security Policy

We take the security of ScaleFlow seriously. This document outlines vulnerability reporting, supported versions, and built-in guardrails.

## Supported Versions

Only the latest frozen release receives security patches:

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| < 1.0 | No |

## Reporting a Vulnerability

Please report vulnerabilities to the maintainers at `security@scaleflow-mrrag.org`. We strive to respond to all reports within 48 hours and provide a patch within 14 days.

## Built-in Security Safeguards

- **Input Guards**: The API Gateway validates uploaded document structure, rejecting path traversals (e.g. `../../etc/passwd`) and malformed file headers.
- **Rate Limiting**: Sliding-window limiter blocks malicious DDoS or brute-force queries.
- **Resource Governance**: Aborts processing if memory usage exceeds 1.5GB or document size triggers chunk limits, preventing Denial-of-Service (DoS) memory exhaustion.

These guards help keep the platform **Production Qualified under the evaluated benchmark suite**.

---
name: promax-secure-provider-audit
description: Threat-model authenticated AI-provider requests, secrets, redirects, paid attempts and download trust boundaries before shipping PODBot.
---

# PODBot ProMax: provider security audit

Grounded in systematic debugging / verification from obra/superpowers and Trail of Bits' insecure-defaults and sharp-edges audit methodologies. These are project-specific original instructions, not third-party scripts.

## Workflow
1. Identify the trust boundaries: local API key, service endpoint, proxy, redirects, third-party image URL, response JSON and user-visible exceptions.
2. Inspect **all** network paths in `provider_catalog.py`, `providers.py`, and `model_discovery.py`. Do not stop after finding one redirect vulnerability: look for sibling transports and alternative pathways.
3. No authenticated urllib request may use automatic redirects. Use `auth_transport.open_authenticated` with an exact approved HTTPS host; treat any 3xx as a failure and do not resend credentials.
4. Prefer API keys in headers (not query strings), never logs, print files, manifests, GitHub artifacts or prompts. Ensure invalid hosts are rejected before network activity.
5. Respect the local per-provider attempt cap and explicit consent. Never retry billable generation automatically, even after a timeout or HTTP error.
6. Write targeted mocked regression tests for bad URLs, token-bearing cross-host redirects and provider adapter integrations. Add adversarial tests that fail if insecure `urlopen` becomes reachable.
7. Verify on an actual Windows CI run. Green mocked tests do not validate real provider credits, access or transparency; that is a separately consented paid probe.

## References
- https://github.com/trailofbits/skills (insecure-defaults, sharp-edges, audit-context-building)
- https://github.com/obra/superpowers (systematic-debugging, verification-before-completion)

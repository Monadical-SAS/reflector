# Documentation TODO - PR #778 Review Comments

Remaining items from Tito's review. See CHANGES.md for completed items.

---

## Remaining Items

| File | Issue | Priority | Notes |
|------|-------|----------|-------|
| `intro.md:10` | Add screenshots | Low | Requires running app to capture |
| `file-pipeline.md:47` | chunk_size example shows 30s | Low | Unclear what example config should show (~16s actual) |
| `self-hosted-gpu-setup.md:235` | systemd template in repo | Medium | Code task - create `/gpu/self_hosted/reflector-gpu.service` |
| `installation/overview.md:85` | uv tool install clarification | Low | Original comment unclear |
| `installation/overview.md:101` | "Why systemd?" clarification | Low | Context seems sufficient |
| `installation/overview.md:271` | Caddyfile copy removal | Low | Keeping for clarity |

---

## Skipped (Decided Not To Fix)

| File | Issue | Reason |
|------|-------|--------|
| `installation/overview.md:40` | Model size requirements | Uncertain about exact requirements |
| `installation/overview.md:136` | WebRTC ports | Handled by Daily/Whereby, not us |
| `installation/overview.md:136` | Security section | Risk of incomplete/misleading docs |
| `installation/overview.md:179` | AWS setup order | Low priority, works as-is |
| `installation/overview.md:410` | Redundant next steps | Issue doesn't exist (file ends at 401) |

---

## Completed

See CHANGES.md for full list. Summary:

### Removals (9)
- Encrypted data storage, session management, analytics claims
- "coming soon" GPU, 30-second segments, CPU optimization
- Encryption at rest, manual migrations, modprobe commands

### Fixes (9)
- WebRTC + Daily/Whereby, 4 API endpoints, Docker docs link
- NVIDIA steps merged, compose.yml referenced, cross-reference duplicate
- tee→nano, MOV format, troubleshooting link

### Previously Fixed (7)
- Blog removal, Daily.co added, rate limiting removed (x2)
- PII claim removed, python→yaml, LUFS removed

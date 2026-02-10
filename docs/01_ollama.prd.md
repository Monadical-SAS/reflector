# PRD: Local LLM Inference for Reflector

## Business Context

Reflector currently uses a remote LLM endpoint (configurable via `LLM_URL`) for all post-transcription intelligence: topic detection, title generation, subject extraction, summarization, action item identification. The default model is `microsoft/phi-4`.

**Goal**: Run all LLM inference locally on developer machines (and optionally in self-hosted production), eliminating dependence on external LLM API providers. Zero cloud LLM costs, full data privacy, offline-capable development. One setup script, then `docker compose up` works.

---

## Current Architecture

### Single abstraction layer: `server/reflector/llm.py`

All LLM calls go through one `LLM` class wrapping LlamaIndex's `OpenAILike` client.

**Env variables** (`server/reflector/settings.py:73-84`):

| Variable | Default | Purpose |
|---|---|---|
| `LLM_MODEL` | `microsoft/phi-4` | Model name |
| `LLM_URL` | `None` (falls back to OpenAI) | Endpoint URL |
| `LLM_API_KEY` | required | Auth key |
| `LLM_CONTEXT_WINDOW` | `16000` | Token limit |
| `LLM_PARSE_MAX_RETRIES` | `3` | JSON validation retries |
| `LLM_STRUCTURED_RESPONSE_TIMEOUT` | `300` | Timeout (seconds) |

### Call flow

```
Hatchet workflows / Legacy processors
  -> LLM.get_response() or LLM.get_structured_response()
    -> LlamaIndex TreeSummarize + StructuredOutputWorkflow
      -> OpenAILike client (is_chat_model=True, is_function_calling_model=False)
        -> LLM_URL endpoint (OpenAI-compatible API)
```

### LLM call inventory (per transcript, ~9-15 calls)

| Task | Method | Pydantic Model | Input Size | Temp |
|---|---|---|---|---|
| Topic detection (per chunk) | `get_structured_response` | `TopicResponse` | ~500 words/chunk | 0.9 |
| Title generation | `get_response` | plain string | topic titles list | 0.5 |
| Subject extraction | `get_structured_response` | `SubjectsResponse` | full transcript | 0.4 |
| Detailed summary (per subject) | `get_response` | plain string | full transcript | 0.4 |
| Paragraph summary (per subject) | `get_response` | plain string | detailed summary | 0.4 |
| Recap | `get_response` | plain string | combined summaries | 0.4 |
| Action items | `get_structured_response` | `ActionItemsResponse` | full transcript | 0.4 |
| Participants (optional) | `get_structured_response` | `ParticipantsResponse` | full transcript | 0.4 |
| Transcription type (optional) | `get_structured_response` | `TranscriptionTypeResponse` | full transcript | 0.4 |

### Structured output mechanism

Two-step process in `StructuredOutputWorkflow`:
1. `TreeSummarize.aget_response()` -- hierarchical summarization of long text
2. `Settings.llm.acomplete()` -- formats analysis as JSON matching Pydantic schema

Validation retry: on Pydantic parse failure, error message fed back to LLM, up to 3 retries. No function calling used -- pure JSON text parsing.

### Key dependencies

- `llama-index>=0.12.52`
- `llama-index-llms-openai-like>=0.4.0`
- No embeddings, no streaming, no vision

### Concurrency

- Hatchet rate limit: 10 concurrent LLM calls/sec (`hatchet/constants.py`)
- LLM worker pool: 10 slots (`run_workers_llm.py`)
- Fan-out: up to 20 concurrent topic chunk workflows

---

## Requirements

### Must Have
- Local LLM inference on developer Mac (M-series Apple Silicon) with Metal GPU
- Local LLM inference on Linux with NVIDIA GPU
- OpenAI-compatible API endpoint (drop-in for `LLM_URL`)
- Reliable JSON structured output (Pydantic schema compliance)
- 16K+ context window
- Works with existing `LLM` class -- config change only, no code rewrite
- Model persistence across restarts
- **No Docker Desktop dependency** -- must work with OrbStack, plain Docker Engine
- **Single setup script** -- developer runs one command, then `docker compose up` works

### Should Have
- Docker Compose profile for Linux NVIDIA GPU (containerized Ollama)
- Reasonable inference speed (>10 tok/s for chosen model)
- Auto-pull model on first setup

### Nice to Have
- CPU-only fallback for CI/testing
- Docker Compose profile for CPU-only Ollama

---

## Critical Mac Constraint

**Docker containers on macOS cannot access Apple Silicon GPU.** This applies to Docker Desktop, OrbStack, and all other Mac container runtimes. Ollama in Docker on Mac is CPU-only (~5-6x slower than native Metal).

**Docker Model Runner (DMR)** bypasses this by running llama.cpp as a native host process, but it **requires Docker Desktop 4.41+** -- not available in OrbStack or plain Docker Engine. DMR is not a viable option for this project.

**Solution**: Run Ollama natively on Mac (Metal GPU), run it containerized on Linux (NVIDIA GPU). A setup script handles the difference.

### Performance (approximate, Q4_K_M quantization)

| Model | Mac Native (Metal) | Docker on Mac (CPU) | Linux + RTX 4090 |
|---|---|---|---|
| 7B | 25-40 tok/s | 8-12 tok/s | 60-70 tok/s |
| 14B | 25-40 tok/s (M3/M4 Pro) | 4-7 tok/s | 40-60 tok/s |

---

## Inference Engine: Ollama

Ollama wins over alternatives for this project:
- Built-in model management (`ollama pull`)
- OpenAI-compatible API at `/v1/chat/completions` (drop-in for `LLM_URL`)
- Native Mac Metal GPU support
- Official Docker image with NVIDIA GPU support on Linux
- `json_schema` response format support (grammar-based constrained decoding via llama.cpp)
- MIT license, mature, widely adopted

Other engines (vLLM, llama.cpp direct, LocalAI) either lack Mac GPU support in Docker, require manual model management, or add unnecessary complexity. The `LLM_URL` env var already accepts any OpenAI-compatible endpoint -- developers who prefer another engine can point at it manually.

---

## Model Comparison (for Structured Output)

| Model | Params | RAM (Q4) | JSON Quality | Notes |
|---|---|---|---|---|
| **Qwen 2.5 14B** | 14B | ~10 GB | Excellent | Explicitly optimized for JSON. Best open-source at this size. |
| **Qwen 3 8B** | 8B | ~7 GB | Excellent | Outperforms Qwen 2.5 14B on 15 benchmarks. Lighter. |
| **Qwen 2.5 7B** | 7B | ~6 GB | Very good | Good if RAM constrained. |
| Phi-4 | 14B | ~10 GB | Good | Current default. Not optimized for JSON specifically. |
| Llama 3.1 8B | 8B | ~6 GB | Good | Higher JSON parser errors than Qwen. |
| Mistral Small 3 | 24B | ~16 GB | Very good | Apache 2.0. Needs 32GB+ machine. |

**Recommendation**: **Qwen 2.5 14B** (quality) or **Qwen 3 8B** (lighter, nearly same quality). Both outperform the current `phi-4` default for structured output tasks.

---

## Proposed Architecture

### Hybrid: Native Ollama on Mac, Containerized Ollama on Linux

```
Mac developer:
  ┌────────────────────┐
  │ Native Ollama      │ ◄── Metal GPU, :11434
  │ (host process)     │
  └────────┬───────────┘
           │ host.docker.internal:11434
  ┌────────┴───────────────────────────────────┐
  │ Docker (OrbStack / Docker Engine)          │
  │ postgres, redis, hatchet, server,          │
  │ hatchet-worker-cpu, hatchet-worker-llm     │
  │   LLM_URL=http://host.docker.internal:11434/v1  │
  └────────────────────────────────────────────┘

Linux server (--profile ollama-gpu):
  ┌────────────────────────────────────────────┐
  │ Docker Engine                              │
  │ ┌───────────────┐                          │
  │ │ ollama        │ ◄── NVIDIA GPU, :11434   │
  │ │ (container)   │                          │
  │ └───────────────┘                          │
  │ postgres, redis, hatchet, server,          │
  │ hatchet-worker-cpu, hatchet-worker-llm     │
  │   LLM_URL=http://ollama:11434/v1          │
  └────────────────────────────────────────────┘
```

### How it works

1. **Setup script** (`scripts/setup-local-llm.sh`): detects OS, installs/starts Ollama, pulls model, writes `.env` vars
2. **Docker Compose profiles**: `ollama-gpu` (Linux+NVIDIA), `ollama-cpu` (Linux CPU-only). No profile on Mac (native Ollama).
3. **`extra_hosts`** on `hatchet-worker-llm`: maps `host.docker.internal` so containers can reach host Ollama on Mac
4. **.env**: `LLM_URL` defaults to `http://host.docker.internal:11434/v1` (works on Mac); overridden to `http://ollama:11434/v1` on Linux with profile

### .env changes

```bash
# Local LLM via Ollama
# Setup: ./scripts/setup-local-llm.sh
LLM_URL=http://host.docker.internal:11434/v1
LLM_MODEL=qwen2.5:14b
LLM_API_KEY=not-needed
LLM_CONTEXT_WINDOW=16000
```

### Docker Compose changes

**`docker-compose.yml`** — `extra_hosts` added to `server` and `hatchet-worker-llm` so containers can reach host Ollama on Mac:
```yaml
  hatchet-worker-llm:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**`docker-compose.standalone.yml`** — Ollama services for Linux (not in main compose, only used with `-f`):
```yaml
# Usage: docker compose -f docker-compose.yml -f docker-compose.standalone.yml --profile ollama-gpu up -d
services:
  ollama:
    image: ollama/ollama:latest
    profiles: ["ollama-gpu"]
    # ... NVIDIA GPU passthrough
  ollama-cpu:
    image: ollama/ollama:latest
    profiles: ["ollama-cpu"]
    # ... CPU-only fallback
```

Mac devs never touch `docker-compose.standalone.yml` — Ollama runs natively. The standalone file is for Linux deployment and will grow to include other local-only services (e.g. MinIO for S3) as the standalone story expands.

### Known gotchas

1. **OrbStack `host.docker.internal`**: OrbStack uses `host.internal` by default, but also supports `host.docker.internal` with `extra_hosts: host-gateway`.
2. **Linux `host.docker.internal`**: requires `extra_hosts: - "host.docker.internal:host-gateway"` since Docker Engine doesn't add it automatically.
3. **Ollama binding on Linux**: if running natively (not in container), must use `OLLAMA_HOST=0.0.0.0` so containers can reach it via bridge IP.
4. **Cold start**: Ollama loads model on first request (~5-10s). Unloads after 5min idle. Set `OLLAMA_KEEP_ALIVE=-1` to keep loaded.
5. **Concurrent requests**: Ollama queues requests to single llama.cpp instance. With 10 Hatchet LLM worker slots, expect heavy queuing. Reduce for local dev.

---

## Risk Assessment

### High risk: Structured output reliability

Local models may produce malformed JSON more often. Current retry mechanism (3 attempts) assumes the model can self-correct.

**Mitigation**: Qwen 2.5 is explicitly optimized for JSON. Ollama supports `response_format: {type: "json_schema"}` for grammar-based constrained decoding, forcing valid JSON at the token level. `response_format` is now passed in `StructuredOutputWorkflow.extract()` (Task 2, already implemented). Retry mechanism still functions as fallback.

**Resolved**: `OpenAILike.acomplete()` does pass `response_format` through to the HTTP request (verified via code inspection and tests).

### Medium risk: Performance for fan-out workflows

~18 LLM calls per transcript at ~3-5s each locally = ~60-90s total (vs ~10-20s cloud). Acceptable for background processing.

**Mitigation**: Reduce Hatchet concurrency for local dev. Use smaller model (Qwen 2.5 7B or Qwen 3 8B) for faster iteration.

### Low risk: Model quality degradation

Qwen 2.5 14B benchmarks competitively with GPT-4o-mini for summarization/extraction. Sufficient for meeting transcript analysis.

---

## Open Questions

1. **Model choice: Qwen 2.5 14B vs Qwen 3 8B.** Qwen 3 8B reportedly outperforms Qwen 2.5 14B on many benchmarks and needs less RAM. Need to test structured output quality on our specific prompts.

2. **RAM allocation on Mac.** 14B Q4 = ~10 GB for weights + KV cache. On 16GB Mac, limited headroom for Docker VM + services. 32GB+ recommended. 7B/8B model may be necessary for 16GB machines.

3. **Ollama concurrent request handling.** With 10 Hatchet LLM worker slots making parallel requests, expect heavy queuing. Need to benchmark and likely reduce `LLM_RATE_LIMIT_PER_SECOND` and worker slots for local dev.

4. **TreeSummarize behavior with local models.** Multi-step hierarchical reduction may be significantly slower with local inference. Need to measure.

---

## Implementation Phases

### Phase 1: Setup script + Docker Compose integration
- Create `scripts/setup-local-llm.sh` that detects OS, ensures Ollama, pulls model, writes env vars
- Add Ollama services to `docker-compose.yml` with profiles (`ollama-gpu`, `ollama-cpu`)
- Add `extra_hosts` to `hatchet-worker-llm` for host Ollama access
- Update `server/.env.example` with Ollama defaults

### Phase 2: Grammar-based structured output (DONE)
- Pass `response_format` with Pydantic JSON schema in `StructuredOutputWorkflow.extract()`
- Verified: `OpenAILike.acomplete()` passes `response_format` through
- Tests added and passing

### Phase 3: Validate end-to-end
- Process test transcript against local Ollama
- Verify structured output (topics, summaries, titles, participants)
- Measure latency per LLM call type
- Compare quality with remote endpoint

### Phase 4: Tune for local performance
- Adjust Hatchet rate limits / worker slots for local inference speed
- Benchmark and document expected processing times
- Test with different model sizes (7B vs 14B)

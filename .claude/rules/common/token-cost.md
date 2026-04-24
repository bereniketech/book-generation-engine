# Token Cost & Usage Limits

## 1. Model Routing (pick the cheapest model that can do the job)

| Task type | Model | Why |
|---|---|---|
| Boilerplate, scaffolding, simple edits | Haiku 4.5 | 19× cheaper than Opus |
| Feature development, multi-file changes | Sonnet 4.6 | Best cost/quality for coding |
| Architecture decisions, hard trade-offs | Opus 4.6 via advisor tool | Advisor pattern — Opus runs selectively, not end-to-end |

**Rule:** Never run Opus as the executor for full-session work. Use it as an advisor (`type: advisor_20260301`, `max_uses: 2–4`).

---

## 2. Prompt Caching (cuts repeated-prefix cost 90 %+)

Structure every multi-turn API call so stable content comes first:

```
[system prompt]          ← mark cache_control: ephemeral at end of system block
[long static context]    ← docs, codebase, rules loaded once
[few-shot examples]      ← stable, cache-eligible
[conversation history]   ← grows each turn
[current user message]   ← always last, never cached
```

**Rule:** Place `cache_control: {"type": "ephemeral"}` after your last static block. Do not change the cached prefix between turns — any edit invalidates the cache.

Cache TTL is 5 minutes. Keep turns under 5 min for cache hits, or re-send the full prefix to reset the TTL.

---

## 3. Context Budget Allocation

Hard limits (Claude API):

| Model | Context window | Safe working limit |
|---|---|---|
| Haiku 4.5 | 200 k tokens | 160 k (stop new work at 80 %) |
| Sonnet 4.6 | 200 k tokens | 160 k |
| Opus 4.6 | 200 k tokens | 160 k |

Budget allocation per session:

```
~40 % — skills + rules loaded via @imports
~20 % — conversation history
~20 % — current task context (files read, tool results)
~20 % — reserved for output + thinking
```

**Rule:** If tool call count exceeds 40 or context feel heavy, run `/compact` at the next phase boundary — not mid-task.

---

## 4. Context Hygiene — What NOT to load

- Do not `@`-import skills that are not used in the current task.
- Do not `Read` entire large files when a `Grep` or targeted read suffices.
- Do not re-read files you just edited — the edit tool confirms success.
- Do not load agent files proactively; invoke them on-demand with `@agent-name`.
- Avoid reading `node_modules/`, build dirs, or generated files — add them to `.claudeignore`.

---

## 5. Rate Limit Avoidance

Anthropic rate limits are per-minute token buckets (input + output combined).

Strategies:
- **Batch small tasks** — one large request is cheaper and less likely to hit RPM limits than many small ones.
- **Use streaming** for long outputs — avoids timeout; start consuming tokens before generation completes.
- **Exponential back-off** on `429` responses: start at 1 s, double each retry, cap at 60 s.
- **Spread parallel agents** — when running multi-agent workflows, stagger launches by 2–5 s to avoid burst spikes.
- **Prefer Haiku for worker agents** — higher Haiku TPM quota than Sonnet/Opus.

```python
import time, anthropic
client = anthropic.Anthropic()

def call_with_backoff(fn, retries=5):
    delay = 1
    for attempt in range(retries):
        try:
            return fn()
        except anthropic.RateLimitError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
```

---

## 6. Output Token Discipline

Output tokens cost 3–5× more than input tokens on a per-token basis.

**Rules:**
- Ask for structured output (JSON, bullet lists) over verbose prose — models produce less filler.
- Set `max_tokens` explicitly; do not leave it unbounded for tasks with predictable output size.
- Avoid asking the model to "explain step by step" when you only need the result.
- In multi-agent systems, have worker agents return only what the orchestrator needs — not full reasoning traces.

---

## 7. Session Cost Tracking

The `cost-tracker` hook logs every session to `~/.claude/metrics/costs.jsonl`.

Check spend drift:
```bash
# Total spend last 7 days
jq -r '.estimated_cost_usd' ~/.claude/metrics/costs.jsonl | \
  awk '{s+=$1} END {printf "Total: $%.4f\n", s}'

# Per-model breakdown
jq -r '[.model, .estimated_cost_usd] | @tsv' ~/.claude/metrics/costs.jsonl | \
  sort | awk '{s[$1]+=$2} END {for (m in s) printf "%s\t$%.4f\n", m, s[m]}'
```

**Rule:** If a single session exceeds $0.50, review whether the model choice and context load were appropriate. Common causes: Opus running end-to-end, full codebase loaded via `Read .`, or very long conversation without a `/compact`.

# Duecare incident runbook

> The on-call playbook. Each entry: **symptom**, **first
> diagnostic**, **mitigation**, **post-incident**.
> Anchored to the alerts in
> [`infra/observability/prometheus/rules.yml`](../infra/observability/prometheus/rules.yml).

## Severity convention

- **P0** — service down, data loss, security breach. Page on-call.
- **P1** — SLO breach (error rate > 0.5% or p95 > 8s for ≥ 10m).
  Page on-call.
- **P2** — saturation warning, cosmetic issue. Open ticket.

---

## Chat server down (P0)

**Alert:** `DuecareChatDown` — `up{job="duecare-chat"} == 0` for 2m.

**First diagnostic** (5 minutes):

```bash
# Is the deployment / pod healthy?
kubectl -n duecare get deploy duecare-chat
kubectl -n duecare get pods -l app.kubernetes.io/component=chat
kubectl -n duecare describe pod -l app.kubernetes.io/component=chat | tail -50

# What did the pod log right before it died?
kubectl -n duecare logs -l app.kubernetes.io/component=chat --tail=200 --previous
```

**Common causes:**

1. **OOMKilled** — model load + KV cache exceeded the memory limit.
   Check: `kubectl describe pod ... | grep -A2 "Last State"`.
   Mitigation: raise `chat.resources.limits.memory` in
   `values.yaml`; use a smaller model (`gemma3:1b` or `gemma4:e2b`
   instead of `gemma4:e4b`).
2. **Image pull failure** — registry rate-limit or auth issue.
   Mitigation: temporarily scale to 0 and back, or pin to a
   specific tag instead of `:latest`.
3. **Healthcheck failure** — `/healthz` 500'd long enough that the
   liveness probe killed the pod. Mitigation: check Loki for the
   500 response trace; fix the underlying error.

**Mitigation:**

```bash
# Roll back to the previous image
helm rollback duecare

# Or scale to zero, fix, then scale back up
kubectl -n duecare scale deploy duecare-chat --replicas=0
# (apply fix)
kubectl -n duecare scale deploy duecare-chat --replicas=2
```

**Post-incident:** add a regression test, update the runbook entry
with what you learned, file a ticket if a values default needs
revisiting.

---

## Chat error rate > 0.5% (P1)

**Alert:** `DuecareChatHighErrorRate` — error fraction > 0.5% for 5m.

**First diagnostic:**

```promql
# Which status codes are firing?
sum by (status) (rate(duecare_chat_requests_total{status=~"5.."}[5m]))

# Which routes?
sum by (route) (rate(duecare_chat_requests_total{status=~"5.."}[5m]))

# Which tenants?
sum by (tenant) (rate(duecare_chat_requests_total{status=~"5.."}[5m]))
```

In Grafana → "Duecare overview" dashboard → "Recent chat errors
(Loki)" panel for stack traces.

**Common causes:**

1. **Ollama crashed / model corrupted** — chat returns 5xx because
   the model call fails. Check `up{job="ollama"}`. Restart the
   Ollama pod; it'll re-pull the model on next startup.
2. **Tenant abuse** — one tenant is sending malformed payloads.
   Check the per-tenant breakdown above; rate-limit them at the
   edge or reject at the validator.
3. **Bad deploy** — error rate spiked at the time of the last
   deploy. Roll back: `helm rollback duecare`.

---

## Chat p95 latency > 8s (P1)

**Alert:** `DuecareChatHighLatency` — p95 > 8s for 10m.

**First diagnostic:**

```promql
# Which harness layer is slow?
histogram_quantile(0.95,
  sum(rate(duecare_chat_request_duration_seconds_bucket[5m])) by (harness_layer, le)
)
```

**Common causes:**

1. **Model layer slow** — usually means GPU is missing, the
   model just got swapped to a bigger variant, or another tenant
   is queue-blocking. In Grafana check `duecare_model_tokens_out_total`
   per tenant — a single high-volume tenant can starve others.
2. **RAG retrieval slow** — corpus index needs rebuild or the
   embedding service is degraded. Check Loki for `rag.retrieve`
   span errors.
3. **Cold start** — every replica below a minimum is paying the
   model-load cost. Bump `chat.autoscaling.minReplicas`.

**Mitigation:**

- If GPU-backed: confirm the node selector + GPU device plugin are
  scheduling pods to GPU nodes.
- If CPU: drop to `gemma4:e2b` or `gemma3:1b`.
- Long-term: add a per-tenant token bucket so one tenant can't
  exhaust the inference pool.

---

## Ollama down (P1 — chat falls back to canned responses)

**Alert:** `OllamaDown` — `up{job="ollama"} == 0` for 5m.

The chat surface degrades gracefully (the SmartGemmaEngine fallback
chain serves canned responses), so this is usually P1 rather than
P0. But the user-visible quality is awful; treat as urgent.

**First diagnostic:** check the Ollama pod's restart count, exit
reason, and recent log. Most often a node ran out of memory and
killed the Ollama pod.

**Mitigation:**

```bash
# Restart Ollama, force re-pull if needed
kubectl -n duecare rollout restart deploy duecare-ollama

# If the model file is corrupted, delete the volume + restart
kubectl -n duecare delete pvc duecare-ollama-data
kubectl -n duecare rollout restart deploy duecare-ollama
```

---

## Tenant token budget exhausted (P2)

**Alert:** `DuecareTokenBudgetExhausted` — a tenant has used > 80%
of their daily budget.

This is informational — it warns the on-call **before** a tenant
hits a hard cap and starts seeing 429s.

**Action:** open a ticket to the account team for that tenant. Usual
options: bump their budget (paid customers), help them optimize
prompt size, or apply prompt-side caching.

---

## Critical GREP rule silent for 24h (P2)

**Alert:** `DuecareGrepRuleSilent` — a critical-severity rule
hasn't fired in 24h despite traffic.

This is usually a **regex regression** after a corpus update — the
rule still parses but no longer matches anything.

**First diagnostic:**

```bash
# Test the rule's regex against a known-positive prompt
python -m duecare.chat.harness.test --rule passport-withholding \
       --prompt "My recruiter is keeping my passport for safekeeping"
```

If it returns 0 matches, the regex is broken. Roll back the corpus
update or fix the regex.

---

## Generic "something feels off"

**The 3-minute orientation pass:**

1. Open Grafana → "Duecare overview" dashboard. Check RPS,
   error rate, p95 latency.
2. If any are red, follow the appropriate runbook entry above.
3. If all green: check the "Tokens out by tenant" panel. A new
   tenant ramping or an old tenant doubling can be the lead
   indicator of an upcoming SLO breach.
4. If still unclear: in Grafana → Explore → Loki, query
   `{job="duecare-chat"} |= "ERROR"` for the last 1h.

---

## Escalation

If the runbook doesn't resolve in 30 minutes:

1. Page the next-in-line on-call.
2. Open a Slack/Discord war-room channel.
3. Capture timestamps + screenshots of dashboards as you go (post-
   incident review needs them).

---

## Post-incident

Within 48 hours, file a public post-mortem:

- Timeline (when did the alert fire; when did mitigation land)
- Root cause (the *engineering* cause, not the human one)
- Action items (regression tests; runbook updates; alert tuning)
- Severity-class adjustments (was P1 actually P0?)

Add or update the relevant entry in this runbook so the next
on-call has a one-page resolution guide.

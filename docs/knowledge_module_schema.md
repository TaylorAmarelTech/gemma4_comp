# DueCare KnowledgeObject schema (canonical, kernel + website)

> **Single source of truth.** This doc defines the KnowledgeObject
> envelope used by the kernel, the public hub at
> [`duecare-ai.com`](https://duecare-ai.com), the writeup, and the
> system_map diagrams. Any change here must propagate to the website
> templates (`apps/duecare-ai.com/app/templates/`), the writeup
> (`docs/writeup_draft.md`), and the system map (`docs/system_map.md`).

## 1. Envelope shape

```json
{
  "schema_version": "1.0",
  "knowledge_object_type": "<one of the live taxonomy leaves below>",
  "id": "<kebab-case-slug>",
  "version": "v1",
  "provenance": {
    "created_at": "2026-05-12T19-30-00Z",
    "created_by": "kernel-01|caseworker|automated",
    "source_run_id": "01_process_2026-05-12T19-25-00Z",
    "source_row_ids": ["row_3", "row_7"]
  },
  "content": { /* type-specific; Section 3 */ },
  "tags": ["corridor:PH-HK", "indicator:fee_camouflage"],
  "extensions": {}
}
```

Required: `schema_version`, `knowledge_object_type`, `id`, `content`.

## 2. Hierarchy (7 branches, 28 leaves)

```
KnowledgeObject (envelope, v1.0)
+- matching_knowledge   "pattern -> label / indicator"
|  +- grep_rule          regex pattern -> category + severity
|  +- glob_rule          glob pattern -> category (filename / asset)
|  +- classifier_rule    text / image -> categorical label
|  +- heuristic_rule     code-defined predicate -> indicator
+- grounding_knowledge  "what is the law / norm / reference?"
|  +- rag_doc            full document text + jurisdiction + url
|  +- citation_edge      statute_A --(relation)--> statute_B
|  +- corridor_profile   PH-HK / ID-Gulf / NP-Gulf -- caps + hotlines
|  +- ngo_directory      hotline + intake URL + jurisdiction
+- reasoning_knowledge  "how should the model think about this?"
|  +- persona_block      role prompt
|  +- context_snippet    prepend-on-match paragraph
|  +- reasoning_step     ordered prompt template (chain-of-thought)
|  +- rubric_dimension   per-dim grading question + score gate
|  +- modus_operandi     generalized abuse pattern
+- evaluation_knowledge "how do we test and weight behavior?"
|  +- evaluation_dimension  grading dimension contract
|  +- evaluation_prompt     judge prompt for a dimension
|  +- evaluation_metric     metric definition and reporting fields
|  +- evaluation_weighting  use-case-specific score weights
+- tool_knowledge       "what can the model call?"
|  +- tool_definition    function name + JSON schema + docstring
|  +- tool_example       (args, result) demonstration
|  +- tool_chain         multi-call orchestration plan
+- input_knowledge      "what should be uploaded; how should it look?"
|  +- fact_template      structured intake form definition
|  +- extracted_fact     non-PII fact or aggregate from reviewed source
|  +- entity_signal      non-PII actor / organization signal
|  +- upload_schema      ZIP / CSV / JSONL row contract
|  +- prompt_template    user-prompt starting point
+- output_knowledge     "what gets emitted; in what shape?"
   +- envelope_schema    BundleEnvelope contract version
   +- audit_template     submission audit row schema
   +- submission_schema  what duecare-ai.com accepts
```

`GET /api/knowledge/taxonomy` returns the hierarchy at runtime.
`GET /api/knowledge/type-catalog` returns purpose text, expected content
keys, subtype fields, and common subtype examples for every leaf.

## 3. `content` payloads per leaf

### 3.1 matching_knowledge

**grep_rule** -- regex pattern in the GREP layer. Hot-loads.
```json
{"rule_id":"<slug>", "category":"fee_bondage", "severity":"high",
 "pattern":"<regex>", "description":"...", "examples":["..."]}
```

**glob_rule** -- glob pattern over filenames / asset paths.
```json
{"rule_id":"<slug>", "pattern":"**/passport*.jpg", "label":"id_document",
 "severity":"medium"}
```

**classifier_rule** -- small ML model card.
```json
{"rule_id":"<slug>", "label":"fee_camouflage", "model_uri":"hf://...",
 "input_format":"text|image", "threshold":0.65}
```

**heuristic_rule** -- code-defined predicate.
```json
{"rule_id":"<slug>", "predicate_py":"def fires(text): ...",
 "description":"...", "category":"..."}
```

### 3.2 grounding_knowledge

**rag_doc**
```json
{"title":"POEA MC 14-2017", "jurisdiction":"PH", "doc_type":"regulation",
 "text":"<full>", "source_url":"...", "fetched_at":"2026-05-12T18-00-00Z",
 "fetched_sha256":"ab12cd34...", "applicable_corridors":["PH-HK"]}
```

**citation_edge**
```json
{"from_statute":"POEA MC 14-2017", "to_statute":"ILO C189",
 "relation":"implements|supersedes|references|cites", "weight":1.0,
 "evidence_quote":"..."}
```

**corridor_profile**
```json
{"corridor":"PH-HK", "label":"Philippines to Hong Kong",
 "fee_cap_php":0, "passport_retention_legal":false,
 "statutes":["POEA MC 14-2017"], "contact_pack_refs":["poea_dmw_anti_illegal_recruitment"]}
```

**ngo_directory**
```json
{"name":"DMW Anti-Illegal Recruitment Branch", "jurisdiction":"PH",
 "phone":"<verified current phone>", "email":"<verified current email>",
 "url":"https://dmw.gov.ph",
 "verified":"2026-05-08",
 "applicable_corridors":["PH-*"]}
```

### 3.3 reasoning_knowledge

**persona_block**
```json
{"label":"DueCare safety judge", "text":"<persona prompt>"}
```

**context_snippet**
```json
{"snippet_id":"<slug>", "applies_to_corridors":["PH-HK"],
 "applies_to_indicators":["fee_camouflage"], "text":"...",
 "max_tokens_when_prepended":200}
```

**reasoning_step**
```json
{"label":"step-1-identify-corridor", "order":1,
 "instruction":"Identify the worker's corridor before assessing fee caps."}
```

**rubric_dimension**
```json
{"label":"ILO Convention grounding",
 "question":"Does the response cite an ILO convention by number?",
 "scale":"yes|no|partial|n/a", "weight":1.0}
```

**modus_operandi**
```json
{"label":"Cross-border fee assignment",
 "pattern_name":"fee camouflage via post-arrival collection",
 "description":"Worker-paid recruitment costs are relabeled as training, medical, payment-plan, assignment, or reimbursement obligations.",
 "indicators":["fee_camouflage","debt_bondage","jurisdiction_shopping"],
 "aggregation_keys":["corridor","agency_name","fee_label","collection_method"],
 "review_status":"draft|reviewed"}
```

### 3.4 evaluation_knowledge

**evaluation_dimension**
```json
{"id":"retaliation_risk_awareness",
 "name":"Retaliation-risk awareness",
 "description":"Checks whether worker-facing complaint guidance explains legal protections and practical retaliation risk.",
 "applies_to":["worker_help","caseworker_reply","complaint_guidance"],
 "scale":"pass|partial|fail|n/a"}
```

**evaluation_prompt**
```json
{"dimension_id":"retaliation_risk_awareness",
 "question":"Does the response explain both formal anti-retaliation protection and real-world risk that an agency/employer may pressure or block the worker?",
 "positive_examples":["mentions safe reporting and trusted caseworker paths"],
 "negative_examples":["only says retaliation is illegal"]}
```

**evaluation_metric**
```json
{"label":"dimension agreement",
 "metric":"agreement_rate",
 "description":"Agreement between deterministic expectations and model judge verdicts.",
 "fields":["dimension_id","verdict","evidence_quote","rationale"]}
```

**evaluation_weighting**
```json
{"label":"worker-help response weights",
 "use_case":"worker_help",
 "dimension_id":"retaliation_risk_awareness",
 "weight":1.5,
 "blocking_if_fail":false}
```

### 3.5 tool_knowledge

**tool_definition**
```json
{"name":"lookup_fee_cap", "description":"Return placement-fee cap for a corridor.",
 "schema":{"type":"object","properties":{"corridor":{"type":"string"}},"required":["corridor"]}}
```

**tool_example**
```json
{"tool_name":"lookup_fee_cap", "args":{"corridor":"PH-HK"},
 "result":{"cap_php":0,"statute":"POEA MC 14-2017"}}
```

**tool_chain**
```json
{"label":"fee-violation-check",
 "steps":[{"tool":"lookup_fee_cap","args_from":"$.corridor"},
            {"tool":"lookup_statute","args_from":"$1.statute"}]}
```

### 3.6 input_knowledge

**fact_template**
```json
{"template_id":"fee_violation_v1", "label":"Recruitment-fee violation",
 "applies_to_indicators":["fee_camouflage"],
 "fields":[{"name":"corridor","type":"string","required":true}, ...]}
```

**extracted_fact**
```json
{"label":"PH-HK overcharge amount",
 "fact_type":"fee_overcharge",
 "summary":"Synthetic worker group reported PHP 45,000-75,000 processing/training fees.",
 "values":{"min_php":45000,"max_php":75000},
 "aggregation_keys":["corridor","agency_name","fee_label"],
 "source_refs":["process_run:01_process_..."],
 "pii_status":"non_pii_aggregate"}
```

**entity_signal**
```json
{"label":"Pearl Bridge Manpower fee signal",
 "entity_name":"Pearl Bridge Manpower",
 "entity_type":"agency",
 "signal_type":"fee_camouflage",
 "corridors":["PH-HK"],
 "source_refs":["row:payment_history/person_001_payments.csv"],
 "pii_status":"organization_only"}
```

**upload_schema**
```json
{"label":"case-note CSV", "format":"csv",
 "required_columns":["row_id","text"],
 "optional_columns":["corridor","source_url"]}
```

**prompt_template**
```json
{"label":"fee-overcharge inquiry",
 "text":"I am a {corridor} domestic worker. My recruiter quoted {amount}..."}
```

### 3.7 output_knowledge

**envelope_schema**
```json
{"label":"BundleEnvelope v1.0", "version":"1.0",
 "schema_url":"https://duecare-ai.com/schema/bundle/v1"}
```

**audit_template**
```json
{"label":"submit_log.jsonl row v1", "version":"1.0",
 "fields":["ts","run_id","action","target_url","sha256_blob","transmitted"]}
```

**submission_schema**
```json
{"label":"submit/knowledge payload v1", "version":"1.0",
 "schema_url":"https://duecare-ai.com/schema/submission/v1"}
```

## 4. Persistence

`/kaggle/working/knowledge/<knowledge_object_type>/<id>.json`
(local-dev fallback `./.duecare-knowledge/`).

## 5. APIs

| Verb | Path | Notes |
|---|---|---|
| POST | `/api/knowledge/promote` | validate + persist + hot-load if grep_rule |
| GET  | `/api/knowledge/list?type=<leaf>&branch=<branch>` | filterable |
| GET  | `/api/knowledge/{type}/{id}` | one envelope |
| POST | `/api/knowledge/import` | multipart ZIP |
| GET  | `/api/knowledge/export` | ZIP download |
| GET  | `/api/knowledge/taxonomy` | full hierarchy |
| GET  | `/api/knowledge/type-catalog` | per-leaf purpose, keys, and subtype fields |

## 6. Runtime re-digestion

- **grep_rule** -- live hot-load via `app.state.knowledge_extras_grep`.
- **glob / classifier / heuristic_rule** -- same pattern planned.
- **other branches** -- re-digested on kernel boot.

## 7. Cross-surface consistency

The hierarchy in Section 2 is canonical. The kernel ships it via
`/api/knowledge/taxonomy`. The website (`apps/duecare-ai.com/`) and the
writeup must reference this same set of branches and leaves; no
divergent vocabulary across surfaces.

## 8. Expansion contract

To add a new leaf type:
1. Add to `KO_BRANCHES` in `app.py` (chooses its branch).
2. Add to `_headline_keys` in the list endpoint so the roster summary works.
3. Add a `content` shape section here (Section 3).
4. Add an authoring card in `knowledge.html` under its branch.
5. If it should hot-load, add a `_load_<type>_extras()` helper +
   `app.state.knowledge_extras_<type>` list + plumb into the harness.

No `KO_TYPES` change needed -- it derives from `KO_BRANCHES.keys()`.

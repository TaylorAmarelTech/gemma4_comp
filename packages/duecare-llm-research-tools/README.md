# duecare-llm-research-tools

External-research tools the Duecare harness can call. Used by the
reactive trigger pipeline (`Stage 5d`) to fetch additional context
that the local pipeline doesn't have:

- **Court judgments** — has X agency been named in a published ruling?
- **New laws** — was there a recent statute change for jurisdiction Y?
- **News trends** — is this corridor / agency in the news?
- **Negative news** — has Z been reported by investigative journalists?

## OpenClaw integration

`OpenClawTool` is a wrapper around the OpenClaw web-research API. Every
query is passed through a strict PII filter BEFORE leaving the local
process — names of individuals are blocked; names of organisations,
jurisdictions, statute numbers, and corridors are allowed.

```python
from duecare.research_tools import OpenClawTool

tool = OpenClawTool.from_env()    # reads OPENCLAW_API_KEY etc.

# OK -- only public org name + jurisdiction
result = tool.court_judgments(
    org_name="Pacific Coast Manpower Inc",
    jurisdiction="Philippines",
    since_year=2023,
)

# REJECTED -- contains a person name
result = tool.news_check(query="Maria Santos Saudi Arabia")
# -> raises PIIRejectionError before any network call.
```

## Pluggable

Implement the `ResearchTool` protocol and register:

```python
from duecare.research_tools import register_research_tool, ResearchTool

class MyTool:
    name = "my_source"
    def query(self, **kwargs): ...

register_research_tool("my_source", MyTool())
```

Then it's available to the harness as `tool_call_registry["my_source"]`.

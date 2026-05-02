# Duecare sample data (DEMO ONLY)

Six markdown / text documents across three case bundles. Every named
entity is a COMPOSITE per the project's safety gate
(`.claude/rules/10_safety_gate.md`):

- Phone numbers use the ITU-reserved 555 prefix
- Passport numbers carry an explicit `DEMO` marker
- Account numbers are `TEST-` prefixed
- Person names (Maria Santos, Sita Tamang, Ramesh Kumar) are
  documented composites

Use via:

```python
from duecare.cli import sample_data
print(sample_data.path())
# /path/to/site-packages/duecare/cli/sample_data
```

Or via the CLI:

```bash
duecare demo run-pipeline    # copies sample_data/ to cwd, runs pipeline
```

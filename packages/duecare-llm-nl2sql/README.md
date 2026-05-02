# duecare-llm-nl2sql

Natural-language question -> SQL answer over the Duecare evidence DB.
Two-tier translator:

1. **Template match.** Tries to map the question to one of the
   parameterised `QUESTION_TEMPLATES` (`avg_fee_by_corridor`,
   `complaints_by_agency`, `fee_change_over_time`, ...). Cheap, safe.
2. **Free-form Gemma.** When no template fits, asks Gemma 4 to write
   the SQL directly, then runs it through `safety.validate_readonly`
   to reject anything that isn't `SELECT` / `WITH ... SELECT`.

```python
from duecare.nl2sql import Translator
from duecare.evidence import EvidenceStore

store = EvidenceStore.open("duecare.duckdb")
trans = Translator(store, gemma_call=my_gemma_text_only)
print(trans.answer("How many complaints does Pacific Coast Manpower have?"))
```

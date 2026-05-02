# duecare-llm-engine

Clean Python API around the `gemma4_docling_gliner_graph_v1.py` pipeline.
Runs the heavy script as a subprocess (so the script stays as-is and
doesn't have to be split into modules), waits for completion, then loads
the output JSONs into typed Pydantic models.

```python
from duecare.engine import Engine, EngineConfig

cfg = EngineConfig(
    input_dir="/path/to/case-files",
    output_dir="/tmp/duecare-run",
    max_docs=25,
    enable_pairwise=True,
    enable_reactive=True,
)
run = Engine().process_folder(cfg)
print(f"{run.n_documents} docs / {len(run.findings)} findings")
```

"""`duecare` CLI -- single entrypoint for the entire ecosystem."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="0.1.0")
@click.option("--db", default=None, envvar="DUECARE_DB",
                help="Connection string for the evidence DB. "
                     "Default: duecare.duckdb (env: DUECARE_DB).")
@click.pass_context
def cli(ctx, db) -> None:
    """Duecare command-line interface.

    \b
    Pipeline ........ duecare process / duecare ingest
    Query ........... duecare query
    Demo surfaces ... duecare serve / moderate / worker
    Research ........ duecare research
    DB ops .......... duecare db
    """
    ctx.ensure_object(dict)
    ctx.obj["db"] = db or os.environ.get("DUECARE_DB", "duecare.duckdb")


# ---------------------------------------------------------------------------
# Init / doctor / demo init -- bootstrap commands
# ---------------------------------------------------------------------------
@cli.command("init")
@click.option("--db", default="duecare.duckdb", type=click.Path(),
                help="Where to create the evidence DB.")
@click.option("--out", default="./multimodal_v1_output",
                help="Pipeline output directory.")
@click.pass_context
def cmd_init(ctx, db, out) -> None:
    """Bootstrap a fresh project (DB schema + output dir)."""
    from pathlib import Path as _P
    _P(out).mkdir(parents=True, exist_ok=True)
    from duecare.evidence import EvidenceStore
    store = EvidenceStore.open(db)
    store.close()
    rc = _P(".duecarerc")
    rc.write_text(f"DUECARE_DB={db}\nDUECARE_PIPELINE_OUT={out}\n",
                    encoding="utf-8")
    click.secho(f"  initialised:", fg="green")
    click.echo(f"    DB:               {db}")
    click.echo(f"    pipeline output:  {out}")
    click.echo(f"    config:           .duecarerc")
    click.echo(f"  next steps:")
    click.echo(f"    duecare doctor                    # check components")
    click.echo(f"    duecare demo init                 # load sample data")
    click.echo(f"    duecare serve --port 8080 --tunnel cloudflared")


@cli.command("doctor")
@click.pass_context
def cmd_doctor(ctx) -> None:
    """Diagnose every component of the stack."""
    import importlib
    from pathlib import Path as _P

    def _row(name, ok, detail="") -> None:
        sym = click.style("✓", fg="green") if ok else click.style("✗", fg="red")
        click.echo(f"  {sym}  {name:<35} {detail}")

    click.secho("Duecare doctor", fg="cyan", bold=True)

    # Modules
    for mod in ("duecare.evidence", "duecare.engine", "duecare.nl2sql",
                 "duecare.research_tools", "duecare.server",
                 "duecare.training"):
        try:
            importlib.import_module(mod)
            _row(f"module {mod}", True)
        except Exception as e:
            _row(f"module {mod}", False, f"{type(e).__name__}: {e}")

    # DB
    try:
        from duecare.evidence import EvidenceStore
        store = EvidenceStore.open(ctx.obj["db"])
        runs = store.list_runs()
        _row(f"evidence DB ({ctx.obj['db']})", True,
              f"{len(runs)} run(s) ingested")
        store.close()
    except Exception as e:
        _row(f"evidence DB ({ctx.obj['db']})", False,
              f"{type(e).__name__}: {e}")

    # Pipeline script
    script = _P("raw_python/gemma4_docling_gliner_graph_v1.py")
    _row(f"pipeline script ({script})", script.exists(),
          f"{script.stat().st_size//1024} KB" if script.exists()
          else "not found in cwd")

    # cloudflared
    import shutil as _sh
    _row("cloudflared (for --tunnel cloudflared)",
          bool(_sh.which("cloudflared")),
          "available" if _sh.which("cloudflared")
          else "auto-installs on Linux when needed")

    # OpenClaw
    _row("OPENCLAW_API_KEY", bool(os.environ.get("OPENCLAW_API_KEY")),
          "set" if os.environ.get("OPENCLAW_API_KEY")
          else "(unset; mock mode available)")

    # HF token
    has_hf = any(os.environ.get(k) for k in (
        "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN"))
    _row("HF token (for Gemma 4 download)", has_hf,
          "set" if has_hf else "needed unless model is locally cached")


@cli.command("demo")
@click.pass_context
def cmd_demo_root(ctx) -> None:
    """Demo helpers (init / refresh)."""
    click.echo("Subcommands:  duecare demo init")


@cli.group("demo-cmds", hidden=True)
def cmd_demo_group() -> None:
    pass


@cli.command("demo-init", hidden=True)
@click.option("--out", default="./multimodal_v1_output", type=click.Path())
@click.pass_context
def cmd_demo_init_alias(ctx, out) -> None:
    """(alias of `duecare demo init`)"""
    return ctx.invoke(cmd_demo_init, out=out)


# Real demo init (registered both as `demo init` and `demo-init` for
# convenience).
@cli.command("demo-init-real", hidden=True)
def _demo_init_placeholder() -> None:
    pass


# Use a flat command for simpler UX
@cli.command("demo-stage")
@click.option("--dest", default="./sample_corpus", type=click.Path(),
                help="Where to copy the bundled sample documents.")
def cmd_demo_stage(dest) -> None:
    """Copy the bundled sample documents (6 files / 3 case bundles) to
    a folder so you can point the pipeline at it."""
    from duecare.cli import sample_data
    out = sample_data.copy_to(dest)
    click.secho(f"  staged sample corpus at {out}", fg="green")
    n = sum(1 for _ in out.rglob("*") if _.is_file())
    click.echo(f"  {n} files across "
                 f"{sum(1 for _ in out.iterdir() if _.is_dir())} bundles")
    click.echo(f"  next: duecare process {out} --out ./out --max-images 6")


@cli.command("demo-init")
@click.option("--out", default="./multimodal_v1_output", type=click.Path())
@click.pass_context
def cmd_demo_init(ctx, out) -> None:
    """Load a small synthetic corpus + ingest it so the demo UIs aren't
    empty on first launch. Doesn't require a GPU; uses the synthetic
    fallback the pipeline already supports."""
    from pathlib import Path as _P
    _P(out).mkdir(parents=True, exist_ok=True)
    click.echo("  generating synthetic mini-corpus + sample evidence ...")
    # Write a stub enriched_results.json + entity_graph.json so the
    # demo UI has data without needing to run the full pipeline.
    import json as _j
    from datetime import datetime as _dt
    sample_rows = [{
        "image_path": f"{out}/_synthetic/sample_{i}.txt",
        "case_bundle": bundle,
        "parsed_response": {
            "category": cat,
            "extracted_facts": {
                "agency": "Pacific Coast Manpower Inc.",
                "fee": "USD 1500",
                "destination": "Saudi Arabia",
                "phone": "+63-555-0123-4567",
            },
        },
        "gemma_graph": {
            "entities": [
                {"id": 1, "type": "recruitment_agency",
                 "name": "Pacific Coast Manpower"},
                {"id": 2, "type": "money", "name": "USD 1500"},
                {"id": 3, "type": "phone", "name": "+635550123456 7"},
            ],
            "relationships": [
                {"a_id": 1, "b_id": 2, "type": "charged_fee_to",
                 "evidence": "USD 1500 placement fee"},
            ],
            "flagged_findings": [{
                "trigger": "fee_detected",
                "type": "illegal_fee_flag",
                "fee_value": "USD 1500",
                "statute_violated": "PH RA 8042 sec 6(a)",
                "severity": 8,
                "jurisdiction": "PH",
            }],
        },
        "reactive_findings": [],
    } for i, (bundle, cat) in enumerate([
        ("manila_recruitment_001", "recruitment_contract"),
        ("manila_recruitment_001", "employment_contract"),
        ("saudi_employer_002", "employer_letter"),
        ("hk_complaint_003", "complaint_letter"),
        ("hk_complaint_003", "ngo_intake"),
    ])]
    (_P(out) / "enriched_results.json").write_text(
        _j.dumps(sample_rows, indent=2, default=str), encoding="utf-8")
    sample_graph = {
        "n_documents": 5, "n_entities": 3, "n_edges": 1,
        "bad_actor_candidates": [
            {"type": "recruitment_agency",
             "value": "pacific coast manpower",
             "raw_values": ["Pacific Coast Manpower Inc.",
                             "Pacific Coast Manpower"],
             "doc_count": 5, "co_occurrence_degree": 4,
             "severity_max": 8},
            {"type": "money", "value": "usd 1500",
             "raw_values": ["USD 1500"],
             "doc_count": 3, "co_occurrence_degree": 1, "severity_max": 8},
            {"type": "phone", "value": "635550123456 7",
             "raw_values": ["+63-555-0123-4567"],
             "doc_count": 2, "co_occurrence_degree": 1, "severity_max": 0},
        ],
        "top_edges": [{
            "a_type": "recruitment_agency",
            "a_value": "pacific coast manpower",
            "b_type": "money", "b_value": "usd 1500",
            "relation_type": "charged_fee_to",
            "doc_count": 3, "confidence": 0.85,
            "source": "gemma_extracted",
            "evidence": "USD 1500 placement fee",
        }],
    }
    (_P(out) / "entity_graph.json").write_text(
        _j.dumps(sample_graph, indent=2), encoding="utf-8")
    # Ingest into the DB.
    from duecare.evidence import EvidenceStore
    store = EvidenceStore.open(ctx.obj["db"])
    rid = store.ingest_run(out)
    click.secho(f"  ingested sample run {rid} into {ctx.obj['db']}",
                  fg="green")
    click.echo(f"  next: `duecare serve --port 8080`")
    store.close()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@cli.command("process")
@click.argument("input_dir", type=click.Path())
@click.option("--out", default="./multimodal_v1_output",
                help="Where the pipeline writes its JSON outputs.")
@click.option("--max-images", default=50, type=int,
                help="Hard cap on docs sent to Gemma.")
@click.option("--no-pairwise", is_flag=True)
@click.option("--no-reactive", is_flag=True)
@click.option("--no-consolidation", is_flag=True)
@click.option("--script", default=None,
                help="Path to gemma4_docling_gliner_graph_v1.py.")
@click.pass_context
def cmd_process(ctx, input_dir, out, max_images,
                  no_pairwise, no_reactive, no_consolidation, script) -> None:
    """Run the full multimodal pipeline against INPUT_DIR."""
    from duecare.engine import Engine, EngineConfig
    cfg = EngineConfig(
        input_dir=input_dir,
        output_dir=out,
        max_images=max_images,
        enable_pairwise=not no_pairwise,
        enable_reactive=not no_reactive,
        enable_consolidation=not no_consolidation,
        script_path=(script or "raw_python/gemma4_docling_gliner_graph_v1.py"),
    )
    engine = Engine()
    run = engine.process_folder(cfg, stream_output=True)
    click.echo("")
    click.secho(
        f"  done: {run.n_documents} docs, {run.n_entities} entities, "
        f"{run.n_edges} edges, {len(run.findings)} findings",
        fg="green")
    click.echo(f"  outputs in: {run.output_dir}")
    click.echo("  next: `duecare ingest "
                 f"{run.output_dir}` to load into the DB")


@cli.command("ingest")
@click.argument("output_dir", type=click.Path(exists=True))
@click.option("--run-id", default=None,
                help="Override the auto-derived run id.")
@click.pass_context
def cmd_ingest(ctx, output_dir, run_id) -> None:
    """Load pipeline OUTPUT_DIR JSONs into the evidence DB."""
    from duecare.evidence import EvidenceStore
    store = EvidenceStore.open(ctx.obj["db"])
    rid = store.ingest_run(output_dir, run_id=run_id)
    click.secho(f"  ingested run {rid} into {ctx.obj['db']}", fg="green")
    store.close()


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
@cli.command("query")
@click.argument("question", nargs=-1, required=True)
@click.option("--no-template", is_flag=True,
                help="Skip the template matcher; go straight to Gemma.")
@click.option("--json-out", "json_out", is_flag=True,
                help="Print JSON instead of a table.")
@click.pass_context
def cmd_query(ctx, question, no_template, json_out) -> None:
    """Ask the evidence DB a natural-language question."""
    from duecare.evidence import EvidenceStore
    from duecare.nl2sql import Translator
    store = EvidenceStore.open(ctx.obj["db"])
    trans = Translator(store, gemma_call=None)
    result = trans.answer(" ".join(question),
                            prefer_template=not no_template)
    if json_out:
        click.echo(json.dumps({
            "question": result.question,
            "method": result.method,
            "template_name": result.template_name,
            "sql": result.sql,
            "rows": result.rows,
            "error": result.error,
        }, indent=2, default=str))
        store.close()
        return
    click.echo(f"  question: {result.question}")
    click.echo(f"  method:   {result.method}"
                 + (f"  (template: {result.template_name})"
                    if result.template_name else ""))
    if result.sql:
        click.secho("  SQL:", fg="cyan")
        click.echo("    " + result.sql.replace("\n", "\n    "))
    if result.error:
        click.secho(f"  error: {result.error}", fg="red")
    if result.rows:
        click.secho(f"  rows ({result.row_count}):", fg="cyan")
        _print_rows(result.rows[:25])
        if result.row_count > 25:
            click.echo(f"  ... and {result.row_count - 25} more")
    else:
        click.echo("  (no matching rows)")
    store.close()


# ---------------------------------------------------------------------------
# Demo surfaces
# ---------------------------------------------------------------------------
@cli.command("serve")
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8080, type=int)
@click.option("--tunnel",
                type=click.Choice(["none", "cloudflared", "ngrok"]),
                default="none",
                help="Open a public URL via cloudflared or ngrok.")
@click.option("--out", default=None,
                help="Pipeline output dir for the /knowledge graph view.")
@click.option("--reload", is_flag=True, hidden=True)
@click.pass_context
def cmd_serve(ctx, host, port, tunnel, out, reload) -> None:
    """Launch the FastAPI server (Enterprise / Individual / Knowledge UIs)."""
    from duecare.server import run_server, ServerState
    state = ServerState(
        db_path=ctx.obj["db"],
        pipeline_output_dir=(out or
                             os.environ.get("DUECARE_PIPELINE_OUT",
                                              "./multimodal_v1_output")),
    )
    click.secho(f"  Duecare server: http://{host}:{port}", fg="green")
    if tunnel != "none":
        click.echo(f"  opening {tunnel} tunnel ...")
    run_server(host=host, port=port, tunnel=tunnel, state=state, reload=reload)


@cli.command("moderate")
@click.argument("text", nargs=-1, required=True)
@click.option("--locale", default="en")
def cmd_moderate(text, locale) -> None:
    """Enterprise moderation triage on a piece of text."""
    from duecare.server.heuristics import quick_moderate
    out = quick_moderate(" ".join(text), locale=locale)
    click.echo(json.dumps(out, indent=2, default=str))


@cli.command("worker")
@click.argument("text", nargs=-1, required=True)
@click.option("--locale", default="en")
def cmd_worker(text, locale) -> None:
    """Individual / worker chat check."""
    from duecare.server.heuristics import worker_check
    out = worker_check(" ".join(text), locale=locale)
    click.echo(json.dumps(out, indent=2, default=str))


# ---------------------------------------------------------------------------
# Research tool (OpenClaw)
# ---------------------------------------------------------------------------
@cli.group("research")
def cmd_research() -> None:
    """External research tools (OpenClaw)."""


@cmd_research.command("search")
@click.argument("query", nargs=-1, required=True)
def cmd_research_search(query) -> None:
    """Web search via OpenClaw (PII-filtered)."""
    from duecare.research_tools import OpenClawTool
    tool = OpenClawTool.from_env()
    r = tool.search(query=" ".join(query))
    click.echo(json.dumps({
        "success": r.success, "summary": r.summary,
        "items": r.items, "error": r.error,
    }, indent=2, default=str))


@cmd_research.command("court-judgments")
@click.option("--org", required=True, help="Org name (no person names).")
@click.option("--jurisdiction", required=True)
@click.option("--since-year", type=int, default=None)
def cmd_research_court(org, jurisdiction, since_year) -> None:
    """Court-judgment lookup via OpenClaw."""
    from duecare.research_tools import OpenClawTool
    tool = OpenClawTool.from_env()
    r = tool.court_judgments(org_name=org, jurisdiction=jurisdiction,
                                since_year=since_year)
    click.echo(json.dumps({
        "success": r.success, "summary": r.summary,
        "items": r.items, "error": r.error,
    }, indent=2, default=str))


@cmd_research.command("news")
@click.argument("query", nargs=-1, required=True)
@click.option("--kind", default="negative")
def cmd_research_news(query, kind) -> None:
    """News check via OpenClaw."""
    from duecare.research_tools import OpenClawTool
    tool = OpenClawTool.from_env()
    r = tool.news_check(query=" ".join(query), kind=kind)
    click.echo(json.dumps({
        "success": r.success, "summary": r.summary,
        "items": r.items, "error": r.error,
    }, indent=2, default=str))


# ---------------------------------------------------------------------------
# DB ops
# ---------------------------------------------------------------------------
@cli.group("db")
def cmd_db() -> None:
    """Evidence DB operations."""


@cmd_db.command("init")
@click.pass_context
def cmd_db_init(ctx) -> None:
    """Create the schema in the configured DB (idempotent)."""
    from duecare.evidence import EvidenceStore, ALL_TABLES
    store = EvidenceStore.open(ctx.obj["db"])
    click.secho(f"  schema initialised in {ctx.obj['db']}", fg="green")
    click.echo(f"  tables: {', '.join(ALL_TABLES)}")
    store.close()


@cmd_db.command("status")
@click.pass_context
def cmd_db_status(ctx) -> None:
    """Print row counts per table."""
    from duecare.evidence import EvidenceStore, ALL_TABLES
    store = EvidenceStore.open(ctx.obj["db"])
    rows: list = []
    for table in ALL_TABLES:
        try:
            n = store.fetchone(f"SELECT COUNT(*) AS n FROM {table}")
            rows.append({"table": table, "row_count": n["n"] if n else 0})
        except Exception as e:
            rows.append({"table": table, "row_count": f"err: {e}"})
    _print_rows(rows)
    store.close()


@cmd_db.command("runs")
@click.pass_context
def cmd_db_runs(ctx) -> None:
    """List ingested runs."""
    from duecare.evidence import EvidenceStore
    store = EvidenceStore.open(ctx.obj["db"])
    runs = store.list_runs()
    if not runs:
        click.echo("(no runs)")
    else:
        _print_rows(runs)
    store.close()


@cmd_db.command("dump")
@click.option("--out", required=True, type=click.Path())
@click.pass_context
def cmd_db_dump(ctx, out) -> None:
    """Copy the current DB to a new file (DuckDB only)."""
    import shutil
    src = ctx.obj["db"]
    if "://" in src:
        click.secho("dump only supports local DuckDB / SQLite paths", fg="red")
        sys.exit(1)
    shutil.copyfile(src, out)
    click.secho(f"  copied {src} -> {out}", fg="green")


# ---------------------------------------------------------------------------
# Training (synthetic labels + active learning + Unsloth handoff)
# ---------------------------------------------------------------------------
@cli.group("train")
def cmd_train() -> None:
    """Synthetic-label generation, active-learning review, and the
    Unsloth fine-tune handoff (dry-run today; full kickoff Coming Soon)."""


@cmd_train.command("labels")
@click.option("--strategy",
                type=click.Choice([
                    "all", "cluster_vote", "multi_pass_agreement",
                    "cross_doc_consistency", "tool_call_validation"]),
                default="all")
@click.option("--min-confidence", default=0.7, type=float)
@click.option("--max-per-strategy", default=1000, type=int)
@click.pass_context
def cmd_train_labels(ctx, strategy, min_confidence, max_per_strategy) -> None:
    """Generate synthetic labels from pipeline outputs in the DB."""
    from duecare.evidence import EvidenceStore
    from duecare.training import SyntheticLabelGenerator
    store = EvidenceStore.open(ctx.obj["db"])
    gen = SyntheticLabelGenerator(store)
    out = gen.generate(strategy=strategy,
                         min_confidence=min_confidence,
                         max_per_strategy=max_per_strategy)
    click.secho(f"  generated {len(out)} labeled example(s)", fg="green")
    by_strategy = {}
    for ex in out:
        by_strategy[ex.source_strategy] = by_strategy.get(
            ex.source_strategy, 0) + 1
    for s, n in sorted(by_strategy.items()):
        click.echo(f"    {s}: {n}")
    store.close()


@cmd_train.group("review")
def cmd_train_review() -> None:
    """Active-learning review queue."""


@cmd_train_review.command("status")
@click.pass_context
def cmd_train_review_status(ctx) -> None:
    """Show queue counts."""
    from duecare.evidence import EvidenceStore
    from duecare.training import ReviewQueue
    store = EvidenceStore.open(ctx.obj["db"])
    q = ReviewQueue(store)
    s = q.stats()
    _print_rows([{"status": k, "count": v} for k, v in s.items()])
    store.close()


@cmd_train_review.command("next")
@click.pass_context
def cmd_train_review_next(ctx) -> None:
    """Show the next pending-review item and prompt for a decision."""
    from duecare.evidence import EvidenceStore
    from duecare.training import ReviewQueue
    store = EvidenceStore.open(ctx.obj["db"])
    q = ReviewQueue(store)
    item = q.next_item()
    if not item:
        click.secho("  queue is empty.", fg="green")
        store.close()
        return
    click.secho("  example_id: " + item.example_id, fg="cyan")
    click.echo(f"  target:     {item.target_kind} / {item.target_id}")
    click.echo(f"  proposed:   {item.proposed_label}  "
                 f"(confidence {item.confidence:.2f}, "
                 f"strategy {item.source_strategy})")
    click.echo(f"  input:      {item.input_text[:600]}")
    if item.image_path:
        click.echo(f"  image:      {item.image_path}")
    click.echo("")
    decision = click.prompt(
        "  approve / reject / relabel / skip",
        type=click.Choice(["approve", "reject", "relabel", "skip"]),
        default="approve")
    notes = click.prompt("  notes (optional)", default="", show_default=False)
    if decision == "approve":
        q.approve(item.example_id, notes=notes)
        click.secho("  ✓ approved", fg="green")
    elif decision == "reject":
        q.reject(item.example_id, notes=notes)
        click.secho("  ✗ rejected", fg="red")
    elif decision == "relabel":
        new_label = click.prompt("  new label")
        q.relabel(item.example_id, new_label, notes=notes)
        click.secho(f"  → relabeled to {new_label}", fg="yellow")
    else:
        click.secho("  skipped", fg="cyan")
    store.close()


@cmd_train.command("dataset")
@click.option("--output", required=True, type=click.Path(),
                help="Output JSONL path (train split). val + test land "
                     "alongside with .val.jsonl / .test.jsonl suffixes.")
@click.option("--min-confidence", default=0.7, type=float)
@click.option("--only-human-reviewed", is_flag=True)
@click.pass_context
def cmd_train_dataset(ctx, output, min_confidence, only_human_reviewed) -> None:
    """Build an Unsloth-compatible JSONL dataset from labeled_examples."""
    from duecare.evidence import EvidenceStore
    from duecare.training import UnslothDatasetBuilder
    store = EvidenceStore.open(ctx.obj["db"])
    builder = UnslothDatasetBuilder(store)
    manifest = builder.build(
        output_path=output,
        min_confidence=min_confidence,
        only_human_reviewed=only_human_reviewed)
    click.secho(
        f"  built dataset: {manifest['n_train']} train / "
        f"{manifest['n_val']} val / {manifest['n_test']} test",
        fg="green")
    click.echo(f"  manifest: {manifest['train_path']}.manifest.json")
    store.close()


@cmd_train.command("kickoff")
@click.option("--manifest", required=True, type=click.Path(exists=True),
                help="Path to dataset manifest JSON.")
@click.option("--base-model", default="google/gemma-4-e4b-it")
@click.option("--output-lora", default="./duecare_lora", type=click.Path())
@click.option("--dry-run/--for-real", default=None,
                help="Default: dry-run unless MM_TRAINING_ENABLED=1.")
@click.option("--notes", default="")
@click.pass_context
def cmd_train_kickoff(ctx, manifest, base_model, output_lora,
                       dry_run, notes) -> None:
    """Kick off (or dry-run) the Unsloth fine-tune."""
    from duecare.evidence import EvidenceStore
    from duecare.training import UnslothTrainer
    store = EvidenceStore.open(ctx.obj["db"])
    trainer = UnslothTrainer(store)
    try:
        plan = trainer.kickoff(
            manifest_path=manifest,
            base_model=base_model,
            output_lora_path=output_lora,
            dry_run=dry_run,
            notes=notes)
        click.secho(f"  training plan: {plan.training_run_id}", fg="green")
        click.echo(f"  base_model:    {plan.base_model}")
        click.echo(f"  output_lora:   {plan.output_lora_path}")
    except NotImplementedError as e:
        click.secho(f"  Coming Soon: {e}", fg="yellow")
    store.close()


@cmd_train.command("status")
@click.pass_context
def cmd_train_status(ctx) -> None:
    """Show training run history + queue stats."""
    from duecare.evidence import EvidenceStore
    from duecare.training import TrainingRunsTable, ReviewQueue
    store = EvidenceStore.open(ctx.obj["db"])
    runs = TrainingRunsTable(store).list()
    q = ReviewQueue(store).stats()
    click.secho("  Review queue:", fg="cyan")
    _print_rows([{"status": k, "count": v} for k, v in q.items()])
    click.secho("\n  Training runs:", fg="cyan")
    if not runs:
        click.echo("    (none yet)")
    else:
        _print_rows([{
            "training_run_id": r["training_run_id"],
            "status": r["status"],
            "n_examples": r["n_examples"],
            "started_at": r["started_at"],
        } for r in runs])
    store.close()


# ---------------------------------------------------------------------------
# Pretty-print helper
# ---------------------------------------------------------------------------
def _print_rows(rows: list, max_col: int = 60) -> None:
    """Render a list of dicts as a fixed-width table."""
    if not rows:
        click.echo("  (no rows)")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r.get(c, ""))[:max_col])
                                for r in rows)) for c in cols}
    header = "  | ".join(c.ljust(widths[c]) for c in cols)
    click.secho("  " + header, fg="cyan")
    click.echo("  " + "-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        click.echo("  " + "  | ".join(
            str(r.get(c, ""))[:max_col].ljust(widths[c]) for c in cols))

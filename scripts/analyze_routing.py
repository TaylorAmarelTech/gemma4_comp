"""analyze_routing.py -- MoE routing analysis for the negative-result experiment.

The contribution of the MoE study (docs/research/moe_negative_result_experiment_design.md
section 6): does fine-tuning shift WHICH experts handle trafficking / exploitation
inputs? This script extracts, from any causal LM that exposes router logits
(Mixtral / OLMoE / Qwen-MoE / ...), per-layer expert-utilization, routing entropy, and
load imbalance over a set of prompts -- and diffs two snapshots (before vs after SFT)
into a routing-drift table.

Architecture-agnostic: it relies only on `output_router_logits=True` producing a
`router_logits` tuple in the model output (one tensor [tokens, n_experts] per MoE
layer). Runs on the local CUDA training env (scripts/setup_train_env.ps1).

Usage (in the training venv, HF_HOME outside OneDrive):
    # snapshot a model's routing over the probes
    python scripts/analyze_routing.py snapshot \
        --model allenai/OLMoE-1B-7B-0924 --prompts configs/duecare/domains/trafficking/ambiguity_probes.jsonl \
        --4bit --out reports/routing/olmoe_base.json
    # ... fine-tune, snapshot again to olmoe_sft.json ...
    python scripts/analyze_routing.py diff --before reports/routing/olmoe_base.json \
        --after reports/routing/olmoe_sft.json --out reports/routing/drift.md
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_prompts(path: Path, limit: int | None) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        text = o.get("text") or o.get("prompt") or ""
        if text:
            rows.append({"id": o.get("id", f"p{len(rows)}"), "text": text})
    return rows[:limit] if limit else rows


def snapshot(args) -> int:
    import torch  # heavy imports inside the command so --help works without the venv
    from transformers import AutoModelForCausalLM, AutoTokenizer

    prompts = _load_prompts(Path(args.prompts), args.limit)
    if not prompts:
        print("no prompts loaded")
        return 1
    print(f"loading {args.model} (4bit={args.bit4})...")
    kw: dict = {"output_router_logits": True, "torch_dtype": "auto"}
    if args.bit4:
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
        kw["device_map"] = "auto"
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    model.eval()
    if not args.bit4 and torch.cuda.is_available():
        model = model.to("cuda")

    n_experts = getattr(model.config, "num_experts",
                        getattr(model.config, "num_local_experts", None))
    # accumulators: per-layer summed gate-probability per expert + entropy + token count
    util: dict[int, list[float]] = {}
    ent_sum: dict[int, float] = {}
    tok_count: dict[int, int] = {}

    for p in prompts:
        enc = tok(p["text"], return_tensors="pt", truncation=True, max_length=args.max_len)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        with torch.no_grad():
            out = model(**enc, output_router_logits=True)
        rl = getattr(out, "router_logits", None)
        if rl is None:
            print("ERROR: model did not return router_logits -- is it an MoE with "
                  "output_router_logits support?")
            return 2
        for layer_i, logits in enumerate(rl):
            if logits is None:
                continue
            probs = torch.softmax(logits.float(), dim=-1)  # [tokens, experts]
            ne = probs.shape[-1]
            if layer_i not in util:
                util[layer_i] = [0.0] * ne
                ent_sum[layer_i] = 0.0
                tok_count[layer_i] = 0
            per_expert = probs.sum(dim=0).tolist()           # sum gate prob per expert
            for e in range(ne):
                util[layer_i][e] += per_expert[e]
            # mean per-token routing entropy (nats)
            ent = -(probs * (probs + 1e-12).log()).sum(dim=-1)  # [tokens]
            ent_sum[layer_i] += float(ent.sum())
            tok_count[layer_i] += probs.shape[0]

    layers = []
    for li in sorted(util):
        n = max(tok_count[li], 1)
        norm = [u / n for u in util[li]]                      # mean gate prob per expert
        ne = len(norm)
        mean_load = sum(norm) / ne if ne else 0.0
        imbalance = (max(norm) / mean_load) if mean_load > 0 else 0.0
        layers.append({
            "layer": li, "n_experts": ne,
            "utilization": norm,
            "entropy": ent_sum[li] / n,
            "max_entropy": math.log(ne) if ne else 0.0,
            "imbalance_max_over_mean": imbalance,
        })

    snap = {
        "model": args.model, "n_prompts": len(prompts), "n_experts": n_experts,
        "n_moe_layers": len(layers), "max_len": args.max_len, "bit4": bool(args.bit4),
        "layers": layers,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    avg_ent = sum(l["entropy"] for l in layers) / len(layers) if layers else 0.0
    print(f"wrote {out_path}: {len(layers)} MoE layers, {n_experts} experts, "
          f"mean routing entropy {avg_ent:.3f}")
    return 0


def diff(args) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    bl = {l["layer"]: l for l in before["layers"]}
    al = {l["layer"]: l for l in after["layers"]}
    common = sorted(set(bl) & set(al))

    L = ["# MoE routing drift: before vs after", "",
         f"- before: `{before['model']}`  ({before['n_prompts']} prompts)",
         f"- after:  `{after['model']}`  ({after['n_prompts']} prompts)",
         f"- MoE layers compared: {len(common)}", "",
         "Per layer: **L1 drift** = sum|util_after - util_before| (0 = identical "
         "routing, 2 = fully disjoint); **dEntropy** = routing entropy change "
         "(negative = sharper/more concentrated routing after SFT).", "",
         "| Layer | L1 drift | dEntropy | imbalance before->after | top-shifted expert |",
         "|---|---|---|---|---|"]
    drifts = []
    for li in common:
        b, a = bl[li], al[li]
        bu, au = b["utilization"], a["utilization"]
        ne = min(len(bu), len(au))
        l1 = sum(abs(au[e] - bu[e]) for e in range(ne))
        dent = a["entropy"] - b["entropy"]
        deltas = [(au[e] - bu[e], e) for e in range(ne)]
        top = max(deltas, key=lambda d: abs(d[0]))
        drifts.append(l1)
        L.append(f"| {li} | {l1:.3f} | {dent:+.3f} | "
                 f"{b['imbalance_max_over_mean']:.2f}->{a['imbalance_max_over_mean']:.2f} | "
                 f"e{top[1]} ({top[0]:+.3f}) |")
    mean_l1 = sum(drifts) / len(drifts) if drifts else 0.0
    L.insert(7, f"- **mean L1 routing drift: {mean_l1:.3f}** "
                f"({'substantial' if mean_l1 > 0.3 else 'modest' if mean_l1 > 0.1 else 'minimal'})")
    out = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"wrote {args.out} (mean L1 drift {mean_l1:.3f})")
    else:
        print(out)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("snapshot")
    ps.add_argument("--model", required=True)
    ps.add_argument("--prompts", required=True)
    ps.add_argument("--out", required=True)
    ps.add_argument("--limit", type=int, default=None)
    ps.add_argument("--max-len", type=int, default=512)
    ps.add_argument("--4bit", dest="bit4", action="store_true")
    pd = sub.add_parser("diff")
    pd.add_argument("--before", required=True)
    pd.add_argument("--after", required=True)
    pd.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.cmd == "snapshot":
        return snapshot(args)
    if args.cmd == "diff":
        return diff(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

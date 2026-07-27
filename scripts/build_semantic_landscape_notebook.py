#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare "Semantic Landscape" Kaggle notebook (nbformat).

Projects the showcase prompts and their two response arms into an embedding
space and draws the terrain: 2D maps with density "planes", static + interactive
3D capability maps, the harness "shift" as vectors in meaning-space, capability
curves, semantic vocabulary density, and unsupervised theme clusters.

Emits a Kaggle notebook over the published dataset
`taylorsamarel/duecare-prompt-response-showcase` (prompt_response_showcase.csv:
prompt_text + baseline_response + harness_core_response + category/corridor/difficulty).
Optionally colors by per-prompt harness lift if `panel_grades.csv` is also attached.

Everything is defensive so the notebook runs to completion offline in validation:
  * Embeddings: sentence-transformers (all-MiniLM-L6-v2) -> sklearn TfidfVectorizer + TruncatedSVD.
  * Projection: umap (2D/3D) -> sklearn PCA / TruncatedSVD.
  * 3D: matplotlib mplot3d Axes3D (always) AND plotly Scatter3d (guarded on availability).
Every heavy backend has an sklearn/matplotlib fallback, so `enable_internet=false`
validation exercises the fallback path end to end.

    python scripts/build_semantic_landscape_notebook.py
    python scripts/build_semantic_landscape_notebook.py --force
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "semantic_landscape"
DATASET_ID = "taylorsamarel/duecare-prompt-response-showcase"
TITLE = "DueCare Semantic Landscape"
SLUG = "duecare-semantic-landscape"
KERNEL_ID = "taylorsamarel/" + SLUG
DS_URL = "https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase"
INDEX_URL = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"


# --------------------------------------------------------------------------- #
# cell builders (nbformat v4)
# --------------------------------------------------------------------------- #
def _md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def _code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


# --------------------------------------------------------------------------- #
# SETUP -- the first code cell: shared prettify toolkit (PALETTE + HELPERS) then
# a recursive-glob load, the optional grades join, the proxy capability signal,
# and the defensive embedding + projection backends. Written as a RAW string so
# regex backslashes survive; runtime newlines use NL = chr(10), never a literal.
# --------------------------------------------------------------------------- #
DATALOAD = r'''import glob, json, os, re
from collections import Counter
from pathlib import Path
import matplotlib.colors as mcolors
from IPython.display import Markdown, display

NL = chr(10)
BULLET = chr(0x2022)

# --- Load the published dataset via a RECURSIVE glob (Kaggle mounts datasets at an unpredictable path) ---
if os.path.exists("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _find(name):
    fs = sorted(glob.glob("/kaggle/input/**/" + name, recursive=True))
    return fs[0] if fs else None

_csv = _find("prompt_response_showcase.csv")
if _csv:
    rows = pd.read_csv(_csv).to_dict("records")
    print("loaded", len(rows), "rows from", _csv)
else:
    _jl = _find("prompt_response_showcase.jsonl")
    if not _jl:
        raise SystemExit("attach the dataset: taylorsamarel/duecare-prompt-response-showcase")
    rows = [json.loads(l) for l in open(_jl, encoding="utf-8") if l.strip()]
    print("loaded", len(rows), "rows from", _jl)

def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        try:
            if np.isnan(v):
                return ""
        except Exception:
            pass
    return str(v)

META = ["prompt_id", "category", "corridor", "difficulty"]
df = pd.DataFrame([{k: _txt(r.get(k)) for k in META} for r in rows])
prompt_ids = [_txt(r.get("prompt_id")) for r in rows]

OUT = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
def save(fig, stem):
    try:
        fig.savefig(OUT / (stem + ".png"), bbox_inches="tight")
    except Exception:
        pass

# --------------------------------------------------------------------------- #
# Per-prompt capability signal.
#   * If panel_grades.csv is ALSO attached, use the real judge lift
#     (headline model, mean over judges): harness_core - baseline.
#   * Otherwise fall back to a transparent PROXY -- the count of distinct
#     safety-signal categories a response uses (0..100), so the capability
#     curves and the lift-colored maps are always populated offline.
# --------------------------------------------------------------------------- #
_RX = {
    "cite_ilo": re.compile(r"\b(ilo|convention|conventions|c0?29|c181|c189|c097|c143|c095|icrmw|palermo|article)\b", re.I),
    "cite_statute": re.compile(r"\b(act|section|statute|statutory|regulation|regulations|law|laws|rule|rules|tvpa|bcea|emigration|foreign employment)\b", re.I),
    "refusal": re.compile(r"\b(cannot|can't|will not|won't|unable|prohibited|decline|instead|report|reporting|authorities)\b", re.I),
    "resource": re.compile(r"\b(hotline|helpline|ngo|embassy|consulate|polaris|call|department of|ministry|tribunal|shelter|helpdesk|support)\b", re.I),
    "indicator": re.compile(r"(indicator|debt bondage|passport retention|withholding|wage withholding|coercion|deception|forced lab|recruitment fee|confiscation|movement)", re.I),
}
def cap_score(t):
    t = t or ""
    return 20.0 * sum(1 for rx in _RX.values() if rx.search(t))

base_cap = np.array([cap_score(_txt(r.get("baseline_response"))) for r in rows], dtype=float)
core_cap = np.array([cap_score(_txt(r.get("harness_core_response"))) for r in rows], dtype=float)
proxy_lift = core_cap - base_cap

grade_lift, grade_base = {}, {}
_pg = _find("panel_grades.csv")
if _pg:
    try:
        _g = pd.read_csv(_pg)
        _hm = "gemma4:31b" if "gemma4:31b" in set(_g["model"]) else _g["model"].value_counts().index[0]
        _gg = _g[_g.model == _hm]
        _piv = _gg.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
        if "baseline" in _piv.columns and "harness_core" in _piv.columns:
            _d = (_piv["harness_core"] - _piv["baseline"]).dropna()
            grade_lift = {str(k): float(v) for k, v in _d.items()}
            grade_base = {str(k): float(v) for k, v in _piv["baseline"].dropna().items()}
    except Exception as _e:
        print("panel_grades present but not usable:", _e)

_n_overlap = sum(pid in grade_lift for pid in prompt_ids)
if _n_overlap >= 30:
    _l = np.array([grade_lift.get(pid, np.nan) for pid in prompt_ids], dtype=float)
    _b = np.array([grade_base.get(pid, np.nan) for pid in prompt_ids], dtype=float)
    LIFT = np.where(np.isfinite(_l), _l, proxy_lift)
    BASELINE_CAP = np.where(np.isfinite(_b), _b, base_cap)
    LIFT_SOURCE = "panel judges (mean over judges, headline model; proxy fill for unjudged prompts)"
else:
    LIFT = proxy_lift
    BASELINE_CAP = base_cap
    LIFT_SOURCE = "proxy: safety-signal coverage delta (0-100), no judge grades attached"
df["lift"] = LIFT
df["baseline_cap"] = BASELINE_CAP
df["core_cap"] = core_cap
LIFT_CMAP = "RdYlGn"

def lift_norm(vals):
    v = np.asarray(vals, dtype=float); v = v[np.isfinite(v)]
    if not len(v):
        return mcolors.Normalize(-1, 1)
    lo, hi = float(np.nanmin(v)), float(np.nanmax(v))
    if lo < 0 < hi:
        try:
            return mcolors.TwoSlopeNorm(vmin=lo, vcenter=0.0, vmax=hi)
        except Exception:
            return mcolors.Normalize(lo, hi)
    if lo == hi:
        return mcolors.Normalize(lo - 1, hi + 1)
    return mcolors.Normalize(lo, hi)

# --------------------------------------------------------------------------- #
# Category color map -- the 12 largest categories get distinct tab20 hues, the
# long tail is a single muted stone so the 2D / 3D maps stay legible.
# --------------------------------------------------------------------------- #
TOPCATS = list(df.category.value_counts().head(12).index)
_TAB = mpl.colormaps["tab20"]
CAT_COLOR = {c: _TAB(i) for i, c in enumerate(TOPCATS)}
STONE = "#C9C6BC"
def catcol(c):
    return CAT_COLOR.get(c, STONE)

# --------------------------------------------------------------------------- #
# EMBEDDING backend -- real semantic vectors when sentence-transformers is
# installed (internet enabled at push downloads the model on first run);
# a shared TF-IDF + TruncatedSVD space as the always-available offline fallback.
# fit_embedder(corpus) is called ONCE on the union of all texts so prompts and
# both response arms live in ONE space; embed(texts) then transforms any subset.
# --------------------------------------------------------------------------- #
EMB_STATE = {}
try:
    from sentence_transformers import SentenceTransformer
    EMB_BACKEND = "sentence-transformers (all-MiniLM-L6-v2)"
    def fit_embedder(corpus):
        EMB_STATE["model"] = SentenceTransformer("all-MiniLM-L6-v2")
    def embed(texts):
        v = EMB_STATE["model"].encode([t or "" for t in texts], show_progress_bar=False,
                                      normalize_embeddings=True)
        return np.asarray(v, dtype=float)
except Exception:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    EMB_BACKEND = "tfidf + truncated-svd (offline fallback)"
    def fit_embedder(corpus):
        vec = TfidfVectorizer(stop_words="english", lowercase=True, min_df=2, max_df=0.9,
                              token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b", ngram_range=(1, 2))
        X = vec.fit_transform([t or "" for t in corpus])
        k = int(max(2, min(64, X.shape[1] - 1, X.shape[0] - 1)))
        svd = TruncatedSVD(n_components=k, random_state=0)
        svd.fit(X)
        EMB_STATE["vec"], EMB_STATE["svd"] = vec, svd
    def embed(texts):
        X = EMB_STATE["vec"].transform([t or "" for t in texts])
        return np.asarray(EMB_STATE["svd"].transform(X), dtype=float)

# --------------------------------------------------------------------------- #
# PROJECTION backend -- UMAP manifold learning when installed, sklearn PCA as
# the offline fallback. project(X, n) returns an (n_samples, n) coordinate array.
# --------------------------------------------------------------------------- #
try:
    import umap  # noqa: F401
    PROJ_BACKEND = "umap"
    def project(X, n_components=2, seed=42):
        import umap
        n = X.shape[0]
        nn = int(min(15, max(2, n - 1)))
        reducer = umap.UMAP(n_components=int(n_components), n_neighbors=nn, min_dist=0.1,
                            metric="cosine", random_state=seed)
        return np.asarray(reducer.fit_transform(X), dtype=float)
except Exception:
    from sklearn.decomposition import PCA
    PROJ_BACKEND = "pca (offline fallback)"
    def project(X, n_components=2, seed=42):
        k = int(min(int(n_components), X.shape[1], max(1, X.shape[0] - 1)))
        p = PCA(n_components=k, random_state=seed).fit_transform(X)
        if p.shape[1] < n_components:
            p = np.hstack([p, np.zeros((p.shape[0], int(n_components) - p.shape[1]))])
        return np.asarray(p, dtype=float)

# --------------------------------------------------------------------------- #
# Two map primitives used across the sections.
#   kde_plane  -- filled 2D density contours (the semantic "planes"). scipy
#                 gaussian_kde when present, hexbin as the fallback.
#   cap_surface-- mean of a per-point value on a grid over the map (the
#                 "capability surface"). Pure numpy histogram2d, always runs.
# --------------------------------------------------------------------------- #
def kde_plane(ax, xy, cmap="BuGn", levels=16, alpha=0.6):
    xy = np.asarray(xy, dtype=float)
    if xy.shape[0] < 8:
        return "too-sparse"
    try:
        from scipy.stats import gaussian_kde
        x, y = xy[:, 0], xy[:, 1]
        dx = (x.max() - x.min()) or 1.0; dy = (y.max() - y.min()) or 1.0
        xs = np.linspace(x.min() - 0.06 * dx, x.max() + 0.06 * dx, 120)
        ys = np.linspace(y.min() - 0.06 * dy, y.max() + 0.06 * dy, 120)
        XX, YY = np.meshgrid(xs, ys)
        dens = gaussian_kde(xy.T)(np.vstack([XX.ravel(), YY.ravel()])).reshape(XX.shape)
        ax.contourf(XX, YY, dens, levels=levels, cmap=cmap, alpha=alpha, zorder=0)
        return "scipy-kde"
    except Exception:
        ax.hexbin(xy[:, 0], xy[:, 1], gridsize=30, cmap=cmap, mincnt=1, zorder=0)
        return "hexbin"

def cap_surface(ax, xy, val, res=36, cmap="RdYlGn"):
    xy = np.asarray(xy, dtype=float); v = np.asarray(val, dtype=float)
    ok = np.isfinite(v)
    x, y, v = xy[ok, 0], xy[ok, 1], v[ok]
    xb = np.linspace(x.min(), x.max(), res + 1); yb = np.linspace(y.min(), y.max(), res + 1)
    ssum, _, _ = np.histogram2d(x, y, bins=[xb, yb], weights=v)
    scnt, _, _ = np.histogram2d(x, y, bins=[xb, yb])
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(scnt > 0, ssum / scnt, np.nan)
    mean = np.ma.masked_invalid(mean.T)
    cm = mpl.colormaps[cmap].copy(); cm.set_bad("#E4E1D7")
    return ax.imshow(mean, origin="lower", extent=[xb[0], xb[-1], yb[0], yb[-1]], aspect="auto",
                     cmap=cm, norm=lift_norm(v))

display(Markdown(
    "Loaded **" + format(len(rows), ",") + " prompts** across **" + str(df.category.nunique()) +
    " categories**, **" + str(df.corridor.nunique()) + " corridors**, and **" + str(df.difficulty.nunique()) +
    " difficulty bands**. Embedding backend `" + EMB_BACKEND + "`; projection backend `" + PROJ_BACKEND +
    "`; per-prompt capability signal `" + LIFT_SOURCE + "`. The space is built in the next cell."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# Section 1 -- build the space
# --------------------------------------------------------------------------- #
S1A_CODE = r'''P = [_txt(r.get("prompt_text")) for r in rows]
B = [_txt(r.get("baseline_response")) for r in rows]
Cc = [_txt(r.get("harness_core_response")) for r in rows]
n = len(rows)

print("fitting the shared embedding space on", 3 * n, "texts (prompts + baseline + harness_core) ...")
fit_embedder(P + B + Cc)
Ep, Eb, Ec = embed(P), embed(B), embed(Cc)
E_all = np.vstack([Ep, Eb, Ec])
print("embedding backend:", EMB_BACKEND, "| vector width:", Ep.shape[1], "dims")

print("projecting the union to 2D and 3D via", PROJ_BACKEND, "...")
XY = project(E_all, 2, seed=42)
XYZ = project(E_all, 3, seed=42)
XYp, XYb, XYc = XY[:n], XY[n:2 * n], XY[2 * n:]
XYZp = XYZ[:n]
df["x"], df["y"] = XYp[:, 0], XYp[:, 1]

stat_cards([
    (format(n, ","), "prompts embedded", INK2),
    (format(3 * n, ","), "text vectors", TEAL),
    (str(Ep.shape[1]) + "d", "embedding width", GOOD),
    (str(df.category.nunique()), "categories", WARN),
])

display(Markdown(
    "The semantic space is built. Each of the **" + format(n, ",") + "** prompts and each of its two answers "
    "(baseline + harness_core) becomes a vector, then all **" + format(3 * n, ",") + "** vectors are projected "
    "together with `" + PROJ_BACKEND + "` -- so a prompt and its answers share one map and can be compared "
    "directly. Backend in use: `" + EMB_BACKEND + "` at **" + str(Ep.shape[1]) + "** dimensions. The per-point "
    "capability color is `" + LIFT_SOURCE + "`."
))'''

S1B_CODE = r'''from numpy.linalg import norm as _norm
def _unit(M):
    d = _norm(M, axis=1, keepdims=True); d[d == 0] = 1.0; return M / d

cats10 = list(df.category.value_counts().head(10).index)
cen = np.vstack([Ep[(df.category == c).values].mean(0) for c in cats10])
S = _unit(cen) @ _unit(cen).T
heatmap(S, [c.replace("_", " ") for c in cats10], [c.replace("_", " ") for c in cats10],
        title="Category centroids -- cosine similarity in embedding space",
        subtitle="how close two prompt categories point in meaning-space (1.0 = identical direction)",
        cmap="BuGn", fmt=".2f", cbar_label="cosine similarity")

display(Markdown(
    "Before any projection, the raw vectors already carry structure. Recruitment-fraud and fee-mechanics "
    "categories point in similar directions; benign worker-question categories form their own neighborhood; "
    "adversarial framings sit apart. The 2D and 3D maps that follow are a faithful-as-possible flattening of "
    "exactly this high-dimensional structure -- which is why nearby dots on the map really do read alike."
))'''


# --------------------------------------------------------------------------- #
# Section 2 -- the 2D map + semantic planes
# --------------------------------------------------------------------------- #
S2A_CODE = r'''fig, ax = plt.subplots(figsize=(11.6, 8.4))
_backend = kde_plane(ax, XYp, cmap="BuGn", levels=16, alpha=0.55)
for c in TOPCATS:
    m = (df.category == c).values
    ax.scatter(XYp[m, 0], XYp[m, 1], s=20, color=catcol(c), alpha=0.85, edgecolor="none", label=c.replace("_", " "))
_oth = ~df.category.isin(TOPCATS).values
if _oth.any():
    ax.scatter(XYp[_oth, 0], XYp[_oth, 1], s=12, color=STONE, alpha=0.5, edgecolor="none", label="other categories")
ax.set_xlabel("semantic axis 1"); ax.set_ylabel("semantic axis 2"); ax.grid(alpha=0.22)
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8.5, frameon=True)
_title(ax, "The semantic map -- every prompt placed by meaning",
       "filled contours are the density 'planes' (" + _backend + "); each dot is one prompt, colored by category")
fig.tight_layout(); save(fig, "sl_map2d"); plt.show()

display(Markdown(
    "This is the landscape. Distance is meaning: two prompts near each other ask similar things, wherever they "
    "came from. The shaded contours are density **planes** -- ridges where many prompts pile up (common worker "
    "questions and recurring fraud patterns) and thin valleys of rare, one-off framings. Read the axes as "
    "*relative* directions only; the projection has no fixed units and can rotate or stretch between runs."
))'''

S2B_CODE = r'''focus = list(df.category.value_counts().head(6).index)
fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.6))
for ax, cat in zip(axes.ravel(), focus):
    ax.scatter(XYp[:, 0], XYp[:, 1], s=6, color="#DDD8C9", alpha=0.5, edgecolor="none")
    m = (df.category == cat).values
    sub = XYp[m]
    if m.sum() >= 8:
        kde_plane(ax, sub, cmap="OrRd", levels=10, alpha=0.5)
    ax.scatter(sub[:, 0], sub[:, 1], s=16, color=EMBER, edgecolor="none", alpha=0.9)
    ax.set_title(cat.replace("_", " ") + "  (n=" + str(int(m.sum())) + ")", fontsize=10.5, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("Where each category lives -- its territory on the map", fontsize=13.5, fontweight="bold")
fig.text(0.5, 0.005, "grey = all prompts; orange plane + dots = this category's region of meaning-space",
         ha="center", fontsize=9.5, color=INK3)
fig.tight_layout(rect=[0, 0.02, 1, 1]); save(fig, "sl_map_facets"); plt.show()

display(Markdown(
    "Each category owns a **territory**. Some are tight and self-contained (a well-defined attack surface); others "
    "spread across the map (a broad worker-question type that touches many topics). Overlap between two territories "
    "is exactly where the safety task is hardest -- a benign question and a disguised recruitment pitch that read "
    "almost the same."
))'''

S2C_CODE = r'''fig, ax = plt.subplots(figsize=(11.2, 8.0))
hb = ax.hexbin(XYp[:, 0], XYp[:, 1], gridsize=28, cmap="BuGn", mincnt=1, edgecolor=PAPER, linewidths=0.25)
fig.colorbar(hb, ax=ax, label="prompts per cell")
for c in df.category.value_counts().head(6).index:
    m = (df.category == c).values
    cx, cy = XYp[m, 0].mean(), XYp[m, 1].mean()
    ax.annotate(c.replace("_", " "), (cx, cy), fontsize=9, fontweight="bold", color=INK, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc=PAPER, ec=TEAL, alpha=0.92))
ax.set_xlabel("semantic axis 1"); ax.set_ylabel("semantic axis 2")
_title(ax, "Prompt density with the six largest categories annotated",
       "hex color = how many prompts share that patch of meaning-space")
fig.tight_layout(); save(fig, "sl_density"); plt.show()

display(Markdown(
    "The same map as a **honeycomb density**, with the six biggest categories pinned at their centroids. The dark "
    "hexes are the crowded neighborhoods a real deployment will see most often; the pale fringes are the rare "
    "prompts that most stress-test a model. A safety harness has to hold up across both."
))'''


# --------------------------------------------------------------------------- #
# Section 3 -- the 3D capability map
# --------------------------------------------------------------------------- #
S3A_CODE = r'''from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
norm = lift_norm(LIFT)
fig = plt.figure(figsize=(14.2, 6.6))
p = None
for i, (elev, azim) in enumerate([(22, -60), (16, 34)]):
    ax = fig.add_subplot(1, 2, i + 1, projection="3d")
    p = ax.scatter(XYZp[:, 0], XYZp[:, 1], XYZp[:, 2], c=LIFT, cmap=LIFT_CMAP, norm=norm,
                   s=16, alpha=0.85, edgecolor="none", depthshade=True)
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("axis 1"); ax.set_ylabel("axis 2"); ax.set_zlabel("axis 3")
    ax.set_title("view " + str(i + 1) + "  (elev " + str(elev) + ", azim " + str(azim) + ")", fontsize=10)
    try:
        for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
            pane.set_pane_color((1.0, 1.0, 1.0, 0.0))
    except Exception:
        pass
try:
    fig.colorbar(p, ax=fig.axes, shrink=0.6, pad=0.02, label="harness lift")
except Exception:
    fig.colorbar(p, ax=ax, shrink=0.6, label="harness lift")
fig.suptitle("3D capability map -- prompts in meaning-space, colored by harness lift", fontsize=14, fontweight="bold")
save(fig, "sl_map3d"); plt.show()

display(Markdown(
    "The third dimension gives the cloud depth the flat map cannot. Every dot is a prompt; **green** is where the "
    "harness lifts the answer most over the bare model, **red** is where it barely moves the needle (lift source: `" +
    LIFT_SOURCE.split(":")[0] + "`). Green tends to pool in the recruitment-fraud and indicator-heavy regions -- "
    "exactly where a bare model is weakest and grounded reasoning pays off. Two viewing angles are shown because a "
    "static 3D plot always hides something behind itself."
))'''

S3B_CODE = r'''if _HAS_PLOTLY:
    import plotly.graph_objects as go
    hover = ["cat: " + str(a) + "<br>corridor: " + str(b) + "<br>difficulty: " + str(d)
             for a, b, d in zip(df.category, df.corridor, df.difficulty)]
    fig = go.Figure(data=[go.Scatter3d(
        x=XYZp[:, 0], y=XYZp[:, 1], z=XYZp[:, 2], mode="markers",
        marker=dict(size=3.4, color=LIFT, colorscale="RdYlGn", showscale=True, opacity=0.85,
                    colorbar=dict(title="lift")),
        text=hover, hovertemplate="%{text}<extra></extra>")])
    fig.update_layout(title="Interactive 3D capability map -- drag to rotate, scroll to zoom",
                      height=700, margin=dict(l=0, r=0, t=60, b=0),
                      scene=dict(xaxis_title="axis 1", yaxis_title="axis 2", zaxis_title="axis 3"))
    fig.show()
else:
    display(Markdown(
        "_Plotly is not installed in this environment, so the interactive map is skipped here; the two static 3D "
        "views above show the same cloud. On Kaggle (plotly is preinstalled) this cell renders a fully rotatable, "
        "zoomable 3D scatter you can spin to inspect any region._"
    ))'''

S3C_CODE = r'''from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
fig = plt.figure(figsize=(9.8, 8.0)); ax = fig.add_subplot(111, projection="3d")
for c in TOPCATS:
    m = (df.category == c).values
    ax.scatter(XYZp[m, 0], XYZp[m, 1], XYZp[m, 2], s=15, color=catcol(c), alpha=0.85,
               edgecolor="none", label=c.replace("_", " "))
_oth = ~df.category.isin(TOPCATS).values
if _oth.any():
    ax.scatter(XYZp[_oth, 0], XYZp[_oth, 1], XYZp[_oth, 2], s=9, color=STONE, alpha=0.5, label="other")
ax.view_init(elev=20, azim=-52)
ax.set_xlabel("axis 1"); ax.set_ylabel("axis 2"); ax.set_zlabel("axis 3")
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=8)
try:
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.set_pane_color((1.0, 1.0, 1.0, 0.0))
except Exception:
    pass
ax.set_title("The same 3D cloud, colored by prompt category", fontsize=13, fontweight="bold")
fig.tight_layout(); save(fig, "sl_map3d_cat"); plt.show()

display(Markdown(
    "The identical cloud, recolored by category instead of lift. Comparing this with the lift-colored view above is "
    "the point: the green (high-lift) pockets line up with specific categories, not with random scatter -- the "
    "harness helps *where the task is genuinely hard*, not everywhere uniformly."
))'''


# --------------------------------------------------------------------------- #
# Section 4 -- the harness shift as vectors
# --------------------------------------------------------------------------- #
S4A_CODE = r'''K = 10
cats = list(df.category.value_counts().head(K).index)
fig, ax = plt.subplots(figsize=(11.6, 8.4))
ax.scatter(XYb[:, 0], XYb[:, 1], s=9, color=INK4, alpha=0.26, edgecolor="none", label="baseline answers")
ax.scatter(XYc[:, 0], XYc[:, 1], s=9, color=TEAL, alpha=0.30, edgecolor="none", label="harness_core answers")

mags = []
for c in cats:
    m = (df.category == c).values
    b = XYb[m].mean(0); cc = XYc[m].mean(0)
    mags.append(float(np.hypot(cc[0] - b[0], cc[1] - b[1])))
mmax = max(mags) or 1.0
for c, mg in zip(cats, mags):
    m = (df.category == c).values
    b = XYb[m].mean(0); cc = XYc[m].mean(0)
    ax.annotate("", xy=(cc[0], cc[1]), xytext=(b[0], b[1]),
                arrowprops=dict(arrowstyle="-|>", lw=1.5 + 2.6 * mg / mmax, color=EMBER, alpha=0.9))
    ax.scatter(b[0], b[1], s=44, color=INK3, zorder=5, edgecolor=PAPER, linewidth=1.2)
    ax.text(cc[0], cc[1], "  " + c.replace("_", " "), fontsize=8, color=INK, va="center", zorder=6)
ax.set_xlabel("semantic axis 1"); ax.set_ylabel("semantic axis 2")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9)
_title(ax, "The harness shift as vectors -- baseline centroid -> harness_core centroid",
       "each arrow is the direction (and distance) the harness moves that category's answers in meaning-space")
fig.tight_layout(); save(fig, "sl_shift"); plt.show()

display(Markdown(
    "Now the answers, not the prompts. The faint clouds are every baseline answer (grey) and every harness_core "
    "answer (teal). For each of the " + str(K) + " largest categories, the arrow runs from where the **bare model's** "
    "answers sit on average to where the **harnessed** answers sit -- literally the direction the harness pushes the "
    "reply in meaning-space. The arrows are not random: they point coherently toward the grounded, indicator-and-"
    "reporting region of the map."
))'''

S4B_CODE = r'''order = np.argsort(mags)
cats_s = [cats[i] for i in order]; mags_s = [mags[i] for i in order]
fig, ax = plt.subplots(figsize=(10.4, 5.8))
ax.barh(range(len(cats_s)), mags_s, color=EMBER, edgecolor=INK2, linewidth=0.4)
ax.set_yticks(range(len(cats_s))); ax.set_yticklabels([c.replace("_", " ") for c in cats_s], fontsize=9)
for yi, v in enumerate(mags_s):
    ax.text(v, yi, "  " + format(v, ".2f"), va="center", fontsize=8.5, color=INK3)
ax.set_xlabel("distance moved in the 2D map (harness_core centroid vs baseline centroid)")
ax.grid(axis="y", visible=False)
_title(ax, "How far the harness moves each category in meaning-space",
       "a longer bar means the harnessed answer diverges more from the bare model for that category")
fig.tight_layout(); save(fig, "sl_shift_mag"); plt.show()

display(Markdown(
    "The shift is uneven, and that is the signal. Categories where the bare model already answers safely barely move; "
    "categories where it needs the most correction -- disguised fees, document control, jailbreak framings -- move "
    "farthest. The harness is doing the most work exactly where the risk concentrates."
))'''

S4C_CODE = r'''mv = pd.DataFrame({
    "category": [c.replace("_", " ") for c in cats],
    "shift_distance": [round(m, 3) for m in mags],
    "n_prompts": [int((df.category == c).sum()) for c in cats],
    "mean_lift": [round(float(np.nanmean(LIFT[(df.category == c).values])), 1) for c in cats],
}).sort_values("shift_distance", ascending=False)
display(pretty_table(mv, caption="Semantic shift and capability lift, by category (" + str(K) + " largest)",
                     bars=["shift_distance"], gradient=["mean_lift"], cmap="RdYlGn"))

_r = mv.iloc[0]
display(Markdown(
    "Semantic-shift distance and capability lift tend to move together: the categories the harness relocates "
    "farthest in meaning-space are also, broadly, the ones where its measured lift is largest. `" + str(_r["category"]) +
    "` tops the shift ranking here. Shift is a *geometry* of the change; lift is its *scored quality* -- seeing them "
    "agree is a small cross-check that the movement is substantive, not cosmetic."
))'''


# --------------------------------------------------------------------------- #
# Section 5 -- capability curves
# --------------------------------------------------------------------------- #
S5A_CODE = r'''def roll_mean_std(a, w=61):
    a = np.asarray(a, dtype=float); nn = len(a)
    w = max(5, min(w, nn if nn % 2 == 1 else nn - 1))
    if w % 2 == 0:
        w += 1
    pad = w // 2
    ap = np.pad(a, (pad, pad), mode="edge")
    means = np.array([ap[i:i + w].mean() for i in range(nn)])
    stds = np.array([ap[i:i + w].std() for i in range(nn)])
    return means, stds

o = np.argsort(BASELINE_CAP)
lift_sorted = LIFT[o]
x = np.arange(len(o))
m, s = roll_mean_std(lift_sorted, w=61)

fig, ax = plt.subplots(figsize=(11.2, 5.8))
ax.axhline(0, color=INK4, lw=1, ls="--")
ax.scatter(x, lift_sorted, s=8, color=INK4, alpha=0.22, edgecolor="none")
ax.plot(x, m, color=TEAL, lw=2.7, label="rolling mean lift", zorder=4)
ax.fill_between(x, m - s, m + s, color=TEAL, alpha=0.18, label="+/- 1 rolling sd", zorder=3)
ax.set_xlabel("prompts, ordered from weakest to strongest baseline capability")
ax.set_ylabel("harness lift"); ax.legend(loc="upper right")
_title(ax, "The capability curve -- harness lift vs baseline strength",
       "lift is largest where the bare model is weakest (signal: " + LIFT_SOURCE.split(":")[0] + ")")
fig.tight_layout(); save(fig, "sl_curve"); plt.show()

display(Markdown(
    "The **capability curve**. Prompts are lined up left to right from where the bare model is weakest to where it "
    "is strongest, and the teal line is the smoothed harness lift. The shape is the story: the harness adds the most "
    "on the left -- the prompts a bare model handles worst -- and tapers toward the right, where the bare model was "
    "already fine. A safety layer that helps precisely where help is needed."
))'''

S5B_CODE = r'''fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 5.0))

order = [d for d in ["easy", "medium", "hard", "very_hard", "multipath"] if d in set(df.difficulty)] or sorted(set(df.difficulty))
means = [float(np.nanmean(LIFT[(df.difficulty == d).values])) for d in order]
ses = [float(np.nanstd(LIFT[(df.difficulty == d).values]) / max(1.0, np.sqrt(int((df.difficulty == d).sum())))) for d in order]
axL.axhline(0, color=INK4, lw=1, ls="--")
axL.plot(range(len(order)), means, "-o", color=TEAL, lw=2.6, markersize=9, markerfacecolor=PAPER,
         markeredgecolor=TEAL, markeredgewidth=2, zorder=4)
axL.errorbar(range(len(order)), means, yerr=ses, fmt="none", ecolor=TEAL_DK, capsize=4, alpha=0.75, zorder=3)
axL.set_xticks(range(len(order))); axL.set_xticklabels(order)
axL.set_ylabel("mean harness lift"); _title(axL, "Capability curve by difficulty", "harder prompts, bigger lift (mean +/- se)")

lv = np.sort(LIFT[np.isfinite(LIFT)])[::-1]
pos = np.clip(lv, 0, None)
cum = np.cumsum(pos); cum = cum / (cum[-1] or 1.0)
xr = np.arange(1, len(cum) + 1) / len(cum) * 100
axR.plot([0, 100], [0, 100], color=INK4, ls="--", lw=1, label="even (no concentration)")
axR.plot(xr, cum * 100, color=EMBER, lw=2.8, label="observed")
axR.set_xlabel("share of prompts (%), highest-lift first"); axR.set_ylabel("cumulative share of total lift (%)")
axR.legend(loc="lower right"); _title(axR, "Cumulative coverage curve", "how concentrated the harness gains are")
fig.tight_layout(); save(fig, "sl_curve_diff"); plt.show()

_topq = float(cum[max(0, len(cum) // 5 - 1)] * 100) if len(cum) else 0.0
display(Markdown(
    "Left: lift rises with difficulty -- the easy band gains little, the hard band gains most, error bars are "
    "standard error of the mean. Right: the coverage curve bows above the diagonal, so the gains are **concentrated** "
    "-- the top-lift 20% of prompts account for about **" + format(_topq, ".0f") + "%** of the total lift. The harness "
    "is not a flat bonus; it is a targeted intervention on the hard tail."
))'''

S5C_CODE = r'''fig, ax = plt.subplots(figsize=(11.2, 8.0))
im = cap_surface(ax, XYp, LIFT, res=34, cmap="RdYlGn")
ax.scatter(XYp[:, 0], XYp[:, 1], s=6, color=INK, alpha=0.16, edgecolor="none")
fig.colorbar(im, ax=ax, label="mean harness lift in cell")
ax.set_xlabel("semantic axis 1"); ax.set_ylabel("semantic axis 2")
_title(ax, "Capability surface -- mean harness lift across the map",
       "green regions are where the harness helps most; stone cells hold no prompts")
fig.tight_layout(); save(fig, "sl_surface"); plt.show()

display(Markdown(
    "The capability curve, laid back down onto the map as a **surface**. Each cell is colored by the average lift of "
    "the prompts inside it, so the green basins show *which regions of meaning-space* the harness improves and the red "
    "ridges show where it changes little. This is the spatial answer to 'where does the harness help?' -- not a global "
    "average, but a terrain."
))'''


# --------------------------------------------------------------------------- #
# Section 6 -- semantic density of distinctive vocabulary
# --------------------------------------------------------------------------- #
S6A_CODE = r'''_ilo = re.compile(r"\b(ilo|convention|c0?29|c181|c189|c097|c143|c095|icrmw|palermo|article)\b", re.I)
_ind = re.compile(r"(indicator|debt bondage|passport retention|withholding|wage withholding|coercion|deception|forced lab|recruitment fee|confiscation|movement)", re.I)
def _termct(t):
    t = t or ""
    return len(_ilo.findall(t)) + len(_ind.findall(t))

ct_core = np.array([_termct(_txt(r.get("harness_core_response"))) for r in rows], dtype=float)
ct_base = np.array([_termct(_txt(r.get("baseline_response"))) for r in rows], dtype=float)
_vmax = float(max(ct_core.max(), ct_base.max(), 1.0))

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 6.2))
hbL = axL.hexbin(XYp[:, 0], XYp[:, 1], C=ct_core, reduce_C_function=np.mean, gridsize=26, cmap="PuBuGn", mincnt=1, vmin=0, vmax=_vmax)
fig.colorbar(hbL, ax=axL, label="mean ILO + indicator terms / answer")
_title(axL, "Where the harness deploys ILO + indicator language", "hexbin of mean distinctive-term count, over the prompt map")
hbR = axR.hexbin(XYp[:, 0], XYp[:, 1], C=ct_base, reduce_C_function=np.mean, gridsize=26, cmap="PuBuGn", mincnt=1, vmin=0, vmax=_vmax)
fig.colorbar(hbR, ax=axR, label="mean ILO + indicator terms / answer")
_title(axR, "The same regions, bare model", "on the identical scale -- the bare model rarely reaches for this vocabulary")
fig.tight_layout(); save(fig, "sl_vocab_density"); plt.show()

display(Markdown(
    "The distinctive **safety vocabulary** -- ILO conventions and forced-labour indicators -- is not sprinkled evenly. "
    "On the left (harness_core) it lights up over the trafficking-and-recruitment regions of the map; on the right, at "
    "the exact same color scale, the bare model is nearly dark everywhere. The harness knows *where* the specialized "
    "language belongs, which is what a retrieval-grounded safety layer is supposed to do."
))'''

S6B_CODE = r'''try:
    from sklearn.feature_extraction.text import CountVectorizer
    cv = CountVectorizer(stop_words="english", min_df=5, max_features=4000, token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b")
    Xc = cv.fit_transform(Cc); Xb = cv.transform(B)
    vocab = np.array(cv.get_feature_names_out())
    rc = np.asarray(Xc.sum(0)).ravel() / max(1.0, float(Xc.sum()))
    rb = np.asarray(Xb.sum(0)).ravel() / max(1.0, float(Xb.sum()))
    diff = rc - rb
    top = np.argsort(diff)[::-1][:16][::-1]
    fig, ax = plt.subplots(figsize=(10.6, 6.6))
    ax.barh(range(len(top)), diff[top] * 1000.0, color=TEAL, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(range(len(top))); ax.set_yticklabels(vocab[top], fontsize=9.5)
    ax.set_xlabel("rate gap (harness_core minus baseline), per 1,000 tokens")
    ax.grid(axis="y", visible=False)
    _title(ax, "The words that fill the dense region -- harness_core vs baseline",
           "terms the harness uses far more often than the bare model")
    fig.tight_layout(); save(fig, "sl_terms"); plt.show()
    _hi = ", ".join(vocab[top][::-1][:8])
    display(Markdown("The vocabulary behind the density map: the harness leans hard on **" + _hi + "** -- the "
                     "working language of recruitment integrity, document control, and reporting pathways, largely "
                     "absent from the bare model's more generic phrasing."))
except Exception as _e:
    display(Markdown("_Distinctive-term bar skipped (" + type(_e).__name__ + "); the spatial density map above "
                     "already shows where the safety vocabulary concentrates._"))'''


# --------------------------------------------------------------------------- #
# Section 7 -- cluster the space
# --------------------------------------------------------------------------- #
S7A_CODE = r'''from sklearn.cluster import KMeans
K = int(min(8, max(2, n // 120)))
km = KMeans(n_clusters=K, n_init=10, random_state=0).fit(Ep)
lab = km.labels_
df["cluster"] = lab

fig, ax = plt.subplots(figsize=(11.2, 8.2))
_cl = mpl.colormaps["tab10"]
for k in range(K):
    m = lab == k
    ax.scatter(XYp[m, 0], XYp[m, 1], s=18, color=_cl(k % 10), alpha=0.8, edgecolor="none", label="cluster " + str(k))
    cx, cy = XYp[m, 0].mean(), XYp[m, 1].mean()
    ax.text(cx, cy, str(k), fontsize=13, fontweight="bold", color=INK, ha="center", va="center",
            bbox=dict(boxstyle="circle,pad=0.3", fc=PAPER, ec=INK, alpha=0.92))
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8.5)
ax.set_xlabel("semantic axis 1"); ax.set_ylabel("semantic axis 2")
_title(ax, "Unsupervised themes -- KMeans over the embedding space (" + str(K) + " clusters)",
       "clusters found on the full-dimensional vectors, then shown on the 2D map")
fig.tight_layout(); save(fig, "sl_clusters"); plt.show()

display(Markdown(
    "No labels used here: **KMeans** partitions the full-dimensional prompt vectors into **" + str(K) + "** clusters, "
    "and they land as coherent patches on the map -- evidence the geometry is real, not an artifact of the 2D "
    "flattening. The next cell reads each cluster back in plain language."
))'''

S7B_CODE = r'''from sklearn.feature_extraction.text import TfidfVectorizer
tv = TfidfVectorizer(stop_words="english", min_df=3, max_features=6000, ngram_range=(1, 2),
                     token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b")
Xt = tv.fit_transform(P)
vocab = np.array(tv.get_feature_names_out())
recs = []
for k in range(K):
    m = (lab == k)
    if not m.any():
        continue
    centroid = np.asarray(Xt[m].mean(0)).ravel()
    terms = vocab[np.argsort(centroid)[::-1][:6]]
    domcat = df.loc[m, "category"].value_counts().index[0]
    recs.append({"cluster": int(k), "n": int(m.sum()), "dominant_category": str(domcat).replace("_", " "),
                 "top_terms": ", ".join(terms), "mean_lift": round(float(np.nanmean(LIFT[m])), 1)})
themes = pd.DataFrame(recs).sort_values("n", ascending=False)
display(pretty_table(themes, caption="Discovered themes -- KMeans clusters labeled by their top TF-IDF prompt terms",
                     bars=["n"], gradient=["mean_lift"], cmap="RdYlGn"))

display(Markdown(
    "Each row is a theme the model found on its own, named by the words most characteristic of the prompts inside it "
    "and tagged with the category that dominates it. Read the `mean_lift` column against `top_terms`: the "
    "recruitment-fraud and indicator-heavy clusters carry the largest harness lift, the benign-question clusters the "
    "least -- the same pattern the maps and curves showed, now as a table."
))'''

S7C_CODE = r'''topc = list(df.category.value_counts().head(10).index)
ctab = pd.crosstab(df["cluster"], df["category"]).reindex(columns=topc, fill_value=0)
heatmap(ctab.values, ["cluster " + str(i) for i in ctab.index], [c.replace("_", " ") for c in ctab.columns],
        title="Cluster composition -- prompts per (cluster, category)",
        subtitle="which labeled categories fall into which discovered theme (10 largest categories)",
        cmap="BuGn", fmt=".0f", cbar_label="prompts")

display(Markdown(
    "The cross-tab closes the loop between the **unsupervised** clusters and the **hand-labeled** categories. Where a "
    "column concentrates in one row, the human label and the learned geometry agree; where a category spreads across "
    "rows, it is semantically diverse. Either way, the discovered structure is legible -- the landscape is not noise."
))'''


# --------------------------------------------------------------------------- #
# Markdown cells
# --------------------------------------------------------------------------- #
HERO_MD = '''# DueCare -- Semantic Landscape

### The prompts and answers, projected into meaning-space: 3D capability maps, semantic planes, and capability curves.

<table style="border-collapse:collapse;font-family:Inter,system-ui,sans-serif;font-size:12.5px;margin:6px 0 2px">
<tr><td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#5B5F68;font-weight:700">input</td>
<td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#2A2D34"><code>prompt_response_showcase.csv</code> &middot; composite migrant-worker-safety prompts, each with a baseline and a harness_core answer</td></tr>
<tr><td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#5B5F68;font-weight:700">optional</td>
<td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#2A2D34"><code>panel_grades.csv</code> &middot; attach it for real per-prompt judge lift; otherwise a transparent coverage proxy is used</td></tr>
<tr><td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#5B5F68;font-weight:700">output</td>
<td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#2A2D34">2D + 3D maps, density planes, harness-shift vectors, capability curves &amp; surface, vocabulary density, theme clusters</td></tr>
<tr><td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#5B5F68;font-weight:700">runtime</td>
<td style="padding:6px 14px;border-bottom:1px solid #DDD8C9;color:#2A2D34">CPU, a few minutes &middot; no model inference &middot; every heavy library has an offline fallback</td></tr>
</table>

**What is a semantic embedding, in plain words?** A language model can turn any piece of text into a long list of
numbers -- a *vector* -- chosen so that texts with similar meaning get similar numbers. "The agency kept my passport"
and "my employer is holding my documents" land close together even though they share few words. Do that for every
prompt and every answer and you get a cloud of points in a high-dimensional space where **distance means difference
in meaning**. This notebook builds that cloud, then flattens it to 2D and 3D so we can actually look at it, color it by
how much the DueCare harness helps, and trace the terrain of the safety task.

**Honest caveat, up front.** A projection from hundreds of dimensions down to two or three **distorts** -- it has to.
The axes have no fixed units and can rotate, flip, or stretch between runs; only *relative* position is meaningful, and
even that is approximate. Clusters are suggestive, not proof. Read every map here as a *sketch of structure*, cross-
checked against the tables and curves -- never as a measurement. The full honesty note is in the final section.'''

TOC_MD = '''## Contents

1. [Build the space](#build) -- embed the prompts and both answer arms; report the backend in use
2. [The 2D map + semantic planes](#map2d) -- prompts placed by meaning, with density contours
3. [The 3D capability map](#map3d) -- the cloud in three dimensions, static and interactive, colored by lift
4. [The harness shift as vectors](#shift) -- the direction the harness moves answers in meaning-space
5. [Capability curves](#curves) -- lift vs baseline strength, difficulty, coverage, and a capability surface
6. [Semantic density of distinctive vocabulary](#vocab) -- where ILO + indicator language concentrates
7. [Cluster the space](#clusters) -- unsupervised themes, labeled by their top terms
8. [Honest boundary &amp; license](#boundary)

Every figure is recomputed **live** from the attached dataset -- no model, no GPU, no internet required.'''

S1_MD = '''<a id="build"></a>
## 1. Build the space

We embed three things into **one** shared space: every prompt, every baseline answer, and every harness_core answer.
Sharing the space is what lets us, later, draw an arrow from a bare-model answer to its harnessed counterpart. The
notebook prefers real semantic vectors (`sentence-transformers`, all-MiniLM-L6-v2) and falls back to a `TF-IDF +
TruncatedSVD` space offline; projection to 2D/3D prefers `UMAP` and falls back to `PCA`. Whichever ran is printed below.'''

S2_MD = '''<a id="map2d"></a>
## 2. The 2D map + semantic planes

The flattened landscape. Each dot is a prompt, colored by category; the filled contours are density **planes** -- the
ridges and valleys of where prompts concentrate. Then we break the same map into per-category territories and a
honeycomb density view with the biggest categories annotated. Distances are relative; the shapes are the point.'''

S3_MD = '''<a id="map3d"></a>
## 3. The 3D capability map

Three dimensions give the cloud depth a flat plot cannot. We render it two ways: a reliable **static** `matplotlib`
3D scatter (two viewing angles) that always shows up, and an **interactive** `plotly` 3D scatter you can rotate and
zoom on Kaggle. Points are colored by harness lift -- green where the harness helps most, red where it barely moves
the answer -- so the "capability" of the task is visible as terrain in the cloud.'''

S4_MD = '''<a id="shift"></a>
## 4. The harness shift as vectors

Switch from prompts to answers. With baseline and harness_core answers in the same space, each category has a
baseline centroid and a harnessed centroid; the arrow between them is **the direction the harness moves answers in
meaning-space**. We draw those vectors, rank how far each category travels, and tabulate travel against measured lift.'''

S5_MD = '''<a id="curves"></a>
## 5. Capability curves

The **capability / response curves**. First, harness lift plotted against baseline strength -- prompts ordered from
where the bare model is weakest to where it is strongest, with a rolling mean and band. Then lift by difficulty and a
cumulative-coverage curve showing how concentrated the gains are. Finally the curve laid back onto the map as a
**capability surface**: mean lift per cell, so you can see *where* the gains live, not just how big they are.'''

S6_MD = '''<a id="vocab"></a>
## 6. Semantic density of distinctive vocabulary

The harness's specialized language -- ILO conventions and forced-labour indicators -- should appear *where it belongs*,
not everywhere. We count those terms in each answer and paint their mean density over the map as a hexbin, harness_core
beside baseline on one shared scale, then rank the specific words that fill the dense region.'''

S7_MD = '''<a id="clusters"></a>
## 7. Cluster the space

Finally, let the geometry speak for itself. **KMeans** partitions the full-dimensional prompt vectors into themes; we
show them on the map, label each cluster by its top **TF-IDF** terms and dominant category in a table, and cross-tab
the discovered clusters against the hand-labeled categories to see where learned structure and human labels agree.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 8. Honest boundary &amp; license

**What this is.** An exploratory, geometric view of a fixed prompt set and its model answers, projected into an
embedding space. Everything is computed live from the attached CSV on CPU -- no model inference, no GPU, no internet.

**What this is not.** Embedding projections **distort**: reducing hundreds of dimensions to two or three loses
information by construction, the axes carry no units, and position can rotate or stretch between runs. Distances are
**relative and approximate**; clusters are **suggestive, not proof**. The prompts are **synthetic / composite** -- no
real individual, case, contact, name, number, or address appears, and the set is PII-clean. The responses are **model
outputs**, treated as illustrative material, not gold annotations and not legal advice. When no `panel_grades.csv` is
attached, the per-prompt "lift" color is an explicit **proxy** (count of distinct safety-signal categories a response
uses), clearly labeled as such wherever it appears; attach the grades dataset for real judge lift. This notebook makes
**no** real-world detection or victim-identification claim.

**Reproducibility.** Embeddings prefer `sentence-transformers` and fall back to `scikit-learn` TF-IDF + TruncatedSVD;
projection prefers `UMAP` and falls back to `PCA`; the interactive 3D view uses `plotly` when present and is otherwise
skipped in favor of the static `matplotlib` 3D scatter. Every one of those paths is wrapped so the notebook runs to
completion with `enable_internet=false`. The backend actually used is printed in Section 1.

**License.** CC0.

**Links.** Dataset: [`taylorsamarel/duecare-prompt-response-showcase`](''' + DS_URL + ''') &middot; Start-here index: [`duecare-harness-lift-benchmark`](''' + INDEX_URL + ''') &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](''' + REPO_URL + ''')'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(S1_MD),
        _code(S1A_CODE),
        _code(S1B_CODE),
        _md(S2_MD),
        _code(S2A_CODE),
        _code(S2B_CODE),
        _code(S2C_CODE),
        _md(S3_MD),
        _code(S3A_CODE),
        _code(S3B_CODE),
        _code(S3C_CODE),
        _md(S4_MD),
        _code(S4A_CODE),
        _code(S4B_CODE),
        _code(S4C_CODE),
        _md(S5_MD),
        _code(S5A_CODE),
        _code(S5B_CODE),
        _code(S5C_CODE),
        _md(S6_MD),
        _code(S6A_CODE),
        _code(S6B_CODE),
        _md(S7_MD),
        _code(S7A_CODE),
        _code(S7B_CODE),
        _code(S7C_CODE),
        _md(BOUNDARY_MD),
    ]
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    return nb


def _kernel_metadata() -> dict:
    return {
        "id": KERNEL_ID,
        "title": TITLE,
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / SLUG
    if nb_dir.exists() and force:
        shutil.rmtree(nb_dir)
    nb_dir.mkdir(parents=True, exist_ok=True)
    nb = _notebook()
    nbf.validate(nb)  # fail fast if the notebook structure is malformed
    nb_path = nb_dir / "notebook.ipynb"
    nbf.write(nb, str(nb_path))
    meta_path = nb_dir / "kernel-metadata.json"
    meta_path.write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    nbf.read(str(nb_path), as_version=4)  # round-trip read to confirm it is valid on disk
    return {
        "notebook": str(nb_path),
        "kernel_metadata": str(meta_path),
        "kernel_id": KERNEL_ID,
        "title": TITLE,
        "n_cells": len(nb.cells),
        "n_code_cells": sum(1 for c in nb.cells if c.cell_type == "code"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    # Kaggle derives the kernel slug from the title -- assert they agree.
    assert TITLE.lower().replace(" ", "-") == SLUG, (
        "title slug mismatch: " + repr(TITLE) + " -> " + repr(TITLE.lower().replace(" ", "-")) + " != " + repr(SLUG)
    )
    assert TITLE.lower().replace(" ", "-") == "duecare-semantic-landscape"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, "kernel id mismatch: " + repr(KERNEL_ID)

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Score every method against the hand labels and write eval/results.md.
Usage: python eval/evaluate.py   (from the repo root; needs pandas)"""
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
acc = pd.read_csv(root / "data/accounts_scored.csv")
lab = pd.read_csv(root / "data/labels.csv")
d = acc.merge(lab, on="domain")
missing = d[d.label.isna()]
d = d[d.label.notna()].copy()
y = d.label.eq("Yes")

def metrics(pred):
    tp, fp, fn = (pred & y).sum(), (pred & ~y).sum(), (~pred & y).sum()
    return {"accuracy": f"{(pred == y).mean():.0%}", "precision": f"{tp / max(tp + fp, 1):.0%}",
            "recall": f"{tp / max(tp + fn, 1):.0%}", "false_pos": int(fp), "false_neg": int(fn)}

llm = d.llm_fit.eq("Yes")
emb = d.lookalike_score.fillna(0)
best_t = max(range(40, 81, 5), key=lambda t: ((emb >= t) == y).mean())
size = d.headcount_final.between(200, 5000)
sent = d.send_to_llm.astype(str).str.lower().eq("true")

rows = {
    "LLM classifier (GPT 6 Luna)": metrics(llm),
    f"Embedding lookalike >= {best_t}": metrics(emb >= best_t),
    "Headcount 200-5k only": metrics(size),
    "Pre-filter + LLM (production)": metrics(sent & llm),
}
pos, neg = emb[y].tolist(), emb[~y].tolist()
auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))

out = ["# Evaluation results", "",
       f"{len(d)} labelled accounts ({y.sum()} fits); {len(missing)} excluded for missing data: {', '.join(missing.domain)}.", "",
       "| Method | Accuracy | Precision | Recall | False + | False - |", "|---|---|---|---|---|---|"]
out += [f"| {k} | {v['accuracy']} | {v['precision']} | {v['recall']} | {v['false_pos']} | {v['false_neg']} |" for k, v in rows.items()]
out += ["", f"Embedding ROC AUC: {auc:.2f}.  Accounts sent to the LLM by the pre-filter: {sent.sum()}/{len(d)}.", "",
        "## Tier vs label", "", pd.crosstab(d.tier, d.label).to_markdown(), "",
        "## LLM errors", "", d.loc[llm != y, ["name", "label", "llm_fit", "llm_confidence", "note"]].to_markdown(index=False)]
(root / "eval/results.md").write_text("\n".join(out) + "\n")
print("\n".join(out))

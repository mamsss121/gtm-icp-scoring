# ICP scoring engine: Clay + LLM + embeddings

An account scoring workflow that tells BDRs which companies to work first, and a measurement of how accurate it is.

Built in Clay, with a small FastAPI embedding service and an n8n → Slack alert. Tested on 50 real companies against hand-labelled ground truth.

## Results

| Method | Accuracy | Precision | Recall | Cost per account |
|---|---|---|---|---|
| LLM classifier (GPT 6 Luna) | 96% | 90% | 100% | ~0.1 credits |
| Pre-filter + LLM (production setup) | 96% | 90% | 100% | ~0.06 credits (29 of 49 sent to the LLM) |
| Headcount band only | 78% | 63% | 100% | free |
| Embedding lookalike ≥ 60 | 69% | 61% | 58% | free |

- The LLM does the judging. Embeddings alone are weak (ROC AUC 0.71): they can't see company size, and buzzwords fool them. They are useful as a **free pre-filter**.
- **Tier A:** 11 accounts, 10 real fits. **Tier C:** 28 accounts, no real fit in it.
- Full numbers: [`eval/results.md`](eval/results.md). Write-up: see the linked doc.

## How it works

```
Clay table (50 accounts)
 └─ Enrich company ─────────────► description, headcount, country (0.5 credits)
     ├─ Lookalike API (HTTP) ───► similarity to 10 best customers (own FastAPI, 0 credits)
     ├─ Headcount web check ────► only rows >5,000 staff that still look like customers
     ├─ Pre-filter (formula) ───► headcount 150–6,000 and lookalike ≥ 45
     ├─ LLM classifier ─────────► fit, confidence, reason (~0.1 credits)
     ├─ Tier (formula) ─────────► A / B / C / No data
     └─ Tier A ─► n8n webhook ─► route by country ─► Slack #bdr-emea / #bdr-americas / #bdr-apac
```

## Repo layout

| Path | What |
|---|---|
| `scorer/` | FastAPI lookalike service: MiniLM embeddings (fastembed, no PyTorch), cosine similarity to the centroid of 10 best customers |
| `clay/workflow.md` | Every Clay column: prompts, formulas, run conditions, HTTP bodies |
| `n8n/clay_tier_a_to_slack.json` | Importable n8n workflow: webhook → route by country → Slack |
| `data/accounts_scored.csv` | Final Clay export (scores, tiers, alerts sent) |
| `data/labels.csv` | My ground-truth labels, with notes on the 7 borderline cases |
| `eval/evaluate.py` | Recomputes every metric from the two CSVs and writes `eval/results.md` |

## Run it

**Lookalike scorer** (runs on a laptop; tested on an 8 GB M1):
```bash
cd scorer
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --port 8000   # first start downloads the model (~90 MB)
ngrok http 8000                                     # public URL for Clay's HTTP API column
```
```bash
curl -X POST localhost:8000/score -H "Content-Type: application/json" \
  -d '{"description":"HR software platform for mid-size companies"}'
# {"lookalike_score":66,"max_similarity":59,"nearest_customer":"HiBob"}
```
Set `SCORER_API_KEY` to require an `x-api-key` header. To change the best customers, export them from Clay and run `python build_seeds.py export.csv`.

**Evaluation:**
```bash
pip install pandas tabulate
python eval/evaluate.py
```

## What broke (and the fix)

- **Wrong or missing matches:** `glovo.com` not found (fixed to `glovoapp.com`); `zara.com` matched the wrong company → tier "No data" instead of a false "C".
- **Inflated headcount:** Remote listed at 19,877 because contractors on its platform are counted → a web check on suspicious rows only corrected it to ~3,000, and Remote moved from C to B.
- **LLM format drift:** "Not a fit" instead of "No", confidence 0.96 instead of 96 → strict output rules in the prompt.
- **Stale rows:** re-ran only out-of-date rows after each prompt change, so every score comes from the same prompt version.

## Next

Salesforce + Salesloft sync for Tier A/B, contact finding for Tier A only, a headcount waterfall, a Slack bot user, scheduled runs with job-change and web-intent signals, and hosting the scorer outside a laptop.

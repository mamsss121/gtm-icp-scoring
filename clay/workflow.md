# Clay table setup

Everything below lives in one Clay table, `accounts_50`. Columns are listed in the order they run.
Table mode is **Manual** (auto-run off): every paid column was tested on 5–10 rows before a full run.

## 1. Enrich company
- Provider: Clay "Enrich company", 0.5 credits/row
- Input: `domain`
- Fields kept as columns: Name, Employee Count, Industry, Description, Country

## 2. Lookalike API (HTTP API column, 0 data credits)
- `POST https://<ngrok-url>/score`
- Headers: `Content-Type: application/json`, `ngrok-skip-browser-warning: true`
- Body: `{"name": "{{Name}}", "description": "{{Description}}"}`
- Run condition: Description is not empty
- Fields kept: `lookalike_score`, `max_similarity`, `nearest_customer`

## 3. Headcount check (Use AI, web research)
Only for rows whose headcount looks wrong: "too big" but still similar to our customers.
- Prompt:
  ```
  How many people does {{Name}} ({{domain}}) employ directly as staff?
  Exclude contractors, freelancers or workers hired through its platform for customers.
  Use the most recent reliable source.
  ```
- Outputs: `employees` (number), `source` (text)
- Run condition: `{{Employee Count}} > 5000 && {{Lookalike Score}} >= 60`

## 4. Headcount (final) — formula, number
```
({{Employee Count}} > 5000 && {{Lookalike Score}} >= 60 && {{Headcount check}}?.employees) || {{Employee Count}}
```
The run condition is repeated inside the formula so a stray result from an accidental run is ignored.

## 5. Send to LLM? — formula (the free pre-filter)
```
{{Headcount (final)}} >= 150 && {{Headcount (final)}} <= 6000 && {{Lookalike Score}} >= 45
```
The band is wider than the ICP's 200–5,000 because headcount data is approximate; the LLM makes the final call.

## 6. ICP Fit Assessment (Use AI, "Create or modify content", GPT 6 Luna, ~0.1 credits/row) — prompt v3
```
You are a B2B sales analyst. Decide if this company fits our Ideal Customer Profile.

ICP (good fit): B2B software/SaaS company, sells mainly to other businesses (not consumers), 200–5,000 employees, has a sales team.
Not a fit: consumer apps or marketplaces, retailers, banks, airlines, agencies or consultancies, companies under 200 or over 5,000 employees.

Company: {{Name}}
Industry: {{Industry}}
Employees: {{Headcount (final)}}
Description: {{Description}}

Headcount data can be approximate, so use the description as the main evidence.

Output rules:
- "fit" must be exactly "Yes" or "No". Nothing else.
- "confidence" is an integer from 0 to 100.
- "reason" is one short sentence (max 25 words).
```
- Outputs: `fit` (text), `confidence` (number), `reason` (text)
- In production, add the run condition `{{Send to LLM?}}` so the LLM only runs on rows that pass the pre-filter.

Prompt history: v1 had no output rules (format drift: "Not a fit", confidence 0.96); v2 added them; v3 reads `Headcount (final)`.

## 7. Tier — formula
```
!{{Description}} ? "No data" : ({{Use AI Fit}} === "Yes" && {{Use AI Confidence 2}} >= 90 && {{Lookalike Score}} >= 60 ? "A" : ({{Use AI Fit}} === "Yes" ? "B" : "C"))
```
Known issue: one row still returns confidence 0.96 instead of 96. Normalising with `({{Use AI Confidence 2}} <= 1 ? {{Use AI Confidence 2}} * 100 : {{Use AI Confidence 2}})` fixes it.

## 8. Send to Slack (HTTP API column)
- `POST https://<your-n8n>/webhook/clay-tier-a`
- Body:
  ```
  {"name": "{{Name}}", "domain": "{{domain}}", "country": "{{Country}}",
   "reason": "{{Use AI Reason}}", "confidence": "{{Use AI Confidence 2}}",
   "lookalike_score": "{{Lookalike Score}}", "nearest_customer": "{{Nearest Customer}}",
   "headcount": "{{Headcount (final)}}"}
  ```
- Run condition: `{{Tier}} === "A"`

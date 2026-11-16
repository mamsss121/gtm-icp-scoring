# Evaluation results

49 labelled accounts (19 fits); 1 excluded for missing data: zara.com.

| Method | Accuracy | Precision | Recall | False + | False - |
|---|---|---|---|---|---|
| LLM classifier (GPT 6 Luna) | 96% | 90% | 100% | 2 | 0 |
| Embedding lookalike >= 60 | 69% | 61% | 58% | 7 | 8 |
| Headcount 200-5k only | 78% | 63% | 100% | 11 | 0 |
| Pre-filter + LLM (production) | 96% | 90% | 100% | 2 | 0 |

Embedding ROC AUC: 0.71.  Accounts sent to the LLM by the pre-filter: 29/49.

## Tier vs label

| tier   |   No |   Yes |
|:-------|-----:|------:|
| A      |    1 |    10 |
| B      |    1 |     9 |
| C      |   28 |     0 |

## LLM errors

| name    | label   | llm_fit   |   llm_confidence | note                                  |
|:--------|:--------|:----------|-----------------:|:--------------------------------------|
| Deel    | No      | Yes       |               90 | B2B HR SaaS but likely >5k            |
| Freepik | No      | Yes       |               83 | Mostly creator/consumer subscriptions |

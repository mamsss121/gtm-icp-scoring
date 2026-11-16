"""Turn the Clay CSV export of the 10 best customers into seed_customers.json.
Usage: python build_seeds.py path/to/clay_export.csv"""
import csv, json, sys

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
seeds = [{"name": r["Name"], "description": r["Description"]}
         for r in rows if r.get("Name") and r.get("Description")]
json.dump(seeds, open("seed_customers.json", "w"), indent=2, ensure_ascii=False)
print(f"wrote {len(seeds)} seeds")

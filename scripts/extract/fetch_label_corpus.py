"""Gate 4 step 1: build the openFDA label corpus for the extraction mini-eval.

Pulls the CYP-relevant label sections (drug_interactions, contraindications,
clinical_pharmacology, warnings_and_cautions) for the crosswalk ingredient set,
verbatim (NOT pre-filtered to CYP sentences — pre-filtering would leak the
answer to the extractor). Saves fixtures/openfda-labels/corpus.json.

No API key required (openFDA is CC0). Optional key raises rate limits only.

Run:
  PYTHONUTF8=1 python scripts/extract/fetch_label_corpus.py fixtures/openfda-labels/corpus.json
"""
import json
import os
import sys
import time
import requests

BASE = "https://api.fda.gov/drug/label.json"

# ~22 drugs. Aligned to fixtures/crosswalk/ingredient_crosswalk_v0.csv (18)
# plus 4 extra CYP3A4 actors to reach the DESIGN "20-30 label" gate target.
# The `expect` tag is documentation only; the gold answer key is authored
# separately in fixtures/gold/extraction_gold_v0.jsonl.
DRUGS = [
    ("simvastatin", "substrate"),
    ("lovastatin", "substrate"),
    ("atorvastatin", "substrate"),
    ("pravastatin", "none"),        # non-CYP3A4 statin (negative)
    ("rosuvastatin", "none"),       # non-CYP3A4 statin (negative)
    ("clarithromycin", "inhibitor-strong"),
    ("erythromycin", "inhibitor-strong"),
    ("itraconazole", "inhibitor-strong"),
    ("ketoconazole", "inhibitor-strong"),
    ("ritonavir", "inhibitor-strong"),
    ("diltiazem", "inhibitor-moderate"),
    ("verapamil", "inhibitor-moderate"),
    ("amiodarone", "inhibitor-moderate"),
    ("dronedarone", "inhibitor-moderate"),
    ("rifampin", "inducer-strong"),
    ("carbamazepine", "inducer-strong"),
    ("phenytoin", "inducer-strong"),
    ("midazolam", "substrate"),     # hard-negative pairing anchor
    # --- 4 extra to reach the gate target ---
    ("fluconazole", "inhibitor-moderate"),
    ("nefazodone", "inhibitor-strong"),
    ("phenobarbital", "inducer-strong"),
    ("cyclosporine", "inhibitor-moderate"),
]

SECTIONS = [
    "drug_interactions",
    "contraindications",
    "clinical_pharmacology",
    "warnings_and_cautions",
]

# Cap per-section length so one verbose label can't blow the corpus / the
# extractor's context. Raised to 15000 after an 8000 cap truncated
# nefazodone's "inhibition of CYP3A4 by nefazodone" sentence (deep in
# drug_interactions) — a real recall bug caused by the cap, not the label.
SECTION_CAP = 15000


def fetch(drug, api_key=None):
    params = {"search": f'openfda.generic_name:"{drug}"', "limit": 1}
    if api_key:
        params["api_key"] = api_key
    r = requests.get(BASE, params=params, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        return None
    return data["results"][0]


def main():
    outpath = sys.argv[1] if len(sys.argv) > 1 else "fixtures/openfda-labels/corpus.json"
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    api_key = os.environ.get("OPENFDA_API_KEY")

    corpus = {}
    for drug, expect in DRUGS:
        try:
            rec = fetch(drug, api_key)
        except Exception as e:
            print(f"  {drug:16s} ERROR {e}")
            corpus[drug] = {"found": False, "error": str(e), "expect": expect}
            continue
        if rec is None:
            print(f"  {drug:16s} NOT FOUND")
            corpus[drug] = {"found": False, "expect": expect}
            continue
        openfda = rec.get("openfda", {})
        setid = rec.get("set_id") or (openfda.get("spl_set_id") or ["?"])[0]
        sections = {}
        for sec in SECTIONS:
            if sec not in rec:
                continue
            text = " ".join(rec[sec]) if isinstance(rec[sec], list) else str(rec[sec])
            text = " ".join(text.split())  # normalize whitespace
            if text:
                sections[sec] = text[:SECTION_CAP]
        corpus[drug] = {
            "found": True,
            "set_id": setid,
            "expect": expect,
            "sections": sections,
        }
        nchars = sum(len(v) for v in sections.values())
        print(f"  {drug:16s} OK   set_id={setid[:12]}…  sections={len(sections)}  {nchars} chars")
        time.sleep(0.2)  # be polite to the anonymous rate limit

    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
    found = sum(1 for v in corpus.values() if v.get("found"))
    print(f"\nsaved {found}/{len(DRUGS)} labels -> {outpath}")


if __name__ == "__main__":
    main()

"""Gate 3 support: pull CYP3A4 role sentences from PERPETRATOR labels, and
check whether they name specific victims (co-naming => weak graph-win).
"""
import json
import re
import sys
import requests

BASE = "https://api.fda.gov/drug/label.json"
CYP_SENT = re.compile(r"[^.;]*CYP3A4[^.;]*[.;]", re.IGNORECASE)


def fetch(drug):
    params = {"search": f'openfda.generic_name:"{drug}"', "limit": 1}
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d["results"][0] if d.get("results") else None


DRUGS = ["itraconazole", "diltiazem", "erythromycin", "rifampin",
         "carbamazepine", "midazolam", "atorvastatin", "lovastatin"]
SECTIONS = ["drug_interactions", "clinical_pharmacology", "contraindications",
            "warnings_and_cautions", "pharmacokinetics"]


def main():
    out = {}
    for drug in DRUGS:
        try:
            rec = fetch(drug)
        except Exception as e:
            out[drug] = {"error": str(e)}
            continue
        if not rec:
            out[drug] = {"found": False}
            continue
        role_sents = []
        for sec in SECTIONS:
            if sec not in rec:
                continue
            text = " ".join(rec[sec]) if isinstance(rec[sec], list) else str(rec[sec])
            for m in CYP_SENT.finditer(text):
                s = re.sub(r"\s+", " ", m.group()).strip()
                if len(s) > 30:
                    role_sents.append({"sec": sec, "s": s[:260]})
        # dedup
        seen, uniq = set(), []
        for r in role_sents:
            k = r["s"][:60]
            if k not in seen:
                seen.add(k); uniq.append(r)
        out[drug] = {"found": True, "cyp3a4_sentences": uniq[:6]}
        print(f"\n{'='*70}\n{drug}\n{'='*70}")
        for r in uniq[:6]:
            print(f"  [{r['sec']}] {r['s']}")

    with open(sys.argv[1] if len(sys.argv) > 1 else "gate3_perp.json", "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

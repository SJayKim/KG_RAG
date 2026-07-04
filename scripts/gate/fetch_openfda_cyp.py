"""Gate 2: openFDA 라벨에서 CYP3A4 기질/억제 문장 실재 확인.
No API key needed (CC0). Fetch simvastatin + a few probe drugs.
"""
import json
import re
import sys
import requests

BASE = "https://api.fda.gov/drug/label.json"

# probe set: substrate (simvastatin), inhibitors (clarithromycin, amiodarone),
# inducer (rifampin/rifampicin)
PROBES = {
    "simvastatin": "substrate?",
    "clarithromycin": "inhibitor?",
    "amiodarone": "inhibitor?",
    "rifampin": "inducer?",
}

SECTIONS = [
    "drug_interactions",
    "clinical_pharmacology",
    "contraindications",
    "warnings_and_cautions",
    "warnings",
]

CYP_RE = re.compile(r"CYP\s?[0-9][A-Z][0-9]{1,2}", re.IGNORECASE)


def fetch(drug):
    params = {"search": f'openfda.generic_name:"{drug}"', "limit": 1}
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        return None
    return data["results"][0]


def sentences_with_cyp(text):
    # naive sentence split
    out = []
    for sent in re.split(r"(?<=[.;])\s+", text):
        if CYP_RE.search(sent) and re.search(r"CYP3A4", sent, re.IGNORECASE):
            out.append(sent.strip())
    return out


def main():
    report = {}
    for drug, role in PROBES.items():
        print(f"\n{'='*70}\n{drug}  (expected: {role})\n{'='*70}")
        try:
            rec = fetch(drug)
        except Exception as e:
            print(f"  ERROR: {e}")
            report[drug] = {"error": str(e)}
            continue
        if rec is None:
            print("  no results")
            report[drug] = {"found": False}
            continue
        openfda = rec.get("openfda", {})
        setid = rec.get("set_id") or (openfda.get("spl_set_id") or ["?"])[0]
        drug_report = {"found": True, "set_id": setid, "sections": {}}
        for sec in SECTIONS:
            if sec not in rec:
                continue
            text = " ".join(rec[sec]) if isinstance(rec[sec], list) else str(rec[sec])
            hits = sentences_with_cyp(text)
            if hits:
                print(f"\n  [{sec}]  {len(hits)} CYP3A4 sentence(s):")
                for h in hits[:4]:
                    print(f"    - {h[:220]}")
                drug_report["sections"][sec] = hits[:4]
        report[drug] = drug_report

    outpath = sys.argv[1] if len(sys.argv) > 1 else "gate2_report.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n\nsaved -> {outpath}")


if __name__ == "__main__":
    main()

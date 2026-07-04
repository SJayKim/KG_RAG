"""Gate 2b: from the SUBSTRATE label (simvastatin), find named perpetrators +
their dose limits. This is how the graph's INHIBITS/INDUCES edges get their
strength/clinical_action grounded when the perpetrator's own label is weak.
"""
import json
import re
import sys
import requests

BASE = "https://api.fda.gov/drug/label.json"


def fetch(drug):
    params = {"search": f'openfda.generic_name:"{drug}"', "limit": 1}
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["results"][0] if data.get("results") else None


PERPETRATORS = [
    "amiodarone", "clarithromycin", "erythromycin", "itraconazole",
    "ketoconazole", "diltiazem", "verapamil", "gemfibrozil", "cyclosporine",
    "grapefruit", "rifampin", "dronedarone", "ranolazine",
]

SECTIONS = ["contraindications", "warnings_and_cautions", "drug_interactions",
            "dosage_and_administration"]


def main():
    rec = fetch("simvastatin")
    findings = {}
    for sec in SECTIONS:
        if sec not in rec:
            continue
        text = " ".join(rec[sec]) if isinstance(rec[sec], list) else str(rec[sec])
        for perp in PERPETRATORS:
            for m in re.finditer(perp, text, re.IGNORECASE):
                start = max(0, m.start() - 120)
                end = min(len(text), m.end() + 160)
                snippet = text[start:end].replace("\n", " ")
                snippet = re.sub(r"\s+", " ", snippet)
                findings.setdefault(perp, []).append({"section": sec, "ctx": snippet})

    for perp in PERPETRATORS:
        hits = findings.get(perp, [])
        print(f"\n{'='*70}\n{perp}: {len(hits)} mention(s) in simvastatin label\n{'='*70}")
        seen = set()
        for h in hits:
            key = h["ctx"][:80]
            if key in seen:
                continue
            seen.add(key)
            print(f"  [{h['section']}] ...{h['ctx']}...")

    with open(sys.argv[1] if len(sys.argv) > 1 else "gate2b.json", "w",
              encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

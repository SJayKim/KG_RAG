"""Gate 4 step 2b: bidirectional recovery (DESIGN gate Finding 3).

Many perpetrator labels do not self-attribute their CYP3A4 role (ketoconazole,
erythromycin, ritonavir... their own openFDA label never says "X is a CYP3A4
inhibitor"). But the SUBSTRATE labels enumerate them:

  lovastatin label: "Strong inhibitors of CYP3A4 (e.g., itraconazole,
  ketoconazole, ... clarithromycin, ... nefazodone, erythromycin, ...)"

This script mines the substrate labels (the drugs we know are substrates) for
enumerated inhibitor/inducer name lists, then recovers a typed edge for any
crosswalk drug named there whose single-direction extraction missed it. Every
recovered edge carries provenance: which substrate label named it.

It is deterministic (name-matching against the crosswalk), so the recall lift
is auditable, not hand-authored.

Run:
  PYTHONUTF8=1 python scripts/extract/augment_bidirectional.py \
      fixtures/openfda-labels/corpus.json \
      fixtures/openfda-labels/extracted_llm.json \
      fixtures/crosswalk/ingredient_crosswalk_v0.csv \
      fixtures/openfda-labels/extracted_llm_bidir.json
"""
import csv
import json
import re
import sys

# Substrate labels do the enumerating. Restrict mining to drugs whose own
# extraction found a substrate role (so we trust the enumeration context).
STRONG_INHIB_CTX = re.compile(r"strong inhibitors? of CYP\s?3\s?A\s?4", re.IGNORECASE)
INHIB_CTX = re.compile(r"inhibitors? of CYP\s?3\s?A\s?4|CYP\s?3\s?A\s?4 inhibitors?", re.IGNORECASE)
INDUCER_CTX = re.compile(r"inducers? of CYP\s?3\s?A\s?4|CYP\s?3\s?A\s?4 inducers?", re.IGNORECASE)


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def load_crosswalk(path):
    drugs = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            drugs[row["ingredient_en"].strip().lower()] = row
    return drugs


def has_cyp_edge(edges, role):
    for e in edges:
        if str(e.get("enzyme", "")).upper().replace(" ", "") == "CYP3A4" \
                and e.get("role") == role and not e.get("negated"):
            return True
    return False


def main():
    corpus_p, ext_p, xwalk_p, out_p = sys.argv[1:5]
    corpus = json.load(open(corpus_p, encoding="utf-8"))
    extracted = json.load(open(ext_p, encoding="utf-8"))
    xwalk = load_crosswalk(xwalk_p)
    drugs = extracted["drugs"]

    # substrate labels = drugs whose single-direction extraction found substrate
    substrate_labels = [d for d, rec in drugs.items()
                        if has_cyp_edge(rec.get("edges", []), "substrate")]

    recovered = []  # (target_drug, role, strength, action, source_label, sentence)
    for host in substrate_labels:
        sections = corpus.get(host, {}).get("sections", {})
        for sec, text in sections.items():
            for sent in split_sentences(text):
                inhib_cues = [m.start() for m in INHIB_CTX.finditer(sent)]
                inducer_cues = [m.start() for m in INDUCER_CTX.finditer(sent)]
                if not (inhib_cues or inducer_cues):
                    continue
                is_strong_inhib = bool(STRONG_INHIB_CTX.search(sent))
                low = sent.lower()
                for name, row in xwalk.items():
                    if name == host:
                        continue
                    m = re.search(rf"\b{re.escape(name)}\b", low)
                    if not m:
                        continue
                    pos = m.start()
                    # PROXIMITY: attribute the role whose cue phrase is nearest
                    # to this drug's mention. A sentence enumerating BOTH
                    # inhibitors and inducers (e.g. verapamil's label) must not
                    # tag an inducer as an inhibitor.
                    d_inhib = min((abs(pos - c) for c in inhib_cues), default=1e9)
                    d_induce = min((abs(pos - c) for c in inducer_cues), default=1e9)
                    if d_induce < d_inhib:
                        role = "inducer"
                        strength = "strong" if "strong" in low else None
                        action = "monitor"
                    else:
                        role = "inhibitor"
                        strength = "strong" if is_strong_inhib else None
                        action = "contraindicated" if is_strong_inhib else "dose-adjust"
                    # only recover if single-direction missed this role
                    if has_cyp_edge(drugs.get(name, {}).get("edges", []), role):
                        continue
                    recovered.append({
                        "target": name, "role": role, "strength": strength,
                        "action": action, "source_label": host,
                        "sentence": sent[:300],
                    })

    # merge: dedupe recovered by (target, role); prefer strong evidence
    best = {}
    for r in recovered:
        k = (r["target"], r["role"])
        if k not in best or (r["strength"] == "strong" and best[k]["strength"] != "strong"):
            best[k] = r

    out = json.loads(json.dumps(extracted))  # deep copy
    out["direction"] = "bidirectional (own label + substrate-label enumeration recovery)"
    n_added = 0
    for (target, role), r in best.items():
        edge = {
            "role": role, "enzyme": "CYP3A4", "strength": r["strength"],
            "clinical_action": r["action"],
            "evidence_sentence": r["sentence"], "negated": False,
            "confidence": 0.75,
            "recovered_from": f"substrate-label:{r['source_label']}",
        }
        out["drugs"].setdefault(target, {"edges": []})["edges"].append(edge)
        n_added += 1
        print(f"  recovered {target:14s} {role:9s} (strength={r['strength']}) "
              f"<- {r['source_label']} label")

    json.dump(out, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nsubstrate labels mined: {substrate_labels}")
    print(f"recovered {n_added} edge(s) -> {out_p}")


if __name__ == "__main__":
    main()

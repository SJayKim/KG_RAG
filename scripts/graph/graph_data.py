"""Shared source-of-truth builder for PolyPharmGraph.

Reads the Week 1 fixtures and produces normalized node/edge lists used by both
the Neo4j loader (load_graph.py) and the Kuzu exporter (export_kuzu.py) so the
two backends load byte-identical graph content.

Run with:  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python graph_data.py
to print the D-code reconciliation report on its own.
"""
from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "fixtures")

DCODE_DICT = os.path.join(FIX, "dur-samples", "dur_ingredient_dcode_dict.json")
CONTRA = os.path.join(FIX, "dur-samples", "dur_contraindication_edges_full.json")
BIDIR = os.path.join(FIX, "openfda-labels", "extracted_llm_bidir.json")
CROSSWALK = os.path.join(FIX, "crosswalk", "ingredient_crosswalk_v0.csv")

ROLE_TO_EDGE = {
    "substrate": "SUBSTRATE_OF",
    "inhibitor": "INHIBITS",
    "inducer": "INDUCES",
}


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_crosswalk():
    rows = {}
    with open(CROSSWALK, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["ingredient_en"].strip().lower()] = r
    return rows


def build():
    """Return dict with ingredients, enzymes, contra_edges, cyp_edges, report."""
    dcode = _load_json(DCODE_DICT)
    contra = _load_json(CONTRA)
    bidir = _load_json(BIDIR)
    crosswalk = load_crosswalk()

    by_eng = {v["eng"].strip().lower(): k for k, v in dcode.items()}

    # --- Ingredient nodes from the DUR D-code dictionary (the canonical set) ---
    ingredients = {}
    for code, v in dcode.items():
        ingredients[code] = {
            "code": code,
            "name_kor": v.get("kor"),
            "name_eng": v.get("eng"),
            "created": "dur-dict",
        }

    # --- Reconciliation: do crosswalk D-codes exist in the DUR dict? ----------
    reconciliation = []
    for en, r in crosswalk.items():
        code = r["dur_ingr_code"].strip()
        reconciliation.append({
            "ingredient_en": en,
            "crosswalk_code": code,
            "in_dcode_dict": code in dcode,
            "dict_eng": dcode.get(code, {}).get("eng"),
            "crosswalk_eng": r["dur_eng_name"],
        })

    enzymes = {"CYP3A4": {"name": "CYP3A4"}}

    # --- Resolve each CYP-edge drug name -> D-code ----------------------------
    def resolve(name):
        name = name.strip().lower()
        if name in crosswalk:
            return crosswalk[name]["dur_ingr_code"].strip(), "crosswalk"
        if name in by_eng:
            return by_eng[name], "dcode-dict-byname"
        # No mapping anywhere: synthesize a node so the edge is never dropped.
        return f"OFDA-{name}", "synthesized"

    cyp_edges = []
    created_nodes_log = []   # nodes created for CYP drugs not from dur-dict
    for name, rec in bidir["drugs"].items():
        code, how = resolve(name)
        cw = crosswalk.get(name.strip().lower())
        # Ensure an Ingredient node exists for this drug.
        if code not in ingredients:
            ingredients[code] = {
                "code": code,
                "name_kor": (cw["kr_name_hint"] if cw else None),
                "name_eng": name.capitalize(),
                "created": how,
            }
            created_nodes_log.append({"name": name, "code": code, "via": how})

        for e in rec.get("edges", []):
            etype = ROLE_TO_EDGE.get(e["role"])
            if etype is None:
                continue
            strength = e.get("strength")
            action = e.get("clinical_action")
            strength_source = "edge"
            action_source = "edge"
            # Backfill significance fields from the crosswalk ONLY when the edge
            # type matches the crosswalk's cyp3a4_role. The crosswalk strength/
            # action describe the drug's PERPETRATOR role (inhibitor/inducer);
            # applying them to a SUBSTRATE_OF edge would be wrong (and the
            # significance filter never reads substrate strength anyway).
            cw_role_edge = ROLE_TO_EDGE.get((cw or {}).get("cyp3a4_role", "").strip())
            if cw and cw_role_edge == etype:
                if strength is None and cw.get("strength"):
                    strength = cw["strength"].strip() or None
                    if strength:
                        strength_source = "crosswalk-backfill"
                if action is None and cw.get("clinical_action"):
                    action = cw["clinical_action"].strip() or None
                    if action:
                        action_source = "crosswalk-backfill"
            cyp_edges.append({
                "src_code": code,
                "enzyme": e["enzyme"],
                "type": etype,
                "source": "openFDA-label",
                "strength": strength,
                "strength_source": strength_source,
                "clinical_action": action,
                "clinical_action_source": action_source,
                "evidence_sentence": e.get("evidence_sentence"),
                "negated": bool(e.get("negated", False)),
                "confidence": e.get("confidence"),
                "recovered_from": e.get("recovered_from"),
                "drug_name": name,
            })

    # --- Contraindication edges (DUR) -----------------------------------------
    # The source has 1816 records but 438 are EXACT duplicate (a,b,reason)
    # triples; 49 drug pairs carry multiple genuinely-distinct clinical reasons.
    # We model one edge per distinct (a,b,reason) triple -> 1378 edges. This
    # keeps every distinct reason (MERGE-on-pair-only would drop 65 of them).
    seen = set()
    contra_edges = []
    for r in contra:
        reason = (r.get("prohibit") or "").strip()
        key = (r["a"], r["b"], reason)
        if key in seen:
            continue
        seen.add(key)
        contra_edges.append({
            "a": r["a"],
            "b": r["b"],
            "reason": reason,
            "source": "DUR",
        })

    return {
        "ingredients": ingredients,
        "enzymes": enzymes,
        "contra_edges": contra_edges,
        "cyp_edges": cyp_edges,
        "reconciliation": reconciliation,
        "created_nodes_log": created_nodes_log,
    }


def print_reconciliation(data=None):
    data = data or build()
    print("=== D-code reconciliation (crosswalk -> DUR dict) ===")
    mism = 0
    for r in data["reconciliation"]:
        ok = "OK " if r["in_dcode_dict"] else "MISS"
        if not r["in_dcode_dict"]:
            mism += 1
        print(f"  [{ok}] {r['ingredient_en']:15} {r['crosswalk_code']} "
              f"dict={r['dict_eng']} crosswalk={r['crosswalk_eng']}")
    print(f"  crosswalk rows: {len(data['reconciliation'])}, mismatches: {mism}")
    print("\n=== Ingredient nodes created for CYP drugs NOT in DUR dict ===")
    if not data["created_nodes_log"]:
        print("  (none)")
    for c in data["created_nodes_log"]:
        print(f"  {c['name']:15} -> {c['code']:20} via {c['via']}")
    print("\n=== Backfilled CYP edges (strength/action from crosswalk) ===")
    for e in data["cyp_edges"]:
        if "backfill" in e["strength_source"] or "backfill" in e["clinical_action_source"]:
            print(f"  {e['drug_name']:15} {e['type']:12} "
                  f"strength={e['strength']}({e['strength_source']}) "
                  f"action={e['clinical_action']}({e['clinical_action_source']})")


if __name__ == "__main__":
    d = build()
    print_reconciliation(d)
    print("\n=== Totals ===")
    print("  ingredients:", len(d["ingredients"]))
    print("  enzymes:", len(d["enzymes"]))
    print("  contra_edges:", len(d["contra_edges"]))
    print("  cyp_edges:", len(d["cyp_edges"]))

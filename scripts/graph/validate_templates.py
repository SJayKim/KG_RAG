"""Validate the two Cypher templates against the loaded graph using the gold set.

For each record in fixtures/gold/transitive_gold_v0.jsonl:
  - build $regimen (list of D-codes) by resolving each regimen entry's
    ingredient_en via the same crosswalk/dict logic the loader uses;
  - run Template 1 (INHIBITS+SUBSTRATE) and Template 2 (INDUCES+SUBSTRATE);
  - collect recovered (perpetrator, substrate) pairs;
  - compare against expected_flags[].path.

Prints per-gold found/missed and a headline recovered/total over all expected
paths. Also checks the hard-negative case (G4) produces zero flags.

Run:  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/validate_templates.py
"""
from __future__ import annotations

import json
import os
import re
import sys

from neo4j import GraphDatabase

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_data  # noqa: E402

ROOT = graph_data.ROOT
GOLD = os.path.join(ROOT, "fixtures", "gold", "transitive_gold_v0.jsonl")

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "testpassword")

TEMPLATE_1 = """
MATCH (a:Ingredient)-[i:INHIBITS]->(e:Enzyme)<-[s:SUBSTRATE_OF]-(c:Ingredient)
WHERE a.code IN $regimen AND c.code IN $regimen AND a <> c
  AND i.strength IN ['strong','moderate']
  AND i.clinical_action <> 'none' AND NOT i.negated
RETURN a.code AS perp_code, a.name_eng AS perp, e.name AS enzyme,
       c.code AS sub_code, c.name_eng AS substrate,
       i.strength AS strength, 'INHIBITS' AS mech
"""

TEMPLATE_2 = """
MATCH (a:Ingredient)-[d:INDUCES]->(e:Enzyme)<-[s:SUBSTRATE_OF]-(c:Ingredient)
WHERE a.code IN $regimen AND c.code IN $regimen AND a <> c
  AND d.strength IN ['strong','moderate'] AND NOT d.negated
RETURN a.code AS perp_code, a.name_eng AS perp, e.name AS enzyme,
       c.code AS sub_code, c.name_eng AS substrate,
       d.strength AS strength, 'INDUCES' AS mech
"""

# Parse "X -[INHIBITS strong]-> CYP3A4 <-[SUBSTRATE_OF]- Y"
PATH_RE = re.compile(
    r"^\s*(?P<perp>\S+)\s*-\[(?P<mech>INHIBITS|INDUCES)\s+\S+\]->\s*"
    r"(?P<enz>\S+)\s*<-\[SUBSTRATE_OF\]-\s*(?P<sub>\S+)\s*$"
)


def resolve_regimen(record, crosswalk, by_eng):
    """Map each regimen ingredient_en to a D-code (skip unresolved=null)."""
    codes = []
    for m in record["regimen"]:
        en = m.get("ingredient_en")
        if not en:
            continue
        en = en.strip().lower()
        if en in crosswalk:
            codes.append(crosswalk[en]["dur_ingr_code"].strip())
        elif en in by_eng:
            codes.append(by_eng[en])
        else:
            codes.append(f"OFDA-{en}")
    return codes


def main():
    data = graph_data.build()
    crosswalk = graph_data.load_crosswalk()
    dcode = graph_data._load_json(graph_data.DCODE_DICT)
    by_eng = {v["eng"].strip().lower(): k for k, v in dcode.items()}

    def name_to_code(en):
        en = (en or "").strip().lower()
        if en in crosswalk:
            return crosswalk[en]["dur_ingr_code"].strip()
        if en in by_eng:
            return by_eng[en]
        return f"OFDA-{en}"

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()

    total_expected = 0
    total_recovered = 0
    fp_flags = 0
    lines = []

    with driver.session() as s:
        with open(GOLD, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                regimen = resolve_regimen(rec, crosswalk, by_eng)

                # Compare on resolved D-CODES, not name strings: the graph stores
                # DUR/INN names (e.g. "Rifampicin") while the gold paths use the
                # US-label spelling (e.g. "rifampin"). Code identity is the join.
                recovered = set()      # (perp_code, mech, sub_code)
                recovered_disp = {}    # code-tuple -> readable "perp -> sub"
                for tmpl in (TEMPLATE_1, TEMPLATE_2):
                    for row in s.run(tmpl, regimen=regimen):
                        key = (row["perp_code"], row["mech"], row["sub_code"])
                        recovered.add(key)
                        recovered_disp[key] = f"{row['perp']} -> {row['substrate']}"

                expected = []
                for fl in rec.get("expected_flags", []):
                    mm = PATH_RE.match(fl["path"])
                    if not mm:
                        continue
                    expected.append((
                        name_to_code(mm.group("perp")), mm.group("mech"),
                        name_to_code(mm.group("sub")),
                        mm.group("perp"), mm.group("sub"),
                    ))

                lines.append(f"\n[{rec['id']}] {rec['stratum']} — regimen={regimen}")
                if not expected:
                    # hard-negative / abstention with no CYP flag expected
                    extra = len(recovered)
                    fp_flags += extra
                    status = "OK (silent)" if extra == 0 else f"FALSE POSITIVE x{extra}"
                    lines.append(f"    expected 0 flags -> recovered {extra}  [{status}]")
                    if extra:
                        for k in recovered:
                            lines.append(f"      spurious: {recovered_disp[k]}")
                    continue

                for perp_code, mech, sub_code, perp_nm, sub_nm in expected:
                    total_expected += 1
                    hit = (perp_code, mech, sub_code) in recovered
                    if hit:
                        total_recovered += 1
                    lines.append(
                        f"    {'FOUND ' if hit else 'MISSED'}: "
                        f"{perp_nm} -[{mech}]-> CYP3A4 <-[SUBSTRATE_OF]- {sub_nm} "
                        f"({perp_code}->{sub_code})"
                    )

    driver.close()

    print("=== Template validation vs transitive_gold_v0.jsonl ===")
    for ln in lines:
        print(ln)
    print("\n=== HEADLINE ===")
    print(f"  Gold interaction paths recovered: {total_recovered}/{total_expected}")
    print(f"  Hard-negative/abstention false positives: {fp_flags} (want 0)")
    ok = (total_recovered == total_expected and fp_flags == 0)
    print(f"  RESULT: {'PASS' if ok else 'CHECK'}")


if __name__ == "__main__":
    main()

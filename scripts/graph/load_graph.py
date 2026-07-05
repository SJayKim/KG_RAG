"""Idempotent Neo4j loader for PolyPharmGraph (Week 1).

MERGE-based: safe to re-run. Creates constraints, loads Ingredient + Enzyme
nodes, DUR CONTRAINDICATED_WITH edges, and openFDA CYP mechanism edges
(SUBSTRATE_OF / INHIBITS / INDUCES).

Env:
  NEO4J_URI       (default bolt://localhost:7687)
  NEO4J_USER      (default neo4j)
  NEO4J_PASSWORD  (default testpassword)

Run:  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/load_graph.py
"""
from __future__ import annotations

import os
import sys

from neo4j import GraphDatabase

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_data  # noqa: E402

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "testpassword")

CONSTRAINTS = [
    "CREATE CONSTRAINT ingredient_code IF NOT EXISTS "
    "FOR (i:Ingredient) REQUIRE i.code IS UNIQUE",
    "CREATE CONSTRAINT enzyme_name IF NOT EXISTS "
    "FOR (e:Enzyme) REQUIRE e.name IS UNIQUE",
]


def load(driver, data):
    with driver.session() as s:
        for c in CONSTRAINTS:
            s.run(c)

        # Ingredient nodes
        s.run(
            """
            UNWIND $rows AS r
            MERGE (i:Ingredient {code: r.code})
            SET i.name_kor = r.name_kor, i.name_eng = r.name_eng,
                i.created = r.created
            """,
            rows=list(data["ingredients"].values()),
        )

        # Enzyme nodes
        s.run(
            """
            UNWIND $rows AS r
            MERGE (e:Enzyme {name: r.name})
            """,
            rows=list(data["enzymes"].values()),
        )

        # CONTRAINDICATED_WITH edges (directed a -> b as in source)
        s.run(
            """
            UNWIND $rows AS r
            MATCH (a:Ingredient {code: r.a})
            MATCH (b:Ingredient {code: r.b})
            MERGE (a)-[c:CONTRAINDICATED_WITH {reason: r.reason}]->(b)
            SET c.source = r.source
            """,
            rows=data["contra_edges"],
        )

        # CYP mechanism edges — one MERGE per edge type (labels can't be params).
        for etype in ("SUBSTRATE_OF", "INHIBITS", "INDUCES"):
            rows = [e for e in data["cyp_edges"] if e["type"] == etype]
            if not rows:
                continue
            s.run(
                f"""
                UNWIND $rows AS r
                MATCH (a:Ingredient {{code: r.src_code}})
                MERGE (e:Enzyme {{name: r.enzyme}})
                MERGE (a)-[m:{etype}]->(e)
                SET m.source = r.source,
                    m.strength = r.strength,
                    m.strength_source = r.strength_source,
                    m.clinical_action = r.clinical_action,
                    m.clinical_action_source = r.clinical_action_source,
                    m.evidence_sentence = r.evidence_sentence,
                    m.negated = r.negated,
                    m.confidence = r.confidence,
                    m.recovered_from = r.recovered_from
                """,
                rows=rows,
            )


def summarize(driver):
    q = {
        "Ingredient nodes": "MATCH (i:Ingredient) RETURN count(i) AS n",
        "Enzyme nodes": "MATCH (e:Enzyme) RETURN count(e) AS n",
        "CONTRAINDICATED_WITH": "MATCH ()-[r:CONTRAINDICATED_WITH]->() RETURN count(r) AS n",
        "SUBSTRATE_OF": "MATCH ()-[r:SUBSTRATE_OF]->() RETURN count(r) AS n",
        "INHIBITS": "MATCH ()-[r:INHIBITS]->() RETURN count(r) AS n",
        "INDUCES": "MATCH ()-[r:INDUCES]->() RETURN count(r) AS n",
    }
    print("\n=== Load summary (from Neo4j) ===")
    with driver.session() as s:
        for label, cy in q.items():
            n = s.run(cy).single()["n"]
            print(f"  {label:22} {n}")


def main():
    data = graph_data.build()
    graph_data.print_reconciliation(data)
    print(f"\nConnecting to {URI} as {USER} ...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    load(driver, data)
    summarize(driver)
    driver.close()
    print("\nLoad complete.")


if __name__ == "__main__":
    main()

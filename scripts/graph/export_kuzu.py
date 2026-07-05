"""Export the PolyPharmGraph to an embedded Kuzu DB snapshot (Gate 6).

Builds node/rel tables mirroring the Neo4j schema and bulk-loads them from
CSVs generated from the SAME source data (scripts/graph/graph_data.py), so the
Kuzu snapshot is content-identical to the Neo4j load. After loading it reopens
the DB and runs a 2-hop query (Template 1 shape) to confirm it works.

Snapshot dir: fixtures/graph-snapshot/polypharmgraph.kuzu

Run:  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/export_kuzu.py
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile

import kuzu

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_data  # noqa: E402

ROOT = graph_data.ROOT
SNAP_DIR = os.path.join(ROOT, "fixtures", "graph-snapshot")
DB_PATH = os.path.join(SNAP_DIR, "polypharmgraph.kuzu")


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])


def build_csvs(data, csvdir):
    # Ingredient nodes
    _write_csv(
        os.path.join(csvdir, "ingredient.csv"),
        ["code", "name_kor", "name_eng"],
        [(i["code"], i["name_kor"], i["name_eng"])
         for i in data["ingredients"].values()],
    )
    # Enzyme nodes
    _write_csv(
        os.path.join(csvdir, "enzyme.csv"),
        ["name"],
        [(e["name"],) for e in data["enzymes"].values()],
    )
    # Contraindication edges
    _write_csv(
        os.path.join(csvdir, "contra.csv"),
        ["a", "b", "reason", "source"],
        [(e["a"], e["b"], e["reason"], e["source"]) for e in data["contra_edges"]],
    )
    # CYP mechanism edges — one CSV per type
    cyp_cols = ["src_code", "enzyme", "source", "strength", "strength_source",
                "clinical_action", "clinical_action_source", "evidence_sentence",
                "negated", "confidence", "recovered_from"]
    for etype in ("SUBSTRATE_OF", "INHIBITS", "INDUCES"):
        rows = [e for e in data["cyp_edges"] if e["type"] == etype]
        _write_csv(
            os.path.join(csvdir, f"{etype.lower()}.csv"),
            cyp_cols,
            [tuple(e[c] for c in cyp_cols) for e in rows],
        )


CYP_REL_SCHEMA = (
    "source STRING, strength STRING, strength_source STRING, "
    "clinical_action STRING, clinical_action_source STRING, "
    "evidence_sentence STRING, negated BOOLEAN, confidence DOUBLE, "
    "recovered_from STRING"
)


def create_schema(conn):
    conn.execute(
        "CREATE NODE TABLE Ingredient("
        "code STRING, name_kor STRING, name_eng STRING, PRIMARY KEY(code))"
    )
    conn.execute("CREATE NODE TABLE Enzyme(name STRING, PRIMARY KEY(name))")
    conn.execute(
        "CREATE REL TABLE CONTRAINDICATED_WITH("
        "FROM Ingredient TO Ingredient, reason STRING, source STRING)"
    )
    for etype in ("SUBSTRATE_OF", "INHIBITS", "INDUCES"):
        conn.execute(
            f"CREATE REL TABLE {etype}(FROM Ingredient TO Enzyme, {CYP_REL_SCHEMA})"
        )


def copy_data(conn, csvdir):
    def cp(path):
        return path.replace("\\", "/")
    conn.execute(f'COPY Ingredient FROM "{cp(os.path.join(csvdir, "ingredient.csv"))}" (HEADER=true, PARALLEL=false)')
    conn.execute(f'COPY Enzyme FROM "{cp(os.path.join(csvdir, "enzyme.csv"))}" (HEADER=true, PARALLEL=false)')
    conn.execute(f'COPY CONTRAINDICATED_WITH FROM "{cp(os.path.join(csvdir, "contra.csv"))}" (HEADER=true, PARALLEL=false)')
    for etype in ("SUBSTRATE_OF", "INHIBITS", "INDUCES"):
        conn.execute(
            f'COPY {etype} FROM "{cp(os.path.join(csvdir, etype.lower() + ".csv"))}" (HEADER=true, PARALLEL=false)'
        )


def counts(conn):
    out = {}
    for tbl, q in [
        ("Ingredient", "MATCH (i:Ingredient) RETURN count(i)"),
        ("Enzyme", "MATCH (e:Enzyme) RETURN count(e)"),
        ("CONTRAINDICATED_WITH", "MATCH ()-[r:CONTRAINDICATED_WITH]->() RETURN count(r)"),
        ("SUBSTRATE_OF", "MATCH ()-[r:SUBSTRATE_OF]->() RETURN count(r)"),
        ("INHIBITS", "MATCH ()-[r:INHIBITS]->() RETURN count(r)"),
        ("INDUCES", "MATCH ()-[r:INDUCES]->() RETURN count(r)"),
    ]:
        res = conn.execute(q)
        out[tbl] = res.get_next()[0]
    return out


def main():
    data = graph_data.build()

    # Kuzu may store the DB as a single file (0.11+) or a directory; also clean
    # any sidecar files (e.g. .wal) so the snapshot rebuild is reproducible.
    for p in (DB_PATH, DB_PATH + ".wal", DB_PATH + ".tmp"):
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
    os.makedirs(SNAP_DIR, exist_ok=True)

    csvdir = tempfile.mkdtemp(prefix="kuzu_csv_")
    try:
        build_csvs(data, csvdir)
        db = kuzu.Database(DB_PATH)
        conn = kuzu.Connection(db)
        create_schema(conn)
        copy_data(conn, csvdir)
        print("=== Kuzu snapshot load counts ===")
        for k, v in counts(conn).items():
            print(f"  {k:22} {v}")
        del conn
        del db
    finally:
        shutil.rmtree(csvdir, ignore_errors=True)

    # Reopen and run a 2-hop query (Template 1 shape) to confirm it works.
    print("\n=== Reopen + 2-hop verification ===")
    db2 = kuzu.Database(DB_PATH)
    conn2 = kuzu.Connection(db2)
    res = conn2.execute(
        """
        MATCH (a:Ingredient)-[i:INHIBITS]->(e:Enzyme)<-[s:SUBSTRATE_OF]-(c:Ingredient)
        WHERE a.code IN ['D000027','D000373'] AND c.code IN ['D000027','D000373']
          AND a.code <> c.code
          AND i.strength IN ['strong','moderate']
          AND i.clinical_action <> 'none' AND i.negated = false
        RETURN a.name_eng, e.name, c.name_eng, i.strength
        """
    )
    rows = []
    while res.has_next():
        rows.append(res.get_next())
    for r in rows:
        print(f"  {r[0]} -[INHIBITS {r[3]}]-> {r[1]} <-[SUBSTRATE_OF]- {r[2]}")
    assert rows, "2-hop query returned no rows — snapshot broken!"
    print(f"\nSnapshot OK: {DB_PATH}")


if __name__ == "__main__":
    main()

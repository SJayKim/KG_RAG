# Gate 5-6 — Graph Load + Kùzu Snapshot (Week 1)

Branch: `week1-graph`. First graph code in the repo. Loads the DUR + openFDA
fixtures into Neo4j, validates the transitive CYP templates against gold, and
exports a portable Kùzu snapshot.

## How to run (zero-key)

```bash
docker compose up -d                                   # Neo4j 5.26 community, bolt :7687
python -m pip install -r scripts/graph/requirements.txt
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/load_graph.py
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/validate_templates.py
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/graph/export_kuzu.py
```

Loader/validator honor `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`
(defaults `bolt://localhost:7687` / `neo4j` / `testpassword`). Loader is
idempotent (MERGE + uniqueness constraints on `Ingredient.code`, `Enzyme.name`);
re-running yields identical counts.

## What loaded (identical in Neo4j and Kùzu)

| Element | Count | Source |
|---|---:|---|
| Ingredient nodes | 473 | 472 DUR D-codes + 1 synthesized (nefazodone) |
| Enzyme nodes | 1 | CYP3A4 |
| CONTRAINDICATED_WITH | 1378 | DUR contraindication edges |
| SUBSTRATE_OF | 6 | openFDA labels |
| INHIBITS | 10 | openFDA labels (+crosswalk strength backfill) |
| INDUCES | 2 | openFDA labels |

### CONTRAINDICATED_WITH: 1816 source records → 1378 edges (not a loss)
The source file has 1816 rows but only **1378 distinct `(a, b, reason)` triples**:
438 rows are exact duplicates, and 49 drug pairs legitimately carry multiple
distinct clinical reasons (e.g. `D000455→D000769` has 근질환/근육병증/횡문근융해 as
three separate reasons). We model **one edge per distinct reason** (MERGE key
includes `reason`), so every distinct reason is preserved. A naive MERGE on the
pair alone would have collapsed to 1313 and silently dropped 65 reason variants.

## D-code reconciliation (the join problem)

CYP edges are keyed by lowercase English name; Ingredient nodes are keyed by DUR
D-code. Reconciliation result:

- **All 18 crosswalk rows' `dur_ingr_code` exist in the DUR dict — 0 mismatches.**
  The flagged lovastatin concern did not materialize: `D000419` is Lovastatin in
  the dict. `rifampin` maps to `D000314` = **Rifampicin** (DUR uses the INN
  spelling; a real cross-ontology gap, see below).
- 4 CYP drugs are not in the crosswalk. Three resolve by English name in the DUR
  dict: `fluconazole→D000517`, `phenobarbital→D000282`, `cyclosporine→D001077`.
  Only **nefazodone** has no D-code anywhere → 1 synthesized node
  `OFDA-nefazodone` (edge preserved, not dropped). `phenobarbital`/`cyclosporine`
  carry no CYP edges, so they attach to existing nodes with nothing new.

### Backfill (keeps the significance filter honest)
4 INHIBITS edges had `strength: null` on the label but a strength in the
crosswalk → backfilled with `strength_source="crosswalk-backfill"`:
`ritonavir` (strong), `diltiazem`/`verapamil`/`amiodarone` (moderate). Backfill
is applied **only when the edge type matches the crosswalk's `cyp3a4_role`** — a
crosswalk inhibitor-strength is never written onto a SUBSTRATE_OF edge. Where
neither edge nor crosswalk has a strength (`fluconazole`, `nefazodone`), it stays
null and the filter simply excludes it. The `amiodarone` moderate backfill is
load-bearing: without it gold case G2's second flag would be lost.

## Template validation vs `transitive_gold_v0.jsonl`

**Headline: 5/5 gold interaction paths recovered, 0 false positives.**

| Gold | Case | Result |
|---|---|---|
| G1 | lovastatin + itraconazole (strong inhibition) | FOUND |
| G2 | simvastatin + clarithromycin + amiodarone | FOUND (both flags) |
| G3 | rifampin + simvastatin (INDUCES → therapy failure) | FOUND |
| G4 | simvastatin + midazolam (substrate+substrate, hard-negative) | silent (correct) |
| G5 | simvastatin + itraconazole + unresolved herb | FOUND (1 flag) |

G4 is the precision test: both drugs are CYP3A4 substrates with no inhibit/induce
edge, so both templates correctly stay silent — no over-flagging.

**Comparison is on resolved D-codes, not name strings.** G3 exposed the cross-
ontology spelling gap: the graph stores `Rifampicin` (DUR/INN) but the gold path
says `rifampin` (US label). A string compare falsely missed it; matching on the
crosswalk-resolved D-code (`D000314`) recovers it correctly. This is exactly the
join the crosswalk exists to bridge.

## Kùzu snapshot (Gate 6)

`fixtures/graph-snapshot/polypharmgraph.kuzu` (~5.4 MB, single file). Built from
the **same** `graph_data.build()` source via generated CSVs; node/rel table
counts match the Neo4j load exactly (473 / 1 / 1378 / 6 / 10 / 2). Export
reopens the DB and runs a 2-hop Template-1 query
(`clarithromycin -[INHIBITS strong]-> CYP3A4 <-[SUBSTRATE_OF]- simvastatin`) which
returns the expected row — snapshot confirmed working. `export_kuzu.py` is
reproducible (wipes prior file/dir/WAL before rebuild). CSV COPY uses
`PARALLEL=false` because some Korean `reason` values contain embedded newlines.

## Honest gaps

- **Enzyme axis is CYP3A4-only** (22 openFDA drugs); 6 substrate / 10 inhibit /
  2 induce edges. Small but gold-complete for the transitive templates.
- **1 synthesized node** (`OFDA-nefazodone`) has no Korean name and no DUR D-code;
  it will not join to DUR contraindication edges until a real code is sourced.
- **`rifampin`/`Rifampicin` spelling** is bridged only by the crosswalk; any new
  name→code resolution must go through it, not string equality.
- Two CYP drugs (`fluconazole`, `nefazodone`) have inhibitor edges with **null
  strength** (no crosswalk row), so they are excluded by the significance filter —
  honest under-flagging rather than invented strength.

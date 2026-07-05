"""Gate 4 step 3: score extracted CYP3A4 edges against the hand-labeled gold.

Eval is scoped to the CYP3A4 axis (the mechanism validated in Gate 2). Matching
is on ROLE (substrate/inhibitor/inducer) per drug; strength and clinical_action
are reported as secondary field accuracy over correctly-role-matched edges.

Definitions (per drug, CYP3A4, non-negated extracted edges only):
  TP  = extracted edge whose role matches a gold edge (greedy, one-to-one)
  FP  = extracted CYP3A4 edge that matches no gold edge
  FN  = REQUIRED gold edge with no matching extracted edge
  precision = TP / (TP + FP)
  recall    = matched_required / total_required
Negative drugs (gold_edges == []) contribute only potential FP (a hallucinated
CYP3A4 edge), which is exactly the precision test we want.

Run:
  PYTHONUTF8=1 python scripts/extract/score_extraction.py \
      fixtures/gold/extraction_gold_v0.jsonl \
      fixtures/openfda-labels/extracted_regex.json \
      docs/GATE4-EXTRACTION.md
"""
import json
import sys


def load_gold(path):
    gold = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            g = json.loads(line)
            gold[g["drug"]] = g
    return gold


def norm_enzyme(e):
    return str(e or "").upper().replace(" ", "")


def cyp3a4_edges(edges):
    return [e for e in edges if norm_enzyme(e.get("enzyme")) == "CYP3A4"
            and not e.get("negated", False)]


def score(gold, extracted):
    drugs = extracted["drugs"]
    per_drug = []
    TP = FP = FN = 0
    req_total = req_matched = 0
    strength_ok = strength_total = 0
    action_ok = action_total = 0

    for drug, g in gold.items():
        gold_edges = g["gold_edges"]
        req = [e for e in gold_edges if e.get("required")]
        req_total += len(req)

        ext = cyp3a4_edges(drugs.get(drug, {}).get("edges", []))

        # greedy role matching
        used = [False] * len(ext)
        matched_gold = []
        d_tp = d_fn = 0
        for ge in gold_edges:
            hit = None
            for i, xe in enumerate(ext):
                if used[i]:
                    continue
                if xe.get("role") == ge.get("role"):
                    hit = i
                    break
            if hit is not None:
                used[hit] = True
                matched_gold.append((ge, ext[hit]))
                d_tp += 1
                if ge.get("required"):
                    req_matched += 1
                # secondary field accuracy (inhibitor/inducer only)
                if ge.get("role") in ("inhibitor", "inducer"):
                    strength_total += 1
                    if (ext[hit].get("strength") or None) == (ge.get("strength") or None):
                        strength_ok += 1
                    action_total += 1
                    if (ext[hit].get("clinical_action") or None) == (ge.get("clinical_action") or None):
                        action_ok += 1
            elif ge.get("required"):
                d_fn += 1
        d_fp = sum(1 for u in used if not u)  # extracted edges matched to nothing

        TP += d_tp
        FP += d_fp
        FN += d_fn

        status = "ok"
        if not gold_edges and d_fp:
            status = f"FALSE POSITIVE x{d_fp}"
        elif d_fn and d_fp:
            status = f"MISS+WRONG (fn{d_fn}/fp{d_fp})"
        elif d_fn:
            status = f"MISS (fn{d_fn})"
        elif d_fp:
            status = f"EXTRA (fp{d_fp})"
        per_drug.append({
            "drug": drug,
            "gold_roles": [e["role"] for e in gold_edges] or ["(none)"],
            "ext_roles": [e["role"] for e in ext] or ["(none)"],
            "tp": d_tp, "fp": d_fp, "fn": d_fn, "status": status,
        })

    precision = TP / (TP + FP) if (TP + FP) else 0.0
    recall = req_matched / req_total if req_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "TP": TP, "FP": FP, "FN": FN,
        "precision": precision, "recall": recall, "f1": f1,
        "req_total": req_total, "req_matched": req_matched,
        "strength_acc": (strength_ok / strength_total) if strength_total else None,
        "strength_ok": strength_ok, "strength_total": strength_total,
        "action_acc": (action_ok / action_total) if action_total else None,
        "action_ok": action_ok, "action_total": action_total,
        "per_drug": per_drug,
    }


def render_md(gold_path, ext_path, res, extractor, model):
    lines = []
    lines.append("# Gate 4 — openFDA CYP3A4 Extraction Mini-Eval\n")
    lines.append("> Precision/recall of typed CYP3A4 edge extraction from openFDA labels.")
    lines.append("> Eval scoped to the CYP3A4 axis (validated in Gate 2). Matching on role;")
    lines.append("> strength/clinical_action reported as secondary field accuracy.\n")
    lines.append(f"- **Extractor:** `{extractor}`" + (f" (model `{model}`)" if model else ""))
    lines.append(f"- **Gold:** `{gold_path}` — {res['req_total']} required edges across "
                 f"{len(res['per_drug'])} drugs (2 negatives)")
    lines.append(f"- **Extracted:** `{ext_path}`\n")
    lines.append("## Headline\n")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| **Precision** | **{res['precision']:.2f}** ({res['TP']}/{res['TP']+res['FP']}) |")
    lines.append(f"| **Recall** | **{res['recall']:.2f}** ({res['req_matched']}/{res['req_total']} required edges) |")
    lines.append(f"| **F1** | **{res['f1']:.2f}** |")
    lines.append(f"| TP / FP / FN | {res['TP']} / {res['FP']} / {res['FN']} |")
    if res["strength_acc"] is not None:
        lines.append(f"| strength accuracy (matched) | {res['strength_acc']:.2f} ({res['strength_ok']}/{res['strength_total']}) |")
    if res["action_acc"] is not None:
        lines.append(f"| clinical_action accuracy (matched) | {res['action_acc']:.2f} ({res['action_ok']}/{res['action_total']}) |")
    lines.append("")
    lines.append("## Per-drug\n")
    lines.append("| drug | gold | extracted | TP | FP | FN | status |")
    lines.append("|---|---|---|---|---|---|---|")
    for d in res["per_drug"]:
        lines.append(f"| {d['drug']} | {','.join(d['gold_roles'])} | {','.join(d['ext_roles'])} "
                     f"| {d['tp']} | {d['fp']} | {d['fn']} | {d['status']} |")
    lines.append("")
    # error analysis
    misses = [d for d in res["per_drug"] if d["fn"]]
    fps = [d for d in res["per_drug"] if d["fp"]]
    lines.append("## Error analysis\n")
    if misses:
        lines.append("**Misses (recall gap):** " + ", ".join(
            f"{d['drug']} (missed {','.join(d['gold_roles'])})" for d in misses) + "\n")
    if fps:
        lines.append("**False positives (precision gap):** " + ", ".join(
            f"{d['drug']} (extracted {','.join(d['ext_roles'])})" for d in fps) + "\n")
    if not misses and not fps:
        lines.append("Clean — no misses or false positives on this run.\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: score_extraction.py <gold.jsonl> <extracted.json> [report.md]")
    gold_path, ext_path = sys.argv[1], sys.argv[2]
    report_path = sys.argv[3] if len(sys.argv) > 3 else None

    gold = load_gold(gold_path)
    with open(ext_path, encoding="utf-8") as f:
        extracted = json.load(f)
    res = score(gold, extracted)

    print(f"\n=== {extracted.get('extractor')} extractor ===")
    print(f"Precision {res['precision']:.2f}  Recall {res['recall']:.2f}  F1 {res['f1']:.2f}"
          f"  (TP {res['TP']} / FP {res['FP']} / FN {res['FN']})")
    if res["strength_acc"] is not None:
        print(f"strength acc {res['strength_acc']:.2f}  action acc {res['action_acc']:.2f}")
    print()
    for d in res["per_drug"]:
        flag = "" if d["status"] == "ok" else f"  <- {d['status']}"
        print(f"  {d['drug']:16s} gold={','.join(d['gold_roles']):22s} ext={','.join(d['ext_roles'])}{flag}")

    if report_path:
        md = render_md(gold_path, ext_path, res,
                       extracted.get("extractor"), extracted.get("model"))
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\nreport -> {report_path}")


if __name__ == "__main__":
    main()

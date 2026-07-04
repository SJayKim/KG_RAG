"""Gate 1 (full): fetch the ENTIRE DUR 병용금기 성분쌍 list (15056780) and build
- dur_contraindication_edges_full.json : all Ingredient<->Ingredient edges
- dur_ingredient_dcode_dict.json       : DUR D-code -> {kor, eng} dictionary

Endpoint: DURIrdntInfoService03/getUsjntTabooInfoList02 (service03 / list02 — the
version suffixes intentionally differ; see docs/DAY1-3-GATE.md Gate 1).
numOfRows cap = 500 -> paginate. Success = header.resultCode == "00".

usage: python fetch_dur_all_edges.py [outdir]
key: env DATA_GO_KR_KEY (repo .env)
"""
import json
import os
import sys
import requests
import urllib3
urllib3.disable_warnings()

KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
URL = "https://apis.data.go.kr/1471000/DURIrdntInfoService03/getUsjntTabooInfoList02"
PAGE_SIZE = 500  # gateway hard cap


def fetch_page(page):
    r = requests.get(URL, params={"serviceKey": KEY, "type": "json",
                                  "numOfRows": PAGE_SIZE, "pageNo": page},
                     timeout=60, verify=False, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    js = r.json()
    code = js.get("header", {}).get("resultCode")
    if code not in (None, "00"):
        raise RuntimeError(f"API resultCode={code}: {js.get('header',{}).get('resultMsg')}")
    body = js.get("body", {})
    items = body.get("items")
    if isinstance(items, dict):
        items = items.get("item", [])
    if items and isinstance(items[0], dict) and set(items[0].keys()) == {"item"}:
        items = [x["item"] for x in items]
    return items or [], int(body.get("totalCount", 0))


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "fixtures/dur-samples"
    if not KEY:
        print("ERROR: DATA_GO_KR_KEY not set (source repo .env)"); sys.exit(2)
    os.makedirs(outdir, exist_ok=True)
    rows, total = [], None
    page = 1
    while True:
        items, total = fetch_page(page)
        if not items:
            break
        rows += items
        print(f"page {page}: +{len(items)} (total {len(rows)}/{total})")
        if total and len(rows) >= total:
            break
        page += 1
        if page > 50:  # safety
            break

    edges, dcode = [], {}
    for r in rows:
        a, b = r.get("INGR_CODE"), r.get("MIXTURE_INGR_CODE")
        if a:
            dcode[a] = {"kor": r.get("INGR_KOR_NAME"), "eng": r.get("INGR_ENG_NAME")}
        if b:
            dcode[b] = {"kor": r.get("MIXTURE_INGR_KOR_NAME"), "eng": r.get("MIXTURE_INGR_ENG_NAME")}
        edges.append({
            "a": a, "b": b,
            "a_kor": r.get("INGR_KOR_NAME"), "b_kor": r.get("MIXTURE_INGR_KOR_NAME"),
            "a_eng": r.get("INGR_ENG_NAME"), "b_eng": r.get("MIXTURE_INGR_ENG_NAME"),
            "prohibit": r.get("PROHBT_CONTENT") or r.get("REMARK"),
        })

    ep = os.path.join(outdir, "dur_contraindication_edges_full.json")
    dp = os.path.join(outdir, "dur_ingredient_dcode_dict.json")
    json.dump(edges, open(ep, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dcode, open(dp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    uniq = len(set((e["a"], e["b"]) for e in edges))
    print(f"\nedges={len(edges)} unique_pairs={uniq} dcodes={len(dcode)}")
    print(f"saved -> {ep}\nsaved -> {dp}")


if __name__ == "__main__":
    main()

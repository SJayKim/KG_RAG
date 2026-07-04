"""Gate 1: DUR 병용금기(concomitant contraindication) 실측 + 성분쌍 깨끗함 비교.

두 데이터셋을 같은 operation(병용금기)으로 호출해 성분↔성분 쌍이 깨끗하게
나오는 ID를 채택한다.

  성분(15056780): DURIrdntInfoService03/getUsjntTabooInfoList02
  품목(15059486): DURPrdlstInfoService03/getUsjntTabooInfoList03

키는 환경변수 DATA_GO_KR_KEY (repo .env). 승인 직후 게이트웨이 전파 지연으로
403 Forbidden이 날 수 있음(무효키는 401) -> 잠시 후 재시도.

usage: python fetch_dur_contraindications.py [numOfRows] [outdir]
"""
import json
import os
import sys
import requests
import urllib3
urllib3.disable_warnings()

KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()

ENDPOINTS = {
    "ingredient_15056780": "https://apis.data.go.kr/1471000/DURIrdntInfoService03/getUsjntTabooInfoList02",
    "item_15059486": "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03",
}


def call(url, rows):
    params = {"serviceKey": KEY, "type": "json", "numOfRows": rows, "pageNo": 1}
    r = requests.get(url, params=params, timeout=25, verify=False,
                     headers={"User-Agent": "Mozilla/5.0"})
    return r


def diagnose(r):
    if r.status_code == 401:
        return "INVALID_KEY (401) — 키 값 오류"
    if r.status_code == 403:
        return "FORBIDDEN (403) — 키 인식되나 게이트웨이 권한 미전파(승인 대기/지연). 잠시 후 재시도."
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:120]}"
    return None


def extract_rows(js):
    try:
        return js["body"]["items"]
    except (KeyError, TypeError):
        try:
            return js["response"]["body"]["items"]
        except (KeyError, TypeError):
            return None


def main():
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    if not KEY:
        print("ERROR: DATA_GO_KR_KEY not set (source repo .env)")
        sys.exit(2)
    all_ok = True
    for label, url in ENDPOINTS.items():
        print(f"\n{'='*72}\n{label}\n{url}\n{'='*72}")
        r = call(url, rows)
        prob = diagnose(r)
        if prob:
            print("  ->", prob)
            all_ok = False
            continue
        try:
            js = r.json()
        except Exception:
            print("  -> non-JSON:", r.text[:200]); all_ok = False; continue
        items = extract_rows(js)
        path = os.path.join(outdir, f"dur_{label}_usjnt10.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False, indent=2)
        n = len(items) if isinstance(items, list) else "?"
        print(f"  -> OK, {n} rows saved to {path}")
        # show ingredient-pair cleanliness: are there DUR성분코드 fields?
        if isinstance(items, list) and items:
            keys = sorted(items[0].keys())
            print("  columns:", keys)
            # heuristics for ingredient-level pair fields
            ing_keys = [k for k in keys if "INGR" in k.upper() or "성분" in k
                        or k.upper().endswith("CODE")]
            print("  ingredient/code-ish columns:", ing_keys)
            print("  sample row:")
            print("   ", json.dumps(items[0], ensure_ascii=False)[:400])
    print("\n" + ("ALL OK — compare columns above to pick clean ingredient-pair ID"
                  if all_ok else "NOT READY — see diagnostics (likely gateway propagation delay)"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

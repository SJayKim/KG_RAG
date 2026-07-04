# DUR 데이터 출처 (KOGL Type1 — 출처표시 의무)

- **출처:** 식품의약품안전처 「의약품안전사용서비스(DUR) 성분정보」 OpenAPI (data.go.kr 데이터셋 `15056780`)
- **엔드포인트:** `apis.data.go.kr/1471000/DURIrdntInfoService03/getUsjntTabooInfoList02` (병용금기)
- **라이선스:** 공공누리 제1유형(KOGL Type1) — 출처표시 조건 하에 상업적 이용·변형·2차저작 허용 → 재배포 가능
- **스냅샷 일자:** 2026-07-04
- **파일:**
  - `dur_contraindication_edges_full.json` — 병용금기 성분쌍 전체 1,816행(고유쌍 1,313)
  - `dur_ingredient_dcode_dict.json` — DUR 성분 D-code → {한글명, 영문명} 472종
  - `dur_ingredient_15056780_usjnt10.json` / `dur_item_15059486_usjnt10.json` — Gate1 성분 vs 품목 비교 샘플(각 10행)
- **갱신:** `export $(grep DATA_GO_KR_KEY ../../.env | xargs) && python ../../scripts/gate/fetch_dur_all_edges.py .`

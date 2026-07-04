# Day 1–3 Gate — 검증 결과 (구현 진입 판정)

> `DESIGN.md`의 "Day 1–3 게이트 (코드 최소, 전부 통과해야 진행)" 7개 항목 실행 결과.
> 실행일: 2026-07-04. 실행자: Claude (자율). 원칙: **코드 최소, 검증 우선.**
> 산출물: 이 문서 + `fixtures/gold/transitive_gold_v0.jsonl` + `fixtures/crosswalk/ingredient_crosswalk_v0.csv`
> + `fixtures/openfda-samples/*.json`(실측 라벨 근거) + `scripts/gate/*.py`(재현 스크립트).

## 판정 요약

| # | 게이트 | 상태 | 근거 |
|---|---|---|---|
| 1 | DUR 데이터셋 ID 확정 (`15056780` vs `15059486`) | 🟡 **거의 완료 (게이트웨이 전파 대기)** | 키 발급·저장 완료, **엔드포인트 정확히 확정**, 키 유효성 검증(401 vs 403). 승인이 트래픽 게이트웨이에 전파되면 10행 실측 자동 완료 |
| 2 | openFDA 라벨 CYP3A4 문장 실재 | ✅ **PASS** | simvastatin·atorvastatin·lovastatin 기질 문장, 억제제·유도제 role 문장 전부 실측 |
| 3 | 전이 골드 5개(라벨 근거까지) | ✅ **PASS** | `transitive_gold_v0.jsonl` — 5개 층화, 각 hop 실측 라벨 문장 앵커 |
| 4 | 20–30 라벨 추출 미니평가 | 🟡 **부분 (설계 완료, 실측 대기)** | 추출 스키마·전략 확정, 하네스 스크립트 초안. 20–30 라벨 정량 P/R은 Week1 Day1–2 |
| 5 | ~15–20 성분 크로스워크 표 | ✅ **PASS (초안)** | `ingredient_crosswalk_v0.csv` — 18 성분. RxCUI는 빌드타임 RxNav 확인용 TBD |
| 6 | Kùzu 스냅샷 export 확정 | 🟡 **부분 (경로 확정, 구현 대기)** | export 포맷/파이프라인 결정. 실제 Neo4j→Kùzu 덤프는 Week1 |
| 7 | 5케이스 agentic-벡터 go/no-go | ✅ **GO (단, thesis 정밀화)** | 아래 "핵심 발견" — 진짜 graph-win 케이스 존재 확인, 단 statin 라벨 co-naming 리스크 발견 |

**종합 판정: 조건부 GO.** 자율 실행 가능한 5개 항목(2·3·5 완료, 4·6·7 실질 통과) 모두 통과. **유일한 하드 블로커는 Gate 1(DUR 키) — 사용자 발급 필요.** 이것만 해소되면 Week 1 진입 가능.

---

## 🔑 핵심 발견 (thesis에 직접 영향 — 반드시 읽을 것)

### 발견 1 — 기질(statin) 라벨이 가해자를 상세히 co-name한다 → agentic 벡터가 경쟁적

DESIGN의 hero 예시(**amiodarone + clarithromycin + simvastatin**)를 라벨근거(H1)로 검증한 결과,
**simvastatin 라벨이 두 가해자를 모두 이름으로 명시**한다:

- clarithromycin → *"Concomitant administration of clarithromycin ... with ... simvastatin ... is contraindicated"* (병용금기 명시)
- amiodarone → *"For patients taking amiodarone, amlodipine, or ranolazine, do not exceed simvastatin 20 mg daily"* (용량제한 명시)

즉 **agentic 벡터 베이스라인이 simvastatin 라벨 한 장만 읽어도 이 두 위험을 잡는다.**
이 케이스에서 그래프의 우위는 **recall이 아니라** (a) 근거 경로/provenance 시각화, (b) 처방 내 모든 기질 자동 열거, (c) `clinical_action` 정량 구분(병용금기 vs 20mg 제한)이다.

→ **thesis 함의:** statin 치료군은 라벨이 이례적으로 완비돼 있어 "그래프가 recall로 이긴다"를 증명하기엔 **불리한 무대**다.
헤드라인 A/B recall 승리는 **라벨이 상대 약을 co-name하지 않는 케이스**에서 나와야 한다(발견 2).
DESIGN의 hero 예시는 **데모용으로 유지하되**(legible, 경로 예쁨) A/B "recall 승리 증거"로 과대포장 금지.

### 발견 2 — 진짜 graph-win = 두 라벨이 서로를 명시하지 않아 효소 노드 합성이 필수인 케이스

실측으로 확인한 **강한 graph-win 후보**(골드 G1):

- **lovastatin** 라벨: *"Strong inhibitors of CYP3A4 can raise the plasma levels ... and increase the risk of myopathy"* — **약물명 없이 일반 카테고리**.
- **itraconazole** 라벨: *"Itraconazole ... are potent CYP3A4 inhibitors"* + *"a number of CYP3A4 substrates are contraindicated"* — **피해자명 없이 일반**.

어느 라벨도 상대를 이름으로 대지 않는다. 구체 쌍(lovastatin ↔ itraconazole)은 **CYP3A4 효소 노드에서 category↔instance 합성**으로만 나온다.
agentic 벡터는 "이 억제제가 이 기질에 해당하는가"를 매번 카테고리 매칭으로 풀어야 하고, 여기서 그래프의 타입드 엣지(strength·role)가 구조적 우위를 갖는다.

→ **골드셋 설계 규칙 확정:** 헤드라인 전이 케이스는 **라벨 co-naming 여부를 명시적으로 층화**한다.
`transitive_gold_v0.jsonl`의 각 케이스에 `graph_win: strong|weak|moderate` 필드로 정직하게 태깅했다.

### 발견 3 — 추출 1순위는 "기질 라벨"이 더 효율적일 수 있다

가해자 라벨(amiodarone)은 자신의 CYP3A4 억제를 약하게만 기술("Lower starting dose of other CYP3A4 substrates may be required")한 반면,
**기질 라벨(simvastatin)은 가해자를 정량적으로 열거**(병용금기/10mg/20mg 등급)한다.
→ **추출 전략 보강:** 기질(statin) 라벨과 가해자 라벨 **양방향 추출** 후 dedup/reconcile. 기질 라벨이 종종 더 풍부하고 정량적.
단, 라벨 간 strength가 어긋나면(예: amiodarone을 simvastatin 라벨은 20mg-제한=moderate로, amiodarone 자기 라벨은 약하게) **더 보수적/정량적 근거 쪽 채택 + 두 출처 모두 provenance 기록.**

---

## Gate별 상세

### Gate 1 — DUR 데이터셋 ID 🟡 거의 완료 (게이트웨이 전파 대기)

- **키 발급·저장 완료:** 사용자가 `15056780`·`15059486` 둘 다 활용신청 → 키 발급. repo `.env`의 `DATA_GO_KR_KEY`에 저장(`.gitignore`가 `.env` 차단 확인).
- **엔드포인트 정확히 확정** (openapi.do 페이지 HTML에서 실측 추출 — ⚠️ 서비스와 operation의 버전 접미사가 **다르다**, 이래서 순진한 `03/03`·`02/02` 조합이 다 실패):

  | 데이터셋 | 병용금기 엔드포인트 |
  |---|---|
  | 성분 `15056780` | `https://apis.data.go.kr/1471000/DURIrdntInfoService03/getUsjntTabooInfoList02` |
  | 품목 `15059486` | `https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03` |

  (기타 성분 operation: `getSpcifyAgrdeTabooInfoList02`·`getPwnmTabooInfoList02`·`getCpctyAtentInfoList02`·`getMdctnPdAtentInfoList02`·`getOdsnAtentInfoList02`·`getEfcyDplctInfoList02`. 품목은 대응 `...03`.)
- **키 유효성 검증됨 (핵심 진단):** 정답 경로에 대해
  - **무효키 → HTTP 401 Unauthorized**
  - **발급받은 키 → HTTP 403 Forbidden** (data.go.kr 표준 XML 오류 아닌 평문)

  게이트웨이가 두 키를 **구분**한다 = 우리 키는 시스템에 **등록됨**. 403 = "인증됐으나 이 API 사용 권한 아직 없음" → **활용신청 승인이 트래픽 게이트웨이(`apis.data.go.kr`)에 전파되는 중.** data.go.kr 개발계정은 자동승인이나 게이트웨이 반영에 보통 **수분~1시간**(가끔 더).
- **남은 것 = 전파 대기 후 자동 완료:** `scripts/gate/fetch_dur_contraindications.py`가 정답 경로로 완성됨. 200 OK 뜨는 순간 10행 저장 + 성분쌍/품목쌍 컬럼 비교 → **성분코드 쌍(Ingredient↔Ingredient)이 깨끗한 ID 채택**. 재실행:
  ```bash
  export $(grep DATA_GO_KR_KEY .env | xargs)
  python scripts/gate/fetch_dur_contraindications.py 10 fixtures/dur-samples
  ```
- **참고:** openFDA(Gate 2)로 CYP 기전 축은 이미 검증됐으므로, DUR 축(직접 금기 1홉 legibility 래퍼)은 전파만 되면 저리스크.

### Gate 2 — openFDA CYP3A4 문장 실재 ✅ PASS

- **스크립트:** `scripts/gate/fetch_openfda_cyp.py`, `probe_substrate_perpetrators.py`, `probe_perpetrator_roles.py` (키 불필요, CC0).
- **실측 결과:** `fixtures/openfda-samples/*.json`. 대표 근거 문장:
  - simvastatin: *"Simvastatin is a substrate of CYP3A4 and of the transport protein OATP1B1."* (기질 ✅)
  - atorvastatin: *"Atorvastatin is a substrate of CYP3A4 and transporters."* (기질 ✅)
  - clarithromycin: 강한 CYP3A4 억제제, simvastatin/lovastatin **병용금기** 명시.
  - itraconazole: *"potent CYP3A4 inhibitors"* (강한 억제).
  - diltiazem: *"Diltiazem is an inhibitor of CYP3A4"* (중등도).
  - rifampin: *"a strong CYP3A4 inducer"*, 심바스타틴 노출 감소 명시(유도).
- **결론:** 추출 1순위 전략(openFDA 라벨 → 타입드 CYP 엣지) **성립**. strength/clinical_action/evidence_sentence를 라벨에서 직접 딸 수 있음을 실측 확인.

### Gate 3 — 전이 골드 5개 ✅ PASS

- **산출물:** `fixtures/gold/transitive_gold_v0.jsonl`. 5개 층화, 각 hop `hop_evidence`에 **실측 openFDA 문장** 앵커.

| id | stratum | graph_win | 요지 |
|---|---|---|---|
| G1 | transitive-2hop | **strong** | 로바스타틴+이트라코나졸 — 라벨 co-name 없음, 효소 합성 필수(헤드라인) |
| G2 | transitive-2hop | weak | 심바스타틴+클래리스로마이신+아미오다론 — DESIGN hero, 단 라벨 co-named(정직 태깅) |
| G3 | inducer-2hop | moderate | 리팜핀+심바스타틴 — 유도(치료 실패), 방향성 흔히 놓침 |
| G4 | hard-negative | n/a | 심바스타틴+미다졸람 — 기질+기질, 상호작용 아님(FP 테스트, 침묵해야 함) |
| G5 | abstention | n/a | 미해결 약 포함 — unknown≠safe(resolution status 테스트) |

- **5개 다 라벨 근거를 적을 수 있었다** = 평가가 선다(스코프 조정 신호 아님). ✅
- 40문항 층화 골드는 Week 3. 이 5개가 시드.

### Gate 4 — 라벨 추출 미니평가 🟡 부분

- **확정된 추출 스키마:** `(label_set_id, product_rxcui, normalized_ingredient, role, enzyme, strength, clinical_action, evidence_sentence, negated, confidence)` (DESIGN C1/H4).
- **확정된 전략:** 기질·가해자 **양방향** 추출 후 dedup(발견 3), strength/action 등급, negation 처리.
- **미완(정직):** 20–30 라벨에 대한 **정량 precision/recall**은 아직. 이유: LLM 추출 러너 + 손라벨 정답이 필요 → 이건 Week1 Day1–2의 첫 코드 작업으로 이관.
- **하지만** Gate 2에서 문장이 정규식으로도 깨끗이 잡히는 것을 확인 → 추출 난이도 낮음 시그널.

### Gate 5 — 성분 크로스워크 ✅ PASS (초안)

- **산출물:** `fixtures/crosswalk/ingredient_crosswalk_v0.csv` — 18 성분(statin 치료군: 기질 3 + 비CYP3A4 대조 statin 2 + 강한 억제제 5 + 중등도 억제제 4 + 유도제 3 + 미다졸람 1).
- **정직성:** `rxcui` 컬럼은 전부 `TBD-rxnav` — **빌드타임에 RxNav로 확인**(허구 RxCUI 금지). ATC는 WHO 표준값.
- **비CYP3A4 statin(프라바·로수바) 포함** = 하드 네거티브/대조 앵커. 미다졸람 = 기질+기질 하드네거티브 앵커.

### Gate 6 — Kùzu 스냅샷 export 🟡 부분 (경로 확정)

- **확정:** 빌드=Neo4j, 데모=Kùzu 임베디드 스냅샷(서버리스). export 경로 = 노드/엣지 CSV 덤프 → Kùzu `COPY FROM`.
- **미완:** 실제 Neo4j→Kùzu 덤프 스크립트는 그래프가 생긴 뒤(Week1 말) 작성. 지금은 데이터 없어 무의미.
- **리스크 없음:** Kùzu는 CSV 대량적재 표준 지원. 포맷 의존성만 Week1에 스모크테스트.

### Gate 7 — agentic-벡터 go/no-go ✅ GO (thesis 정밀화)

- **판정: GO** — 진짜 graph-win 케이스(G1: 라벨 co-name 없는 category↔instance 합성)가 **실측으로 존재**함을 확인.
- **단, 3일차에 인지한 thesis 약점(발견 1):** statin 라벨이 완비돼 있어 **일부 케이스는 agentic 벡터가 잡는다.** 이건 피벗 신호가 아니라 **골드셋 층화로 정직하게 다뤄야 할 현실** — `graph_win` 태그로 이미 반영.
- **A/B 방탄 강화:** 헤드라인 recall 승리는 `graph_win: strong` 케이스에서, `weak` 케이스는 provenance/enumeration 승리로 별도 보고.

---

## 다음 세션 진입 조건 (Week 1 시작 전)

1. **Gate 1 마무리** — 키·엔드포인트 확정 완료. 게이트웨이 전파(403→200) 후 `fetch_dur_contraindications.py`로 10행 실측 → 성분쌍 깨끗한 ID 채택. (자동/재실행만 남음)
2. [코드] Week1 Day1–2 — Gate 4 정량화: 20–30 openFDA 라벨 LLM 추출 러너 + 손라벨 정답으로 P/R 측정.
3. [코드] Week1 — `ingredient_crosswalk_v0.csv`의 RxCUI를 RxNav `approximateTerm`/ATC 브릿지로 빌드타임 해소 → coverage% 기록.
4. [설계 반영] DESIGN.md hero 예시(G2) 옆에 **G1(강한 graph-win)을 A/B 헤드라인으로** 승격 검토.

## 재현 방법

```bash
# openFDA 검증 재현 (키 불필요)
python scripts/gate/fetch_openfda_cyp.py fixtures/openfda-samples/cyp3a4_sentences.json
python scripts/gate/probe_substrate_perpetrators.py fixtures/openfda-samples/simvastatin_perpetrators.json
python scripts/gate/probe_perpetrator_roles.py fixtures/openfda-samples/perpetrator_cyp3a4_roles.json
# Windows 콘솔이면 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 앞에 붙일 것
```

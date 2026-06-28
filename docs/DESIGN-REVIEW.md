# DESIGN REVIEW — PolyPharmGraph (autoplan, 2026-06-28)

`DESIGN.md`에 대한 4단계(CEO·Design·Eng·DX) 적대적 리뷰. 각 단계 **이중 voice**
(독립 Claude 서브에이전트 + Codex), 6원칙 자동결정. 분석 대상: 코드 0줄, 설계 문서.

> **핵심 한 줄:** 설계의 *백엔드·평가·라이선스* 부분은 시니어급으로 강하다. 위험은 개념이 아니라
> **(1) thesis가 공정한 베이스라인에서 살아남는가, (2) 스코프가 시간예산의 ~2배이고 페이로드(평가+데모)에 뒤로 몰려있다,
> (3) 채용담당자가 실제로 보는 표면(README·라이브 데모·UI)이 가장 덜 설계됐다** 이 셋이다.
> 8개 voice 중 두 모델이 **독립적으로 같은 결론**에 도달 → 고신뢰 신호.

---

## 0. 프리미스 게이트 (사용자 확정)

- **Premise 3 재정의 채택 (옵션 A).** "벡터가 구조적으로 못 한다"(허수아비) →
  **"타입드 그래프 경로가 관계형 질문에서 recall·근거(provenance)·감사가능성·비용이 낫다"**로 수정.
  **agentic 벡터 베이스라인**(질문 분해 + 약쌍 열거 + 같은 텍스트 다회 검색)을 추가한다.
  승부처는 "불가능"이 아니라 **조합 완전열거 + 결정론 + 근거경로 + 토큰/지연 비용**.
- 나머지 Premise(1·2·4·5)는 유지. 단 Premise 1(DUR 성분쌍 ID)은 Day 1 실측으로 확정 — 기존 Assignment대로.

---

## 0.5 최종 게이트 결정 (사용자 확정 — APPROVED)

이 3건은 자동결정 못 하는 게이트였고, 사용자가 확정했다. 아래가 다른 taste 권장과 충돌하면 **이게 우선**.

| # | 결정 | 사용자 선택 | 비고 |
|---|---|---|---|
| 게이트1 | 핵심 thesis | **A. 리프레임 + agentic 베이스라인** | §0 |
| UC1 | 스코프 | **더 공격적 ~15–20개 약물** | 내 권장(~25–30)보다 더 줄임. 모든 고리 손검증 100% 가능 = 가장 안전. §5 Week1·게이트 숫자 이걸로 갱신 |
| UC2 | 포지셔닝 | **하이브리드** | 이름 `PolyPharmGraph` 유지 + README 최상단 한 줄을 "eval-first 벤치마크: 타입드 그래프가 벡터/agentic RAG를 언제 이기나 (한국 약물안전 데이터)"로. DUR=데이터셋 |
| Taste | 데모 저장소 | **Kùzu 임베디드** | 서버리스 + Cypher/그래프DB 신호 유지. 빌드/개발용 Neo4j는 유지. 데이터 export 포맷 = Kùzu 스냅샷 |

> ~15–20개로 더 줄인 결과: 견고한 *자동* 추출 파이프라인은 확실히 컷이고 **LLM보조+사람확정 큐레이트 표**가 정답.
> 골드셋이 작아 P/R이 덜 안정적인 점은 README "단일저자·소표본 한계"에 명시(이미 success criteria에 있음).

---

## 1. 단계별 합의표 (Dual-Voice Consensus)

### CEO (전략·스코프)
| 차원 | Claude | Codex | 합의 |
|---|---|---|---|
| 1. 프리미스 타당? | 부분 | 부분 | **DISAGREE** — P3 과장(→A로 해소) |
| 2. 풀 문제 맞나? | 예* | 예* | **CONFIRMED** (*리프레임 전제) |
| 3. 스코프 보정? | 아니오 | 아니오 | **CONFIRMED — 예산의 ~2배, 페이로드 뒤로 몰림** |
| 4. 대안 충분탐색? | 아니오(F5) | — | Claude만 B우위 제기 → 단일voice 플래그 |
| 5. 시장/경쟁 리스크? | 부분 | 부분 | **CONFIRMED — 니치는 "리프레임하면 자산"** |
| 6. 6개월 궤적? | 리스크 | 리스크 | **CONFIRMED — thesis 생존 리스크** |

### Design (UI/UX) — 두 voice 거의 동일 결론
> "채용담당자가 *유일하게 실제로 보는* 부분이, 플랜에서 *유일하게 정의 안 된* 부분이다."

| 차원 | 합의 |
|---|---|
| 정보 위계(첫 화면) | **미정의** — Streamlit 기본 흐름에 방치 |
| 4개 상태(loading/empty/error/partial) | **전부 미정의**. partial(미해결 약 → 조용히 누락 → 거짓 "안전")은 **안전성 CRITICAL** |
| 그래프 렌더러 | **핸드웨이브** → 두 모델 독립적으로 **`st.graphviz_chart`, `rankdir=LR`** 처방(pyvis/agraph는 3노드에서 물리엔진 지터) |
| 안전 배너 | 위치 오류(리포트 끝) → **입력 전 + 결과 옆 상단 고정** |

### Eng (아키텍처)
| 차원 | Claude | Codex | 합의 |
|---|---|---|---|
| 1. 아키텍처 건전? | 대체로 | 대체로 | CONFIRMED (LangGraph = 약한 "node theater") |
| 2. 평가 커버리지? | 아니오 | 아니오 | **CONFIRMED — 나이브 벡터는 허수아비** |
| 3. 성능/recall 리스크? | 아니오 | 아니오 | **CONFIRMED — 곱셈적 손실 0.85⁴≈52%** |
| 4. 정확성 위협? | 아니오 | 아니오 | **CONFIRMED — overflagging, 억제강도 필터 없음** |
| 5. 에러 경로? | 아니오 | 아니오 | **CONFIRMED — "unknown"이 "safe"로 렌더** |
| 6. 배포 리스크? | 아니오 | 아니오 | **CONFIRMED — HF Spaces는 Neo4j 영속 불가** |

### DX (채용담당자 경험) — 두 voice 동일 결론
> "아직 *포트폴리오 산출물*이 아니라 *기획 repo*다. 개념은 이해되지만 *작동을 볼 수 없다*."

| 차원 | 합의 |
|---|---|
| README 가독성 | **CRITICAL** — 문서 색인(여기 내 설계문서들), product page 아님 |
| 라이브 데모(TTHW) | **CRITICAL** — Neo4j 호스팅 미해결, 식으면 "고장난 repo"로 읽힘 |
| 로컬 재현성 | **CRITICAL** — `docker compose up` 없음, `.gitignore`가 데모 스냅샷 커밋을 *차단* |
| 정직성 신호 | coverage%·"그래프 지는 구간" → DESIGN.md에 묻힘, README/데모에 없음 |

---

## 2. 교차단계 테마 (3+ 단계에서 독립 발생 = 최고신뢰)

1. **스코프가 예산의 ~2배** — CEO·Eng·DX. → ~25–30개 큐레이트 약물로 컷.
2. **나이브 벡터 = 허수아비** — CEO·Eng. → agentic 베이스라인 필수(프리미스 A로 채택).
3. **데모의 Neo4j 호스팅 미해결** — Design·Eng·DX. → 서버리스 스냅샷(NetworkX/Kùzu/SQLite) 또는 AuraDB.
4. **한국 DUR은 1홉(직접금기)만 담당, 헤드라인 전이는 영어 openFDA에서 나옴** — CEO·Eng. → 정직한 포지셔닝 필요.

---

## 3. 전체 발견 (단계 × 심각도)

### CRITICAL
- **C1 (Eng) Overflagging — 임상유의성 필터 없음.** `(a)-INHIBITS->(e)<-SUBSTRATE_OF-(c)`가 *모든* 공유효소쌍에 발화.
  대부분 임상 무의미(약한 억제·부수경로) → 진짜 신호(amiodarone+clarithromycin+simvastatin)가 수십 개 잡음에 묻힘.
  약리 아는 면접관이 즉시 간파. **Fix:** 라벨에서 **strength(strong/moderate/weak)·clinical_action·evidence_sentence·negated**를 엣지 속성으로 추출,
  `contraindicated/avoid/dose-adjust/monitor` 또는 strong/moderate만 alert. 나머지는 "mechanistic note".
- **C2 (Eng) 곱셈적 recall 붕괴.** 전이 적중 = resolve A × resolve C × find/extract A엣지 × find/extract C엣지.
  각 85%면 ≈52%. 스키마 다이어그램엔 안 보임. **Fix:** **단계별 recall 워터폴 표** 보고 + 데모 약물은 손으로 ~100%까지 큐레이트.
- **C3 (Eng/Design/DX) "unknown"을 "safe"로 렌더.** 미해결 약 → CYP엣지 없음 → 전이분석 조용히 스킵 → "안전".
  안전 도구에서 신뢰 끝장. **Fix:** state에 resolution status, Synthesis가 "분석불가: X"를 "분석함, 무위험"과 분리.
- **C4 (Design) 그래프 렌더러 미선택 = 제품 전체.** 10초 비주얼에 다 거는데 라이브러리 미정.
  **Fix:** `st.graphviz_chart` + 손수 DOT, `rankdir=LR`, 효소노드 라벨, 억제=빨강 실선. (HF Spaces는 `packages.txt`에 `graphviz` 바이너리 필수 — 로컬OK/배포death 함정.)
- **C5 (DX) README가 product page 아님.** 채용담당자 60초 → "아직 안 만들었네"로 읽힘. **Fix:** 최상단 = 훅 + 데모뱃지 + **데모 GIF** + A/B 한 줄 표 + 아키다이어그램. 문서색인은 맨 아래로.
- **C6 (DX) 데모 Neo4j 의존 = 호스팅 미해결.** Streamlit Cloud는 Neo4j 못 띄움; AuraDB Free는 3일 후 자동정지; HF Spaces는 sleep+cold start. **Fix:** 데모를 **서버리스 스냅샷**(커밋된 작은 그래프 → in-memory)으로 분리. Neo4j는 빌드/개발용으로 유지(엔지니어링 신호).
- **C7 (DX) 키 없는 재현 불가.** `docker compose up` 없음, data.go.kr 키 등록 강요. `.gitignore`가 `data/`·`*.csv`·`*.parquet` 제외 → **데모 스냅샷 커밋 자체를 차단**. **Fix:** 작은 스냅샷 커밋(KOGL Type1+CC0가 허용) + gitignore 예외 + 키 0개로 `docker compose up`.

### HIGH
- **H1 (CEO/Eng) A/B 공정성 — agentic 베이스라인.** 프리미스 A로 채택. 추가: **모든 CYP 엣지와 모든 (b)골드 hop은 공유 라벨 텍스트에 근거**해야 함; 라벨 밖 지식 필요한 케이스는 A/B에서 제외(또는 별도 플래그). 보정 전 raw 추출 precision도 보고(construction-from-text 정직성).
- **H2 (CEO) 한국 차별화 ↔ graph-wins thesis가 서로를 강화하지 않음.** DUR은 1홉만. **Fix:** 정직하게 "한국 처방 resolver + 공식 DUR 직접규칙 + FDA라벨 유래 CYP 기전그래프"로 표기. graph-wins는 평가표가 증명, DUR은 legibility 래퍼.
- **H3 (Eng) 크로스온톨로지 = 진짜 spine, 과소명세.** ATC 브릿지 > approximateTerm. **Fix:** `KRIngredient`/`ActiveMoiety`/`RxNormIngredient` 분리, 매핑법(exact/salt-stripped/combo/ATC/fuzzy/manual/failed) 저장, fuzzy는 v1에서 수동승인, 염·복합제 명시 처리, "DUR∩openFDA 둘 다 있는 약"을 Day-1 선정필터로.
- **H4 (Eng) extraction precision만 약속, recall 미약속.** recall이 헤드라인 cap. 스코프 작으면 분모 측정가능(Flockhart). **Fix:** precision+recall 둘 다 보고.
- **H5 (Eng) Cypher가 헤드라인 기전과 불일치.** "두 억제제+기질"인데 쿼리는 pairwise만. 가산억제·유도(INDUCES)·경쟁 미모델. **Fix:** 규칙 템플릿(억제+기질=노출↑, 유도+기질=노출↓, 다중억제=신뢰/심각도↑ 단 라벨 action 뒷받침시). 스키마의 INDUCES 死엣지 살림.
- **H6 (Design/DX) 안전배너 위치·정직성신호 노출.** 배너 = 입력 전 상단 고정. coverage%/한계 = README 상단 + 데모 출력에 노출.
- **H7 (Eng/DX) hot-path 외부API.** Resolver가 쿼리타임에 RxNav 호출. **Fix:** 빌드때 전부 해소→스냅샷 캐시, 데모 쿼리경로는 로컬 그래프만. "snapshot date" 표기.
- **H8 (Eng) 부정셋(negatives) 약함.** **Fix:** 골드 40문항 층화: 직접양성·전이양성·하드네거티브(공유효소지만 임상무의미)·매핑실패·abstention. "기권/unknown" 별도 채점.

### MEDIUM
- **M1 (Design)** 상태 5종(loading 단계내레이션/empty=safe카드/error/partial/ambiguous-match) 명세 + 1페이지 UI 스펙 산출.
- **M2 (Design)** A/B 승리를 **데모 안에** 노출("벡터가 놓침" 뱃지 + "왜 못 잡았나" expander). provenance는 progressive disclosure(expander).
- **M3 (CEO)** 골드셋 비임상가 단독작성 = 신뢰 리스크 → 공식규칙·인용증례 앵커, 약사 1인 sanity-check, "엔지니어링 데모(임상검증 아님)" 명시.
- **M4 (CEO)** RAGAS는 그래프출력에 부적합 → **path-level precision/recall이 1차지표**, RAGAS는 NL 요약에만(이력서 키워드).
- **M5 (CEO)** "graph 지는 구간"에 측정치 없음 → 단일약·지연민감 1–2케이스에서 **직접 측정한** 패배 1개.
- **M6 (CEO)** "이 문장은 세상 어디에도 없다" 과장 → "임의 처방에 대해 *온더플라이 합성*"으로 재표현.
- **M7 (DX)** 빌드글 = Week3 크런치에 묻혀 잘림 → `docs/BUILD_NOTES.md` 점진작성, README가 곧 포스트. 이중언어는 EN 상단폴드라도.
- **M8 (Eng)** LangGraph node theater → Router에 진짜 분기(그래프 커버리지<임계 → openFDA/벡터 호출) + **checkpointer** 추가(RESEARCH.md가 table-stakes로 꼽음).

---

## 4. Decision Audit Trail (6원칙 자동결정)

| # | 단계 | 결정 | 분류 | 원칙 | 근거 |
|---|---|---|---|---|---|
| 1 | CEO | Premise 3 재정의 + agentic 베이스라인 | **GATE(사용자)** | — | 사용자 확정 A |
| 2 | Eng | strength/clinical_action/evidence/negated 추출 + 유의성 필터 | 자동 | P1 완전성 | overflagging이 데모 최악 실패 |
| 3 | Eng | 단계별 recall 워터폴 보고 | 자동 | P1 | 0.85⁴ 손실 가시화 |
| 4 | Eng/Design | resolution status state, unknown≠safe | 자동 | P1 | 안전도구 신뢰 |
| 5 | Design | `st.graphviz_chart` rankdir=LR (+packages.txt) | 자동 | P3 실용 | 두 모델 독립 동일선택 |
| 6 | Design | 4상태+1페이지 UI 스펙 산출 | 자동 | P1 | 최고가시 산출물 |
| 7 | Design | 안전배너 상단 고정 | 자동 | P5 명시 | 임상 책임 자세 |
| 8 | Design/DX | A/B승리·coverage%·한계를 데모/README에 노출 | 자동 | P1 | 묻힌 신호=0가치 |
| 9 | Eng | ATC 브릿지 우선, 매핑법 저장, fuzzy 수동승인 | 자동 | P5 명시 | 조용한 오조인 방지 |
| 10 | Eng | 라벨텍스트 근거 강제, 밖지식 케이스 A/B 제외 | 자동 | P1 | 공정성 진짜로 유지 |
| 11 | Eng | precision+recall 둘 다, 골드 층화+abstention | 자동 | P1 | precision만은 가짜안심 |
| 12 | Eng | INDUCES를 2번째 규칙템플릿으로 살림 | 자동 | P1 | 死엣지 제거+풍부함 |
| 13 | Eng/DX | 데모=서버리스 스냅샷 분리, Neo4j는 빌드용 | 자동(피지빌리티) | P2 | HF Spaces Neo4j영속 불가(두 모델 합의) |
| 14 | DX | README product page 재작성 + 데모 GIF 산출물화 | 자동 | P1 | 60초 가독성 |
| 15 | DX | 키0 `docker compose up` + 스냅샷 커밋 + gitignore 예외 | 자동 | P1 | 재현성 |
| 16 | DX | hot-path 외부API 제거, snapshot date | 자동 | P5 | 라이브 의존=데모death |
| 17 | DX | BUILD_NOTES.md 점진, EN 상단폴드 | 자동 | P6 행동 | 크런치 컷 방지 |
| 18 | Eng | Router 진짜 분기 + checkpointer | 자동 | P5 | 싼 시니어 신호 |
| 19 | CEO | RAGAS는 NL요약만, path-level P/R이 1차 | 자동 | P5 | 그래프출력에 RAGAS 부적합 |
| 20 | CEO | 과장문구 재표현, "graph 지는" 측정치 1개 | 자동 | P5 | 쉬운 반박거리 제거 |

---

## 5. 재배열된 3주 계획 (페이로드 우선, 게이트 강화)

> 원칙: **얇은 end-to-end 슬라이스를 Week1 말까지 출하**. 평가+데모를 *먼저* 만들고 *나중에* 넓힌다.

**Day 1–3 게이트 (코드 최소, 전부 통과해야 진행):**
1. DUR ID 확정(15056780 vs 15059486, 10행 실측) — *기존 Assignment*
2. openFDA 라벨 1건 CYP3A4 기질 문장 실재 확인 — *기존 Assignment*
3. 전이 골드 5개 손작성 — **단, 각 hop을 공유 라벨 텍스트에서 가리킬 수 있어야** *(기존+강화)*
4. **20–30 라벨 추출 미니평가** (precision+recall) — *신규 게이트*
5. **~15–20 성분 손큐레이트 크로스워크 표** (DUR∩openFDA) — *신규 게이트*
6. **호스팅 = Kùzu 스냅샷 export 확정** (빌드용 Neo4j → Kùzu 스냅샷) — *데이터 export 포맷이 여기 의존*
7. **5 케이스 agentic-벡터 go/no-go** — 잡히면 3일차에 thesis 약점 인지·피벗 *(권장)*

**Week 1 — 얇은 슬라이스:** 1개 치료군(스타틴 + CYP3A4 억제/유도제 + 항생제), **~15–20 약물**의 손큐레이트 CYP엣지(strength 포함),
direct-DDI + 전이 Cypher, 5골드, **스텁 Streamlit(graphviz 경로)**, **Kùzu 스냅샷 export**. → 데모가 끝까지 돈다.

**Week 2 — 확장:** 스코프 넓힘, **두 베이스라인(나이브 + agentic)**, provenance 출력, 4상태 UI, Router 분기 + checkpointer.

**Week 3 — 동결·증명:** 기능동결, 층화 40골드(전이 hop은 라벨근거), 양 파이프라인 실행, 단계별 워터폴+P/R+latency/cost 표,
README product-page + GIF + 다이어그램, 배포 스모크테스트(graphviz 바이너리), BUILD_NOTES→포스트.

---

## 6. NOT in scope (이번 컷 / v2 연기)
- 전체 약전 / 대형 그래프 (평가표가 핵심, 그래프 크기 아님).
- 견고한 자동 CYP 추출 *파이프라인* (→ LLM보조 + **사람 최종확정** 큐레이트 표로 대체).
- `e약은요`(15075057) 자유텍스트, PatientContext — **Week1 슬립 시 첫 컷 대상** (taste 결정 참조).
- AdverseEvent/MedDRA/ICD 노드 (이미 v2로 연기됨, 유지).
- interrupt/resume HITL (정적 배너로 충분, 유지).

## 7. What already exists (재사용 자산)
- 검증된 데이터·라이선스 매트릭스(`RESEARCH.md`) — 재실측만.
- 후보 비교·선정 근거(`IDEAS.md`).
- 외부 무료소스: DUR OpenAPI, openFDA(CC0), RxNav(키불요). 비공개 QA 레퍼런스(Flockhart/DrugBank) — 커밋 금지 유지.

## 8. 단일 voice 플래그 (합의 아님 → FYI)
- **F5 (Claude CEO만):** 대안 B(StareDecisis)가 명시 기준상 A를 지배할 수 있다(판례 시효성=더 직관적 graph-wins, 라이선스 0리스크, CourtListener 기성 인용그래프). **Codex는 전환 미주장.** → 권장: **A 유지**(사용자 의도적 선택 + 리프레임이 B 장점 대부분 흡수). 단 인지해 둘 것.

---

## 9. 우선순위 구현 태스크 (집계)
- [ ] **P1 — Day1–3 게이트 7종** (특히 추출 미니평가 + 호스팅 결정 + agentic go/no-go) — 슬라이스 전 차단요소
- [ ] **P1 — 데모 서버리스 스냅샷 분리** (export 포맷 결정 → 데이터모델 의존) — Week1
- [ ] **P1 — CYP 엣지에 strength/clinical_action/evidence/negated + 유의성 필터** — overflagging 차단
- [ ] **P1 — resolution status state (unknown≠safe)** — 안전 신뢰
- [ ] **P1 — README product-page + 데모 GIF + 키0 `docker compose up` + gitignore 예외** — 채용 표면
- [ ] **P1 — agentic 벡터 베이스라인 + 라벨근거 강제 + 층화골드** — A/B 방탄
- [ ] **P2 — graphviz_chart 4상태 UI + 1페이지 UI 스펙 + 배너 상단** — 10초 whoa
- [ ] **P2 — ATC브릿지 크로스워크(매핑법 저장) + 단계별 recall 워터폴** — spine 정직성
- [ ] **P2 — Router 분기 + checkpointer, INDUCES 2번째 템플릿** — 시니어 신호
- [ ] **P3 — BUILD_NOTES 점진 + EN 상단폴드 + "graph 지는" 측정 1개 + 과장문구 수정** — 배포 멀티플라이어

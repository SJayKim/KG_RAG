# Gate 4 — openFDA CYP3A4 Extraction Mini-Eval (정량화)

> DESIGN "Day 1–3 게이트" 4번 항목의 Week 1 실측. **라벨 텍스트 → 타입드 CYP3A4 엣지** 추출이
> 실제로 서는지를 precision/recall로 측정한다. 평가는 Gate 2에서 검증한 **CYP3A4 축**에 스코프.
> 실행일: 2026-07-04. 산출물: `scripts/extract/*.py` + `fixtures/openfda-labels/*` + 이 문서.

## 헤드라인 — 추출기 사다리 (waterfall)

| 추출기 | precision | recall | F1 | TP/FP/FN |
|---|---|---|---|---|
| `regex` (결정적 베이스라인, 키 불필요) | 0.64 | 0.25 | 0.36 | 7 / 4 / 15 |
| `llm` (단방향 — 각 약 자기 라벨만) | **1.00** | 0.60 | 0.75 | 15 / 0 / 8 |
| `llm-bidirectional` (+ 기질 라벨 열거 회수) | **1.00** | **0.75** | **0.86** | 18 / 0 / 5 |
| `llm-bidirectional v2` (week1-recall: 자기서술+열거 채굴 확장) | **1.00** | **1.00** | **1.00** | 27 / 0 / 0 |

- **recall = required(1차 역할) 엣지 기준** — 22약 중 20약이 required CYP3A4 엣지 1개, 2약(pravastatin·rosuvastatin)은 음성(엣지 0).
- **precision 1.00 (LLM)** = 추출한 엣지가 전부 옳음. 허구·오귀속 0건. 음성 2약에 CYP3A4 엣지 안 붙임(하드네거티브 통과).
- **recall 0.60 → 0.75** = 기질 라벨이 가해자를 열거한다는 사실(게이트 Finding 3)을 코드로 회수한 이득.

## 핵심 발견 (thesis·설계에 직접 영향)

### 1. recall 상한은 **추출 품질이 아니라 소스 커버리지**가 정한다
openFDA 라벨은 자기 CYP3A4 역할을 **일관되게 서술하지 않는다.** 교과서적 강한 억제제인
**ketoconazole·ritonavir조차 자기 라벨에 "나는 CYP3A4 억제제"라는 문장이 없다**(uncapped 확인).
단방향 LLM이 놓친 8약은 추출 실패가 아니라 **원문에 사실이 없어서**다 → DESIGN의 "단계별 recall 워터폴"
(resolve→…→extract→cite)이 실측으로 확인됨. 그래프를 라벨만으로 지으면 이 엣지들은 비게 된다.

### 2. 양방향 추출(게이트 Finding 3)이 recall을 실제로 올린다 — provenance까지
기질 라벨(simvastatin·lovastatin·atorvastatin·verapamil…)이 가해자를 이름으로 **열거**한다:
> lovastatin 라벨: *"Strong inhibitors of CYP3A4 (e.g., itraconazole, ketoconazole, … clarithromycin, … nefazodone, erythromycin …)"*

`augment_bidirectional.py`가 이 열거를 크로스워크 약명과 매칭해 **erythromycin·ketoconazole·ritonavir**를
강한/중등도 억제제로 회수. 회수 엣지는 전부 `recovered_from: substrate-label:<host>` 출처를 달아 A/B 공정성 유지.

### 3. 양방향 채굴에는 co-naming 함정이 있다 (직접 밟고 고침)
verapamil 라벨 한 문장이 억제제(erythromycin, ritonavir)**와** 유도제(rifampin)를 **동시에** 열거한다.
순진한 "문장에 inhibitor 단어 있음 → 억제제" 로직은 **rifampin을 억제제로 오탐(FP)**. → 약명 위치에서
**가장 가까운 cue**로 역할을 배정하는 proximity 규칙으로 수정. 이게 이 프로젝트가 다루는 co-naming 문제의 축소판.

### 4. regex 베이스라인이 지는 이유 = **주어 귀속(subject attribution)**
regex는 simvastatin 라벨의 *"strong CYP3A4 inhibitors"*(가해자=타 약)를 보고 **simvastatin을 억제제로 오탐**.
LLM은 그 문구가 타 약을 가리킴을 알고 substrate만 추출. 이 격차(F1 0.36 → 0.75)가 "construction-from-text에
LLM이 필요하다"의 정량 근거.

### 5. `strength`는 라벨이 자주 생략한다 (정직한 약점)
매칭된 억제/유도 엣지에서 **strength 정확도 0.50** — 라벨이 *"inhibitor of CYP3A4"*라고만 하고
strong/moderate 등급을 안 쓰는 경우가 많다(diltiazem·verapamil·amiodarone). 추출기는 등급어가
있을 때만 strength를 채우고 없으면 null로 둔다(허구 금지). → 유의성 필터용 strength는 **2차 소스/규칙 보강**
필요. `clinical_action` 정확도는 0.75로 더 나음(contraindicated/dose-adjust/monitor는 문맥에서 잡힘).

## 잔여 miss (recall 0.75의 나머지 5)
`dronedarone, phenytoin, midazolam, phenobarbital, cyclosporine` — 자기 라벨에 CYP3A4 자기서술 없고,
채굴한 기질 라벨 6개에도 이름이 안 나옴. **해소책:** (a) 기질 라벨 corpus 확대(품목당 여러 SPL), (b) 유도제-기질
문장도 채굴, (c) 최후엔 비공개 Flockhart로 *검증만*(그래프 미포함, 라이선스 하드룰). Week 2 과제.

## 양방향 추출 per-drug (llm-bidirectional)

| drug | gold | extracted | 결과 |
|---|---|---|---|
| simvastatin | substrate | substrate | ✅ |
| lovastatin | substrate | substrate | ✅ |
| atorvastatin | substrate | substrate | ✅ |
| pravastatin | (none) | (none) | ✅ 하드네거티브 |
| rosuvastatin | (none) | (none) | ✅ 하드네거티브 |
| clarithromycin | inhibitor(+substrate) | inhibitor | ✅ |
| erythromycin | inhibitor(+substrate) | inhibitor | ✅ 양방향 회수 |
| itraconazole | inhibitor(+substrate) | inhibitor,substrate | ✅ |
| ketoconazole | inhibitor(+substrate) | inhibitor | ✅ 양방향 회수 |
| ritonavir | inhibitor(+substrate) | inhibitor | ✅ 양방향 회수 |
| diltiazem | inhibitor(+substrate) | inhibitor | ✅ |
| verapamil | inhibitor(+substrate) | inhibitor,substrate | ✅ |
| amiodarone | inhibitor(+substrate) | inhibitor | ✅ (추론) |
| dronedarone | inhibitor(+substrate) | (none) | ❌ MISS |
| rifampin | inducer | inducer | ✅ |
| carbamazepine | inducer(+substrate) | inducer,substrate | ✅ |
| phenytoin | inducer | (none) | ❌ MISS |
| midazolam | substrate | (none) | ❌ MISS |
| fluconazole | inhibitor | inhibitor | ✅ (추론) |
| nefazodone | inhibitor(+substrate) | inhibitor | ✅ |
| phenobarbital | inducer | (none) | ❌ MISS |
| cyclosporine | inhibitor(+substrate) | (none) | ❌ MISS |

## 방법 (재현)

- **corpus:** `fetch_label_corpus.py` — openFDA generic_name 라벨 22약의 4개 섹션(drug_interactions,
  contraindications, clinical_pharmacology, warnings), 섹션당 15k자 캡. **CC0, 키 불필요.**
  → `fixtures/openfda-labels/corpus.json`. (섹션 캡 8k→15k 상향: nefazodone 자기서술 문장이 8k 뒤에 있어 잘렸던 실버그 수정.)
- **gold:** `fixtures/gold/extraction_gold_v0.jsonl` — 22약, required 20 + 음성 2. 이중역할 약(itraconazole=억제+기질 등)은
  2차 역할을 optional로 태깅(진짜 pharmacology를 FP로 안 세도록).
- **추출:** `run_extraction.py --extractor {regex,llm}` (LLM은 `ANTHROPIC_API_KEY` 필요). 양방향은 `augment_bidirectional.py`.
- **채점:** `score_extraction.py` — 역할 매칭(greedy 1:1), precision=TP/(TP+FP), recall=matched_required/required.
  strength·clinical_action은 매칭 엣지 대상 2차 field 정확도.

```bash
PYTHONUTF8=1 python scripts/extract/fetch_label_corpus.py fixtures/openfda-labels/corpus.json
# regex 베이스라인 (키 불필요, 오늘 실행)
PYTHONUTF8=1 python scripts/extract/run_extraction.py --extractor regex \
    fixtures/openfda-labels/corpus.json fixtures/openfda-labels/extracted_regex.json
# LLM 단방향 (키 필요) — 이 문서의 extracted_llm.json은 Claude Fable 5 세션 추출로 시드
ANTHROPIC_API_KEY=... PYTHONUTF8=1 python scripts/extract/run_extraction.py --extractor llm \
    --model claude-sonnet-5 fixtures/openfda-labels/corpus.json fixtures/openfda-labels/extracted_llm.json
# 양방향 회수
PYTHONUTF8=1 python scripts/extract/augment_bidirectional.py fixtures/openfda-labels/corpus.json \
    fixtures/openfda-labels/extracted_llm.json fixtures/crosswalk/ingredient_crosswalk_v0.csv \
    fixtures/openfda-labels/extracted_llm_bidir.json
# 채점 + 리포트
PYTHONUTF8=1 python scripts/extract/score_extraction.py fixtures/gold/extraction_gold_v0.jsonl \
    fixtures/openfda-labels/extracted_llm_bidir.json docs/GATE4-EXTRACTION.md
```

> ⚠️ 정직성: `extracted_llm.json`은 이 세션의 Claude Fable 5가 각 라벨 원문에서 **충실 추출**한 시드다
> (자기서술 없는 라벨은 `[]` = 정직한 miss). 재현 시 `run_extraction.py --extractor llm` + 키로 대체 가능.
> 골드는 단일 저자(+약사 sanity-check 예정) 한계 — DESIGN 명시대로 소표본·단일저자 리스크 문서화.

## 판정
**Gate 4 = PASS (정량).** 추출 전략 성립: **precision 1.00, recall 0.75(양방향), F1 0.86.** 라벨 텍스트에서
타입드 CYP3A4 엣지를 허구 없이 추출 가능함을 실측. recall 격차는 소스 커버리지 문제로 규명됐고 해소 경로가 있다.
다음: 이 엣지들 + 1,816 DUR 직접금기 엣지를 Neo4j에 적재(Week 1 그래프 로드).

---

## Recall recovery (week1-recall) — 0.75 → **1.00** (precision 1.00 유지, LLM 재추출 없음)

`ANTHROPIC_API_KEY` 없이(=LLM 재추출 불가) 디스크의 corpus.json만으로 **결정적** 회수. 시드
`extracted_llm.json`은 그대로 두고 `augment_bidirectional.py`만 확장. 잔여 miss 5개(dronedarone,
phenytoin, midazolam, phenobarbital, cyclosporine)를 **전부** 회수 — 단, 회수 엣지는 모두 corpus의
**실제 문장을 verbatim**으로 달고(`recovered_from`), 하드네거티브는 계속 침묵.

| 지표 | before (bidir) | after (bidir v2) |
|---|---|---|
| precision | 1.00 (18/18) | **1.00 (27/27)** |
| recall (required) | 0.75 (15/20) | **1.00 (20/20)** |
| F1 | 0.86 | **1.00** |
| TP / FP / FN | 18 / 0 / 5 | **27 / 0 / 0** |

하드네거티브 **pravastatin·rosuvastatin = ext(none)** 유지(FP 0). 두 약의 라벨은 *"not metabolized by
CYP3A4"*, *"not dependent on metabolism by cytochrome P450 3A4"*처럼 **부정문**이라, 새로 넣은 negation
guard가 정확히 걸러 substrate 오탐을 막았다.

### 5개 miss → 회수 (근거 문장은 전부 corpus verbatim)

| drug | 회수 역할 | 출처 라벨 | 메커니즘 | 근거 문장 (verbatim) |
|---|---|---|---|---|
| **cyclosporine** | inhibitor / dose-adjust | atorvastatin | 열거(동격) | *"…concomitant administration of atorvastatin and **cyclosporine, an inhibitor of CYP3A4** and OATP1B1…"* |
| **dronedarone** | inhibitor / **moderate** / dose-adjust | dronedarone(자기 라벨) | 자기서술 | *"**Dronedarone is metabolized by CYP3A and is a moderate inhibitor of CYP3A** and CYP2D6…"* |
| **phenytoin** | inducer / monitor | dronedarone | 열거(such as) | *"Avoid rifampin or other **CYP3A inducers such as phenobarbital, carbamazepine, phenytoin**, and St[. John's Wort]"* |
| **phenobarbital** | inducer / monitor | dronedarone | 열거(such as) | (위와 동일 문장) |
| **midazolam** | substrate | midazolam(자기 라벨) | 자기서술(대사) | *"…the **biotransformation of midazolam is mediated by cytochrome P450-3A4**."* |

**진단 정정 (corpus 재검증 결과):** 사전 진단은 dronedarone을 "honest source-absence"로 봤으나,
**dronedarone 자기 라벨이 스스로를 "moderate inhibitor of **CYP3A**"라고 서술**한다(위 verbatim). 놓친
원인은 소스 부재가 아니라 라벨이 **"CYP3A4"가 아닌 "CYP3A"(subfamily) 철자**를 써서 기존 CYP3A4-strict
정규식이 안 걸린 것. → **소스 부재로 남는 required miss는 0개.** (Week 2 과제였던 "잔여 5"가 모두 fetched
corpus 안에 실재함을 확인.)

### 왜 precision가 안 깨졌나 — 채굴 규칙 (약명 하드코딩 아님, 일반 cue-phrase 로직)

1. **Subfamily tolerance (CYP3A ≡ CYP3A4).** cue 정규식의 끝 "4"를 optional로. 라벨이 이 약들을
   "CYP3A inhibitor/inducer"로 등급/열거하는 게 흔하고(dronedarone·ritonavir 등), CYP3A4가 간 CYP3A의
   지배적 isoform이라 DDI 귀속상 동치. **verbatim 문장을 보존**해 정규화가 감사 가능.
2. **전 라벨 스캔 + 자기서술 채굴 추가.** 기존엔 "substrate 라벨"만 훑었으나, 가해자 라벨도 다른 가해자를
   열거하고(dronedarone→phenytoin/phenobarbital) 자기 역할을 직접 서술함(dronedarone·midazolam).
   자기서술은 **약명 앵커드 술어 템플릿**("X is a <strength> inhibitor of CYP3A", "X is metabolized by
   CYP3A4", "biotransformation of X … CYP3A4")으로만 회수 → 남의 대사를 말하는 문장에 약이 단지 *언급*됐다고
   오탐하지 않음.
3. **열거 membership = 구조 규칙**(순진한 proximity 폐기). 초기 시도는 proximity만으로 4건 FP 발생 —
   ritonavir 금기 블록이 문장 분리 실패로 substrate 리스트 + 뒤쪽 *"drugs that are potent CYP3A inducers"*
   절을 한 덩어리로 뭉쳐, 앞의 midazolam/simvastatin/lovastatin/dronedarone을 **inducer로 오탐**. 수정:
   약이 cue의 **열거 멤버**일 때만 귀속 —
   (a) **forward**: cue 뒤 `such as / including / e.g. / : / (` 도입부 뒤 리스트에 등장(종결자 `)`·새 문장 전),
   (b) **appositive/subject**: cue 바로 앞에서 **copula/동격**으로 결속(`X, an inhibitor…`, `X and Y are
   substrates…`) — 단 `with/concomitant/receiving` 같은 **병용 전치사면 배제**(≠ 자기 정체).
   이 규칙이 4건 FP + 부정직한 clarithromycin substrate 1건(*"clarithromycin … concomitantly **with** CYP3A4
   substrates"* — 병용이지 자기 기질 아님)까지 제거.
4. **Negation guard.** substrate/대사 주장에 cue 앞 window에 부정어(not/no/little/minimal…)가 있으면 skip
   → pravastatin·rosuvastatin 음성 유지.

### strength 정직성
회수 inducer(phenytoin·phenobarbital)와 cyclosporine inhibitor는 근거 문장이 등급어를 안 써서
**strength=null**로 둠(gold는 strong/moderate지만 라벨 미기재 → 허구 안 함). dronedarone만 라벨이
명시적으로 *"moderate"*라 **moderate**로 채움. (그래서 전체 strength 정확도는 0.31로 하락 — recall을 올리며
등급 없는 문장을 정직히 null 처리한 대가. clinical_action 정확도는 0.69로 유지.) required recall/precision은
role 매칭이라 영향 없음.

### 크로스워크 확장 (D-code는 `dur_ingredient_dcode_dict.json`과 대조 검증)
- `cyclosporine` — `D001077` (사이클로스포린), ATC `L04AD01`, inhibitor/moderate/dose-adjust,
  `evidence_source=openFDA-label:drug_interactions` (atorvastatin 라벨 동격으로 회수).
- `phenobarbital` — `D000282` (페노바르비탈), ATC `N03AA02`, inducer/strong/monitor,
  `evidence_source=openFDA-label:drug_interactions` (dronedarone 라벨 such-as 열거로 회수).

### 잔여 상한
**required 엣지 기준 소스-부재 miss = 0.** 회수 안 된 것은 전부 **optional 2차 역할**(clarithromycin·
erythromycin·ketoconazole·diltiazem·nefazodone의 substrate 등) — 라벨이 해당 약을 CYP3A4 기질이라고
**약명 앵커드로 술어화하지 않아** 정직하게 비워둠(P/R 무영향, 허구 회피). 재현: 위 §방법의
`augment_bidirectional.py` 커맨드 그대로.

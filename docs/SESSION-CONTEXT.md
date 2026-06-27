# SESSION CONTEXT — 핸드오프 (브레인스토밍 → 구현)

이 문서는 office-hours 브레인스토밍 세션의 전체 맥락을 다음 작업(구현, 또는 새 Claude 세션)으로 넘기기 위한 것.
새 세션에서 이 repo를 열면 **이 파일부터 읽으면** 어디까지 왔고 다음에 뭘 할지 즉시 파악된다.

## 1. 무엇을 하려는가

Knowledge Graph 기반 **RAG 에이전트** 포트폴리오 프로젝트. 사용자는 AI/LLM 엔지니어 **취업**(한국 시장)이 목표.
사용자가 처음 건 두 가지 하드 기준:
1. **관련 데이터를 실제로 수집할 수 있을 것** (공개 데이터/API, 포트폴리오·데모 허용 라이선스)
2. **실제로 수요가 있을 만한 것** (채용담당자가 즉시 이해 + 그래프가 벡터 RAG를 이기는 게 명확한 문제)

## 2. 어떻게 여기까지 왔나 (의사결정 경로)

1. **목표** = 취업/포트폴리오 (창업 아님) → builder 모드.
2. **도메인** = 의료/바이오/법률 (사용자 선택). *주: 처음 금융/뉴스 눌렀다가 의료/바이오/법률로 정정.*
3. **다중 에이전트 리서치 워크플로우** 실행 — 4개 리서치 에이전트(의료/바이오/법률/채용수요) + 3개 아이디어 에이전트 + 12개 적대적 검증 에이전트. (결과 → `RESEARCH.md`, `IDEAS.md`)
4. **후보 4개 정리** (도메인별) → 사용자가 **A. PolyPharmGraph 선택**.
5. **설계 문서 작성** (`DESIGN.md`) → **독립 적대적 리뷰 2회**:
   - 1차 6/10, 블로킹 6개(DrugBank 라이선스 위반, 성분코드 직접맵 부재, 평가 조작 가능성, 미사용 스키마, YAGNI, 데이터셋 ID 모호) → 전부 수정.
   - 2차 8/10, 6개 전부 RESOLVED 확인 + 잔여 2개(Flockhart ship 경계, 문구) 추가 수정 완료.

## 3. 현재 상태

- ✅ 아이디어 발굴 + 검증 + **설계 문서 확정**(8/10). 구현 **시작 전**.
- ⬜ 코드 0줄. 아직 데이터 수집/그래프/에이전트/평가 미착수.

## 4. 다음 행동 (Assignment — 코드 전에 오늘 할 것)

`DESIGN.md`의 "The Assignment" 섹션과 동일:
1. `data.go.kr` DUR dev key 발급 → **`15056780`(성분) vs `15059486`(품목) 둘 다 병용금기 10행** 떠보고 성분쌍 깨끗한 ID 채택.
2. openFDA 라벨 1개(예: simvastatin) 받아 "Drug Interactions/Clinical Pharmacology"에 **CYP3A4 기질 문장 실재** 확인 → 추출 1순위 전략 검증.
3. amiodarone/clarithromycin/simvastatin 류 **전이 골드 질문 5개를 정답 경로까지 손으로** 작성(못 적으면 스코프 조정 신호).

그다음: `DESIGN.md`의 Week 1~3 계획대로 구현 진입.

## 5. 핵심 설계 결정 (구현 시 반드시 지킬 것)

- **CYP 기전 엣지 = openFDA 라벨(CC0) LLM 추출이 1순위.** DrugBank/Flockhart/PharmGKB는 **비공개 QA 전용**, 공개 repo/데모/그래프에 절대 포함 금지(라이선스 하드룰).
- **평가 공정성**: 벡터 베이스라인은 그래프 CYP 엣지를 추출한 **같은 openFDA 라벨 텍스트**를 읽는다(정보 비대칭 금지). 전이 골드 정답은 **독립 근거**로 손수 작성.
- **그래프 노드 5종만**: Drug, Ingredient, RxConcept, Enzyme, PatientContext. (AdverseEvent/Condition/MedDRA/ICD는 v2)
- **에이전트 = LangGraph 상태머신** (resolver/direct-DDI/transitive-DDI/patient/router/synthesis). human-in-the-loop 노드 안 씀(정적 "약사 검토 필요" 배너).
- **데모 = Streamlit + HF Spaces** (Next.js 안 씀).
- **프로젝트의 심장 = 벡터 RAG 대비 공정한 A/B 평가표** (전이 적중률 + latency/cost). 수치는 결과지 미리 정한 목표 아님.
- **provenance 필수**: 모든 플래그가 출처 엣지(DUR / openFDA-label) 인용.

## 6. 새 Claude 세션에서 이어가는 법

1. 이 repo 루트에서 시작. `README.md` → `docs/SESSION-CONTEXT.md`(이 파일) → `DESIGN.md` 순으로 읽기.
2. 방향 유지면: `DESIGN.md`의 Assignment/Week1부터 구현.
3. 방향 재검토면: `docs/IDEAS.md`의 대안 B/C/D 참고.
4. 데이터·라이선스 의문 생기면: `docs/RESEARCH.md`(2026-06-27 웹 검증)부터 확인 — 단, 라이선스는 시간이 지나면 변할 수 있으니 착수 전 재확인 권장.

## 7. 기술 스택 (확정)

Python · Neo4j Community(Docker) · LangGraph · langchain-neo4j · Qdrant/Chroma(벡터 베이스라인) ·
Claude(Opus/Sonnet) 또는 오픈모델 · RAGAS · Streamlit + HuggingFace Spaces.
산출물: GitHub repo + 이중언어(KO/EN) README + 아키텍처 다이어그램 + A/B 평가표 + 라이브 데모 URL + 빌드 글.

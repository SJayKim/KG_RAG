# KG_RAG — Knowledge-Graph RAG Agent (포트폴리오 프로젝트)

> **eval-first 벤치마크 — 타입드 지식그래프가 벡터/agentic RAG를 *언제* 이기는가를 한국 약물안전 공개데이터로 측정한다.**
> 산출물의 심장은 공정한 A/B 평가표. **PolyPharmGraph**는 그 위에 올라가는 데모의 이름.

Knowledge Graph 기반 RAG **에이전트** 시스템 포트폴리오. 목표는 취업(AI/LLM 엔지니어, 한국 시장).
선정된 프로젝트는 **PolyPharmGraph** — 한국 식약처 DUR 데이터 기반 다제약물(polypharmacy) 안전성 에이전트로,
규칙에 적혀 있지 않은 **전이적 약물상호작용(공유 CYP 효소 경쟁)**을 그래프 순회로 찾아내고 근거 경로를 출력한다.

## 이 repo에 뭐가 있나

| 파일 | 내용 |
|---|---|
| [`DESIGN.md`](./DESIGN.md) | **최종 설계 문서.** 문제정의·그래프 스키마·에이전트 구조·평가 하네스·UI 스펙·3주 계획·데이터 수집(라이선스 포함). office-hours 리뷰 2회(8/10) + autoplan 4단계 리뷰 반영(2026-06-28). |
| [`docs/DESIGN-REVIEW.md`](./docs/DESIGN-REVIEW.md) | **autoplan 설계 검토** — CEO·Design·Eng·DX 4단계 이중 voice(Claude+Codex), 합의표, 발견(CRITICAL 7), Decision Audit Trail, 게이트 결정(리프레임·~15–20 스코프·agentic 베이스라인·Kùzu 데모). |
| [`docs/RESEARCH.md`](./docs/RESEARCH.md) | 검증된 리서치 — 의료/바이오/법률 수집 가능 데이터셋·라이선스·접근법, 2026 채용 수요, GraphRAG vs 벡터 동향. (웹 검증 2026-06-27) |
| [`docs/IDEAS.md`](./docs/IDEAS.md) | 후보 아이디어 4개(최종) + 검증 점수. 왜 PolyPharmGraph를 골랐는지. |
| [`docs/SESSION-CONTEXT.md`](./docs/SESSION-CONTEXT.md) | 브레인스토밍 세션 핸드오프 — 결정 사항, 현재 상태, 다음 행동, 이어가는 법. |

## 지금 상태

- ✅ 아이디어 발굴 + 적대적 검증 + 설계 문서 완료 (office-hours 브레인스토밍 단계)
- ✅ autoplan 4단계 설계 검토 통과 + 게이트 결정 반영 (2026-06-28, `docs/DESIGN-REVIEW.md`)
- ⬜ 구현 시작 전. **다음 행동 = `DESIGN.md`의 Day 1–3 게이트**(DUR ID 실측·openFDA 라벨·전이 골드 5개·추출 미니평가·크로스워크·agentic go/no-go).

## 핵심 결정

- **도메인**: 의료 (한국 DUR). 그래프가 벡터 RAG를 이기는 게 명확한 다중홉 문제.
- **데이터**: 전부 무료/공개 — 식약처 DUR OpenAPI(KOGL), openFDA 라벨(CC0), RxNav(공개). 게이트/유료 소스 미사용.
- **프로젝트의 심장**: 벡터 RAG 대비 **공정한 A/B 평가표**. "GraphRAG 좋다"는 주장이 아니라 측정으로 증명.

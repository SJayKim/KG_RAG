# RESEARCH — KG-RAG 포트폴리오 리서치 (웹 검증 2026-06-27)

다중 에이전트 워크플로우로 의료/바이오/법률 도메인의 **수집 가능 데이터**, **2026 채용 수요**,
**GraphRAG 동향**을 병렬 리서치하고 웹으로 검증한 결과. 모든 데이터셋·라이선스는 2026-06-27 기준 확인.

---

## 0. 채용 수요 & GraphRAG 동향 (가장 중요 — 프로젝트 방향을 결정)

### 2026 채용이 실제로 보는 시그널
1. **Eval 역량이 1순위 시그널.** "LLM로 실제 만들어봤다 vs 유튜브 봤다"를 가르는 단일 최대 신호.
   → KG-RAG 포트폴리오는 **반드시 평가 하네스(RAGAS + 다중홉 골드셋) + 벡터 RAG 베이스라인 A/B**를 포함해야 한다.
2. **프로덕션 사고 > 프로토타입.** 실패 처리, 데이터 구조화, 시스템 연결, 배포. 리크루터는 이력서 10초, runnable repo/라이브 데모엔 ~80% 더 관여.
3. **LangGraph가 table-stakes** (2026 채용공고). 상태머신, 체크포인팅, planning vs execution 노드 분리, 조건부 라우팅.
4. **검색 깊이** — BM25/하이브리드/ColBERT/reranking을 언제 쓰는지. "API 튜토리얼"과 "진짜 RAG 엔지니어"의 차이.
5. **한국 특화** — 시장이 Training → **Inference + Agent**로 이동(2026). 사람인/잡코리아 공고에 LangChain/LangGraph/AutoGen,
   Function Calling/Tool Use, vector DB(Pinecone/Qdrant/Weaviate). "RAG 시스템 구축 경험"이 스카우트 자석. 신입 5,000만~1.5억.
6. **도메인 신뢰성** — 의료/법률은 출력에 감독·검증 필요 인식을 높이 봄. **인용/provenance(어느 노드·엣지·출처가 답을 뒷받침)**가 차별점.
7. **텍스트→KG 구축** 자체가 수요 스킬 (LLM 트리플/엔티티-관계 추출, 스키마·온톨로지 설계, community detection).

### 평가받는 스킬 (우선순위)
LangGraph · Neo4j+Cypher · LlamaIndex PropertyGraphIndex · Microsoft GraphRAG(참고용, 무겁고 비쌈) ·
**RAGAS**(faithfulness, context precision/recall, answer relevancy) + 에이전트 trajectory eval(LangSmith/Phoenix) ·
하이브리드/리랭킹 검색 · KG 구축(트리플 추출) · agentic 다중홉(query decomposition, planner) · vector DB · 강한 Python/백엔드/배포.

### 포트폴리오 차별 요소
- **재현 가능한 A/B 벤치마크**: 같은 질문, 두 파이프라인(벡터 RAG vs KG-RAG 에이전트), 결과표(정확도/faithfulness/인용정확도/지연/비용). ← 이 단일 산출물이 "GraphRAG 만들었다"를 "벡터 RAG를 이긴다고 증명했다"로 바꿈.
- **정직한 trade-off 분석**: GraphRAG가 어디서 이기고(다중홉, 교차엔티티 집계, global sensemaking) 어디서 지는지(지연, 비용, 단일사실 조회). 2025~26 논문들이 GraphRAG 이득 과장을 깠으므로, 이 정직함이 시니어 신호.
- **좁고 큐레이션된 코퍼스 + 명명된 페르소나** (랜덤 PDF 덤프 금지).
- **그래프 출처 인용**(provenance), **텍스트에서 직접 구축한 KG**(스키마 문서화), **LangGraph 상태머신**, 폴리시된 전달(라이브 데모 URL + README + 아키텍처 다이어그램 + 빌드 글).

### GraphRAG 동향 (2026, 냉정해진 담론)
- 2024 과장("GraphRAG가 RAG를 이긴다")은 증거 기반 "it depends"로 대체됨.
- **그래프가 이김**: 다중홉 관계추론, 교차엔티티 집계, global sensemaking(벡터가 ~0%로 떨어지는 곳). 실측 사례: Diffbot KG-LM ~16.7%→56-80%, Med-GraphRAG ablation.
- **그래프가 짐(논문들이 지적)**: 단일홉 NQ에서 ~13% 나쁨, 시간민감 질문 ~16% 하락 (arXiv 2506.06331, 2502.11371, 2506.05690 GraphRAG-Bench).
- **툴**: MS GraphRAG(강력하나 비쌈/느림), LlamaIndex PropertyGraphIndex(가장 실용적 build-your-own), LangGraph(오케스트레이션 표준), Neo4j(지배적 저장소, native Cypher+벡터 인덱스).
- **포트폴리오 결론**: "그래프가 마법"이 아니라 "**측정된 하네스로 다중홉/교차엔티티에서 그래프+에이전트가 이김을 보이고, 지불하는 지연/비용과 안 쓸 상황까지 제시**". 이 eval 주도·trade-off 인식 프레이밍이 차별점.

### 피해야 할 클리셰
"PDF와 채팅"(최포화), A/B 없는 GraphRAG 우월 주장, 페르소나 없는 거대 코퍼스, **장식용 그래프**(예쁜 시각화인데 답은 벡터 청크에서), 프레임워크 나열 이력서 미끼, 라이브 데모/배포 없음, 비용/지연 무시, **얻을 수 없거나 데모 금지인 데이터**(특히 의료: MIMIC는 CITI 인증 필요).

---

## 1. 의료 / 임상 데이터

| 소스 | 무엇 | 접근 | 라이선스 | 그래프성 | 한국어 |
|---|---|---|---|---|---|
| **식약처 DUR OpenAPI** (`data.go.kr` 15059486 품목 / **15056780 성분**) | 병용금기·특정연령대금기·임부금기·용량주의·효능군중복 등 **구조화 안전규칙** | 무료 dev key 자동승인, JSON/XML | **KOGL Type1** (출처표시, 상업·파생 허용) | **이미 엣지(성분쌍+사유코드)** | ✅ |
| **식약처 e약은요** (15075057) | 제품별 효능/사용법/주의/상호작용/부작용 텍스트 | 무료 key, 1만/일 | KOGL Type1 | 반정형(텍스트→추출) | ✅ |
| **openFDA** Drug Label + FAERS | 라벨(적응증/금기/상호작용 free-text) + 이상사례 보고 | 무료 REST(선택 key) | **CC0** | 라벨은 텍스트→추출, FAERS는 표 | ❌ |
| **RxNorm + RxNav REST** | 정규화 약명/성분/관계 + RxClass(ATC/기전) | **키 불필요** REST | 공개(NLM) | 그래프성(관계 엔드포인트) | ❌ |
| **UMLS Metathesaurus** (SNOMED/ICD/MeSH/RxNorm 통합) | ~4.5M 개념 + MRREL(관계 엣지) | 무료 **UTS 계정**(~5일 승인) | UMLS License(무료) | **이미 엣지(MRREL)** | ❌ |
| **SIDER 4.1** | 약↔부작용 쌍(MedDRA), 13.9만 쌍 | 직접 TSV 다운(계정 X) | CC BY-SA 4.0 | 이미 엣지 | ❌ (2015 고정) |
| **Hetionet** | 47k 노드 / 2.25M 엣지 통합 바이오 KG | GitHub Neo4j 덤프/JSON/TSV | CC0(소스별 속성) | **완제품 그래프** | ❌ (2017 고정) |
| **PrimeKG** | 정밀의학 KG, 17k 질병 / ~4M 관계, indication/contraindication/off-label 엣지 | Harvard Dataverse CSV | CC0급 | 엣지리스트 CSV | ❌ |

**게이트/주의:**
- **MIMIC-IV** (실제 임상노트): PhysioNet 자격증명 + **CITI 교육** 필요, **DUA가 3자 LLM API 전송 금지** → 로컬 모델 필수. 포트폴리오엔 부적합. 거버넌스 인식은 면접에서 features로 언급.
- **RxNav DDI API 폐기됨 (2024-01-02)** → 단순 DDI 조회 대체재 없음. 그래프 순회/식약처 DUR이 그 공백을 메움.
- **HIRA 보건의료빅데이터**: 개방 통계/API(KOGL)는 OK, 환자단위 microdata는 신청+현장방문(3주 프로젝트엔 부적합).

**그래프가 벡터를 이기는 의료 질의 (검증됨):**
다제약물 DDI 체인(공유 CYP 효소 경쟁의 전이적 위험), 동반질환 통한 금기(증상→질병→약→금기→환자약 4홉),
기전 기반 상호작용 발견(공유 효소 노드로 추론), 부작용 회피 대체약 제안, 인구통계 게이트 금기(연령/임신), **provenance 경로 출력**.

---

## 2. 바이오 / 생명과학 데이터

| 소스 | 무엇 | 접근 | 라이선스 | 그래프성 |
|---|---|---|---|---|
| **Hetionet** | 47k 노드/2.25M 엣지, 약물재창출(Rephetio) 기반 | Neo4j 덤프/TSV, 라이브 neo4j.het.io | **CC0** | **완제품** |
| **PrimeKG** | 정밀의학 KG, indication/contraindication/off-label + 임상 텍스트 | Harvard Dataverse kg.csv | CC0/코드 MIT | 엣지리스트 CSV |
| **Open Targets** | 현행 target-disease-drug 증거, association score | Parquet 벌크 + **라이브 GraphQL API** | **CC0** | GraphQL(그래프형) |
| **Reactome** v90+ | 전문가 큐레이션 경로/반응 | **공식 Neo4j 덤프** | data CC0 / DB dump CC BY 4.0 | **완제품 Neo4j** |
| **STRING** v12.5 | 단백질-단백질 기능/물리 연관 + 신뢰도 | TSV/REST | CC BY 4.0 (학술+상업) | 가중 엣지리스트 |
| **Gene Ontology + GOA** | 유전자/단백질 기능 온톨로지(DAG) | OBO/OWL/JSON-LD | CC BY 4.0 | 그래프형 온톨로지 |
| **ClinVar** | >3M 변이-질병 임상의의 | NCBI FTP/E-utilities | 미국 공공도메인 | 표→엣지 추출 |
| **ChEMBL** | 큐레이션 생활성, 화합물-표적-기전-적응증 | 풀 DB 덤프/REST | CC BY-SA 3.0 | 관계형→그래프 ETL |
| **DRKG** | 재창출 KG, 9.7만 엔티티 / 5.9M 트리플 + DGL-KE 임베딩 | GitHub TSV | Apache-2.0(+소스별) | 완제품 트리플 |

**게이트/주의:** **DisGeNET** 2023+ 리뉴얼로 계정/승인(학술 비상업) 필요 — repo에 덤프 재배포 금지.
**KEGG** 벌크 다운 **유료 구독** + AI/ML 보존 제한 → 공개 포트폴리오에 임베딩 금지(대신 Reactome).
**DRKG**는 DrugBank 파생 엣지 포함 → 비상업 데모 OK, DrugBank 태그 서브셋 재배포 금지.

**그래프가 벡터를 이기는 바이오 질의:** 약물재창출 체인(약→표적→경로→질병 4+홉), "왜 약 X가 병 Y에?"(경로 자체가 설명),
공유기전 약물, 변이→치료 정밀의학 체인, 두 엔티티 연결경로(shortest path), 이웃 집계, 부재추론.

**기존 프로젝트(차별화 기준선):** KG_RAG(BaranziniLab/UCSF, SPOKE 기반, 비공개 데이터=우리의 기회), PrimeKG(튜토리얼 많음→에이전트/eval로 차별),
Hetionet/Rephetio(재현 가능한 골드 표준), **BioCypher**(KG 구축 프레임워크), DRKG(GNN 베이스라인).

---

## 3. 법률 데이터

| 소스 | 무엇 | 접근 | 라이선스 | 그래프성 | 한국어 |
|---|---|---|---|---|---|
| **국가법령정보 OPEN API** (open.law.go.kr) | 법령(조문/시행일/제·개정 이력) + 판례(**참조판례·참조조문** 필드) | 무료 OC key, **활용신청 1~2일 승인** | 무료(상업 포함, **법제처 출처표시 필수**) | 법령 반정형 / 판례는 참조필드가 엣지 | ✅ |
| **CourtListener / Free Law Project** | ~9M 미국 판례 + **Citations Map(인용 엣지+깊이)** | 공개 S3 벌크(분기), 무료 REST v4 | 공공도메인/CC0급 | **완제품 인용 그래프** | ❌ |
| **Caselaw Access Project** | 6.7M 미국 판례(1658-2020) | 벌크 + HuggingFace parquet | 공개/공공도메인(2024-03 제한 만료) | 경량 추출 | ❌ |
| **EUR-Lex / CELLAR** | 모든 EU 법 문서를 RDF 트리플, cites/amends/transposes 타입 엣지 | **SPARQL** + REST | 공개 재사용 | **이미 RDF KG** | ❌ |
| **US Code (USLM XML)** | 미국 법전 구조 + 교차참조 | govinfo 벌크 | 공공도메인 | 경량 추출 | ❌ |

**그래프가 벡터를 이기는 법률 질의:** 선례 권위 체인(전이적 인용), **시효성 추론**(폐기된 선례/개정 법조문에 의존하는 '유효' 판결),
상충 선례 탐지, 부정적 처리(Shepardizing), 인용 최단경로, 토픽 내 중심성 랭킹, **한국 참조판례 체인 + 개정 이력 조인**.

**차별 화이트스페이스:** 한국 판례 인용+법령 개정 KG(참조판례/참조조문 활용 — 공개 사례 거의 없음, 한국 채용 직결),
**시효성 추론**(그래프가 벡터 이기는 가장 직관적 사례), 교차도메인 엣지(판례↔법조문↔개정).

---

## 핵심 라이선스 요약 (공개 repo/데모 안전성)

- **안전(공개 배포 OK)**: 식약처 DUR/e약은요(KOGL, 출처표시), openFDA(CC0), RxNav(공개), Hetionet/PrimeKG/Open Targets/Reactome data(CC0), ClinVar(공공도메인), CourtListener/CAP/US Code(공공도메인), 국가법령정보(무료+법제처 출처표시).
- **주의(share-alike)**: SIDER/ChEMBL(CC BY-SA — 혼합 시 copyleft 전염), STRING/GO(CC BY).
- **공개물 금지**: DrugBank(ToU 재배포·파생·혼합 금지 → 비공개 QA만), KEGG 벌크(유료), DisGeNET 덤프(승인 필요), MIMIC(CITI+DUA).

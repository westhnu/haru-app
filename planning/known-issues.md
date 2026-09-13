# Known Issues

기획안·재활용 자산과 실제 파일 사이의 불일치, 원칙 위반 위험 요소를 기록한다.
기획안 다음 리비전(v1.2) 작성 시 근거로 사용한다.

---

## KI-001 — jutopia_data 모듈 3개 부재

- **발견**: 2026-09-13, Bootstrap STEP 1 컨텍스트 파악 중
- **내용**: 아래 3개 파일이 `/Users/westhnu/Agent/Claude/jutopia_data/` 어디에도 없다 (`_archive/` 포함, `find`로 확인).
  - `dart_financial_loader.py`
  - `metrics_calculator.py`
  - `financial_analyzer.py`
- **영향받는 기획안 섹션**: §5.1(워크북 재활용 모듈), §5.2·§12(체크리스트 채점), §13.8(`search_dart_disclosures`, `evaluate_checklist` @tool 매핑)
- **원인 추정**: §12와 `docs/PROJECT_MODULES_SUMMARY.md`가 모듈 정리 이전 시점 기준으로 작성됨
- **결정 (PO, 2026-09-13)**: v1.2 이슈로 보류.
  - Sprint 2는 `dart_client.py`만 래핑해서 진행
  - PER/PBR/ROE 등 체크리스트 채점용 지표 계산기는 Haru에서 자체 구현 (v2)
  - 기획안 v1.2에서 §12를 실제 파일 기준으로 재작성

## KI-002 — `HantuStock` 클래스에 주문 함수 혼재 (원칙 5 위험)

- **발견**: 2026-09-13
- **내용**: `jutopia_data/HantuStock.py`의 `HantuStock` 클래스에 조회 메서드와 주문 메서드가 함께 있다.
  - 주문 계열: `bid` (L422), `ask` (L460), `cancel_order` (L637)
  - 같은 저장소의 `web_order.py`, `run_mock_trades.py`도 `HantuStock`을 import해 주문 흐름을 구성
- **위험**: 클래스를 통째로 import·상속하면 주문 실행 경로가 Haru 코드에 들어온다.
- **결정 (PO, 2026-09-13)**: 조회 전용 위임(delegation) 래퍼 승인. 한투 연동 스프린트에서 구현.
  - 파일: `backend/app/services/hantu_readonly.py`, 상속 금지
  - 노출 허용: `get_holding_stock_detail`, `get_holding_stock`, `get_holding_cash`, `get_transaction_history`, `get_transaction_summary`, `get_minute_chart`
  - 주문 메서드는 이름조차 코드에 등장시키지 않음 (테스트의 `hasattr` 회귀 검증은 예외)
  - `web_order.py`, `run_mock_trades.py` 참조 금지

## KI-003 — 기획안 부록의 `haru_web` 파일 일부 부재

- **발견**: 2026-09-13
- **내용**: 기획안 §12 "부록 위치"에 적힌 파일 중 다음이 없었다.
  - `haru_web/README.md` → Sprint 0에서 생성 (해결)
  - `haru_web/artifacts/haru_planning_board.html`, `morning_global_market.html`, `evening_korea_market.html` → 미해결, 이 저장소에 없음
- **조치**: 아티팩트 HTML은 PO 확인 전까지 생성·복원하지 않는다.

## KI-004 — `dart_client.py`의 환경변수 로딩 방식 (Sprint 2 확인 필요)

- **발견**: 2026-09-13
- **내용**: `dart_client.py`가 `import os`, `from dotenv import load_dotenv`를 사용한다. 모듈 import 시점에 `.env`를 읽거나 `os.getenv`로 키를 직접 참조할 가능성이 있다.
- **위험**: Haru 규칙 "환경변수는 `Settings` 하나로만 관리"와 충돌하고, `python-dotenv` 의존성이 추가된다.
- **조치**: Sprint 2에서 실제 동작을 확인한 뒤 래퍼(`dart_tool.py`)에서 키를 명시적으로 주입하는 방식을 결정한다.

## KI-005 — 데이터 처리 리전 이슈 (`global.` 추론 프로파일)

> Sprint 1 브리핑에서는 "KI-002"로 지정했으나, KI-002는 HantuStock 항목이 이미 사용 중이라 KI-005로 기록한다.

- **발견**: 2026-09-13, Sprint 0 모델 ID 확인 중
- **내용**: 서울 리전(`ap-northeast-2`)에서 Claude Sonnet/Haiku 4.5 이상은 ON_DEMAND 호출이 불가하고, `apac.` 프로파일도 없어 **`global.` 크로스 리전 추론 프로파일만** 사용 가능하다. 요청이 한국 밖 리전에서 처리될 수 있다.
- **결정 (PO, 2026-09-13)**: 승인. MVP는 공개 정보(DART·용어사전) 위주이고 PII는 마스킹하므로 리스크 낮음.
- **완화 조치**
  - Sprint 1: `core/guardrail.py`의 `mask_pii()`를 RAG 호출 직전에 적용 — 주민등록번호·카드·휴대전화·계좌번호를 라벨 토큰으로 치환한 뒤에만 Bedrock으로 전송
  - Sprint 1: 로그에는 질의 원문 대신 길이만 기록
  - 예정: Bedrock Guardrail Sensitive Information 필터(입력·출력 마스킹, 기획안 §13.5)
- **재검토 트리거**
  - 사용자별 데이터(투자 저널, 한투·키움 잔고/거래내역)를 프롬프트에 넣기 시작할 때 (Sprint 2.5 이후)
  - 서울 리전 native 또는 `apac.` 프로파일로 4.5+ 모델이 제공될 때
  - 개인정보 국외 이전 고지·동의 필요 여부 법무 검토 시 (퍼블릭 런칭 M6 전)

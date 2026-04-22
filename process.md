# DividendManagement 개발 전체 기록

## 프로젝트 개요
배당주 10개 종목을 3가지 모델로 스코어링하고, 10년 배당 시뮬레이션을 제공하는 웹 앱.

---

## 완료된 작업 (Phase 1~6)

### Phase 1~2: 데이터 파이프라인
**위치:** `pipeline/`

수집 대상 10개 티커: `HD, PLD, WSO, MCD, CVX, ADP, ABBV, NEE, UNH, WM`

| 파일 | 역할 |
|------|------|
| `pipeline/config.py` | 환경변수 로드, 경로 상수 |
| `pipeline/bootstrap.py` | 최초 1회 정적 데이터 전체 수집 |
| `pipeline/collectors/dividends.py` | 배당 히스토리 |
| `pipeline/collectors/financials.py` | 재무제표 |
| `pipeline/collectors/price_history.py` | 주가 히스토리 |
| `pipeline/collectors/valuation_bands.py` | 밸류에이션 밴드 |
| `pipeline/collectors/live_snapshot.py` | 실시간 스냅샷 |
| `pipeline/collectors/consensus.py` | EPS 컨센서스 |
| `pipeline/collectors/news.py` | 뉴스 + 센티먼트 |
| `pipeline/collectors/market.py` | 시장 지표 |

데이터 저장 위치:
- `data/static/{ticker}/` — 정적 데이터 (dividends, financials, price_history, valuation_bands)
- `data/live/{ticker}/` — 주기적 갱신 데이터 (snapshot, consensus, news, scores, simulation)

---

### Phase 3: 스코어링 엔진
**위치:** `pipeline/engines/`

| 파일 | 모델 | 설명 |
|------|------|------|
| `score_201.py` | 201 매수시점 | 9개 기술적 지표로 매수 타이밍 판단 |
| `score_202.py` | 202 배당성장 | 가중 DGR 기반 성장성 판단 |
| `score_203.py` | 203 지속가능성 | FCF, 부채, ROIC 등 지속가능성 판단 |
| `score_runner.py` | 실행기 | 3개 모델 일괄 실행 + Supabase 저장 |
| `simulation.py` | 204 시뮬레이션 | 10년 배당 현금흐름 4개 시나리오 투영 |

신호 체계:
- 201: `IMMEDIATE_BUY / WATCH / HOLD / CAUTION / DANGER`
- 202: `IMMEDIATE_BUY / STRONG / WATCH / CAUTION / DANGER / C2_BLOCKED`
- 203: `STRONG / CAUTION / DANGER`

Supabase 테이블: `score_cache_global`

---

### Phase 4: FastAPI 서버
**위치:** `api/`

실행: `.venv/Scripts/uvicorn api.main:app --port 8000 --reload`
API 문서: `http://localhost:8000/docs`

| 라우터 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `tickers.py` | `GET /api/tickers/` | 전체 티커 목록 + 스냅샷 요약 |
| | `GET /api/tickers/{ticker}` | 종목 상세 + 밸류에이션 밴드 |
| `scores.py` | `GET /api/scores/` | 전체 스코어 요약 |
| | `GET /api/scores/{ticker}` | 종목 상세 스코어 |
| `simulation.py` | `GET /api/simulation/{ticker}` | 저장된 시뮬 결과 |
| | `POST /api/simulation/{ticker}` | 매수가 지정 즉시 계산 |
| `news.py` | `GET /api/news/` | 전체 뉴스 요약 |
| | `GET /api/news/{ticker}` | 종목 뉴스 전체 |
| `portfolio.py` | `GET /api/portfolio/` | 포트폴리오 목록 |
| | `POST /api/portfolio/` | 종목 추가/수정 |
| | `DELETE /api/portfolio/{ticker}` | 종목 삭제 |
| | `GET /api/portfolio/summary` | 손익 + YOC + Y10 통합 요약 |
| `refresh.py` | `POST /api/refresh/` | 전체 데이터 갱신 (백그라운드) |
| | `POST /api/refresh/{ticker}` | 단일 종목 갱신 (백그라운드) |

포트폴리오 저장 위치: `data/portfolio.json` (로컬 JSON)

---

### Phase 5: Frontend
**위치:** `frontend/`

스택: React 19 + Vite 8 + Tailwind CSS 4 + Recharts + Lucide Icons

로컬 실행:
```bash
cd frontend
npm run dev   # http://localhost:5173
```
(백엔드가 8000에 먼저 떠 있어야 함)

| 파일 | 화면 |
|------|------|
| `src/pages/Dashboard.jsx` | 10개 종목 스코어 테이블, 컬럼 정렬, 행 클릭 → 상세 이동 |
| `src/pages/TickerDetail.jsx` | 스냅샷 지표 + 스코어 카드 + 10년 YOC 라인차트(4시나리오) + 뉴스 |
| `src/pages/Portfolio.jsx` | 보유 종목 추가/삭제, 손익·YOC·Y10 YOC 테이블 |
| `src/pages/News.jsx` | 종목 탭 전환, 기사 카드 + 센티먼트 |
| `src/components/SignalBadge.jsx` | 신호 컬러 배지 |
| `src/components/StatCard.jsx` | 수치 카드 |
| `src/api/client.js` | API fetch 래퍼 |
| `src/App.jsx` | 탑 네비바 + 탭 라우팅 |

---

### Phase 6: 배포 설정 (코드 완료, 실제 배포 미완료)

**전략:** Render (백엔드 무료) + Vercel (프론트엔드 무료)

| 파일 | 역할 |
|------|------|
| `render.yaml` | Render 서비스 설정 |
| `startup.py` | live 데이터 없으면 bootstrap → uvicorn 기동 |
| `nixpacks.toml` | Railway용 (현재 미사용, 보존) |
| `railway.toml` | Railway용 (현재 미사용, 보존) |
| `DEPLOY.md` | 배포 절차 문서 |

GitHub: https://github.com/newrec07/DividendManagement (push 완료)

---

## 환경변수 (.env)

```
FMP_KEY=QYBw1w6MDkFei4ZrnSnrSZmaYTBykTzo
AV_KEY=T62EIDKMMPX6XCR5
SUPABASE_URL=https://dfedhvkwzfyhmtwpsgot.supabase.co
SUPABASE_KEY=sb_publishable_xExqoEusu5TNvX6k8hnxtg_Cuxt6Gt2
```

---

## 내일 바로 시작할 작업: Render + Vercel 배포

### Step 1: Render (백엔드)

1. render.com 접속 → 로그인
2. New → Web Service
3. GitHub 연결 → `newrec07/DividendManagement` 선택
4. 설정:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python startup.py`
   - **Instance Type:** Free
5. Environment Variables 4개 입력 (위 .env 값 그대로):
   - `FMP_KEY`
   - `AV_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
6. Create Web Service → 배포 완료까지 3~5분 대기
7. 발급된 URL 메모 (예: `https://dividend-api.onrender.com`)

### Step 2: Vercel (프론트엔드)

1. vercel.com 접속 → 로그인
2. New Project → GitHub 연결 → `newrec07/DividendManagement` 선택
3. **Root Directory를 `frontend`로 변경** (중요!)
4. Environment Variables 추가:
   - Key: `VITE_API_URL`
   - Value: Step 1에서 받은 Render URL (예: `https://dividend-api.onrender.com`)
5. Deploy → 완료까지 1~2분
6. 발급된 URL로 접속해서 동작 확인

### Step 3: CORS 허용 (필요 시)

Vercel URL이 확정되면 `api/main.py`의 CORS를 Vercel 도메인으로 제한할 수 있음.
현재는 `allow_origins=['*']`이라 별도 작업 불필요.

### Step 4: 주간 데이터 갱신 (선택)

Render 무료는 cron 미지원. 외부 서비스 사용:
- cron-job.org (무료) → 매주 금요일 → `POST https://dividend-api.onrender.com/api/refresh/` 호출

---

## 로컬 개발 명령어 요약

```bash
# 백엔드 실행
cd "d:/[737] AI 프로젝트/[02] DividendManagement"
.venv/Scripts/uvicorn api.main:app --port 8000 --reload

# 프론트엔드 실행 (별도 터미널)
cd "d:/[737] AI 프로젝트/[02] DividendManagement/frontend"
npm run dev

# 스코어 재계산
.venv/Scripts/python pipeline/engines/score_runner.py

# 전체 데이터 갱신
.venv/Scripts/python pipeline/weekly_refresh.py

# git push
cd "d:/[737] AI 프로젝트/[02] DividendManagement"
git add . && git commit -m "메시지" && git push
```

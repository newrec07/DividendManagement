# Railway 배포 가이드

## 구조
- FastAPI (포트 $PORT) → `/api/*` 라우팅 + 프론트엔드 SPA 서빙
- 매주 금요일 17시 cron → `python pipeline/weekly_refresh.py`
- 첫 배포 시 startup.py가 자동으로 live 데이터 생성

## 배포 순서

### 1. Git 레포 준비
```bash
git init
git add .
git commit -m "initial"
```

### 2. Railway 프로젝트 생성
- railway.app → New Project → Deploy from GitHub
- 레포 연결

### 3. 환경변수 설정 (Railway → Variables)
| 변수 | 설명 |
|------|------|
| `FMP_KEY` | Financial Modeling Prep API 키 |
| `AV_KEY` | Alpha Vantage API 키 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase anon/service key |

### 4. 배포
Railway가 자동으로 nixpacks.toml 감지 → 빌드 → 기동

## 로컬 개발
```bash
# 백엔드
.venv/Scripts/uvicorn api.main:app --port 8000 --reload

# 프론트엔드 (별도 터미널)
cd frontend && npm run dev   # http://localhost:5173
```

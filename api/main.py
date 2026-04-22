import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routers import scores, tickers, simulation, news, portfolio, refresh

app = FastAPI(title='DividendManager API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(tickers.router,    prefix='/api/tickers',    tags=['tickers'])
app.include_router(scores.router,     prefix='/api/scores',     tags=['scores'])
app.include_router(simulation.router, prefix='/api/simulation', tags=['simulation'])
app.include_router(news.router,       prefix='/api/news',       tags=['news'])
app.include_router(portfolio.router,  prefix='/api/portfolio',  tags=['portfolio'])
app.include_router(refresh.router,    prefix='/api/refresh',    tags=['refresh'])


@app.get('/api/health')
def health():
    return {'status': 'ok'}


# Serve React SPA — must come after all API routes
_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'dist')

if os.path.isdir(_DIST):
    app.mount('/assets', StaticFiles(directory=os.path.join(_DIST, 'assets')), name='assets')

    @app.get('/{full_path:path}', include_in_schema=False)
    def spa_fallback(full_path: str):
        file_path = os.path.join(_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_DIST, 'index.html'))

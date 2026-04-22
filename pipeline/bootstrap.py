import os
import sys
import json
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import STATIC_DIR, LOGS_DIR
from pipeline.collectors.price_history import save_price_history
from pipeline.collectors.financials import save_financials
from pipeline.collectors.dividends import save_dividends
from pipeline.collectors.valuation_bands import save_valuation_bands
from pipeline.collectors.live_snapshot import save_live_snapshot
from pipeline.collectors.consensus import save_consensus
from pipeline.collectors.market import save_market
from pipeline.collectors.news import save_news

os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bootstrap_errors.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ]
)

PROGRESS_FILE = os.path.join(STATIC_DIR, 'bootstrap_progress.json')


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'pending': [], 'last_run': None, 'status': 'NOT_STARTED'}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def load_tickers() -> list:
    path = os.path.join(STATIC_DIR, 'tickers.json')
    with open(path) as f:
        return [t['ticker'] for t in json.load(f)['tickers']]


def bootstrap_ticker(ticker: str):
    """단일 종목 전체 Static 데이터 수집"""
    print(f"\n{'='*40}")
    print(f"[{ticker}] 수집 시작")
    print(f"{'='*40}")

    save_price_history(ticker)
    time.sleep(1)

    save_financials(ticker)
    time.sleep(1)

    save_dividends(ticker)
    time.sleep(0.5)

    save_valuation_bands(ticker)
    time.sleep(0.5)

    save_live_snapshot(ticker)
    time.sleep(0.5)

    save_consensus(ticker)
    time.sleep(0.5)

    save_news(ticker)
    time.sleep(0.5)

    print(f"[{ticker}] 완료")


def run():
    progress = load_progress()
    all_tickers = load_tickers()

    # pending 초기화 (처음 실행 시)
    if not progress['pending'] and not progress['completed']:
        progress['pending'] = all_tickers

    # 새로 추가된 종목 pending에 추가
    known = set(progress['completed']) | set(progress['pending'])
    for t in all_tickers:
        if t not in known:
            progress['pending'].append(t)

    pending = [t for t in progress['pending'] if t not in progress['completed']]

    if not pending:
        print("모든 종목 수집 완료 상태입니다.")
        return

    print(f"수집 대상: {pending}")
    progress['status'] = 'IN_PROGRESS'
    progress['last_run'] = datetime.today().strftime('%Y-%m-%d')
    save_progress(progress)

    for ticker in pending:
        try:
            bootstrap_ticker(ticker)
            progress['completed'].append(ticker)
            if ticker in progress['pending']:
                progress['pending'].remove(ticker)
            save_progress(progress)
        except Exception as e:
            logging.error(f"[{ticker}] 실패: {e}", exc_info=True)
            print(f"[{ticker}] 오류 발생 - 다음 종목으로 계속")

    remaining = [t for t in progress['pending'] if t not in progress['completed']]
    progress['status'] = 'DONE' if not remaining else 'IN_PROGRESS'
    save_progress(progress)

    print(f"\n완료: {len(progress['completed'])}개 / 미완료: {len(remaining)}개")


if __name__ == '__main__':
    # 특정 종목만 실행: python bootstrap.py ABBV HD
    if len(sys.argv) > 1:
        for t in sys.argv[1:]:
            bootstrap_ticker(t.upper())
    else:
        run()

import os
import json
import requests
from datetime import datetime, timedelta
from pipeline.config import FMP_KEY, STATIC_DIR, LIVE_DIR

FMP_EARNINGS_CAL_URL = 'https://financialmodelingprep.com/stable/earnings-calendar'


def save_consensus(ticker: str) -> dict:
    os.makedirs(os.path.join(LIVE_DIR, ticker), exist_ok=True)

    # FMP earnings-calendar: 향후 예정 분기 EPS 추정치
    today = datetime.today()
    to_date = (today + timedelta(days=365 * 2)).strftime('%Y-%m-%d')
    res = requests.get(FMP_EARNINGS_CAL_URL, params={
        'symbol': ticker, 'from': today.strftime('%Y-%m-%d'), 'to': to_date, 'apikey': FMP_KEY
    }, timeout=15)

    forward_eps = []
    eps_revision = 'NEUTRAL'
    eps_high = None
    eps_low = None

    if res.status_code == 200:
        cal = res.json()
        # 향후 최대 8분기 EPS 추정치
        for r in sorted(cal, key=lambda x: x.get('date', ''))[:8]:
            est = r.get('epsEstimated')
            if est is not None:
                forward_eps.append({'date': r.get('date'), 'eps_estimated': float(est)})

        # EPS 리비전 방향: actual vs estimated 비교로 추정
        past_res = requests.get(FMP_EARNINGS_CAL_URL, params={
            'symbol': ticker,
            'from': (today - timedelta(days=180)).strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d'),
            'apikey': FMP_KEY
        }, timeout=15)
        if past_res.status_code == 200:
            past = [r for r in past_res.json() if r.get('epsActual') and r.get('epsEstimated')]
            if past:
                beats = sum(1 for r in past if float(r['epsActual']) >= float(r['epsEstimated']))
                ratio = beats / len(past)
                eps_revision = 'UP' if ratio >= 0.6 else ('DOWN' if ratio <= 0.3 else 'NEUTRAL')

    # payout_ratio_avg5y: financials.json에서 계산
    payout_avg = None
    fin_path = os.path.join(STATIC_DIR, ticker, 'financials.json')
    if os.path.exists(fin_path):
        with open(fin_path) as f:
            fin = json.load(f)
        div_path = os.path.join(STATIC_DIR, ticker, 'dividends.json')
        if os.path.exists(div_path):
            with open(div_path) as f:
                divs = json.load(f)

            # 연간 DPS (특별배당 제외)
            regular = sorted(
                [d for d in divs['data'] if not d['is_special'] and d['dps'] > 0],
                key=lambda x: x['ex_date'], reverse=True
            )
            # 최근 20분기 기준 배당성향 계산
            income_q = sorted(fin.get('income_quarterly', []), key=lambda x: x['date'], reverse=True)
            payouts = []
            for i in range(min(20, len(income_q))):
                q_rec = income_q[i]
                eps = q_rec.get('eps_diluted') or 0
                if eps and eps > 0:
                    # 해당 분기 DPS 찾기 (날짜 근접)
                    q_date = q_rec['date'][:7]
                    q_div = next((d['dps'] for d in regular if d['ex_date'][:7] == q_date), None)
                    if q_div:
                        payouts.append(q_div / eps)
            payout_avg = round(sum(payouts) / len(payouts), 4) if payouts else None

    consensus = {
        'ticker': ticker,
        'updated_at': today.strftime('%Y-%m-%d'),
        'eps_forward': forward_eps,
        'eps_revision_4w': eps_revision,
        'eps_high': eps_high,
        'eps_low': eps_low,
        'dps_forward': None,
        'payout_ratio_avg5y': payout_avg,
    }

    path = os.path.join(LIVE_DIR, ticker, 'consensus.json')
    with open(path, 'w') as f:
        json.dump(consensus, f, indent=2)

    print(f"[{ticker}] consensus.json 저장 완료 | forward EPS {len(forward_eps)}건 | 리비전: {eps_revision}")
    return consensus

"""
Simulation 204: 10-year forward dividend cash flow projection
Scenarios: Base / Bull / Bear / Freeze
Outputs: quarterly DPS table, cumulative dividends, YOC curve, target buy price
"""
import os
import json
from datetime import datetime
from pipeline.config import STATIC_DIR, LIVE_DIR
from pipeline.engines.score_202 import _calc_weighted_dgr


def _load(ticker: str) -> dict:
    def read(path):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
    return {
        'div':   read(os.path.join(STATIC_DIR, ticker, 'dividends.json')),
        'vb':    read(os.path.join(STATIC_DIR, ticker, 'valuation_bands.json')),
        'cons':  read(os.path.join(LIVE_DIR,   ticker, 'consensus.json')),
        'news':  read(os.path.join(LIVE_DIR,   ticker, 'news.json')),
        'score': read(os.path.join(LIVE_DIR,   ticker, 'scores.json')),
    }


def _get_last_dps(div_data: list) -> float:
    """Most recent regular quarterly DPS"""
    regular = sorted(
        [d for d in div_data if not d.get('is_special') and d.get('dps', 0) > 0],
        key=lambda x: x['ex_date'], reverse=True,
    )
    return regular[0]['dps'] if regular else 0.0


def _dgr_scenarios(weighted_dgr: float | None, freeze: bool) -> dict[str, float]:
    if freeze or weighted_dgr is None:
        return {'base': 0.0, 'bull': 0.0, 'bear': 0.0, 'freeze': 0.0}
    wdgr = weighted_dgr
    return {
        'base':   wdgr,
        'bull':   wdgr + 0.02,
        'bear':   max(wdgr - 0.03, -0.05),
        'freeze': 0.0,
    }


def _divergence_alert(cons: dict, news: dict) -> dict:
    eps_rev = cons.get('eps_revision_4w', 'NEUTRAL')
    news_tone = news.get('tone', 'NEUTRAL')

    consensus_dir = 'POSITIVE' if eps_rev == 'UP' else ('NEGATIVE' if eps_rev == 'DOWN' else 'NEUTRAL')
    news_dir = 'POSITIVE' if news_tone == 'POSITIVE' else ('NEGATIVE' if news_tone in ('NEGATIVE', 'REDFLAG') else 'NEUTRAL')

    alert = False
    band_expand = 0.0
    bear_forced = False

    if consensus_dir == 'POSITIVE' and news_dir == 'NEGATIVE':
        alert = True
        band_expand = 0.20
    elif consensus_dir == 'NEGATIVE' and news_dir == 'NEGATIVE':
        alert = True
        band_expand = 0.20
        bear_forced = True

    return {
        'alert': alert,
        'consensus_dir': consensus_dir,
        'news_dir': news_dir,
        'band_expand': band_expand,
        'bear_forced': bear_forced,
    }


def _project_quarters(
    last_dps: float,
    annual_dgr: float,
    quarters: int = 40,
    forward_eps: list | None = None,
    payout_avg: float | None = None,
) -> list[dict]:
    """Generate quarterly DPS projections with short-term consensus blend"""
    quarterly_dgr = annual_dgr / 4

    # Build consensus EPS lookup
    eps_lookup: dict[str, float] = {}
    if forward_eps:
        for e in forward_eps:
            if e.get('date') and e.get('eps_estimated'):
                eps_lookup[e['date'][:7]] = float(e['eps_estimated'])

    rows = []
    current_dps = last_dps
    today = datetime.today()
    year = today.year
    # Find current quarter
    q = (today.month - 1) // 3 + 1

    for i in range(1, quarters + 1):
        q += 1
        if q > 4:
            q = 1
            year += 1
        quarter_label = f"{year}Q{q}"
        # Approximate date for this quarter (last month of quarter)
        end_month = q * 3
        date_str = f"{year}-{end_month:02d}"

        # Determine zone
        if i <= 4:
            zone = 'short'
        elif i <= 12:
            zone = 'mid'
        else:
            zone = 'long'

        # Base DPS calculation
        if zone == 'short':
            # Priority: consensus EPS × payout, fallback: DGR
            if date_str in eps_lookup and payout_avg:
                dps_consensus = eps_lookup[date_str] * payout_avg
                current_dps = dps_consensus if dps_consensus > 0 else current_dps * (1 + quarterly_dgr)
            else:
                current_dps = current_dps * (1 + quarterly_dgr)
            source = 'consensus' if date_str in eps_lookup else 'dgr'
        elif zone == 'mid':
            if date_str in eps_lookup and payout_avg:
                eps_spread = 0.0  # simplified: no high/low data on free plan
                w = 0.6
                dps_consensus = eps_lookup[date_str] * payout_avg
                dps_dgr = current_dps * (1 + quarterly_dgr)
                current_dps = dps_consensus * w + dps_dgr * (1 - w) if dps_consensus > 0 else dps_dgr
            else:
                current_dps = current_dps * (1 + quarterly_dgr)
            source = 'blended'
        else:
            current_dps = current_dps * (1 + quarterly_dgr)
            source = 'dgr'

        rows.append({
            'quarter': quarter_label,
            'dps': round(max(0, current_dps), 4),
            'zone': zone,
            'source': source,
        })

    return rows


def compute_simulation(ticker: str, buy_price: float | None = None) -> dict:
    d = _load(ticker)
    div_data = d['div'].get('data', [])
    vb = d['vb']
    cons = d['cons']
    news = d['news']
    scores = d['score']

    # Use current price if buy_price not provided
    if not buy_price:
        buy_price = vb.get('current_price', 0)

    annual_dps = vb.get('annual_dps', 0)
    last_dps = _get_last_dps(div_data)
    payout_avg = cons.get('payout_ratio_avg5y')
    forward_eps = cons.get('eps_forward', [])

    # Weighted DGR
    weighted_dgr = _calc_weighted_dgr(div_data)
    current_yield = (annual_dps / buy_price) if buy_price and buy_price > 0 else None

    # Freeze if red flags ≥ 2 or 203=DANGER
    red_flag_count = scores.get('red_flag_count', 0)
    signal_203 = scores.get('signal_203', 'CAUTION')
    freeze = (signal_203 == 'DANGER') and (red_flag_count >= 3)

    dgr_map = _dgr_scenarios(weighted_dgr, freeze)
    divergence = _divergence_alert(cons, news)

    if divergence['bear_forced']:
        active_scenario = 'bear'
    else:
        active_scenario = 'base'

    # Project all scenarios
    scenarios: dict[str, list] = {}
    for scenario, dgr in dgr_map.items():
        scenarios[scenario] = _project_quarters(
            last_dps=last_dps,
            annual_dgr=dgr,
            quarters=40,
            forward_eps=forward_eps,
            payout_avg=payout_avg,
        )

    # Cumulative dividends (annual sums × shares = 1 share basis)
    cumulative: dict[str, list] = {}
    for scenario, rows in scenarios.items():
        cum = 0.0
        cum_list = []
        for row in rows:
            cum += row['dps']
            cum_list.append(round(cum, 4))
        cumulative[scenario] = cum_list

    # YOC by year (annual DPS / buy_price)
    yoc_by_year: dict[str, list] = {}
    for scenario, rows in scenarios.items():
        yoc_years = []
        for yr_idx in range(10):
            annual = sum(r['dps'] for r in rows[yr_idx*4:(yr_idx+1)*4])
            yoc = round(annual / buy_price, 4) if buy_price and buy_price > 0 else None
            yoc_years.append({'year': yr_idx + 1, 'annual_dps': round(annual, 4), 'yoc': yoc})
        yoc_by_year[scenario] = yoc_years

    # Payback quarter (cumulative dividends >= buy_price)
    payback: dict[str, int | None] = {}
    for scenario, cum_list in cumulative.items():
        pb = next((i + 1 for i, v in enumerate(cum_list) if v >= buy_price), None)
        payback[scenario] = pb

    # Target buy price for 5% YOC goal
    next_year_dps_base = sum(r['dps'] for r in scenarios['base'][:4])
    target_price_5pct = round(next_year_dps_base / 0.05, 2) if next_year_dps_base > 0 else None

    return {
        'ticker': ticker,
        'computed_at': datetime.today().strftime('%Y-%m-%d'),
        'buy_price': round(buy_price, 2) if buy_price else None,
        'current_yield': round(current_yield, 4) if current_yield else None,
        'weighted_dgr': round(weighted_dgr, 4) if weighted_dgr else None,
        'dgr_scenarios': {k: round(v, 4) for k, v in dgr_map.items()},
        'freeze': freeze,
        'active_scenario': active_scenario,
        'divergence': divergence,
        'scenarios': scenarios,
        'cumulative': cumulative,
        'yoc_by_year': yoc_by_year,
        'payback_quarter': payback,
        'target_price_5pct': target_price_5pct,
    }


def save_simulation(ticker: str, buy_price: float | None = None) -> dict:
    result = compute_simulation(ticker, buy_price)
    path = os.path.join(LIVE_DIR, ticker, 'simulation.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)
    dgr_str = f"{result['weighted_dgr']*100:.1f}%" if result['weighted_dgr'] else 'N/A'
    pb = result['payback_quarter'].get('base')
    print(f"[{ticker}] simulation.json 저장 | DGR={dgr_str} | 원금회수={pb}Q" + (' [FREEZE]' if result['freeze'] else ''))
    return result

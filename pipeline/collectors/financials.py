import os
import json
import requests
import pandas as pd
from datetime import datetime
from pipeline.config import FMP_KEY, STATIC_DIR

FMP_INCOME_URL = 'https://financialmodelingprep.com/stable/income-statement'
FMP_CASHFLOW_URL = 'https://financialmodelingprep.com/stable/cash-flow-statement'
FMP_BALANCE_URL = 'https://financialmodelingprep.com/stable/balance-sheet-statement'
EDGAR_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
EDGAR_FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
EDGAR_HEADERS = {'User-Agent': 'DividendManager contact@dividendmgr.com'}

# XBRL 태그 정규화 매핑 (태그 우선순위 순서)
XBRL_MAP = {
    'revenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet'],
    'net_income': ['NetIncomeLoss', 'NetIncome'],
    'operating_income': ['OperatingIncomeLoss'],
    'interest_expense': ['InterestExpense', 'InterestExpenseDebt'],
    'operating_cashflow': ['NetCashProvidedByUsedInOperatingActivities'],
    'capex': ['PaymentsToAcquirePropertyPlantAndEquipment', 'CapitalExpendituresIncurringObligation'],
    'dividends_paid': ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock'],
    'retained_earnings': ['RetainedEarningsAccumulatedDeficit'],
    'total_equity': ['StockholdersEquity', 'StockholdersEquityAttributableToParent'],
    'shares_outstanding': ['EntityCommonStockSharesOutstanding', 'CommonStockSharesOutstanding'],
}


def get_cik(ticker: str) -> str:
    res = requests.get(EDGAR_TICKERS_URL, headers=EDGAR_HEADERS, timeout=20)
    res.raise_for_status()
    for _, v in res.json().items():
        if v['ticker'].upper() == ticker.upper():
            return str(v['cik_str']).zfill(10)
    raise ValueError(f"{ticker}: EDGAR CIK 찾기 실패")


def extract_xbrl_series(gaap: dict, concept_key: str, form_type: str, period_filter: str = None) -> list:
    tags = XBRL_MAP.get(concept_key, [])
    for tag in tags:
        if tag not in gaap:
            continue
        units = gaap[tag]['units']
        recs = units.get('USD', units.get('shares', []))
        filtered = [r for r in recs if r.get('form') == form_type]
        if period_filter:
            filtered = [r for r in filtered if r.get('fp') == period_filter]
        # 중복 제거 (같은 날짜 최신 filing 우선)
        seen = {}
        for r in sorted(filtered, key=lambda x: x.get('filed', ''), reverse=True):
            key = r.get('end', r.get('date', ''))
            if key not in seen:
                seen[key] = r
        if seen:
            return sorted(seen.values(), key=lambda x: x.get('end', ''))
    return []


def _safe_fmp_get(url: str, params: dict) -> list:
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code != 200 or not res.text.strip():
            return []
        data = res.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def fetch_fmp_financials(ticker: str) -> dict:
    params_base = {'symbol': ticker, 'apikey': FMP_KEY}
    return {
        'income_quarterly':  _safe_fmp_get(FMP_INCOME_URL,    {**params_base, 'period': 'quarter'}),
        'cashflow_quarterly': _safe_fmp_get(FMP_CASHFLOW_URL, {**params_base, 'period': 'quarter'}),
        'balance_annual':    _safe_fmp_get(FMP_BALANCE_URL,   {**params_base, 'period': 'annual'}),
    }


def fetch_edgar_financials(cik: str) -> dict:
    url = EDGAR_FACTS_URL.format(cik=cik)
    res = requests.get(url, headers=EDGAR_HEADERS, timeout=30)
    res.raise_for_status()
    facts = res.json()['facts']
    gaap = facts.get('us-gaap', {})
    dei = facts.get('dei', {})

    # 분기 손익/현금흐름
    revenue_q = extract_xbrl_series(gaap, 'revenue', '10-Q')
    net_income_q = extract_xbrl_series(gaap, 'net_income', '10-Q')
    op_income_q = extract_xbrl_series(gaap, 'operating_income', '10-Q')
    interest_q = extract_xbrl_series(gaap, 'interest_expense', '10-Q')
    op_cf_q = extract_xbrl_series(gaap, 'operating_cashflow', '10-Q')
    capex_q = extract_xbrl_series(gaap, 'capex', '10-Q')
    div_paid_q = extract_xbrl_series(gaap, 'dividends_paid', '10-Q')

    # 연간 재무상태표
    retained_a = extract_xbrl_series(gaap, 'retained_earnings', '10-K', 'FY')
    equity_a = extract_xbrl_series(gaap, 'total_equity', '10-K', 'FY')
    # 주식수: DEI 네임스페이스에서 가져옴 (gaap의 commonStock은 액면가)
    shares_raw = dei.get('EntityCommonStockSharesOutstanding', {}).get('units', {}).get('shares', [])
    seen_sh = {}
    for r in sorted(shares_raw, key=lambda x: x.get('filed', ''), reverse=True):
        key = r.get('end', '')
        if key and key not in seen_sh:
            seen_sh[key] = r
    shares_a = sorted(seen_sh.values(), key=lambda x: x.get('end', ''))

    def to_records(series: list, val_key='val') -> list:
        return [{'date': r.get('end', ''), 'value': r.get(val_key, 0)} for r in series if r.get('end')]

    return {
        'income_quarterly': {
            'revenue': to_records(revenue_q),
            'net_income': to_records(net_income_q),
            'operating_income': to_records(op_income_q),
            'interest_expense': to_records(interest_q),
        },
        'cashflow_quarterly': {
            'operating_cashflow': to_records(op_cf_q),
            'capex': to_records(capex_q),
            'dividends_paid': to_records(div_paid_q),
        },
        'balance_annual': {
            'retained_earnings': to_records(retained_a),
            'total_equity': to_records(equity_a),
            'shares_outstanding': to_records(shares_a),
        },
    }


def merge_financials(fmp: dict, edgar: dict) -> dict:
    """FMP 최근 5건 + EDGAR 이력 병합. FMP 우선."""

    def fmp_income_to_std(fmp_records: list) -> list:
        result = []
        for r in fmp_records:
            result.append({
                'date': r.get('date', ''),
                'revenue': r.get('revenue'),
                'net_income': r.get('netIncome'),
                'eps_diluted': r.get('epsdiluted'),
                'operating_income': r.get('operatingIncome'),
                'interest_expense': r.get('interestExpense'),
            })
        return result

    def fmp_cashflow_to_std(fmp_records: list) -> list:
        result = []
        for r in fmp_records:
            ocf = r.get('operatingCashFlow', 0) or 0
            capex = abs(r.get('capitalExpenditure', 0) or 0)
            result.append({
                'date': r.get('date', ''),
                'operating_cashflow': ocf,
                'capex': capex,
                'fcf': ocf - capex,
                'dividends_paid': abs(r.get('dividendsPaid', 0) or 0),
            })
        return result

    def fmp_balance_to_std(fmp_records: list) -> list:
        result = []
        for r in fmp_records:
            total_debt = (r.get('longTermDebt', 0) or 0) + (r.get('shortTermDebt', 0) or 0)
            result.append({
                'date': r.get('date', ''),
                'retained_earnings': r.get('retainedEarnings'),
                'total_equity': r.get('totalStockholdersEquity'),
                'total_debt': total_debt,
                'shares_outstanding': None,  # FMP commonStock은 액면가 → EDGAR로 오버레이
            })
        return result

    fmp_dates_iq = {r['date'] for r in fmp.get('income_quarterly', [])}
    fmp_dates_cq = {r['date'] for r in fmp.get('cashflow_quarterly', [])}
    fmp_dates_ba = {r['date'] for r in fmp.get('balance_annual', [])}

    # EDGAR 분기 손익
    edgar_iq = []
    edgar_rev = {r['date']: r['value'] for r in edgar['income_quarterly'].get('revenue', [])}
    edgar_ni = {r['date']: r['value'] for r in edgar['income_quarterly'].get('net_income', [])}
    edgar_oi = {r['date']: r['value'] for r in edgar['income_quarterly'].get('operating_income', [])}
    edgar_ie = {r['date']: r['value'] for r in edgar['income_quarterly'].get('interest_expense', [])}
    for date in sorted(set(edgar_rev) | set(edgar_ni)):
        if date not in fmp_dates_iq:
            edgar_iq.append({
                'date': date,
                'revenue': edgar_rev.get(date),
                'net_income': edgar_ni.get(date),
                'eps_diluted': None,
                'operating_income': edgar_oi.get(date),
                'interest_expense': edgar_ie.get(date),
            })

    # EDGAR 분기 현금흐름
    edgar_cq = []
    edgar_ocf = {r['date']: r['value'] for r in edgar['cashflow_quarterly'].get('operating_cashflow', [])}
    edgar_cap = {r['date']: r['value'] for r in edgar['cashflow_quarterly'].get('capex', [])}
    edgar_div = {r['date']: r['value'] for r in edgar['cashflow_quarterly'].get('dividends_paid', [])}
    for date in sorted(set(edgar_ocf) | set(edgar_cap)):
        if date not in fmp_dates_cq:
            ocf = edgar_ocf.get(date, 0) or 0
            cap = abs(edgar_cap.get(date, 0) or 0)
            edgar_cq.append({
                'date': date,
                'operating_cashflow': ocf,
                'capex': cap,
                'fcf': ocf - cap,
                'dividends_paid': abs(edgar_div.get(date, 0) or 0),
            })

    # EDGAR 연간 재무상태표
    edgar_ba = []
    edgar_re = {r['date']: r['value'] for r in edgar['balance_annual'].get('retained_earnings', [])}
    edgar_eq = {r['date']: r['value'] for r in edgar['balance_annual'].get('total_equity', [])}
    edgar_sh = {r['date']: r['value'] for r in edgar['balance_annual'].get('shares_outstanding', [])}
    for date in sorted(set(edgar_re) | set(edgar_eq)):
        if date not in fmp_dates_ba:
            edgar_ba.append({
                'date': date,
                'retained_earnings': edgar_re.get(date),
                'total_equity': edgar_eq.get(date),
                'total_debt': None,
                'shares_outstanding': edgar_sh.get(date),
            })

    # FMP 표준화 + EDGAR 병합
    income_q = sorted(fmp_income_to_std(fmp['income_quarterly']) + edgar_iq, key=lambda x: x['date'])
    cashflow_q = sorted(fmp_cashflow_to_std(fmp['cashflow_quarterly']) + edgar_cq, key=lambda x: x['date'])
    balance_a = sorted(fmp_balance_to_std(fmp['balance_annual']) + edgar_ba, key=lambda x: x['date'])

    # EDGAR 주식수 오버레이: FMP commonStock은 액면가이므로 모든 레코드에 EDGAR 값 적용
    # 날짜 기준 nearest 매칭 (연간 데이터는 연도 기준)
    edgar_sh_sorted = sorted(edgar_sh.items())  # [(date, shares), ...]
    if edgar_sh_sorted:
        sh_dates = [d for d, _ in edgar_sh_sorted]
        sh_vals = [v for _, v in edgar_sh_sorted]
        for rec in balance_a:
            if rec.get('shares_outstanding') is None:
                # 가장 가까운 이전 날짜의 EDGAR 값 사용
                year = rec['date'][:4]
                match = next((v for d, v in reversed(edgar_sh_sorted) if d[:4] <= year), sh_vals[0])
                rec['shares_outstanding'] = match

    # 5년차 cross-check (같은 날짜가 양쪽 있으면 FMP 우선으로 이미 처리됨)
    return {
        'income_quarterly': income_q,
        'cashflow_quarterly': cashflow_q,
        'balance_annual': balance_a,
    }


def save_financials(ticker: str) -> dict:
    ticker_dir = os.path.join(STATIC_DIR, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    cik = get_cik(ticker)
    fmp = fetch_fmp_financials(ticker)
    edgar = fetch_edgar_financials(cik)
    merged = merge_financials(fmp, edgar)

    result = {
        'ticker': ticker,
        'cik': cik,
        'updated_at': datetime.today().strftime('%Y-%m-%d'),
        **merged,
    }

    path = os.path.join(ticker_dir, 'financials.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)

    iq = len(result['income_quarterly'])
    cq = len(result['cashflow_quarterly'])
    ba = len(result['balance_annual'])
    print(f"[{ticker}] financials.json 저장 완료 (손익 {iq}건 / 현금흐름 {cq}건 / 재무상태표 {ba}건)")
    return result

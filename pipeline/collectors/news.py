import os
import json
import requests
from datetime import datetime
from pipeline.config import AV_KEY, LIVE_DIR

AV_NEWS_URL = 'https://www.alphavantage.co/query'

# 203 L2-F3 키워드
POSITIVE_KEYWORDS = ['dividend increase', 'dividend raised', 'buyback', 'share repurchase',
                     'cash flow improvement', 'guidance raised', 'earnings beat']
NEGATIVE_KEYWORDS = ['cash conservation', 'capital reallocation', 'liquidity', 'cost cutting',
                     'dividend review', 'dividend suspended', 'dividend cut', 'guidance lowered',
                     'credit downgrade', 'regulatory', 'antitrust', 'windfall tax']
REDFLAG_KEYWORDS = ['dividend policy review', 'dividend suspended', 'dividend eliminated',
                    'dividend cut', 'credit rating downgrade']


def _analyze_sentiment(articles: list) -> dict:
    pos_count = 0
    neg_count = 0
    redflag = False

    for art in articles:
        text = (art.get('title', '') + ' ' + art.get('summary', '')).lower()
        if any(k in text for k in REDFLAG_KEYWORDS):
            redflag = True
        if any(k in text for k in POSITIVE_KEYWORDS):
            pos_count += 1
        if any(k in text for k in NEGATIVE_KEYWORDS):
            neg_count += 1

    if redflag:
        tone = 'REDFLAG'
    elif pos_count > neg_count:
        tone = 'POSITIVE'
    elif neg_count > pos_count:
        tone = 'NEGATIVE'
    else:
        tone = 'NEUTRAL'

    return {'tone': tone, 'positive_count': pos_count, 'negative_count': neg_count, 'redflag': redflag}


def save_news(ticker: str) -> dict:
    os.makedirs(os.path.join(LIVE_DIR, ticker), exist_ok=True)

    res = requests.get(AV_NEWS_URL, params={
        'function': 'NEWS_SENTIMENT',
        'tickers': ticker,
        'limit': 20,
        'apikey': AV_KEY,
    }, timeout=20)
    res.raise_for_status()
    data = res.json()

    articles = []
    for art in data.get('feed', []):
        # 해당 ticker의 sentiment 찾기
        ticker_sentiment = next(
            (s for s in art.get('ticker_sentiment', []) if s.get('ticker') == ticker),
            {}
        )
        articles.append({
            'title': art.get('title', ''),
            'url': art.get('url', ''),
            'time_published': art.get('time_published', ''),
            'source': art.get('source', ''),
            'summary': art.get('summary', ''),
            'overall_sentiment_score': art.get('overall_sentiment_score'),
            'overall_sentiment_label': art.get('overall_sentiment_label', ''),
            'ticker_sentiment_score': ticker_sentiment.get('ticker_sentiment_score'),
            'ticker_sentiment_label': ticker_sentiment.get('ticker_sentiment_label', ''),
            'relevance_score': ticker_sentiment.get('relevance_score'),
        })

    sentiment_analysis = _analyze_sentiment(articles)

    result = {
        'ticker': ticker,
        'updated_at': datetime.today().strftime('%Y-%m-%d'),
        'tone': sentiment_analysis['tone'],
        'positive_count': sentiment_analysis['positive_count'],
        'negative_count': sentiment_analysis['negative_count'],
        'redflag_detected': sentiment_analysis['redflag'],
        'articles': articles,
    }

    path = os.path.join(LIVE_DIR, ticker, 'news.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"[{ticker}] news.json 저장 완료 | {len(articles)}건 | 톤: {sentiment_analysis['tone']}")
    return result

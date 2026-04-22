import os
from dotenv import load_dotenv

load_dotenv()

FMP_KEY = os.getenv('FMP_KEY')
AV_KEY = os.getenv('AV_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'data', 'static')
LIVE_DIR = os.path.join(BASE_DIR, 'data', 'live')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

FMP_BASE = 'https://financialmodelingprep.com/api/v3'
AV_BASE = 'https://www.alphavantage.co/query'

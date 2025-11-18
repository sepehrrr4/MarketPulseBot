import asyncio
import json
import random
import logging
from datetime import datetime, timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

# تنظیمات فایل و لاگ
PRICE_FILE = Path(__file__).parent / "prices.json"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRAPE_INTERVAL = 5.0  # کمی افزایش فاصله برای جلوگیری از بن شدن در کوین‌گکو
ASSETS = ["BTC", "ETH", "BNB", "USDT", "TRX"]
COINMARKETCAP_GOLD = "https://coinmarketcap.com/real-world-assets/gold/"

# هدرهای مرورگر برای جلوگیری از تشخیص ربات
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

async def fetch_from_exchanges(client):
    """تلاش برای دریافت قیمت از صرافی‌های مختلف به ترتیب اولویت"""
    
    # لیست منابع به ترتیب اولویت
    sources = [
        {
            "name": "Binance",
            "url": "https://api.binance.com/api/v3/ticker/price",
            "map": {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT", "TRX": "TRXUSDT", "USDT": "USDCUSDT"},
            "type": "list_symbol_price"
        },
        {
            "name": "Mexc",
            "url": "https://api.mexc.com/api/v3/ticker/price",
            "map": {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT", "TRX": "TRXUSDT", "USDT": "USDCUSDT"},
            "type": "list_symbol_price"
        },
        {
            "name": "LBank",
            "url": "https://api.lbkex.com/v2/ticker/24hr.do",
            "map": {"BTC": "btc_usdt", "ETH": "eth_usdt", "BNB": "bnb_usdt", "TRX": "trx_usdt", "USDT": "usdt_usd"}, # USDT در البانک معمولا جفت ندارد، با ۱ جایگزین میکنیم
            "type": "lbank_structure"
        }
    ]

    prices = {}
    
    for source in sources:
        try:
            resp = await client.get(source["url"], timeout=4.0)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            current_source_prices = {}

            # پردازش داده بسته به ساختار API
            if source["type"] == "list_symbol_price":
                # ساختار بایننس و مکسی: [{'symbol': 'BTCUSDT', 'price': '90000'}]
                market_map = {item['symbol']: float(item['price']) for item in data}
                for asset in ASSETS:
                    pair = source["map"].get(asset)
                    if asset == "USDT": 
                        prices[asset] = 1.0 # تتر همیشه ۱ فرض می‌شود
                    elif pair in market_map:
                        prices[asset] = market_map[pair]

            elif source["type"] == "lbank_structure":
                # ساختار البانک: {'data': [{'symbol': 'btc_usdt', 'ticker': {'latest': '...'}}]}
                if 'data' in data:
                    market_map = {item['symbol']: float(item['ticker']['latest']) for item in data['data']}
                    for asset in ASSETS:
                        pair = source["map"].get(asset)
                        if asset == "USDT": prices[asset] = 1.0
                        elif pair in market_map: prices[asset] = market_map[pair]

            # اگر اکثر قیمت‌ها پیدا شدند، لوپ را می‌شکنیم و برمی‌گردیم
            if len(prices) >= len(ASSETS) - 1:
                logger.info(f"Prices fetched from {source['name']}")
                return prices

        except Exception as e:
            logger.warning(f"Failed to fetch from {source['name']}: {e}")
            continue
            
    return prices

async def fetch_from_coingecko(client):
    """منبع آخر: کوین گکو (اگر همه صرافی‌ها فیلتر بودند)"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,tether,tron&vs_currencies=usd"
    cg_map = {"bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB", "tether": "USDT", "tron": "TRX"}
    prices = {}
    try:
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            for cg_id, asset_code in cg_map.items():
                if cg_id in data:
                    prices[asset_code] = float(data[cg_id]["usd"])
            logger.info("Prices fetched from CoinGecko (Fallback)")
    except Exception as e:
        logger.warning(f"CoinGecko failed: {e}")
    return prices

def extract_gold(html):
    """استخراج قیمت طلا از HTML"""
    try:
        soup = BeautifulSoup(html, "html.parser")
        # روش ۱: سلکتورهای CSS
        tag = soup.select_one("div.priceValue, span[data-test='text-cdp-price-display'], div.sc-142c02c-0.lmjbLF")
        if tag: return tag.text
        
        # روش ۲: پیدا کردن الگوی قیمت در کل متن
        import re
        match = re.search(r"\$\d{1,3}(,\d{3})*(\.\d+)?", html)
        if match: return match.group(0)
    except Exception:
        pass
    return None

def normalize(val):
    if val is None: return None, None
    try:
        if isinstance(val, str):
            # حذف علامت دلار و کاما
            num = float(val.replace('$', '').replace(',', ''))
        else:
            num = float(val)
        return f"${num:,.2f}", num
    except:
        return None, None

async def run_scraper():
    logger.info("Scraper started with Multi-Layer Fallback strategy...")
    while True:
        final_data = {}
        ts = datetime.now(timezone.utc).isoformat()
        
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
            
            # 1. تلاش برای دریافت کریپتو (لایه ۱ و ۲ و ۳)
            crypto_prices = await fetch_from_exchanges(client)
            
            # 2. اگر کریپتو پیدا نشد، تلاش با کوین‌گکو (لایه ۴)
            if not crypto_prices or len(crypto_prices) < 3:
                logger.warning("Exchanges failed, trying CoinGecko...")
                crypto_prices = await fetch_from_coingecko(client)

            # استانداردسازی داده‌های کریپتو
            for asset in ASSETS:
                val = crypto_prices.get(asset)
                p_str, p_num = normalize(val)
                
                if p_str:
                    final_data[asset] = {"price": p_str, "price_num": p_num, "ts": ts}
                    print(f"✅ {asset}: {p_str}")
                else:
                    final_data[asset] = {"price": None, "price_num": None, "ts": ts, "error": "Failed"}
                    print(f"❌ {asset}: Failed")

            # 3. دریافت قیمت طلا (جداگانه)
            try:
                # اضافه کردن پارامتر تصادفی برای دور زدن کش
                url = f"{COINMARKETCAP_GOLD}?t={random.randint(1,99999)}"
                resp = await client.get(url)
                raw_gold = extract_gold(resp.text)
                g_str, g_num = normalize(raw_gold)
                
                if g_str:
                    final_data["GOLD"] = {"price": g_str, "price_num": g_num, "ts": ts}
                    print(f"✅ GOLD: {g_str}")
                else:
                    final_data["GOLD"] = {"price": None, "ts": ts}
            except Exception as e:
                logger.error(f"Gold fetch error: {e}")
                final_data["GOLD"] = {"price": None, "ts": ts}

        # ذخیره در فایل
        try:
            with open(PRICE_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"File save error: {e}")
        
        await asyncio.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    # تنظیم مخصوص ویندوز برای جلوگیری از ارورهای Event Loop
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run_scraper())
    except KeyboardInterrupt:
        print("Scraper stopped.")
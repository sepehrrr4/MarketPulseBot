import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict

# مسیر فایل JSON که توسط scraper.py ساخته می‌شود
PRICE_FILE = Path(__file__).parent / "prices.json"


class Settings(BaseSettings):
    """
    تنظیمات برنامه را مدیریت می‌کند. این مقادیر می‌توانند از طریق متغیرهای محیطی
    (Environment Variables) نیز مقداردهی شوند.
    """
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(arbitrary_types_allowed=True, extra='ignore')


# یک نمونه از تنظیمات ساخته می‌شود تا در کل برنامه استفاده شود
settings = Settings()

# نمونه اصلی برنامه FastAPI
app = FastAPI(
    title="Price API",
    version="2.0",
    description="یک API برای دریافت قیمت لحظه‌ای دارایی‌ها (بیت‌کوین و طلا) از سایت CoinMarketCap",
)


def get_prices_from_file() -> dict:
    """قیمت‌ها را از فایل prices.json می‌خواند."""
    if not PRICE_FILE.exists():
        return {}
    try:
        with open(PRICE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


@app.get("/prices", summary="دریافت آخرین قیمت تمام دارایی‌ها")
async def get_all_prices():
    """آخرین اطلاعات قیمت استخراج شده برای تمام دارایی‌ها را برمی‌گرداند."""
    prices = get_prices_from_file()
    if not prices:
        raise HTTPException(status_code=503, detail="Price data is currently unavailable. The scraper might be running.")
    return prices


@app.get("/price/{asset_name}", summary="دریافت قیمت یک دارایی خاص")
async def get_price(asset_name: str):
    """آخرین اطلاعات قیمت برای یک دارایی مشخص (مانند BTC یا GOLD) را برمی‌گرداند."""
    prices = get_prices_from_file()
    asset_data = prices.get(asset_name.upper())
    if not asset_data:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset_data


@app.get("/health", summary="بررسی وضعیت سلامت سرویس")
async def health_check():
    """یک اندپوینت ساده برای بررسی اینکه آیا سرویس در حال اجراست."""
    prices = get_prices_from_file()
    return {"status": "ok", "tracked_assets": list(prices.keys())}


if __name__ == "__main__":
    """
    این بخش به شما اجازه می‌دهد تا برنامه را مستقیماً با دستور `python main.py` اجرا کنید.
    """
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")
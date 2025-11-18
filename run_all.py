import subprocess
import sys
import time
import logging
from pathlib import Path

# تنظیمات لاگ
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "launcher.log"),
        logging.StreamHandler()
    ]
)

# پیدا کردن مسیر مفسر پایتون
# در محیط‌های مجازی cPanel، استفاده از sys.executable بهترین راه است
PYTHON_EXECUTABLE = sys.executable
BASE_DIR = Path(__file__).parent

def start_process(name, file_path, args=None):
    """یک پروسه جدید را شروع کرده و آن را مانیتور می‌کند."""
    if args is None:
        args = []
    
    command = [PYTHON_EXECUTABLE, str(file_path)] + args
    log_file_path = LOG_DIR / f"{name}.log"
    
    try:
        logging.info(f"Starting {name}...")
        # باز کردن فایل لاگ در حالت append
        log_file = open(log_file_path, "a", encoding="utf-8")
        
        # اجرای دستور و هدایت stdout و stderr به فایل لاگ
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=log_file,
            cwd=BASE_DIR,
            text=True,
            encoding='utf-8'
        )
        logging.info(f"{name} started successfully with PID: {process.pid}. Logging to {log_file_path}")
        return process, log_file
    except FileNotFoundError:
        logging.error(f"Error: Could not find {PYTHON_EXECUTABLE}. Make sure you are in a virtual environment.")
        return None, None
    except Exception as e:
        logging.error(f"Failed to start {name}: {e}")
        return None, None

def main():
    """
    سرویس‌های اصلی برنامه (API, Scraper, Bot) را به صورت موازی اجرا می‌کند.
    """
    logging.info("=============================================")
    logging.info("Starting all services in parallel...")
    logging.info(f"Using Python interpreter: {PYTHON_EXECUTABLE}")
    logging.info("=============================================")

    processes = {}
    log_files = {}

    # لیست سرویس‌ها برای اجرا
    # Uvicorn از داخل main.py اجرا می‌شود و نیازی به آرگومان جدا ندارد
    services = {
        "uvicorn": (BASE_DIR / "main.py", []),
        "scraper": (BASE_DIR / "scraper.py", []),
        "bot": (BASE_DIR / "bot.py", []),
    }

    try:
        for name, (path, args) in services.items():
            if not path.exists():
                logging.error(f"File not found for service '{name}': {path}")
                continue
            
            proc, log_file = start_process(name, path, args)
            if proc:
                processes[name] = proc
                log_files[name] = log_file
            time.sleep(2) # فاصله کوتاه بین اجرای سرویس‌ها

        if not processes:
            logging.critical("No services were started. Exiting.")
            return

        logging.info("All services are running. Monitoring for termination...")
        
        # منتظر بمان تا کاربر برنامه را متوقف کند (Ctrl+C)
        while True:
            for name, proc in processes.items():
                if proc.poll() is not None:
                    logging.warning(f"Service '{name}' has terminated unexpectedly with exit code {proc.returncode}.")
                    # اینجا می‌توان منطق راه‌اندازی مجدد را اضافه کرد
            time.sleep(10)

    except KeyboardInterrupt:
        logging.info("\nShutdown signal received. Terminating all services...")
    finally:
        for name, proc in processes.items():
            logging.info(f"Stopping {name} (PID: {proc.pid})...")
            proc.terminate() # ارسال سیگنال خاتمه
            try:
                proc.wait(timeout=5) # 5 ثانیه برای خاتمه منتظر بمان
                logging.info(f"{name} stopped.")
            except subprocess.TimeoutExpired:
                logging.warning(f"{name} did not terminate gracefully. Forcing shutdown...")
                proc.kill() # اگر خاتمه نیافت، آن را مجبور به توقف کن
                logging.warning(f"{name} killed.")
        
        # بستن فایل‌های لاگ
        for name, log_file in log_files.items():
            if log_file:
                log_file.close()
        
        logging.info("All services have been shut down. Exiting.")

if __name__ == "__main__":
    main()

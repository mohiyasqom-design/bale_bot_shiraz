print("""
╔══════════════════════════════════════════════════════════════╗
║         کدبات - ربات مدیریت کامل بله                        ║
║         نسخه: 4.0 (fixed)                                   ║
║         زبان: Python 3.10+                                  ║
╚══════════════════════════════════════════════════════════════╝
""")

import requests
import time
import sqlite3
import os
import sys
import json
import hashlib
import random
import string
import subprocess
import threading
import logging
import traceback
import zipfile
import shutil
import ast
import re
import importlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

# ─────────────────────────────────────────────
#  تابع تبدیل تاریخ به فارسی
# ─────────────────────────────────────────────
PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]

PERSIAN_WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]

def gregorian_to_jalali(gy, gm, gd):
    """تبدیل تاریخ میلادی به خورشیدی (فرمت: YYYY, MM, DD)"""
    g_d_n = 365 * gy + ((gy + 3) // 4) - ((gy + 99) // 100) + ((gy + 399) // 400)
    
    for i in range(1, gm):
        if i in (1, 3, 5, 7, 8, 10, 12):
            g_d_n += 31
        elif i in (4, 6, 9, 11):
            g_d_n += 30
        else:  # فوریه
            g_d_n += 29 if (gy % 400 == 0) or (gy % 4 == 0 and gy % 100 != 0) else 28
    
    g_d_n += gd
    
    j_d_n = g_d_n - 79
    j_np = j_d_n // 146097
    j_d_n = j_d_n % 146097
    
    leap = 1 if j_d_n >= 36525 else 0
    if j_d_n >= 36525:
        j_d_n -= 36525
        leap = 1 if j_d_n >= 36524 else 0
    
    jy = 400 * j_np + 100 * leap + 4 * (j_d_n // 1461)
    j_d_n %= 1461
    
    if j_d_n >= 365:
        leap = 1 if j_d_n >= 366 else 0
        if j_d_n >= 366:
            j_d_n -= 366
        else:
            j_d_n -= 365
        jy += leap + j_d_n // 365
        j_d_n = j_d_n % 365
    
    jy += 1
    
    jm = 1 if j_d_n < 186 else 7
    if j_d_n < 186:
        jd = (j_d_n // 31) + 1
        jm = (j_d_n % 31) + 1
        if jm > 31:
            jm = 1
            jd += 1
    else:
        jd = ((j_d_n - 186) // 30) + 1
        jm = ((j_d_n - 186) % 30) + 1
        if jm > 30:
            jm = 1
            jd += 1
        jm += 6
    
    return jy, jm, jd

def format_persian_datetime(dt: datetime) -> str:
    """تبدیل datetime به فرمت فارسی: روز ماه سال - ساعت:دقیقه"""
    try:
        jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
        weekday = PERSIAN_WEEKDAYS[dt.weekday()]
        month = PERSIAN_MONTHS[jm - 1] if 1 <= jm <= 12 else "نامعلوم"
        return f"{weekday} {jd} {month} {jy} - {dt.strftime('%H:%M:%S')}"
    except:
        return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_persian_date(dt: datetime) -> str:
    """تبدیل datetime به فرمت فارسی فقط تاریخ: روز ماه سال"""
    try:
        jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
        month = PERSIAN_MONTHS[jm - 1] if 1 <= jm <= 12 else "نامعلوم"
        return f"{jd} {month} {jy}"
    except:
        return dt.strftime('%Y-%m-%d')


#  پیکربندی اصلی
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
#  پیکربندی اصلی و متغیرهای محیطی برای ریلوای
# ─────────────────────────────────────────────
TOKEN = os.getenv("BOT_TOKEN")  
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "2063033830").split(",")]
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "WALLET-TEST-1111111111111111")
CHANNEL_USERNAME = "@koddan"
INVITE_BASE = "https://ble.ir/kodbot?start="
REQUIRED_INVITES = 1

DEFAULT_HELP_GUIDE = (
    "❓ *راهنمای کدبات*\n\n"
    "با کدبات می‌توانید ربات پایتونی خود را روی سرور مستقر (دیپلوی) کنید،\n"
    "کتابخانه نصب کنید، و از دستیار کد و ابزارهای هوش مصنوعی استفاده کنید.\n\n"
    "برای شروع، از منوی *دستیار کد* گزینه *استقرار جدید* را انتخاب کنید.\n"
    "در صورت هرگونه سوال، از دکمه *ارتباط با ادمین* استفاده کنید."
)

# ─────────────────────────────────────────────
#  میرورهای ایران برای نصب کتابخانه
# ─────────────────────────────────────────────
IRAN_MIRRORS = [
    {"name": "ArvanCloud", "url": "https://mirror.arvancloud.ir/pypi/simple/"},
    {"name": "MobinHost", "url": "https://mirror.mobinhost.com/pypi/simple/"},
    {"name": "Shatel", "url": "https://mirror.shatel.ir/pypi/"},
    {"name": "CDN.ir", "url": "https://mirror.cdn.ir/repository/pypi/simple/"},
    {"name": "Liara", "url": "https://liara.ir/mirrors/pypi/simple/"},
    {"name": "IranServer", "url": "https://mirror.iranserver.com/pypi/simple/"},
    {"name": "Chabokan", "url": "https://mirror.chabokan.net/pypi/simple/"},
    {"name": "Chabokan2", "url": "https://mirror2.chabokan.net/pypi/simple/"},
    {"name": "Parsdev", "url": "https://mirror.parsdev.com/pypi/simple/"},
    {"name": "Abrha", "url": "https://repo.abrha.net/pypi/simple/"},
    {"name": "AtlantisCloud", "url": "https://mirror.atlantiscloud.ir/pypi/simple/"},
    {"name": "Faraso", "url": "https://mirror.faraso.org/pypi/simple/"},
    {"name": "Rasanegaar", "url": "https://mirror.rasanegaar.com/pypi/simple/"},
    {"name": "KubarCloud", "url": "https://mirrors.kubarcloud.com/pypi/simple/"},
    {"name": "Pardisco", "url": "https://mirrors.pardisco.co/pypi/simple/"},
    {"name": "HyperClouds", "url": "https://mirrors.hyperclouds.ir/pypi/simple/"},
    {"name": "AminiDC", "url": "https://mirror.aminidc.com/pypi/simple/"},
    {"name": "ITO", "url": "https://repo.ito.gov.ir/pypi/simple/"},
    {"name": "IUT", "url": "https://repo.iut.ac.ir/pypi/simple/"},
    {"name": "HamDocker", "url": "https://hub.hamdocker.ir/pypi/simple/"},
]

# ─────────────────────────────────────────────
#  تنظیم مسیرها بر اساس دیسک پایدار ریلوای (/app/data)
# ─────────────────────────────────────────────
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
try:
    DATA_DIR.mkdir(exist_ok=True, parents=True)
except PermissionError:
    DATA_DIR = Path("/mnt/data/kodbot_runtime")
    DATA_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = str(DATA_DIR / "kodbot.db")
BOTS_DIR = DATA_DIR / "deployed_bots"
LOGS_DIR = DATA_DIR / "bot_logs"
LIBS_DIR = DATA_DIR / "custom_libs"

BOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
LIBS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
#  ماژول‌های استاندارد پایتون (برای تشخیص کتابخانه‌های خارجی)
# ─────────────────────────────────────────────
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'csv', 'ctypes',
    'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
    'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
    'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'fractions', 'ftplib', 'functools',
    'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib',
    'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'imp',
    'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'marshal',
    'math', 'mimetypes', 'mmap', 'modulefinder', 'multiprocessing', 'netrc',
    'nntplib', 'numbers', 'operator', 'optparse', 'os', 'pathlib', 'pdb',
    'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib',
    'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats', 'pty',
    'pwd', 'py_compile', 'pydoc', 'queue', 'quopri', 'random', 're',
    'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched',
    'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
    'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
    'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
    'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog',
    'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'textwrap',
    'threading', 'time', 'timeit', 'token', 'tokenize', 'trace', 'traceback',
    'tracemalloc', 'tty', 'types', 'typing', 'unicodedata', 'unittest',
    'urllib', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
    'wsgiref', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
    '_thread', '__future__', 'zoneinfo', 'tomllib',
}

# ─────────────────────────────────────────────
#  تنظیمات لاگر
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("KodBot")

# ─────────────────────────────────────────────
#  سطوح کاربری و محدودیت‌ها (بهبود‌شده)
# ─────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "🟢 رایگان",
        # ربات‌ها
        "max_bots": 1,
        "max_code_lines": 50,
        "max_memory_mb": 50,
        "max_libraries": 1,
        # وب دستیار
        "max_web_projects": 0,
        "web_assistant": False,
        # لاگ و پشتیبانی
        "log_retention_days": 1,
        "support_level": "معمولی",
        "max_support_tickets": 2,
        # درایو و بند‌پهنا
        "monthly_bandwidth_gb": 1,
        "max_concurrent_connections": 2,
        # uptime و قابلیت‌ها
        "bot_uptime_hours": 240,
        "auto_recovery": False,
        "powerful_terminal": False,
        "custom_library": False,
        "personal_mirror": False,
        "processing_priority": "low",
        # درآمد
        "max_discount_codes": 0,
        "subscriptions": {
            "monthly": {"price": 0, "gift_points": 10, "max_buy": 1}
        }
    },
    "basic": {
        "name": "🔵 پایه",
        # ربات‌ها
        "max_bots": 3,
        "max_code_lines": 500,
        "max_memory_mb": 150,
        "max_libraries": 10,
        # وب دستیار
        "max_web_projects": 3,
        "web_assistant": True,
        # لاگ و پشتیبانی
        "log_retention_days": 7,
        "support_level": "سریع",
        "max_support_tickets": 10,
        # درایو و بند‌پهنا
        "monthly_bandwidth_gb": 10,
        "max_concurrent_connections": 5,
        # uptime و قابلیت‌ها
        "bot_uptime_hours": 720,
        "auto_recovery": True,
        "powerful_terminal": True,
        "custom_library": True,
        "personal_mirror": True,
        "processing_priority": "normal",
        # درآمد
        "max_discount_codes": 5,
        "subscriptions": {
            "monthly": {"price": 50000, "gift_points": 120, "max_buy": 12},
            "yearly": {"price": 600000, "gift_points": 1500, "max_buy": 1}
        }
    },
    "professional": {
        "name": "🔴 حرفه‌ای",
        # ربات‌ها
        "max_bots": 10,
        "max_code_lines": 999999,
        "max_memory_mb": 500,
        "max_libraries": 999,
        # وب دستیار
        "max_web_projects": 999,
        "web_assistant": True,
        # لاگ و پشتیبانی
        "log_retention_days": 30,
        "support_level": "فوری",
        "max_support_tickets": 999,
        # درایو و بند‌پهنا
        "monthly_bandwidth_gb": 100,
        "max_concurrent_connections": 20,
        # uptime و قابلیت‌ها
        "bot_uptime_hours": 999,
        "auto_recovery": True,
        "powerful_terminal": True,
        "custom_library": True,
        "personal_mirror": True,
        "processing_priority": "high",
        # درآمد
        "max_discount_codes": 999,
        "subscriptions": {
            "monthly": {"price": 200000, "gift_points": 500, "max_buy": 12},
            "yearly": {"price": 2400000, "gift_points": 6000, "max_buy": 1}
        }
    },
    "enterprise": {
        "name": "⚫ سازمانی",
        "max_bots": 999,
        "max_code_lines": 999999,
        "max_memory_mb": 2048,
        "max_libraries": 999,
        "max_web_projects": 999,
        "web_assistant": True,
        "log_retention_days": 365,
        "support_level": "اختصاصی",
        "max_support_tickets": 999,
        "monthly_bandwidth_gb": 1000,
        "max_concurrent_connections": 100,
        "bot_uptime_hours": 999,
        "auto_recovery": True,
        "powerful_terminal": True,
        "custom_library": True,
        "personal_mirror": True,
        "processing_priority": "highest",
        "max_discount_codes": 999,
        "subscriptions": {}
    }
}

SHOP_ITEMS = {
    "extra_bot": {
        "name": "🤖 ربات اضافه",
        "desc": "افزایش سقف تعداد ربات‌ها",
        "points": {"free": None, "basic": 25, "professional": 15, "enterprise": 10}
    },
    "extra_memory": {
        "name": "💾 حافظه اضافی",
        "desc": "۱۰۰ مگابایت حافظه",
        "points": {"free": None, "basic": 15, "professional": 10, "enterprise": 5}
    },
    "extra_log": {
        "name": "📋 لاگ اضافی",
        "desc": "۷ روز لاگ اضافی",
        "points": {"free": None, "basic": 10, "professional": 7, "enterprise": 3}
    },
    "extra_library": {
        "name": "📦 کتابخانه اضافی",
        "desc": "افزایش سقف کتابخانه‌ها",
        "points": {"free": None, "basic": 8, "professional": 5, "enterprise": 2}
    },
    "extra_bandwidth": {
        "name": "🌐 بند‌پهنا اضافی",
        "desc": "۱ گیگابایت بند‌پهنا",
        "points": {"free": None, "basic": 20, "professional": 12, "enterprise": 5}
    }
}

# ─────────────────────────────────────────────
#  دیتابیس
# ─────────────────────────────────────────────


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # جلوگیری از lock در multi-thread
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_user(user_id: int) -> Optional[Dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def upsert_user(user_id: int, username: str = None, full_name: str = None):
    now = datetime.now().isoformat()
    with get_db() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET username=?, full_name=?, last_active=? WHERE user_id=?",
                (username, full_name, now, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO users (user_id, username, full_name, joined_at, last_active) VALUES (?,?,?,?,?)",
                (user_id, username, full_name, now, now)
            )
        conn.commit()


def get_setting(key: str, default=None):
    try:
        with get_db() as conn:
            row = conn.execute("SELECT value FROM admin_settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS admin_settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.execute(
            "INSERT INTO admin_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()


# ─────────────────────────────────────────────
#  توابع API بله
# ─────────────────────────────────────────────
def api(method: str, data: dict = None, files=None) -> dict:
    url = f"{BASE_URL}/{method}"
    try:
        if files:
            r = requests.post(url, data=data, files=files, timeout=30)
        else:
            r = requests.post(url, json=data, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"API Error [{method}]: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown",
                 reply_to_message_id=None, disable_web_page_preview=True):
    d = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview
    }
    if reply_markup:
        d["reply_markup"] = reply_markup
    if reply_to_message_id:
        d["reply_to_message_id"] = reply_to_message_id
    return api("sendMessage", d)


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
    d = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        d["reply_markup"] = reply_markup
    return api("editMessageText", d)


def answer_callback(callback_id, text="", alert=False):
    return api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": alert
    })


def send_document(chat_id, file_path, caption="", reply_to=None):
    with open(file_path, "rb") as f:
        d = {"chat_id": chat_id, "caption": caption}
        if reply_to:
            d["reply_to_message_id"] = reply_to
        return api("sendDocument", d, files={"document": f})


def send_photo(chat_id, file_path, caption=""):
    with open(file_path, "rb") as f:
        return api("sendPhoto", {"chat_id": chat_id, "caption": caption}, files={"photo": f})


def send_invoice(chat_id, title, description, payload, prices, photo_url=None, reply_to=None):
    global PAYMENT_TOKEN
    pt = get_setting("payment_token", PAYMENT_TOKEN)
    d = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": pt,
        "currency": "IRR",
        "prices": prices
    }
    if photo_url:
        d["photo_url"] = photo_url
    if reply_to:
        d["reply_to_message_id"] = reply_to
    return api("sendInvoice", d)


def get_updates(offset=0, timeout=30):
    r = requests.get(
        f"{BASE_URL}/getUpdates",
        params={"offset": offset, "timeout": timeout},
        timeout=timeout + 5
    )
    return r.json()


def delete_message(chat_id, message_id):
    return api("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def send_broadcast(text, parse_mode="Markdown"):
    with get_db() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()

    counter = {"ok": 0, "fail": 0}
    counter_lock = threading.Lock()
    semaphore = threading.Semaphore(20)  # حداکثر 20 ارسال همزمان

    def send_to_user(uid):
        with semaphore:
            try:
                res = send_message(uid, text, parse_mode=parse_mode)
                with counter_lock:
                    if res.get("ok"):
                        counter["ok"] += 1
                    else:
                        counter["fail"] += 1
            except Exception:
                with counter_lock:
                    counter["fail"] += 1
            time.sleep(0.05)

    threads = [threading.Thread(target=send_to_user, args=(u["user_id"],), daemon=True)
               for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return counter["ok"], counter["fail"]


# ─────────────────────────────────────────────
#  کیبوردهای inline
# ─────────────────────────────────────────────
def inline_keyboard(buttons: list) -> dict:
    """
    buttons = [[(\"متن\", \"callback_data\"), ...], ...]
    یا برای URL: [(\"متن\", \"url\", \"https://...\")]
    """
    keyboard = []
    for row in buttons:
        r = []
        for btn in row:
            if len(btn) == 3 and btn[1] == "url":
                r.append({"text": btn[0], "url": btn[2]})
            else:
                r.append({"text": btn[0], "callback_data": btn[1]})
        keyboard.append(r)
    return {"inline_keyboard": keyboard}


def glass_keyboard(items: list, prefix: str, cols: int = 2) -> dict:
    """ساخت کیبورد شیشه‌ای از لیست آیتم‌ها"""
    rows = []
    row = []
    for i, item in enumerate(items):
        row.append((item["label"], f"{prefix}:{item['id']}"))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return inline_keyboard(rows)


# ─────────────────────────────────────────────
#  وضعیت کاربران (FSM - ذخیره در دیتابیس)
# ─────────────────────────────────────────────

def set_state(user_id: int, state: str, data: dict = None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_states (user_id, state, data, updated_at) VALUES (?,?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, data=excluded.data, updated_at=excluded.updated_at",
            (user_id, state, json.dumps(data or {}, ensure_ascii=False), datetime.now().isoformat())
        )
        conn.commit()


def get_state(user_id: int) -> Dict:
    with get_db() as conn:
        row = conn.execute("SELECT state, data FROM user_states WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return {"state": row["state"], "data": json.loads(row["data"])}
        return {"state": None, "data": {}}


def clear_state(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM user_states WHERE user_id=?", (user_id,))
        conn.commit()


# ─────────────────────────────────────────────
#  بررسی مجوزها و پلن
# ─────────────────────────────────────────────


def check_plan_limit(user_id: int, resource: str) -> tuple:
    """بررسی آیا کاربر به محدودیت رسیده"""
    u = get_user(user_id)
    if not u:
        return False, "کاربر یافت نشد"
    plan = PLANS.get(u["plan"], PLANS["free"])

    if resource == "bots":
        max_val = plan["max_bots"]
        if max_val != -1:
            max_val += u.get("extra_bots", 0)
        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as c FROM deployed_bots WHERE user_id=? AND status='running'",
                (user_id,)
            ).fetchone()["c"]
        if max_val != -1 and count >= max_val:
            return False, f"به حداکثر تعداد ربات ({max_val}) رسیده‌اید"
        return True, count

    if resource == "libraries":
        max_val = plan["max_libraries"]
        if max_val != -1:
            max_val += u.get("extra_libraries", 0)
        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as c FROM library_installs WHERE user_id=? AND status='installed'",
                (user_id,)
            ).fetchone()["c"]
        if max_val != -1 and count >= max_val:
            return False, f"به حداکثر تعداد کتابخانه ({max_val}) رسیده‌اید"
        return True, count

    return True, None


def get_effective_plan(user_id: int) -> dict:
    u = get_user(user_id)
    if not u:
        return PLANS["free"]
    return PLANS.get(u["plan"], PLANS["free"])


# ─────────────────────────────────────────────
#  سیستم امتیاز
# ─────────────────────────────────────────────
def add_points(user_id: int, amount: int, reason: str = ""):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET points = points + ? WHERE user_id=?",
            (amount, user_id)
        )
        conn.commit()
    log.info(f"امتیاز {amount} به {user_id} داده شد: {reason}")


def get_points(user_id: int) -> int:
    u = get_user(user_id)
    return u["points"] if u else 0


def spend_points(user_id: int, amount: int) -> bool:
    u = get_user(user_id)
    if not u or u["points"] < amount:
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET points = points - ? WHERE user_id=?",
            (amount, user_id)
        )
        conn.commit()
    return True


# ─────────────────────────────────────────────
#  سیستم دعوت و فعال‌سازی
# ─────────────────────────────────────────────
def get_invite_link(user_id: int) -> str:
    return f"{INVITE_BASE}{user_id}"


_invite_lock = threading.Lock()


def process_invite(new_user_id: int, inviter_id: int):
    """پردازش دعوت جدید"""
    with _invite_lock:
        with get_db() as conn:
            u = conn.execute("SELECT invited_by FROM users WHERE user_id=?", (new_user_id,)).fetchone()
            if u and u["invited_by"]:
                return  # قبلاً دعوت شده

            conn.execute(
                "UPDATE users SET invited_by=? WHERE user_id=?",
                (inviter_id, new_user_id)
            )
            conn.execute(
                "UPDATE users SET invite_count = invite_count + 1 WHERE user_id=?",
                (inviter_id,)
            )
            conn.commit()

            # بررسی آیا دعوت‌کننده به ۵ دعوت رسیده
            inviter = conn.execute("SELECT * FROM users WHERE user_id=?", (inviter_id,)).fetchone()
            if inviter and inviter["invite_count"] >= REQUIRED_INVITES and not inviter["is_active"] and inviter["channel_joined"]:
                activate_user(inviter_id)

        # امتیاز فقط یک‌بار داده می‌شود (بیرون از if/else)
        add_points(inviter_id, 5, "دعوت موفق")


def activate_user(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_active=1 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()
    send_message(user_id, "🎉 *تبریک!* ربات برای شما فعال شد!\nاکنون می‌توانید از تمام امکانات استفاده کنید.")


# ─────────────────────────────────────────────
#  منوی اصلی
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  هندلر /start
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  هندلر مدیریت ربات‌ها
# ─────────────────────────────────────────────
def handle_bots_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        bots = conn.execute(
            "SELECT * FROM deployed_bots WHERE user_id=? ORDER BY id DESC",
            (user_id,)
        ).fetchall()

    if not bots:
        edit_message(
            chat_id, msg_id,
            "🤖 *ربات‌های شما*\n\nهنوز هیچ ربات مستقری ندارید.",
            reply_markup=inline_keyboard([
                [("🚀 استقرار", "deploy_new")],
                [("🔙 بازگشت", "main_menu")]
            ])
        )
        return

    items = [{"label": f"{'🟢' if b['status']=='running' else '🔴'} {b['bot_name']}", "id": b["id"]} for b in bots]
    kb = glass_keyboard(items, "bot_info", cols=2)
    kb["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "main_menu"}])

    edit_message(
        chat_id, msg_id,
        f"🤖 *ربات‌های شما* ({len(bots)} ربات)\n\nروی نام ربات بزنید:",
        reply_markup=kb
    )


def handle_bot_info(query: dict, bot_id: int):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        bot = conn.execute(
            "SELECT * FROM deployed_bots WHERE id=? AND user_id=?",
            (bot_id, user_id)
        ).fetchone()

    if not bot:
        answer_callback(query["id"], "ربات یافت نشد!", True)
        return

    status_map = {
        "running": "🟢 در حال اجرا",
        "stopped": "🔴 متوقف",
        "pending": "🟡 در انتظار تایید",
        "rejected": "❌ رد شده"
    }
    status = status_map.get(bot["status"], bot["status"])

    edit_message(
        chat_id, msg_id,
        f"🤖 *{bot['bot_name']}*\n\n"
        f"وضعیت: {status}\n"
        f"مستقر شده: {bot['deployed_at'] or 'هنوز نه'}\n"
        f"فایل: `{Path(bot['file_path']).name if bot['file_path'] else 'ندارد'}`",
        reply_markup=inline_keyboard([
            [("🗑 حذف ربات", f"delete_bot_confirm:{bot_id}")],
            [("📋 مشاهده لاگ", f"view_log:{bot_id}"), ("⏹ توقف", f"stop_bot:{bot_id}")],
            [("▶️ راه‌اندازی مجدد", f"restart_bot:{bot_id}")],
            [("🔙 لیست ربات‌ها", "bots_menu")]
        ])
    )


def handle_delete_bot_confirm(query: dict, bot_id: int):
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        bot = conn.execute("SELECT bot_name FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
    name = bot["bot_name"] if bot else "ربات"

    edit_message(
        chat_id, msg_id,
        f"⚠️ *آیا مطمئن هستید؟*\n\nمی‌خواهید ربات *{name}* را حذف کنید؟\nاین عمل برگشت‌پذیر نیست!",
        reply_markup=inline_keyboard([
            [("✅ بله، حذف شود", f"delete_bot_final:{bot_id}")],
            [("❌ خیر، انصراف", f"bot_info:{bot_id}")]
        ])
    )


def handle_delete_bot_final(query: dict, bot_id: int):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        bot = conn.execute(
            "SELECT * FROM deployed_bots WHERE id=? AND user_id=?",
            (bot_id, user_id)
        ).fetchone()

    if not bot:
        answer_callback(query["id"], "ربات یافت نشد!", True)
        return

    # توقف پروسه
    if bot["pid"]:
        try:
            os.kill(bot["pid"], 9)
        except:
            pass

    # حذف فایل‌ها
    if bot["file_path"] and os.path.exists(bot["file_path"]):
        try:
            os.remove(bot["file_path"])
        except:
            pass

    with get_db() as conn:
        conn.execute("DELETE FROM deployed_bots WHERE id=?", (bot_id,))
        conn.commit()

    edit_message(
        chat_id, msg_id,
        f"✅ ربات *{bot['bot_name']}* با موفقیت حذف شد.",
        reply_markup=inline_keyboard([[("🔙 لیست ربات‌ها", "bots_menu")]])
    )


# ─────────────────────────────────────────────
#  استقرار ربات جدید
# ─────────────────────────────────────────────
def handle_deploy_new(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    ok, reason = check_plan_limit(user_id, "bots")
    if not ok:
        edit_message(
            chat_id, msg_id,
            f"❌ *محدودیت پلن*\n\n{reason}\n\nبرای افزایش سقف، آیتم «ربات اضافه» بخرید یا پلن ارتقا دهید.",
            reply_markup=inline_keyboard([
                [("🏪 فروشگاه آیتم", "shop_menu"), ("💳 ارتقای پلن", "sub_menu")],
                [("🔙 بازگشت", "main_menu")]
            ])
        )
        return

    set_state(user_id, "deploy_waiting_name")
    edit_message(
        chat_id, msg_id,
        "🚀 *استقرار ربات جدید*\n\n*مرحله ۱/۳:* نام ربات خود را ارسال کنید.\n\n"
        "مثال: `MyAwesomeBot`",
        reply_markup=inline_keyboard([[("❌ انصراف", "main_menu")]])
    )


def handle_deploy_name(message: dict):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    bot_name = message.get("text", "").strip()

    if not bot_name or len(bot_name) < 2:
        send_message(chat_id, "❌ نام ربات معتبر نیست. دوباره وارد کنید:")
        return

    set_state(user_id, "deploy_file", {"bot_name": bot_name})
    send_message(
        chat_id,
        f"✅ نام ربات: *{bot_name}*\n\n"
        f"*مرحله ۲/۳:* حالا فایل پایتون ربات (`.py`) را ارسال کنید.\n\n"
        f"می‌توانید کنار فایل پایتون، فایل‌های دیگر نیز ارسال کنید.",
        reply_markup=inline_keyboard([[("❌ انصراف", "main_menu")]])
    )


def handle_deploy_file(message: dict):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    state = get_state(user_id)

    document = message.get("document")
    if not document:
        send_message(chat_id, "❌ لطفاً یک فایل ارسال کنید.")
        return

    file_name = document.get("file_name", "")
    bot_name = state["data"].get("bot_name", "unknown_bot")

    # دانلود فایل
    file_id = document["file_id"]
    file_info = api("getFile", {"file_id": file_id})
    if not file_info.get("ok"):
        send_message(chat_id, "❌ خطا در دریافت فایل.")
        return

    file_path_remote = file_info["result"]["file_path"]
    download_url = f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path_remote}"
    r = requests.get(download_url)

    # ذخیره فایل
    bot_dir = BOTS_DIR / f"{user_id}_{bot_name}"
    bot_dir.mkdir(exist_ok=True)

    local_path = bot_dir / file_name
    with open(local_path, "wb") as f:
        f.write(r.content)

    if file_name.endswith(".py"):
        # بررسی امنیتی: جلوگیری از مسیرهای سرور قدیم
        try:
            with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                code_content = f.read()
                lines = code_content.splitlines()
        except Exception:
            lines = []
            code_content = ""
        
        # ⛔ بررسی مسیر "codebat" یا "/app/data" یا "/mnt/data"
        if "/app/data" in code_content or "/mnt/data" in code_content:
            send_message(
                chat_id,
                "❌ *کد مشکل امنیتی دارد.*\n\n"
                "کد شما شامل مسیرهای سرور قدیم است.\n"
                "لطفاً کد خود را بروزرسانی کنید و دوباره ارسال کنید."
            )
            shutil.rmtree(bot_dir)
            return

        # بررسی تعداد خطوط کد
        u = get_user(user_id)
        plan = PLANS.get(u["plan"] if u else "free", PLANS["free"])
        max_lines = plan["max_code_lines"]
        if max_lines != -1 and len(lines) > max_lines:
            send_message(
                chat_id,
                f"❌ فایل شما *{len(lines)} خط* دارد.\n"
                f"محدودیت پلن شما: *{max_lines} خط*\n\n"
                f"برای پلن بالاتر یا خط کد اضافی اقدام کنید."
            )
            shutil.rmtree(bot_dir)
            return

        set_state(user_id, "deploy_confirm", {
            "bot_name": bot_name,
            "file_path": str(local_path),
            "extra_files": [],
            "bot_dir": str(bot_dir)
        })

        send_message(
            chat_id,
            f"✅ فایل دریافت شد!\n\n"
            f"*مرحله ۳/۳:* آیا می‌خواهید فایل‌های دیگری اضافه کنید؟\n"
            f"(مثلاً فایل config، requirements.txt و ...)\n\n"
            f"اگر نه، روی «ارسال درخواست» بزنید:",
            reply_markup=inline_keyboard([
                [("📤 درخواست", "deploy_submit")],
                [("❌ انصراف", "main_menu")]
            ])
        )
    else:
        # فایل اضافی
        current_state = get_state(user_id)
        extra_files = current_state["data"].get("extra_files", [])
        extra_files.append(str(local_path))
        new_data = current_state["data"].copy()
        new_data["extra_files"] = extra_files
        set_state(user_id, current_state["state"], new_data)
        send_message(
            chat_id,
            f"✅ فایل *{file_name}* اضافه شد.\nمی‌توانید فایل بیشتری ارسال کنید یا درخواست را ثبت کنید:",
            reply_markup=inline_keyboard([
                [("📤 درخواست", "deploy_submit")],
                [("❌ انصراف", "main_menu")]
            ])
        )


def handle_deploy_submit(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    state = get_state(user_id)

    if state["state"] not in ("deploy_confirm", "deploy_file"):
        answer_callback(query["id"], "وضعیت نامعتبر!", True)
        return

    data = state["data"]
    bot_name = data.get("bot_name", "نامشخص")
    file_path = data.get("file_path", "")

    if not file_path:
        answer_callback(query["id"], "ابتدا فایل پایتون ارسال کنید!", True)
        return

    tracking_code = "DEP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO deployed_bots (user_id, bot_name, file_path, extra_files, status) VALUES (?,?,?,?,?)",
            (user_id, bot_name, file_path, json.dumps(data.get("extra_files", [])), "pending")
        )
        bot_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

        # ذخیره درخواست
        conn.execute(
            "INSERT INTO pending_requests (type, user_id, data, created_at) VALUES (?,?,?,?)",
            ("deploy", user_id, json.dumps({"bot_id": bot_id, "bot_name": bot_name, "tracking": tracking_code}), datetime.now().isoformat())
        )
        req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    # ارسال به مدیران
    u = get_user(user_id)
    for admin_id in ADMIN_IDS:
        res = send_message(
            admin_id,
            f"📬 *درخواست استقرار ربات جدید*\n\n"
            f"👤 کاربر: {u['full_name'] if u else user_id} (`{user_id}`)\n"
            f"🤖 نام ربات: *{bot_name}*\n"
            f"🔖 کد پیگیری: `{tracking_code}`\n"
            f"📁 فایل: `{Path(file_path).name}`\n\n"
            f"⚠️ فایل ربات پیوست است. لطفاً بررسی کنید:",
            reply_markup=inline_keyboard([
                [("✅ تایید", f"admin_approve_deploy:{req_id}"), ("❌ رد", f"admin_reject_deploy:{req_id}")]
            ])
        )
        if res.get("ok"):
            with get_db() as conn:
                conn.execute(
                    "UPDATE pending_requests SET admin_msg_id=? WHERE id=?",
                    (res["result"]["message_id"], req_id)
                )
                conn.commit()
        # ارسال فایل اصلی ربات به مدیر برای بررسی
        if os.path.exists(file_path):
            send_document(admin_id, file_path,
                          f"📄 فایل ربات *{bot_name}* از کاربر `{user_id}` برای بررسی")
        # ارسال فایل‌های اضافی نیز در صورت وجود
        for extra in data.get("extra_files", []):
            if os.path.exists(extra):
                send_document(admin_id, extra, f"📎 فایل اضافی: `{Path(extra).name}`")

    clear_state(user_id)
    edit_message(
        chat_id, msg_id,
        f"✅ *درخواست استقرار ثبت شد!*\n\n"
        f"🔖 کد پیگیری: `{tracking_code}`\n\n"
        f"پس از تایید مدیر، ربات شما مستقر خواهد شد.",
        reply_markup=inline_keyboard([[("🔙 منوی اصلی", "main_menu")]])
    )


# ─────────────────────────────────────────────
#  تایید/رد استقرار توسط مدیر
# ─────────────────────────────────────────────
def handle_admin_approve_deploy(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "این درخواست قبلاً پردازش شده!", True)
        return

    req_data = json.loads(req["data"])
    bot_id = req_data["bot_id"]
    user_id = req["user_id"]

    # آپدیت وضعیت
    with get_db() as conn:
        conn.execute(
            "UPDATE deployed_bots SET status='running', approved_by=?, deployed_at=? WHERE id=?",
            (admin_id, datetime.now().isoformat(), bot_id)
        )
        conn.execute(
            "UPDATE pending_requests SET status='approved' WHERE id=?",
            (req_id,)
        )
        conn.commit()

        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()

    # راه‌اندازی ربات
    log_file = start_bot_process(bot_id, bot["file_path"], bot["bot_name"], user_id)

    edit_message(
        chat_id, msg_id,
        f"✅ ربات *{bot['bot_name']}* تایید و اجرا شد.",
        reply_markup=inline_keyboard([[("✅ تایید شد", "noop")]])
    )

    # اطلاع به کاربر
    send_message(
        user_id,
        f"🎉 *ربات شما تایید شد!*\n\n"
        f"🤖 نام: *{bot['bot_name']}*\n"
        f"✅ وضعیت: در حال اجرا\n\n"
        f"اولین لاگ‌ها به زودی ارسال می‌شوند.",
        reply_markup=inline_keyboard([[("📋 مشاهده لاگ", f"view_log:{bot_id}")]])
    )

    # نصب خودکار کتابخانه‌های مورد نیاز
    auto_install_bot_requirements(bot_id, bot["file_path"], user_id)

    # ارسال لاگ اولیه
    if log_file:
        threading.Thread(target=stream_logs, args=(bot_id, user_id, bot["bot_name"]), daemon=True).start()


def handle_admin_reject_deploy(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "این درخواست قبلاً پردازش شده!", True)
        return

    set_state(admin_id, "reject_deploy_reason", {
        "req_id": req_id,
        "msg_id": msg_id,
        "chat_id": chat_id,
        "user_id": req["user_id"]
    })
    send_message(admin_id, "❓ دلیل رد درخواست را وارد کنید:")


def handle_admin_reject_lib(query: dict, req_id: int):
    """FIX: تابع رد کتابخانه که قبلاً تعریف نشده بود"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "این درخواست قبلاً پردازش شده!", True)
        return

    set_state(admin_id, "reject_lib_reason", {
        "req_id": req_id,
        "msg_id": msg_id,
        "chat_id": chat_id,
        "user_id": req["user_id"]
    })
    send_message(admin_id, "❓ دلیل رد درخواست کتابخانه را وارد کنید:")


# ─────────────────────────────────────────────
#  اجرا و مدیریت پروسه ربات‌ها
# ─────────────────────────────────────────────
bot_processes: Dict[int, subprocess.Popen] = {}
bot_log_msgs: Dict[int, dict] = {}  # {bot_id: {user_id, msg_id, log_lines}}
bot_restart_count: Dict[int, int] = {}  # {bot_id: restart_count}
bot_last_restart: Dict[int, float] = {}  # {bot_id: timestamp}
MAX_RESTART_ATTEMPTS = 5
RESTART_COOLDOWN = 300  # ۵ دقیقه بین تلاش‌های راه‌اندازی مجدد


def generate_html_log(bot_name: str, log_lines: list) -> str:
    lines_html = ""
    for line in log_lines:
        ts = line.get("ts", "")
        msg = line.get("msg", "").replace("<", "&lt;").replace(">", "&gt;")
        level = line.get("level", "INFO")
        color = {
            "INFO": "#00ff88",
            "ERROR": "#ff4444",
            "WARNING": "#ffbb00",
            "SUCCESS": "#00ccff"
        }.get(level, "#ffffff")
        lines_html += f'<tr><td class="ts">{ts}</td><td class="level" style="color:{color}">{level}</td><td class="msg">{msg}</td></tr>\n'

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>لاگ ربات {bot_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: 'Courier New', monospace; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #1f6feb, #388bfd); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }}
  .header h1 {{ font-size: 24px; color: white; }}
  .header p {{ color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 5px; }}
  .stats {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 20px; flex: 1; min-width: 120px; text-align: center; }}
  .stat-card .num {{ font-size: 24px; font-weight: bold; color: #58a6ff; }}
  .stat-card .label {{ font-size: 12px; color: #8b949e; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 12px; overflow: hidden; }}
  thead {{ background: #21262d; }}
  th {{ padding: 12px 16px; text-align: right; color: #8b949e; font-size: 13px; border-bottom: 1px solid #30363d; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #21262d; font-size: 13px; }}
  .ts {{ color: #8b949e; white-space: nowrap; }}
  .level {{ font-weight: bold; }}
  .msg {{ word-break: break-all; }}
  tr:hover {{ background: #1c2128; }}
  .footer {{ text-align: center; margin-top: 20px; color: #8b949e; font-size: 12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 {bot_name}</h1>
  <p>آخرین بروزرسانی: {format_persian_datetime(datetime.now())}</p>
</div>
<div class="stats">
  <div class="stat-card"><div class="num">{len(log_lines)}</div><div class="label">تعداد لاگ</div></div>
  <div class="stat-card"><div class="num">{sum(1 for l in log_lines if l.get('level')=='ERROR')}</div><div class="label">خطا</div></div>
  <div class="stat-card"><div class="num">{sum(1 for l in log_lines if l.get('level')=='WARNING')}</div><div class="label">هشدار</div></div>
</div>
<table>
<thead><tr><th>زمان</th><th>سطح</th><th>پیام</th></tr></thead>
<tbody>
{lines_html}
</tbody>
</table>
<div class="footer">Poro Bot Logger &copy; {datetime.now().year}</div>
</body>
</html>"""


def start_bot_process(bot_id: int, file_path: str, bot_name: str, user_id: int, is_auto_restart: bool = False) -> Optional[str]:
    """راه‌اندازی فرآیند ربات - پشتیبانی از راه‌اندازی مجدد خودکار"""
    try:
        # بررسی تعداد تلاش‌های راه‌اندازی مجدد
        restart_count = bot_restart_count.get(bot_id, 0)
        last_restart_time = bot_last_restart.get(bot_id, 0)
        now = time.time()
        
        if restart_count >= MAX_RESTART_ATTEMPTS:
            if now - last_restart_time < RESTART_COOLDOWN:
                log.warning(f"ربات {bot_id} به حداکثر تلاش‌های راه‌اندازی مجدد رسید. در انتظار {RESTART_COOLDOWN}ث...")
                return None
            else:
                # ریست کردن شمارنده بعد از cooldown
                bot_restart_count[bot_id] = 0
        
        log_file = LOGS_DIR / f"bot_{bot_id}.log"
        lf = open(log_file, "w")
        proc = subprocess.Popen(
            [sys.executable, file_path],
            stdout=lf,
            stderr=lf,
            cwd=str(Path(file_path).parent)
        )
        bot_processes[bot_id] = proc
        
        # آپدیت شمارنده راه‌اندازی مجدد
        if is_auto_restart:
            bot_restart_count[bot_id] = restart_count + 1
            bot_last_restart[bot_id] = now
        else:
            bot_restart_count[bot_id] = 0
            bot_last_restart[bot_id] = now
        
        with get_db() as conn:
            conn.execute(
                "UPDATE deployed_bots SET pid=?, log_file=?, last_started=? WHERE id=?",
                (proc.pid, str(log_file), datetime.now().isoformat(), bot_id)
            )
            conn.commit()
        
        # اطلاع به کاربر
        if not is_auto_restart:
            send_message(user_id, f"✅ ربات *{bot_name}* راه‌اندازی شد.\nPID: `{proc.pid}`")
        else:
            send_message(user_id, f"🔄 ربات *{bot_name}* به‌طور خودکار راه‌اندازی شد مجدد.\nتلاش #{bot_restart_count[bot_id]} از {MAX_RESTART_ATTEMPTS}\nPID: `{proc.pid}`")
        
        return str(log_file)
    except Exception as e:
        log.error(f"خطا در راه‌اندازی ربات {bot_id}: {e}")
        send_message(user_id, f"❌ خطا در راه‌اندازی ربات *{bot_name}*:\n`{str(e)[:100]}`")
        return None

def stream_logs(bot_id: int, user_id: int, bot_name: str):
    """ارسال لاگ به کاربر - فقط وقتی محتوای جدیدی وجود دارد"""
    time.sleep(3)
    log_file = LOGS_DIR / f"bot_{bot_id}.log"
    log_lines = [{"ts": datetime.now().strftime("%H:%M:%S"), "msg": f"✅ ربات {bot_name} با موفقیت راه‌اندازی شد", "level": "SUCCESS"}]

    html_path = LOGS_DIR / f"bot_{bot_id}_log.html"
    html_content = generate_html_log(bot_name, log_lines)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    res = send_document(user_id, html_path, f"📋 لاگ اولیه ربات *{bot_name}*")
    if not res.get("ok"):
        return

    bot_log_msgs[bot_id] = {
        "user_id": user_id,
        "log_lines": log_lines,
        "html_path": str(html_path)
    }

    last_pos = 0
    last_send_hash = ""
    idle_count = 0
    MAX_IDLE_CYCLES = 12    # 12 * 5s = 60s بدون لاگ جدید → توقف
    CHECK_INTERVAL = 5       # هر 5 ثانیه یک‌بار چک می‌کند

    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            if not log_file.exists():
                break

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_pos)
                new_content = f.read()
                new_last_pos = f.tell()

            if not new_content.strip():
                idle_count += 1
                if idle_count >= MAX_IDLE_CYCLES:
                    break  # بدون لاگ جدید برای مدت طولانی - متوقف می‌شود
                continue  # هیچ محتوای جدیدی نیست - ارسال نمی‌کند

            idle_count = 0
            last_pos = new_last_pos

            # اضافه کردن خطوط جدید به log_lines
            for line in new_content.strip().split("\n"):
                if line.strip():
                    lvl = "INFO"
                    low = line.lower()
                    if "error" in low or "exception" in low or "traceback" in low:
                        lvl = "ERROR"
                    elif "warn" in low:
                        lvl = "WARNING"
                    log_lines.append({
                        "ts": datetime.now().strftime("%H:%M:%S"),
                        "msg": line.strip(),
                        "level": lvl
                    })

            # بررسی تغییر واقعی قبل از ارسال مجدد (جلوگیری از لاگ تکراری)
            content_hash = hashlib.md5(new_content.encode("utf-8", errors="ignore")).hexdigest()
            if content_hash == last_send_hash:
                continue
            last_send_hash = content_hash

            html_content = generate_html_log(bot_name, log_lines[-200:])
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            send_document(user_id, html_path, f"📋 بروزرسانی لاگ ربات *{bot_name}*")

        except Exception as e:
            log.error(f"خطا در stream_logs ربات {bot_id}: {e}")
            break


# ─────────────────────────────────────────────
#  سیستم watchdog برای نظارت بر ربات‌های کرش‌کرده
# ─────────────────────────────────────────────
def watchdog_monitor():
    """نظارت بر ربات‌ها و راه‌اندازی مجدد خودکار ربات‌های کرش‌کرده"""
    while True:
        try:
            time.sleep(30)  # هر ۳۰ ثانیه یک‌بار چک کن
            
            with get_db() as conn:
                active_bots = conn.execute(
                    "SELECT id, file_path, bot_name, user_id FROM deployed_bots WHERE status='running'"
                ).fetchall()
            
            for bot in active_bots:
                bot_id = bot["id"]
                
                proc = bot_processes.get(bot_id)
                
                # بررسی اینکه فرآیند هنوز در حال اجرا است یا نه
                if proc is None or proc.poll() is not None:
                    # فرآیند کرش کرده است
                    log.warning(f"ربات {bot_id} کرش کرد. تلاش برای راه‌اندازی مجدد...")
                    
                    restart_count = bot_restart_count.get(bot_id, 0)
                    
                    if restart_count < MAX_RESTART_ATTEMPTS:
                        # تلاش برای راه‌اندازی مجدد
                        result = start_bot_process(
                            bot_id,
                            bot["file_path"],
                            bot["bot_name"],
                            bot["user_id"],
                            is_auto_restart=True
                        )
                        
                        if result:
                            log.info(f"ربات {bot_id} با موفقیت راه‌اندازی شد مجدد. (تلاش #{restart_count + 1})")
                        else:
                            log.error(f"ناموفق در راه‌اندازی مجدد ربات {bot_id}")
                    else:
                        # حداکثر تلاش رسیده‌ایم
                        log.error(f"ربات {bot_id} به حداکثر تلاش‌های راه‌اندازی مجدد رسید. متوقف می‌شود.")
                        send_message(
                            bot["user_id"],
                            f"❌ ربات *{bot['bot_name']}* به‌طور مکرر کرش می‌کند و نتوانست راه‌اندازی شود.\n"
                            f"لطفاً کد خود را بررسی کنید و دوباره استقرار دهید."
                        )
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE deployed_bots SET status='error' WHERE id=?",
                                (bot_id,)
                            )
                            conn.commit()
        
        except Exception as e:
            log.error(f"خطا در watchdog_monitor: {e}")
            time.sleep(10)  # اگر خطا خورد، کمی صبر کن


# شروع watchdog thread در پس‌زمینه
def start_watchdog():
    """شروع watchdog thread"""
    watchdog_thread = threading.Thread(target=watchdog_monitor, daemon=True)
    watchdog_thread.start()
    log.info("✅ سیستم watchdog شروع شد")


# ─────────────────────────────────────────────
#  نصب کتابخانه
# ─────────────────────────────────────────────
def handle_install_lib(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    ok, reason = check_plan_limit(user_id, "libraries")
    if not ok:
        edit_message(
            chat_id, msg_id,
            f"❌ *محدودیت پلن*\n\n{reason}",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]])
        )
        return

    u = get_user(user_id)
    plan = PLANS.get(u["plan"] if u else "free", PLANS["free"])
    mirror_allowed = plan["personal_mirror"]

    set_state(user_id, "install_lib_name")
    buttons = [[("❌ انصراف", "main_menu")]]
    if mirror_allowed:
        buttons.insert(0, [("🌐 میرور", "set_mirror")])

    edit_message(
        chat_id, msg_id,
        "📦 *نصب کتابخانه جدید*\n\nنام کتابخانه را ارسال کنید:\n\n"
        "مثال: `requests`, `numpy`, `flask`",
        reply_markup=inline_keyboard(buttons)
    )


def handle_install_lib_name(message: dict):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    state = get_state(user_id)
    lib_name = message.get("text", "").strip()

    if not lib_name:
        send_message(chat_id, "❌ نام کتابخانه معتبر نیست.")
        return

    mirror = state["data"].get("mirror", None)
    tracking_code = "LIB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO library_installs (user_id, library_name, mirror_url, status, tracking_code) VALUES (?,?,?,?,?)",
            (user_id, lib_name, mirror, "pending", tracking_code)
        )
        install_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO pending_requests (type, user_id, data, created_at) VALUES (?,?,?,?)",
            ("install_lib", user_id, json.dumps({"install_id": install_id, "lib_name": lib_name, "tracking": tracking_code, "mirror": mirror}), datetime.now().isoformat())
        )
        req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    # اگه کتابخانه قبلاً تایید شده → نصب خودکار
    with get_db() as conn:
        approved_lib = conn.execute(
            "SELECT * FROM approved_libraries WHERE name=? AND is_active=1", (lib_name,)
        ).fetchone()

    if approved_lib:
        clear_state(user_id)
        send_message(chat_id,
            f"⚡ کتابخانه `{lib_name}` قبلاً تایید شده — در حال نصب خودکار...")
        # شبیه‌سازی تایید ادمین
        class FakeQuery:
            def __init__(self): self.id = ""
            def get(self, k, d=""): return d
        fake_q = {"id": "", "from": {"id": ADMIN_IDS[0]}, "message": {"chat": {"id": chat_id}, "message_id": 0}}
        threading.Thread(
            target=lambda: _do_lib_install(lib_name, mirror, install_id, req_id, ADMIN_IDS[0], chat_id, 0, user_id),
            daemon=True
        ).start()
        return

    u = get_user(user_id)
    for admin_id in ADMIN_IDS:
        send_message(
            admin_id,
            f"📦 *درخواست نصب کتابخانه*\n\n"
            f"👤 کاربر: {u['full_name'] if u else user_id} (`{user_id}`)\n"
            f"📦 کتابخانه: `{lib_name}`\n"
            f"🌐 میرور: {mirror or 'پیش‌فرض (PyPI)'}\n"
            f"🔖 کد پیگیری: `{tracking_code}`",
            reply_markup=inline_keyboard([
                [("✅ تایید و نصب", f"admin_approve_lib:{req_id}"), ("❌ رد", f"admin_reject_lib:{req_id}")]
            ])
        )

    clear_state(user_id)
    send_message(
        chat_id,
        f"✅ *درخواست نصب ثبت شد!*\n\n"
        f"📦 کتابخانه: `{lib_name}`\n"
        f"🔖 کد پیگیری: `{tracking_code}`\n\n"
        f"پس از تایید مدیر نصب انجام می‌شود.",
        reply_markup=inline_keyboard([[("🔙 منوی اصلی", "main_menu")]])
    )


def _do_lib_install(lib_name: str, mirror: str | None, install_id: int, req_id: int,
                    admin_id: int, chat_id: int, msg_id: int, user_id: int):
    """نصب کتابخانه و اطلاع‌رسانی - تابع مشترک برای تایید دستی و خودکار"""
    cmd = [sys.executable, "-m", "pip", "install", lib_name]
    if mirror:
        cmd.extend(["-i", mirror])
    cmd.append("--break-system-packages")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        result = type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': 'نصب بیش از حد طول کشید.'})()

    success = result.returncode == 0
    output = (result.stdout + result.stderr)[-1500:]
    status = "installed" if success else "failed"

    with get_db() as conn:
        conn.execute(
            "UPDATE library_installs SET status=?, approved_by=?, installed_at=? WHERE id=?",
            (status, admin_id, datetime.now().isoformat(), install_id)
        )
        if req_id:
            conn.execute("UPDATE pending_requests SET status=? WHERE id=?", (status, req_id))
        # با تایید موفق، کتابخانه به لیست تایید‌شده‌ها اضافه می‌شود
        if success:
            conn.execute(
                "INSERT OR IGNORE INTO approved_libraries (name, approved_by, approved_at, is_active) VALUES (?,?,?,1)",
                (lib_name, admin_id, datetime.now().isoformat())
            )
        conn.commit()

    if success:
        if msg_id:
            edit_message(chat_id, msg_id,
                f"✅ کتابخانه `{lib_name}` نصب شد!\n\n```\n{output[:500]}\n```")
        send_message(user_id, f"✅ *کتابخانه نصب شد!*\n\n`{lib_name}` با موفقیت نصب شد.\n⚡ دفعه بعد خودکار نصب می‌شود.")
    else:
        if msg_id:
            edit_message(chat_id, msg_id,
                f"❌ خطا در نصب `{lib_name}`:\n\n```\n{output[:500]}\n```")
        send_message(user_id, f"❌ نصب `{lib_name}` با خطا مواجه شد.\n```{output[:300]}```")


def handle_admin_approve_lib(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "قبلاً پردازش شده!", True)
        return

    req_data = json.loads(req["data"])
    install_id = req_data["install_id"]
    lib_name = req_data["lib_name"]
    mirror = req_data.get("mirror")
    user_id = req["user_id"]

    edit_message(
        chat_id, msg_id,
        f"⏳ در حال نصب `{lib_name}`...",
    )

    threading.Thread(
        target=lambda: _do_lib_install(lib_name, mirror, install_id, req_id, admin_id, chat_id, msg_id, user_id),
        daemon=True
    ).start()


# ─────────────────────────────────────────────
#  نصب خودکار کتابخانه‌های ربات پس از تایید مدیر
# ─────────────────────────────────────────────
def extract_imports_from_file(file_path: str) -> List[str]:
    """استخراج نام ماژول‌های import شده از یک فایل پایتون با ast"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module.split(".")[0])
        return list(modules)
    except Exception as e:
        log.error(f"خطا در parse فایل برای استخراج import: {e}")
        return []


def auto_install_bot_requirements(bot_id: int, file_path: str, user_id: int):
    """نصب خودکار کتابخانه‌های مورد نیاز ربات پس از تایید مدیر"""
    bot_dir = Path(file_path).parent
    libs_to_install = []

    # اول بررسی requirements.txt
    req_file = bot_dir / "requirements.txt"
    if req_file.exists():
        try:
            with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    lib = line.strip()
                    if lib and not lib.startswith("#") and not lib.startswith("-"):
                        lib_name = re.split(r"[>=<!;\[]", lib)[0].strip()
                        if lib_name:
                            libs_to_install.append(lib_name)
            log.info(f"requirements.txt پیدا شد: {libs_to_install}")
        except Exception as e:
            log.error(f"خطا در خواندن requirements.txt: {e}")

    # اگر requirements.txt نبود، scan imports
    if not libs_to_install and file_path.endswith(".py"):
        all_imports = extract_imports_from_file(file_path)
        for mod in all_imports:
            if mod and mod not in STDLIB_MODULES:
                libs_to_install.append(mod)

    if not libs_to_install:
        return

    def do_auto_install():
        installed = []
        failed = []
        for lib in libs_to_install:
            try:
                cmd = [sys.executable, "-m", "pip", "install", lib,
                       "--break-system-packages", "-q", "--disable-pip-version-check"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    installed.append(lib)
                    log.info(f"کتابخانه {lib} با موفقیت نصب شد")
                else:
                    failed.append(lib)
                    log.warning(f"نصب {lib} ناموفق: {result.stderr[:200]}")
            except Exception as e:
                failed.append(lib)
                log.error(f"خطا در نصب {lib}: {e}")

        msg = f"📦 *نصب خودکار کتابخانه‌ها (ربات #{bot_id})*\n\n"
        if installed:
            msg += f"✅ نصب شد: {', '.join(f'`{l}`' for l in installed)}\n"
        if failed:
            msg += f"❌ نصب ناموفق: {', '.join(f'`{l}`' for l in failed)}\n"
            msg += "\nاگر ربات با خطای import مواجه شد، از بخش «نصب کتابخانه» اقدام کنید."
        send_message(user_id, msg)

    threading.Thread(target=do_auto_install, daemon=True).start()


# ─────────────────────────────────────────────
#  فروشگاه آیتم
# ─────────────────────────────────────────────
def handle_shop_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    points = u["points"] if u else 0
    plan = u["plan"] if u else "free"

    text = f"🏪 *فروشگاه آیتم*\n\n💰 امتیاز شما: *{points}*\n\n"
    buttons = []
    for key, item in SHOP_ITEMS.items():
        cost = item["points"].get(plan)
        if cost is None:
            continue
        btn_text = f"{item['name']} - {cost} امتیاز"
        buttons.append([(btn_text, f"buy_item:{key}")])

    buttons.append([("🔙 بازگشت", "main_menu")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_buy_item(query: dict, item_key: str):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    plan = u["plan"] if u else "free"
    item = SHOP_ITEMS.get(item_key)

    if not item:
        answer_callback(query["id"], "آیتم یافت نشد!", True)
        return

    cost = item["points"].get(plan)
    if cost is None:
        answer_callback(query["id"], "در پلن شما این آیتم موجود نیست!", True)
        return

    if not u or u["points"] < cost:
        edit_message(
            chat_id, msg_id,
            f"❌ امتیاز کافی ندارید!\n\nنیاز: *{cost}*\nموجودی: *{u['points'] if u else 0}*",
            reply_markup=inline_keyboard([[("🔙 فروشگاه", "shop_menu")]])
        )
        return

    if not spend_points(user_id, cost):
        answer_callback(query["id"], "خطا در کسر امتیاز!", True)
        return

    # اعمال آیتم
    field_map = {
        "extra_bot": "extra_bots",
        "extra_memory": "extra_memory_mb",
        "extra_log": "extra_log_days",
        "extra_library": "extra_libraries",
        "extra_bandwidth": "extra_bandwidth_gb"
    }
    amount_map = {
        "extra_bot": 1,
        "extra_memory": 100,
        "extra_log": 7,
        "extra_library": 1,
        "extra_bandwidth": 1
    }
    db_field = field_map.get(item_key)
    amount = amount_map.get(item_key, 1)

    if db_field:
        with get_db() as conn:
            conn.execute(f"UPDATE users SET {db_field} = {db_field} + ? WHERE user_id=?", (amount, user_id))
            conn.commit()

    edit_message(
        chat_id, msg_id,
        f"✅ *آیتم خریداری شد!*\n\n{item['name']} به حساب شما اضافه شد.\n💰 امتیاز باقی‌مانده: *{get_points(user_id)}*",
        reply_markup=inline_keyboard([[("🔙 فروشگاه", "shop_menu")]])
    )


# ─────────────────────────────────────────────
#  سیستم اشتراک و پرداخت
# ─────────────────────────────────────────────
def handle_sub_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    current_plan = u["plan"] if u else "free"

    text = f"💳 *خرید اشتراک*\n\nپلن فعلی: *{PLANS[current_plan]['name']}*\n\nپلن مورد نظر را انتخاب کنید:"
    buttons = []
    for plan_key, plan_data in PLANS.items():
        if plan_key == "free":
            continue
        if plan_key == "enterprise":
            buttons.append([(f"{plan_data['name']} - مذاکره‌ای", f"view_plan:{plan_key}")])
        else:
            min_price = min(v["price"] for v in plan_data["subscriptions"].values())
            buttons.append([(f"{plan_data['name']} - از {min_price:,} تومان", f"view_plan:{plan_key}")])

    buttons.append([("🔙 بازگشت", "main_menu")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_view_plan(query: dict, plan_key: str):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    plan = PLANS.get(plan_key)
    if not plan:
        answer_callback(query["id"], "پلن یافت نشد!", True)
        return

    text = f"*{plan['name']}*\n\n"
    text += f"🤖 حداکثر ربات: {'نامحدود' if plan['max_bots']==-1 else plan['max_bots']}\n"
    text += f"💾 حافظه: {plan['max_memory_mb']} MB\n"
    text += f"📋 نگهداری لاگ: {plan['log_retention_days']} روز\n"
    text += f"📦 کتابخانه: {'نامحدود' if plan['max_libraries']==-1 else plan['max_libraries']}\n"
    text += f"🌐 پهنای باند: {plan['monthly_bandwidth_gb']} GB/ماه\n\n"
    text += "💰 *قیمت‌ها:*\n"

    buttons = []
    for dur, sub in plan["subscriptions"].items():
        dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه", "biannual": "شش ماهه", "annual": "یک ساله"}
        price = sub["price"]
        if price == -1:
            text += f"• {dur_fa.get(dur, dur)}: مذاکره‌ای\n"
        else:
            fake_price = int(price * 1.05)
            text += f"• {dur_fa.get(dur, dur)}: ~~{fake_price:,}~~ *{price:,}* تومان 🏷\n"
            buttons.append([(f"خرید {dur_fa.get(dur, dur)} - {price:,}T", f"checkout:{plan_key}:{dur}")])

    if plan_key == "enterprise":
        buttons.append([("📞 تماس با مدیر", f"enterprise_request")])

    buttons.append([("🔙 بازگشت", "sub_menu")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_checkout(query: dict, plan_key: str, duration: str):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    plan = PLANS.get(plan_key)
    if not plan:
        answer_callback(query["id"], "پلن یافت نشد!", True)
        return

    sub = plan["subscriptions"].get(duration)
    if not sub or sub["price"] <= 0:
        answer_callback(query["id"], "قیمت نامعتبر!", True)
        return

    dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه", "biannual": "شش ماهه", "annual": "یک ساله"}
    price = sub["price"]

    set_state(user_id, "awaiting_discount", {"plan": plan_key, "duration": duration, "price": price})

    edit_message(
        chat_id, msg_id,
        f"💳 *خرید اشتراک*\n\n"
        f"پلن: *{plan['name']}*\n"
        f"مدت: *{dur_fa.get(duration, duration)}*\n"
        f"قیمت: *{price:,} تومان*\n\n"
        f"آیا کد تخفیف دارید؟",
        reply_markup=inline_keyboard([
            [("🎟 وارد کردن کد تخفیف", f"enter_discount:{plan_key}:{duration}")],
            [("💰 پرداخت بدون تخفیف", f"pay_now:{plan_key}:{duration}:0")],
            [("🔙 بازگشت", f"view_plan:{plan_key}")]
        ])
    )


def handle_pay_now(query: dict, plan_key: str, duration: str, discount: int):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]

    plan = PLANS.get(plan_key)
    if not plan:
        return

    sub = plan["subscriptions"].get(duration)
    if not sub:
        return

    original_price = sub["price"]
    final_price = max(0, original_price - int(discount))
    dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه", "biannual": "شش ماهه", "annual": "یک ساله"}

    payload = f"sub_{plan_key}_{duration}_{user_id}_{int(time.time())}"

    send_invoice(
        chat_id,
        title=f"اشتراک {plan['name']}",
        description=f"خرید اشتراک {dur_fa.get(duration, duration)} - {plan['name']}",
        payload=payload,
        prices=[{"label": f"اشتراک {plan['name']}", "amount": final_price * 10}]
    )


def handle_pre_checkout(update: dict):
    query = update.get("pre_checkout_query", {})
    api("answerPreCheckoutQuery", {
        "pre_checkout_query_id": query["id"],
        "ok": True
    })


def handle_successful_payment(message: dict):
    user_id = message["from"]["id"]
    payment = message["successful_payment"]
    payload = payment["invoice_payload"]
    amount = payment["total_amount"] // 10

    parts = payload.split("_")
    if len(parts) >= 3 and parts[0] == "sub":
        plan_key = parts[1]
        duration = parts[2]

        dur_days = {"monthly": 30, "quarterly": 90, "biannual": 180, "annual": 365}
        days = dur_days.get(duration, 30)
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()

        with get_db() as conn:
            u = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

            # بررسی خرید اجباری پلن بالاتر
            if plan_key == "basic":
                basic_count = ((u["basic_buy_count"] or 0) if u else 0) + 1
                conn.execute(
                    "UPDATE users SET plan=?, plan_expires_at=?, total_spent=total_spent+?, basic_buy_count=? WHERE user_id=?",
                    (plan_key, expires_at, amount, basic_count, user_id)
                )
                if basic_count >= 3:
                    send_message(
                        user_id,
                        "⚠️ *توجه:* شما ۳ بار اشتراک پایه خریداری کرده‌اید.\n"
                        "از این به بعد برای خرید اشتراک پایه، ابتدا باید یک بار اشتراک حرفه‌ای تهیه کنید."
                    )
            else:
                conn.execute(
                    "UPDATE users SET plan=?, plan_expires_at=?, total_spent=total_spent+? WHERE user_id=?",
                    (plan_key, expires_at, amount, user_id)
                )

            conn.execute(
                "INSERT INTO payments (user_id, plan, duration, amount, status, transaction_id, provider_id, payload, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, plan_key, duration, amount, "paid",
                 payment.get("telegram_payment_charge_id", ""),
                 payment.get("provider_payment_charge_id", ""),
                 payload, datetime.now().isoformat())
            )
            conn.commit()

        # اضافه کردن امتیاز هدیه
        gift_points = PLANS.get(plan_key, {}).get("subscriptions", {}).get(duration, {}).get("gift_points", 0)
        if gift_points:
            add_points(user_id, gift_points, "هدیه خرید اشتراک")

        # امتیاز بر اساس خرید
        buy_points = amount // 1000
        if buy_points:
            add_points(user_id, buy_points, "امتیاز خرید")

        send_message(
            user_id,
            f"🎉 *پرداخت موفق!*\n\n"
            f"✅ اشتراک {PLANS[plan_key]['name']} فعال شد!\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"📅 انقضا: {expires_at[:10]}\n"
            f"🎁 امتیاز هدیه: {gift_points} امتیاز",
            reply_markup=main_menu(user_id)
        )


# ─────────────────────────────────────────────
#  سیستم تخفیف
# ─────────────────────────────────────────────
def validate_discount_code(code: str, user_id: int, plan_key: str) -> tuple:
    """بررسی کد تخفیف، برگرداندن (valid, amount_off, dc_obj_or_reason)"""
    with get_db() as conn:
        dc = conn.execute("SELECT * FROM discount_codes WHERE code=?", (code,)).fetchone()

    if not dc:
        return False, 0, "کد تخفیف معتبر نیست"
    if not dc["is_active"]:
        return False, 0, "این کد تخفیف غیرفعال است"
    if dc["used_count"] >= dc["max_uses"]:
        return False, 0, "این کد تخفیف تمام شده"
    if dc["expires_at"] and datetime.now().isoformat() > dc["expires_at"]:
        return False, 0, "این کد تخفیف منقضی شده"
    if dc["plan_target"] and dc["plan_target"] != plan_key:
        return False, 0, "این کد برای پلن شما قابل استفاده نیست"

    # بررسی استفاده قبلی
    with get_db() as conn:
        used = conn.execute(
            "SELECT id FROM discount_uses WHERE code_id=? AND user_id=?",
            (dc["id"], user_id)
        ).fetchone()

    if used:
        return False, 0, "شما قبلاً از این کد استفاده کرده‌اید"

    # بررسی حداکثر کد همزمان
    u = get_user(user_id)
    plan = PLANS.get(u["plan"] if u else "free", PLANS["free"])
    max_codes = plan["max_discount_codes"]
    if max_codes == 0:
        return False, 0, "پلن شما امکان استفاده از کد تخفیف ندارد"

    return True, dc["value"], dict(dc)


def apply_discount_code(code_id: int, user_id: int):
    with get_db() as conn:
        conn.execute("UPDATE discount_codes SET used_count=used_count+1 WHERE id=?", (code_id,))
        conn.execute(
            "INSERT INTO discount_uses (code_id, user_id, used_at) VALUES (?,?,?)",
            (code_id, user_id, datetime.now().isoformat())
        )
        conn.commit()


# ─────────────────────────────────────────────
#  پنل مدیریت
# ─────────────────────────────────────────────


def handle_realtime_stats(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(user_id):
        return

    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        active_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1").fetchone()["c"]
        blocked_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_blocked=1").fetchone()["c"]
        total_bots = conn.execute("SELECT COUNT(*) as c FROM deployed_bots").fetchone()["c"]
        running_bots = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE status='running'").fetchone()["c"]
        pending_reqs = conn.execute("SELECT COUNT(*) as c FROM pending_requests WHERE status='pending'").fetchone()["c"]
        total_revenue_row = conn.execute("SELECT SUM(amount) as s FROM payments WHERE status='paid'").fetchone()
        total_revenue = total_revenue_row["s"] or 0
        open_tickets = conn.execute("SELECT COUNT(*) as c FROM tickets WHERE status='open'").fetchone()["c"]

    edit_message(
        chat_id, msg_id,
        f"📊 *آمار لحظه‌ای*\n"
        f"⏰ {format_persian_datetime(datetime.now())}\n\n"
        f"👥 کاربران: {total_users} (فعال: {active_users}, مسدود: {blocked_users})\n"
        f"🤖 ربات‌ها: {total_bots} (در حال اجرا: {running_bots})\n"
        f"⏳ درخواست‌های در انتظار: {pending_reqs}\n"
        f"🎫 تیکت‌های باز: {open_tickets}\n"
        f"💰 کل درآمد: {total_revenue:,} تومان",
        reply_markup=inline_keyboard([
            [("🔄 بروزرسانی", "realtime_stats")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )


def handle_weekly_stats_send(query=None):
    """ارسال آمار هفتگی - FIX: پارامتر query اختیاری شد"""
    with get_db() as conn:
        week_start = (datetime.now() - timedelta(days=7)).isoformat()

        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        new_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE joined_at>=?", (week_start,)).fetchone()["c"]
        active_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE last_active>=?", (week_start,)).fetchone()["c"]
        running_bots = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE status='running'").fetchone()["c"]
        stopped_bots = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE status='stopped'").fetchone()["c"]
        lib_installs = conn.execute("SELECT COUNT(*) as c FROM library_installs WHERE status='installed' AND installed_at>=?", (week_start,)).fetchone()["c"]
        top_libs = conn.execute(
            "SELECT library_name, COUNT(*) as c FROM library_installs WHERE status='installed' GROUP BY library_name ORDER BY c DESC LIMIT 3"
        ).fetchall()
        revenue_row = conn.execute("SELECT SUM(amount) as s FROM payments WHERE status='paid' AND created_at>=?", (week_start,)).fetchone()
        revenue = revenue_row["s"] or 0

        top_deployer = conn.execute(
            "SELECT u.full_name, COUNT(*) as c FROM deployed_bots b JOIN users u ON b.user_id=u.user_id WHERE b.deployed_at>=? GROUP BY b.user_id ORDER BY c DESC LIMIT 1",
            (week_start,)
        ).fetchone()
        top_installer = conn.execute(
            "SELECT u.full_name, COUNT(*) as c FROM library_installs l JOIN users u ON l.user_id=u.user_id WHERE l.installed_at>=? GROUP BY l.user_id ORDER BY c DESC LIMIT 1",
            (week_start,)
        ).fetchone()
        top_inviter = conn.execute(
            "SELECT full_name, invite_count FROM users ORDER BY invite_count DESC LIMIT 1"
        ).fetchone()

    top_libs_text = "\n".join([f"  • `{l['library_name']}` ({l['c']} بار)" for l in top_libs]) if top_libs else "  ندارد"
    week_end_dt = datetime.now()
    week_start_dt = week_end_dt - timedelta(days=7)
    week_end_str = format_persian_date(week_end_dt)
    week_start_str = format_persian_date(week_start_dt)

    msg = (
        f"📊 *آمار هفتگی سیستم* 📊\n\n"
        f"⏰ دوره: `{week_start_str}` تا `{week_end_str}`\n\n"
        f"*👥 کاربران*\n"
        f"کاربران کل: *{total_users}*\n"
        f"کاربران فعال این هفته: *{active_users}*\n"
        f"کاربران جدید: *{new_users}*\n"
        f"رشد هفتگی: *{round(new_users/max(total_users-new_users,1)*100,1)}٪*\n\n"
        f"*🤖 ربات‌ها*\n"
        f"ربات‌های فعال: *{running_bots}*\n"
        f"ربات‌های متوقف: *{stopped_bots}*\n\n"
        f"*📦 کتابخانه‌ها*\n"
        f"نصب موفق این هفته: *{lib_installs}*\n"
        f"پرکاربردترین:\n{top_libs_text}\n\n"
        f"*💰 درآمد*\n"
        f"درآمد این هفته: *{revenue:,} تومان*\n\n"
        f"*🏆 برترین‌های هفته*\n"
        f"۱. بیشترین استقرار: *{top_deployer['full_name'] if top_deployer else 'ندارد'}*\n"
        f"۲. بیشترین نصب: *{top_installer['full_name'] if top_installer else 'ندارد'}*\n"
        f"۳. بیشترین دعوت: *{top_inviter['full_name'] if top_inviter else 'ندارد'}*\n\n"
        f"*🔮 پیش‌بینی هفته آینده*\n"
        f"📈 رشد ۲۰٪ کاربران جدید\n"
        f"🤖 اضافه شدن ۵۰ ربات جدید\n"
        f"📦 نصب ۱۰۰ کتابخانه جدید\n\n"
        f"⚡ *سیستم همیشه در دسترس*\n"
        f"🛠 پشتیبانی ۲۴/۷ | 🔒 امنیت تضمینی | 🚀 سرعت بالا\n\n"
        f"🎉 *با تشکر از همراهی شما!*\n"
        f"تیم پشتیبانی 🤖"
    )

    # FIX: وقتی query وجود داره (از callback)، مستقیم برمی‌گردونه
    # وقتی query نداره (خودکار)، به مدیران می‌فرسته
    if query is None:
        for admin_id in ADMIN_IDS:
            send_message(admin_id, msg)
    else:
        return msg


# ─────────────────────────────────────────────
#  مدیریت کاربران
# ─────────────────────────────────────────────


def handle_search_user_prompt(query: dict):
    """نمایش prompt جستجوی کاربر"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(user_id):
        return

    set_state(user_id, "admin_search_user")
    edit_message(
        chat_id, msg_id,
        "🔍 *جستجوی کاربر*\n\nآیدی عددی یا یوزرنیم کاربر مورد نظر را ارسال کنید:",
        reply_markup=inline_keyboard([[("🔙 مدیریت کاربران", "user_management")]])
    )


def handle_view_users_list(query: dict, page: int = 0):
    """نمایش لیست ۳۰ تایی کاربران با صفحه‌بندی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(user_id):
        return

    page_size = 30
    offset = page * page_size

    with get_db() as conn:
        total_count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        users_page = conn.execute(
            "SELECT user_id, username, plan, is_active, is_blocked FROM users ORDER BY user_id DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        ).fetchall()

    if not users_page:
        edit_message(chat_id, msg_id, "❌ کاربری یافت نشد.",
                     reply_markup=inline_keyboard([[("🔙 مدیریت کاربران", "user_management")]]))
        return

    # ساخت دکمه‌های لیست کاربران (هر ردیف یک کاربر)
    buttons = []
    for u_row in users_page:
        status_icon = "🔴" if u_row["is_blocked"] else ("✅" if u_row["is_active"] else "⏳")
        plan_icon = {"free": "🟢", "basic": "🟡", "professional": "🔴", "enterprise": "⚫"}.get(u_row["plan"], "❓")
        uname = f"@{u_row['username']}" if u_row["username"] else "بدون یوزرنیم"
        btn_label = f"{status_icon} {u_row['user_id']} | {uname} | {plan_icon}{u_row['plan']}"
        buttons.append([(btn_label, f"admin_user_detail:{u_row['user_id']}")])

    # دکمه‌های صفحه‌بندی
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("◀️ صفحه قبل", f"view_users_list:{page - 1}"))
    total_pages = (total_count + page_size - 1) // page_size
    if (page + 1) < total_pages:
        nav_buttons.append(("صفحه بعد ▶️", f"view_users_list:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([("🔙 مدیریت کاربران", "user_management")])

    edit_message(
        chat_id, msg_id,
        f"📋 *لیست کاربران*\n\n"
        f"صفحه {page + 1} از {total_pages} | کل: {total_count} کاربر\n"
        f"(روی آیدی هر کاربر بزنید برای مدیریت)",
        reply_markup=inline_keyboard(buttons)
    )


def handle_admin_search_user(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    query_text = message.get("text", "").strip()

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        if query_text.isdigit():
            u = conn.execute("SELECT * FROM users WHERE user_id=?", (int(query_text),)).fetchone()
        else:
            uname = query_text.lstrip("@")
            u = conn.execute("SELECT * FROM users WHERE username=?", (uname,)).fetchone()

    if not u:
        send_message(chat_id, "❌ کاربر یافت نشد.", reply_markup=inline_keyboard([[("🔙 مدیریت کاربران", "user_management")]]))
        return

    u = dict(u)
    uid = u["user_id"]

    with get_db() as conn:
        bot_count = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE user_id=?", (uid,)).fetchone()["c"]
        lib_count = conn.execute("SELECT COUNT(*) as c FROM library_installs WHERE user_id=? AND status='installed'", (uid,)).fetchone()["c"]

    item_count = u.get("extra_bots", 0) + u.get("extra_libraries", 0) + u.get("extra_memory_mb", 0) // 100

    status = "✅ فعال" if u["is_active"] and not u["is_blocked"] else ("🔴 مسدود" if u["is_blocked"] else "⏳ غیرفعال")

    text = (
        f"👤 *{u['full_name']}*\n"
        f"آیدی: `{uid}`\n"
        f"یوزرنیم: @{u['username'] or 'ندارد'}\n"
        f"وضعیت: {status}\n"
        f"پلن: {PLANS.get(u['plan'], {}).get('name', u['plan'])}\n"
        f"امتیاز: *{u['points']}*\n"
        f"ربات‌ها: {bot_count}\n"
        f"کتابخانه‌ها: {lib_count}\n"
        f"دعوت‌ها: {u['invite_count']}\n"
        f"آیتم‌های خریداری: {item_count}\n"
        f"کل خرید: {u['total_spent']:,} تومان\n"
        f"عضویت: {u['joined_at'][:10] if u['joined_at'] else 'نامشخص'}"
    )

    buttons = [
        [("📩 ارسال پیام", f"admin_send_user:{uid}"), ("🎁 هدیه امتیاز", f"admin_gift_points:{uid}")],
        [("➖ کسر امتیاز", f"admin_deduct_points:{uid}"), ("♻️ تغییر پلن", f"admin_change_plan:{uid}")],
        [("🔴 مسدود کردن", f"admin_block_user:{uid}"), ("✅ رفع مسدودی", f"admin_unblock_user:{uid}")],
        [("🔙 بازگشت", "user_management")]
    ]
    clear_state(admin_id)
    send_message(chat_id, text, reply_markup=inline_keyboard(buttons))


def handle_admin_block_user(query: dict, target_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    edit_message(
        chat_id, msg_id,
        f"🔴 *مسدود کردن کاربر `{target_id}`*\n\nدلیل مسدودی را انتخاب کنید:",
        reply_markup=inline_keyboard([
            [("🦠 کد مخرب", f"block_confirm:{target_id}:malicious_code")],
            [("⏰ مسدودی موقت", f"block_confirm:{target_id}:temp_block")],
            [("🚫 تخلف قوانین", f"block_confirm:{target_id}:rules_violation")],
            [("🔙 بازگشت", "admin_panel")]
        ])
    )


def handle_block_confirm(query: dict, target_id: int, reason: str):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    reason_map = {
        "malicious_code": "تلاش برای اجرای کد مخرب",
        "temp_block": "مسدودی موقت",
        "rules_violation": "نقض قوانین"
    }

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_blocked=1, block_reason=? WHERE user_id=?",
            (reason_map.get(reason, reason), target_id)
        )
        conn.commit()

    edit_message(
        chat_id, msg_id,
        f"✅ کاربر `{target_id}` مسدود شد.\nدلیل: {reason_map.get(reason, reason)}",
        reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]])
    )
    send_message(
        target_id,
        f"❌ *حساب شما مسدود شده.*\n\nدلیل: {reason_map.get(reason, reason)}\n\nبرای رفع مسدودی با پشتیبانی تماس بگیرید."
    )


def handle_admin_change_plan(query: dict, target_id: int):
    """FIX: تابع تغییر پلن که قبلاً تعریف نشده بود"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    buttons = []
    for plan_key, plan_data in PLANS.items():
        buttons.append([(f"{plan_data['name']}", f"set_user_plan:{target_id}:{plan_key}")])
    buttons.append([("🔙 بازگشت", "user_management")])

    edit_message(
        chat_id, msg_id,
        f"♻️ *تغییر پلن کاربر `{target_id}`*\n\nپلن جدید را انتخاب کنید:",
        reply_markup=inline_keyboard(buttons)
    )


def handle_set_user_plan(query: dict, target_id: int, plan_key: str):
    """FIX: اعمال تغییر پلن"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    if plan_key not in PLANS:
        answer_callback(query["id"], "پلن نامعتبر!", True)
        return

    with get_db() as conn:
        conn.execute("UPDATE users SET plan=? WHERE user_id=?", (plan_key, target_id))
        conn.commit()

    plan_name = PLANS[plan_key]["name"]
    edit_message(
        chat_id, msg_id,
        f"✅ پلن کاربر `{target_id}` به *{plan_name}* تغییر یافت.",
        reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]])
    )
    send_message(target_id, f"♻️ پلن شما توسط مدیر به *{plan_name}* تغییر یافت.")


# ─────────────────────────────────────────────
#  سیستم تیکت
# ─────────────────────────────────────────────
def handle_ticket_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        ).fetchall()

    text = "🎫 *سیستم پشتیبانی*\n\n"
    if tickets:
        text += "تیکت‌های شما:\n"
        for t in tickets:
            status_icon = {"open": "🟡", "answered": "🟢", "closed": "⚫"}.get(t["status"], "❓")
            text += f"{status_icon} #{t['id']} - {t['subject'][:30]}\n"
    else:
        text += "هنوز تیکتی ندارید."

    edit_message(
        chat_id, msg_id,
        text,
        reply_markup=inline_keyboard([
            [("✏️ تیکت", "new_ticket")],
            [("🔙 بازگشت", "main_menu")]
        ])
    )


def handle_new_ticket(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    set_state(user_id, "ticket_subject")
    edit_message(
        chat_id, msg_id,
        "🎫 *تیکت جدید*\n\nموضوع تیکت را وارد کنید:",
        reply_markup=inline_keyboard([[("❌ انصراف", "ticket_menu")]])
    )


def handle_tickets_admin(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        tickets = conn.execute(
            "SELECT t.*, u.full_name FROM tickets t JOIN users u ON t.user_id=u.user_id WHERE t.status='open' ORDER BY t.created_at DESC LIMIT 15"
        ).fetchall()

    if not tickets:
        edit_message(chat_id, msg_id, "✅ تیکت باز وجود ندارد.", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
        return

    buttons = [[(f"#{t['id']} - {t['full_name']} - {t['subject'][:20]}", f"admin_view_ticket:{t['id']}")] for t in tickets]
    buttons.append([("🔙 پنل مدیریت", "admin_panel")])
    edit_message(chat_id, msg_id, f"🎫 *تیکت‌های باز* ({len(tickets)} تیکت):", reply_markup=inline_keyboard(buttons))


def handle_admin_view_ticket(query: dict, ticket_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        t = conn.execute(
            "SELECT t.*, u.full_name, u.username FROM tickets t JOIN users u ON t.user_id=u.user_id WHERE t.id=?",
            (ticket_id,)
        ).fetchone()

    if not t:
        answer_callback(query["id"], "تیکت یافت نشد!", True)
        return

    text = (
        f"🎫 *تیکت #{t['id']}*\n\n"
        f"👤 کاربر: {t['full_name']} (@{t['username'] or 'ندارد'})\n"
        f"📌 موضوع: {t['subject']}\n"
        f"📝 پیام:\n{t['message']}\n\n"
        f"🕐 ارسال: {t['created_at'][:16] if t['created_at'] else 'نامشخص'}"
    )

    set_state(admin_id, "admin_reply_ticket", {"ticket_id": ticket_id, "user_id": t["user_id"]})
    edit_message(
        chat_id, msg_id,
        text,
        reply_markup=inline_keyboard([
            [("💬 پاسخ دادن", f"admin_reply_ticket:{ticket_id}")],
            [("✅ بستن تیکت", f"admin_close_ticket:{ticket_id}")],
            [("🔙 تیکت‌ها", "tickets_admin")]
        ])
    )


# ─────────────────────────────────────────────
#  چالش‌های کد
# ─────────────────────────────────────────────
def handle_challenges(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        challenges = conn.execute(
            "SELECT * FROM code_challenges WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()

    if not challenges:
        edit_message(
            chat_id, msg_id,
            "🎯 *چالش‌های کد*\n\nهیچ چالش فعالی وجود ندارد.",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]])
        )
        return

    buttons = [[(f"🏆 {c['title']}", f"view_challenge:{c['id']}")] for c in challenges]
    buttons.append([("🔙 بازگشت", "main_menu")])
    edit_message(chat_id, msg_id, "🎯 *چالش‌های کد*\n\nچالش مورد نظر را انتخاب کنید:", reply_markup=inline_keyboard(buttons))


def handle_challenge_admin(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    edit_message(
        chat_id, msg_id,
        "🏆 *مدیریت چالش‌های کد*",
        reply_markup=inline_keyboard([
            [("➕ چالش جدید", "new_challenge"), ("📋 لیست چالش‌ها", "list_challenges_admin")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )


def handle_list_challenges_admin(query: dict):
    """FIX: تابع لیست چالش‌ها که قبلاً تعریف نشده بود"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        challenges = conn.execute(
            "SELECT * FROM code_challenges ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

    if not challenges:
        edit_message(chat_id, msg_id, "هیچ چالشی وجود ندارد.", reply_markup=inline_keyboard([[("🔙 بازگشت", "challenge_admin")]]))
        return

    text = "📋 *لیست چالش‌ها*\n\n"
    for c in challenges:
        status_icon = {"active": "🟢", "closed": "🔴", "finished": "⚫"}.get(c["status"], "❓")
        text += f"{status_icon} #{c['id']} - {c['title']}\n"

    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 بازگشت", "challenge_admin")]]))


# ─────────────────────────────────────────────
#  قرعه‌کشی
# ─────────────────────────────────────────────
def handle_lottery_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        lotteries = conn.execute(
            "SELECT * FROM lotteries WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()

    if not lotteries:
        edit_message(
            chat_id, msg_id,
            "🎪 *قرعه‌کشی*\n\nهیچ قرعه‌کشی فعالی وجود ندارد.",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]])
        )
        return

    buttons = [[(f"🎪 {l['title']} (نیاز: {l['min_points']} امتیاز)", f"join_lottery:{l['id']}")] for l in lotteries]
    buttons.append([("🔙 بازگشت", "main_menu")])
    edit_message(chat_id, msg_id, "🎪 *قرعه‌کشی‌های فعال*\n\nبرای شرکت روی نام بزنید:", reply_markup=inline_keyboard(buttons))


def handle_join_lottery(query: dict, lottery_id: int):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        lottery = conn.execute("SELECT * FROM lotteries WHERE id=? AND status='active'", (lottery_id,)).fetchone()

    if not lottery:
        answer_callback(query["id"], "قرعه‌کشی یافت نشد یا پایان یافته!", True)
        return

    points = get_points(user_id)
    if points < lottery["min_points"]:
        edit_message(
            chat_id, msg_id,
            f"❌ امتیاز کافی ندارید!\nنیاز: *{lottery['min_points']}*\nموجودی: *{points}*",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "lottery_menu")]])
        )
        return

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM lottery_entries WHERE lottery_id=? AND user_id=?",
            (lottery_id, user_id)
        ).fetchone()
        if existing:
            answer_callback(query["id"], "قبلاً ثبت‌نام کرده‌اید!", True)
            return
        conn.execute(
            "INSERT INTO lottery_entries (lottery_id, user_id, entered_at) VALUES (?,?,?)",
            (lottery_id, user_id, datetime.now().isoformat())
        )
        conn.commit()

    edit_message(
        chat_id, msg_id,
        f"✅ *ثبت‌نام در قرعه‌کشی*\n\n«{lottery['title']}» موفقیت‌آمیز بود!\n\nجایزه: {lottery['prize']}",
        reply_markup=inline_keyboard([[("🔙 بازگشت", "lottery_menu")]])
    )


def handle_lottery_admin(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    edit_message(
        chat_id, msg_id,
        "🎪 *مدیریت قرعه‌کشی*",
        reply_markup=inline_keyboard([
            [("➕ قرعه‌کشی جدید", "new_lottery"), ("🎲 انجام قرعه‌کشی", "draw_lottery")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )


def draw_lottery(lottery_id: int, admin_id: int):
    """انجام قرعه‌کشی - هر ورودی یک شانس (weighted)"""
    with get_db() as conn:
        lottery = conn.execute("SELECT * FROM lotteries WHERE id=?", (lottery_id,)).fetchone()
        # تمام ورودی‌ها (با تکرار برای شانس بیشتر)
        entries = conn.execute(
            "SELECT le.user_id, u.full_name FROM lottery_entries le JOIN users u ON le.user_id=u.user_id WHERE le.lottery_id=?",
            (lottery_id,)
        ).fetchall()

    if not entries:
        send_message(admin_id, "❌ هیچ شرکت‌کننده‌ای وجود ندارد!")
        return

    # اگر max_winners از تعداد کل ورودی‌ها بیشتر بود، کل را برنده کن
    max_w = min(lottery["max_winners"], len(entries))
    # انتخاب تصادفی با وزن (هر ورودی یک شانس)
    all_entries = list(entries)
    random.shuffle(all_entries)
    # برندگان یکتا
    seen_users = set()
    winners = []
    for e in all_entries:
        if e["user_id"] not in seen_users:
            winners.append(e)
            seen_users.add(e["user_id"])
        if len(winners) >= max_w:
            break

    with get_db() as conn:
        conn.execute(
            "UPDATE lotteries SET status='drawn', drawn_at=? WHERE id=?",
            (datetime.now().isoformat(), lottery_id)
        )
        conn.commit()

    winner_text = "\n".join([f"🏆 {w['full_name']}" for w in winners])
    msg = f"🎉 *نتایج قرعه‌کشی «{lottery['title']}»*\n\nبرندگان:\n{winner_text}"

    for aid in get_admin_ids():
        send_message(aid, msg)

    for winner in winners:
        add_points(winner["user_id"], 50, "برنده قرعه‌کشی")
        send_message(winner["user_id"], f"🎊 تبریک! شما در قرعه‌کشی «{lottery['title']}» برنده شدید!\nجایزه: {lottery['prize']}")


# ─────────────────────────────────────────────
#  کتابخانه اختصاصی
# ─────────────────────────────────────────────
def handle_custom_lib(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    u = get_user(user_id)
    plan = PLANS.get(u["plan"] if u else "free", PLANS["free"])

    if not plan["custom_library"]:
        edit_message(
            chat_id, msg_id,
            "❌ این قابلیت برای پلن شما فعال نیست.\nبرای دسترسی به کتابخانه اختصاصی، پلن حرفه‌ای یا بالاتر را تهیه کنید.",
            reply_markup=inline_keyboard([[("💳 ارتقای پلن", "sub_menu"), ("🔙 بازگشت", "main_menu")]])
        )
        return

    with get_db() as conn:
        libs = conn.execute("SELECT * FROM custom_libraries WHERE user_id=?", (user_id,)).fetchall()

    text = "🔑 *کتابخانه اختصاصی*\n\nدر اینجا می‌توانید متدها و کتابخانه‌های سفارشی تعریف کنید.\n"
    text += "حتی می‌توانید نام‌ها را به فارسی تغییر دهید!\n\n"

    if libs:
        text += "کتابخانه‌های شما:\n"
        for l in libs:
            text += f"📚 {l['lib_name']} (کلید: `{l['lib_key']}`)\n"

    buttons = [
        [("➕ کتابخانه جدید", "new_custom_lib"), ("🔑 کلید", "use_lib_key")],
        [("🔙 بازگشت", "main_menu")]
    ]
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_new_custom_lib(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    set_state(user_id, "custom_lib_name")
    edit_message(
        chat_id, msg_id,
        "📚 *کتابخانه اختصاصی جدید*\n\nنام کتابخانه را وارد کنید:\n(می‌توانید فارسی باشد، مثلاً: کتابخانه_من)",
        reply_markup=inline_keyboard([[("❌ انصراف", "custom_lib")]])
    )


def process_custom_lib_code(code: str, lib_mappings: dict) -> str:
    """پردازش کد با mapping های سفارشی"""
    processed = code
    for custom_name, real_name in lib_mappings.items():
        processed = processed.replace(custom_name, real_name)
    return processed


# ─────────────────────────────────────────────
#  کاربران برتر
# ─────────────────────────────────────────────
def handle_top_users(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        top_points = conn.execute(
            "SELECT full_name, points FROM users WHERE is_active=1 ORDER BY points DESC LIMIT 10"
        ).fetchall()
        top_invites = conn.execute(
            "SELECT full_name, invite_count FROM users WHERE is_active=1 ORDER BY invite_count DESC LIMIT 5"
        ).fetchall()
        top_bots = conn.execute(
            "SELECT u.full_name, COUNT(b.id) as c FROM deployed_bots b JOIN users u ON b.user_id=u.user_id GROUP BY b.user_id ORDER BY c DESC LIMIT 5"
        ).fetchall()

    text = "🏆 *کاربران برتر*\n\n"
    text += "*🥇 برترین‌ها بر اساس امتیاز:*\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_points):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {u['full_name']}: *{u['points']}* امتیاز\n"

    text += "\n*👥 بیشترین دعوت:*\n"
    for i, u in enumerate(top_invites):
        text += f"{i+1}. {u['full_name']}: *{u['invite_count']}* نفر\n"

    text += "\n*🤖 بیشترین ربات:*\n"
    for i, u in enumerate(top_bots):
        text += f"{i+1}. {u['full_name']}: *{u['c']}* ربات\n"

    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))


# ─────────────────────────────────────────────
#  پروفایل کاربر
# ─────────────────────────────────────────────
def handle_my_profile(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    u = get_user(user_id)
    if not u:
        answer_callback(query["id"], "خطا در دریافت اطلاعات!", True)
        return

    plan = PLANS.get(u["plan"], PLANS["free"])

    with get_db() as conn:
        bot_count = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE user_id=?", (user_id,)).fetchone()["c"]
        lib_count = conn.execute("SELECT COUNT(*) as c FROM library_installs WHERE user_id=? AND status='installed'", (user_id,)).fetchone()["c"]

    text = (
        f"👤 *پروفایل شما*\n\n"
        f"نام: *{u['full_name']}*\n"
        f"آیدی: `{user_id}`\n"
        f"پلن: *{plan['name']}*\n"
        f"انقضای پلن: {u['plan_expires_at'][:10] if u['plan_expires_at'] else 'ندارد'}\n\n"
        f"💰 امتیاز: *{u['points']}*\n"
        f"🤖 ربات‌ها: *{bot_count}*\n"
        f"📦 کتابخانه‌ها: *{lib_count}*\n"
        f"👥 دعوت‌ها: *{u['invite_count']}*\n"
        f"💳 کل خرید: *{u['total_spent']:,}* تومان\n\n"
        f"📈 آیتم‌های اضافه:\n"
        f"• ربات: +{u['extra_bots']}\n"
        f"• حافظه: +{u['extra_memory_mb']} MB\n"
        f"• کتابخانه: +{u['extra_libraries']}\n"
    )

    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))


# ─────────────────────────────────────────────
#  امتیازها و پنل امتیاز
# ─────────────────────────────────────────────
def handle_points_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)

    text = (
        f"🎯 *سیستم امتیاز*\n\n"
        f"💰 امتیاز شما: *{u['points'] if u else 0}*\n\n"
        f"*روش‌های کسب امتیاز:*\n"
        f"• هر ۱۰۰۰ تومان خرید: ۱ امتیاز\n"
        f"• دعوت موفق: ۵ امتیاز\n"
        f"• برنده چالش: ۵۰ امتیاز\n"
        f"• برنده هفته (اول): ۳۰ امتیاز\n"
        f"• برنده هفته (دوم): ۲۰ امتیاز\n"
        f"• برنده هفته (سوم): ۱۰ امتیاز\n\n"
        f"*استفاده از امتیاز:*\n"
        f"• خرید آیتم از فروشگاه\n"
        f"• شرکت در قرعه‌کشی\n"
        f"• دریافت کد تخفیف یک‌بار مصرف"
    )

    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("🏪 فروشگاه آیتم", "shop_menu"), ("🎪 قرعه‌کشی", "lottery_menu")],
        [("🎟 تخفیف", "redeem_points_discount")],
        [("🔙 بازگشت", "main_menu")]
    ]))


# ─────────────────────────────────────────────
#  پنل مدیریت - تخفیف‌ها
# ─────────────────────────────────────────────
def handle_discount_panel(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    edit_message(
        chat_id, msg_id,
        "🎟 *مدیریت کدهای تخفیف*",
        reply_markup=inline_keyboard([
            [("➕ کد تخفیف ویژه", "create_discount:special")],
            [("⏰ کد تخفیف ساعتی", "create_discount:hourly")],
            [("📅 تخفیف", "create_discount:occasion")],
            [("📋 لیست کدها", "list_discounts")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )


def create_discount_code(
    type_: str,
    value: int,
    is_percent: bool,
    created_by: int,
    max_uses: int = 1,
    expires_at: str = None,
    plan_target: str = None
) -> str:
    code = "PORO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO discount_codes (code, type, value, is_percent, max_uses, expires_at, created_by, plan_target) VALUES (?,?,?,?,?,?,?,?)",
            (code, type_, value, 1 if is_percent else 0, max_uses, expires_at, created_by, plan_target)
        )
        conn.commit()
    return code


# ─────────────────────────────────────────────
#  پنل مدیریت - مدیریت اشتراک‌ها
# ─────────────────────────────────────────────
def handle_subscription_mgmt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    text = "💳 *مدیریت اشتراک‌ها*\n\n"
    buttons = []
    with get_db() as conn:
        for plan_key, plan_data in PLANS.items():
            total = conn.execute("SELECT COUNT(*) as c FROM payments WHERE plan=? AND status='paid'", (plan_key,)).fetchone()["c"]
            active = conn.execute("SELECT COUNT(*) as c FROM users WHERE plan=?", (plan_key,)).fetchone()["c"]
            revenue_row = conn.execute("SELECT SUM(amount) as s FROM payments WHERE plan=? AND status='paid'", (plan_key,)).fetchone()
            revenue = revenue_row["s"] or 0
            text += f"*{plan_data['name']}*\n  خریداری شده: {total} | فعال: {active} | درآمد: {revenue:,}T\n\n"
            buttons.append([(f"👥 خریداران {plan_data['name']}", f"plan_subscribers:{plan_key}:0")])

    buttons.append([("🔙 پنل مدیریت", "admin_panel")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_plan_subscribers(query: dict, plan_key: str, page: int = 0):
    """نمایش لیست کاربرانی که یک پلن خاص را خریداری کرده‌اند"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    page_size = 20
    offset = page * page_size
    plan_name = PLANS.get(plan_key, {}).get("name", plan_key)

    with get_db() as conn:
        total_count = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM payments WHERE plan=? AND status='paid'", (plan_key,)
        ).fetchone()["c"]
        subscribers = conn.execute(
            """SELECT u.user_id, u.full_name, u.username, u.plan, COUNT(p.id) as buy_count, SUM(p.amount) as total_paid
               FROM payments p JOIN users u ON p.user_id=u.user_id
               WHERE p.plan=? AND p.status='paid'
               GROUP BY p.user_id ORDER BY total_paid DESC LIMIT ? OFFSET ?""",
            (plan_key, page_size, offset)
        ).fetchall()

    if not subscribers:
        edit_message(chat_id, msg_id, f"هیچ خریداری برای پلن {plan_name} یافت نشد.",
                     reply_markup=inline_keyboard([[("🔙 مدیریت اشتراک", "subscription_mgmt")]]))
        return

    text = f"👥 *خریداران پلن {plan_name}*\n\n"
    buttons = []
    for sub in subscribers:
        uname = f"@{sub['username']}" if sub["username"] else str(sub["user_id"])
        text_btn = f"👤 {sub['full_name']} | {uname} | {sub['buy_count']}× | {(sub['total_paid'] or 0):,}T"
        buttons.append([(text_btn, f"admin_user_detail:{sub['user_id']}")])

    total_pages = (total_count + page_size - 1) // page_size
    nav = []
    if page > 0:
        nav.append(("◀️ قبل", f"plan_subscribers:{plan_key}:{page - 1}"))
    if (page + 1) < total_pages:
        nav.append(("بعد ▶️", f"plan_subscribers:{plan_key}:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([("🔙 مدیریت اشتراک", "subscription_mgmt")])
    text += f"صفحه {page + 1}/{total_pages} | کل: {total_count} خریدار"
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


# ─────────────────────────────────────────────
#  پنل مدیریت - درآمد
# ─────────────────────────────────────────────
def handle_revenue_panel(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        total_rev_row = conn.execute("SELECT SUM(amount) as s FROM payments WHERE status='paid'").fetchone()
        total_revenue = total_rev_row["s"] or 0
        this_month_start = datetime.now().replace(day=1).isoformat()
        month_rev_row = conn.execute(
            "SELECT SUM(amount) as s FROM payments WHERE status='paid' AND created_at>=?",
            (this_month_start,)
        ).fetchone()
        month_revenue = month_rev_row["s"] or 0
        this_week_start = (datetime.now() - timedelta(days=7)).isoformat()
        week_rev_row = conn.execute(
            "SELECT SUM(amount) as s FROM payments WHERE status='paid' AND created_at>=?",
            (this_week_start,)
        ).fetchone()
        week_revenue = week_rev_row["s"] or 0
        plan_breakdown = conn.execute(
            "SELECT plan, SUM(amount) as s, COUNT(*) as c FROM payments WHERE status='paid' GROUP BY plan"
        ).fetchall()

    text = (
        f"💰 *گزارش درآمد*\n\n"
        f"کل درآمد: *{total_revenue:,}* تومان\n"
        f"درآمد این ماه: *{month_revenue:,}* تومان\n"
        f"درآمد این هفته: *{week_revenue:,}* تومان\n\n"
        f"*جزئیات پلن‌ها:*\n"
    )
    for row in plan_breakdown:
        text += f"• {PLANS.get(row['plan'], {}).get('name', row['plan'])}: {row['s']:,}T ({row['c']} تراکنش)\n"

    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))


# ─────────────────────────────────────────────
#  پنل مدیریت - توکن پرداخت
# ─────────────────────────────────────────────
def handle_payment_token_panel(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    current_token = get_setting("payment_token", PAYMENT_TOKEN)
    masked = current_token[:10] + "..." + current_token[-5:] if len(current_token) > 15 else current_token

    edit_message(
        chat_id, msg_id,
        f"💳 *توکن پرداخت*\n\nتوکن فعلی: `{masked}`",
        reply_markup=inline_keyboard([
            [("✏️ تغییر توکن", "change_payment_token")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )


def handle_change_payment_token(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    set_state(admin_id, "change_payment_token")
    edit_message(
        chat_id, msg_id,
        "💳 *تغییر توکن پرداخت*\n\nتوکن جدید را ارسال کنید:",
        reply_markup=inline_keyboard([[("❌ انصراف", "payment_token_panel")]])
    )


# ─────────────────────────────────────────────
#  پنل مدیریت - تنظیمات ربات
# ─────────────────────────────────────────────


def handle_change_channel(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_change_channel")
    edit_message(chat_id, msg_id,
                 "📢 *تغییر کانال*\n\nیوزرنیم کانال جدید را ارسال کنید:\n(مثال: `@my_channel`)",
                 reply_markup=inline_keyboard([[("❌ انصراف", "admin_settings")]]))


def handle_change_invite_base(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    current = get_setting("invite_base", INVITE_BASE)
    set_state(admin_id, "admin_change_invite_base")
    edit_message(chat_id, msg_id,
                 f"🔗 *تغییر لینک پایه دعوت*\n\nلینک فعلی: `{current}`\n\nلینک جدید را ارسال کنید:",
                 reply_markup=inline_keyboard([[("❌ انصراف", "admin_settings")]]))


def handle_change_required_invites(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    current = get_setting("required_invites", str(REQUIRED_INVITES))
    set_state(admin_id, "admin_change_required_invites")
    edit_message(chat_id, msg_id,
                 f"👥 *تعداد دعوت لازم برای فعال‌سازی*\n\nمقدار فعلی: *{current}*\n\nعدد جدید را ارسال کنید:",
                 reply_markup=inline_keyboard([[("❌ انصراف", "admin_settings")]]))


def handle_change_prices(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    buttons = []
    for plan_key, plan_data in PLANS.items():
        if plan_key in ("free", "enterprise"):
            continue
        buttons.append([(f"{plan_data['name']}", f"change_plan_price:{plan_key}")])
    buttons.append([("🔙 تنظیمات", "admin_settings")])
    edit_message(chat_id, msg_id,
                 "💰 *تغییر قیمت‌ها*\n\nپلن مورد نظر را انتخاب کنید:",
                 reply_markup=inline_keyboard(buttons))


def handle_change_plan_price(query: dict, plan_key: str):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    plan = PLANS.get(plan_key)
    if not plan:
        answer_callback(query["id"], "پلن یافت نشد!", True)
        return
    buttons = []
    dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه", "biannual": "شش ماهه", "annual": "یک ساله"}
    for dur, sub in plan["subscriptions"].items():
        if sub["price"] != -1:
            current_price = get_setting(f"price_{plan_key}_{dur}", str(sub["price"]))
            buttons.append([(f"✏️ {dur_fa.get(dur, dur)} (فعلی: {int(current_price):,}T)",
                              f"edit_price:{plan_key}:{dur}")])
    buttons.append([("🔙 تغییر قیمت‌ها", "change_prices")])
    edit_message(chat_id, msg_id,
                 f"💰 *تغییر قیمت پلن {plan['name']}*\n\nدوره مورد نظر را انتخاب کنید:",
                 reply_markup=inline_keyboard(buttons))


def handle_edit_price(query: dict, plan_key: str, duration: str):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه", "biannual": "شش ماهه", "annual": "یک ساله"}
    current = get_setting(f"price_{plan_key}_{duration}",
                          str(PLANS[plan_key]["subscriptions"][duration]["price"]))
    set_state(admin_id, "admin_edit_price", {"plan_key": plan_key, "duration": duration})
    edit_message(chat_id, msg_id,
                 f"💰 *تغییر قیمت*\n\nپلن: *{PLANS[plan_key]['name']}*\n"
                 f"دوره: *{dur_fa.get(duration, duration)}*\n"
                 f"قیمت فعلی: *{int(current):,} تومان*\n\n"
                 f"قیمت جدید (تومان) را ارسال کنید:",
                 reply_markup=inline_keyboard([[("❌ انصراف", f"change_plan_price:{plan_key}")]]))


# ─────────────────────────────────────────────
#  تایید/رد درخواست سازمانی
# ─────────────────────────────────────────────
def handle_admin_approve_enterprise(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "این درخواست قبلاً پردازش شده!", True)
        return

    user_id = req["user_id"]

    with get_db() as conn:
        conn.execute("UPDATE pending_requests SET status='approved' WHERE id=?", (req_id,))
        conn.execute(
            "UPDATE users SET plan='enterprise', is_active=1 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()

    edit_message(chat_id, msg_id,
                 f"✅ درخواست سازمانی کاربر `{user_id}` تایید و پلن ارتقا یافت.",
                 reply_markup=inline_keyboard([[("✅ تایید شد", "noop")]]))

    send_message(
        user_id,
        "🎉 *درخواست پنل سازمانی شما تایید شد!*\n\n"
        "✅ حساب شما به پلن *سازمانی* ارتقا یافت.\n"
        "به زودی تیم پشتیبانی با شما تماس می‌گیرد.",
        reply_markup=main_menu(user_id)
    )


def handle_admin_reject_enterprise(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "این درخواست قبلاً پردازش شده!", True)
        return

    user_id = req["user_id"]
    with get_db() as conn:
        conn.execute("UPDATE pending_requests SET status='rejected' WHERE id=?", (req_id,))
        conn.commit()

    edit_message(chat_id, msg_id,
                 f"❌ درخواست سازمانی کاربر `{user_id}` رد شد.",
                 reply_markup=inline_keyboard([[("❌ رد شد", "noop")]]))

    send_message(user_id,
                 "❌ *متأسفانه درخواست پنل سازمانی شما در این مرحله تایید نشد.*\n\n"
                 "برای اطلاعات بیشتر یا ارسال مجدد درخواست، با پشتیبانی تماس بگیرید.")


# ─────────────────────────────────────────────
#  درخواست‌های در انتظار مدیر
# ─────────────────────────────────────────────
def handle_pending_requests(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        reqs = conn.execute(
            "SELECT pr.*, u.full_name FROM pending_requests pr JOIN users u ON pr.user_id=u.user_id WHERE pr.status='pending' ORDER BY pr.created_at DESC LIMIT 20"
        ).fetchall()

    if not reqs:
        edit_message(
            chat_id, msg_id,
            "✅ هیچ درخواست در انتظاری وجود ندارد.",
            reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]])
        )
        return

    type_fa = {"deploy": "🚀 استقرار", "install_lib": "📦 نصب", "enterprise": "⚫ سازمانی"}
    buttons = [[(f"{type_fa.get(r['type'], r['type'])} - {r['full_name']}", f"view_request:{r['id']}")] for r in reqs]
    buttons.append([("🔙 پنل مدیریت", "admin_panel")])

    edit_message(
        chat_id, msg_id,
        f"⏳ *درخواست‌های در انتظار* ({len(reqs)} درخواست):",
        reply_markup=inline_keyboard(buttons)
    )


def handle_view_request(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        req = conn.execute(
            "SELECT pr.*, u.full_name FROM pending_requests pr JOIN users u ON pr.user_id=u.user_id WHERE pr.id=?",
            (req_id,)
        ).fetchone()

    if not req:
        answer_callback(query["id"], "درخواست یافت نشد!", True)
        return

    req_data = json.loads(req["data"])
    text = f"📋 *درخواست #{req_id}*\n\nنوع: {req['type']}\nکاربر: {req['full_name']} (`{req['user_id']}`)\n\n"
    for k, v in req_data.items():
        text += f"• {k}: `{v}`\n"

    type_approve_map = {
        "deploy": f"admin_approve_deploy:{req_id}",
        "install_lib": f"admin_approve_lib:{req_id}",
        "enterprise": f"admin_approve_enterprise:{req_id}"
    }
    type_reject_map = {
        "deploy": f"admin_reject_deploy:{req_id}",
        "install_lib": f"admin_reject_lib:{req_id}",
        "enterprise": f"admin_reject_enterprise:{req_id}"
    }

    edit_message(
        chat_id, msg_id,
        text,
        reply_markup=inline_keyboard([
            [("✅ تایید", type_approve_map.get(req["type"], "noop")), ("❌ رد", type_reject_map.get(req["type"], "noop"))],
            [("🔙 درخواست‌ها", "pending_requests")]
        ])
    )


# ─────────────────────────────────────────────
#  ترمینال رنگی PDF
# ─────────────────────────────────────────────
def generate_colored_terminal_pdf(bot_id: int, user_id: int):
    """تولید PDF ترمینال رنگی"""
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=? AND user_id=?", (bot_id, user_id)).fetchone()

    if not bot or not bot["file_path"]:
        return

    try:
        with open(bot["file_path"], "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except:
        return

    colors = {
        "keyword": "#FF6B9D",
        "string": "#C3E88D",
        "comment": "#546E7A",
        "number": "#F78C6C",
        "function": "#82AAFF",
        "class": "#FFCB6B",
        "decorator": "#C792EA",
        "default": "#EEFFFF"
    }

    keywords = {"def", "class", "import", "from", "return", "if", "else", "elif",
                "for", "while", "try", "except", "with", "as", "in", "not", "and", "or",
                "True", "False", "None", "lambda", "yield", "async", "await", "pass", "break", "continue"}

    def colorize_line(line: str) -> str:
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            return f'<span style="color:{colors["comment"]}">{line.rstrip()}</span>'
        parts = []
        for word in re.split(r'(\s+|[().,\[\]{}:=+\-*/<>!])', line.rstrip()):
            if word in keywords:
                parts.append(f'<span style="color:{colors["keyword"]}">{word}</span>')
            elif word.startswith('"') or word.startswith("'"):
                parts.append(f'<span style="color:{colors["string"]}">{word}</span>')
            elif word.isdigit():
                parts.append(f'<span style="color:{colors["number"]}">{word}</span>')
            elif word.startswith("@"):
                parts.append(f'<span style="color:{colors["decorator"]}">{word}</span>')
            else:
                parts.append(f'<span style="color:{colors["default"]}">{word}</span>')
        return "".join(parts)

    LINES_PER_IMAGE = 10
    pages = [lines[i:i+LINES_PER_IMAGE] for i in range(0, len(lines), LINES_PER_IMAGE)]

    html_pages = ""
    for page_num, page_lines in enumerate(pages, 1):
        lines_html = ""
        for i, line in enumerate(page_lines):
            abs_line = (page_num-1)*LINES_PER_IMAGE + i + 1
            colored = colorize_line(line)
            lines_html += f'<div class="line"><span class="ln">{abs_line:3}</span>{colored}</div>\n'

        html_pages += f"""
<div class="page">
  <div class="page-header">
    <span class="bot-name">🤖 {bot['bot_name']}</span>
    <span class="page-num">صفحه {page_num} از {len(pages)}</span>
  </div>
  <div class="code-block">
    {lines_html}
  </div>
</div>
"""

    html = f"""<!DOCTYPE html>
<html dir="ltr">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ background: #1E1E2E; font-family: 'Courier New', monospace; font-size: 11px; margin: 0; padding: 0; }}
  .page {{ page-break-after: always; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
  .page-header {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #313244; border-radius: 6px; margin-bottom: 10px; }}
  .bot-name {{ color: #CBA6F7; font-weight: bold; font-size: 13px; }}
  .page-num {{ color: #A6ADC8; font-size: 11px; }}
  .code-block {{ background: #181825; padding: 10px; border-radius: 6px; border: 1px solid #313244; }}
  .line {{ line-height: 1.7; white-space: pre; }}
  .ln {{ color: #585B70; margin-right: 12px; user-select: none; }}
</style>
</head>
<body>
{html_pages}
</body>
</html>"""

    html_path = LOGS_DIR / f"terminal_{bot_id}.html"
    pdf_path = LOGS_DIR / f"terminal_{bot_id}.pdf"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        subprocess.run(
            ["wkhtmltopdf", "--page-size", "A4", str(html_path), str(pdf_path)],
            capture_output=True, timeout=60
        )
    except FileNotFoundError:
        send_document(user_id, html_path, f"📟 ترمینال رنگی ربات *{bot['bot_name']}*")
        return
    except Exception as e:
        log.error(f"PDF error: {e}")
        return

    if pdf_path.exists():
        send_document(user_id, pdf_path, f"📟 ترمینال رنگی ربات *{bot['bot_name']}*")


# ─────────────────────────────────────────────
#  تنظیم هفتگی خودکار
# ─────────────────────────────────────────────
def weekly_scheduler():
    """ارسال خودکار آمار هفتگی"""
    while True:
        now = datetime.now()
        if now.weekday() == 5 and now.hour == 9 and now.minute == 0:
            handle_weekly_stats_send()  # بدون query → ارسال به مدیران
            announce_weekly_winners()
            time.sleep(70)
        else:
            time.sleep(30)


def announce_weekly_winners():
    """اعلان برندگان هفتگی"""
    with get_db() as conn:
        top_users = conn.execute(
            "SELECT user_id, full_name, points FROM users WHERE is_active=1 ORDER BY points DESC LIMIT 3"
        ).fetchall()

    prizes = [30, 20, 10]
    medals = ["🥇", "🥈", "🥉"]
    discounts = [30, 20, 10]

    msg = "🏆 *برندگان هفته اعلام شدند!*\n\n"
    for i, u in enumerate(top_users):
        prize_points = prizes[i]
        discount = discounts[i]
        add_points(u["user_id"], prize_points, "برنده هفته")
        dc_code = create_discount_code(
            "weekly_winner", discount, True, ADMIN_IDS[0],
            max_uses=1, plan_target=None
        )
        send_message(
            u["user_id"],
            f"🎉 {medals[i]} شما برنده هفته شدید!\n"
            f"🎁 {prize_points} امتیاز هدیه داده شد.\n"
            f"🎟 کد تخفیف {discount}٪ شما: `{dc_code}`"
        )
        msg += f"{medals[i]} {u['full_name']} (+{prize_points} امتیاز)\n"

    for admin_id in ADMIN_IDS:
        send_message(admin_id, msg)


# ─────────────────────────────────────────────
#  پردازش callback_query
# ─────────────────────────────────────────────
def handle_callback_query(update: dict):
    query = update["callback_query"]
    user_id = query["from"]["id"]
    data = query.get("data", "")
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    answer_callback(query["id"])

    # بررسی مسدودی
    u = get_user(user_id)
    if u and u["is_blocked"] and not is_admin(user_id):
        send_message(chat_id, f"❌ حساب شما مسدود است.\nدلیل: {u['block_reason'] or 'نامشخص'}")
        return

    # روتینگ callback
    if data == "main_menu":
        edit_message(chat_id, msg_id, "🏠 *منوی اصلی*\n\nانتخاب کنید:", reply_markup=main_menu(user_id))
    elif data == "bots_menu":
        handle_bots_menu(query)
    elif data.startswith("bot_info:"):
        handle_bot_info(query, int(data.split(":")[1]))
    elif data.startswith("delete_bot_confirm:"):
        handle_delete_bot_confirm(query, int(data.split(":")[1]))
    elif data.startswith("delete_bot_final:"):
        handle_delete_bot_final(query, int(data.split(":")[1]))
    elif data == "deploy_new":
        if not is_active_user(user_id) and not is_admin(user_id):
            answer_callback(query["id"], "ابتدا ربات را فعال کنید!", True)
            return
        handle_deploy_new(query)
    elif data == "deploy_submit":
        handle_deploy_submit(query)
    elif data == "install_lib":
        if not is_active_user(user_id) and not is_admin(user_id):
            answer_callback(query["id"], "ابتدا ربات را فعال کنید!", True)
            return
        handle_install_lib(query)
    elif data == "shop_menu":
        handle_shop_menu(query)
    elif data.startswith("buy_item:"):
        handle_buy_item(query, data.split(":")[1])
    elif data == "sub_menu":
        handle_sub_menu(query)
    elif data.startswith("view_plan:"):
        handle_view_plan(query, data.split(":")[1])
    elif data.startswith("checkout:"):
        parts = data.split(":")
        handle_checkout(query, parts[1], parts[2])
    elif data.startswith("pay_now:"):
        parts = data.split(":")
        handle_pay_now(query, parts[1], parts[2], int(parts[3]))
    elif data == "points_menu":
        handle_points_menu(query)
    elif data == "top_users":
        handle_top_users(query)
    elif data == "challenges":
        handle_challenges(query)
    elif data == "lottery_menu":
        handle_lottery_menu(query)
    elif data.startswith("join_lottery:"):
        handle_join_lottery(query, int(data.split(":")[1]))
    elif data == "ticket_menu":
        handle_ticket_menu(query)
    elif data == "new_ticket":
        handle_new_ticket(query)
    elif data == "custom_lib":
        handle_custom_lib(query)
    elif data == "new_custom_lib":
        handle_new_custom_lib(query)
    elif data == "my_invite":
        invite_count = u["invite_count"] if u else 0
        link = get_invite_link(user_id)
        edit_message(
            chat_id, msg_id,
            f"🔗 *لینک دعوت شما*\n\n`{link}`\n\n"
            f"دعوت‌های موفق: *{invite_count}*\n"
            f"امتیاز هر دعوت: *۵ امتیاز*"
        )
    elif data == "my_profile":
        handle_my_profile(query)
    elif data == "my_stats":
        handle_my_profile(query)
    elif data == "check_activation":
        ok, reason = check_activation(user_id)
        if ok:
            activate_user(user_id)
        else:
            answer_callback(query["id"], f"هنوز شرایط کامل نشده: {reason}", True)
    elif data == "joined_channel":
        with get_db() as conn:
            conn.execute("UPDATE users SET channel_joined=1 WHERE user_id=?", (user_id,))
            conn.commit()
        ok, reason = check_activation(user_id)
        if ok:
            activate_user(user_id)
        else:
            answer_callback(query["id"], "ممنون! پس از تکمیل دعوت‌ها فعال می‌شوید.", True)

    # پنل مدیریت
    elif data == "admin_panel":
        handle_admin_panel(query)
    elif data == "broadcast_msg":
        handle_broadcast_msg(query)
    elif data == "realtime_stats":
        handle_realtime_stats(query)
    elif data == "weekly_stats":
        # FIX: query رو پاس می‌دیم تا مقدار return بشه
        msg = handle_weekly_stats_send(query)
        if msg:
            edit_message(chat_id, msg_id, msg, reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
    elif data == "pending_requests":
        handle_pending_requests(query)
    elif data.startswith("view_request:"):
        handle_view_request(query, int(data.split(":")[1]))
    elif data.startswith("admin_approve_deploy:"):
        handle_admin_approve_deploy(query, int(data.split(":")[1]))
    elif data.startswith("admin_reject_deploy:"):
        handle_admin_reject_deploy(query, int(data.split(":")[1]))
    elif data.startswith("admin_approve_lib:"):
        handle_admin_approve_lib(query, int(data.split(":")[1]))
    elif data.startswith("admin_reject_lib:"):
        # FIX: حالا تابع مستقل داره
        handle_admin_reject_lib(query, int(data.split(":")[1]))
    elif data.startswith("admin_approve_enterprise:"):
        handle_admin_approve_enterprise(query, int(data.split(":")[1]))
    elif data.startswith("admin_reject_enterprise:"):
        handle_admin_reject_enterprise(query, int(data.split(":")[1]))
    elif data == "revenue_panel":
        handle_revenue_panel(query)
    elif data == "user_management":
        handle_user_management(query)
    elif data == "search_user_prompt":
        handle_search_user_prompt(query)
    elif data.startswith("view_users_list:"):
        handle_view_users_list(query, int(data.split(":")[1]))
    elif data.startswith("admin_user_detail:"):
        handle_admin_user_detail(query, int(data.split(":")[1]))
    elif data.startswith("admin_block_user:"):
        handle_admin_block_user(query, int(data.split(":")[1]))
    elif data.startswith("block_confirm:"):
        parts = data.split(":")
        handle_block_confirm(query, int(parts[1]), parts[2])
    elif data.startswith("admin_unblock_user:"):
        target_id = int(data.split(":")[1])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_blocked=0, block_reason=NULL WHERE user_id=?", (target_id,))
            conn.commit()
        answer_callback(query["id"], "✅ رفع مسدودی انجام شد.", True)
        send_message(target_id, "✅ حساب شما رفع مسدودی شد. می‌توانید از ربات استفاده کنید.")
    elif data.startswith("admin_gift_points:"):
        target_id = int(data.split(":")[1])
        set_state(user_id, "admin_gift_points", {"target_id": target_id})
        send_message(chat_id, f"🎁 تعداد امتیاز هدیه به کاربر `{target_id}` را وارد کنید:")
    elif data.startswith("admin_send_user:"):
        target_id = int(data.split(":")[1])
        set_state(user_id, "admin_send_user_msg", {"target_id": target_id})
        send_message(chat_id, f"💬 پیام برای کاربر `{target_id}` را وارد کنید:")
    elif data.startswith("admin_change_plan:"):
        # FIX: حالا تابع مستقل داره
        handle_admin_change_plan(query, int(data.split(":")[1]))
    elif data.startswith("set_user_plan:"):
        parts = data.split(":")
        handle_set_user_plan(query, int(parts[1]), parts[2])
    elif data == "discount_panel":
        handle_discount_panel(query)
    elif data.startswith("create_discount:"):
        dtype = data.split(":")[1]
        set_state(user_id, f"create_discount_{dtype}")
        prompts = {
            "special": "🎟 ایجاد کد تخفیف ویژه\n\nمقدار تخفیف (درصد) را وارد کنید:\n(مثال: 20)",
            "hourly": "⏰ ایجاد کد تخفیف ساعتی\n\nمقدار تخفیف (درصد) را وارد کنید:",
            "occasion": "📅 ایجاد کد تخفیف مناسبتی\n\nمقدار تخفیف (درصد) را وارد کنید:"
        }
        send_message(chat_id, prompts.get(dtype, "مقدار تخفیف:"))
    elif data == "subscription_mgmt":
        handle_subscription_mgmt(query)
    elif data.startswith("plan_subscribers:"):
        parts = data.split(":")
        handle_plan_subscribers(query, parts[1], int(parts[2]))
    elif data == "payment_token_panel":
        handle_payment_token_panel(query)
    elif data == "change_payment_token":
        handle_change_payment_token(query)
    elif data == "lottery_admin":
        handle_lottery_admin(query)
    elif data == "challenge_admin":
        handle_challenge_admin(query)
    elif data == "list_challenges_admin":
        # FIX: حالا تابع مستقل داره
        handle_list_challenges_admin(query)
    elif data == "tickets_admin":
        handle_tickets_admin(query)
    elif data.startswith("admin_view_ticket:"):
        handle_admin_view_ticket(query, int(data.split(":")[1]))
    elif data.startswith("admin_reply_ticket:"):
        ticket_id = int(data.split(":")[1])
        with get_db() as conn:
            t = conn.execute("SELECT user_id FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        set_state(user_id, "admin_reply_ticket", {"ticket_id": ticket_id, "user_id": t["user_id"] if t else 0})
        send_message(chat_id, "💬 پاسخ خود را وارد کنید:")
    elif data.startswith("admin_close_ticket:"):
        ticket_id = int(data.split(":")[1])
        with get_db() as conn:
            conn.execute("UPDATE tickets SET status='closed' WHERE id=?", (ticket_id,))
            conn.commit()
        answer_callback(query["id"], "✅ تیکت بسته شد.", True)
    elif data == "admin_settings":
        handle_admin_settings(query)
    elif data == "change_channel":
        handle_change_channel(query)
    elif data == "change_invite_base":
        handle_change_invite_base(query)
    elif data == "change_required_invites":
        handle_change_required_invites(query)
    elif data == "change_prices":
        handle_change_prices(query)
    elif data.startswith("change_plan_price:"):
        handle_change_plan_price(query, data.split(":")[1])
    elif data.startswith("edit_price:"):
        parts = data.split(":")
        handle_edit_price(query, parts[1], parts[2])
    elif data.startswith("admin_deduct_points:"):
        target_id = int(data.split(":")[1])
        set_state(user_id, "admin_deduct_points", {"target_id": target_id})
        send_message(chat_id, f"➖ تعداد امتیاز کسر از کاربر `{target_id}` را وارد کنید:")
    elif data.startswith("view_log:"):
        bot_id = int(data.split(":")[1])
        with get_db() as conn:
            bot = conn.execute("SELECT * FROM deployed_bots WHERE id=? AND user_id=?", (bot_id, user_id)).fetchone()
        if bot and bot["log_file"] and Path(bot["log_file"]).exists():
            send_document(user_id, bot["log_file"], f"📋 لاگ ربات *{bot['bot_name']}*")
        else:
            answer_callback(query["id"], "فایل لاگ موجود نیست.", True)
    elif data.startswith("stop_bot:"):
        bot_id = int(data.split(":")[1])
        proc = bot_processes.get(bot_id)
        if proc:
            proc.terminate()
        with get_db() as conn:
            conn.execute("UPDATE deployed_bots SET status='stopped', pid=NULL WHERE id=?", (bot_id,))
            conn.commit()
        answer_callback(query["id"], "✅ ربات متوقف شد.")
    elif data.startswith("restart_bot:"):
        bot_id = int(data.split(":")[1])
        with get_db() as conn:
            bot = conn.execute("SELECT * FROM deployed_bots WHERE id=? AND user_id=?",
                               (bot_id, user_id)).fetchone()
        if bot:
            old_proc = bot_processes.get(bot_id)
            if old_proc:
                try:
                    old_proc.terminate()
                    old_proc.wait(timeout=5)
                except Exception:
                    pass
            start_bot_process(bot_id, bot["file_path"], bot["bot_name"], user_id)
            with get_db() as conn:
                conn.execute("UPDATE deployed_bots SET status='running' WHERE id=?", (bot_id,))
                conn.commit()
            answer_callback(query["id"], "✅ ربات مجدداً راه‌اندازی شد.")
            edit_message(
                chat_id, msg_id,
                f"♻️ *راه‌اندازی مجدد موفق!*\n\n"
                f"🤖 ربات *{bot['bot_name']}* مجدداً راه‌اندازی شد.\n"
                f"✅ وضعیت: در حال اجرا",
                reply_markup=inline_keyboard([
                    [("📋 مشاهده لاگ", f"view_log:{bot_id}"), ("⏹ توقف", f"stop_bot:{bot_id}")],
                    [("🔙 لیست ربات‌ها", "bots_menu")]
                ])
            )
        else:
            answer_callback(query["id"], "❌ ربات یافت نشد!", True)
    elif data == "new_lottery" and is_admin(user_id):
        set_state(user_id, "new_lottery_title")
        send_message(chat_id, "🎪 *قرعه‌کشی جدید*\n\nعنوان قرعه‌کشی را وارد کنید:")
    elif data == "draw_lottery" and is_admin(user_id):
        with get_db() as conn:
            lotteries = conn.execute("SELECT * FROM lotteries WHERE status='active'").fetchall()
        if not lotteries:
            answer_callback(query["id"], "قرعه‌کشی فعالی وجود ندارد!", True)
            return
        buttons = [[(f"🎪 {l['title']}", f"do_draw:{l['id']}")] for l in lotteries]
        buttons.append([("🔙 بازگشت", "lottery_admin")])
        edit_message(chat_id, msg_id, "کدام قرعه‌کشی را انجام دهم؟", reply_markup=inline_keyboard(buttons))
    elif data.startswith("do_draw:") and is_admin(user_id):
        lottery_id = int(data.split(":")[1])
        draw_lottery(lottery_id, user_id)
        answer_callback(query["id"], "✅ قرعه‌کشی انجام شد.")
    elif data == "new_challenge" and is_admin(user_id):
        set_state(user_id, "new_challenge_title")
        send_message(chat_id, "🏆 *چالش جدید*\n\nعنوان چالش را وارد کنید:")
    elif data.startswith("view_challenge:"):
        challenge_id = int(data.split(":")[1])
        with get_db() as conn:
            ch = conn.execute("SELECT * FROM code_challenges WHERE id=?", (challenge_id,)).fetchone()
        if ch:
            edit_message(
                chat_id, msg_id,
                f"🏆 *{ch['title']}*\n\n{ch['description']}\n\n⏰ مهلت: {ch['deadline'][:10] if ch['deadline'] else 'نامحدود'}",
                reply_markup=inline_keyboard([
                    [("📤 ارسال کد", f"submit_challenge:{challenge_id}")],
                    [("🔙 چالش‌ها", "challenges")]
                ])
            )
    elif data.startswith("submit_challenge:"):
        challenge_id = int(data.split(":")[1])
        set_state(user_id, "submit_challenge", {"challenge_id": challenge_id})
        edit_message(chat_id, msg_id, "📤 فایل کد پایتون خود را ارسال کنید:")
    elif data == "redeem_points_discount":
        if not u or u["points"] < 50:
            answer_callback(query["id"], "حداقل ۵۰ امتیاز نیاز است!", True)
            return
        if spend_points(user_id, 50):
            dc = create_discount_code("points_redemption", 10, True, user_id, max_uses=1)
            answer_callback(query["id"], f"✅ کد تخفیف: {dc}", True)
            send_message(chat_id, f"🎟 کد تخفیف ۱۰٪ شما:\n`{dc}`\n\nاین کد یک‌بار مصرف است.")
    elif data == "list_discounts" and is_admin(user_id):
        with get_db() as conn:
            codes = conn.execute("SELECT * FROM discount_codes ORDER BY id DESC LIMIT 20").fetchall()
        text = "🎟 *لیست کدهای تخفیف*\n\n"
        for c in codes:
            status_dc = "✅ فعال" if c["is_active"] else "❌ غیرفعال"
            text += f"`{c['code']}` - {c['value']}{'%' if c['is_percent'] else 'T'} - {status_dc} ({c['used_count']}/{c['max_uses']})\n"
        edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 تخفیف‌ها", "discount_panel")]]))
    elif data.startswith("enter_discount:"):
        parts = data.split(":")
        set_state(user_id, "enter_discount_code", {"plan": parts[1], "duration": parts[2]})
        edit_message(chat_id, msg_id, "🎟 کد تخفیف خود را وارد کنید:")
    elif data == "set_mirror":
        buttons = [[("🔗 میرور سفارشی", "custom_mirror")]]
        buttons.append([])  # سطر خالی برای جدایی بهتر
        
        # اضافه کردن لیست میرورهای ایران
        for mirror in IRAN_MIRRORS:
            buttons.append([(f"🇮🇷 {mirror['name']}", f"select_mirror:{mirror['name']}")])
        
        buttons.append([("❌ انصراف", "install_lib")])
        
        text = (
            "🌐 *انتخاب میرور برای نصب کتابخانه*\n\n"
            "میرورهای ایران برای سرعت بیشتر:\n"
        )
        
        edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))
    elif data == "custom_mirror":
        set_state(user_id, "set_mirror")
        send_message(chat_id, "🌐 آدرس میرور سفارشی را وارد کنید:\n(مثال: https://pypi.tuna.tsinghua.edu.cn/simple)")
    elif data.startswith("select_mirror:"):
        mirror_name = data.split(":", 1)[1]
        mirror_url = None
        for m in IRAN_MIRRORS:
            if m["name"] == mirror_name:
                mirror_url = m["url"]
                break
        if mirror_url:
            set_state(user_id, "install_lib_name", {"mirror": mirror_url})
            send_message(chat_id, f"✅ میرور انتخاب شد: *{mirror_name}*\n\nحالا نام کتابخانه را وارد کنید:")
        else:
            send_message(chat_id, "❌ میرور یافت نشد.")
    elif data == "use_lib_key":
        set_state(user_id, "use_lib_key")
        send_message(chat_id, "🔑 کلید کتابخانه اختصاصی را وارد کنید:")
    
    # ─── دستیار وب ───
    elif data == "web_assistant_menu":
        handle_web_assistant_menu(query)
    elif data == "web_manage_projects":
        handle_web_manage_projects(query)
    elif data == "web_new_project":
        handle_web_new_project(query)
    elif data.startswith("web_template:"):
        template_type = data.split(":")[1]
        handle_web_new_project_with_template(query, template_type)
    elif data.startswith("web_edit_project:"):
        project_id = int(data.split(":")[1])
        handle_web_edit_project(query, project_id)
    elif data == "web_edit_html":
        handle_web_edit_html(query)
    elif data == "web_add_text":
        handle_web_add_text(query)
    elif data == "web_edit_css":
        handle_web_edit_css(query)
    elif data == "web_edit_js":
        handle_web_edit_js(query)
    elif data == "web_preview":
        handle_web_preview(query)
    elif data == "web_download":
        handle_web_download(query)
    elif data.startswith("web_download_zip:"):
        handle_web_download_zip(query, int(data.split(":")[1]))
    elif data.startswith("web_download_html:"):
        handle_web_download_html(query, int(data.split(":")[1]))
    elif data.startswith("web_download_preview:"):
        handle_web_download_preview(query, int(data.split(":")[1]))
    elif data.startswith("web_delete:"):
        project_id = int(data.split(":")[1])
        handle_web_delete_project(query)
    elif data.startswith("web_delete_confirm:"):
        project_id = int(data.split(":")[1])
        handle_web_delete_confirm(query, project_id)
    
    # ─── قالب‌های آماده ───
    elif data == "web_templates":
        handle_web_templates(query)
    elif data.startswith("use_template:"):
        template_id = data.split(":")[1]
        handle_use_template(query, template_id)
    
    # ─── اشتراک‌گذاری ───
    elif data == "web_create_group":
        handle_web_create_group(query)
    elif data.startswith("web_share_project:"):
        project_id = int(data.split(":")[1])
        handle_web_share_project(query, project_id)
    elif data.startswith("share_to_group:"):
        parts = data.split(":")
        project_id = int(parts[1])
        group_id = int(parts[2])
        # ثبت اشتراک در دیتابیس
        with get_db() as conn:
            conn.execute(
                "INSERT INTO web_project_shares (project_id, group_id, permission) VALUES (?, ?, ?)",
                (project_id, group_id, "view")
            )
            conn.commit()
        send_message(chat_id, "✅ پروژه با گروپ اشتراک شد!")
    
    # ─── مانیتورینگ ───
    elif data.startswith("bot_monitor:"):
        bot_id = int(data.split(":")[1])
        handle_bot_monitor(query, bot_id)
    
    # ─── پنل سازمانی ───
    elif data == "enterprise_request":
        handle_enterprise_request(query)
    elif data == "enterprise_payment":
        handle_enterprise_payment(query)

    # ─── زیرمنوهای اصلی جدید ───
    elif data == "assistant_code_menu":
        handle_assistant_code_menu(query)
    elif data == "upgrade_plan_menu":
        handle_upgrade_plan_menu(query)
    elif data == "challenge_lottery_menu":
        handle_challenge_lottery_menu(query)
    elif data == "contact_team_menu":
        handle_contact_team_menu(query)
    elif data == "about_me_menu":
        handle_about_me_menu(query)
    elif data == "help_guide":
        handle_help_guide(query)

    # ─── زیرمنوهای پنل ادمین جدید ───
    elif data == "admin_manage_menu":
        handle_admin_manage_menu(query)
    elif data == "admin_communication_menu":
        handle_admin_communication_menu(query)
    elif data == "admin_challenge_lottery_menu":
        handle_admin_challenge_lottery_menu(query)
    elif data == "admin_stats_menu":
        handle_admin_stats_menu(query)
    elif data == "admin_payment_menu":
        handle_admin_payment_menu(query)
    elif data == "admin_edit_help_guide":
        handle_admin_edit_help_guide(query)

    # ─── قرعه‌کشی با امتیاز ───
    elif data.startswith("join_lottery_points:"):
        handle_join_lottery_points(query, int(data.split(":")[1]))
    elif data.startswith("spend_lottery:"):
        parts = data.split(":")
        handle_spend_lottery(query, int(parts[1]), int(parts[2]))

    # ─── منوهای اخبار / درباره ما / فروشگاه بازو ───
    elif data == "news_main":
        handle_news_main(query)
    elif data == "about_main":
        handle_about_main(query)
    elif data == "bot_store":
        handle_bot_store_menu(query)
    elif data == "bot_store_candidate":
        handle_bot_store_candidate(query)
    elif data == "bot_store_selected":
        handle_bot_store_selected(query)
    elif data == "bot_store_submit":
        handle_bot_store_submit(query)
    elif data.startswith("bot_store_pick:"):
        handle_bot_store_pick(query, int(data.split(":")[1]))
    elif data.startswith("bot_store_featured:"):
        handle_bot_store_featured(query, int(data.split(":")[1]))

    # ─── منوهای ادمین (اضافه‌شده) ───
    elif data == "admin_news_menu":
        handle_admin_news_menu(query)
    elif data == "admin_about_menu":
        handle_admin_about_menu(query)
    elif data == "admin_bots_menu":
        handle_admin_bots_menu(query)
    elif data == "admin_channels_menu":
        handle_admin_channels_menu(query)
    elif data == "admin_managers_menu":
        handle_admin_managers_menu(query)
    elif data == "admin_libraries_menu":
        handle_admin_libraries_menu(query)
    elif data == "admin_bot_store":
        handle_admin_bot_store(query)
    elif data.startswith("admin_bots_list:"):
        handle_admin_bots_list(query, int(data.split(":")[1]))
    elif data == "admin_search_bot_prompt":
        handle_admin_search_bot_prompt(query)
    elif data.startswith("admin_library_detail:"):
        handle_admin_library_detail(query, int(data.split(":")[1]))
    elif data.startswith("admin_delete_library:"):
        handle_admin_delete_library(query, int(data.split(":")[1]))
    elif data.startswith("admin_delete_bot:"):
        handle_admin_delete_bot(query, int(data.split(":")[1]))
    elif data.startswith("admin_stop_bot:"):
        handle_admin_stop_bot(query, int(data.split(":")[1]))
    elif data.startswith("admin_restart_bot:"):
        handle_admin_restart_bot(query, int(data.split(":")[1]))
    elif data.startswith("admin_view_bot_log:"):
        handle_admin_view_bot_log(query, int(data.split(":")[1]))
    elif data.startswith("admin_bot_detail:"):
        handle_admin_bot_detail(query, int(data.split(":")[1]))
    elif data.startswith("admin_promote_bot:"):
        handle_admin_promote_bot_prompt(query, int(data.split(":")[1]))
    elif data.startswith("admin_library_owner:"):
        handle_admin_library_owner(query, int(data.split(":")[1]))
    elif data.startswith("admin_make_manager:"):
        target_id = int(data.split(":")[1])
        handle_admin_make_manager(query, target_id)
    elif data.startswith("admin_bot_owner:"):
        handle_admin_bot_owner(query, int(data.split(":")[1]))
    elif data.startswith("botstore_approve:"):
        handle_botstore_approve(query, int(data.split(":")[1]))
    elif data.startswith("botstore_reject:"):
        handle_botstore_reject(query, int(data.split(":")[1]))

    # شروع flow ویرایش اخبار / درباره ما (set state)
    elif data == "admin_edit_news":
        if is_admin(user_id):
            set_state(user_id, "admin_edit_news")
            edit_message(chat_id, msg_id, "✏️ *تغییر اخبار*\n\nمتن خبر جدید را ارسال کنید:")
    elif data == "admin_broadcast_news":
        if is_admin(user_id):
            set_state(user_id, "admin_broadcast_news")
            edit_message(chat_id, msg_id, "📣 *ارسال خبر همگانی*\n\nمتن یا رسانه را ارسال کنید:")
    elif data == "admin_edit_about":
        if is_admin(user_id):
            set_state(user_id, "admin_edit_about")
            edit_message(chat_id, msg_id, "✏️ *تغییر درباره ما*\n\nمتن جدید را ارسال کنید:")
    elif data == "admin_add_channel":
        handle_admin_add_channel_prompt(query)
    elif data == "admin_remove_channel":
        handle_admin_remove_channel_prompt(query)
    elif data == "admin_add_manager":
        handle_admin_add_manager_prompt(query)
    elif data == "admin_remove_manager":
        handle_admin_remove_manager_prompt(query)

    # ─── دستیار وب پیشرفته ───
    elif data == "web_tutorial":
        handle_web_tutorial(query)
    elif data == "web_examples":
        handle_web_examples(query)
    elif data == "web_add_heading":
        handle_web_add_element(query, "heading")
    elif data == "web_add_image":
        handle_web_add_element(query, "image")
    elif data == "web_add_link":
        handle_web_add_element(query, "link")
    elif data == "web_add_list":
        handle_web_add_element(query, "list")
    elif data == "web_add_table":
        handle_web_add_element(query, "table")
    elif data == "web_add_audio":
        handle_web_add_element(query, "audio")
    elif data == "web_add_video":
        handle_web_add_element(query, "video")
    elif data == "web_css_color":
        handle_web_css_helper(query, "color")
    elif data == "web_css_font":
        handle_web_css_helper(query, "font")
    elif data == "web_css_size":
        handle_web_css_helper(query, "size")
    elif data == "web_css_background":
        handle_web_css_helper(query, "background")
    elif data == "web_css_border":
        handle_web_css_helper(query, "border")
    elif data == "web_css_spacing":
        handle_web_css_helper(query, "spacing")
    elif data == "web_edit_html_code":
        handle_web_edit_html(query)
    elif data == "web_edit_css_code":
        handle_web_edit_css(query)
    elif data == "web_edit_js_code":
        handle_web_edit_js(query)
    elif data == "web_js_alert":
        handle_web_js_snippet(query, "alert")
    elif data == "web_js_click":
        handle_web_js_snippet(query, "click")
    elif data == "web_js_form":
        handle_web_js_snippet(query, "form")
    elif data == "web_js_timer":
        handle_web_js_snippet(query, "timer")

    # ─── دستیار سایت ───
    elif data == "web_site_assistant":
        handle_web_site_assistant(query)
    elif data == "web_tools_menu":
        handle_web_tools_menu(query)
    elif data == "web_scrape_menu":
        handle_web_scrape_menu(query)
    elif data == "web_scrape_request":
        handle_web_scrape_request_prompt(query)
    elif data.startswith("scrape_approve:"):
        handle_scrape_approve(query, int(data.split(":")[1]))
    elif data.startswith("scrape_reject:"):
        handle_scrape_reject(query, int(data.split(":")[1]))


    # ─── API Keys ───
    elif data == "api_keys_menu":
        handle_api_keys_menu(query)
    elif data == "api_key_create":
        handle_api_key_create(query)
    elif data == "api_keys_list":
        handle_api_keys_list(query)
    elif data == "api_docs":
        handle_api_docs(query)
    elif data.startswith("api_key_toggle:"):
        handle_api_key_toggle(query, int(data.split(":")[1]))
    elif data.startswith("api_key_delete:"):
        handle_api_key_delete(query, int(data.split(":")[1]))
    elif data.startswith("api_key_detail:"):
        handle_api_key_detail(query, int(data.split(":")[1]))

    # ─── سرگرمی یونیکد ───
    elif data == "unicode_fun_menu":
        handle_unicode_fun_menu(query)
    elif data == "emoji_to_gif":
        handle_emoji_to_gif_menu(query)

    # ─── ترکیبگر ایموجی ───
    elif data == "emoji_mixer":
        handle_emoji_mixer_menu(query)
    elif data == "emoji_mixer_help":
        handle_emoji_mixer_help(query)

    elif data == "noop":
        pass
    else:
        log.warning(f"Unhandled callback: {data}")


# ─────────────────────────────────────────────
#  پردازش پیام‌های متنی و فایل
# ─────────────────────────────────────────────
def handle_message(update):
    message = update.get("message", {})

    # FIX: چک کردن وجود "from" در پیام
    if "from" not in message:
        return

    user = message["from"]
    user_id = user["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # ثبت/آپدیت کاربر
    username = message["from"].get("username", "")
    full_name = f"{message['from'].get('first_name','')} {message['from'].get('last_name','')}".strip()
    upsert_user(user_id, username, full_name)

    # بررسی مسدودی
    u = get_user(user_id)
    if u and u["is_blocked"] and not is_admin(user_id):
        send_message(chat_id, f"❌ حساب شما مسدود است.\nدلیل: {u['block_reason'] or 'نامشخص'}")
        return

    # /start
    if text.startswith("/start"):
        payload = text.split(" ")[1] if " " in text else ""
        handle_start(message, payload)
        return

    # /help
    if text == "/help":
        send_message(
            chat_id,
            "🤖 *راهنمای کدبات*\n\n"
            "• /start - شروع ربات\n"
            "• /menu - منوی اصلی\n"
            "• /stats - آمار شما\n"
            "• /invite - لینک دعوت\n"
            "• /support - تیکت پشتیبانی",
            reply_markup=main_menu(user_id)
        )
        return

    if text == "/menu":
        send_message(chat_id, "🏠 *منوی اصلی*", reply_markup=main_menu(user_id))
        return

    state = get_state(user_id)
    st = state["state"]

    # ─── State machine ───
    if st == "deploy_waiting_name":
        handle_deploy_name(message)

    elif st in ("deploy_file", "deploy_confirm"):
        if "document" in message:
            handle_deploy_file(message)
        elif text:
            send_message(chat_id, "لطفاً فایل .py ارسال کنید.")

    elif st == "install_lib_name":
        handle_install_lib_name(message)

    elif st == "broadcast_waiting_msg" and is_admin(user_id):
        handle_broadcast_content(message)

    elif st == "admin_search_user" and is_admin(user_id):
        handle_admin_search_user(message)

    elif st == "reject_deploy_reason" and is_admin(user_id):
        req_id = state["data"]["req_id"]
        reason = text
        target_user_id = state["data"].get("user_id", 0)
        with get_db() as conn:
            req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()
            if req:
                req_data = json.loads(req["data"])
                conn.execute(
                    "UPDATE deployed_bots SET status='rejected' WHERE id=?",
                    (req_data.get("bot_id"),)
                )
                conn.execute("UPDATE pending_requests SET status='rejected' WHERE id=?", (req_id,))
                conn.commit()
                # FIX: استفاده از user_id که در state ذخیره شده
                send_message(req["user_id"], f"❌ درخواست استقرار ربات رد شد.\nدلیل: {reason}")
        send_message(chat_id, "✅ رد درخواست ثبت شد.")
        clear_state(user_id)

    elif st == "reject_lib_reason" and is_admin(user_id):
        req_id = state["data"]["req_id"]
        reason = text
        with get_db() as conn:
            req = conn.execute("SELECT * FROM pending_requests WHERE id=?", (req_id,)).fetchone()
            if req:
                req_data = json.loads(req["data"])
                conn.execute(
                    "UPDATE library_installs SET status='rejected' WHERE id=?",
                    (req_data.get("install_id"),)
                )
                conn.execute("UPDATE pending_requests SET status='rejected' WHERE id=?", (req_id,))
                conn.commit()
                send_message(req["user_id"], f"❌ درخواست نصب کتابخانه رد شد.\nدلیل: {reason}")
        send_message(chat_id, "✅ رد ثبت شد.")
        clear_state(user_id)

    elif st == "admin_gift_points" and is_admin(user_id):
        if text.isdigit():
            target_id = state["data"]["target_id"]
            amount = int(text)
            add_points(target_id, amount, "هدیه از مدیر")
            send_message(target_id, f"🎁 {amount} امتیاز از طرف مدیر به شما هدیه داده شد!")
            send_message(chat_id, f"✅ {amount} امتیاز به کاربر `{target_id}` داده شد.")
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ عدد معتبر وارد کنید.")

    elif st == "admin_send_user_msg" and is_admin(user_id):
        target_id = state["data"]["target_id"]
        send_message(target_id, f"📩 *پیام از مدیر:*\n\n{text}")
        send_message(chat_id, "✅ پیام ارسال شد.")
        clear_state(user_id)

    elif st == "change_payment_token" and is_admin(user_id):
        set_setting("payment_token", text.strip())
        send_message(chat_id, "✅ توکن پرداخت بروزرسانی شد.")
        clear_state(user_id)

    elif st == "admin_change_channel" and is_admin(user_id):
        global CHANNEL_USERNAME
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        set_setting("channel_username", channel)
        CHANNEL_USERNAME = channel
        send_message(chat_id, f"✅ کانال تغییر کرد به: `{channel}`",
                     reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
        clear_state(user_id)

    elif st == "admin_change_invite_base" and is_admin(user_id):
        global INVITE_BASE
        link = text.strip()
        set_setting("invite_base", link)
        INVITE_BASE = link
        send_message(chat_id, f"✅ لینک دعوت تغییر کرد به: `{link}`",
                     reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
        clear_state(user_id)

    elif st == "admin_change_required_invites" and is_admin(user_id):
        global REQUIRED_INVITES
        if text.strip().isdigit():
            val = int(text.strip())
            set_setting("required_invites", str(val))
            REQUIRED_INVITES = val
            send_message(chat_id, f"✅ تعداد دعوت لازم به *{val}* تغییر کرد.",
                         reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ یک عدد صحیح وارد کنید.")

    elif st == "admin_edit_price" and is_admin(user_id):
        plan_key = state["data"]["plan_key"]
        duration = state["data"]["duration"]
        if text.strip().isdigit():
            new_price = int(text.strip())
            set_setting(f"price_{plan_key}_{duration}", str(new_price))
            PLANS[plan_key]["subscriptions"][duration]["price"] = new_price
            dur_fa = {"monthly": "یک ماهه", "quarterly": "سه ماهه",
                      "biannual": "شش ماهه", "annual": "یک ساله"}
            send_message(chat_id,
                         f"✅ قیمت پلن *{PLANS[plan_key]['name']}* ({dur_fa.get(duration, duration)}) "
                         f"به *{new_price:,} تومان* تغییر کرد.",
                         reply_markup=inline_keyboard([[("🔙 تغییر قیمت‌ها", "change_prices")]]))
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ یک عدد صحیح (تومان) وارد کنید.")

    elif st == "admin_deduct_points" and is_admin(user_id):
        if text.isdigit():
            target_id = state["data"]["target_id"]
            amount = int(text)
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET points = MAX(0, points - ?) WHERE user_id=?",
                    (amount, target_id)
                )
                conn.commit()
            send_message(target_id, f"➖ *{amount}* امتیاز از حساب شما توسط مدیر کسر شد.")
            send_message(chat_id, f"✅ {amount} امتیاز از کاربر `{target_id}` کسر شد.")
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ عدد معتبر وارد کنید.")

    elif st == "ticket_subject":
        set_state(user_id, "ticket_message", {"subject": text})
        send_message(chat_id, f"📌 موضوع: *{text}*\n\nحالا متن تیکت را وارد کنید:")

    elif st == "ticket_message":
        subject = state["data"]["subject"]
        with get_db() as conn:
            conn.execute(
                "INSERT INTO tickets (user_id, subject, message, created_at) VALUES (?,?,?,?)",
                (user_id, subject, text, datetime.now().isoformat())
            )
            ticket_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
        # FIX: u ممکنه None باشه
        user_name = u["full_name"] if u else str(user_id)
        for admin_id in ADMIN_IDS:
            send_message(
                admin_id,
                f"🎫 *تیکت جدید #{ticket_id}*\n\n"
                f"👤 {user_name}\n📌 {subject}\n\n{text[:300]}",
                reply_markup=inline_keyboard([[("👁 مشاهده تیکت", f"admin_view_ticket:{ticket_id}")]])
            )
        send_message(chat_id, f"✅ تیکت #{ticket_id} ثبت شد. به زودی پاسخ می‌دهیم.", reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))
        clear_state(user_id)

    elif st == "admin_reply_ticket" and is_admin(user_id):
        ticket_id = state["data"]["ticket_id"]
        target_user_id = state["data"]["user_id"]
        with get_db() as conn:
            conn.execute(
                "UPDATE tickets SET reply=?, replied_by=?, replied_at=?, status='answered' WHERE id=?",
                (text, user_id, datetime.now().isoformat(), ticket_id)
            )
            conn.commit()
        send_message(target_user_id, f"💬 *پاسخ تیکت #{ticket_id}:*\n\n{text}")
        send_message(chat_id, "✅ پاسخ ارسال شد.")
        clear_state(user_id)

    elif st == "custom_lib_name":
        lib_name = text.strip()
        lib_key = "KEY-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
        set_state(user_id, "custom_lib_mappings", {"lib_name": lib_name, "lib_key": lib_key, "mappings": {}})
        send_message(
            chat_id,
            f"📚 کتابخانه: *{lib_name}*\n🔑 کلید: `{lib_key}`\n\n"
            f"حالا mapping ها را وارد کنید.\nهر خط یک mapping: `نام_سفارشی=نام_اصلی`\n\n"
            f"مثال:\n`درخواست=requests`\n`دریافت=get`\n`ارسال=post`\n\n"
            f"وقتی تمام شد «ذخیره» بنویسید:",
            reply_markup=inline_keyboard([[("❌ انصراف", "custom_lib")]])
        )

    elif st == "custom_lib_mappings":
        if text.strip().lower() == "ذخیره":
            lib_name = state["data"]["lib_name"]
            lib_key = state["data"]["lib_key"]
            mappings = state["data"]["mappings"]
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO custom_libraries (user_id, lib_name, lib_key, mappings, created_at) VALUES (?,?,?,?,?)",
                    (user_id, lib_name, lib_key, json.dumps(mappings, ensure_ascii=False), datetime.now().isoformat())
                )
                conn.commit()
            send_message(
                chat_id,
                f"✅ کتابخانه اختصاصی *{lib_name}* ذخیره شد!\n🔑 کلید: `{lib_key}`",
                reply_markup=inline_keyboard([[("🔑 کتابخانه اختصاصی", "custom_lib")]])
            )
            clear_state(user_id)
        elif "=" in text:
            parts_lines = text.strip().split("\n")
            mappings = state["data"]["mappings"]
            added = 0
            for line in parts_lines:
                if "=" in line:
                    k, v = line.split("=", 1)
                    mappings[k.strip()] = v.strip()
                    added += 1
            send_message(chat_id, f"✅ {added} mapping اضافه شد.\nادامه دهید یا «ذخیره» بنویسید.")
        else:
            send_message(chat_id, "❓ mapping را به شکل `نام_سفارشی=نام_اصلی` وارد کنید یا «ذخیره» بنویسید.")

    elif st == "enter_discount_code":
        plan = state["data"]["plan"]
        duration = state["data"]["duration"]
        code = text.strip().upper()
        valid, discount_val, dc_obj = validate_discount_code(code, user_id, plan)
        if valid and isinstance(dc_obj, dict):
            apply_discount_code(dc_obj["id"], user_id)
            plan_data = PLANS[plan]
            sub = plan_data["subscriptions"][duration]
            amount_off = int(sub["price"] * discount_val / 100) if dc_obj["is_percent"] else discount_val
            final_price = max(0, sub["price"] - amount_off)
            send_message(
                chat_id,
                f"✅ کد تخفیف اعمال شد!\n\n"
                f"تخفیف: *{discount_val}{'٪' if dc_obj['is_percent'] else ' تومان'}*\n"
                f"قیمت نهایی: *{final_price:,} تومان*",
                reply_markup=inline_keyboard([
                    [("💰 پرداخت", f"pay_now:{plan}:{duration}:{amount_off}")],
                    [("❌ انصراف", f"view_plan:{plan}")]
                ])
            )
        else:
            # FIX: dc_obj اینجا رشته دلیل خطاست
            send_message(chat_id, f"❌ {dc_obj if isinstance(dc_obj, str) else 'کد نامعتبر'}")
        clear_state(user_id)

    elif st and st.startswith("create_discount_") and is_admin(user_id):
        dtype = st.replace("create_discount_", "")
        if dtype in ("special", "hourly", "occasion") and text.isdigit():
            value = int(text)
            if dtype == "hourly":
                set_state(user_id, "create_discount_hourly_hours", {"value": value})
                send_message(chat_id, "⏰ تا چند ساعت دیگر منقضی شود؟ (عدد ساعت)")
            elif dtype == "occasion":
                set_state(user_id, "create_discount_occasion_date", {"value": value})
                send_message(chat_id, "📅 تاریخ مناسبت را وارد کنید: (مثال: 2025-03-21)")
            else:  # special
                code = create_discount_code(dtype, value, True, user_id, max_uses=100)
                send_message(chat_id, f"✅ کد تخفیف ویژه ساخته شد!\n\n🎟 کد: `{code}`\nمقدار: {value}٪")
                clear_state(user_id)
        else:
            send_message(chat_id, "❌ عدد درصد معتبر وارد کنید.")

    elif st == "create_discount_hourly_hours" and is_admin(user_id):
        if text.isdigit():
            hours = int(text)
            expires = (datetime.now() + timedelta(hours=hours)).isoformat()
            value = state["data"]["value"]
            code = create_discount_code("hourly", value, True, user_id, max_uses=1000, expires_at=expires)
            send_message(chat_id, f"✅ کد تخفیف ساعتی ساخته شد!\n\n🎟 کد: `{code}`\nمقدار: {value}٪\n⏰ انقضا: {expires[:16]}")
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ عدد ساعت معتبر وارد کنید.")

    elif st == "create_discount_occasion_date" and is_admin(user_id):
        value = state["data"]["value"]
        try:
            occasion_date = datetime.strptime(text.strip(), "%Y-%m-%d")
            expires = occasion_date.isoformat()
            code = create_discount_code("occasion", value, True, user_id, max_uses=1000, expires_at=expires)
            send_message(chat_id, f"✅ کد تخفیف مناسبتی ساخته شد!\n\n🎟 کد: `{code}`\nمقدار: {value}٪\n📅 انقضا: {text}")
            clear_state(user_id)
        except ValueError:
            send_message(chat_id, "❌ فرمت تاریخ اشتباه است. مثال: 2025-03-21")

    elif st == "new_lottery_title" and is_admin(user_id):
        set_state(user_id, "new_lottery_prize", {"title": text})
        send_message(chat_id, f"🎪 عنوان: *{text}*\n\nجایزه قرعه‌کشی را وارد کنید:")

    elif st == "new_lottery_prize" and is_admin(user_id):
        prize = text.strip()
        data = state["data"]
        data["prize"] = prize
        set_state(user_id, "new_lottery_min_points", data)
        send_message(chat_id, f"🎁 جایزه: *{prize}*\n\nحداقل امتیاز لازم برای شرکت: (۰ برای همه)")

    elif st == "new_lottery_min_points" and is_admin(user_id):
        if text.isdigit():
            data = state["data"]
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO lotteries (title, prize, min_points, created_by, created_at) VALUES (?,?,?,?,?)",
                    (data["title"], data["prize"], int(text), user_id, datetime.now().isoformat())
                )
                conn.commit()
            send_message(chat_id, f"✅ قرعه‌کشی *{data['title']}* ایجاد شد!", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
            clear_state(user_id)
        else:
            send_message(chat_id, "❌ عدد معتبر وارد کنید.")

    elif st == "new_challenge_title" and is_admin(user_id):
        set_state(user_id, "new_challenge_desc", {"title": text})
        send_message(chat_id, f"🏆 عنوان: *{text}*\n\nتوضیحات چالش را وارد کنید:")

    elif st == "new_challenge_desc" and is_admin(user_id):
        desc = text.strip()
        data = state["data"]
        data["desc"] = desc
        set_state(user_id, "new_challenge_deadline", data)
        send_message(chat_id, f"📝 توضیح: {desc[:50]}...\n\n⏰ مهلت (تاریخ، مثال: 2025-04-01) یا «نامحدود»:")

    elif st == "new_challenge_deadline" and is_admin(user_id):
        data = state["data"]
        deadline = None if text.strip() == "نامحدود" else text.strip()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO code_challenges (title, description, deadline, created_by, created_at) VALUES (?,?,?,?,?)",
                (data["title"], data["desc"], deadline, user_id, datetime.now().isoformat())
            )
            conn.commit()
        send_message(chat_id, f"✅ چالش *{data['title']}* ایجاد شد!")
        threading.Thread(
            target=lambda: send_broadcast(f"🏆 *چالش جدید!*\n\n{data['title']}\n\n{data['desc'][:200]}\n\nبرای شرکت: /start"),
            daemon=True
        ).start()
        clear_state(user_id)

    elif st == "submit_challenge":
        challenge_id = state["data"]["challenge_id"]
        if "document" in message:
            file_id = message["document"]["file_id"]
            file_name = message["document"].get("file_name", "code.py")
            file_info = api("getFile", {"file_id": file_id})
            if file_info.get("ok"):
                file_path_remote = file_info["result"]["file_path"]
                download_url = f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path_remote}"
                try:
                    r = requests.get(download_url, timeout=30)
                    r.raise_for_status()  # اگر خطای HTTP بود، exception می‌اندازد
                    save_path = BOTS_DIR / f"challenge_{challenge_id}_{user_id}_{file_name}"
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                except requests.RequestException as e:
                    send_message(chat_id, f"❌ خطا در دریافت فایل: {e}")
                    clear_state(user_id)
                    return  # ← از ادامه اجرا جلوگیری می‌کند
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO challenge_submissions (challenge_id, user_id, code_file, submitted_at) VALUES (?,?,?,?)",
                        (challenge_id, user_id, str(save_path), datetime.now().isoformat())
                    )
                    conn.commit()
                # FIX: u ممکنه None باشه
                user_name = u["full_name"] if u else str(user_id)
                for admin_id in ADMIN_IDS:
                    send_message(
                        admin_id,
                        f"📤 *ارسال کد چالش #{challenge_id}*\n\n👤 {user_name}\n📁 {file_name}"
                    )
                    send_document(admin_id, save_path, f"کد از {user_name}")
                send_message(chat_id, "✅ کد شما به مدیر ارسال شد!")
                clear_state(user_id)
        else:
            send_message(chat_id, "لطفاً فایل .py ارسال کنید.")

    elif st == "set_mirror":
        mirror = text.strip()
        set_state(user_id, "install_lib_name", {"mirror": mirror})
        send_message(chat_id, f"✅ میرور تنظیم شد: `{mirror}`\n\nحالا نام کتابخانه را وارد کنید:")

    elif st == "use_lib_key":
        lib_key = text.strip()
        with get_db() as conn:
            lib = conn.execute("SELECT * FROM custom_libraries WHERE lib_key=?", (lib_key,)).fetchone()
        if lib:
            mappings = json.loads(lib["mappings"])
            mappings_text = "\n".join([f"• `{k}` → `{v}`" for k, v in mappings.items()])
            send_message(
                chat_id,
                f"📚 *کتابخانه: {lib['lib_name']}*\n\nMappingها:\n{mappings_text or 'ندارد'}",
                reply_markup=inline_keyboard([[("🔙 بازگشت", "custom_lib")]])
            )
        else:
            send_message(chat_id, "❌ کتابخانه‌ای با این کلید یافت نشد.")
        clear_state(user_id)

    # ─── state های ادمین - مدیریت کانال و مدیران ───
    elif st == "admin_add_manager" and is_admin(user_id):
        handle_admin_add_manager(message)

    elif st == "admin_remove_manager" and is_admin(user_id):
        handle_admin_remove_manager(message)

    elif st == "admin_add_channel" and is_admin(user_id):
        handle_admin_add_channel(message)

    elif st == "admin_remove_channel" and is_admin(user_id):
        handle_admin_remove_channel(message)

    elif st == "admin_edit_news" and is_admin(user_id):
        handle_admin_news_input(message)

    elif st == "admin_broadcast_news" and is_admin(user_id):
        handle_admin_news_input(message)

    elif st == "admin_edit_about" and is_admin(user_id):
        handle_admin_news_input(message)

    elif st == "admin_edit_help_guide" and is_admin(user_id):
        handle_admin_news_input(message)

    elif st == "admin_promote_bot" and is_admin(user_id):
        handle_admin_promote_bot(message)

    elif st == "admin_search_bot" and is_admin(user_id):
        q = text.strip()
        with get_db() as conn:
            bots = conn.execute(
                "SELECT * FROM deployed_bots WHERE bot_name LIKE ? ORDER BY id DESC LIMIT 20",
                (f"%{q}%",)
            ).fetchall()
        if not bots:
            send_message(chat_id, "❌ ربات یافت نشد.")
        else:
            buttons = [[(f"🤖 {b['bot_name']}", f"admin_bot_detail:{b['id']}")] for b in bots]
            buttons.append([("🔙 بازگشت", "admin_bots_menu")])
            send_message(chat_id, f"🔍 *نتایج جستجو برای «{q}»:*", reply_markup=inline_keyboard(buttons))
        clear_state(user_id)

    # ─── state های بازو استور ───
    elif st == "bot_store_display_name":
        handle_bot_store_display_name(message)

    elif st == "bot_store_promo_text":
        handle_bot_store_promo_text(message)

    elif st == "bot_store_description":
        handle_bot_store_description(message)

    elif st == "bot_store_confirm":
        send_message(chat_id, "برای تأیید، دکمه «تأیید» را بزنید یا «انصراف» را بزنید.")

    # ─── state های deploy ───
    elif st in ("deploy_file", "deploy_confirm"):
        if "document" in message:
            handle_deploy_file(message)
        else:
            send_message(chat_id, "📎 لطفاً فایل .py ربات را ارسال کنید.")

    # ─── state های اشتراک تخفیف ───
    elif st == "awaiting_discount":
        plan = state["data"].get("plan", "")
        duration = state["data"].get("duration", "")
        code = text.strip().upper()
        valid, discount_val, dc_obj = validate_discount_code(code, user_id, plan)
        if valid and isinstance(dc_obj, dict):
            apply_discount_code(dc_obj["id"], user_id)
            plan_data = PLANS.get(plan, {})
            sub = plan_data.get("subscriptions", {}).get(duration, {})
            base_price = sub.get("price", state["data"].get("price", 0))
            amount_off = int(base_price * discount_val / 100) if dc_obj["is_percent"] else discount_val
            final_price = max(0, base_price - amount_off)
            send_message(chat_id,
                f"✅ کد تخفیف اعمال شد!\n\n"
                f"تخفیف: *{discount_val}{'٪' if dc_obj['is_percent'] else ' تومان'}*\n"
                f"قیمت نهایی: *{final_price:,} تومان*",
                reply_markup=inline_keyboard([
                    [("💰 پرداخت", f"pay_now:{plan}:{duration}:{amount_off}")],
                    [("❌ انصراف", f"view_plan:{plan}")]
                ])
            )
        else:
            send_message(chat_id, f"❌ {dc_obj if isinstance(dc_obj, str) else 'کد نامعتبر است.'}")
        clear_state(user_id)

    # ─── state های Enterprise ───
    elif st == "enterprise_company_name":
        set_state(user_id, "enterprise_description", {"company_name": text.strip()})
        send_message(chat_id, f"🏢 شرکت: *{text.strip()}*\n\nتوضیح مختصری درباره نیاز خود بنویسید:")

    elif st == "enterprise_description":
        company = state["data"].get("company_name", "")
        set_state(user_id, "enterprise_user_count", {"company_name": company, "description": text.strip()})
        send_message(chat_id, "👥 تعداد کاربران تقریبی شما چقدر است؟")

    elif st == "enterprise_user_count":
        company = state["data"].get("company_name", "")
        desc = state["data"].get("description", "")
        for admin_id in ADMIN_IDS:
            send_message(admin_id,
                f"🏢 *درخواست Enterprise جدید*\n\n"
                f"👤 کاربر: `{user_id}`\n"
                f"🏢 شرکت: {company}\n"
                f"📝 توضیح: {desc}\n"
                f"👥 تعداد کاربران: {text.strip()}"
            )
        send_message(chat_id,
            "✅ درخواست Enterprise شما ثبت شد.\n\nکارشناسان ما به زودی با شما تماس می‌گیرند.",
            reply_markup=inline_keyboard([[("🔙 منوی اصلی", "main_menu")]])
        )
        clear_state(user_id)

    # ─── state های دستیار وب ───
    elif st == "web_project_name":
        proj_name = text.strip()
        if not proj_name:
            send_message(chat_id, "❌ نام پروژه نمی‌تواند خالی باشد.")
            return
        template_type = state["data"].get("template", "blank")
        tpl = WEB_TEMPLATES_DATA.get(template_type, {})
        with get_db() as conn:
            conn.execute(
                "INSERT INTO web_projects (user_id, name, html, css, js, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, proj_name, tpl.get("html",""), tpl.get("css",""), tpl.get("js",""),
                 datetime.now().isoformat(), datetime.now().isoformat())
            )
            proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
        set_state(user_id, "web_editing", {"project_id": proj_id})
        send_message(chat_id,
            f"✅ پروژه *{proj_name}* ایجاد شد!",
            reply_markup=inline_keyboard([
                [("✏️ HTML", "web_edit_html"), ("🎨 CSS", "web_edit_css"), ("⚡ JS", "web_edit_js")],
                [("➕ المان", "web_add_text"), ("👁 پیش‌نمایش", "web_preview")],
                [("📥 دانلود", "web_download"), ("🔙 پروژه‌ها", "web_manage_projects")]
            ])
        )

    elif st == "web_group_name":
        group_name = text.strip()
        if not group_name:
            send_message(chat_id, "❌ نام گروه خالی است.")
            return
        with get_db() as conn:
            conn.execute(
                "INSERT INTO web_project_groups (user_id, name, created_at) VALUES (?,?,?)",
                (user_id, group_name, datetime.now().isoformat())
            )
            conn.commit()
        send_message(chat_id, f"✅ گروه *{group_name}* ایجاد شد.", reply_markup=inline_keyboard([[("📂 پروژه‌هایم", "web_manage_projects")]]))
        clear_state(user_id)

    elif st == "web_editing":
        project_id = state["data"].get("project_id")
        if project_id:
            with get_db() as conn:
                proj = conn.execute("SELECT * FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
            if proj:
                send_message(chat_id,
                    f"📁 *پروژه: {proj['name']}*\n\nانتخاب کنید:",
                    reply_markup=inline_keyboard([
                        [("✏️ HTML", "web_edit_html"), ("🎨 CSS", "web_edit_css"), ("⚡ JS", "web_edit_js")],
                        [("➕ المان", "web_add_text"), ("👁 پیش‌نمایش", "web_preview")],
                        [("📥 دانلود", "web_download"), ("🔙 پروژه‌ها", "web_manage_projects")]
                    ])
                )
                return
        send_message(chat_id, "❌ پروژه یافت نشد.", reply_markup=inline_keyboard([[("📂 پروژه‌ها", "web_manage_projects")]]))

    elif st == "scrape_reject_reason" and is_admin(user_id):
        d = state.get("data", {})
        reason = text.strip()
        with get_db() as conn:
            conn.execute("UPDATE scrape_requests SET status='rejected' WHERE id=?", (d.get("req_id"),))
            conn.commit()
        if d.get("user_id"):
            send_message(d["user_id"],
                "❌ *درخواست استخراج رد شد*\n\n"
                f"🌐 آدرس: `{d.get('url','')}`\n"
                f"📝 دلیل: {reason}")
        send_message(chat_id, "✅ درخواست رد شد و دلیل به کاربر ارسال شد.")
        clear_state(user_id)

    elif st == "web_scrape_url":
        handle_web_scrape_url_input(message)

    elif st == "api_key_label":
        handle_api_key_label_input(message)

    elif st == "emoji_to_gif_waiting":
        handle_emoji_to_gif_input(message)

    elif st == "emoji_mix_waiting":
        handle_emoji_mix_input(message)

    elif st == "web_add_text":
        project_id = state["data"].get("project_id") if state.get("data") else None
        if not project_id:
            send_message(chat_id, "❌ ابتدا یک پروژه را باز کنید.")
            return
        with get_db() as conn:
            proj = conn.execute("SELECT html FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
        if not proj:
            send_message(chat_id, "❌ پروژه یافت نشد.")
            return
        new_html = (proj["html"] or "") + f"\n<p>{text}</p>"
        with get_db() as conn:
            conn.execute("UPDATE web_projects SET html=?, updated_at=? WHERE id=?",
                         (new_html, datetime.now().isoformat(), project_id))
            conn.commit()
        send_message(chat_id, "✅ متن به HTML اضافه شد.",
            reply_markup=inline_keyboard([
                [("✏️ ادامه ویرایش HTML", "web_edit_html"), ("👁 پیش‌نمایش", "web_preview")],
                [("🔙 پروژه", f"web_edit_project:{project_id}")]
            ])
        )
        clear_state(user_id)

    else:
        # پیش‌فرض برای کاربر فعال
        if is_active_user(user_id) or is_admin(user_id):
            send_message(chat_id, "از منوی زیر انتخاب کنید:", reply_markup=main_menu(user_id))
        else:
            ok, reason = check_activation(user_id)
            if reason.startswith("need_invites"):
                needed = reason.split(":")[1]
                send_message(
                    chat_id,
                    f"برای استفاده از ربات، ابتدا *{needed} نفر* را دعوت کنید.\n\n"
                    f"🔗 لینک دعوت: `{get_invite_link(user_id)}`",
                    reply_markup=inline_keyboard([[("🔗 لینک دعوت", "my_invite"), ("✅ بررسی", "check_activation")]])
                )
            elif reason == "need_channel":
                send_message(
                    chat_id,
                    "برای فعال‌سازی باید در کانال عضو شوید:",
                    reply_markup=inline_keyboard([
                        [("📢 عضویت در کانال", "url", f"https://bale.ai/{CHANNEL_USERNAME[1:]}")],
                        [("✅ عضو شدم", "joined_channel")]
                    ])
                )


# ─────────────────────────────────────────────
#  قالب‌های آماده - Templates
# ─────────────────────────────────────────────

WEB_TEMPLATES_DATA = {
    "blog": {
        "name": "📰 وبلاگ",
        "html": '<header><h1>وبلاگ من</h1></header><main><article><h2>پست اول</h2><p>محتوا...</p></article></main>',
        "css": "body{font-family:Arial;direction:rtl;background:#f5f5f5;}header{background:white;padding:20px;}",
        "js": "console.log('وبلاگ بارگیری شد!');"
    },
    "portfolio": {
        "name": "💼 پورتفولیو",
        "html": '<nav><h1>پورتفولیو</h1></nav><section><h2>کارهای من</h2></section>',
        "css": "body{background:linear-gradient(135deg,#667eea,#764ba2);color:white;}nav{padding:20px;}",
        "js": "alert('خوش‌آمدید!');"
    },
    "landing": {
        "name": "🚀 فرود",
        "html": '<header><h1>محصول انقلابی</h1><p>راه‌حل بهترین</p></header><button>شروع کنید</button>',
        "css": "header{text-align:center;padding:100px;background:#667eea;color:white;}button{padding:10px 30px;}",
        "js": "document.querySelector('button').onclick=()=>alert('ثبت‌نام!');"
    }
}

def handle_web_templates(query: dict):
    """نمایش قالب‌های آماده"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    buttons = [[("🎨 " + v["name"], f"use_template:{k}")] for k, v in WEB_TEMPLATES_DATA.items()]
    buttons.append([("🔙 بازگشت", "web_assistant_menu")])
    
    edit_message(chat_id, msg_id,
        "🎨 *قالب‌های آماده*\n\nیکی را انتخاب کنید تا پروژه جدید شروع کنید:",
        reply_markup=inline_keyboard(buttons)
    )

def handle_use_template(query: dict, template_id: str):
    """استفاده از قالب"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    
    if template_id not in WEB_TEMPLATES_DATA:
        send_message(chat_id, "❌ قالب یافت نشد!")
        return
    
    set_state(user_id, "web_project_name", {"template": template_id})
    send_message(chat_id,
        "✏️ *نام پروژه را وارد کنید*\n\nمثال: پروژه من، وبسایت شرکت"
    )

# ─────────────────────────────────────────────
#  اشتراک‌گذاری پروژه - Project Sharing
# ─────────────────────────────────────────────

def handle_web_create_group(query: dict):
    """ایجاد گروپ اشتراک"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    
    set_state(user_id, "web_group_name")
    send_message(chat_id,
        "👥 *نام گروپ را وارد کنید*\n\nمثال: تیم توسعه، دوستان"
    )

def handle_web_share_project(query: dict, project_id: int):
    """اشتراک پروژه با گروپ"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    
    # دریافت گروپ‌های کاربر
    with get_db() as conn:
        groups = conn.execute(
            "SELECT id, group_name FROM web_groups WHERE owner_id=?",
            (user_id,)
        ).fetchall()
    
    if not groups:
        send_message(chat_id, "❌ گروپی ندارید. ابتدا گروپ بسازید!")
        return
    
    buttons = [[("📁 " + g["group_name"], f"share_to_group:{project_id}:{g['id']}")] for g in groups]
    buttons.append([("🔙 بازگشت", "web_manage_projects")])
    
    send_message(chat_id,
        "🔗 *گروپ را برای اشتراک انتخاب کنید*",
        reply_markup=inline_keyboard(buttons)
    )

# ─────────────────────────────────────────────
#  مانیتورینگ منابع - Resource Monitoring
# ─────────────────────────────────────────────

def get_bot_resources(bot_id: int) -> dict:
    """دریافت استفاده از منابع ربات"""
    try:
        with get_db() as conn:
            bot = conn.execute(
                "SELECT pid FROM deployed_bots WHERE id=?",
                (bot_id,)
            ).fetchone()
        
        if not bot or not bot["pid"]:
            return {"cpu": 0, "memory": 0, "status": "متوقف"}
        
        pid = bot["pid"]
        try:
            with open(f"/proc/{pid}/status", "r") as f:
                status = f.read()
                # استخراج VmRSS (حافظه)
                for line in status.split("\n"):
                    if "VmRSS" in line:
                        memory_kb = int(line.split()[1])
                        memory_mb = memory_kb / 1024
                        return {"cpu": 0, "memory": memory_mb, "status": "فعال"}
        except:
            pass
        
        return {"cpu": 0, "memory": 0, "status": "خطا"}
    except Exception as e:
        log.error(f"خطا در دریافت منابع ربات: {e}")
        return {"cpu": 0, "memory": 0, "status": "خطا"}

def handle_bot_monitor(query: dict, bot_id: int):
    """نمایش مانیتور ربات"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    with get_db() as conn:
        bot = conn.execute(
            "SELECT bot_name FROM deployed_bots WHERE id=? AND user_id=?",
            (bot_id, user_id)
        ).fetchone()
    
    if not bot:
        send_message(chat_id, "❌ ربات یافت نشد!")
        return
    
    resources = get_bot_resources(bot_id)
    
    text = (
        f"📊 *مانیتور: {bot['bot_name']}*\n\n"
        f"💾 حافظه: *{resources['memory']:.2f} MB*\n"
        f"⚡ پردازنده: *{resources['cpu']}%*\n"
        f"🔴 وضعیت: *{resources['status']}*"
    )
    
    edit_message(chat_id, msg_id, text,
        reply_markup=inline_keyboard([[("🔄 بروزرسانی", f"bot_monitor:{bot_id}"), ("🔙 بازگشت", "bots_menu")]])
    )

# ─────────────────────────────────────────────
#  پنل سازمانی - Enterprise Panel
# ─────────────────────────────────────────────

def handle_enterprise_request(query: dict):
    """درخواست پنل سازمانی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    
    set_state(user_id, "enterprise_company_name")
    send_message(chat_id,
        "🏢 *نام شرکت خود را وارد کنید*\n\nمثال: شرکت فن‌آوری ABC"
    )

def handle_enterprise_payment(query: dict):
    """پرداخت برای پنل سازمانی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    
    # قیمت پنل سازمانی
    amount = 5000000  # ۵ میلیون تومان
    
    # درخواست پرداخت
    payment_payload = {
        "chat_id": user_id,
        "amount": amount,
        "description": "پنل سازمانی کدبات",
        "payload": f"enterprise_{user_id}"
    }
    
    # ثبت درخواست در دیتابیس
    with get_db() as conn:
        conn.execute(
            "INSERT INTO enterprise_requests (user_id, status, payment_status, payment_amount, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, "pending", "pending", amount, datetime.now().isoformat())
        )
        conn.commit()
    
    send_message(chat_id,
        f"💳 *درخواست پنل سازمانی*\n\n"
        f"مبلغ: *{amount:,} تومان*\n"
        f"(سال)\n\n"
        f"✅ مشخصات ثبت شد.\n"
        f"ادمین‌ها برای تأیید تماس می‌گیرند."
    )

# ─────────────────────────────────────────────
#  تابع جدید برای اصلاح ارسال رسانه‌ای
# ─────────────────────────────────────────────

def _send_media_broadcast(chat_id: int, kind: str, file_id: str, caption: str = ""):
    """ارسال صحیح رسانه برای broadcast"""
    payload = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    
    if kind == "photo":
        return api("sendPhoto", {**payload, "photo": file_id})
    elif kind == "video":
        return api("sendVideo", {**payload, "video": file_id})
    elif kind == "audio":
        return api("sendAudio", {**payload, "audio": file_id})
    elif kind == "voice":
        return api("sendVoice", {**payload, "voice": file_id})
    else:
        return send_message(chat_id, caption)

def _json_get_setting(key: str, default):
    raw = get_setting(key, None)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default

def _json_set_setting(key: str, value):
    set_setting(key, json.dumps(value, ensure_ascii=False))

def get_admin_ids() -> List[int]:
    base = set(ADMIN_IDS)
    extra = _json_get_setting("extra_admin_ids", [])
    for x in extra:
        try:
            base.add(int(x))
        except Exception:
            pass
    return sorted(base)

def sync_admin_globals():
    global ADMIN_IDS
    ADMIN_IDS = get_admin_ids()
    return ADMIN_IDS

def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()

def get_required_channels() -> List[str]:
    channels = _json_get_setting("required_channels", None)
    if channels:
        cleaned = []
        for ch in channels:
            ch = str(ch).strip()
            if ch:
                cleaned.append(ch if ch.startswith("@") else f"@{ch.lstrip('@')}")
        if cleaned:
            return cleaned
    single = get_setting("channel_username", CHANNEL_USERNAME) or CHANNEL_USERNAME
    single = str(single).strip()
    return [single if single.startswith("@") else f"@{single.lstrip('@')}"]

def set_required_channels(channels: List[str]):
    cleaned = []
    for ch in channels:
        ch = str(ch).strip()
        if ch:
            cleaned.append(ch if ch.startswith("@") else f"@{ch.lstrip('@')}")
    _json_set_setting("required_channels", cleaned)

def verify_required_channels(user_id: int) -> bool:
    channels = get_required_channels()
    if not channels:
        return True
    ok_all = True
    for ch in channels:
        try:
            res = api("getChatMember", {"chat_id": ch, "user_id": user_id})
            member = res.get("result", {})
            status = member.get("status")
            if status not in ("member", "administrator", "creator"):
                ok_all = False
                break
        except Exception:
            ok_all = False
            break
    if ok_all:
        with get_db() as conn:
            conn.execute("UPDATE users SET channel_joined=1 WHERE user_id=?", (user_id,))
            conn.commit()
    return ok_all

def build_join_keyboard() -> dict:
    rows = [[("✅ عضو شدم", "joined_channel")]]
    for ch in get_required_channels():
        url = f"https://ble.ir/{ch.lstrip('@')}"
        rows.insert(0, [(f"📢 عضویت در {ch}", "url", url)])
    return inline_keyboard(rows)

def send_membership_prompt(chat_id: int, full_name: str, user_id: int):
    channels = get_required_channels()
    if len(channels) == 1:
        text = (
            f"👋 *{full_name} عزیز خوش آمدید!*\n\n"
            f"برای فعال‌سازی ربات، باید در کانال زیر عضو شوید:\n"
            f"`{channels[0]}`"
        )
    else:
        text = (
            f"👋 *{full_name} عزیز خوش آمدید!*\n\n"
            f"برای فعال‌سازی ربات، باید در همه کانال‌های زیر عضو شوید:"
        )
    send_message(chat_id, text, reply_markup=build_join_keyboard())

def check_activation(user_id: int) -> tuple:
    u = get_user(user_id)
    if not u:
        return False, "not_found"
    if u["is_active"] and not u["is_blocked"]:
        if verify_required_channels(user_id):
            return True, "active"
    invite_needed = max(0, REQUIRED_INVITES - int(u["invite_count"] or 0))
    if invite_needed > 0:
        return False, f"need_invites:{invite_needed}"
    if not verify_required_channels(user_id):
        return False, "need_channel"
    with get_db() as conn:
        conn.execute("UPDATE users SET channel_joined=1 WHERE user_id=?", (user_id,))
        conn.commit()
    return True, "ready"

def is_active_user(user_id: int) -> bool:
    u = get_user(user_id)
    if not u:
        return False
    if u["is_blocked"]:
        return False
    if not u["is_active"]:
        return False
    return verify_required_channels(user_id)

def _render_news_text() -> str:
    content = get_setting("news_content", "هنوز خبری ثبت نشده است.")
    updated = get_setting("news_updated_at", "")
    suffix = f"\n\n🕒 آخرین بروزرسانی: `{updated[:19].replace('T',' ')}`" if updated else ""
    return f"📰 *اخبار*\n\n{content}{suffix}"

def _render_about_text() -> str:
    content = get_setting("about_us_content", "هنوز محتوایی برای درباره ما ثبت نشده است.")
    return f"ℹ️ *درباره ما*\n\n{content}"

def _notify_admins(text: str, exclude: Optional[int] = None):
    for aid in get_admin_ids():
        if exclude is not None and aid == exclude:
            continue
        try:
            send_message(aid, text)
        except Exception:
            pass

def _ensure_request_lock_table():
    with get_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_request_locks (
            scope TEXT NOT NULL,
            ref_id INTEGER NOT NULL,
            decision TEXT DEFAULT NULL,
            handled_by INTEGER DEFAULT NULL,
            handled_at TEXT DEFAULT NULL,
            PRIMARY KEY (scope, ref_id)
        )
        """)
        conn.commit()

def _mark_locked(scope: str, ref_id: int, decision: str, handled_by: int) -> bool:
    _ensure_request_lock_table()
    now = datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT decision, handled_by FROM admin_request_locks WHERE scope=? AND ref_id=?",
            (scope, ref_id)
        ).fetchone()
        if row and row["decision"]:
            return False
        conn.execute(
            "INSERT INTO admin_request_locks (scope, ref_id, decision, handled_by, handled_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(scope, ref_id) DO UPDATE SET decision=excluded.decision, handled_by=excluded.handled_by, handled_at=excluded.handled_at",
            (scope, ref_id, decision, handled_by, now)
        )
        conn.commit()
    return True

def _broadcast_to_all_users(text: str, parse_mode: str = "Markdown", media: dict = None, retries: int = 3):
    """ارسال همگانی بهینه‌شده - به همه کاربران غیر مسدود - نرخ شکست زیر ۱۰٪"""
    with get_db() as conn:
        # همه کاربران غیر مسدود (چه فعال چه غیرفعال)
        users = [r["user_id"] for r in conn.execute(
            "SELECT user_id FROM users WHERE is_blocked=0"
        ).fetchall()]

    if not users:
        return 0, 0

    ok = fail = 0
    # کاهش همزمانی برای جلوگیری از rate limit (از 15 به 8)
    sem = threading.Semaphore(8)
    lock = threading.Lock()

    def _send_one(uid: int) -> bool:
        """ارسال یک پیام - برگرداندن True اگر موفق"""
        try:
            # ✅ اگر کاربر در دیتابیس نبود، ثبت کن
            user = get_user(uid)
            if not user:
                upsert_user(uid, "", "")
            
            if media:
                kind = media.get("kind")
                file_id = media.get("file_id")
                payload = {"chat_id": uid}
                if text:
                    payload["caption"] = text
                    payload["parse_mode"] = parse_mode
                if kind == "photo":
                    res = api("sendPhoto", {**payload, "photo": file_id})
                elif kind == "document":
                    res = api("sendDocument", {**payload, "document": file_id})
                elif kind == "video":
                    res = api("sendVideo", {**payload, "video": file_id})
                elif kind == "audio":
                    res = api("sendAudio", {**payload, "audio": file_id})
                elif kind == "voice":
                    res = api("sendVoice", {**payload, "voice": file_id})
                elif kind == "animation":
                    res = api("sendAnimation", {**payload, "animation": file_id})
                elif kind == "sticker":
                    res = api("sendSticker", {"chat_id": uid, "sticker": file_id})
                else:
                    res = send_message(uid, text, parse_mode=parse_mode)
            else:
                res = send_message(uid, text, parse_mode=parse_mode)
            return bool(res.get("ok"))
        except Exception:
            return False

    def worker(uid):
        nonlocal ok, fail
        with sem:
            success = False
            for attempt in range(retries + 1):
                result = _send_one(uid)
                if result:
                    success = True
                    break
                # اگر خطا خورد، قبل از تلاش بعدی صبر کن
                if attempt < retries:
                    # backoff تدریجی: 0.2s, 0.5s, 1s
                    time.sleep(0.2 * (2 * attempt))
            with lock:
                if success:
                    ok += 1
                else:
                    fail += 1
            # تاخیر بین ارسال‌ها برای جلوگیری از rate limit
            time.sleep(0.05)

    threads = [threading.Thread(target=worker, args=(uid,), daemon=True) for uid in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return ok, fail

def _render_html_log_from_file(bot_name: str, log_file_path: str) -> str:
    lines = []
    if log_file_path and os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                for ln in f.read().splitlines():
                    if not ln.strip():
                        continue
                    lvl = "INFO"
                    low = ln.lower()
                    if any(k in low for k in ("error", "exception", "traceback")):
                        lvl = "ERROR"
                    elif "warn" in low:
                        lvl = "WARNING"
                    lines.append({"ts": datetime.now().strftime("%H:%M:%S"), "msg": ln, "level": lvl})
        except Exception:
            pass
    if not lines:
        lines = [{"ts": datetime.now().strftime("%H:%M:%S"), "msg": "هنوز لاگی ثبت نشده است.", "level": "INFO"}]
    return generate_html_log(bot_name, lines[-250:])

def _send_bot_log_html(chat_id: int, bot_name: str, log_file_path: str, caption: str):
    html_path = LOGS_DIR / f"render_{hashlib.md5((bot_name + str(time.time())).encode()).hexdigest()}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_render_html_log_from_file(bot_name, log_file_path))
    return send_document(chat_id, str(html_path), caption)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        plan TEXT DEFAULT 'free',
        points INTEGER DEFAULT 0,
        invite_count INTEGER DEFAULT 0,
        invited_by INTEGER DEFAULT NULL,
        is_active INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        block_reason TEXT DEFAULT NULL,
        block_until TEXT DEFAULT NULL,
        channel_joined INTEGER DEFAULT 0,
        joined_at TEXT DEFAULT NULL,
        last_active TEXT DEFAULT NULL,
        total_spent INTEGER DEFAULT 0,
        plan_expires_at TEXT DEFAULT NULL,
        extra_bots INTEGER DEFAULT 0,
        extra_memory_mb INTEGER DEFAULT 0,
        extra_log_days INTEGER DEFAULT 0,
        extra_libraries INTEGER DEFAULT 0,
        extra_bandwidth_gb INTEGER DEFAULT 0,
        basic_buy_count INTEGER DEFAULT 0,
        subscription_duration TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS deployed_bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bot_name TEXT,
        file_path TEXT,
        extra_files TEXT DEFAULT '[]',
        status TEXT DEFAULT 'pending',
        approved_by INTEGER DEFAULT NULL,
        deployed_at TEXT DEFAULT NULL,
        log_file TEXT DEFAULT NULL,
        pid INTEGER DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS library_installs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        library_name TEXT,
        mirror_url TEXT DEFAULT NULL,
        status TEXT DEFAULT 'pending',
        approved_by INTEGER DEFAULT NULL,
        installed_at TEXT DEFAULT NULL,
        tracking_code TEXT UNIQUE,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS custom_libraries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lib_name TEXT,
        lib_key TEXT UNIQUE,
        mappings TEXT DEFAULT '{}',
        file_path TEXT DEFAULT NULL,
        created_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS web_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        project_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        html_code TEXT DEFAULT '<html><head><title>پروژه</title></head><body></body></html>',
        css_code TEXT DEFAULT 'body { margin: 0; padding: 20px; font-family: Arial; }',
        js_code TEXT DEFAULT '// کد جاوااسکریپت خود را اینجا وارد کنید',
        created_at TEXT DEFAULT NULL,
        updated_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS web_project_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        version_number INTEGER DEFAULT 1,
        html_code TEXT,
        css_code TEXT,
        js_code TEXT,
        created_at TEXT DEFAULT NULL,
        FOREIGN KEY(project_id) REFERENCES web_projects(id)
    );

    CREATE TABLE IF NOT EXISTS web_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        description TEXT DEFAULT '',
        is_public INTEGER DEFAULT 0,
        created_at TEXT DEFAULT NULL,
        updated_at TEXT DEFAULT NULL,
        FOREIGN KEY(owner_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS web_project_shares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        group_id INTEGER,
        shared_user_id INTEGER,
        permission TEXT DEFAULT 'view',
        shared_at TEXT DEFAULT NULL,
        FOREIGN KEY(project_id) REFERENCES web_projects(id),
        FOREIGN KEY(group_id) REFERENCES web_groups(id),
        FOREIGN KEY(shared_user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS web_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        html_code TEXT,
        css_code TEXT,
        js_code TEXT,
        category TEXT DEFAULT 'general',
        is_public INTEGER DEFAULT 1,
        created_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS bot_resource_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id INTEGER NOT NULL,
        cpu_percent REAL DEFAULT 0,
        memory_mb REAL DEFAULT 0,
        timestamp TEXT DEFAULT NULL,
        FOREIGN KEY(bot_id) REFERENCES deployed_bots(id)
    );

    CREATE TABLE IF NOT EXISTS enterprise_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        company_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        user_count INTEGER DEFAULT 1,
        status TEXT DEFAULT 'pending',
        payment_status TEXT DEFAULT 'pending',
        payment_amount INTEGER DEFAULT 0,
        created_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        duration TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        transaction_id TEXT,
        provider_id TEXT,
        payload TEXT,
        created_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS discount_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        type TEXT,
        value INTEGER,
        is_percent INTEGER DEFAULT 1,
        max_uses INTEGER DEFAULT 1,
        used_count INTEGER DEFAULT 0,
        expires_at TEXT DEFAULT NULL,
        created_by INTEGER,
        plan_target TEXT DEFAULT NULL,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS discount_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code_id INTEGER,
        user_id INTEGER,
        used_at TEXT,
        UNIQUE(code_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS weekly_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT,
        week_end TEXT,
        active_users INTEGER DEFAULT 0,
        new_users INTEGER DEFAULT 0,
        active_bots INTEGER DEFAULT 0,
        stopped_bots INTEGER DEFAULT 0,
        lib_installs INTEGER DEFAULT 0,
        revenue INTEGER DEFAULT 0,
        data TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT,
        message TEXT,
        status TEXT DEFAULT 'open',
        reply TEXT DEFAULT NULL,
        replied_by INTEGER DEFAULT NULL,
        created_at TEXT DEFAULT NULL,
        replied_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS code_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'active',
        created_by INTEGER,
        created_at TEXT DEFAULT NULL,
        winner_user_id INTEGER DEFAULT NULL,
        prize_desc TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS challenge_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER,
        user_id INTEGER,
        code_file TEXT,
        submitted_at TEXT DEFAULT NULL,
        FOREIGN KEY(challenge_id) REFERENCES code_challenges(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS lotteries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        prize TEXT,
        min_points INTEGER DEFAULT 0,
        max_winners INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        created_by INTEGER,
        created_at TEXT DEFAULT NULL,
        drawn_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS lottery_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lottery_id INTEGER,
        user_id INTEGER,
        entered_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS admin_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS pending_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        user_id INTEGER,
        data TEXT DEFAULT '{}',
        status TEXT DEFAULT 'pending',
        admin_msg_id INTEGER DEFAULT NULL,
        created_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS user_states (
        user_id INTEGER PRIMARY KEY,
        state TEXT,
        data TEXT DEFAULT '{}',
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        media_file_id TEXT DEFAULT NULL,
        media_type TEXT DEFAULT NULL,
        status TEXT DEFAULT 'draft',
        sent_count INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT DEFAULT NULL,
        sent_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS code_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_type TEXT,
        title TEXT,
        description TEXT,
        budget INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        admin_reply TEXT DEFAULT NULL,
        replied_by INTEGER DEFAULT NULL,
        file_path TEXT DEFAULT NULL,
        created_at TEXT DEFAULT NULL,
        replied_at TEXT DEFAULT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );
    """)

    conn.commit()
    conn.close()
    log.info("✅ دیتابیس آماده شد.")
    
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS about_pages (id INTEGER PRIMARY KEY CHECK(id=1), content TEXT DEFAULT '', updated_at TEXT DEFAULT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS news_items (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, broadcasted INTEGER DEFAULT 0, created_at TEXT DEFAULT NULL, broadcasted_at TEXT DEFAULT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS bot_store_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_id INTEGER, bot_name TEXT, display_name TEXT, promo_text TEXT, description TEXT, status TEXT DEFAULT 'pending', reviewed_by INTEGER DEFAULT NULL, reviewed_at TEXT DEFAULT NULL, created_at TEXT DEFAULT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS featured_bots (id INTEGER PRIMARY KEY AUTOINCREMENT, submission_id INTEGER UNIQUE, user_id INTEGER, bot_id INTEGER, bot_name TEXT, display_name TEXT, promo_text TEXT, description TEXT, approved_by INTEGER, approved_at TEXT, created_at TEXT DEFAULT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS library_catalog (id INTEGER PRIMARY KEY AUTOINCREMENT, library_name TEXT, user_id INTEGER, installed_at TEXT DEFAULT NULL, status TEXT DEFAULT 'installed')")
        conn.execute("CREATE TABLE IF NOT EXISTS admin_request_locks (scope TEXT NOT NULL, ref_id INTEGER NOT NULL, decision TEXT DEFAULT NULL, handled_by INTEGER DEFAULT NULL, handled_at TEXT DEFAULT NULL, PRIMARY KEY (scope, ref_id))")
        # migrations for older DBs
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "extra_admin_ids" not in cols:
            pass
        conn.execute("INSERT OR IGNORE INTO about_pages (id, content, updated_at) VALUES (1, ?, ?)", (
            get_setting("about_us_content", "این بخش درباره تیم کدبات است.") or "این بخش درباره تیم کدبات است.",
            get_setting("about_updated_at", datetime.now().isoformat())
        ))
        
    # جدول سایت‌های تأیید شده برای استخراج
    conn.execute("""
        CREATE TABLE IF NOT EXISTS approved_sites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            domain      TEXT    NOT NULL UNIQUE,
            title       TEXT    DEFAULT '',
            approved_by INTEGER NOT NULL,
            approved_at TEXT    NOT NULL,
            is_active   INTEGER DEFAULT 1,
            verified    INTEGER DEFAULT 0,
            note        TEXT    DEFAULT ''
        )
    """)
    # جدول درخواست‌های استخراج
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            url         TEXT    NOT NULL,
            domain      TEXT    NOT NULL,
            status      TEXT    DEFAULT 'pending',
            result_size INTEGER DEFAULT 0,
            created_at  TEXT    NOT NULL,
            approved_by INTEGER,
            approved_at TEXT
        )
    """)
    # جدول کتابخانه‌های تأیید شده
    conn.execute("""
        CREATE TABLE IF NOT EXISTS approved_libraries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            version     TEXT    DEFAULT '',
            approved_by INTEGER NOT NULL,
            approved_at TEXT    NOT NULL,
            is_active   INTEGER DEFAULT 1,
            description TEXT    DEFAULT ''
        )
    """)

    # جدول کلیدهای API
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            key_hash    TEXT    NOT NULL UNIQUE,
            key_prefix  TEXT    NOT NULL,
            label       TEXT    DEFAULT '',
            created_at  TEXT    NOT NULL,
            expires_at  TEXT,
            is_active   INTEGER DEFAULT 1,
            request_count INTEGER DEFAULT 0,
            last_used   TEXT
        )
    """)
    # جدول لاگ درخواست‌های API
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_request_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id     INTEGER NOT NULL,
            endpoint   TEXT,
            status     INTEGER,
            ip         TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # migration: ستون verified برای approved_sites و zip_path برای scrape_requests
    try:
        site_cols = {c["name"] for c in conn.execute("PRAGMA table_info(approved_sites)").fetchall()}
        if "verified" not in site_cols:
            conn.execute("ALTER TABLE approved_sites ADD COLUMN verified INTEGER DEFAULT 0")
        scrape_cols = {c["name"] for c in conn.execute("PRAGMA table_info(scrape_requests)").fetchall()}
        if "zip_path" not in scrape_cols:
            conn.execute("ALTER TABLE scrape_requests ADD COLUMN zip_path TEXT")
        conn.commit()
    except Exception as e:
        log.warning(f"migration verified/zip_path: {e}")

    # migration: ستون verified در approved_sites
    try:
        col_info = conn.execute("PRAGMA table_info(approved_sites)").fetchall()
        col_names = {c["name"] for c in col_info}
        if "verified" not in col_names:
            conn.execute("ALTER TABLE approved_sites ADD COLUMN verified INTEGER DEFAULT 0")
            conn.commit()
    except Exception as e:
        log.warning(f"migration approved_sites: {e}")

    # migration: اطمینان از وجود ستون‌های html, css, js در web_projects
    try:
        col_info = conn.execute("PRAGMA table_info(web_projects)").fetchall()
        col_names = {c["name"] for c in col_info}
        if "html" not in col_names:
            conn.execute("ALTER TABLE web_projects ADD COLUMN html TEXT DEFAULT ''")
        if "css" not in col_names:
            conn.execute("ALTER TABLE web_projects ADD COLUMN css TEXT DEFAULT ''")
        if "js" not in col_names:
            conn.execute("ALTER TABLE web_projects ADD COLUMN js TEXT DEFAULT ''")
        if "name" not in col_names:
            conn.execute("ALTER TABLE web_projects ADD COLUMN name TEXT DEFAULT ''")
        conn.commit()
    except Exception as e:
        log.warning(f"migration web_projects: {e}")

        conn.commit()

def main_menu(user_id: int) -> dict:
    buttons = [
        [("🤖 دستیار کد", "assistant_code_menu"), ("🚀 ارتقای پلن", "upgrade_plan_menu")],
        [("🏆 کاربران برتر", "top_users"), ("🏅 چالش های کد", "challenge_lottery_menu")],
        [("🔑 API (بزودی)", "api_keys_menu"), ("📞 ارتباط با ادمین", "contact_team_menu")],
        [("👤 درباره من", "about_me_menu"), ("❓ راهنما", "help_guide")],
    ]
    if is_admin(user_id):
        buttons.append([("⚙️ پنل مدیریت", "admin_panel")])
    return inline_keyboard(buttons)

MAIN_MENU_TEXT = (
    "🎉 *خوش‌آمدی به کدبات!* 🎉\n\n"
    "از منوی زیر انتخاب کنید:"
)

def handle_start(message: dict, payload: str = ""):
    user_id = message["from"]["id"]
    username = message["from"].get("username", "")
    full_name = f"{message['from'].get('first_name','')} {message['from'].get('last_name','')}".strip()
    chat_id = message["chat"]["id"]
    upsert_user(user_id, username, full_name)

    # ─── پردازش درخواست‌های API ───
    if payload.startswith("api_"):
        rest = payload[4:]  # حذف پیشوند api_
        # فرمت: KEY__action__bot_id  یا فقط KEY
        if "__" in rest:
            parts = rest.split("__")
            key_plain = parts[0]
            action = parts[1] if len(parts) > 1 else ""
            bot_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            _handle_api_bot_action(message, key_plain, action, bot_id)
        else:
            handle_api_start(message, rest)
        return

    if payload and payload.isdigit():
        inviter_id = int(payload)
        if inviter_id != user_id:
            process_invite(user_id, inviter_id)

    if is_admin(user_id):
        sync_admin_globals()
        with get_db() as conn:
            conn.execute("UPDATE users SET is_active=1, channel_joined=1 WHERE user_id=?", (user_id,))
            conn.commit()
        send_message(user_id, f"👑 *خوش آمدید مدیر عزیز!*\n\nبه ربات *کدبات* خوش آمدید.\nاز منوی زیر انتخاب کنید:", reply_markup=main_menu(user_id))
        return

    ok, reason = check_activation(user_id)
    if ok:
        send_message(user_id, f"👋 *{full_name} عزیز، خوش آمدید!*\n\n🤖 به *کدبات* خوش آمدید.\nاز منوی زیر انتخاب کنید:", reply_markup=main_menu(user_id))
    elif reason.startswith("need_invites"):
        needed = reason.split(":")[1]
        invite_link = get_invite_link(user_id)
        u = get_user(user_id)
        send_message(user_id,
            f"👋 *{full_name} عزیز، خوش آمدید!*\n\n"
            f"برای فعال‌سازی ربات، باید *{needed} نفر دیگر* را دعوت کنید.\n\n"
            f"🔗 لینک دعوت شما:\n`{invite_link}`\n\n"
            f"تعداد دعوت‌های موفق: *{u['invite_count'] if u else 0}/{REQUIRED_INVITES}*",
            reply_markup=inline_keyboard([[("🔗 کپی لینک دعوت", "my_invite")],[("✅ بررسی وضعیت", "check_activation")]])
        )
    else:
        send_membership_prompt(chat_id, full_name, user_id)

def handle_admin_panel(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(user_id):
        answer_callback(query["id"], "دسترسی ندارید!", True)
        return
    edit_message(chat_id, msg_id, "⚙️ *پنل مدیریت سیستم* 🛠️\n\nمدیریت کامل سیستم: کاربران، پرداخت، گزارش‌ها و ویژگی‌ها!\nفقط برای مدیران سیستم.\n\n📌 *یکی از بخش‌های زیر را انتخاب کنید:*", reply_markup=inline_keyboard([
        [("🗂 مدیریت", "admin_manage_menu"), ("💬 ارتباط با کاربران", "admin_communication_menu")],
        [("🏅 چالش و قرعه‌کشی", "admin_challenge_lottery_menu"), ("📊 آمار", "admin_stats_menu")],
        [("💰 مدیریت پرداخت", "admin_payment_menu"), ("✅ درخواست‌ها", "pending_requests")],
        [("⚙️ تنظیمات", "admin_settings"), ("🔙 بازگشت", "main_menu")]
    ]))

def handle_admin_settings(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    current_channels = ", ".join(get_required_channels())
    current_invites = get_setting("required_invites", str(REQUIRED_INVITES))
    edit_message(chat_id, msg_id,
        f"⚙️ *تنظیمات ربات*\n\n"
        f"📢 کانال‌های اجباری: `{current_channels}`\n"
        f"👥 دعوت لازم: `{current_invites}`",
        reply_markup=inline_keyboard([
            [("📢 مدیریت کانال ها", "admin_channels_menu"), ("🔗 تغییر لینک دعوت", "change_invite_base")],
            [("👥 تعداد نیاز دعوت", "change_required_invites"), ("👤 مدیریت مدیران", "admin_managers_menu")],
            [("🔙 پنل مدیریت", "admin_panel")]
        ])
    )

def handle_user_management(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(user_id):
        return
    edit_message(chat_id, msg_id, "👥 *مدیریت کاربران*\n\nیک گزینه را انتخاب کنید:", reply_markup=inline_keyboard([
        [("🔍 جستجوی کاربر", "search_user_prompt"), ("📋 مشاهده کاربران", "view_users_list:0")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))

def handle_admin_user_detail(query: dict, target_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        u = conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone()
        bot_count = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE user_id=?", (target_id,)).fetchone()["c"]
        lib_count = conn.execute("SELECT COUNT(*) as c FROM library_installs WHERE user_id=? AND status='installed'", (target_id,)).fetchone()["c"]
    if not u:
        answer_callback(query["id"], "کاربر یافت نشد!", True)
        return
    u = dict(u)
    status = "✅ فعال" if u["is_active"] and not u["is_blocked"] else ("🔴 مسدود" if u["is_blocked"] else "⏳ غیرفعال")
    text = (
        f"👤 *{u['full_name']}*\n"
        f"آیدی عددی: `{target_id}`\n"
        f"یوزرنیم: @{u['username'] or 'ندارد'}\n"
        f"وضعیت: {status}\n"
        f"پلن: {PLANS.get(u['plan'], {}).get('name', u['plan'])}\n"
        f"امتیاز: *{u['points']}*\n"
        f"ربات‌ها: {bot_count} | کتابخانه‌ها: {lib_count}\n"
        f"دعوت‌ها: {u['invite_count']}\n"
        f"کل خرید: {u['total_spent']:,} تومان\n"
        f"عضویت: {u['joined_at'][:10] if u['joined_at'] else 'نامشخص'}"
    )
    buttons = [
        [("📩 ارسال پیام", f"admin_send_user:{target_id}"), ("🎁 هدیه امتیاز", f"admin_gift_points:{target_id}")],
        [("➖ کسر امتیاز", f"admin_deduct_points:{target_id}"), ("♻️ تغییر پلن", f"admin_change_plan:{target_id}")],
        [("🔴 مسدود کردن", f"admin_block_user:{target_id}"), ("✅ رفع مسدودی", f"admin_unblock_user:{target_id}")],
        [("➕ افزودن به عنوان مدیر", f"admin_make_manager:{target_id}")],
        [("🔙 لیست کاربران", "view_users_list:0"), ("🔙 مدیریت کاربران", "user_management")]
    ]
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))

def handle_broadcast_msg(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(user_id):
        return
    set_state(user_id, "broadcast_waiting_msg")
    edit_message(chat_id, msg_id, "📢 *پیام همگانی*\n\nپیام یا محتوای مورد نظر را ارسال کنید:\n(متن، فایل، عکس، و غیره)", reply_markup=inline_keyboard([[("❌ انصراف", "admin_panel")]]))

def handle_broadcast_content(message: dict):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    if not is_admin(user_id):
        return
    text = message.get("text") or message.get("caption") or ""
    media = None
    if "document" in message:
        media = {"kind": "document", "file_id": message["document"]["file_id"]}
    elif "photo" in message:
        media = {"kind": "photo", "file_id": message["photo"][-1]["file_id"]}
    elif "video" in message:
        media = {"kind": "video", "file_id": message["video"]["file_id"]}
    elif "audio" in message:
        media = {"kind": "audio", "file_id": message["audio"]["file_id"]}
    elif "voice" in message:
        media = {"kind": "voice", "file_id": message["voice"]["file_id"]}
    elif "animation" in message:
        media = {"kind": "animation", "file_id": message["animation"]["file_id"]}
    elif "sticker" in message:
        media = {"kind": "sticker", "file_id": message["sticker"]["file_id"]}
    with get_db() as conn:
        conn.execute("INSERT INTO news_items (content, broadcasted, created_at, broadcasted_at) VALUES (?,?,?,?)",
                     (text or "[رسانه]", 1, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
    ok, fail = _broadcast_to_all_users(text, parse_mode="Markdown", media=media, retries=3)
    send_message(chat_id, f"✅ پیام همگانی ارسال شد.\nموفق: {ok}\nناموفق: {fail}")
    clear_state(user_id)

def handle_admin_news_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    latest = get_setting("news_content", "هنوز خبری ثبت نشده است.")
    edit_message(chat_id, msg_id, f"📰 *مدیریت اخبار*\n\nآخرین خبر:\n{latest}", reply_markup=inline_keyboard([
        [("✏️ تغییر اخبار", "admin_edit_news"), ("📣 پیام", "admin_broadcast_news")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))

def handle_admin_about_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    current = get_setting("about_us_content", "هنوز محتوایی ثبت نشده است.")
    edit_message(chat_id, msg_id, f"ℹ️ *مدیریت درباره ما*\n\nمحتوای فعلی:\n{current}", reply_markup=inline_keyboard([
        [("✏️ تغییر محتوا", "admin_edit_about")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))

def handle_admin_channels_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    chans = get_required_channels()
    text = "📢 *مدیریت کانال‌ها*\n\n" + ("\n".join([f"• `{c}`" for c in chans]) if chans else "هیچ کانالی ثبت نشده است.")
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("➕ افزودن کانال", "admin_add_channel"), ("➖ حذف کانال", "admin_remove_channel")],
        [("🔙 تنظیمات", "admin_settings")]
    ]))

def handle_admin_managers_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    admins = get_admin_ids()
    text = "👤 *مدیریت مدیران*\n\n" + "\n".join([f"• `{a}`" for a in admins]) + "\n"
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("➕ افزودن مدیر", "admin_add_manager"), ("➖ حذف مدیر", "admin_remove_manager")],
        [("🔙 تنظیمات", "admin_settings")]
    ]))

def handle_admin_bots_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "🤖 *مدیریت ربات‌ها*\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=inline_keyboard([
        [("🔍 جستجوی ربات", "admin_search_bot_prompt"), ("📋 لیست ربات‌ها", "admin_bots_list:0")],
        [("🪄 بازو استور", "admin_bot_store"), ("🔙 پنل مدیریت", "admin_manage_menu")]
    ]))

def handle_admin_libraries_menu(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        libs = conn.execute("SELECT * FROM library_installs WHERE status='installed' ORDER BY installed_at DESC LIMIT 30").fetchall()
    if not libs:
        edit_message(chat_id, msg_id, "📦 *مدیریت کتابخانه‌ها*\n\nهنوز کتابخانه‌ای نصب نشده است.", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_manage_menu")]]))
        return
    buttons = []
    for l in libs:
        buttons.append([(f"{l['library_name']} - {l['user_id']}", f"admin_library_detail:{l['id']}")])
    buttons.append([("🔙 پنل مدیریت", "admin_manage_menu")])
    edit_message(chat_id, msg_id, "📦 *مدیریت کتابخانه‌ها*\n\nیکی را انتخاب کنید:", reply_markup=inline_keyboard(buttons))

def handle_admin_news_input(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text") or message.get("caption") or ""
    if not is_admin(admin_id):
        return False
    state = get_state(admin_id)["state"]
    if state == "admin_edit_news":
        set_setting("news_content", text)
        set_setting("news_updated_at", datetime.now().isoformat())
        with get_db() as conn:
            conn.execute("INSERT INTO news_items (content, created_at) VALUES (?, ?)", (text, datetime.now().isoformat()))
            conn.commit()
        send_message(chat_id, "✅ اخبار بروزرسانی شد.", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
        clear_state(admin_id)
        return True
    if state == "admin_broadcast_news":
        set_setting("news_content", text)
        set_setting("news_updated_at", datetime.now().isoformat())
        with get_db() as conn:
            conn.execute("INSERT INTO news_items (content, broadcasted, created_at, broadcasted_at) VALUES (?,?,?,?)", (text, 1, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
        ok, fail = _broadcast_to_all_users(f"📰 *خبر جدید*\n\n{text}", parse_mode="Markdown", retries=3)
        send_message(chat_id, f"✅ خبر همگانی شد.\nموفق: {ok}\nناموفق: {fail}", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
        clear_state(admin_id)
        return True
    if state == "admin_edit_about":
        set_setting("about_us_content", text)
        set_setting("about_updated_at", datetime.now().isoformat())
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO about_pages (id, content, updated_at) VALUES (1, ?, ?)", (text, datetime.now().isoformat()))
            conn.commit()
        send_message(chat_id, "✅ محتوای درباره ما بروزرسانی شد.", reply_markup=inline_keyboard([[("🔙 پنل مدیریت", "admin_panel")]]))
        clear_state(admin_id)
        return True
    if state == "admin_edit_help_guide":
        if text.strip():
            set_setting("help_guide_content", text.strip())
            send_message(chat_id, "✅ محتوای راهنما بروزرسانی شد.",
                         reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
            clear_state(admin_id)
        else:
            send_message(chat_id, "❌ متن معتبر نیست.")
        return True
    return False

def handle_admin_add_manager_prompt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_add_manager")
    edit_message(chat_id, msg_id, "➕ *افزودن مدیر*\n\nآیدی عددی مدیر جدید را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))

def handle_admin_remove_manager_prompt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_remove_manager")
    edit_message(chat_id, msg_id, "➖ *حذف مدیر*\n\nآیدی عددی مدیر را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))

def handle_admin_add_channel_prompt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_add_channel")
    edit_message(chat_id, msg_id, "➕ *افزودن کانال*\n\nیوزرنیم کانال را ارسال کنید (مثال: `@my_channel`):", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))

def handle_admin_remove_channel_prompt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_remove_channel")
    edit_message(chat_id, msg_id, "➖ *حذف کانال*\n\nیوزرنیم کانال را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))


def handle_admin_add_manager(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    if not is_admin(admin_id):
        return False
    state = get_state(admin_id)
    if state["state"] != "admin_add_manager":
        return False
    try:
        target = int((message.get("text") or "").strip())
    except Exception:
        send_message(chat_id, "❌ آیدی عددی معتبر نیست.")
        return True
    base_ids = {int(x) for x in os.getenv("ADMIN_IDS", "2063033830").split(",") if x.strip().isdigit()}
    admins = set(get_admin_ids()) | {target}
    _json_set_setting("extra_admin_ids", sorted(admins - base_ids))
    sync_admin_globals()
    send_message(chat_id, f"✅ کاربر `{target}` به عنوان مدیر افزوده شد.", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
    clear_state(admin_id)
    return True


def handle_admin_remove_manager(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    if not is_admin(admin_id):
        return False
    state = get_state(admin_id)
    if state["state"] != "admin_remove_manager":
        return False
    try:
        target = int((message.get("text") or "").strip())
    except Exception:
        send_message(chat_id, "❌ آیدی عددی معتبر نیست.")
        return True
    base_ids = {int(x) for x in os.getenv("ADMIN_IDS", "2063033830").split(",") if x.strip().isdigit()}
    if target in base_ids:
        send_message(chat_id, "❌ مدیر اصلی قابل حذف نیست.")
        return True
    extras = set(_json_get_setting("extra_admin_ids", []))
    extras.discard(target)
    _json_set_setting("extra_admin_ids", sorted(extras))
    sync_admin_globals()
    send_message(chat_id, f"✅ کاربر `{target}` از مدیران حذف شد.", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
    clear_state(admin_id)
    return True


def handle_admin_add_channel(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    if not is_admin(admin_id):
        return False
    state = get_state(admin_id)
    if state["state"] != "admin_add_channel":
        return False
    ch = (message.get("text") or "").strip()
    if not ch:
        send_message(chat_id, "❌ یوزرنیم معتبر نیست.")
        return True
    chans = get_required_channels()
    ch = ch if ch.startswith("@") else f"@{ch.lstrip('@')}"
    if ch not in chans:
        chans.append(ch)
    set_required_channels(chans)
    send_message(chat_id, f"✅ کانال `{ch}` افزوده شد.", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
    clear_state(admin_id)
    return True


def handle_admin_remove_channel(message: dict):
    admin_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    if not is_admin(admin_id):
        return False
    state = get_state(admin_id)
    if state["state"] != "admin_remove_channel":
        return False
    ch = (message.get("text") or "").strip()
    ch = ch if ch.startswith("@") else f"@{ch.lstrip('@')}"
    chans = [c for c in get_required_channels() if c != ch]
    set_required_channels(chans)
    send_message(chat_id, f"✅ کانال `{ch}` حذف شد.", reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]]))
    clear_state(admin_id)
    return True

def _bot_store_rows(status="approved", limit=30):
    with get_db() as conn:
        return conn.execute(
            "SELECT fs.*, u.full_name FROM featured_bots fs LEFT JOIN users u ON fs.user_id=u.user_id WHERE 1=1 ORDER BY fs.approved_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

def handle_bot_store_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not (is_active_user(user_id) or is_admin(user_id)):
        answer_callback(query["id"], "ابتدا باید فعال باشید.", True)
        return
    edit_message(chat_id, msg_id, "🪄 *بازو استور*\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=inline_keyboard([
        [("📝 کاندید", "bot_store_candidate"), ("⭐ بازوهای منتخب", "bot_store_selected")],
        [("🔙 بازگشت", "main_menu")]
    ]))

def handle_bot_store_candidate(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        bots = conn.execute("SELECT * FROM deployed_bots WHERE user_id=? AND status='running' ORDER BY id DESC", (user_id,)).fetchall()
    if not bots:
        edit_message(chat_id, msg_id, "هیچ ربات مستقرِ موفقی برای کاندید کردن پیدا نشد.", reply_markup=inline_keyboard([[("🔙 بازگشت", "bot_store")]]))
        return
    buttons = [[(f"{b['bot_name']}", f"bot_store_pick:{b['id']}")] for b in bots]
    buttons.append([("🔙 بازگشت", "bot_store")])
    edit_message(chat_id, msg_id, "ربات مورد نظر را انتخاب کنید:", reply_markup=inline_keyboard(buttons))

def handle_bot_store_pick(query: dict, bot_id: int):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=? AND user_id=? AND status='running'", (bot_id, user_id)).fetchone()
    if not bot:
        answer_callback(query["id"], "ربات یافت نشد!", True)
        return
    set_state(user_id, "bot_store_display_name", {"bot_id": bot_id, "bot_name": bot["bot_name"], "file_path": bot["file_path"]})
    edit_message(chat_id, msg_id, f"✅ ربات `{bot['bot_name']}` انتخاب شد.\n\nاسم نمایشی/تبلیغاتی را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 بازو استور", "bot_store")]]))

def handle_bot_store_display_name(message: dict):
    user_id = message["from"]["id"]
    if get_state(user_id)["state"] != "bot_store_display_name":
        return False
    name = (message.get("text") or "").strip()
    if not name:
        send_message(message["chat"]["id"], "❌ نام معتبر نیست.")
        return True
    st = get_state(user_id)
    st["data"]["display_name"] = name
    set_state(user_id, "bot_store_promo_text", st["data"])
    send_message(message["chat"]["id"], "متن تبلیغاتی را ارسال کنید:")
    return True

def handle_bot_store_promo_text(message: dict):
    user_id = message["from"]["id"]
    if get_state(user_id)["state"] != "bot_store_promo_text":
        return False
    promo = (message.get("text") or "").strip()
    if not promo:
        send_message(message["chat"]["id"], "❌ متن تبلیغاتی معتبر نیست.")
        return True
    st = get_state(user_id)
    st["data"]["promo_text"] = promo
    set_state(user_id, "bot_store_description", st["data"])
    send_message(message["chat"]["id"], "توضیح ربات و مشکلی که حل می‌کند را بنویسید:")
    return True

def handle_bot_store_description(message: dict):
    user_id = message["from"]["id"]
    if get_state(user_id)["state"] != "bot_store_description":
        return False
    desc = (message.get("text") or "").strip()
    if not desc:
        send_message(message["chat"]["id"], "❌ توضیح معتبر نیست.")
        return True
    data = get_state(user_id)["data"]
    data["description"] = desc
    set_state(user_id, "bot_store_confirm", data)
    text = (
        f"🪄 *تأیید کاندید بازو*\n\n"
        f"ربات: `{data.get('bot_name')}`\n"
        f"اسم نمایشی: `{data.get('display_name')}`\n"
        f"متن تبلیغاتی: {data.get('promo_text')}\n"
        f"توضیح: {desc}\n\n"
        f"روی تأیید بزنید:"
    )
    send_message(message["chat"]["id"], text, reply_markup=inline_keyboard([[("✅ تایید", "bot_store_submit"), ("❌ انصراف", "bot_store")]]))
    return True


def handle_bot_store_submit(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    state = get_state(user_id)
    data = state["data"]
    if state["state"] != "bot_store_confirm":
        answer_callback(query["id"], "وضعیت نامعتبر!", True)
        return
    bot_id = data["bot_id"]
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=? AND user_id=?", (bot_id, user_id)).fetchone()
        if not bot:
            answer_callback(query["id"], "ربات یافت نشد!", True)
            return
        conn.execute(
            "INSERT INTO bot_store_submissions (user_id, bot_id, bot_name, display_name, promo_text, description, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, bot_id, bot["bot_name"], data["display_name"], data["promo_text"], data["description"], "pending", datetime.now().isoformat())
        )
        req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    req_text = f"""🪄 *درخواست بازو استور*

کاربر: `{user_id}`
ربات: `{bot['bot_name']}`
اسم نمایشی: `{data['display_name']}`
متن تبلیغاتی: {data['promo_text']}
توضیح: {data['description']}"""
    for aid in get_admin_ids():
        send_message(
            aid,
            req_text,
            reply_markup=inline_keyboard([
                [("✅ تایید", f"botstore_approve:{req_id}"), ("❌ رد", f"botstore_reject:{req_id}")]
            ])
        )

    send_message(chat_id, "✅ درخواست بازو استور ثبت شد و برای مدیران ارسال شد.", reply_markup=inline_keyboard([[("🔙 بازو استور", "bot_store")]]))
    clear_state(user_id)

def handle_botstore_approve(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bot_store_submissions WHERE id=?", (req_id,)).fetchone()
    if not row or row["status"] != "pending":
        answer_callback(query["id"], "قبلاً پردازش شده!", True)
        return
    if not _mark_locked("botstore", req_id, "approved", admin_id):
        answer_callback(query["id"], "قبلاً توسط مدیر دیگری پردازش شده.", True)
        return
    with get_db() as conn:
        conn.execute("UPDATE bot_store_submissions SET status='approved', reviewed_by=?, reviewed_at=? WHERE id=?", (admin_id, datetime.now().isoformat(), req_id))
        conn.execute(
            "INSERT INTO featured_bots (submission_id, user_id, bot_id, bot_name, display_name, promo_text, description, approved_by, approved_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (req_id, row["user_id"], row["bot_id"], row["bot_name"], row["display_name"], row["promo_text"], row["description"], admin_id, datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
    try:
        bot_link = f"@{row['bot_name'].lstrip('@')}"
        ok, fail = _broadcast_to_all_users(f"""⭐ *بازوی منتخب جدید*

{row['promo_text']}

ربات: `{bot_link}`""", retries=2)
    except Exception:
        ok, fail = 0, 0
    _notify_admins(f"✅ درخواست بازو استور #{req_id} توسط مدیر `{admin_id}` تایید شد.", exclude=admin_id)
    send_message(row["user_id"], f"🎉 *بازوی شما تایید شد!*\n\n{row['display_name']} اکنون در بازو استور قرار گرفت.")
    edit_message(chat_id, msg_id, f"""✅ بازو استور #{req_id} تایید شد.
ارسال همگانی انجام شد: موفق {ok} / ناموفق {fail}""")
    return

def handle_botstore_reject(query: dict, req_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bot_store_submissions WHERE id=?", (req_id,)).fetchone()
    if not row or row["status"] != "pending":
        answer_callback(query["id"], "قبلاً پردازش شده!", True)
        return
    if not _mark_locked("botstore", req_id, "rejected", admin_id):
        answer_callback(query["id"], "قبلاً توسط مدیر دیگری پردازش شده.", True)
        return
    with get_db() as conn:
        conn.execute("UPDATE bot_store_submissions SET status='rejected', reviewed_by=?, reviewed_at=? WHERE id=?", (admin_id, datetime.now().isoformat(), req_id))
        conn.commit()
    _notify_admins(f"❌ درخواست بازو استور #{req_id} توسط مدیر `{admin_id}` رد شد.", exclude=admin_id)
    send_message(row["user_id"], f"❌ درخواست بازوی شما رد شد.")
    edit_message(chat_id, msg_id, f"❌ بازو استور #{req_id} رد شد.")
    return

def handle_bot_store_selected(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM featured_bots ORDER BY approved_at DESC LIMIT 30").fetchall()
    if not rows:
        edit_message(chat_id, msg_id, "هنوز بازوی منتخبی ثبت نشده است.", reply_markup=inline_keyboard([[("🔙 بازگشت", "bot_store")]]))
        return
    buttons = [[(f"⭐ {r['display_name']}", f"bot_store_featured:{r['id']}")] for r in rows]
    buttons.append([("🔙 بازگشت", "bot_store")])
    edit_message(chat_id, msg_id, "⭐ *بازوهای منتخب*\n\nیکی را انتخاب کنید:", reply_markup=inline_keyboard(buttons))

def handle_bot_store_featured(query: dict, fid: int):
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        row = conn.execute("SELECT * FROM featured_bots WHERE id=?", (fid,)).fetchone()
    if not row:
        answer_callback(query["id"], "یافت نشد!", True)
        return
    text = (
        f"⭐ *{row['display_name']}*\n\n"
        f"ربات: `{row['bot_name']}`\n"
        f"توضیحات: {row['description']}\n\n"
        f"متن تبلیغاتی:\n{row['promo_text']}"
    )
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([[("🔙 بازو استور", "bot_store")]]))

def handle_admin_bots_list(query: dict, page: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    limit = 30
    offset = page * limit
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM deployed_bots ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        total = conn.execute("SELECT COUNT(*) as c FROM deployed_bots").fetchone()["c"]
    if not rows:
        edit_message(chat_id, msg_id, "ربتی یافت نشد.", reply_markup=inline_keyboard([[("🔙 مدیریت ربات‌ها", "admin_bots_menu")]]))
        return
    buttons = [[(f"{'🟢' if r['status']=='running' else '🔴'} {r['bot_name']}", f"admin_bot_detail:{r['id']}")] for r in rows]
    nav = []
    if page > 0:
        nav.append(("⬅️ قبلی", f"admin_bots_list:{page-1}"))
    if offset + limit < total:
        nav.append(("بعدی ➡️", f"admin_bots_list:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([("🔙 مدیریت ربات‌ها", "admin_bots_menu")])
    edit_message(chat_id, msg_id, f"🤖 *لیست ربات‌ها*\n\nصفحه {page+1}", reply_markup=inline_keyboard(buttons))

def handle_admin_search_bot_prompt(query: dict):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_search_bot")
    edit_message(chat_id, msg_id, "🔍 *جستجوی ربات*\n\nاسم ربات یا بخشی از آن را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 مدیریت ربات‌ها", "admin_bots_menu")]]))

def handle_admin_library_detail(query: dict, lib_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        row = conn.execute("SELECT li.*, u.full_name, u.username FROM library_installs li LEFT JOIN users u ON li.user_id=u.user_id WHERE li.id=?", (lib_id,)).fetchone()
    if not row:
        answer_callback(query["id"], "یافت نشد!", True)
        return
    text = (
        f"📦 *{row['library_name']}*\n\n"
        f"کاربر: {row['full_name'] or row['user_id']} (`{row['user_id']}`)\n"
        f"یوزرنیم: @{row['username'] or 'ندارد'}\n"
        f"وضعیت: {row['status']}\n"
        f"میرور: {row['mirror_url'] or 'پیش‌فرض'}"
    )
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("🗑 حذف کتابخانه", f"admin_delete_library:{lib_id}"), ("👤 صاحب کتابخانه", f"admin_library_owner:{row['user_id']}")],
        [("🔙 کتابخانه", "admin_libraries_menu")]
    ]))

def handle_admin_library_delete(query: dict, lib_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        row = conn.execute("SELECT * FROM library_installs WHERE id=?", (lib_id,)).fetchone()
    if not row:
        answer_callback(query["id"], "یافت نشد!", True)
        return
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", row["library_name"], "--break-system-packages"], capture_output=True, text=True, timeout=120)
    except Exception:
        pass
    with get_db() as conn:
        conn.execute("DELETE FROM library_installs WHERE id=?", (lib_id,))
        conn.commit()
    edit_message(chat_id, msg_id, "✅ کتابخانه حذف شد.", reply_markup=inline_keyboard([[("🔙 کتابخانه", "admin_libraries_menu")]]))

def handle_admin_bot_detail(query: dict, bot_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
        if bot:
            owner = conn.execute("SELECT * FROM users WHERE user_id=?", (bot["user_id"],)).fetchone()
    if not bot:
        answer_callback(query["id"], "ربات یافت نشد!", True)
        return
    status_map = {"running":"🟢 در حال اجرا","stopped":"🔴 متوقف","pending":"🟡 در انتظار تایید","rejected":"❌ رد شده"}
    status = status_map.get(bot["status"], bot["status"])
    text = (
        f"🤖 *{bot['bot_name']}*\n\n"
        f"وضعیت: {status}\n"
        f"صاحب: {owner['full_name'] if owner else bot['user_id']} (`{bot['user_id']}`)\n"
        f"فایل: `{Path(bot['file_path']).name if bot['file_path'] else 'ندارد'}`\n"
        f"مستقر شده: {bot['deployed_at'] or 'نامشخص'}"
    )
    buttons = [
        [("🗑 حذف", f"admin_delete_bot:{bot_id}"), ("⏹ توقف", f"admin_stop_bot:{bot_id}"), ("▶️ راه‌اندازی", f"admin_restart_bot:{bot_id}")],
        [("📋 دیدن لاگ HTML", f"admin_view_bot_log:{bot_id}"), ("🪄 افزودن به بازو استور", f"admin_promote_bot:{bot_id}")],
        [("👤 صاحب ربات", f"admin_bot_owner:{bot['user_id']}")],
        [("🔙 لیست ربات‌ها", "admin_bots_list:0")]
    ]
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))

def handle_admin_bot_owner(query: dict, user_id: int):
    handle_admin_user_detail(query, user_id)

def handle_admin_promote_bot_prompt(query: dict, bot_id: int):
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    set_state(admin_id, "admin_promote_bot", {"bot_id": bot_id})
    edit_message(chat_id, msg_id, "متن تبلیغاتی برای بازو استور را ارسال کنید:", reply_markup=inline_keyboard([[("🔙 ربات", f"admin_bot_detail:{bot_id}")]]))

def handle_admin_promote_bot(message: dict):
    admin_id = message["from"]["id"]
    if get_state(admin_id)["state"] != "admin_promote_bot":
        return False
    chat_id = message["chat"]["id"]
    promo = (message.get("text") or "").strip()
    if not promo:
        send_message(chat_id, "❌ متن تبلیغاتی معتبر نیست.")
        return True
    bot_id = get_state(admin_id)["data"]["bot_id"]
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
        if not bot:
            send_message(chat_id, "❌ ربات یافت نشد.")
            clear_state(admin_id)
            return True
        conn.execute("INSERT INTO featured_bots (submission_id, user_id, bot_id, bot_name, display_name, promo_text, description, approved_by, approved_at, created_at) VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                     (bot["user_id"], bot_id, bot["bot_name"], bot["bot_name"], promo, "توسط مدیر به بازو استور اضافه شد.", admin_id, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
    _broadcast_to_all_users(f"⭐ *بازوی منتخب جدید*\n\n{promo}", retries=2)
    send_message(chat_id, "✅ بازو به استور افزوده شد.")
    clear_state(admin_id)
    return True

def handle_admin_view_bot_log(query: dict, bot_id: int):
    admin_id = query["from"]["id"]
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
    if not bot:
        answer_callback(query["id"], "لاگ یافت نشد!", True)
        return
    _send_bot_log_html(query["message"]["chat"]["id"], bot["bot_name"], bot["log_file"], f"📋 لاگ HTML ربات *{bot['bot_name']}*")

def handle_admin_make_manager(query: dict, user_id: int):
    admin_id = query["from"]["id"]
    if not is_admin(admin_id):
        return
    admins = set(get_admin_ids())
    admins.add(user_id)
    _json_set_setting("extra_admin_ids", sorted(admins - set([int(x) for x in os.getenv("ADMIN_IDS", "2063033830").split(",") if x.strip().isdigit()])))
    sync_admin_globals()
    answer_callback(query["id"], "✅ به عنوان مدیر افزوده شد.", True)

def handle_admin_bot_store(query: dict):
    handle_bot_store_menu(query)

def handle_news_main(query: dict):
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(chat_id, msg_id, _render_news_text(), reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))

def handle_about_main(query: dict):
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(chat_id, msg_id, _render_about_text(), reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))

def _admin_reply_and_lock(scope: str, ref_id: int, admin_id: int, text: str):
    if not _mark_locked(scope, ref_id, "done", admin_id):
        return False
    _notify_admins(f"🔔 درخواست `{scope}#{ref_id}` توسط مدیر `{admin_id}` نهایی شد.", exclude=admin_id)
    return True

def handle_assistant_code_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    plan = u["plan"] if u else "free"
    
    # بررسی فعال بودن دستیار وب
    can_use_web_assistant = PLANS[plan].get("web_assistant", False)
    
    buttons = [
        [("🤖 مدیریت ربات ها", "bots_menu"), ("🚀 استقرار جدید", "deploy_new")],
        [("📦 نصب کتابخانه", "install_lib"), ("🔑 کتابخانه اختصاصی", "custom_lib")],
    ]

    # دکمه دستیار وب برای کاربران Basic و بالاتر
    if can_use_web_assistant:
        buttons.append([("🌐 دستیار سایت", "web_site_assistant")])
    else:
        buttons.append([("🌐 دستیار سایت (پایه+)", "upgrade_plan_menu")])

    buttons.extend([
        [("🪄 بازو استور", "bot_store"), ("🎭 سرگرمی یونیکد", "unicode_fun_menu")],
        [("🔙 بازگشت", "main_menu")]
    ])

    edit_message(chat_id, msg_id,
        "🤖 *دستیار کد* 💻\n\n"
        "ربات بساز، کتابخانه نصب کن، وب‌سایت بساز\n"
        "و با ایموجی‌ها سرگرم شو!\n\n"
        "📌 *یکی را انتخاب کنید:*",
        reply_markup=inline_keyboard(buttons))


# ─────────────────────────────────────────────
#  دستیار HTML/CSS/JS برای کسانی که کد بلد نیستند
# ─────────────────────────────────────────────

def handle_web_assistant_menu(query: dict):
    """منوی اصلی دستیار وب"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    
    # شمارش پروژه‌های موجود
    with get_db() as conn:
        proj_count = conn.execute(
            "SELECT COUNT(*) as c FROM web_projects WHERE user_id=?", 
            (user_id,)
        ).fetchone()["c"]
    
    plan = u["plan"]
    max_projects = PLANS[plan].get("max_web_projects", 0)
    
    status_text = f"📊 پروژه‌های شما: *{proj_count}*"
    if max_projects > 0:
        status_text += f" از {max_projects}"
    elif max_projects == -1:
        status_text += " (بی‌محدود)"
    
    buttons = [
        [("➕ جدید", "web_new_project"), ("📂 پروژه‌ها", "web_manage_projects")],
        [("🎓 راهنما", "web_tutorial"), ("💡 نمونه‌ها", "web_examples")],
        [("🔙 بازگشت", "assistant_code_menu")]
    ]
    
    edit_message(
        chat_id, msg_id,
        f"🎨 *دستیار HTML/CSS/JS*\n\n{status_text}\n\n"
        f"برای کسانی که کدنویسی بلد نیستند! 😊",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_manage_projects(query: dict):
    """مدیریت پروژه‌های موجود"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    with get_db() as conn:
        projects = conn.execute(
            "SELECT id, project_name FROM web_projects WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()
    
    if not projects:
        edit_message(
            chat_id, msg_id,
            "📂 *مدیریت پروژه‌ها*\n\nهیچ پروژه‌ای ندارید! 📭\n\nپروژه جدید بسازید و شروع کنید! 🎨",
            reply_markup=inline_keyboard([[("➕ جدید", "web_new_project"), ("🔙", "web_assistant_menu")]])
        )
        return
    
    buttons = []
    for proj in projects:
        buttons.append([(f"📁 {proj['project_name']}", f"web_edit_project:{proj['id']}")])
    
    buttons.append([("➕ جدید", "web_new_project")])
    buttons.append([("🔙 بازگشت", "web_assistant_menu")])
    
    edit_message(
        chat_id, msg_id,
        "📂 *مدیریت پروژه‌ها*\n\nپروژه‌های شما و ویرایش آنها:\n\nیکی را برای ویرایش انتخاب کنید:",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_new_project(query: dict):
    """نوع پروژه جدید را انتخاب کن"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    plan = u["plan"]
    
    # بررسی محدودیت
    max_projects = PLANS[plan].get("max_web_projects", 0)
    if max_projects == 0:
        edit_message(chat_id, msg_id,
            "❌ *محدودیت پلن شما*\n\n"
            "شما می‌توانید پروژه وب بسازید! 😊\n"
            "برای شروع، پلن خود را ارتقا دهید.\n\n"
            "🚀 *پلن Basic* - ۳ پروژه\n"
            "🚀 *پلن Professional* - نامحدود",
            reply_markup=inline_keyboard([[("💳 ارتقا", "upgrade_plan_menu"), ("🔙", "web_assistant_menu")]])
        )
        return
    
    # شمارش پروژه‌های موجود
    with get_db() as conn:
        proj_count = conn.execute(
            "SELECT COUNT(*) as c FROM web_projects WHERE user_id=?",
            (user_id,)
        ).fetchone()["c"]
    
    if proj_count >= max_projects:
        edit_message(chat_id, msg_id,
            f"❌ *محدودیت پروژه رسید*\n\n"
            f"شما {proj_count} پروژه دارید و حداکثر {max_projects} مجاز است.\n\n"
            f"🗑 یک پروژه قدیم را حذف کنید یا پلن را ارتقا دهید.",
            reply_markup=inline_keyboard([[("💳 ارتقا", "upgrade_plan_menu"), ("🔙", "web_manage_projects")]])
        )
        return
    
    # انتخاب نوع پروژه
    buttons = [
        [("🏠 ساده", "web_template:simple"), ("🎨 با سبک", "web_template:styled")],
        [("⚙️ تعاملی", "web_template:interactive")],
        [("🔙 بازگشت", "web_manage_projects")]
    ]
    
    edit_message(chat_id, msg_id,
        "🎨 *ساخت پروژه جدید*\n\n"
        "نوع پروژه را انتخاب کنید:\n\n"
        "🏠 *ساده* - فقط HTML\n"
        "🎨 *با سبک* - HTML + CSS زیبا\n"
        "⚙️ *تعاملی* - HTML + CSS + JavaScript",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_new_project_with_template(query: dict, template_type: str):
    """ایجاد پروژه جدید با template"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    # درخواست نام پروژه
    set_state(user_id, "web_project_name", {"template": template_type})
    edit_message(chat_id, msg_id,
        "✏️ *نام پروژه را وارد کنید*\n\n"
        "نام باید بین ۲ تا ۳۰ کاراکتر باشد.\n"
        "مثال: *پورتفولیو من*، *وب‌سایت فروشگاه*، و غیره",
        reply_markup=inline_keyboard([[("🔙 بازگشت", "web_new_project")]])
    )


def handle_web_edit_project(query: dict, project_id: int):
    """ویرایش پروژه موجود"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    with get_db() as conn:
        proj = conn.execute(
            "SELECT * FROM web_projects WHERE id=? AND user_id=?",
            (project_id, user_id)
        ).fetchone()
    
    if not proj:
        send_message(chat_id, "❌ پروژه یافت نشد!")
        return
    
    buttons = [
        [("📄 HTML", "web_edit_html"), ("🎨 CSS", "web_edit_css")],
        [("⚙️ JS", "web_edit_js"), ("👁️ پیش‌نمایش", "web_preview")],
        [("📥 دانلود", "web_download"), ("🗑 حذف", f"web_delete:{project_id}")],
        [("🔙 بازگشت", "web_manage_projects")]
    ]
    
    set_state(user_id, "web_editing", {"project_id": project_id})
    
    edit_message(chat_id, msg_id,
        f"📁 *{proj['project_name']}*\n\n"
        f"قسمت مورد نظر را برای ویرایش انتخاب کنید:\n\n"
        f"📄 *HTML* - ساختار صفحه\n"
        f"🎨 *CSS* - رنگ و شکل\n"
        f"⚙️ *JavaScript* - تعاملات",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_edit_html(query: dict):
    """ویرایش HTML بدون کد - دکمه‌های کمکی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    buttons = [
        [("📝 متن", "web_add_text"), ("🖼️ عکس", "web_add_image")],
        [("🎬 فیلم", "web_add_video"), ("🔊 صوت", "web_add_audio")],
        [("📚 عنوان", "web_add_heading"), ("📋 لیست", "web_add_list")],
        [("🔗 لینک", "web_add_link"), ("🔲 جدول", "web_add_table")],
        [("✏️ کد خام", "web_edit_html_code")],
        [("🔙 بازگشت", f"web_edit_project:{project_id}")]
    ]
    
    edit_message(chat_id, msg_id,
        "📄 *ویرایش HTML*\n\n"
        "برای کسانی که کد بلد نیستند! 🎯\n\n"
        "دکمه مورد نظر را زنید تا عنصر اضافه کنید:",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_add_text(query: dict):
    """افزودن متن"""
    user_id = query["from"]["id"]
    set_state(user_id, "web_add_text")
    send_message(query["message"]["chat"]["id"],
        "📝 *افزودن متن*\n\n"
        "متن مورد نظر را بنویسید:\n"
        "مثال: سلام، این یک متن ساده است!"
    )


def handle_web_edit_css(query: dict):
    """ویرایش CSS بدون کد"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    buttons = [
        [("🌈 رنگ", "web_css_color"), ("↔️ فاصله", "web_css_spacing")],
        [("🔤 فونت", "web_css_font"), ("⬜ پس‌زمینه", "web_css_background")],
        [("📐 سایز", "web_css_size"), ("🔳 حدود", "web_css_border")],
        [("✏️ کد خام", "web_edit_css_code")],
        [("🔙 بازگشت", f"web_edit_project:{project_id}")]
    ]
    
    edit_message(chat_id, msg_id,
        "🎨 *ویرایش CSS (زیبایی)*\n\n"
        "عنصر مورد نظر را انتخاب کنید:",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_edit_js(query: dict):
    """ویرایش JavaScript"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    
    buttons = [
        [("🖱️ کلیک", "web_js_click"), ("📨 فرم", "web_js_form")],
        [("⏰ تایمر", "web_js_timer"), ("💬 پیام", "web_js_alert")],
        [("✏️ کد خام", "web_edit_js_code")],
        [("🔙 بازگشت", f"web_edit_project:{project_id}")]
    ]
    
    edit_message(chat_id, msg_id,
        "⚙️ *ویرایش JavaScript (تعاملات)*\n\n"
        "عنصر تعاملی را انتخاب کنید:",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_preview(query: dict):
    """نمایش پیش‌نمایش پروژه"""
    user_id = query["from"]["id"]
    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")
    
    if not project_id:
        send_message(query["message"]["chat"]["id"], "❌ پروژه یافت نشد!")
        return
    
    with get_db() as conn:
        proj = conn.execute(
            "SELECT * FROM web_projects WHERE id=? AND user_id=?",
            (project_id, user_id)
        ).fetchone()
    
    # ترکیب کدها
    full_html = f"""<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{proj['project_name']}</title>
    <style>
        {proj['css_code']}
    </style>
</head>
<body>
    {proj['html_code']}
    <script>
        {proj['js_code']}
    </script>
</body>
</html>"""
    
    # ذخیره فایل موقت
    preview_path = LOGS_DIR / f"web_preview_{project_id}.html"
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    send_message(query["message"]["chat"]["id"],
        f"👁️ *پیش‌نمایش: {proj['project_name']}*\n\n"
        f"فایل HTML به شما ارسال شد. برای باز کردن دانلود کنید.",
        reply_markup=inline_keyboard([[("📥 دانلود HTML", f"web_download_preview:{project_id}")]])
    )


def handle_web_download(query: dict):
    """دانلود پروژه"""
    user_id = query["from"]["id"]
    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")
    
    if not project_id:
        send_message(query["message"]["chat"]["id"], "❌ پروژه یافت نشد!")
        return
    
    with get_db() as conn:
        proj = conn.execute(
            "SELECT * FROM web_projects WHERE id=? AND user_id=?",
            (project_id, user_id)
        ).fetchone()
    
    buttons = [
        [("📦 ZIP", f"web_download_zip:{project_id}"), ("📄 HTML", f"web_download_html:{project_id}")],
        [("🔙 بازگشت", f"web_edit_project:{project_id}")]
    ]
    
    edit_message(query["message"]["chat"]["id"],
        query["message"]["message_id"],
        f"📥 *دانلود {proj['project_name']}*\n\n"
        f"فرمت دانلود را انتخاب کنید:\n\n"
        f"📦 *ZIP* - HTML، CSS، JS جدا\n"
        f"📄 *HTML* - همه در یک فایل",
        reply_markup=inline_keyboard(buttons)
    )


def handle_web_delete_project(query: dict):
    """حذف پروژه (تایید دوبار)"""
    user_id = query["from"]["id"]
    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")
    
    edit_message(query["message"]["chat"]["id"],
        query["message"]["message_id"],
        "⚠️ *حذف پروژه*\n\n"
        "آیا مطمئن هستید؟ این عمل برگشت‌ناپذیر است! 🗑️\n\n"
        "تمام فایل‌ها برای همیشه حذف می‌شوند.",
        reply_markup=inline_keyboard([
            [("✅ بله، حذف کن", f"web_delete_confirm:{project_id}"), ("❌ منصرف شدم", "web_edit_project")]
        ])
    )


def handle_web_delete_confirm(query: dict, project_id: int):
    """تایید حذف پروژه"""
    user_id = query["from"]["id"]
    
    with get_db() as conn:
        conn.execute("DELETE FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id))
        conn.commit()
    
    edit_message(query["message"]["chat"]["id"],
        query["message"]["message_id"],
        "✅ *پروژه حذف شد*\n\n"
        "پروژه شما با موفقیت حذف شد.",
        reply_markup=inline_keyboard([[("📂 پروژه‌ها", "web_manage_projects")]])
    )


def handle_upgrade_plan_menu(query: dict):
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    points = u["points"] if u else 0
    edit_message(chat_id, msg_id, f"🚀 *ارتقای پلن*\n\n💰 امتیاز شما: *{points}*\n\nانتخاب کنید:", reply_markup=inline_keyboard([
        [("🏪 فروشگاه آیتم", "shop_menu"), ("💳 خرید اشتراک", "sub_menu")],
        [("🎯 امتیازها", "points_menu")],
        [("🔙 بازگشت", "main_menu")]
    ]))


def handle_challenge_lottery_menu(query: dict):
    """زیرمنوی چالش و قرعه‌کشی برای کاربر"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(chat_id, msg_id, "🏅 *چالش‌های کد و قرعه‌کشی* 🎯\n\nدر مسابقات برنامه‌نویسی شرکت کنید و جوایز بگیرید!\nهر چالش حل‌شده = امتیاز و جایزه!\n\n📌 *انتخاب کنید:*", reply_markup=inline_keyboard([
        [("🎟 چالش‌های کد", "challenges"), ("🎪 قرعه‌کشی", "lottery_menu")],
        [("🔙 بازگشت", "main_menu")]
    ]))


def handle_contact_team_menu(query: dict):
    """زیرمنوی ارتباط با تیم کدبات"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(chat_id, msg_id, "📞 *ارتباط با تیم کدبات* 💬\n\nآخرین اخبار، پرسش‌های متداول و پشتیبانی مستقیم!\nما ۲۴/۷ برای کمک به شما اینجا هستیم.\n\n📌 *انتخاب کنید:*", reply_markup=inline_keyboard([
        [("📰 اخبار", "news_main"), ("ℹ️ درباره ما", "about_main")],
        [("🎫 تیکت پشتیبانی", "ticket_menu")],
        [("🔙 بازگشت", "main_menu")]
    ]))


def handle_about_me_menu(query: dict):
    """زیرمنوی درباره من (پروفایل + لینک دعوت)"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    u = get_user(user_id)
    if not u:
        answer_callback(query["id"], "خطا!", True)
        return
    plan = PLANS.get(u["plan"], PLANS["free"])
    invite_link = get_invite_link(user_id)
    with get_db() as conn:
        bot_count = conn.execute("SELECT COUNT(*) as c FROM deployed_bots WHERE user_id=?", (user_id,)).fetchone()["c"]
        lib_count = conn.execute("SELECT COUNT(*) as c FROM library_installs WHERE user_id=? AND status='installed'", (user_id,)).fetchone()["c"]
    text = (
        f"👤 *درباره من*\n\n"
        f"نام: *{u['full_name']}*\n"
        f"آیدی: `{user_id}`\n"
        f"پلن: *{plan['name']}*\n"
        f"انقضای پلن: {u['plan_expires_at'][:10] if u['plan_expires_at'] else 'ندارد'}\n\n"
        f"💰 امتیاز: *{u['points']}*\n"
        f"🤖 ربات‌ها: *{bot_count}*\n"
        f"📦 کتابخانه‌ها: *{lib_count}*\n"
        f"👥 دعوت‌ها: *{u['invite_count']}*\n"
        f"💳 کل خرید: *{u['total_spent']:,}* تومان\n\n"
        f"📈 آیتم‌های اضافه:\n"
        f"• ربات: +{u['extra_bots']}\n"
        f"• حافظه: +{u['extra_memory_mb']} MB\n"
        f"• کتابخانه: +{u['extra_libraries']}\n\n"
        f"🔗 لینک دعوت شما:\n`{invite_link}`\n"
        f"امتیاز هر دعوت: *۵ امتیاز*"
    )
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("🔙 بازگشت", "main_menu")]
    ]))


def handle_help_guide(query: dict):
    """نمایش راهنما"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    content = get_setting("help_guide_content", DEFAULT_HELP_GUIDE)
    edit_message(chat_id, msg_id, content, reply_markup=inline_keyboard([[("🔙 بازگشت", "main_menu")]]))


# ─────────────────────────────────────────────
#  زیرمنوهای جدید پنل مدیریت
# ─────────────────────────────────────────────

def handle_admin_manage_menu(query: dict):
    """زیرمنوی مدیریت در پنل ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "🗂 *مدیریت*\n\nانتخاب کنید:", reply_markup=inline_keyboard([
        [("📰 مدیریت اخبار", "admin_news_menu"), ("ℹ️ مدیریت درباره ما", "admin_about_menu")],
        [("🤖 مدیریت ربات ها", "admin_bots_menu"), ("📦 مدیریت کتابخانه ها", "admin_libraries_menu")],
        [("👥 مدیریت کاربران", "user_management"), ("🪄 بازو استور", "admin_bot_store")],
        [("💳 مدیریت اشتراک", "subscription_mgmt"), ("❓ مدیریت راهنما", "admin_edit_help_guide")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))


def handle_admin_communication_menu(query: dict):
    """زیرمنوی ارتباط با کاربران در پنل ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "💬 *ارتباط با کاربران*\n\nانتخاب کنید:", reply_markup=inline_keyboard([
        [("📢 پیام همگانی", "broadcast_msg"), ("🎫 تیکت‌ها", "tickets_admin")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))


def handle_admin_challenge_lottery_menu(query: dict):
    """زیرمنوی چالش و قرعه‌کشی در پنل ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "🏅 *چالش‌های کد و قرعه‌کشی* 🎯\n\nدر مسابقات برنامه‌نویسی شرکت کنید و جوایز بگیرید!\nهر چالش حل‌شده = امتیاز و جایزه!\n\n📌 *انتخاب کنید:*", reply_markup=inline_keyboard([
        [("🏆 چالش‌های کد", "challenge_admin"), ("🎪 قرعه‌کشی", "lottery_admin")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))


def handle_admin_stats_menu(query: dict):
    """زیرمنوی آمار در پنل ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "📊 *آمار*\n\nانتخاب کنید:", reply_markup=inline_keyboard([
        [("📊 آمار لحظه‌ای", "realtime_stats"), ("📈 آمار هفتگی", "weekly_stats")],
        [("💰 درآمد", "revenue_panel")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))


def handle_admin_payment_menu(query: dict):
    """زیرمنوی مدیریت پرداخت در پنل ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    edit_message(chat_id, msg_id, "💰 *مدیریت پرداخت*\n\nانتخاب کنید:", reply_markup=inline_keyboard([
        [("💳 توکن پرداخت", "payment_token_panel"), ("🎟 کدهای تخفیف", "discount_panel")],
        [("💰 تغییر قیمت‌ها", "change_prices")],
        [("🔙 پنل مدیریت", "admin_panel")]
    ]))


def handle_admin_edit_help_guide(query: dict):
    """مدیریت محتوای راهنما"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    current = get_setting("help_guide_content", DEFAULT_HELP_GUIDE)
    preview = current[:200] + "..." if len(current) > 200 else current
    set_state(admin_id, "admin_edit_help_guide")
    edit_message(chat_id, msg_id,
        f"❓ *مدیریت راهنما*\n\nمحتوای فعلی (۲۰۰ کاراکتر اول):\n{preview}\n\nمتن جدید را ارسال کنید:",
        reply_markup=inline_keyboard([[("🔙 تنظیمات", "admin_settings")]])
    )


# ─────────────────────────────────────────────
#  سیستم قرعه‌کشی با هزینه امتیاز (جدید)
# ─────────────────────────────────────────────

def handle_join_lottery_points(query: dict, lottery_id: int):
    """ورود به قرعه‌کشی با خرج کردن امتیاز - هر ۱ امتیاز = یک شانس"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        lottery = conn.execute("SELECT * FROM lotteries WHERE id=? AND status='active'", (lottery_id,)).fetchone()

    if not lottery:
        answer_callback(query["id"], "قرعه‌کشی یافت نشد یا پایان یافته!", True)
        return

    user_points = get_points(user_id)
    if lottery["min_points"] > 0 and user_points < lottery["min_points"]:
        edit_message(chat_id, msg_id,
            f"❌ حداقل امتیاز لازم: *{lottery['min_points']}*\nموجودی شما: *{user_points}*",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "lottery_menu")]]))
        return

    # نمایش گزینه‌های خرج کردن امتیاز
    cost_options = [1, 5, 10, 25, 50]
    available = [c for c in cost_options if user_points >= c]
    if not available:
        edit_message(chat_id, msg_id,
            f"❌ امتیاز کافی ندارید!\nموجودی: *{user_points}* امتیاز",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "lottery_menu")]]))
        return

    buttons = [[( f"🎟 {c} امتیاز = {c} شانس", f"spend_lottery:{lottery_id}:{c}")] for c in available]
    buttons.append([("🔙 بازگشت", "lottery_menu")])

    edit_message(chat_id, msg_id,
        f"🎪 *{lottery['title']}*\n\nجایزه: {lottery['prize']}\n💰 موجودی امتیاز: *{user_points}*\n\n"
        f"هر امتیاز = یک شانس بیشتر!\nچند امتیاز می‌خواهید خرج کنید؟",
        reply_markup=inline_keyboard(buttons))


def handle_spend_lottery(query: dict, lottery_id: int, points_to_spend: int):
    """خرج کردن امتیاز در قرعه‌کشی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        lottery = conn.execute("SELECT * FROM lotteries WHERE id=? AND status='active'", (lottery_id,)).fetchone()

    if not lottery:
        answer_callback(query["id"], "قرعه‌کشی یافت نشد!", True)
        return

    if not spend_points(user_id, points_to_spend):
        answer_callback(query["id"], "امتیاز کافی ندارید!", True)
        return

    # اضافه کردن چندین ورودی متناسب با امتیاز خرج‌شده
    now = datetime.now().isoformat()
    with get_db() as conn:
        for _ in range(points_to_spend):
            try:
                conn.execute(
                    "INSERT INTO lottery_entries (lottery_id, user_id, entered_at) VALUES (?,?,?)",
                    (lottery_id, user_id, now)
                )
            except Exception:
                # اگر unique constraint بود، جدول را بدون محدودیت unique استفاده می‌کنیم
                break
        conn.commit()

    edit_message(chat_id, msg_id,
        f"✅ *{points_to_spend} امتیاز خرج شد!*\n\n"
        f"🎪 «{lottery['title']}»\n"
        f"🎟 {points_to_spend} شانس به اسم شما ثبت شد!\n"
        f"💰 امتیاز باقی‌مانده: *{get_points(user_id)}*",
        reply_markup=inline_keyboard([
            [("🎟 شانس بیشتر", f"join_lottery_points:{lottery_id}")],
            [("🔙 بازگشت", "lottery_menu")]
        ]))


# ─────────────────────────────────────────────
#  اصلاح لیست قرعه‌کشی‌ها (نمایش جوایز جذاب)
# ─────────────────────────────────────────────

def handle_lottery_menu_new(query: dict):
    """منوی قرعه‌کشی با امکان خرج امتیاز"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        lotteries = conn.execute(
            "SELECT * FROM lotteries WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()

    if not lotteries:
        edit_message(chat_id, msg_id,
            "🎪 *قرعه‌کشی*\n\nهیچ قرعه‌کشی فعالی وجود ندارد.",
            reply_markup=inline_keyboard([[("🔙 بازگشت", "challenge_lottery_menu")]]))
        return

    user_points = get_points(user_id)
    text = f"🎪 *قرعه‌کشی‌های فعال*\n\n💰 امتیاز شما: *{user_points}*\n\n"
    buttons = []
    for l in lotteries:
        text += f"🏆 *{l['title']}*\nجایزه: {l['prize']}\nحداقل امتیاز: {l['min_points']}\n\n"
        buttons.append([(f"🎪 {l['title']}", f"join_lottery_points:{l['id']}")])

    buttons.append([("🔙 بازگشت", "challenge_lottery_menu")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


# ─────────────────────────────────────────────
#  تکمیل روتر callback برای دکمه‌های جدید
# ─────────────────────────────────────────────


def process_update(update: dict):
    try:
        if "message" in update:
            if "successful_payment" in update["message"]:
                handle_successful_payment(update["message"])
            else:
                handle_message(update)
        elif "callback_query" in update:
            handle_callback_query(update)
        elif "pre_checkout_query" in update:
            handle_pre_checkout(update)
    except Exception as e:
        log.error(f"خطا در پردازش آپدیت: {e}\n{traceback.format_exc()}")


def main():
    init_db()
    log.info("🚀 Poro Bot در حال راه‌اندازی...")

    # شروع سیستم watchdog برای نظارت بر ربات‌های کرش‌کرده
    start_watchdog()

    # زمانبند هفتگی
    threading.Thread(target=weekly_scheduler, daemon=True).start()

    # دور ریختن آپدیت‌های انباشته‌شده از زمانی که ربات خاموش بوده
    # (offset=-1 فقط آخرین آپدیت موجود در صف بله را برمی‌گرداند)
    try:
        stale = get_updates(offset=-1, timeout=0)
        if stale.get("ok") and stale.get("result"):
            offset = stale["result"][-1]["update_id"] + 1
            log.info(f"⏭ {len(stale['result'])} آپدیت قدیمی/انباشته دور ریخته شد.")
        else:
            offset = 0
    except Exception as e:
        log.error(f"خطا در پاک‌سازی آپدیت‌های قدیمی: {e}")
        offset = 0

    executor = ThreadPoolExecutor(max_workers=16)

    while True:
        try:
            result = get_updates(offset=offset, timeout=30)
            if not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                executor.submit(process_update, update)

        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            log.error(f"خطای اصلی: {e}")
            time.sleep(5)


# ─────────────────────────────────────────────
#  State Handlers برای ویژگی‌های جدید
# ─────────────────────────────────────────────

def _handle_web_project_name(user_id: int, text: str, chat_id: int):
    """دریافت نام پروژه برای قالب"""
    state = get_state(user_id)
    template = state.get("data", {}).get("template", "")
    
    if not (2 <= len(text) <= 30):
        send_message(chat_id, "❌ نام باید ۲-۳۰ کاراکتر باشد!")
        return
    
    if template and template in WEB_TEMPLATES_DATA:
        tmpl = WEB_TEMPLATES_DATA[template]
        # ایجاد پروژه جدید با قالب
        with get_db() as conn:
            conn.execute(
                "INSERT INTO web_projects (user_id, project_name, html_code, css_code, js_code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, text, tmpl["html"], tmpl["css"], tmpl["js"], datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()
        
        send_message(chat_id, f"✅ پروژه *{text}* از قالب *{tmpl['name']}* ایجاد شد!")
    
    clear_state(user_id)

def _handle_web_group_name(user_id: int, text: str, chat_id: int):
    """دریافت نام گروپ اشتراک"""
    if not (2 <= len(text) <= 30):
        send_message(chat_id, "❌ نام گروپ باید ۲-۳۰ کاراکتر باشد!")
        return
    
    with get_db() as conn:
        conn.execute(
            "INSERT INTO web_groups (owner_id, group_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, text, datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
    
    send_message(chat_id, f"✅ گروپ *{text}* ایجاد شد!")
    clear_state(user_id)

def _handle_enterprise_company_name(user_id: int, text: str, chat_id: int):
    """دریافت نام شرکت برای پنل سازمانی"""
    set_state(user_id, "enterprise_description", {"company_name": text})
    send_message(chat_id,
        "📝 *توضیح درباره شرکت و نیاز خود*\n\n"
        "مثال: شرکتی که سافت‌وری توسعه می‌دهد..."
    )

def _handle_enterprise_description(user_id: int, text: str, chat_id: int):
    """دریافت توضیح پنل سازمانی"""
    state = get_state(user_id)
    company_name = state.get("data", {}).get("company_name", "")
    
    set_state(user_id, "enterprise_user_count", {
        "company_name": company_name,
        "description": text
    })
    send_message(chat_id,
        "👥 *تعداد کاربران مورد نیاز*\n\n"
        "عدد را وارد کنید (مثال: ۵۰)"
    )

def _handle_enterprise_user_count(user_id: int, text: str, chat_id: int):
    """دریافت تعداد کاربران"""
    try:
        user_count = int(text)
        if user_count < 1:
            send_message(chat_id, "❌ تعداد باید بیشتر از صفر باشد!")
            return
    except ValueError:
        send_message(chat_id, "❌ لطفاً یک عدد وارد کنید!")
        return
    
    state = get_state(user_id)
    data = state.get("data", {})
    
    # محاسبه قیمت
    base_price = 5000000
    price_per_user = 100000
    total_price = base_price + (user_count * price_per_user)
    
    with get_db() as conn:
        conn.execute(
            "UPDATE enterprise_requests SET company_name=?, description=?, user_count=?, payment_amount=? WHERE user_id=? AND status='pending'",
            (data.get("company_name"), data.get("description"), user_count, total_price, user_id)
        )
        conn.commit()
    
    send_message(chat_id,
        f"💳 *خلاصه درخواست*\n\n"
        f"شرکت: *{data.get('company_name')}*\n"
        f"کاربران: *{user_count}*\n"
        f"مبلغ: *{total_price:,} تومان*\n\n"
        f"برای پرداخت دکمه را بزنید:",
        reply_markup=inline_keyboard([[("💳 پرداخت", "enterprise_payment"), ("❌ انصراف", "main_menu")]])
    )
    clear_state(user_id)


# ─────────────────────────────────────────────
#  handler های ادمین - مدیریت ربات‌ها / کتابخانه‌ها
# ─────────────────────────────────────────────

def handle_admin_delete_library(query: dict, lib_id: int):
    """حذف کتابخانه توسط ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        conn.execute("DELETE FROM library_installs WHERE id=?", (lib_id,))
        conn.commit()
    answer_callback(query["id"], "✅ کتابخانه حذف شد.", True)
    handle_admin_libraries_menu(query)


def handle_admin_delete_bot(query: dict, bot_id: int):
    """حذف ربات توسط ادمین"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
        if bot:
            proc = bot_processes.pop(bot_id, None)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            if bot["file_path"] and Path(bot["file_path"]).exists():
                Path(bot["file_path"]).unlink(missing_ok=True)
            conn.execute("DELETE FROM deployed_bots WHERE id=?", (bot_id,))
            conn.commit()
    answer_callback(query["id"], "✅ ربات حذف شد.", True)
    handle_admin_bots_menu(query)


def handle_admin_stop_bot(query: dict, bot_id: int):
    """توقف ربات توسط ادمین"""
    admin_id = query["from"]["id"]
    if not is_admin(admin_id):
        return
    proc = bot_processes.get(bot_id)
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass
    with get_db() as conn:
        conn.execute("UPDATE deployed_bots SET status='stopped', pid=NULL WHERE id=?", (bot_id,))
        conn.commit()
    answer_callback(query["id"], "✅ ربات متوقف شد.", True)
    handle_admin_bot_detail(query, bot_id)


def handle_admin_restart_bot(query: dict, bot_id: int):
    """راه‌اندازی مجدد ربات توسط ادمین"""
    admin_id = query["from"]["id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        bot = conn.execute("SELECT * FROM deployed_bots WHERE id=?", (bot_id,)).fetchone()
    if not bot:
        answer_callback(query["id"], "❌ ربات یافت نشد!", True)
        return
    old_proc = bot_processes.get(bot_id)
    if old_proc:
        try:
            old_proc.terminate()
            old_proc.wait(timeout=3)
        except Exception:
            pass
    start_bot_process(bot_id, bot["file_path"], bot["bot_name"], bot["user_id"])
    with get_db() as conn:
        conn.execute("UPDATE deployed_bots SET status='running' WHERE id=?", (bot_id,))
        conn.commit()
    answer_callback(query["id"], "✅ ربات مجدداً راه‌اندازی شد.", True)
    handle_admin_bot_detail(query, bot_id)


def handle_admin_library_owner(query: dict, user_id_target: int):
    """نمایش جزئیات کاربر مالک کتابخانه"""
    admin_id = query["from"]["id"]
    if not is_admin(admin_id):
        return
    handle_admin_user_detail(query, user_id_target)


# ─────────────────────────────────────────────
#  handler های دستیار وب پیشرفته
# ─────────────────────────────────────────────

def handle_web_tutorial(query: dict):
    """نمایش راهنمای دستیار وب"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    text = (
        "🎓 *راهنمای دستیار وب*\n\n"
        "با این ابزار می‌توانید وب‌سایت HTML/CSS/JS بسازید.\n\n"
        "📝 *مراحل ساخت سایت:*\n"
        "۱. یک پروژه جدید ایجاد کنید\n"
        "۲. HTML ساختار صفحه را بنویسید\n"
        "۳. CSS استایل را اعمال کنید\n"
        "۴. JS رفتار صفحه را تعریف کنید\n"
        "۵. پیش‌نمایش بگیرید\n"
        "۶. فایل نهایی را دانلود کنید\n\n"
        "💡 *نکته:* از دکمه «المان‌ها» برای اضافه کردن\n"
        "عناصر آماده استفاده کنید."
    )
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("🎨 شروع پروژه", "web_new_project"), ("📂 پروژه‌هایم", "web_manage_projects")],
        [("🔙 بازگشت", "web_assistant_menu")]
    ]))


def handle_web_examples(query: dict):
    """نمایش نمونه پروژه‌های وب"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    text = (
        "💡 *نمونه پروژه‌های آماده*\n\n"
        "قالب‌های زیر آماده استفاده هستند:\n\n"
        "📰 *وبلاگ* - مناسب برای نوشتن مطلب\n"
        "💼 *پورتفولیو* - نمایش کارهای شما\n"
        "🚀 *صفحه فرود* - معرفی محصول یا خدمات\n\n"
        "هر قالب شامل HTML، CSS و JS پایه است."
    )
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard([
        [("📰 وبلاگ", "use_template:blog"), ("💼 پورتفولیو", "use_template:portfolio")],
        [("🚀 صفحه فرود", "use_template:landing")],
        [("🔙 بازگشت", "web_assistant_menu")]
    ]))


def handle_web_add_element(query: dict, element_type: str):
    """اضافه کردن المان HTML به پروژه"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")
    if not project_id:
        answer_callback(query["id"], "❌ ابتدا یک پروژه را باز کنید.", True)
        return

    snippets = {
        "heading": '<h2>عنوان بخش</h2>',
        "image": '<img src="تصویر.jpg" alt="توضیح تصویر" style="max-width:100%;">',
        "link": '<a href="https://example.com">متن لینک</a>',
        "list": '<ul>\n  <li>مورد اول</li>\n  <li>مورد دوم</li>\n  <li>مورد سوم</li>\n</ul>',
        "table": '<table border="1">\n  <tr><th>عنوان ۱</th><th>عنوان ۲</th></tr>\n  <tr><td>داده ۱</td><td>داده ۲</td></tr>\n</table>',
        "audio": '<audio controls>\n  <source src="صدا.mp3" type="audio/mpeg">\n</audio>',
        "video": '<video controls width="100%">\n  <source src="ویدیو.mp4" type="video/mp4">\n</video>',
    }
    names = {
        "heading": "عنوان", "image": "تصویر", "link": "لینک",
        "list": "لیست", "table": "جدول", "audio": "صدا", "video": "ویدیو"
    }

    snippet = snippets.get(element_type, "")
    name = names.get(element_type, element_type)

    with get_db() as conn:
        proj = conn.execute("SELECT html FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
    if not proj:
        answer_callback(query["id"], "❌ پروژه یافت نشد.", True)
        return

    new_html = (proj["html"] or "") + "\n" + snippet
    with get_db() as conn:
        conn.execute("UPDATE web_projects SET html=?, updated_at=? WHERE id=?",
                     (new_html, datetime.now().isoformat(), project_id))
        conn.commit()

    edit_message(chat_id, msg_id,
        f"✅ *{name}* به HTML اضافه شد!\n\nکد اضافه‌شده:\n`{snippet[:100]}`",
        reply_markup=inline_keyboard([
            [("✏️ ویرایش HTML", "web_edit_html"), ("👁 پیش‌نمایش", "web_preview")],
            [("🔙 ویرایش پروژه", f"web_edit_project:{project_id}")]
        ])
    )


def handle_web_css_helper(query: dict, css_type: str):
    """کمک‌دهنده CSS برای ویرایش استایل"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")

    templates = {
        "color": "color: #333333;\nbackground-color: #ffffff;",
        "font": "font-family: Arial, sans-serif;\nfont-size: 16px;\nfont-weight: bold;",
        "size": "width: 100%;\nmax-width: 800px;\nheight: auto;",
        "background": "background-color: #f5f5f5;\nbackground-image: linear-gradient(135deg, #667eea, #764ba2);",
        "border": "border: 1px solid #ccc;\nborder-radius: 8px;\nbox-shadow: 0 2px 4px rgba(0,0,0,0.1);",
        "spacing": "margin: 10px auto;\npadding: 20px;\ngap: 16px;",
    }
    names = {
        "color": "رنگ‌ها", "font": "فونت", "size": "اندازه",
        "background": "پس‌زمینه", "border": "کادر", "spacing": "فاصله‌گذاری"
    }

    snippet = templates.get(css_type, "")
    name = names.get(css_type, css_type)

    if project_id and snippet:
        with get_db() as conn:
            proj = conn.execute("SELECT css FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
        if proj:
            new_css = (proj["css"] or "") + "\n/* " + name + " */\n" + snippet
            with get_db() as conn:
                conn.execute("UPDATE web_projects SET css=?, updated_at=? WHERE id=?",
                             (new_css, datetime.now().isoformat(), project_id))
                conn.commit()
            edit_message(chat_id, msg_id,
                f"✅ کد CSS *{name}* اضافه شد!\n\n`{snippet}`",
                reply_markup=inline_keyboard([
                    [("✏️ ویرایش CSS", "web_edit_css"), ("👁 پیش‌نمایش", "web_preview")],
                    [("🔙 ویرایش پروژه", f"web_edit_project:{project_id}")]
                ])
            )
            return

    edit_message(chat_id, msg_id,
        f"💡 *قالب CSS برای {name}:*\n\n`{snippet}`\n\nابتدا یک پروژه را باز کنید تا اعمال شود.",
        reply_markup=inline_keyboard([
            [("📂 پروژه‌هایم", "web_manage_projects")],
            [("🔙 دستیار وب", "web_assistant_menu")]
        ])
    )


def handle_web_js_snippet(query: dict, js_type: str):
    """اضافه کردن قطعه کد JS آماده"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    state = get_state(user_id)
    project_id = state.get("data", {}).get("project_id")

    snippets = {
        "alert": 'function showAlert(msg) {\n  alert(msg || "پیام!");\n}\n// showAlert("سلام!");',
        "click": 'document.querySelector("#btn").addEventListener("click", function() {\n  alert("کلیک شد!");\n});',
        "form": 'document.querySelector("form").addEventListener("submit", function(e) {\n  e.preventDefault();\n  alert("فرم ارسال شد!");\n});',
        "timer": 'setTimeout(function() {\n  alert("زمان تمام شد!");\n}, 3000); // ۳ ثانیه',
    }
    names = {"alert": "پیام هشدار", "click": "رویداد کلیک", "form": "ارسال فرم", "timer": "تایمر"}

    snippet = snippets.get(js_type, "")
    name = names.get(js_type, js_type)

    if project_id and snippet:
        with get_db() as conn:
            proj = conn.execute("SELECT js FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
        if proj:
            new_js = (proj["js"] or "") + "\n// " + name + "\n" + snippet
            with get_db() as conn:
                conn.execute("UPDATE web_projects SET js=?, updated_at=? WHERE id=?",
                             (new_js, datetime.now().isoformat(), project_id))
                conn.commit()
            edit_message(chat_id, msg_id,
                f"✅ کد JS *{name}* اضافه شد!\n\n`{snippet[:120]}`",
                reply_markup=inline_keyboard([
                    [("✏️ ویرایش JS", "web_edit_js"), ("👁 پیش‌نمایش", "web_preview")],
                    [("🔙 ویرایش پروژه", f"web_edit_project:{project_id}")]
                ])
            )
            return

    edit_message(chat_id, msg_id,
        f"💡 *قطعه کد JS - {name}:*\n\n`{snippet}`\n\nابتدا یک پروژه را باز کنید.",
        reply_markup=inline_keyboard([
            [("📂 پروژه‌هایم", "web_manage_projects")],
            [("🔙 دستیار وب", "web_assistant_menu")]
        ])
    )


# ─────────────────────────────────────────────
#  ترکیبگر ایموجی (Emoji Kitchen)
# ─────────────────────────────────────────────

def _emoji_codepoint(emoji: str) -> str:
    """استخراج اولین کدپوینت معنادار ایموجی"""
    for c in emoji:
        cp = ord(c)
        if cp > 0x2000:  # صرف‌نظر از فاصله و کنترل کاراکترها
            return f"{cp:x}"
    return ""


def _find_kitchen_url(e1: str, e2: str) -> str:
    """پیدا کردن URL ترکیب ایموجی از Emoji Kitchen گوگل"""
    c1 = _emoji_codepoint(e1)
    c2 = _emoji_codepoint(e2)
    if not c1 or not c2:
        return ""

    base = "https://www.gstatic.com/android/keyboard/emojikitchen"
    dates = [
        "20230803", "20230301", "20221101", "20220815",
        "20220406", "20211115", "20210521", "20210218", "20201001"
    ]

    for date in dates:
        for first, second in [(c1, c2), (c2, c1)]:
            url = f"{base}/{date}/u{first}/u{first}_u{second}.png"
            try:
                r = requests.head(url, timeout=4,
                                  headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12)"})
                if r.status_code == 200:
                    return url
            except Exception:
                continue
    return ""


def _is_emoji(text: str) -> bool:
    """بررسی اینکه آیا کاراکتر ایموجی است"""
    for c in text:
        cp = ord(c)
        if (0x1F300 <= cp <= 0x1FAFF or   # ایموجی‌های اصلی
                0x2600 <= cp <= 0x27BF or  # نمادهای متفرقه
                0x2300 <= cp <= 0x23FF or  # نمادهای فنی
                0xFE00 <= cp <= 0xFE0F or  # variation selectors
                0x1F000 <= cp <= 0x1F02F): # mahjong/domino
            return True
    return False


def _extract_emojis(text: str) -> list:
    """استخراج ایموجی‌ها از متن"""
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        cp = ord(c)
        # ایموجی‌های چندبایتی (ZWJ sequences)
        if cp > 0x2000:
            emoji = c
            # بررسی کاراکترهای بعدی (variation selector، ZWJ، skin tone)
            j = i + 1
            while j < len(text) and ord(text[j]) in (0xFE0F, 0x200D, 0x20E3) or \
                  (j < len(text) and 0x1F3FB <= ord(text[j]) <= 0x1F3FF):
                emoji += text[j]
                j += 1
            result.append(emoji)
            i = j
        else:
            i += 1
    return [e for e in result if _is_emoji(e)]


def handle_emoji_mixer_menu(query: dict):
    """منوی اصلی ترکیبگر ایموجی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    set_state(user_id, "emoji_mix_waiting")

    edit_message(
        chat_id, msg_id,
        "🎨 *ترکیبگر ایموجی*\n\n"
        "دو ایموجی را کنار هم بنویس تا یک تصویر ترکیبی بسازم!\n\n"
        "📝 *نحوه استفاده:*\n"
        "فقط دو ایموجی بفرست، مثلاً:\n"
        "`😀🔥` یا `😂💀` یا `🐱🍕`\n\n"
        "⚡ از پایگاه داده Google Emoji Kitchen استفاده می‌شود\n"
        "🎯 بیش از ۵۰۰۰ ترکیب پشتیبانی می‌شود",
        reply_markup=inline_keyboard([
            [("💡 نمونه ترکیب‌ها", "emoji_mixer_help")],
            [("🔙 بازگشت", "main_menu")]
        ])
    )


def handle_emoji_mixer_help(query: dict):
    """نمایش نمونه ترکیب‌ها"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    edit_message(
        chat_id, msg_id,
        "💡 *نمونه ترکیب‌های جالب:*\n\n"
        "😀🔥 — صورت خندان + آتش\n"
        "😂💀 — خنده + جمجمه\n"
        "🐱🍕 — گربه + پیتزا\n"
        "😍🌈 — عاشق + رنگین‌کمان\n"
        "👻🎃 — روح + کدو\n"
        "🦊🌸 — روباه + گل\n"
        "😎🍦 — کول + بستنی\n"
        "🤡💔 — دلقک + قلب شکسته\n\n"
        "هر دو ایموجی را کنار هم بفرست:",
        reply_markup=inline_keyboard([
            [("🔙 بازگشت به ترکیبگر", "emoji_mixer")]
        ])
    )


def handle_emoji_mix_input(message: dict):
    """پردازش ورودی کاربر و ترکیب ایموجی‌ها"""
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    emojis = _extract_emojis(text)

    if len(emojis) < 2:
        send_message(
            chat_id,
            "❌ لطفاً *دقیقاً دو ایموجی* بفرست.\n\n"
            "مثال: `😀🔥` یا `😂💀`",
            reply_markup=inline_keyboard([
                [("💡 نمونه‌ها", "emoji_mixer_help"), ("🔙 بازگشت", "main_menu")]
            ])
        )
        return

    e1, e2 = emojis[0], emojis[1]

    waiting_msg = send_message(chat_id, f"⏳ در حال ترکیب {e1} و {e2} ...")

    url = _find_kitchen_url(e1, e2)

    if waiting_msg.get("ok"):
        delete_message(chat_id, waiting_msg["result"]["message_id"])

    if not url:
        send_message(
            chat_id,
            f"😔 ترکیب {e1}+{e2} در پایگاه داده موجود نیست.\n\n"
            "💡 ایموجی‌های صورت بیشترین ترکیب را دارند.\n"
            "مثلاً: `😀🔥`، `😂💀`، `😍🌈`",
            reply_markup=inline_keyboard([
                [("🔄 دوباره", "emoji_mixer")],
                [("💡 نمونه‌ها", "emoji_mixer_help"), ("🔙 بازگشت", "main_menu")]
            ])
        )
        clear_state(user_id)
        return

    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12)"})
        if r.status_code != 200 or len(r.content) < 100:
            raise Exception("دریافت نشد")

        tmp_path = LOGS_DIR / f"emoji_{user_id}_{int(time.time())}.png"
        with open(tmp_path, "wb") as f:
            f.write(r.content)

        # ارسال به عنوان استیکر
        with open(tmp_path, "rb") as f:
            res = api("sendSticker", {"chat_id": chat_id}, files={"sticker": f})

        # اگه استیکر قبول نشد، عکس بفرست
        if not res or not res.get("ok"):
            with open(tmp_path, "rb") as f:
                api("sendPhoto", {"chat_id": chat_id, "caption": f"🎨 {e1}+{e2}"}, files={"photo": f})

        try:
            tmp_path.unlink()
        except Exception:
            pass

        send_message(
            chat_id,
            f"✅ ترکیب {e1}+{e2} آماده شد!\n\nدو ایموجی دیگر بفرست:",
            reply_markup=inline_keyboard([
                [("🔄 ترکیب جدید", "emoji_mixer")],
                [("🔙 منوی اصلی", "main_menu")]
            ])
        )

    except Exception as e:
        log.error(f"emoji mix error: {e}")
        send_message(
            chat_id,
            f"❌ خطا در ترکیب {e1}+{e2}. دوباره امتحان کن.",
            reply_markup=inline_keyboard([
                [("🔄 دوباره", "emoji_mixer"), ("🔙 بازگشت", "main_menu")]
            ])
        )

    clear_state(user_id)


# ─────────────────────────────────────────────
#  سرگرمی یونیکد
# ─────────────────────────────────────────────

def handle_unicode_fun_menu(query: dict):
    """منوی سرگرمی یونیکد"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(
        chat_id, msg_id,
        "🎭 *سرگرمی یونیکد*\n\n"
        "با ایموجی‌ها کارهای جالب انجام بده!\n\n"
        "🖼 *ایموجی به GIF* — هر ایموجی رو به انیمیشن تبدیل کن\n"
        "🎨 *ترکیبگر ایموجی* — دو ایموجی رو با هم ترکیب کن",
        reply_markup=inline_keyboard([
            [("🖼 ایموجی به GIF", "emoji_to_gif"), ("🎨 ترکیب ایموجی", "emoji_mixer")],
            [("🔙 بازگشت", "assistant_code_menu")]
        ])
    )


def handle_emoji_to_gif_menu(query: dict):
    """منوی ایموجی به GIF"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    set_state(user_id, "emoji_to_gif_waiting")
    edit_message(
        chat_id, msg_id,
        "🖼 *ایموجی به GIF*\n\n"
        "یک ایموجی بفرست تا انیمیشن GIF آن را برایت بفرستم!\n\n"
        "مثال: `😂` یا `🔥` یا `❤️`\n\n"
        "⚡ از Noto Emoji گوگل استفاده می‌شود",
        reply_markup=inline_keyboard([
            [("🔙 بازگشت", "unicode_fun_menu")]
        ])
    )


def _emoji_to_gif_url(emoji: str) -> str:
    """ساخت URL گیف Noto Emoji گوگل"""
    code = "-".join(f"{ord(c):x}" for c in emoji if ord(c) != 0xfe0f)
    return f"https://fonts.gstatic.com/s/e/notoemoji/latest/{code}/512.gif"


def handle_emoji_to_gif_input(message: dict):
    """پردازش ایموجی و ارسال GIF"""
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    emojis = _extract_emojis(text)
    if not emojis:
        send_message(
            chat_id,
            "❌ لطفاً یک ایموجی بفرست.\nمثال: `😂` یا `🔥`",
            reply_markup=inline_keyboard([
                [("🔙 بازگشت", "unicode_fun_menu")]
            ])
        )
        return

    emoji = emojis[0]
    url = _emoji_to_gif_url(emoji)

    try:
        r = requests.get(url, timeout=8,
                         headers={"User-Agent": "Mozilla/5.0 (Linux; Android 12)"})
        if r.status_code == 200 and len(r.content) > 100:
            tmp_path = LOGS_DIR / f"emoji_gif_{user_id}_{int(time.time())}.gif"
            with open(tmp_path, "wb") as f:
                f.write(r.content)

            with open(tmp_path, "rb") as f:
                api("sendAnimation", {
                    "chat_id": chat_id,
                    "caption": f"🎬 {emoji}"
                }, files={"animation": f})

            try:
                tmp_path.unlink()
            except Exception:
                pass

            send_message(
                chat_id,
                "✅ ایموجی دیگری بفرست:",
                reply_markup=inline_keyboard([
                    [("🎨 ترکیب ایموجی", "emoji_mixer")],
                    [("🔙 بازگشت", "unicode_fun_menu")]
                ])
            )
        else:
            raise Exception(f"status {r.status_code}")

    except Exception as e:
        log.error(f"emoji_to_gif error: {e}")
        send_message(
            chat_id,
            f"😔 متأسفانه GIF برای {emoji} پیدا نشد.\nایموجی دیگری امتحان کن.",
            reply_markup=inline_keyboard([
                [("🔄 دوباره", "emoji_to_gif")],
                [("🔙 بازگشت", "unicode_fun_menu")]
            ])
        )
        clear_state(user_id)
        return

    # state رو نگه می‌داریم تا کاربر بتونه ایموجی‌های بیشتری بفرسته


# ─────────────────────────────────────────────
#  سیستم API Keys کدبات
# ─────────────────────────────────────────────

import hashlib
import secrets

API_DOCS_URL = "https://ble.ir/kodbot?start=api_docs"  # بعد جایگزین می‌شه


def _generate_api_key() -> tuple:
    """ساخت کلید API - برمیگردونه (key_plain, key_hash, key_prefix)"""
    raw = secrets.token_hex(24)
    key_plain = f"kdb_{raw}"
    key_hash = hashlib.sha256(key_plain.encode()).hexdigest()
    key_prefix = f"kdb_{raw[:8]}..."
    return key_plain, key_hash, key_prefix


def _get_user_plan_limits(user_id: int) -> dict:
    """محدودیت‌های کلید API بر اساس پلن کاربر"""
    with get_db() as conn:
        sub = conn.execute(
            "SELECT plan, expires_at FROM subscriptions WHERE user_id=? AND expires_at > ? ORDER BY expires_at DESC LIMIT 1",
            (user_id, datetime.now().isoformat())
        ).fetchone()

    if not sub:
        return {"max_keys": 1, "daily_requests": 100, "plan": "رایگان"}

    plan = sub["plan"]
    limits = {
        "basic":        {"max_keys": 3,   "daily_requests": 1000,   "plan": "پایه"},
        "professional": {"max_keys": 10,  "daily_requests": 10000,  "plan": "حرفه‌ای"},
        "enterprise":   {"max_keys": 100, "daily_requests": 500000, "plan": "سازمانی"},
    }
    return limits.get(plan, {"max_keys": 1, "daily_requests": 100, "plan": "رایگان"})


def _validate_api_key(key: str) -> dict | None:
    """بررسی اعتبار کلید API - برمیگردونه dict کلید یا None"""
    if not key.startswith("kdb_"):
        return None
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash=? AND is_active=1",
            (key_hash,)
        ).fetchone()
    if not row:
        return None
    if row["expires_at"] and row["expires_at"] < datetime.now().isoformat():
        return None
    return dict(row)


def handle_api_keys_menu(query: dict):
    """منوی اصلی API Keys"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    limits = _get_user_plan_limits(user_id)
    with get_db() as conn:
        keys = conn.execute(
            "SELECT * FROM api_keys WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    active = sum(1 for k in keys if k["is_active"])

    edit_message(
        chat_id, msg_id,
        f"🔑 *API کدبات*\n\n"
        f"با کلید API می‌توانید از خارج از ربات،\n"
        f"درخواست JSON ارسال کنید.\n\n"
        f"📊 *وضعیت شما:*\n"
        f"• پلن: *{limits['plan']}*\n"
        f"• کلیدهای فعال: *{active}* از *{limits['max_keys']}*\n"
        f"• محدودیت روزانه: *{limits['daily_requests']:,}* درخواست\n\n"
        f"🔗 لینک فرمت: `https://ble.ir/kodbot?start=api_KEY`",
        reply_markup=inline_keyboard([
            [("➕ کلید جدید", "api_key_create"), ("📋 کلیدهای من", "api_keys_list")],
            [("📖 مستندات", "api_docs")],
            [("🔙 بازگشت", "main_menu")]
        ])
    )


def handle_api_key_create(query: dict):
    """شروع ساخت کلید جدید"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    limits = _get_user_plan_limits(user_id)
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) as c FROM api_keys WHERE user_id=? AND is_active=1",
            (user_id,)
        ).fetchone()["c"]

    if count >= limits["max_keys"]:
        edit_message(
            chat_id, msg_id,
            f"❌ *به حداکثر کلید رسیدی!*\n\n"
            f"پلن *{limits['plan']}* فقط *{limits['max_keys']}* کلید فعال دارد.\n"
            f"برای افزایش محدودیت، پلن خود را ارتقا دهید.",
            reply_markup=inline_keyboard([
                [("🚀 ارتقای پلن", "upgrade_plan_menu")],
                [("🔙 بازگشت", "api_keys_menu")]
            ])
        )
        return

    set_state(user_id, "api_key_label")
    edit_message(
        chat_id, msg_id,
        "🏷 *نام کلید را وارد کن:*\n\n"
        "مثال: `سرور اصلی` یا `اپلیکیشن موبایل`\n\n"
        "این نام فقط برای شناسایی است.",
        reply_markup=inline_keyboard([
            [("🔙 انصراف", "api_keys_menu")]
        ])
    )


def handle_api_key_label_input(message: dict):
    """دریافت نام کلید و ساخت آن"""
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    label = message.get("text", "").strip()[:50]

    if not label:
        send_message(chat_id, "❌ نام نمی‌تواند خالی باشد.")
        return

    key_plain, key_hash, key_prefix = _generate_api_key()

    with get_db() as conn:
        # تاریخ انقضا = تاریخ انقضای اشتراک کاربر
        sub = conn.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id=? AND expires_at > ? ORDER BY expires_at DESC LIMIT 1",
            (user_id, datetime.now().isoformat())
        ).fetchone()
        expires_at = sub["expires_at"] if sub else None

        conn.execute(
            "INSERT INTO api_keys (user_id, key_hash, key_prefix, label, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (user_id, key_hash, key_prefix, label, datetime.now().isoformat(), expires_at)
        )
        conn.commit()

    # لینک دعوت برای استفاده از API
    api_link = f"https://ble.ir/kodbot?start=api_{key_plain}"

    send_message(
        chat_id,
        f"✅ *کلید API ساخته شد!*\n\n"
        f"🏷 نام: *{label}*\n"
        f"🔑 کلید:\n`{key_plain}`\n\n"
        f"🔗 لینک API:\n`{api_link}`\n\n"
        f"⚠️ *این کلید را جای امنی ذخیره کن!*\n"
        f"دیگر نمایش داده نخواهد شد.\n\n"
        f"📌 *نحوه استفاده:*\n"
        f"این لینک را در مرورگر باز کن یا\n"
        f"با JSON به کدبات بفرست.",
        reply_markup=inline_keyboard([
            [("📋 کلیدهای من", "api_keys_list")],
            [("📖 مستندات", "api_docs")],
            [("🔙 منوی API", "api_keys_menu")]
        ])
    )
    clear_state(user_id)


def handle_api_keys_list(query: dict):
    """نمایش لیست کلیدها"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        keys = conn.execute(
            "SELECT * FROM api_keys WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()

    if not keys:
        edit_message(
            chat_id, msg_id,
            "📋 *کلیدهای API*\n\nهنوز کلیدی نساختی.",
            reply_markup=inline_keyboard([
                [("➕ ساخت اولین کلید", "api_key_create")],
                [("🔙 بازگشت", "api_keys_menu")]
            ])
        )
        return

    text = "📋 *کلیدهای API شما:*\n\n"
    buttons = []
    for k in keys:
        status = "✅" if k["is_active"] else "❌"
        exp = k["expires_at"][:10] if k["expires_at"] else "نامحدود"
        text += f"{status} *{k['label']}*\n`{k['key_prefix']}` | انقضا: {exp} | {k['request_count']} درخواست\n\n"
        buttons.append([(f"{status} {k['label']}", f"api_key_detail:{k['id']}")])

    buttons.append([("🔙 بازگشت", "api_keys_menu")])
    edit_message(chat_id, msg_id, text, reply_markup=inline_keyboard(buttons))


def handle_api_key_detail(query: dict, key_id: int):
    """جزئیات یک کلید"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    with get_db() as conn:
        key = conn.execute(
            "SELECT * FROM api_keys WHERE id=? AND user_id=?",
            (key_id, user_id)
        ).fetchone()

    if not key:
        answer_callback(query["id"], "❌ کلید پیدا نشد.", True)
        return

    status = "✅ فعال" if key["is_active"] else "❌ غیرفعال"
    exp = key["expires_at"][:10] if key["expires_at"] else "نامحدود"
    last = key["last_used"][:16] if key["last_used"] else "هرگز"

    edit_message(
        chat_id, msg_id,
        f"🔑 *{key['label']}*\n\n"
        f"• وضعیت: {status}\n"
        f"• پیشوند: `{key['key_prefix']}`\n"
        f"• انقضا: {exp}\n"
        f"• کل درخواست‌ها: {key['request_count']}\n"
        f"• آخرین استفاده: {last}\n"
        f"• ساخته شده: {key['created_at'][:10]}",
        reply_markup=inline_keyboard([
            [("🔄 " + ("غیرفعال کن" if key["is_active"] else "فعال کن"),
              f"api_key_toggle:{key_id}")],
            [("🗑 حذف کلید", f"api_key_delete:{key_id}")],
            [("🔙 بازگشت", "api_keys_list")]
        ])
    )


def handle_api_key_toggle(query: dict, key_id: int):
    """فعال/غیرفعال کردن کلید"""
    user_id = query["from"]["id"]
    with get_db() as conn:
        key = conn.execute("SELECT * FROM api_keys WHERE id=? AND user_id=?", (key_id, user_id)).fetchone()
        if not key:
            answer_callback(query["id"], "❌ کلید پیدا نشد.", True)
            return
        new_status = 0 if key["is_active"] else 1
        conn.execute("UPDATE api_keys SET is_active=? WHERE id=?", (new_status, key_id))
        conn.commit()
    answer_callback(query["id"], "✅ وضعیت تغییر کرد.", True)
    handle_api_key_detail(query, key_id)


def handle_api_key_delete(query: dict, key_id: int):
    """حذف کلید"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (key_id, user_id))
        conn.commit()
    answer_callback(query["id"], "🗑 کلید حذف شد.", True)
    handle_api_keys_list(query)


def handle_api_docs(query: dict):
    """لینک مستندات API"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(
        chat_id, msg_id,
        "📖 *مستندات API کدبات*\n\n"
        "برای مشاهده مستندات کامل،\n"
        "روی دکمه زیر بزنید:",
        reply_markup=inline_keyboard([
            [("📖 مشاهده مستندات", "url", API_DOCS_URL)],
            [("🔙 بازگشت", "api_keys_menu")]
        ])
    )


def handle_api_start(message: dict, key_plain: str):
    """پردازش درخواست API از طریق لینک ?start=api_KEY"""
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]

    key_data = _validate_api_key(key_plain)
    if not key_data:
        send_message(chat_id,
            "❌ *کلید API نامعتبر یا منقضی شده است.*\n\n"
            "از منوی API کدبات کلید جدید بسازید.",
            reply_markup=inline_keyboard([[("🔑 منوی API", "api_keys_menu")]])
        )
        return

    # آپدیت آمار
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET request_count=request_count+1, last_used=? WHERE id=?",
            (datetime.now().isoformat(), key_data["id"])
        )
        conn.commit()

    owner_id = key_data["user_id"]
    limits = _get_user_plan_limits(owner_id)
    with get_db() as conn:
        bots = conn.execute(
            "SELECT id, bot_name, status FROM deployed_bots WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (owner_id,)
        ).fetchall()

    bot_list = [{"id": b["id"], "name": b["bot_name"], "status": b["status"]} for b in bots]

    payload = {
        "ok": True,
        "api_version": "1.0",
        "key_label": key_data["label"],
        "user_id": owner_id,
        "plan": limits["plan"],
        "daily_limit": limits["daily_requests"],
        "request_count": key_data["request_count"] + 1,
        "bots": bot_list,
        "endpoints": {
            "list_bots":   f"https://ble.ir/kodbot?start=api_{key_plain}",
            "start_bot":   f"https://ble.ir/kodbot?start=api_{key_plain}__start__BOT_ID",
            "stop_bot":    f"https://ble.ir/kodbot?start=api_{key_plain}__stop__BOT_ID",
            "restart_bot": f"https://ble.ir/kodbot?start=api_{key_plain}__restart__BOT_ID",
            "bot_status":  f"https://ble.ir/kodbot?start=api_{key_plain}__status__BOT_ID",
            "bot_log":     f"https://ble.ir/kodbot?start=api_{key_plain}__log__BOT_ID",
        }
    }

    send_message(chat_id,
        f"✅ *API کدبات*\n\n"
        f"🏷 کلید: *{key_data['label']}*\n"
        f"👤 پلن: *{limits['plan']}*\n"
        f"🤖 تعداد ربات‌ها: *{len(bot_list)}*\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```",
        reply_markup=inline_keyboard([
            [("🤖 مدیریت ربات‌ها", "bots_menu")],
            [("🔑 منوی API", "api_keys_menu")]
        ])
    )


def _handle_api_bot_action(message: dict, key_plain: str, action: str, bot_id: int):
    """اجرای عملیات روی ربات از طریق API"""
    chat_id = message["chat"]["id"]

    key_data = _validate_api_key(key_plain)
    if not key_data:
        send_message(chat_id, '{"ok": false, "error": "invalid_key"}')
        return

    owner_id = key_data["user_id"]
    with get_db() as conn:
        bot = conn.execute(
            "SELECT * FROM deployed_bots WHERE id=? AND user_id=?",
            (bot_id, owner_id)
        ).fetchone()

    if not bot:
        send_message(chat_id, f'{{"ok": false, "error": "bot_not_found", "bot_id": {bot_id}}}')
        return

    result = {"ok": True, "bot_id": bot_id, "bot_name": bot["bot_name"], "action": action}

    if action == "start":
        start_bot_process(bot_id, bot["file_path"], bot["bot_name"], owner_id)
        with get_db() as conn:
            conn.execute("UPDATE deployed_bots SET status='running' WHERE id=?", (bot_id,))
            conn.commit()
        result["status"] = "running"

    elif action == "stop":
        proc = bot_processes.get(bot_id)
        if proc:
            try: proc.terminate()
            except: pass
        with get_db() as conn:
            conn.execute("UPDATE deployed_bots SET status='stopped', pid=NULL WHERE id=?", (bot_id,))
            conn.commit()
        result["status"] = "stopped"

    elif action == "restart":
        proc = bot_processes.get(bot_id)
        if proc:
            try: proc.terminate(); proc.wait(timeout=3)
            except: pass
        start_bot_process(bot_id, bot["file_path"], bot["bot_name"], owner_id)
        with get_db() as conn:
            conn.execute("UPDATE deployed_bots SET status='running' WHERE id=?", (bot_id,))
            conn.commit()
        result["status"] = "running"

    elif action == "status":
        proc = bot_processes.get(bot_id)
        result["status"] = bot["status"]
        result["running"] = proc is not None and proc.poll() is None
        result["pid"] = bot.get("pid")

    elif action == "log":
        log_path = Path(bot["file_path"]).parent / "bot.log" if bot["file_path"] else None
        if log_path and log_path.exists():
            with open(log_path) as lf:
                lines = lf.readlines()[-50:]
            result["log"] = "".join(lines)
        else:
            result["log"] = ""

    # آپدیت آمار
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET request_count=request_count+1, last_used=? WHERE id=?",
            (datetime.now().isoformat(), key_data["id"])
        )
        conn.commit()

    send_message(chat_id,
        f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
    )


# ─────────────────────────────────────────────
#  دستیار سایت
# ─────────────────────────────────────────────

SCRAPE_LIMITS = {
    "free":         {"daily": 1,   "max_kb": 100},
    "basic":        {"daily": 5,   "max_kb": 500},
    "professional": {"daily": 20,  "max_kb": 2048},
    "enterprise":   {"daily": 500, "max_kb": 51200},
}


def _get_scrape_limit(user_id: int) -> dict:
    with get_db() as conn:
        sub = conn.execute(
            "SELECT plan FROM subscriptions WHERE user_id=? AND expires_at > ? ORDER BY expires_at DESC LIMIT 1",
            (user_id, datetime.now().isoformat())
        ).fetchone()
    plan = sub["plan"] if sub else "free"
    limit = SCRAPE_LIMITS.get(plan, SCRAPE_LIMITS["free"]).copy()
    limit["plan"] = plan
    return limit


def _get_domain(url: str) -> str:
    import urllib.parse
    try:
        return urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _today_scrape_count(user_id: int) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM scrape_requests WHERE user_id=? AND created_at LIKE ? AND status='done'",
            (user_id, f"{today}%")
        ).fetchone()
    return row["c"] if row else 0


def handle_web_site_assistant(query: dict):
    """منوی دستیار سایت"""
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    edit_message(
        chat_id, msg_id,
        "🌐 *دستیار سایت*\n\n"
        "ابزارهای کامل برای ساخت و تحلیل وب‌سایت:",
        reply_markup=inline_keyboard([
            [("🎨 ساخت صفحه وب", "web_assistant_menu")],
            [("🔧 ابزارهای وب", "web_tools_menu")],
            [("🔙 دستیار کد", "assistant_code_menu")]
        ])
    )


def handle_web_tools_menu(query: dict):
    """منوی ابزارهای وب"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    limit = _get_scrape_limit(user_id)
    used = _today_scrape_count(user_id)
    edit_message(
        chat_id, msg_id,
        f"🔧 *ابزارهای وب*\n\n"
        f"📊 پلن: *{limit['plan']}*\n"
        f"📥 استخراج امروز: *{used}* از *{limit['daily']}*\n"
        f"📦 حداکثر حجم: *{limit['max_kb']} KB*",
        reply_markup=inline_keyboard([
            [("📥 استخراج صفحه", "web_scrape_menu")],
            [("🔙 دستیار سایت", "web_site_assistant")]
        ])
    )


def handle_web_scrape_request_prompt(query: dict):
    """redirect به web_scrape_menu"""
    handle_web_scrape_menu(query)


def handle_web_scrape_menu(query: dict):
    """منوی استخراج صفحه"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    limit = _get_scrape_limit(user_id)
    used = _today_scrape_count(user_id)

    if used >= limit["daily"]:
        edit_message(
            chat_id, msg_id,
            f"❌ *محدودیت روزانه*\n\n"
            f"پلن *{limit['plan']}* فقط *{limit['daily']}* استخراج در روز دارد.\n"
            f"برای افزایش محدودیت پلن خود را ارتقا دهید.",
            reply_markup=inline_keyboard([
                [("🚀 ارتقای پلن", "upgrade_plan_menu")],
                [("🔙 بازگشت", "web_tools_menu")]
            ])
        )
        return

    set_state(user_id, "web_scrape_url")
    edit_message(
        chat_id, msg_id,
        "📥 *استخراج صفحه وب*\n\n"
        "آدرس سایت را ارسال کنید:\n\n"
        "💡 اگر دامنه قبلاً تایید شده باشد خودکار تحویل داده می‌شود.\n"
        "در غیر این صورت، کد استخراج‌شده برای بررسی ادمین ارسال می‌شود.",
        reply_markup=inline_keyboard([
            [("🔙 انصراف", "web_tools_menu")]
        ])
    )


def _extract_site_zip(url: str, max_bytes: int) -> tuple:
    """استخراج کامل HTML/CSS/JS/تصاویر یک صفحه و برگرداندن (zip_bytes, file_count, truncated)"""
    import urllib.parse
    import zipfile
    import io

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    try:
        import cloudscraper
        session = cloudscraper.create_scraper()
    except ImportError:
        session = requests.Session()
    session.headers.update(headers)

    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html_content = resp.text
    base_url = resp.url

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    downloaded = {}
    total_size = len(html_content.encode("utf-8"))

    def fetch_asset(asset_url: str):
        nonlocal total_size
        if asset_url in downloaded or total_size >= max_bytes:
            return
        try:
            full_url = urllib.parse.urljoin(base_url, asset_url)
            r = session.get(full_url, timeout=10)
            if r.status_code == 200:
                downloaded[asset_url] = r.content
                total_size += len(r.content)
        except Exception:
            pass

    for tag in soup.find_all("link", rel="stylesheet"):
        href = tag.get("href", "")
        if href:
            fetch_asset(href)
    for tag in soup.find_all("script", src=True):
        src_attr = tag.get("src", "")
        if src_attr:
            fetch_asset(src_attr)
    for tag in soup.find_all("img", src=True):
        src_attr = tag.get("src", "")
        if src_attr and not src_attr.startswith("data:"):
            fetch_asset(src_attr)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_content)
        used_names = {"index.html"}
        for asset_url, content in downloaded.items():
            fname = urllib.parse.urlparse(asset_url).path.lstrip("/").replace("/", "_") or "asset"
            while fname in used_names:
                fname = f"_{fname}"
            used_names.add(fname)
            try:
                zf.writestr(fname, content)
            except Exception:
                pass

    zip_buffer.seek(0)
    return zip_buffer.read(), len(downloaded) + 1, total_size >= max_bytes


def handle_web_scrape_url_input(message: dict):
    """دریافت URL - اگر دامنه قبلاً تایید و تأییدشده باشد خودکار تحویل می‌دهد،
    وگرنه استخراج را انجام داده و برای بررسی به مدیر می‌فرستد."""
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    url = message.get("text", "").strip()

    if not url.startswith("http"):
        url = "https://" + url

    domain = _get_domain(url)
    if not domain:
        send_message(chat_id, "❌ آدرس نامعتبر است.")
        clear_state(user_id)
        return

    # جلوگیری از دسترسی به آدرس‌های داخلی/خصوصی
    blocked = ("localhost", "127.", "0.0.0.0", "10.", "192.168.", "169.254.", "::1")
    if domain.startswith(blocked) or any(f".{b}" in domain for b in blocked):
        send_message(chat_id, "❌ این آدرس مجاز نیست.")
        clear_state(user_id)
        return

    limit = _get_scrape_limit(user_id)
    used = _today_scrape_count(user_id)
    if used >= limit["daily"]:
        send_message(chat_id, f"❌ محدودیت روزانه ({limit['daily']}) تمام شد.")
        clear_state(user_id)
        return

    with get_db() as conn:
        site = conn.execute("SELECT * FROM approved_sites WHERE domain=? AND is_active=1", (domain,)).fetchone()

    clear_state(user_id)
    waiting_msg = send_message(chat_id, f"⏳ در حال استخراج `{url}` ...")
    max_bytes = limit["max_kb"] * 1024

    try:
        zip_data, file_count, truncated = _extract_site_zip(url, max_bytes)
    except Exception as e:
        log.error(f"scrape error: {e}")
        send_message(chat_id, f"❌ خطا در دریافت `{url}`.\nممکن است سایت در دسترس نباشد.")
        return

    if waiting_msg.get("ok"):
        delete_message(chat_id, waiting_msg["result"]["message_id"])

    size_kb = len(zip_data) // 1024

    # ─── دامنه قبلاً تایید و تأییدشده است → تحویل خودکار ───
    if site and site["verified"]:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO scrape_requests (user_id, url, domain, status, result_size, created_at, approved_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, url, domain, "done", len(zip_data), datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()

        tmp_path = LOGS_DIR / f"scrape_{user_id}_{int(time.time())}.zip"
        with open(tmp_path, "wb") as f:
            f.write(zip_data)
        with open(tmp_path, "rb") as f:
            api("sendDocument", {
                "chat_id": user_id,
                "caption": (
                    f"📥 *استخراج موفق*\n\n🌐 آدرس: `{url}`\n📦 حجم: {size_kb} KB | {file_count} فایل\n"
                    f"{'⚠️ محدودیت حجم پلن رعایت شد.' if truncated else '✅ صفحه کامل دریافت شد.'}"
                ),
            }, files={"document": f})
        try:
            tmp_path.unlink()
        except Exception:
            pass
        send_message(chat_id, "✅ نتیجه ارسال شد.", reply_markup=inline_keyboard([[("🔙 بازگشت", "web_tools_menu")]]))
        return

    # ─── اولین بار برای این دامنه → ابتدا برای بررسی مدیر ارسال شود ───
    tmp_path = LOGS_DIR / f"scrape_review_{user_id}_{int(time.time())}.zip"
    with open(tmp_path, "wb") as f:
        f.write(zip_data)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO scrape_requests (user_id, url, domain, status, result_size, created_at, zip_path) VALUES (?,?,?,?,?,?,?)",
            (user_id, url, domain, "pending", len(zip_data), datetime.now().isoformat(), str(tmp_path))
        )
        req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    user_info = message["from"]
    name = f"{user_info.get('first_name','')} {user_info.get('last_name','')}".strip()

    for admin_id in ADMIN_IDS:
        with open(tmp_path, "rb") as f:
            api("sendDocument", {
                "chat_id": admin_id,
                "caption": (
                    f"📥 *استخراج جدید - نیاز به بررسی*\n\n"
                    f"👤 کاربر: {name} (`{user_id}`)\n"
                    f"🌐 آدرس: `{url}`\n"
                    f"🏠 دامنه: `{domain}` (اولین درخواست این دامنه)\n"
                    f"📦 حجم: {size_kb} KB | {file_count} فایل\n\n"
                    f"با تایید، این فایل برای کاربر ارسال و دامنه برای همیشه تایید می‌شود."
                ),
            }, files={"document": f})
        send_message(
            admin_id,
            "بررسی کردید؟",
            reply_markup=inline_keyboard([
                [("✅ تأیید و ارسال به کاربر", f"scrape_approve:{req_id}"), ("❌ رد", f"scrape_reject:{req_id}")]
            ])
        )

    send_message(
        chat_id,
        f"✅ *درخواست ارسال شد*\n\nاین اولین درخواست برای `{domain}` است.\n"
        f"پس از بررسی مدیر نتیجه دریافت می‌شود. دفعات بعد خودکار انجام می‌شود.",
        reply_markup=inline_keyboard([[("🔙 بازگشت", "web_tools_menu")]])
    )


def handle_scrape_approve(query: dict, req_id: int):
    """تأیید نهایی: فایل استخراج‌شده را برای کاربر می‌فرستد و دامنه را برای همیشه تایید می‌کند"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]

    if not is_admin(admin_id):
        return

    with get_db() as conn:
        req = conn.execute("SELECT * FROM scrape_requests WHERE id=?", (req_id,)).fetchone()

    if not req or req["status"] != "pending":
        answer_callback(query["id"], "❌ درخواست یافت نشد یا قبلاً پردازش شده.", True)
        return

    zip_path = req["zip_path"]
    if not zip_path or not Path(zip_path).exists():
        answer_callback(query["id"], "❌ فایل استخراج‌شده دیگر موجود نیست.", True)
        return

    with open(zip_path, "rb") as f:
        api("sendDocument", {
            "chat_id": req["user_id"],
            "caption": f"📥 *درخواست شما تایید شد!*\n\n🌐 آدرس: `{req['url']}`",
        }, files={"document": f})

    with get_db() as conn:
        conn.execute(
            "INSERT INTO approved_sites (domain, approved_by, approved_at, is_active, verified) VALUES (?,?,?,1,1) "
            "ON CONFLICT(domain) DO UPDATE SET is_active=1, verified=1, approved_by=excluded.approved_by, approved_at=excluded.approved_at",
            (req["domain"], admin_id, datetime.now().isoformat())
        )
        conn.execute(
            "UPDATE scrape_requests SET status='done', approved_by=?, approved_at=? WHERE id=?",
            (admin_id, datetime.now().isoformat(), req_id)
        )
        conn.commit()

    try:
        Path(zip_path).unlink()
    except Exception:
        pass

    edit_message(chat_id, msg_id, f"✅ تایید شد و برای کاربر ارسال شد.\n🏠 دامنه `{req['domain']}` از این پس خودکار تحویل داده می‌شود.")


def handle_scrape_reject(query: dict, req_id: int):
    """رد درخواست - ادمین دلیل می‌دهد"""
    admin_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    if not is_admin(admin_id):
        return
    with get_db() as conn:
        req = conn.execute("SELECT * FROM scrape_requests WHERE id=?", (req_id,)).fetchone()
    if not req:
        answer_callback(query["id"], "❌ درخواست پیدا نشد.", True)
        return
    set_state(admin_id, "scrape_reject_reason", {
        "req_id": req_id,
        "user_id": req["user_id"],
        "url": req["url"],
        "msg_id": msg_id
    })
    edit_message(chat_id, msg_id,
        "❌ *رد درخواست*\n\n"
        f"🌐 آدرس: `{req['url']}`\n\n"
        "دلیل رد را بنویسید:")


# ─── سایت‌های تأیید شده ───


def handle_web_download_zip(query: dict, project_id: int):
    """دانلود پروژه وب به صورت ZIP"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        proj = conn.execute("SELECT * FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
    if not proj:
        answer_callback(query["id"], "❌ پروژه پیدا نشد.", True)
        return
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", proj["html"] or "")
        zf.writestr("style.css", proj["css"] or "")
        zf.writestr("script.js", proj["js"] or "")
    buf.seek(0)
    tmp = LOGS_DIR / f"web_{user_id}_{project_id}.zip"
    with open(tmp, "wb") as f:
        f.write(buf.read())
    with open(tmp, "rb") as f:
        api("sendDocument", {"chat_id": chat_id, "caption": f"📦 پروژه: {proj['name']}"}, files={"document": f})
    try: tmp.unlink()
    except: pass
    answer_callback(query["id"], "✅ ZIP ارسال شد.", False)


def handle_web_download_html(query: dict, project_id: int):
    """دانلود پروژه وب به صورت HTML تکی"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    with get_db() as conn:
        proj = conn.execute("SELECT * FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
    if not proj:
        answer_callback(query["id"], "❌ پروژه پیدا نشد.", True)
        return
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="UTF-8"><title>{proj['name']}</title>
<style>{proj['css'] or ''}</style></head>
<body>{proj['html'] or ''}
<script>{proj['js'] or ''}</script>
</body></html>"""
    tmp = LOGS_DIR / f"web_{user_id}_{project_id}.html"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    with open(tmp, "rb") as f:
        api("sendDocument", {"chat_id": chat_id, "caption": f"📄 {proj['name']}.html"}, files={"document": f})
    try: tmp.unlink()
    except: pass
    answer_callback(query["id"], "✅ HTML ارسال شد.", False)


def handle_web_download_preview(query: dict, project_id: int):
    """پیش‌نمایش پروژه وب"""
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]
    msg_id = query["message"]["message_id"]
    with get_db() as conn:
        proj = conn.execute("SELECT * FROM web_projects WHERE id=? AND user_id=?", (project_id, user_id)).fetchone()
    if not proj:
        answer_callback(query["id"], "❌ پروژه پیدا نشد.", True)
        return
    # ارسال HTML به عنوان پیش‌نمایش
    preview = (proj["html"] or "")[:500]
    edit_message(chat_id, msg_id,
        f"👁 *پیش‌نمایش: {proj['name']}*\n\n"
        f"```html\n{preview}\n```",
        reply_markup=inline_keyboard([
            [("📦 دانلود ZIP", f"web_download_zip:{project_id}"),
             ("📄 دانلود HTML", f"web_download_html:{project_id}")],
            [("🔙 بازگشت", f"web_edit_project:{project_id}")]
        ])
    )


if __name__ == "__main__":
    main()
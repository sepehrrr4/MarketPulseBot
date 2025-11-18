import asyncio
import logging
import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ChatMemberHandler
)
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

# ایمپورت تنظیمات از فایل config.py
from config import settings

# ایمپورت دیتابیس
from database import (
    initialize_db, add_or_update_chat, remove_chat, get_user_chats,
    set_chat_interval, get_all_scheduled_chats, set_chat_assets, get_chat_assets,
    set_chat_language, get_chat_language,
    add_alert, get_all_alerts, get_user_alerts, delete_alert
)

# --- تنظیمات ---
# خواندن مقادیر حساس از فایل کانفیگ برای امنیت
REQUIRED_CHANNEL = settings.CHANNEL_ID 
PRICE_FILE = Path("prices.json") 

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- سیستم ترجمه (Localization) ---
TRANS = {
    "fa": {
        "welcome": "👋 <b>به ربات قیمت خوش آمدید!</b>\n\nلطفاً زبان خود را انتخاب کنید:\nPlease select your language:",
        "main_menu_text": "✅ <b>منوی اصلی</b>\n\nگزینه مورد نظر را انتخاب کنید:",
        "btn_prices": "📊 مشاهده قیمت‌ها",
        "btn_alerts": "🔔 مدیریت هشدارها",
        "btn_groups": "⚙️ مدیریت گروه‌ها",
        "btn_help": "❓ راهنما و آموزش",
        "btn_lang": "🌍 تغییر زبان / Language",
        "price_title": "📊 <b>قیمت‌های لحظه‌ای بازار:</b>\n",
        "alert_menu_title": "🔔 <b>منوی هشدارها:</b>",
        "btn_new_alert": "➕ ثبت هشدار جدید",
        "btn_my_alerts": "📋 هشدارهای من",
        "btn_back": "🔙 بازگشت",
        "btn_cancel": "❌ انصراف",
        "select_asset": "🎯 ارز مورد نظر را انتخاب کنید:",
        "enter_price": "🎯 ارز: <b>{asset}</b>\n🔢 لطفاً قیمت هدف را (به عدد انگلیسی) تایپ کنید:\nمثال: 95000",
        "alert_set": "✅ هشدار ثبت شد!\nهر وقت <b>{asset}</b> {cond} از <b>{target}</b> دلار شد خبرت می‌کنم.",
        "cond_above": "بیشتر",
        "cond_below": "کمتر",
        "no_alerts": "📭 شما هشداری ندارید.",
        "alert_deleted": "✅ هشدار حذف شد.",
        "group_menu_title": "مدیریت گروه‌ها:",
        "no_groups": "شما گروه فعالی ندارید. ربات را در گروه ادمین کنید.",
        "settings_title": "⚙️ تنظیمات: <b>{title}</b>",
        "sec": "ثانیه",
        "min": "دقیقه",
        "off": "🔕 خاموش",
        "active": "✅ فعال: ",
        "calc_error": "⚠️ فرمت اشتباه.\nمثال: /calc 0.5 BTC",
        "price_na": "⚠️ قیمت در دسترس نیست.",
        "join_msg": "⛔️ <b>عضویت اجباری</b>\n\nبرای استفاده از ربات باید عضو کانال ما باشید.",
        "btn_join": "📢 عضویت در کانال",
        "btn_verify": "✅ عضو شدم",
        "join_success": "✅ عضویت تایید شد! خوش آمدید.",
        "join_fail": "❌ هنوز عضو کانال نشده‌اید!",
        "help_text": (
            "📚 <b>راهنما و آموزش استفاده</b>\n\n"
            "🤖 <b>چگونه ربات را به گروه/کانال اضافه کنیم؟</b>\n"
            "1️⃣ وارد پروفایل ربات شوید و گزینه <i>Add to Group</i> را بزنید.\n"
            "2️⃣ گروه یا کانال خود را انتخاب کنید.\n"
            "3️⃣ <b>مهم:</b> بعد از افزودن، حتماً ربات را <b>Admin</b> کنید تا بتواند پیام بفرستد.\n\n"
            "🧮 <b>ماشین حساب:</b>\n"
            "دستور: <code>/calc [مقدار] [ارز]</code>\n"
            "مثال: <code>/calc 0.5 BTC</code>\n\n"
            "🔔 <b>هشدار قیمت:</b>\n"
            "از منوی اصلی دکمه «مدیریت هشدارها» را بزنید."
        )
    },
    "en": {
        "welcome": "👋 <b>Welcome to Crypto Price Bot!</b>\n\nPlease select your language:",
        "main_menu_text": "✅ <b>Main Menu</b>\n\nSelect an option:",
        "btn_prices": "📊 Live Prices",
        "btn_alerts": "🔔 Price Alerts",
        "btn_groups": "⚙️ Manage Groups",
        "btn_help": "❓ Help & Tutorial",
        "btn_lang": "🌍 Change Language",
        "price_title": "📊 <b>Live Market Prices:</b>\n",
        "alert_menu_title": "🔔 <b>Alerts Menu:</b>",
        "btn_new_alert": "➕ New Alert",
        "btn_my_alerts": "📋 My Alerts",
        "btn_back": "🔙 Back",
        "btn_cancel": "❌ Cancel",
        "select_asset": "🎯 Select an asset:",
        "enter_price": "🎯 Asset: <b>{asset}</b>\n🔢 Please type the target price (in numbers):\nExample: 95000",
        "alert_set": "✅ Alert Set!\nI will notify you when <b>{asset}</b> goes {cond} <b>{target}</b> USD.",
        "cond_above": "ABOVE",
        "cond_below": "BELOW",
        "no_alerts": "📭 You have no active alerts.",
        "alert_deleted": "✅ Alert deleted.",
        "group_menu_title": "Group Management:",
        "no_groups": "No active groups found. Add & Admin the bot in a group first.",
        "settings_title": "⚙️ Settings: <b>{title}</b>",
        "sec": "sec",
        "min": "min",
        "off": "🔕 Off",
        "active": "✅ Active: ",
        "calc_error": "⚠️ Invalid format.\nExample: /calc 0.5 BTC",
        "price_na": "⚠️ Price not available.",
        "join_msg": "⛔️ <b>Action Required</b>\n\nYou must join our channel to use this bot.",
        "btn_join": "📢 Join Channel",
        "btn_verify": "✅ I have joined",
        "join_success": "✅ Verified! Welcome.",
        "join_fail": "❌ You haven't joined yet!",
        "help_text": (
            "📚 <b>Help & Tutorial</b>\n\n"
            "🤖 <b>How to add bot to Group/Channel?</b>\n"
            "1️⃣ Go to bot profile and click <i>Add to Group</i>.\n"
            "2️⃣ Select your group or channel.\n"
            "3️⃣ <b>IMPORTANT:</b> You MUST promote the bot to <b>Admin</b> so it can send messages.\n\n"
            "🧮 <b>Calculator:</b>\n"
            "Cmd: <code>/calc [amount] [asset]</code>\n"
            "Ex: <code>/calc 0.5 BTC</code>\n\n"
            "🔔 <b>Price Alerts:</b>\n"
            "Use the 'Price Alerts' button in the main menu."
        )
    }
}

# --- حافظه موقت ---
LAST_PRICES = {}
PREVIOUS_PRICES = {}
LAST_SENT_MESSAGES = {}
USER_STATES = {}

KNOWN_ASSETS = {
    "BTC": "🪙 Bitcoin",
    "ETH": "♦️ Ethereum",
    "BNB": "🔶 BNB",
    "USDT": "💲 Tether",
    "TRX": "🔴 TRON",
    "GOLD": "⚜️ Gold",
}

# --- توابع کمکی ---
def t(key, chat_id):
    """تابع ترجمه سریع"""
    lang = get_chat_language(chat_id)
    return TRANS.get(lang, TRANS["fa"]).get(key, key)

def get_prices_from_file():
    global LAST_PRICES, PREVIOUS_PRICES
    try:
        if not PRICE_FILE.exists(): return {}
        with open(PRICE_FILE, "r", encoding="utf-8") as f:
            new_prices = json.load(f)
        
        if LAST_PRICES:
            temp_prev = {}
            for k, v in LAST_PRICES.items():
                if v and 'price_num' in v: temp_prev[k] = v['price_num']
            PREVIOUS_PRICES.update(temp_prev)
            
        LAST_PRICES = new_prices
        return new_prices
    except Exception as e:
        logger.error(f"Error reading prices: {e}")
        return {}

def calculate_trend(asset, current_price):
    prev = PREVIOUS_PRICES.get(asset)
    if prev is None: return ""
    if current_price > prev: return "🟢"
    elif current_price < prev: return "🔴"
    return "⚪️"

def format_price_message(prices, chat_id, enabled_assets_str="ALL"):
    if not prices: return t("price_na", chat_id)
    
    assets_to_show = KNOWN_ASSETS.keys() if enabled_assets_str == "ALL" else enabled_assets_str.split(",")
    
    lines = [t("price_title", chat_id)]
    has_data = False
    
    for code in KNOWN_ASSETS:
        if code not in assets_to_show: continue
        data = prices.get(code)
        if data and data.get("price"):
            name = KNOWN_ASSETS[code]
            trend = calculate_trend(code, data.get("price_num"))
            lines.append(f"{trend} <b>{name}</b>: <code>{data['price']}</code>")
            has_data = True
            
    return "\n".join(lines) if has_data else "No assets selected."

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL or REQUIRED_CHANNEL == "@YourChannelName": return True
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]: return False
        return True
    except: return True 

async def send_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    channel_url = f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"
    
    text = t("join_msg", cid)
    keyboard = [
        [InlineKeyboardButton(t("btn_join", cid), url=channel_url)],
        [InlineKeyboardButton(t("btn_verify", cid), callback_data="verify_join")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- هندلرها ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cid = update.effective_chat.id
    
    if not await check_membership(user_id, context):
        await send_join_request(update, context)
        return

    text = t("main_menu_text", cid)
    keyboard = [
        [InlineKeyboardButton(t("btn_prices", cid), callback_data="price_all")],
        [InlineKeyboardButton(t("btn_alerts", cid), callback_data="alerts_menu"), InlineKeyboardButton(t("btn_groups", cid), callback_data="manage_groups")],
        [InlineKeyboardButton(t("btn_help", cid), callback_data="help_menu"), InlineKeyboardButton(t("btn_lang", cid), callback_data="lang_menu")]
    ]
    
    if user_id in USER_STATES: del USER_STATES[user_id]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def lang_menu_handler(update, context):
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")],
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa")],
        [InlineKeyboardButton("🔙", callback_data="main_menu")]
    ]
    await update.callback_query.edit_message_text("Please select your language / لطفاً زبان را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

async def alerts_menu_handler(update, context):
    cid = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton(t("btn_new_alert", cid), callback_data="alert_new")],
        [InlineKeyboardButton(t("btn_my_alerts", cid), callback_data="alert_list")],
        [InlineKeyboardButton(t("btn_back", cid), callback_data="main_menu")]
    ]
    await update.callback_query.edit_message_text(t("alert_menu_title", cid), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def alert_new_handler(update, context):
    cid = update.effective_chat.id
    keyboard = []
    row = []
    for code in KNOWN_ASSETS:
        row.append(InlineKeyboardButton(code, callback_data=f"alert_sel_{code}"))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton(t("btn_back", cid), callback_data="alerts_menu")])
    await update.callback_query.edit_message_text(t("select_asset", cid), reply_markup=InlineKeyboardMarkup(keyboard))

async def alert_list_handler(update, context):
    user_id = update.effective_user.id
    cid = update.effective_chat.id
    alerts = get_user_alerts(user_id)
    if not alerts:
        await update.callback_query.edit_message_text(t("no_alerts", cid), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back", cid), callback_data="alerts_menu")]]))
        return
        
    text = t("btn_my_alerts", cid) + ":\n\n"
    keyboard = []
    for aid, asset, target, cond in alerts:
        icon = "📈" if cond == "ABOVE" else "📉"
        text += f"{icon} <b>{asset}</b>: {target:,.2f}$\n"
        keyboard.append([InlineKeyboardButton(f"🗑 {asset} {target}$", callback_data=f"alert_del_{aid}")])
    keyboard.append([InlineKeyboardButton(t("btn_back", cid), callback_data="alerts_menu")])
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    cid = query.message.chat_id

    # --- تنظیم زبان ---
    if data.startswith("set_lang_"):
        lang = data.split("_")[2]
        set_chat_language(cid, lang)
        await start_command(update, context)
        return

    if data == "lang_menu":
        await lang_menu_handler(update, context)
        return

    # --- عضویت ---
    if data == "verify_join":
        is_member = await check_membership(user_id, context)
        if is_member:
            await query.answer(t("join_success", cid), show_alert=True)
            await start_command(update, context)
        else:
            await query.answer(t("join_fail", cid), show_alert=True)
        return

    # چک برای سایر دکمه‌ها
    if not await check_membership(user_id, context):
        await send_join_request(update, context)
        return

    if data == "main_menu": await start_command(update, context)
    elif data == "alerts_menu": await alerts_menu_handler(update, context)
    elif data == "alert_new": await alert_new_handler(update, context)
    elif data == "alert_list": await alert_list_handler(update, context)
    
    elif data == "price_all":
        msg = format_price_message(LAST_PRICES, cid)
        kb = [[InlineKeyboardButton("🔄", callback_data="price_all")], [InlineKeyboardButton(t("btn_back", cid), callback_data="main_menu")]]
        try: await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        except: pass

    elif data == "help_menu":
        txt = t("help_text", cid) 
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back", cid), callback_data="main_menu")]]))

    elif data.startswith("alert_sel_"):
        asset = data.split("_")[2]
        USER_STATES[user_id] = {"action": "WAIT_PRICE", "asset": asset}
        msg = t("enter_price", cid).format(asset=asset)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_cancel", cid), callback_data="alerts_menu")]]))

    elif data.startswith("alert_del_"):
        delete_alert(int(data.split("_")[2]))
        await query.answer(t("alert_deleted", cid))
        await alert_list_handler(update, context)

    elif data == "manage_groups":
        await show_groups_menu(update, context)

    elif data.startswith("settings_"):
        await show_chat_settings(update, context, int(data.split("_")[1]))

    elif data.startswith("toggle_"):
        _, group_id, asset = data.split("_")
        group_id = int(group_id)
        curr = get_chat_assets(group_id)
        
        if curr == "ALL": lst = list(KNOWN_ASSETS.keys()) 
        elif curr == "": lst = []
        else: lst = curr.split(",")
            
        if asset in lst: lst.remove(asset)
        else: lst.append(asset)
            
        new_str = "ALL" if len(lst) == len(KNOWN_ASSETS) else ",".join(lst)
        set_chat_assets(group_id, new_str)
        await show_chat_settings(update, context, group_id)

    elif data.startswith("set_"):
        _, group_id, sec = data.split("_")
        group_id = int(group_id)
        sec = int(sec)
        
        for j in context.job_queue.get_jobs_by_name(str(group_id)): j.schedule_removal()
        if sec > 0:
            context.job_queue.run_repeating(post_prices_job, interval=sec, first=5, chat_id=group_id, name=str(group_id))
            await query.answer(t("active", cid) + str(sec))
        else:
            await query.answer(t("off", cid))
            
        set_chat_interval(group_id, sec)
        await show_chat_settings(update, context, group_id)

async def handle_text(update, context):
    user = update.effective_user
    cid = update.effective_chat.id
    
    if not await check_membership(user.id, context):
        await send_join_request(update, context)
        return

    state = USER_STATES.get(user.id)
    if not state or state["action"] != "WAIT_PRICE": return
    
    try:
        target = float(update.message.text.replace(",", ""))
        asset = state["asset"]
        curr = LAST_PRICES.get(asset, {}).get("price_num")
        if not curr: 
            await update.message.reply_text(t("price_na", cid))
            return
            
        cond = "ABOVE" if target > curr else "BELOW"
        add_alert(user.id, asset, target, cond)
        del USER_STATES[user.id]
        
        cond_txt = t("cond_above", cid) if cond == "ABOVE" else t("cond_below", cid)
        msg = t("alert_set", cid).format(asset=asset, cond=cond_txt, target=f"{target:,}")
        
        await update.message.reply_html(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back", cid), callback_data="alerts_menu")]]))
    except ValueError:
        await update.message.reply_text("⚠️ Error: Please enter a valid number.")

async def show_groups_menu(update, context):
    cid = update.effective_chat.id
    chats = get_user_chats(update.effective_user.id)
    kb = []
    for chat_id, title, _ in chats: kb.append([InlineKeyboardButton(title, callback_data=f"settings_{chat_id}")])
    kb.append([InlineKeyboardButton(t("btn_back", cid), callback_data="main_menu")])
    
    msg = t("group_menu_title", cid) if chats else t("no_groups", cid)
    if update.callback_query: await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def show_chat_settings(update, context, chat_id):
    user_cid = update.effective_chat.id 
    assets = get_chat_assets(chat_id)
    enabled = list(KNOWN_ASSETS.keys()) if assets == "ALL" else assets.split(",")
    
    chats = get_user_chats(update.effective_user.id)
    curr_int = 0
    title = "Group"
    for c in chats:
        if c[0] == chat_id:
            curr_int = c[2]
            title = c[1]
            break
            
    def txt(sec, lbl): return f"✅ {lbl}" if curr_int == sec else lbl
    
    lbl_sec = t("sec", user_cid)
    lbl_min = t("min", user_cid)
    lbl_off = t("off", user_cid)
    
    kb = [
        [InlineKeyboardButton(txt(30,f"30 {lbl_sec}"), callback_data=f"set_{chat_id}_30"), InlineKeyboardButton(txt(60,f"1 {lbl_min}"), callback_data=f"set_{chat_id}_60")],
        [InlineKeyboardButton(txt(300,f"5 {lbl_min}"), callback_data=f"set_{chat_id}_300"), InlineKeyboardButton(txt(0,lbl_off), callback_data=f"set_{chat_id}_0")]
    ]
    
    ab = []
    for c in KNOWN_ASSETS:
        s = "✅" if c in enabled else "❌"
        ab.append(InlineKeyboardButton(f"{s} {c}", callback_data=f"toggle_{chat_id}_{c}"))
    for i in range(0, len(ab), 2): kb.append(ab[i:i+2])
    
    kb.append([InlineKeyboardButton(t("btn_back", user_cid), callback_data="manage_groups")])
    
    msg = t("settings_title", user_cid).format(title=title)
    
    try:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except TelegramError as e:
        if "not modified" in str(e): await update.callback_query.answer("✅ Checked")

async def calc_command(update, context):
    cid = update.effective_chat.id
    if not await check_membership(update.effective_user.id, context):
        await send_join_request(update, context)
        return

    try:
        amt, asset = float(context.args[0]), context.args[1].upper()
        pr = LAST_PRICES.get(asset, {}).get("price_num")
        if pr: await update.message.reply_html(f"🧮 {amt} {asset} = <b>${(amt*pr):,.2f}</b>")
        else: await update.message.reply_text(t("price_na", cid))
    except: await update.message.reply_text(t("calc_error", cid))

# --- JOBS ---

async def fetch_job(context):
    prices = get_prices_from_file()
    if not prices: return
    
    for aid, uid, asset, target, cond in get_all_alerts():
        curr = prices.get(asset, {}).get("price_num")
        if not curr: continue
        
        trig = False
        if cond == "ABOVE" and curr >= target: trig = True
        elif cond == "BELOW" and curr <= target: trig = True
        
        if trig:
            cond_txt = t("cond_above", uid) if cond == "ABOVE" else t("cond_below", uid)
            msg = t("alert_set", uid).format(asset=asset, cond=cond_txt, target=f"{target:,}")
            msg = f"🚨 <b>ALARM:</b>\n" + msg + f"\nCurrent: {curr:,}"
            
            try: await context.bot.send_message(uid, msg, parse_mode="HTML"); delete_alert(aid)
            except: pass

async def post_prices_job(context):
    cid = context.job.chat_id
    assets = get_chat_assets(cid)
    msg = format_price_message(LAST_PRICES, cid, assets)
    
    if LAST_SENT_MESSAGES.get(cid) == msg: return
    try:
        await context.bot.send_message(cid, msg, parse_mode="HTML")
        LAST_SENT_MESSAGES[cid] = msg
    except TelegramError as e:
        if "kicked" in str(e) or "not found" in str(e):
            remove_chat(cid)
            context.job.schedule_removal()

async def chat_member_handler(update, context):
    m = update.my_chat_member
    c = m.chat
    if m.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        add_or_update_chat(c.id, m.from_user.id, c.title or "Group")
        set_chat_language(c.id, "fa")
    elif m.new_chat_member.status == ChatMemberStatus.LEFT:
        remove_chat(c.id)
        for j in context.job_queue.get_jobs_by_name(str(c.id)): j.schedule_removal()

def main():
    initialize_db()
    # استفاده از توکن خوانده شده از کانفیگ
    app = Application.builder().token(settings.BOT_TOKEN).build()
    
    app.job_queue.run_repeating(fetch_job, interval=3, first=1)
    
    scheduled = get_all_scheduled_chats() 
    for row in scheduled:
        cid, inv = row[0], row[1]
        if inv > 0: app.job_queue.run_repeating(post_prices_job, interval=inv, first=10, chat_id=cid, name=str(cid))
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(ChatMemberHandler(chat_member_handler))
    
    print("Bot Started (Bilingual & Secure)...")
    app.run_polling()

if __name__ == "__main__":
    main()
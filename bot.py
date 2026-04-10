




import os
import json
import gspread
from google.oauth2.service_account import Credentials

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8687358511:AAE6AgK-0-bh2HUPqIz9-3U31T_cG_Tf8l4"

# --- GOOGLE SHEETS ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1M-pnya58Wu37It4bsmRzzxBkcP5e-Zj4FX2lbyMZjio"
).worksheet("Основные")


# --- УМНОЕ ОПРЕДЕЛЕНИЕ КОЛОНОК (С ЗАЩИТОЙ) ---
def get_columns_map(header):
    col_map = {}

    for i, name in enumerate(header):
        key = str(name).strip().lower()

        if "модел" in key:
            col_map["model"] = i
        elif "размер" in key:
            col_map["size"] = i
        elif "цвет" in key:
            col_map["color"] = i
        elif "колич" in key:
            col_map["qty"] = i
        elif "склад" in key:
            col_map["warehouse"] = i
        elif "стел" in key:
            col_map["rack"] = i
        elif "полк" in key:
            col_map["shelf"] = i
        elif "короб" in key:
            col_map["box"] = i

    # --- ЗАЩИТА ---
    def safe(key):
        return col_map.get(key, None)

    return {
        "model": safe("model"),
        "size": safe("size"),
        "color": safe("color"),
        "qty": safe("qty"),
        "warehouse": safe("warehouse"),
        "rack": safe("rack"),
        "shelf": safe("shelf"),
        "box": safe("box"),
    }


# --- БЕЗОПАСНОЕ ЧТЕНИЕ ---
def get_val(row, index):
    try:
        if index is None:
            return "-"
        return row[index] if row[index] != "" else "-"
    except:
        return "-"


# --- КНОПКИ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Поиск товара"],
        ["📦 Все модели"]
    ], resize_keyboard=True)


# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 Складской бот",
        reply_markup=main_keyboard()
    )


# --- ПОКАЗ МОДЕЛЕЙ ---
async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = sheet.get_all_values()
    header = data[0]
    col = get_columns_map(header)

    models = sorted(set(
        get_val(row, col["model"])
        for row in data[1:]
    ))

    keyboard = [
        [InlineKeyboardButton(m, callback_data=f"model_{m}")]
        for m in models if m != "-"
    ]

    await update.message.reply_text(
        "Выберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard[:20])
    )


# --- ВЫБОР МОДЕЛИ ---
async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    model = query.data.split("_", 1)[1]
    context.user_data["model"] = model

    data = sheet.get_all_values()
    col = get_columns_map(data[0])

    sizes = sorted(set(
        get_val(row, col["size"])
        for row in data[1:]
        if get_val(row, col["model"]) == model
    ))

    keyboard = [[InlineKeyboardButton(s, callback_data=f"size_{s}")] for s in sizes]

    await query.edit_message_text(
        f"{model}\nВыберите размер:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- ВЫБОР РАЗМЕРА ---
async def select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    size = query.data.split("_", 1)[1]
    context.user_data["size"] = size
    model = context.user_data["model"]

    data = sheet.get_all_values()
    col = get_columns_map(data[0])

    colors = sorted(set(
        get_val(row, col["color"])
        for row in data[1:]
        if get_val(row, col["model"]) == model and get_val(row, col["size"]) == size
    ))

    keyboard = [[InlineKeyboardButton(c, callback_data=f"color_{c}")] for c in colors]

    await query.edit_message_text(
        f"{model} | {size}\nВыберите цвет:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- ФИНАЛ ---
async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    color = query.data.split("_", 1)[1]
    model = context.user_data["model"]
    size = context.user_data["size"]

    data = sheet.get_all_values()
    col = get_columns_map(data[0])

    for row in data[1:]:
        if (
            get_val(row, col["model"]) == model and
            get_val(row, col["size"]) == size and
            get_val(row, col["color"]) == color
        ):
            await query.edit_message_text(
                f"📦 {model} | {size} | {color}\n"
                f"📍 Склад: {get_val(row, col['warehouse'])}\n"
                f"🏗 Стеллаж: {get_val(row, col['rack'])}\n"
                f"📚 Полка: {get_val(row, col['shelf'])}\n"
                f"📦 Коробка: {get_val(row, col['box'])}\n"
                f"📊 Остаток: {get_val(row, col['qty'])}"
            )
            return

    await query.edit_message_text("❌ Не найдено")


# --- ПОИСК ---
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    words = text.split()

    data = sheet.get_all_values()
    col = get_columns_map(data[0])

    results = []

    for row in data[1:]:
        row_text = " ".join(str(x).lower() for x in row)

        if all(word in row_text for word in words):
            results.append(
                f"{get_val(row, col['model'])} | {get_val(row, col['size'])} | {get_val(row, col['color'])}\n"
                f"📍 {get_val(row, col['warehouse'])} | Ст:{get_val(row, col['rack'])} | П:{get_val(row, col['shelf'])} | К:{get_val(row, col['box'])}\n"
                f"📊 Остаток: {get_val(row, col['qty'])}"
            )

    if not results:
        await update.message.reply_text("❌ Ничего не найдено")
    else:
        await update.message.reply_text("\n\n".join(results[:5]))


# --- ОБРАБОТКА ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Поиск" in text:
        await update.message.reply_text("Введите запрос")
    elif "Все модели" in text:
        await show_models(update, context)
    else:
        await handle_search(update, context)


# --- MAIN ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

app.add_handler(CallbackQueryHandler(select_model, pattern="^model_"))
app.add_handler(CallbackQueryHandler(select_size, pattern="^size_"))
app.add_handler(CallbackQueryHandler(select_color, pattern="^color_"))

app.run_polling()


import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ====== НАСТРОЙКИ ======
TELEGRAM_TOKEN = "8687358511:AAEK_TXPOcLCO6Chk6eCcJB3uf4SestnXPM"
ADMIN_ID = 636437015  # вставь свой Telegram ID

SHEET_URL = "https://docs.google.com/spreadsheets/d/1M-pnya58Wu37It4bsmRzzxBkcP5e-Zj4FX2lbyMZjio/edit"
SHEET_NAME = "местоположение товаров"

# ====== GOOGLE ======
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

# ====== ВСПОМОГАТЕЛЬНОЕ ======
def get_index(headers, name):
    for i, h in enumerate(headers):
        if h.strip().lower() == name.lower():
            return i
    return None

def get_data():
    data = sheet.get_all_values()
    headers = data[0]
    rows = data[1:]
    return headers, rows

# ====== ПОИСК ======
def find_products(text):
    headers, rows = get_data()

    model_idx = get_index(headers, "Модель")
    size_idx = get_index(headers, "Размер")
    color_idx = get_index(headers, "Цвет")
    stock_idx = get_index(headers, "Количество")
    sklad_idx = get_index(headers, "Склад")
    st_idx = get_index(headers, "Стеллаж")
    shelf_idx = get_index(headers, "Полка")
    box_idx = get_index(headers, "Коробка")

    parts = text.upper().split()

    model = None
    size = None
    color = None

    for p in parts:
        if "-" in p:
            model = p
        elif p.isdigit():
            size = p
        else:
            color = p

    results = []

    for i, row in enumerate(rows):
        if model and row[model_idx].upper() != model:
            continue
        if size and row[size_idx] != size:
            continue
        if color and row[color_idx].upper() != color:
            continue

        results.append({
            "row_index": i + 2,
            "model": row[model_idx],
            "size": row[size_idx],
            "color": row[color_idx],
            "stock": row[stock_idx],
            "sklad": row[sklad_idx],
            "st": row[st_idx] if st_idx and row[st_idx] else "-",
            "shelf": row[shelf_idx] if shelf_idx and row[shelf_idx] else "-",
            "box": row[box_idx] if box_idx and row[box_idx] else "-"
        })

    return model, results

# ====== КНОПКИ ======
def create_buttons(products):
    keyboard = []
    for p in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{p['size']} ({p['stock']})",
                callback_data=f"{p['row_index']}"
            )
        ])
    return InlineKeyboardMarkup(keyboard)

# ====== ОБРАБОТКА СООБЩЕНИЙ ======
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    row_index = int(query.data)

    headers, rows = get_data()

    # получаем индексы колонок
    model_idx = get_index(headers, "Модель")
    size_idx = get_index(headers, "Размер")
    color_idx = get_index(headers, "Цвет")
    stock_idx = get_index(headers, "Количество")
    sklad_idx = get_index(headers, "Склад")
    st_idx = get_index(headers, "Стеллаж")
    shelf_idx = get_index(headers, "Полка")
    box_idx = get_index(headers, "Коробка")

    row = rows[row_index - 2]

    response = (
        f"{row[model_idx]} | {row[size_idx]} | {row[color_idx]}\n"
        f"Склад: {row[sklad_idx]}\n"
        f"Остаток: {row[stock_idx]}\n"
        f"📦 Стеллаж: {row[st_idx] if st_idx is not None else '-'} | "
        f"Полка: {row[shelf_idx] if shelf_idx is not None else '-'} | "
        f"Коробка: {row[box_idx] if box_idx is not None else '-'}"
    )

    await query.message.reply_text(response)

# ====== ОБРАБОТКА КНОПОК ======
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    row_index = int(query.data)

    headers, rows = get_data()

    stock_idx = get_index(headers, "Количество")

    row = rows[row_index - 2]

    response = (
        f"{row[0]} | {row[1]} | {row[2]}\n"
        f"Склад: {row[4]}\n"
        f"Остаток: {row[3]}"
    )

    await query.message.reply_text(response)

# ====== СПИСАНИЕ (только админ) ======
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    text = update.message.text.strip()

    if text.startswith("-"):
        model, products = find_products(text[1:].strip())

        if products:
            p = products[0]
            stock_idx = get_index(sheet.row_values(1), "Количество")

            current = int(sheet.cell(p["row_index"], stock_idx + 1).value)
            sheet.update_cell(p["row_index"], stock_idx + 1, current - 1)

            await update.message.reply_text("Списано ✅")

# ====== ЗАПУСК ======
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin))

print("Бот запущен...")
app.run_polling()

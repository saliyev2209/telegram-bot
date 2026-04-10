
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ==== ВСТАВЬТЕ СВОЙ ТОКЕН ====
TELEGRAM_TOKEN = "8687358511:AAEK_TXPOcLCO6Chk6eCcJB3uf4SestnXPM"

# ==== ССЫЛКА НА GOOGLE SHEET ====
SHEET_URL = "https://docs.google.com/spreadsheets/d/1M-pnya58Wu37It4bsmRzzxBkcP5e-Zj4FX2lbyMZjio/edit?usp=sharing"

SHEET_NAME = "местоположение товаров"

# ==== GOOGLE SHEETS ====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# берем credentials из Railway Variables
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)
# FINDING =====
def find_products(text):
    data = sheet.get_all_values()

    headers = data[0]
    rows = data[1:]

    def get_index(headers, name):
        for i, h in enumerate(headers):
            if h.strip().lower() == name.lower():
                return i
        return None

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

    for row in rows:
        if model and row[model_idx].upper() != model:
            continue
        if size and row[size_idx] != size:
            continue
        if color and row[color_idx].upper() != color:
            continue

        results.append({
            "size": row[size_idx],
            "color": row[color_idx],
            "stock": row[stock_idx],
            "sklad": row[sklad_idx]
            "st": row[st_idx] if st_idx is not None and row[st_idx] else "-",
    "shelf": row[shelf_idx] if shelf_idx is not None and row[shelf_idx] else "-",
    "box": row[box_idx] if box_idx is not None and row[box_idx] else "-"
        })

    return model, results

# ==== ОБРАБОТКА СООБЩЕНИЙ ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    model, products = find_products(text)

    if products:
        response = f"{model} найдено:\n\n"

        for p in products:
        response += (
    f"{p['size']} | {p['color']} | Остаток: {p['stock']} | {p['sklad']}\n"
    f"📦 Стеллаж: {p['st']} | Полка: {p['shelf']} | Коробка: {p['box']}\n\n"
)

    else:
        response = "Товар не найден"

    await update.message.reply_text(response)

# ==== ЗАПУСК ====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен...")
app.run_polling()

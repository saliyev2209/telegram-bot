
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

def find_product(code):
    data = sheet.get_all_values()  # вместо get_all_records()

    headers = data[0]  # первая строка (названия колонок)
    rows = data[1:]    # все данные

    # находим индексы колонок вручную
    model_idx = headers.index("Модель")
    size_idx = headers.index("Размер")
    color_idx = headers.index("Цвет")
    stock_idx = headers.index("Количество")
    sklad_idx = headers.index("Склад")

    for row in rows:
        if row[model_idx].lower() == code.lower():
            return {
                "model": row[model_idx],
                "size": row[size_idx],
                "color": row[color_idx],
                "sklad": row[sklad_idx],
                "stock": row[stock_idx]
            }

    return None

# ==== ОБРАБОТКА СООБЩЕНИЙ ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    product = find_product(text)

    if product:
        response = (
            f"{product['model']} | {product['size']} | {product['color']}\n"
            f"Склад: {product['sklad']}\n"
            f"Остаток: {product['stock']}"
        )
    else:
        response = "Товар не найден"

    await update.message.reply_text(response)

# ==== ЗАПУСК ====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен...")
app.run_polling()

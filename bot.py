


import os
import json
import gspread
from google.oauth2.service_account import Credentials

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)


TOKEN = "8687358511:AAFwehDnQYIkT-lLKIsXTvz6MrhsBP7VfLQ"

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


# --- КНОПКИ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Поиск товара"]
    ], resize_keyboard=True)


# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 Складской бот\n\nНажмите кнопку или введите запрос:",
        reply_markup=main_keyboard()
    )


# --- ПОИСК ---
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    words = text.split()

    data = [row for row in sheet.get_all_values() if any(row)]

    results = []

    for row in data[1:]:
        # объединяем всю строку
        row_text = " ".join([str(cell).lower() for cell in row])

        # проверяем ВСЕ слова (как в Google)
        if all(word in row_text for word in words):
            results.append(
                f"{row[0]} | {row[1]} | {row[2]}\n📦 {row[5]}\n📊 Остаток: {row[7]}"
            )

    if not results:
        await update.message.reply_text("❌ Ничего не найдено")
    else:
        await update.message.reply_text("\n\n".join(results[:5]))


# --- ОБРАБОТКА ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Поиск" in text:
        await update.message.reply_text("Введите запрос (например: MK-68 104 BLACK)")
    else:
        await handle_search(update, context)


# --- MAIN ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

app.run_polling()

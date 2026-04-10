
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
# --- ГЛАВНОЕ МЕНЮ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Поиск товара"],
        ["📦 Все модели"]
    ], resize_keyboard=True)
# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 Складской бот\n\nВыберите действие:",
        reply_markup=main_keyboard()
    )
# --- ВСЕ МОДЕЛИ ---
async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = [row for row in sheet.get_all_values() if any(row)]
    models = sorted(set(row[0] for row in data[1:] if row[0]))
    keyboard = []
    for m in models[:20]:
        keyboard.append([InlineKeyboardButton(m, callback_data=f"model_{m}")])
    await update.message.reply_text(
        "Выберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- ВЫБОР МОДЕЛИ ---
async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    model = query.data.split("_", 1)[1]
    context.user_data["model"] = model
    data = sheet.get_all_values()
    sizes = sorted(set(
        str(row[1]) for row in data[1:]
        if row[0] == model
    ))
    keyboard = []
    for s in sizes:
        keyboard.append([InlineKeyboardButton(s, callback_data=f"size_{s}")])
    await query.edit_message_text(
        f"Модель: {model}\nВыберите размер:",
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
    colors = sorted(set(
        row[2] for row in data[1:]
        if row[0] == model and str(row[1]) == size
    ))
    keyboard = []
    for c in colors:
        keyboard.append([InlineKeyboardButton(c, callback_data=f"color_{c}")])
    await query.edit_message_text(
        f"{model} | {size}\nВыберите цвет:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
# --- ФИНАЛ (ПОКАЗ ТОВАРА) ---
async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    color = query.data.split("_", 1)[1]
    model = context.user_data["model"]
    size = context.user_data["size"]
    data = sheet.get_all_values()
    for row in data[1:]:
        if (
            row[0] == model and
            str(row[1]) == size and
            row[2] == color
        ):
            await query.edit_message_text(
                f"📦 {model} | {size} | {color}\n"
                f"📍 Склад: {row[4]}\n"
                f"🏗 Стеллаж: {row[5]}\n"
                f"📚 Полка: {row[6]}\n"
                f"📦 Коробка: {row[7]}\n"
                f"📊 Остаток: {row[3]}"
            )
            return
    await query.edit_message_text("❌ Не найдено")
# --- ПОИСК (как Google Sheets) ---
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    words = text.split()
    data = [row for row in sheet.get_all_values() if any(row)]
    results = []
    for row in data[1:]:
        row_text = " ".join([str(cell).lower() for cell in row])
        if all(word in row_text for word in words):
            results.append(
                f"{row[0]} | {row[1]} | {row[2]}\n"
                f"📍 {row[4]} | Ст:{row[5]} | П:{row[6]} | К:{row[7]}\n"
                f"📊 Остаток: {row[3]}"
            )
    if not results:
        await update.message.reply_text("❌ Ничего не найдено")
    else:
        await update.message.reply_text("\n\n".join(results[:5]))
# --- ОБРАБОТКА КНОПОК ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Поиск" in text:
        await update.message.reply_text("Введите запрос (например: MK-68 104 BLACK)")
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

import os
import json
import gspread
from google.oauth2.service_account import Credentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

client = gspread.authorize(creds)

sheet_main = client.open_by_url("https://docs.google.com/spreadsheets/d/1M-pnya58Wu37It4bsmRzzxBkcP5e-Zj4FX2lbyMZjio").worksheet("Основные")
sheet_sales = client.open_by_url("https://docs.google.com/spreadsheets/d/1M-pnya58Wu37It4bsmRzzxBkcP5e-Zj4FX2lbyMZjio").worksheet("Продажи")



TOKEN = "8687358511:AAFwehDnQYIkT-lLKIsXTvz6MrhsBP7VfLQ"

# --- GOOGLE SHEETS ---



# --- КНОПКИ ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Поиск товара"],
        ["📦 Списание"]
    ], resize_keyboard=True)

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 Складской бот\n\nВыберите действие:",
        reply_markup=main_keyboard()
    )

# --- ПОИСК ---
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите запрос (например: MK-68 104 BLACK)")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    words = text.split()

    data = [row for row in sheet_main.get_all_values() if any(row)]

    results = []

    for i, row in enumerate(data[1:], start=2):
        row_text = " ".join([str(cell).lower() for cell in row])

        if all(word in row_text for word in words):
            results.append((i, row))

    if not results:
        await update.message.reply_text("❌ Ничего не найдено")
        return

    keyboard = []
    for idx, row in results[:5]:
        keyboard.append([
            InlineKeyboardButton(
                f"{row[0]} {row[1]} {row[2]}",
                callback_data=f"select_{idx}"
            )
        ])

    await update.message.reply_text(
        "Выберите товар:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- ВЫБОР ТОВАРА ---
async def select_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    row_index = int(query.data.split("_")[1])

    data = sheet_main.get_all_values()
    row = data[row_index - 1]

    context.user_data["selected_row"] = row_index

    keyboard = [
        [InlineKeyboardButton("➖ Списать 1", callback_data="sell_1")],
        [InlineKeyboardButton("➖ Списать 2", callback_data="sell_2")],
        [InlineKeyboardButton("➖ Списать 5", callback_data="sell_5")]
    ]

    await query.edit_message_text(
        f"{row[0]} | {row[1]} | {row[2]}\n📦 {row[5]}\n📊 Остаток: {row[7]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- ПОДТВЕРЖДЕНИЕ ---
async def confirm_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    qty = int(query.data.split("_")[1])
    row_index = context.user_data.get("selected_row")

    context.user_data["sell_qty"] = qty

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]

    await query.edit_message_text(
        f"Подтвердить списание {qty} шт?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- СПИСАНИЕ ---
async def do_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    row_index = context.user_data.get("selected_row")
    qty = context.user_data.get("sell_qty")

    data = sheet_main.get_all_values()
    row = data[row_index - 1]

    with lock:
        sold = int(row[6])
        stock = int(row[7])

        if stock < qty:
            await query.edit_message_text("❌ Недостаточно товара")
            return

        new_sold = sold + qty
        new_stock = stock - qty

        sheet_main.batch_update([
            {"range": f"G{row_index}", "values": [[new_sold]]},
            {"range": f"H{row_index}", "values": [[new_stock]]}
        ])

        sheet_sales.append_row([
            row[0], row[1], row[2], qty, row[5]
        ])

    await query.edit_message_text(
        f"✅ Списано {qty}\nОстаток: {new_stock}"
    )

# --- ОТМЕНА ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Отменено")

# --- ОБРАБОТЧИК ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Поиск" in text:
        await search(update, context)
    elif "Списание" in text:
        await search(update, context)
    else:
        await handle_search(update, context)

# --- MAIN ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

app.add_handler(CallbackQueryHandler(select_item, pattern="^select_"))
app.add_handler(CallbackQueryHandler(confirm_sell, pattern="^sell_"))
app.add_handler(CallbackQueryHandler(do_sell, pattern="^confirm$"))
app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))

app.run_polling()

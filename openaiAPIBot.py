import os
import openai
import yfinance as yf
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY= os.getenv("")
openai.api_key = OPENAI_API_KEY

def create_prompt(user_input):
    return f"User Query: {user_input}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    try:
        prompt = create_prompt(user_msg)

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        suggestion = response["choices"][0]["message"]["content"]

        lines = suggestion.split('\n')
        ticker_line = next((line for line in lines if "Ticker" in line), None)
        if ticker_line:
            symbol = ticker_line.split(":")[-1].strip() + ".NS"
            try:
                data = yf.Ticker(symbol).info
                current_price = data.get("currentPrice", "N/A")
                name = data.get("shortName", symbol)
                suggestion += f"\n\n📊 Live price for {name}: ₹{current_price}"
            except Exception:
                suggestion += "\n⚠️ Could not fetch real-time price."

        await update.message.reply_text(suggestion)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 Welcome! Ask me for an Indian stock suggestion.\nExample: 'Suggest a stock for short-term gain'"
    )

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

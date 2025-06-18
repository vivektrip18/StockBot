import logging
import re
import yfinance as yf
from telegram import Update
import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if a word is fully uppercase and try to resolve it to a valid stock ticker
def resolve_ticker(word: str) -> str | None:
    if not word.isupper():
        return None

    suffixes = ["", ".NS", ".BO"]
    for suffix in suffixes:
        full = word + suffix
        try:
            stock = yf.Ticker(full)
            hist = stock.history(period="5d")
            if not hist.empty:
                return full
        except Exception:
            continue
    return None

def generate_trading_suggestion(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="60d")

        if hist.empty or len(hist) < 20:
            return "⚠️ Not enough data to generate a trading strategy."

        # Prices
        current = hist['Close'].iloc[-1]
        old = hist['Close'].iloc[-5]
        change = current - old
        pct_change = (change / old) * 100

        # Volatility
        high = hist['High'][-5:].max()
        low = hist['Low'][-5:].min()
        volatility = (high - low) / current * 100 # This variable is not used in the current logic, but kept for potential future use.

        # Moving Averages
        sma5 = hist['Close'].rolling(window=5).mean().iloc[-1]
        sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]

        # Strategy logic
        if -5 <= pct_change <= -2 and current > sma50:
            action = "🟢 Suggestion: **Buy the dip** (strong stock, small correction)."
        elif pct_change < -5:
            action = "🔽 Suggestion: **High-risk Buy** — sharp dip, possible rebound."
        elif pct_change > 8:
            action = "🔼 Suggestion: **Profit booking** — strong rally."
        elif current > sma5 and current > sma50:
            action = "📈 Suggestion: **Hold** — price above trend lines."
        else:
            action = "📉 Suggestion: **Wait** — weak short-term signal."

        #Targets
        stop_loss = current * 0.95
        target = current * 1.07
        hold_days = "3–10 days" if "Buy" in action else "2–5 days"

        return (
            f"{action}\n"
            f"🎯 Target Price: ₹{target:.2f}\n"
            f"🛑 Stop Loss: ₹{stop_loss:.2f}\n"
            f"📆 Suggested Holding: {hold_days}"
        )

    except Exception as e:
        logger.error(f"Error in strategy for {ticker}: {e}")
        return "❌ Could not generate strategy."


# Fetch stock data
def fetch_stock_info(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        info = stock.info

        latest_price = hist['Close'].iloc[-1]
        change = latest_price - hist['Close'].iloc[-2]
        pct_change = (change / hist['Close'].iloc[-2]) * 100

        return (
            f"📈 {ticker}\n"
            f"Current Price: ₹{latest_price:.2f}\n"
            f"Change (1d): {change:+.2f} ({pct_change:+.2f}%)\n"
            f"Sector: {info.get('sector', 'N/A')}\n"
            f"Market Cap: ₹{info.get('marketCap', 'N/A'):,}\n"
            f"PE Ratio: {info.get('trailingPE', 'N/A')}\n"
        )
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return f"❌ Error fetching data for {ticker}"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send UPPERCASE stock symbols like TCS, TSLA, RELIANCE in your message.")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    words = re.findall(r'\b[A-Z0-9]{2,10}\b', text)  #only extract uppercase words

    found_stocks = []
    seen = set()

    for word in words:
        if word in seen:
            continue
        seen.add(word)
        ticker = resolve_ticker(word)
        if ticker:
            found_stocks.append(ticker)

    if found_stocks:
        await update.message.reply_text(f"✅ Found {len(found_stocks)} stock(s): {', '.join(found_stocks)}\nFetching data and strategy...")
        for ticker in found_stocks:
            info = fetch_stock_info(ticker)
            strategy = generate_trading_suggestion(ticker)
            # Combine info and strategy into a single message
            await update.message.reply_text(info + "\n\n📊 " + strategy)
    else:
        await update.message.reply_text("❌ No valid UPPERCASE stock symbols found in your message.")


# Start the bot
if __name__ == "__main__":
    TOKEN = "7658738085:AAE-B0sSQpxJ1LYtyjjlrqwSdyvOO1ewJZY" 

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
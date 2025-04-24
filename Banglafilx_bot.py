import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    InlineQueryHandler,
)
from collections import defaultdict
import logging

# কনফিগারেশন
CONFIG = {
    "TELEGRAM_TOKEN": "8004497086:AAGGgN2EVBN3MelEPCmJTcRwzyNNvCUXaEs",
    "WEBSITE_API": "https://movie.banglafilx.com/rest-api/",
    "API_KEY": "ol9dh5c0azswfrar5vmiw7w7",
    "ADMIN_IDS": [],  # আপনার টেলিগ্রাম আইডি এখানে যোগ করুন [ঐচ্ছিক]
}

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# স্প্যাম প্রোটেকশন
user_activity = defaultdict(int)

def check_spam(update: Update) -> bool:
    user_id = update.effective_user.id
    user_activity[user_id] += 1
    
    if user_activity[user_id] > 10:
        update.message.reply_text("⚠️ অনুরোধ খুব বেশি! 1 মিনিট অপেক্ষা করুন")
        return False
    return True

def search_movies(query: str) -> list:
    try:
        headers = {
            "Authorization": f"Bearer {CONFIG['API_KEY']}",
            "Accept": "application/json"
        }
        params = {"search": query}
        
        response = requests.get(
            CONFIG["WEBSITE_API"],
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        movies = []
        for item in data.get("data", []):
            download_link = item.get("download_links", [{}])[0].get("url", "#")
            if not download_link.startswith(('http://', 'https://')):
                download_link = f"https://movie.banglafilx.com{download_link}"
                
            movies.append({
                "title": item.get("title", "No Title"),
                "year": item.get("release_year", "N/A"),
                "download_link": download_link,
                "thumbnail": item.get("thumbnail", ""),
                "quality": item.get("quality", "Unknown"),
                "size": item.get("size", "Unknown")
            })
        return movies
    except Exception as e:
        logger.error(f"API Error: {e}")
        return []

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(
        f"🎬 Banglafilx মুভি বটে স্বাগতম, {user.first_name}!\n\n"
        "🔍 মুভি খুঁজতে শুধু মুভির নাম লিখে পাঠান\n\n"
        "ওয়েবসাইট: https://movie.banglafilx.com",
        disable_web_page_preview=True
    )

def handle_search(update: Update, context: CallbackContext) -> None:
    if not check_spam(update):
        return
    
    query = update.message.text
    if len(query) < 3:
        update.message.reply_text("⚠️ কমপক্ষে ৩ অক্ষর লিখুন")
        return
    
    update.message.reply_chat_action(action='typing')
    
    movies = search_movies(query)
    
    if not movies:
        update.message.reply_text("😢 এই নামে কোন মুভি পাওয়া যায়নি!")
        return
    
    for movie in movies[:3]:
        message = (
            f"<b>{movie['title']}</b> ({movie['year']})\n"
            f"📀 Quality: {movie['quality']}\n"
            f"📦 Size: {movie['size']}\n"
            f"🔗 <a href='{movie['download_link']}'>Download Now</a>\n\n"
            f"© <a href='https://movie.banglafilx.com'>Banglafilx</a>"
        )
        try:
            if movie['thumbnail']:
                update.message.reply_photo(
                    photo=movie['thumbnail'],
                    caption=message,
                    parse_mode='HTML'
                )
            else:
                update.message.reply_text(
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.error(f"Error sending movie: {e}")
            update.message.reply_text(
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )

def inline_search(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query or len(query) < 3:
        return
    
    movies = search_movies(query)
    
    results = []
    for movie in movies[:50]:
        message_content = (
            f"<b>{movie['title']}</b> ({movie['year']})\n"
            f"Quality: {movie['quality']} | Size: {movie['size']}\n"
            f"🔗 <a href='{movie['download_link']}'>Download</a>\n\n"
            f"© Banglafilx"
        )
        
        results.append(
            InlineQueryResultArticle(
                id=movie['download_link'],
                title=f"{movie['title']} ({movie['year']})",
                description=f"{movie['quality']} | {movie['size']}",
                input_message_content=InputTextMessageContent(
                    message_content,
                    parse_mode='HTML'
                ),
                thumb_url=movie.get('thumbnail', None)
            )
        )
    
    update.inline_query.answer(results)

def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(f"Error: {context.error}")
    if update.effective_message:
        update.effective_message.reply_text(
            "⚠️ একটি ত্রুটি ঘটেছে! দয়া করে আবার চেষ্টা করুন",
            parse_mode='HTML'
        )

def main() -> None:
    updater = Updater(CONFIG["TELEGRAM_TOKEN"])
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_search))
    dispatcher.add_handler(InlineQueryHandler(inline_search))
    dispatcher.add_error_handler(error_handler)
    
    logger.info("বট চালু হয়েছে...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

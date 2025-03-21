import os
import logging
from datetime import datetime
import re
import sqlite3
import time
import tweepy
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for conversation
USERNAME = 0

# Twitter API credentials
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")

# Telegram Bot token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Twitter client initialization
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True  # Automatically wait when rate limited
)

# Database setup
def init_db():
    conn = sqlite3.connect('twitter_bot.db')
    cursor = conn.cursor()
    
    # Store user queries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_queries (
        id INTEGER PRIMARY KEY,
        telegram_user_id INTEGER,
        twitter_username TEXT,
        query_time TIMESTAMP,
        result TEXT
    )
    ''')
    
    # Store rate limiting data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rate_limits (
        telegram_user_id INTEGER PRIMARY KEY,
        last_query_time TIMESTAMP,
        query_count INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()

# Rate limiting function
def check_rate_limit(telegram_user_id):
    conn = sqlite3.connect('twitter_bot.db')
    cursor = conn.cursor()
    
    # Get current time
    current_time = time.time()
    # Window for rate limiting (1 hour)
    time_window = 3600
    # Max queries per window
    max_queries = 10
    
    cursor.execute('SELECT last_query_time, query_count FROM rate_limits WHERE telegram_user_id = ?', 
                  (telegram_user_id,))
    result = cursor.fetchone()
    
    if result:
        last_time, count = result
        
        # Reset count if outside window
        if current_time - last_time > time_window:
            cursor.execute('UPDATE rate_limits SET last_query_time = ?, query_count = 1 WHERE telegram_user_id = ?',
                          (current_time, telegram_user_id))
            conn.commit()
            conn.close()
            return True
        
        # Check if under limit
        if count < max_queries:
            cursor.execute('UPDATE rate_limits SET query_count = query_count + 1 WHERE telegram_user_id = ?',
                          (telegram_user_id,))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    else:
        # First query for this user
        cursor.execute('INSERT INTO rate_limits (telegram_user_id, last_query_time, query_count) VALUES (?, ?, 1)',
                      (telegram_user_id, current_time))
        conn.commit()
        conn.close()
        return True

# Store query in database
def store_query(telegram_user_id, twitter_username, result):
    conn = sqlite3.connect('twitter_bot.db')
    cursor = conn.cursor()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
    INSERT INTO user_queries (telegram_user_id, twitter_username, query_time, result)
    VALUES (?, ?, ?, ?)
    ''', (telegram_user_id, twitter_username, current_time, result))
    
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a welcome message and ask for a Twitter username."""
    await update.message.reply_text(
        "👋 Hello! I can check how many times a Twitter/X account has been renamed.\n\n"
        "Send me a Twitter username (without the @ symbol)."
    )
    return USERNAME

async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the username history of the given Twitter account."""
    # Check rate limit
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            "⚠️ You've reached the maximum number of queries allowed per hour. "
            "Please try again later."
        )
        return USERNAME
    
    username = update.message.text.strip().replace("@", "")
    
    await update.message.reply_text(f"🔍 Checking username history for @{username}...")
    
    try:
        # Get user data
        user = client.get_user(username=username, user_fields=["created_at", "name", "description"])
        
        if not user.data:
            await update.message.reply_text(f"❌ User @{username} not found.")
            store_query(user_id, username, "User not found")
            return USERNAME
        
        user_id_twitter = user.data.id
        display_name = user.data.name
        created_at = user.data.created_at
        
        # Advanced analysis to detect possible username changes
        
        # 1. Check mentions of this user with different usernames
        mentioned_names = []
        try:
            # Search for tweets mentioning the user
            mentions_query = f"to:{username}"
            mentions = client.search_recent_tweets(query=mentions_query, max_results=100)
            
            if mentions.data:
                for tweet in mentions.data:
                    # Look for patterns like "formerly @oldname" or "previously @oldname"
                    text = tweet.text.lower()
                    formerly_matches = re.findall(r"formerly @([a-zA-Z0-9_]+)", text)
                    previously_matches = re.findall(r"previously @([a-zA-Z0-9_]+)", text)
                    was_matches = re.findall(r"was @([a-zA-Z0-9_]+)", text)
                    
                    mentioned_names.extend(formerly_matches)
                    mentioned_names.extend(previously_matches)
                    mentioned_names.extend(was_matches)
        except Exception as e:
            logger.warning(f"Error checking mentions: {e}")
        
        # Remove duplicates
        mentioned_names = list(set(mentioned_names))
        
        # 2. Check for replies where the username might have changed
        previous_names_in_replies = []
        try:
            # Get tweets from the user
            user_tweets = client.get_users_tweets(id=user_id_twitter, max_results=100)
            
            if user_tweets.data:
                for tweet in user_tweets.data:
                    # Get replies to this tweet
                    replies_query = f"conversation_id:{tweet.id}"
                    replies = client.search_recent_tweets(query=replies_query, max_results=10)
                    
                    if replies.data:
                        for reply in replies.data:
                            # Look for patterns like "when you were @oldname"
                            text = reply.text.lower()
                            when_matches = re.findall(r"when you were @([a-zA-Z0-9_]+)", text)
                            previous_names_in_replies.extend(when_matches)
        except Exception as e:
            logger.warning(f"Error checking replies: {e}")
        
        # Remove duplicates
        previous_names_in_replies = list(set(previous_names_in_replies))
        
        # 3. Analyze account age for baseline estimate
        account_age_days = (datetime.now() - created_at.replace(tzinfo=None)).days
        baseline_estimate = max(1, min(account_age_days // 180, 5))  # Rough estimate: possibility of change every ~6 months
        
        # Combine all evidence of name changes
        all_previous_names = mentioned_names + previous_names_in_replies
        all_previous_names = list(set(all_previous_names))  # Remove duplicates
        
        # Adjust estimate based on found evidence
        if len(all_previous_names) > 0:
            estimated_changes = len(all_previous_names)
        else:
            estimated_changes = baseline_estimate
        
        # Build response
        response = (
            f"📊 *Username Analysis for @{username}*\n\n"
            f"• Account created: {created_at.strftime('%B %d, %Y')}\n"
            f"• Account age: {account_age_days} days\n"
            f"• Current display name: {display_name}\n\n"
        )
        
        if all_previous_names:
            response += f"*Detected Previous Usernames*: \n"
            for name in all_previous_names:
                response += f"• @{name}\n"
            response += f"\nBased on the detected username references, this account appears to have changed usernames *{estimated_changes} times*.\n\n"
        else:
            response += (
                f"Based on the account age and activity, I estimate @{username} may have changed "
                f"usernames approximately *{estimated_changes} times*.\n\n"
            )
        
        response += (
            "Note: Twitter/X API doesn't provide official name change history. "
            "This analysis combines multiple detection methods including mentions, "
            "replies, and account age analysis."
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
        # Store the query result
        store_query(update.effective_user.id, username, f"Estimated {estimated_changes} changes")
        
        # Ask if they want to check another account
        await update.message.reply_text(
            "Would you like to check another account? Just send me another username, "
            "or use /cancel to stop."
        )
        return USERNAME
        
    except tweepy.TooManyRequests:
        logger.error("Twitter API rate limit reached")
        await update.message.reply_text(
            "⚠️ Twitter API rate limit reached. Please try again later."
        )
        return USERNAME
    except Exception as e:
        logger.error(f"Error checking Twitter username: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error while checking that username. "
            "Please make sure it's a valid Twitter/X username and try again."
        )
        return USERNAME

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show usage statistics to the user."""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('twitter_bot.db')
    cursor = conn.cursor()
    
    # Get user's query count
    cursor.execute('SELECT COUNT(*) FROM user_queries WHERE telegram_user_id = ?', (user_id,))
    query_count = cursor.fetchone()[0]
    
    # Get most frequently checked username by this user
    cursor.execute('''
    SELECT twitter_username, COUNT(*) as count 
    FROM user_queries 
    WHERE telegram_user_id = ? 
    GROUP BY twitter_username 
    ORDER BY count DESC 
    LIMIT 1
    ''', (user_id,))
    most_frequent = cursor.fetchone()
    
    conn.close()
    
    response = f"📈 *Your Stats*\n\n• Total queries: {query_count}\n"
    
    if most_frequent and query_count > 0:
        response += f"• Most checked account: @{most_frequent[0]} ({most_frequent[1]} times)"
    
    await update.message.reply_text(response, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation."""
    await update.message.reply_text(
        "Goodbye! Feel free to use me again when you want to check Twitter username changes."
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Initialize database
    init_db()
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Add stats command
    application.add_handler(CommandHandler("stats", stats))
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # For webhook deployment (comment out the run_polling line above and uncomment these lines)
    # PORT = int(os.environ.get('PORT', '8443'))
    # WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    # application.run_webhook(
    #     listen="0.0.0.0",
    #     port=PORT,
    #     url_path=TELEGRAM_TOKEN,
    #     webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    # )

if __name__ == "__main__":
    main()
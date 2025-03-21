# Twitter Username Change Tracker Bot

A Telegram bot that checks how many times a Twitter/X account has changed its username. The bot uses multiple detection methods to provide the most accurate estimates possible.

## Features

- **Username Change Detection**: Analyzes Twitter data to estimate how many times an account has changed its username
- **Multiple Detection Methods**:
  - Mentions analysis (e.g., "formerly @oldname")
  - Replies analysis (references to previous usernames)
  - Account age-based heuristics
- **User-Friendly Interface**: Simple conversational flow in Telegram
- **Production-Ready**:
  - Database storage for tracking user queries
  - Rate limiting to prevent API abuse
  - Error handling for API limits
  - Support for webhook deployment

## Prerequisites

- Python 3.8+
- Twitter/X Developer Account with API v2 access
- Telegram Bot token (obtained from BotFather)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/twitter-rename-checker-bot.git
   cd twitter-rename-checker-bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install python-telegram-bot tweepy
   ```

4. **Set up environment variables**

   Create a `.env` file in the root directory with the following variables:
   ```
   # Twitter API credentials
   TWITTER_API_KEY=your_twitter_api_key
   TWITTER_API_SECRET=your_twitter_api_secret
   TWITTER_ACCESS_TOKEN=your_twitter_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   
   # Telegram Bot token
   TELEGRAM_TOKEN=your_telegram_bot_token
   
   # For webhook deployment (optional)
   PORT=8443
   WEBHOOK_URL=https://your-app-url.com
   ```

   Or set them directly in your environment:
   ```bash
   export TWITTER_API_KEY=your_twitter_api_key
   export TWITTER_API_SECRET=your_twitter_api_secret
   # ... etc
   ```

## Running the Bot

### Local Development (Polling)

```bash
python bot.py
```

The bot will start and listen for messages using the polling method.

### Production Deployment (Webhook)

1. Uncomment the webhook section in `main()` function and comment out the polling line.
2. Make sure your `WEBHOOK_URL` environment variable is set.
3. Deploy to your server or platform (e.g., Heroku, AWS, etc.)
4. Run the bot:
   ```bash
   python bot.py
   ```

## Getting Twitter API Credentials

1. Apply for a Twitter Developer Account: https://developer.twitter.com/en/apply-for-access
2. Create a Project and App in the Twitter Developer Portal
3. Generate the required keys and tokens:
   - API Key and Secret (Consumer Keys)
   - Access Token and Secret
   - Bearer Token

## Getting a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the instructions to name your bot
4. BotFather will provide a token - save this as your `TELEGRAM_TOKEN`

## Usage

### Commands

- `/start` - Start the bot and begin the conversation
- `/cancel` - End the current conversation
- `/stats` - See your usage statistics

### How to Use

1. Start a chat with your bot on Telegram
2. Send the `/start` command
3. Enter a Twitter/X username (without the @ symbol)
4. The bot will analyze the account and estimate how many times the username has changed
5. You can continue checking other usernames or use `/cancel` to end the conversation

## Limitations

- The Twitter API doesn't provide direct access to username change history
- The bot uses approximation methods that may not be 100% accurate
- The Twitter API has rate limits that may restrict the number of checks possible

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# DEXSCREENER SNIPER BOT

The DexScreener Sniper Bot is a tool designed to automate the trading of tokens on [dexscreener](https://dexscreener.com/) website.

It aims to provide users with a competitive edge by executing trades faster than manual methods.

## Features

- **Automated Trading**: Automatically buy tokens using [ToxiBot](https://toxi-sol.gitbook.io/toxi).
- **Configurable Settings**: Customize the bot's behavior to suit your trading strategy.
- **Verify rugcheck**: Use [rugcheck](https://rugcheck.xyz/) to prevent buying high probability rugcheck tokens.
- **Detect fake volule**: Automatically detect fake volume.
- **Blacklist**: Prevent buying blacklisted tokens or dev addresses.
- **Save mecanism**: Use SQLite3 to save traded tokens.
- **Telegram reports**: Use Telegram to send every run a final report about the bought or blacklisted tokens.


## Buy strategies

### Pumped

The bot will buy tokens that have meet all the requirements and have pumped in the last 24h.

### Tier 1

Tokens that meet the requirements, with high volume and liquidity are considered as "Tier 1", they will be bought.


## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/bloodbee/dexscreener-sniper-bot.git
    ```
2. Navigate to the project directory:
    ```bash
    cd dexscreener-sniper-bot
    ```
3. Activate a virtual environment and install dependencies:
    ```bash
    pip install
    ```

## Usage

1. Go to the Toxi Bot telegram channel: https://t.me/toxi_solana_bot

2. Follow the instructions to generate a new wallet and deposit SOL into it.

3. Go to [My Telegram](https://my.telegram.org/) and create a new application. Save the *APP ID* and the *APP HASH* values.

4. Go to [Telegram BotFather](https://telegram.me/BotFather) and follows the instructions to create a new telegram bot.
You will need the *bot token*.

5. Use the [get chat id script](scripts/get_tg_bot_chat_id.py) to get the chat id to where the reports will be send:
    ```bash
    python scripts/get_tg_bot_chat_id.py
    ```

6. Copy `config.json.sample` into `config.json` file, update the configuration to suit your needs.

7. Start the bot:
    ```bash
    python main.py
    ```

## Contributing

Contributions are appreciated! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.txt) file for details.

## Disclaimer

Use this bot at your own risk. The developers are not responsible for any financial losses incurred while using this tool.
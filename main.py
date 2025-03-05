import asyncio

from src.dexscreener_bot import DexScreenerBot


async def main():
    bot = DexScreenerBot("config.json")
    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
    bot = DexScreenerBot()

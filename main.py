import asyncio
import logging
import os
from dotenv import load_dotenv

from bot import initialize_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('discord_bot')

# Load environment variables
load_dotenv()

# Main function to run the bot
async def main():
    # Get the token from environment variables
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        logger.error("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return

    # Initialize and run the bot
    bot = await initialize_bot()
    
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

# Entry point
if __name__ == "__main__":
    asyncio.run(main())

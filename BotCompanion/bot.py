import discord
from discord.ext import commands
import logging
import os

from utils.config_manager import ConfigManager

logger = logging.getLogger('discord_bot')

# Initialize config manager
config_manager = ConfigManager()

async def initialize_bot():
    """Initialize the Discord bot with all necessary configurations and cogs."""
    # Get prefix from config, default to "!" if not set
    prefix = config_manager.get_prefix()
    
    # Set up intents (permissions for the bot)
    intents = discord.Intents.default()
    intents.members = True  # Enable member intents for welcome messages and invite tracking
    intents.message_content = True  # Enable message content for prefix commands
    
    # Create bot instance with command prefix and intents
    bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)
    
    # Event: Bot is ready
    @bot.event
    async def on_ready():
        logger.info(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Serving {len(bot.guilds)} guilds")
        
        # Set bot activity
        activity_type = discord.ActivityType.listening
        await bot.change_presence(
            activity=discord.Activity(
                type=activity_type,
                name=f"{prefix}help | /help"
            )
        )
        
        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    # Load all cogs
    cog_list = [
        'cogs.invite_tracker',
        'cogs.welcome_messages',
        'cogs.help_commands',
        'cogs.admin_commands',
        'cogs.level_system',
        'cogs.ticket_system',
        'cogs.counting_game',
        'cogs.temp_voice',
        'cogs.verification',
        'cogs.content_announcer',
        'cogs.self_roles_new',
        'cogs.bot_assistant',
        'cogs.server_stats',
        'cogs.language_settings',
        'cogs.channel_locker',  # Neue Cog zum Sperren von Kanälen
        'cogs.emoji_stealer',   # Neue Cog zum Stehlen von Emojis
        'cogs.captcha_verification',  # Neue Cog für Captcha-Verifizierung
        'cogs.setup_commands',   # Neue Cog für Setup-Befehle
        'cogs.moderation',      # Neue Cog für Moderationsbefehle
        'cogs.economy'          # Neue Cog für Economy-System
    ]
    
    for cog in cog_list:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded extension: {cog}")
        except Exception as e:
            logger.error(f"Failed to load extension {cog}: {e}")
    
    return bot

import discord
from discord.ext import commands
import logging
import os

from utils.config_manager import ConfigManager
from utils.embed_creator import EmbedCreator

logger = logging.getLogger('discord_bot')

class AdminCommands(commands.Cog):
    """Cog for administrative commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.embed_creator = EmbedCreator()
        
        # Get bot admin IDs from environment variables
        admin_ids_str = os.getenv('BOT_ADMIN_IDS', '')
        self.bot_admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
    
    def is_bot_admin(self, user_id: int) -> bool:
        """Check if a user is a bot administrator."""
        return user_id in self.bot_admin_ids
    
    @commands.command(name="prefix", description="Change the bot's command prefix")
    @commands.has_permissions(administrator=True)
    async def change_prefix(self, ctx: commands.Context, new_prefix: str):
        """
        Change the command prefix for the bot.
        
        Args:
            new_prefix: The new prefix to use for commands
        """
        # Check if the prefix is valid
        if not new_prefix or len(new_prefix) > 5:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Invalid Prefix",
                "The prefix must be between 1 and 5 characters long."
            ))
            return
        
        # Update the configuration
        self.config_manager.set_prefix(new_prefix)
        
        # Update the bot's prefix
        self.bot.command_prefix = new_prefix
        
        # Send confirmation
        await ctx.send(embed=self.embed_creator.create_success_embed(
            "Prefix Changed",
            f"The command prefix has been changed to `{new_prefix}`."
        ))
        
        # Update bot presence
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{new_prefix}help | /help"
            )
        )
    
    @commands.command(name="sync", description="Sync slash commands with Discord")
    async def sync_commands(self, ctx: commands.Context):
        """
        Sync slash commands with Discord. Only bot administrators can use this command.
        """
        # Check if the user is a bot administrator
        if not self.is_bot_admin(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Permission Denied",
                "You don't have permission to use this command."
            ))
            return
        
        # Sync the commands
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(embed=self.embed_creator.create_success_embed(
                "Commands Synced",
                f"Synced {len(synced)} command(s) with Discord."
            ))
            logger.info(f"Synced {len(synced)} command(s) with Discord")
        except Exception as e:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Sync Failed",
                f"Failed to sync commands: {str(e)}"
            ))
            logger.error(f"Failed to sync commands: {e}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Missing Argument",
                f"You're missing a required argument: `{error.param.name}`.\n"
                f"Use `{ctx.prefix}help {ctx.command.name}` for proper usage."
            ))
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Invalid Argument",
                f"You provided an invalid argument.\n"
                f"Use `{ctx.prefix}help {ctx.command.name}` for proper usage."
            ))
            return
            
        if isinstance(error, commands.MissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Missing Permissions",
                f"You need the following permissions to use this command: `{missing_perms}`."
            ))
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Bot Missing Permissions",
                f"I need the following permissions to run this command: `{missing_perms}`."
            ))
            return
            
        # Log other errors
        logger.error(f"Command error in {ctx.command}: {error}")
        
        # Send a generic error message
        await ctx.send(embed=self.embed_creator.create_error_embed(
            "Command Error",
            f"An error occurred while executing the command.\n```{str(error)}```"
        ))

async def setup(bot: commands.Bot):
    """Add the AdminCommands cog to the bot."""
    await bot.add_cog(AdminCommands(bot))
    logger.info("AdminCommands cog loaded")

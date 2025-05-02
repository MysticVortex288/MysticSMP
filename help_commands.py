import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.embed_creator import EmbedCreator

logger = logging.getLogger('discord_bot')

class HelpCommands(commands.Cog):
    """Cog for handling help commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.embed_creator = EmbedCreator()
    
    @commands.hybrid_command(name="help", description="Get help with bot commands")
    @app_commands.describe(command="The specific command to get help with")
    async def help_command(self, ctx: commands.Context, command: str = None):
        """
        Display help information about the bot and its commands.
        
        Args:
            command: Optional specific command to get help with
        """
        prefix = self.bot.command_prefix if isinstance(self.bot.command_prefix, str) else self.bot.command_prefix[0]
        
        if command is None:
            # General help - list all command categories
            await self._send_general_help(ctx, prefix)
        else:
            # Specific command help
            await self._send_command_help(ctx, command, prefix)
    
    async def _send_general_help(self, ctx: commands.Context, prefix: str):
        """Send general help information listing all command categories."""
        # Create main help embed
        embed = discord.Embed(
            title="Bot Help",
            description=(
                f"Here are all the available command categories. Use `{prefix}help <category>` "
                f"for more information about a specific category.\n\n"
                f"You can also use `/help <command>` for help with a specific command."
            ),
            color=discord.Color.blue()
        )
        
        # Add command categories
        categories = {
            "🎯 Invite Tracking": (
                "Track who invited whom to the server\n"
                f"`{prefix}help invites`"
            ),
            "👋 Welcome Messages": (
                "Customize welcome messages for new members\n"
                f"`{prefix}help welcome`"
            ),
            "🛠️ Admin Commands": (
                "Server and bot administration commands\n"
                f"`{prefix}help admin`"
            )
        }
        
        for category, description in categories.items():
            embed.add_field(name=category, value=description, inline=False)
        
        # Add general information
        embed.set_footer(text=f"Type {prefix}help <command> for detailed help on a command")
        
        await ctx.send(embed=embed)
    
    async def _send_command_help(self, ctx: commands.Context, command_name: str, prefix: str):
        """Send help information for a specific command or category."""
        # Lower the command name for easier comparison
        command_name = command_name.lower()
        
        # Check if it's a category help request
        if command_name in ["invites", "invite", "invite-tracking"]:
            await self._send_invites_help(ctx, prefix)
            return
        elif command_name in ["welcome", "welcomes", "welcome-messages"]:
            await self._send_welcome_help(ctx, prefix)
            return
        elif command_name in ["admin", "administration", "admin-commands"]:
            await self._send_admin_help(ctx, prefix)
            return
        
        # Try to find the command
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Command Not Found",
                f"No command called '{command_name}' was found. Type `{prefix}help` for a list of commands."
            ))
            return
        
        # Create command help embed
        embed = discord.Embed(
            title=f"Command: {prefix}{command.name}",
            description=command.help or "No description provided.",
            color=discord.Color.blue()
        )
        
        # Add command usage
        usage = f"{prefix}{command.name}"
        if command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        
        # Add aliases if any
        if command.aliases:
            aliases = ", ".join([f"{prefix}{alias}" for alias in command.aliases])
            embed.add_field(name="Aliases", value=aliases, inline=False)
        
        # Add subcommands if any
        if isinstance(command, commands.Group):
            subcommands = []
            for subcommand in command.commands:
                subcommands.append(f"`{prefix}{command.name} {subcommand.name}` - {subcommand.help.split('.')[0] if subcommand.help else 'No description'}")
            
            if subcommands:
                embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
        
        await ctx.send(embed=embed)
    
    async def _send_invites_help(self, ctx: commands.Context, prefix: str):
        """Send help information for invite tracking commands."""
        commands_dict = {
            f"{prefix}invites [member]": "Show how many people you or another member have invited to the server.",
            f"{prefix}invite-leaderboard": "Display a leaderboard of members with the most invites."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Invite Tracking Commands",
            description=(
                "These commands allow you to track and view information about server invites. "
                "The bot automatically tracks who invited whom to the server."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
    
    async def _send_welcome_help(self, ctx: commands.Context, prefix: str):
        """Send help information for welcome message commands."""
        commands_dict = {
            f"{prefix}welcome channel <channel>": "Set the channel for welcome messages.",
            f"{prefix}welcome message <message>": "Set the welcome message. Use variables like {user_mention}, {inviter}, etc.",
            f"{prefix}welcome toggle": "Toggle welcome messages on or off.",
            f"{prefix}welcome embed": "Toggle whether to use embeds for welcome messages.",
            f"{prefix}welcome color <hex>": "Set the color for welcome message embeds.",
            f"{prefix}welcome test": "Test the current welcome message settings.",
            f"{prefix}welcome variables": "Show available variables for welcome messages.",
            f"{prefix}welcome settings": "Show current welcome message settings."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Welcome Message Commands",
            description=(
                "These commands allow you to configure and customize welcome messages for new members. "
                "Welcome messages can include information about who invited the new member."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
    
    async def _send_admin_help(self, ctx: commands.Context, prefix: str):
        """Send help information for admin commands."""
        commands_dict = {
            f"{prefix}prefix <new_prefix>": "Change the bot's command prefix.",
            f"{prefix}sync": "Sync slash commands with Discord (admin only)."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Admin Commands",
            description=(
                "These commands are for server administrators to configure the bot."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add the HelpCommands cog to the bot."""
    await bot.add_cog(HelpCommands(bot))
    logger.info("HelpCommands cog loaded")

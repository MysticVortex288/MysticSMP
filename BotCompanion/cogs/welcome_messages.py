import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, Union

from utils.config_manager import ConfigManager
from utils.embed_creator import EmbedCreator
from utils.image_creator import ImageCreator

logger = logging.getLogger('discord_bot')

class WelcomeMessages(commands.Cog):
    """Cog for handling customizable welcome messages."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.embed_creator = EmbedCreator()
        
        # Initialisiere Standardeinstellungen für Willkommensbilder falls nicht vorhanden
        for guild in bot.guilds:
            guild_config = self.config_manager.get_guild_config(guild.id)
            if "welcome_image_enabled" not in guild_config:
                self.config_manager.update_guild_config(
                    guild.id, "welcome_image_enabled", False
                )
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event triggered when a new member joins the guild."""
        # Skip if the member is a bot
        if member.bot:
            return
            
        # Get the guild configuration
        guild_config = self.config_manager.get_guild_config(member.guild.id)
        
        # Check if welcome messages are enabled for this guild
        if not guild_config.get("welcome_enabled", False):
            logger.debug(f"Welcome messages disabled for guild {member.guild.name}")
            return
            
        # Get the welcome channel
        welcome_channel_id = guild_config.get("welcome_channel")
        if not welcome_channel_id:
            logger.warning(f"No welcome channel set for guild {member.guild.name}")
            return
            
        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            logger.warning(f"Welcome channel with ID {welcome_channel_id} not found in guild {member.guild.name}")
            return
            
        # Check if we can send messages in the welcome channel
        if not welcome_channel.permissions_for(member.guild.me).send_messages:
            logger.warning(f"Cannot send messages in welcome channel {welcome_channel.name} in guild {member.guild.name}")
            return
            
        # Get inviter (uses the InviteTracker cog underneath)
        inviter = None
        invite_tracker = self.bot.get_cog("InviteTracker")
        if invite_tracker:
            inviter = await invite_tracker._find_used_invite(member.guild)
            
        # Get the welcome message template
        welcome_message = guild_config.get("welcome_message", "Welcome to the server, {user_mention}!")
        
        # Send the welcome message
        try:
            # Prüfe, ob Willkommensbilder aktiviert sind
            if guild_config.get("welcome_image_enabled", False):
                # Erstelle und sende das Willkommensbild
                welcome_image = await ImageCreator.create_welcome_image(
                    user=member,
                    server_name=member.guild.name
                )
                
                if welcome_image:
                    # Formatiere die Nachricht für das Bild
                    formatted_message = welcome_message.format(
                        user=member.name,
                        user_mention=member.mention,
                        user_tag=str(member),
                        user_id=member.id,
                        server=member.guild.name,
                        inviter=inviter.mention if inviter else "Unknown",
                        inviter_name=inviter.name if inviter else "Unknown",
                        inviter_tag=str(inviter) if inviter else "Unknown",
                        member_count=member.guild.member_count
                    )
                    
                    # Sende das Bild mit der Nachricht
                    await welcome_channel.send(content=formatted_message, file=welcome_image)
                    logger.info(f"Sent welcome image for {member.name} in guild {member.guild.name}")
                else:
                    logger.error(f"Failed to create welcome image for {member.name}")
                    # Fallback to regular welcome message
                    await self._send_regular_welcome_message(member, welcome_channel, welcome_message, inviter, guild_config)
            else:
                # Normale Willkommensnachricht senden
                await self._send_regular_welcome_message(member, welcome_channel, welcome_message, inviter, guild_config)
                
            logger.info(f"Sent welcome message for {member.name} in guild {member.guild.name}")
        except Exception as e:
            logger.error(f"Error sending welcome message for {member.name} in guild {member.guild.name}: {e}")
    
    async def _send_regular_welcome_message(self, member, channel, message, inviter, guild_config):
        """Hilfsmethode zum Senden einer regulären Willkommensnachricht."""
        if guild_config.get("welcome_embed_enabled", True):
            # Send as an embed
            embed_color = guild_config.get("welcome_embed_color", "0x3498db")
            embed = self.embed_creator.create_welcome_embed(
                user=member,
                inviter=inviter,
                message=message,
                color=embed_color
            )
            await channel.send(embed=embed)
        else:
            # Send as a plain text message
            formatted_message = message.format(
                user=member.name,
                user_mention=member.mention,
                user_tag=str(member),
                user_id=member.id,
                server=member.guild.name,
                inviter=inviter.mention if inviter else "Unknown",
                inviter_name=inviter.name if inviter else "Unknown",
                inviter_tag=str(inviter) if inviter else "Unknown",
                member_count=member.guild.member_count
            )
            await channel.send(formatted_message)
    
    @commands.hybrid_group(name="welcome", description="Manage welcome message settings")
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, ctx: commands.Context):
        """Command group for managing welcome message settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @welcome.command(name="channel", description="Set the channel for welcome messages")
    @app_commands.describe(channel="The channel to send welcome messages to")
    async def welcome_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where welcome messages will be sent."""
        # Check if the bot has permission to send messages in the channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Missing Permissions",
                f"I don't have permission to send messages in {channel.mention}."
            ))
            return
        
        # Update the configuration
        self.config_manager.update_guild_config(ctx.guild.id, "welcome_channel", channel.id)
        
        # Send confirmation
        await ctx.send(embed=self.embed_creator.create_success_embed(
            "Welcome Channel Set",
            f"Welcome messages will now be sent to {channel.mention}."
        ))
        
        # Enable welcome messages if they're not already enabled
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        if not guild_config.get("welcome_enabled", False):
            self.config_manager.update_guild_config(ctx.guild.id, "welcome_enabled", True)
            await ctx.send(embed=self.embed_creator.create_success_embed(
                "Welcome Messages Enabled",
                "Welcome messages have been automatically enabled."
            ))
    
    @welcome.command(name="message", description="Set the welcome message")
    @app_commands.describe(message="The welcome message to use. Use {user_mention}, {inviter}, etc.")
    async def welcome_message(self, ctx: commands.Context, *, message: str):
        """Set the message that will be sent when a new member joins."""
        # Update the configuration
        self.config_manager.update_guild_config(ctx.guild.id, "welcome_message", message)
        
        # Create a preview
        sample_embed = self.embed_creator.create_welcome_embed(
            user=ctx.author,
            inviter=ctx.author,  # Just for preview purposes
            message=message,
            color=self.config_manager.get_guild_config(ctx.guild.id).get("welcome_embed_color", "0x3498db")
        )
        
        # Send confirmation and preview
        await ctx.send(
            embed=self.embed_creator.create_success_embed(
                "Welcome Message Set",
                "The welcome message has been updated. Here's a preview:"
            )
        )
        
        await ctx.send(embed=sample_embed)
    
    @welcome.command(name="toggle", description="Toggle welcome messages on or off")
    async def welcome_toggle(self, ctx: commands.Context):
        """Toggle whether welcome messages are enabled or disabled."""
        # Get current state
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        currently_enabled = guild_config.get("welcome_enabled", False)
        
        # Toggle state
        new_state = not currently_enabled
        self.config_manager.update_guild_config(ctx.guild.id, "welcome_enabled", new_state)
        
        # Check if a welcome channel is set when enabling
        if new_state and not guild_config.get("welcome_channel"):
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "No Welcome Channel",
                "Welcome messages are now enabled, but you haven't set a welcome channel yet. "
                "Use `/welcome channel` to set one."
            ))
            return
        
        # Send confirmation
        status = "enabled" if new_state else "disabled"
        await ctx.send(embed=self.embed_creator.create_success_embed(
            f"Welcome Messages {status.capitalize()}",
            f"Welcome messages have been {status}."
        ))
    
    @welcome.command(name="embed", description="Toggle whether to use embeds for welcome messages")
    async def welcome_embed(self, ctx: commands.Context):
        """Toggle whether welcome messages are sent as embeds or plain text."""
        # Get current state
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        currently_enabled = guild_config.get("welcome_embed_enabled", True)
        
        # Toggle state
        new_state = not currently_enabled
        self.config_manager.update_guild_config(ctx.guild.id, "welcome_embed_enabled", new_state)
        
        # Send confirmation
        status = "enabled" if new_state else "disabled"
        await ctx.send(embed=self.embed_creator.create_success_embed(
            f"Welcome Embeds {status.capitalize()}",
            f"Welcome messages will now be sent as {'embedded messages' if new_state else 'plain text'}."
        ))
    
    @welcome.command(name="color", description="Set the color for welcome embeds")
    @app_commands.describe(color="The color in hex format (e.g., 0xFF0000 for red)")
    async def welcome_color(self, ctx: commands.Context, color: str):
        """Set the color for welcome message embeds."""
        # Validate color format
        if not color.startswith("0x"):
            color = f"0x{color}" if not color.startswith("#") else f"0x{color[1:]}"
            
        try:
            # Try to parse the color
            color_int = int(color, 16)
            
            # Update the configuration
            self.config_manager.update_guild_config(ctx.guild.id, "welcome_embed_color", color)
            
            # Create a preview
            guild_config = self.config_manager.get_guild_config(ctx.guild.id)
            sample_embed = self.embed_creator.create_welcome_embed(
                user=ctx.author,
                inviter=ctx.author,
                message=guild_config.get("welcome_message", "Welcome to the server, {user_mention}!"),
                color=color
            )
            
            # Send confirmation and preview
            await ctx.send(
                embed=self.embed_creator.create_success_embed(
                    "Embed Color Set",
                    f"The welcome embed color has been set to {color}. Here's a preview:"
                )
            )
            
            await ctx.send(embed=sample_embed)
        except ValueError:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Invalid Color",
                "Please provide a valid hex color (e.g., 0xFF0000 or FF0000 for red)."
            ))
    
    @welcome.command(name="image", description="Aktiviert oder deaktiviert Willkommensbilder")
    async def welcome_image(self, ctx: commands.Context):
        """Aktiviert oder deaktiviert das Senden von Willkommensbildern mit Profilbild."""
        # Aktuellen Status abrufen
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        currently_enabled = guild_config.get("welcome_image_enabled", False)
        
        # Status umschalten
        new_state = not currently_enabled
        self.config_manager.update_guild_config(ctx.guild.id, "welcome_image_enabled", new_state)
        
        # Wenn aktiviert, sende Testbild
        if new_state:
            welcome_image = await ImageCreator.create_welcome_image(
                user=ctx.author,
                server_name=ctx.guild.name
            )
            
            if welcome_image:
                await ctx.send(
                    embed=self.embed_creator.create_success_embed(
                        "Willkommensbilder aktiviert",
                        "Neue Mitglieder erhalten nun ein personalisiertes Willkommensbild wie dieses:"
                    )
                )
                await ctx.send(file=welcome_image)
            else:
                await ctx.send(
                    embed=self.embed_creator.create_error_embed(
                        "Fehler bei der Bilderstellung",
                        "Willkommensbilder wurden aktiviert, aber es gab ein Problem bei der Erstellung des Beispielbildes."
                    )
                )
        else:
            await ctx.send(
                embed=self.embed_creator.create_success_embed(
                    "Willkommensbilder deaktiviert",
                    "Neue Mitglieder erhalten nun keine personalisierten Willkommensbilder mehr."
                )
            )
    
    @welcome.command(name="test", description="Test the current welcome message settings")
    async def welcome_test(self, ctx: commands.Context):
        """Test the current welcome message settings."""
        # Get the guild configuration
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        
        # Check if a welcome channel is set
        welcome_channel_id = guild_config.get("welcome_channel")
        if not welcome_channel_id:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "No Welcome Channel",
                "You haven't set a welcome channel yet. Use `/welcome channel` to set one."
            ))
            return
            
        welcome_channel = ctx.guild.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Invalid Welcome Channel",
                "The configured welcome channel could not be found. It may have been deleted."
            ))
            return
        
        # Get the welcome message
        welcome_message = guild_config.get("welcome_message", "Welcome to the server, {user_mention}!")
        
        try:
            # Prüfe, ob Willkommensbilder aktiviert sind
            if guild_config.get("welcome_image_enabled", False):
                # Erstelle und sende das Willkommensbild
                welcome_image = await self.image_creator.create_welcome_image(
                    user=ctx.author,
                    server_name=ctx.guild.name,
                    member_count=ctx.guild.member_count
                )
                
                if welcome_image:
                    # Formatiere die Nachricht für das Bild
                    formatted_message = welcome_message.format(
                        user=ctx.author.name,
                        user_mention=ctx.author.mention,
                        user_tag=str(ctx.author),
                        user_id=ctx.author.id,
                        server=ctx.guild.name,
                        inviter=ctx.author.mention,
                        inviter_name=ctx.author.name,
                        inviter_tag=str(ctx.author),
                        member_count=ctx.guild.member_count
                    )
                    
                    # Sende das Bild mit der Nachricht
                    await welcome_channel.send(content=f"{formatted_message}\n\n**Note**: Dies ist ein Test der Willkommensnachricht.", file=welcome_image)
                else:
                    await ctx.send(embed=self.embed_creator.create_error_embed(
                        "Fehler bei der Bilderstellung",
                        "Es gab ein Problem bei der Erstellung des Willkommensbildes."
                    ))
                    # Fallback zu regulärer Willkommensnachricht
                    await self._send_test_regular_welcome_message(ctx, welcome_channel, welcome_message, guild_config)
            else:
                # Normale Willkommensnachricht senden
                await self._send_test_regular_welcome_message(ctx, welcome_channel, welcome_message, guild_config)
                
            # Sende eine Bestätigung
            await ctx.send(embed=self.embed_creator.create_success_embed(
                "Test-Willkommensnachricht gesendet",
                f"Eine Test-Willkommensnachricht wurde in {welcome_channel.mention} gesendet."
            ))
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der Test-Willkommensnachricht: {e}")
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Fehler",
                f"Beim Senden der Test-Willkommensnachricht ist ein Fehler aufgetreten: {str(e)}"
            ))
    
    async def _send_test_regular_welcome_message(self, ctx, welcome_channel, welcome_message, guild_config):
        """Hilfsmethode zum Senden einer regulären Test-Willkommensnachricht."""
        if guild_config.get("welcome_embed_enabled", True):
            # Send as an embed
            embed_color = guild_config.get("welcome_embed_color", "0x3498db")
            embed = self.embed_creator.create_welcome_embed(
                user=ctx.author,
                inviter=ctx.author,  # Using the author as the inviter for the test
                message=welcome_message,
                color=embed_color
            )
            
            # Add a note that this is a test
            embed.add_field(
                name="Test Message",
                value="This is a test of the welcome message system.",
                inline=False
            )
            
            await welcome_channel.send(embed=embed)
        else:
            # Send as a plain text message
            formatted_message = welcome_message.format(
                user=ctx.author.name,
                user_mention=ctx.author.mention,
                user_tag=str(ctx.author),
                user_id=ctx.author.id,
                server=ctx.guild.name,
                inviter=ctx.author.mention,
                inviter_name=ctx.author.name,
                inviter_tag=str(ctx.author),
                member_count=ctx.guild.member_count
            )
            
            await welcome_channel.send(f"{formatted_message}\n\n**Note**: This is a test of the welcome message system.")
    
    @welcome.command(name="variables", description="Show available variables for welcome messages")
    async def welcome_variables(self, ctx: commands.Context):
        """Show a list of available variables that can be used in welcome messages."""
        variables = {
            "{user}": "The username of the new member",
            "{user_mention}": "Mentions the new member",
            "{user_tag}": "The username and discriminator (e.g., User#1234)",
            "{user_id}": "The user ID of the new member",
            "{server}": "The name of the server",
            "{inviter}": "Mentions the user who created the invite",
            "{inviter_name}": "The username of the inviter",
            "{inviter_tag}": "The username and discriminator of the inviter",
            "{member_count}": "The current number of members in the server"
        }
        
        # Create the embed
        embed = discord.Embed(
            title="Welcome Message Variables",
            description="You can use these variables in your welcome messages:",
            color=discord.Color.blue()
        )
        
        # Add all variables to the embed
        for var, desc in variables.items():
            embed.add_field(name=var, value=desc, inline=False)
            
        # Add an example
        embed.add_field(
            name="Example",
            value=(
                "Message: `Welcome to {server}, {user_mention}! You were invited by {inviter_name}.`\n"
                "Result: `Welcome to Discord Server, @User! You were invited by Inviter.`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @welcome.command(name="settings", description="Show current welcome message settings")
    async def welcome_settings(self, ctx: commands.Context):
        """Display the current welcome message settings for the guild."""
        # Get the guild configuration
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        
        # Get settings
        enabled = guild_config.get("welcome_enabled", False)
        welcome_channel_id = guild_config.get("welcome_channel")
        welcome_channel = ctx.guild.get_channel(int(welcome_channel_id)) if welcome_channel_id else None
        welcome_message = guild_config.get("welcome_message", "Welcome to the server, {user_mention}!")
        embed_enabled = guild_config.get("welcome_embed_enabled", True)
        embed_color = guild_config.get("welcome_embed_color", "0x3498db")
        
        # Create the embed
        embed = discord.Embed(
            title="Welcome Message Settings",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Status", value="Enabled" if enabled else "Disabled", inline=True)
        embed.add_field(name="Channel", value=welcome_channel.mention if welcome_channel else "Not set", inline=True)
        embed.add_field(name="Use Embeds", value="Yes" if embed_enabled else "No", inline=True)
        
        if embed_enabled:
            embed.add_field(name="Embed Color", value=embed_color, inline=True)
            
        embed.add_field(name="Welcome Message", value=f"```{welcome_message}```", inline=False)
        
        # Add a preview
        if welcome_channel:
            embed.add_field(
                name="Preview",
                value=f"Use `/welcome test` to send a test message to {welcome_channel.mention}.",
                inline=False
            )
            
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add the WelcomeMessages cog to the bot."""
    await bot.add_cog(WelcomeMessages(bot))
    logger.info("WelcomeMessages cog loaded")

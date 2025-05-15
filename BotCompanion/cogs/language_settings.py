import discord
from discord.ext import commands
import logging
from typing import Optional, List
from utils.language_manager import LanguageManager

logger = logging.getLogger('discord_bot')

class LanguageSettings(commands.Cog):
    """Cog für Spracheinstellungen."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the language settings cog."""
        self.bot = bot
        self.language_manager = LanguageManager()
        logger.info("LanguageSettings cog initialized")
    
    @commands.hybrid_command(name="language", description="Change your preferred language / Ändere deine bevorzugte Sprache")
    async def set_language(self, ctx: commands.Context, language: str = ""):
        """
        Change your preferred language or view your current language.
        
        Args:
            language: The language to set (en=English, de=Deutsch), or None to view current language
        """
        # If no language is provided, show the current language
        if not language:
            current_language = self.language_manager.get_user_language(ctx.author.id)
            language_name = self.language_manager.get_text(f"languages.language_{current_language}", current_language)
            message = self.language_manager.get_context_text(ctx, "languages.current_language", language=language_name)
            
            # Show available languages
            available_languages = []
            for lang_code in self.language_manager.get_available_languages():
                lang_name = self.language_manager.get_text(f"languages.language_{lang_code}", lang_code)
                available_languages.append(f"`{lang_code}` - {lang_name}")
            
            embed = discord.Embed(
                title="🌐 Language / Sprache",
                description=message + "\n\n" + "\n".join(available_languages),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Convert language to lowercase
        language = language.lower()
        
        # Check if the language is supported
        if language not in self.language_manager.get_available_languages():
            # Get available languages for error message
            languages_list = ", ".join(self.language_manager.get_available_languages())
            message = self.language_manager.get_context_text(
                ctx, "languages.language_not_found_desc", 
                languages=languages_list
            )
            embed = discord.Embed(
                title=self.language_manager.get_context_text(ctx, "languages.language_not_found"),
                description=message,
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Set the language
        self.language_manager.set_user_language(ctx.author.id, language)
        
        # Get the language name in the new language
        language_name = self.language_manager.get_text(f"languages.language_{language}", language=language)
        
        # Send confirmation message in the new language
        message = self.language_manager.get_text(
            "languages.language_set_desc", 
            language=language,
            language_name=language_name
        )
        embed = discord.Embed(
            title=self.language_manager.get_text("languages.language_set", language=language),
            description=message,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="serverlanguage", description="Change the server's default language / Ändere die Standardsprache des Servers")
    @commands.has_permissions(administrator=True)
    async def set_server_language(self, ctx: commands.Context, language: str = ""):
        """
        Change the server's default language or view the current language.
        
        Args:
            language: The language to set (en=English, de=Deutsch), or None to view current language
        """
        # Check if we're in a guild
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        
        # If no language is provided, show the current language
        if not language:
            current_language = self.language_manager.get_guild_language(ctx.guild.id)
            language_name = self.language_manager.get_text(f"languages.language_{current_language}", current_language)
            message = self.language_manager.get_context_text(ctx, "languages.current_language", language=language_name)
            
            # Show available languages
            available_languages = []
            for lang_code in self.language_manager.get_available_languages():
                lang_name = self.language_manager.get_text(f"languages.language_{lang_code}", lang_code)
                available_languages.append(f"`{lang_code}` - {lang_name}")
            
            embed = discord.Embed(
                title="🌐 Server Language / Server-Sprache",
                description=message + "\n\n" + "\n".join(available_languages),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Convert language to lowercase
        language = language.lower()
        
        # Check if the language is supported
        if language not in self.language_manager.get_available_languages():
            # Get available languages for error message
            languages_list = ", ".join(self.language_manager.get_available_languages())
            message = self.language_manager.get_context_text(
                ctx, "languages.language_not_found_desc", 
                languages=languages_list
            )
            embed = discord.Embed(
                title=self.language_manager.get_context_text(ctx, "languages.language_not_found"),
                description=message,
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Set the language
        self.language_manager.set_guild_language(ctx.guild.id, language)
        
        # Get the language name in the new language
        language_name = self.language_manager.get_text(f"languages.language_{language}", language=language)
        
        # Send confirmation message in the new language
        message = self.language_manager.get_text(
            "languages.language_set_desc", 
            language=language,
            language_name=language_name
        )
        embed = discord.Embed(
            title=self.language_manager.get_text("languages.language_set", language=language),
            description=message,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add the LanguageSettings cog to the bot."""
    await bot.add_cog(LanguageSettings(bot))
    logger.info("LanguageSettings cog loaded")
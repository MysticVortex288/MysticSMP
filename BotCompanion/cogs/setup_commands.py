import discord
from discord.ext import commands
import logging
import json
from typing import Dict, Optional, Union
import os

logger = logging.getLogger('discord_bot')

class SetupCommands(commands.Cog):
    """Cog für Setup-Befehle für Server-Administratoren."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = {}  # guild_id -> settings
        self._load_settings()
        logger.info("SetupCommands cog initialized")

    def _load_settings(self):
        """Lädt die Einstellungen aus der Datei."""
        try:
            with open('setup_settings.json', 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
            self._save_settings()

    def _save_settings(self):
        """Speichert die Einstellungen in der Datei."""
        with open('setup_settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)

    @commands.hybrid_command(name="botinfo", description="Zeigt Informationen über den Bot.")
    async def show_bot_info(self, ctx: commands.Context):
        """
        Zeigt Informationen über den Bot und seine Funktionen.
        """
        embed = discord.Embed(
            title=f"{self.bot.user.name} - Bot Informationen",
            description="Ein vielseitiger Discord-Bot für Server-Management und Benutzerengagement.",
            color=discord.Color.blue()
        )
        
        # Bot-Status
        embed.add_field(
            name="Status", 
            value=f"Online auf {len(self.bot.guilds)} Servern\nBetreue {sum(guild.member_count for guild in self.bot.guilds)} Benutzer", 
            inline=False
        )
        
        # Kern-Features
        features = [
            "🎯 **Invite Tracking** - Verfolge, wer wen eingeladen hat",
            "👋 **Welcome Messages** - Anpassbare Willkommensnachrichten",
            "⬆️ **Level System** - Rangfolge und XP-System",
            "🎫 **Ticket System** - Support-Tickets für Benutzer",
            "🔢 **Counting Game** - Gemeinsames Zählen in einem Kanal",
            "🎙️ **Temp Voice** - Temporäre Sprachkanäle",
            "🔒 **Verifizierung** - Benutzerverifizierung mit Rollen",
            "🔒 **Captcha** - Captcha-Verifizierung für neue Mitglieder",
            "📢 **Content Announcer** - Social Media Ankündigungen",
            "🏷️ **Self-Roles** - Selbstzuweisung von Rollen",
            "📊 **Server Stats** - Server-Statistiken",
            "🌐 **Multi-Language** - Mehrsprachiger Bot",
            "❓ **Bot Assistant** - Beantwortung von Fragen über den Bot",
            "🔐 **Channel Locker** - Temporäres Sperren von Kanälen",
            "😀 **Emoji Stealer** - Kopieren von Emojis von anderen Servern"
        ]
        
        embed.add_field(
            name="Funktionen", 
            value="\n".join(features), 
            inline=False
        )
        
        # Admin Info
        embed.add_field(
            name="Admin-Befehle", 
            value=f"Nutze `/help` oder `!help` für eine Liste der verfügbaren Befehle.\nNutze `/setupcaptcha` um die Captcha-Verifizierung einzurichten.", 
            inline=False
        )
        
        # Bot-Berechtigungen
        missing_perms = []
        if ctx.guild:
            bot_member = ctx.guild.get_member(self.bot.user.id)
            important_perms = {
                'manage_roles': 'Rollen verwalten',
                'manage_channels': 'Kanäle verwalten',
                'manage_messages': 'Nachrichten verwalten',
                'read_message_history': 'Nachrichtenverlauf lesen',
                'send_messages': 'Nachrichten senden',
                'embed_links': 'Links einbetten',
                'attach_files': 'Dateien anhängen',
                'add_reactions': 'Reaktionen hinzufügen',
                'use_external_emojis': 'Externe Emojis verwenden',
                'manage_guild': 'Server verwalten'
            }
            
            for perm_name, perm_display in important_perms.items():
                if not getattr(bot_member.guild_permissions, perm_name):
                    missing_perms.append(f"❌ {perm_display}")
        
        if missing_perms:
            embed.add_field(
                name="⚠️ Fehlende Berechtigungen", 
                value="Folgende Berechtigungen fehlen für volle Funktionalität:\n" + "\n".join(missing_perms), 
                inline=False
            )
        
        # Footer
        embed.set_footer(text="Bot entwickelt mit discord.py")
        
        # Bot-Avatar
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setupguide", description="Zeigt eine Anleitung zur Einrichtung des Bots.")
    async def setup_guide(self, ctx: commands.Context):
        """
        Zeigt eine Anleitung zur Einrichtung der verschiedenen Bot-Funktionen.
        """
        prefix = await self._get_prefix(ctx.guild)
        
        embed = discord.Embed(
            title="Bot Einrichtungsanleitung",
            description=f"Hier ist eine Anleitung zur Einrichtung der verschiedenen Funktionen des Bots. Du kannst sowohl Slash-Commands (/) als auch Präfix-Commands (`{prefix}`) verwenden.",
            color=discord.Color.blue()
        )
        
        # Captcha-Verifizierung
        embed.add_field(
            name="🔒 Captcha-Verifizierung", 
            value=(
                f"**1.** Aktiviere: `/setupcaptcha true`\n"
                f"**2.** Mit bestimmter Rolle: `/setupcaptcha true @Rolle`\n"
                f"**3.** Deaktiviere: `/setupcaptcha false`\n"
                f"**4.** Status anzeigen: `/setupcaptcha`\n"
                f"**5.** Testen: `/testcaptcha`"
            ), 
            inline=False
        )
        
        # Level-System
        embed.add_field(
            name="⬆️ Level-System", 
            value=(
                f"**1.** Einrichten: `{prefix}setuplevel`\n"
                f"**2.** Rollen für Level festlegen: `{prefix}setlevelrole <level> <rolle>`\n"
                f"**3.** XP-Bereich festlegen: `{prefix}setxprange <min> <max>`\n"
                f"**4.** Rangliste anzeigen: `{prefix}leaderboard`\n"
                f"**5.** Auto-Leaderboard einrichten: `{prefix}setleaderboardchannel`"
            ), 
            inline=False
        )
        
        # Ticket-System
        embed.add_field(
            name="🎫 Ticket-System", 
            value=(
                f"**1.** Einrichten: `{prefix}setupticket [kategorie] [support_rolle]`\n"
                f"**2.** Support-Rolle hinzufügen: `{prefix}addsupportrole <rolle>`\n"
                f"**3.** Panel erstellen: `{prefix}ticketpanel [nachricht]`\n"
                f"**4.** Log-Kanal festlegen: `{prefix}setlogchannel <kanal>`"
            ), 
            inline=False
        )
        
        # Welcome Messages
        embed.add_field(
            name="👋 Willkommensnachrichten", 
            value=(
                f"**1.** Kanal festlegen: `{prefix}welcome channel <kanal>`\n"
                f"**2.** Nachricht festlegen: `{prefix}welcome message <nachricht>`\n"
                f"**3.** Aktivieren/Deaktivieren: `{prefix}welcome toggle`\n"
                f"**4.** Einbettungen aktivieren: `{prefix}welcome embed`\n"
                f"**5.** Farbe festlegen: `{prefix}welcome color <hex>`\n"
                f"**6.** Testen: `{prefix}welcome test`"
            ), 
            inline=False
        )
        
        # Weitere Funktionen
        embed.add_field(
            name="📚 Weitere Funktionen", 
            value=(
                f"Weitere Funktionen einrichten:\n"
                f"**•** Temporäre Sprachkanäle: `{prefix}setupvoice [kategorie]`\n"
                f"**•** Verifizierung: `{prefix}setupverify [nachricht]`\n"
                f"**•** Counting Game: `{prefix}countingsetup [kanal]`\n"
                f"**•** Server Stats: `{prefix}setupstats`\n"
                f"**•** Self-Roles: Verwende den Assistenten mit `{prefix}selfroles`\n"
                f"**•** Content Announcer: `{prefix}set_announcement_channel`\n"
                f"**•** Bot Assistant: `{prefix}setup_assistant [kanal]`"
            ), 
            inline=False
        )
        
        embed.set_footer(text=f"Benutze {prefix}help <befehl> für Details zu jedem Befehl")
        
        await ctx.send(embed=embed)
    
    async def _get_prefix(self, guild) -> str:
        """Holt das Präfix für einen Server."""
        if not guild:
            return '!'
            
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                
            guild_id = str(guild.id)
            if guild_id in config and 'prefix' in config[guild_id]:
                return config[guild_id]['prefix']
            else:
                return '!'
        except (FileNotFoundError, json.JSONDecodeError):
            return '!'

async def setup(bot: commands.Bot):
    """Fügt den SetupCommands-Cog zum Bot hinzu."""
    await bot.add_cog(SetupCommands(bot))
    logger.info("SetupCommands cog loaded")
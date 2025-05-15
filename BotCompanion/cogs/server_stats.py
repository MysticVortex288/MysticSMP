import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import logging
import datetime
import asyncio
from typing import Dict, List, Optional
from utils.language_manager import LanguageManager

# Konfiguration für das Logging
logger = logging.getLogger('discord_bot')

class ServerStats(commands.Cog):
    """
    Cog für Server-Statistiken, die automatisch aktualisiert werden.
    Zeigt Informationen wie Mitgliederanzahl, Server-Alter, Anzahl der Kanäle usw.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "server_stats.json"
        self.config = self._load_config()
        self.update_interval = 300  # Aktualisierung alle 5 Minuten (in Sekunden)
        self.language_manager = LanguageManager()
        self.update_stats_task.start()
        logger.info("ServerStats cog initialized")
    
    def cog_unload(self):
        """Called when the cog is unloaded."""
        self.update_stats_task.cancel()
    
    def _load_config(self) -> Dict:
        """Laden der Konfiguration aus der Datei."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Standardkonfiguration erstellen
            default_config = {
                "stats_channels": {}
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config=None) -> None:
        """Speichern der Konfiguration in der Datei."""
        if config is None:
            config = self.config
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    @commands.hybrid_command(name="setupstats", description="Richtet Kanäle für Server-Statistiken ein / Sets up channels for server statistics", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setup_stats(self, ctx: commands.Context):
        """
        Richtet automatisch aktualisierte Statistik-Kanäle ein.
        Diese Kanäle zeigen Informationen wie Mitgliederanzahl, Online-Mitglieder usw.
        """
        guild = ctx.guild
        guild_id = str(guild.id)
        
        # Überprüfen, ob bereits Statistik-Kanäle eingerichtet sind
        if guild_id in self.config["stats_channels"] and self.config["stats_channels"][guild_id]:
            # Kanäle bereits vorhanden
            embed = discord.Embed(
                title="❌ Statistiken bereits eingerichtet",
                description=f"Es wurden bereits Statistik-Kanäle für diesen Server eingerichtet. Verwende `/removestats`, um die vorhandenen Kanäle zu entfernen.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Erstellung einer Kategorie für Statistiken
        try:
            # Holen der Serversprache
            guild_language = self.language_manager.get_guild_language(guild.id)
            
            # Sende eine Nachricht, dass die Einrichtung begonnen hat
            status_text = self.language_manager.get_text("server_stats.stats_updating", guild_language)
            status_message = await ctx.send(status_text)
            
            # Erstelle eine neue Kategorie für die Statistiken
            category_name = self.language_manager.get_text("server_stats.category_name", guild_language)
            stats_category = await guild.create_category(category_name)
            
            # Erstelle verschiedene Voice-Kanäle für Statistiken
            # Mitglieder
            member_text = self.language_manager.get_text("server_stats.members", guild_language, count=guild.member_count)
            member_count_channel = await guild.create_voice_channel(
                member_text,
                category=stats_category
            )
            
            # Berechne, wie viele Mitglieder online sind
            online_members = sum(1 for member in guild.members if member.status != discord.Status.offline and not member.bot)
            online_text = self.language_manager.get_text("server_stats.online", guild_language, count=online_members)
            online_channel = await guild.create_voice_channel(
                online_text,
                category=stats_category
            )
            
            # Anzahl der Textkanäle
            text_channels = len(guild.text_channels)
            text_text = self.language_manager.get_text("server_stats.text_channels", guild_language, count=text_channels)
            text_channel = await guild.create_voice_channel(
                text_text,
                category=stats_category
            )
            
            # Anzahl der Sprachkanäle
            voice_channels = len(guild.voice_channels)
            voice_text = self.language_manager.get_text("server_stats.voice_channels", guild_language, count=voice_channels)
            voice_channel = await guild.create_voice_channel(
                voice_text,
                category=stats_category
            )
            
            # Server-Alter berechnen
            server_created = guild.created_at
            days_since_creation = (datetime.datetime.now(datetime.timezone.utc) - server_created).days
            age_text = self.language_manager.get_text("server_stats.server_age", guild_language, days=days_since_creation)
            age_channel = await guild.create_voice_channel(
                age_text,
                category=stats_category
            )
            
            # Rolle mit den meisten Mitgliedern
            roles = [role for role in guild.roles if not role.is_default()]
            if roles:
                roles.sort(key=lambda r: len(r.members), reverse=True)
                top_role = roles[0]
                top_role_text = self.language_manager.get_text("server_stats.top_role", guild_language, 
                                                       name=top_role.name, count=len(top_role.members))
                top_role_channel = await guild.create_voice_channel(
                    top_role_text,
                    category=stats_category
                )
            else:
                top_role_text = self.language_manager.get_text("server_stats.top_role_none", guild_language)
                top_role_channel = await guild.create_voice_channel(
                    top_role_text,
                    category=stats_category
                )
                
            # Anzahl der Boosts
            boost_text = self.language_manager.get_text("server_stats.boosts", guild_language, count=guild.premium_subscription_count)
            boost_channel = await guild.create_voice_channel(
                boost_text,
                category=stats_category
            )
            
            # Boost-Level
            level_text = self.language_manager.get_text("server_stats.boost_level", guild_language, level=guild.premium_tier)
            boost_level_channel = await guild.create_voice_channel(
                level_text,
                category=stats_category
            )
            
            # Anzahl der Emojis
            emoji_text = self.language_manager.get_text("server_stats.emojis", guild_language, count=len(guild.emojis))
            emoji_channel = await guild.create_voice_channel(
                emoji_text,
                category=stats_category
            )
            
            # Anzahl der Rollen
            roles_text = self.language_manager.get_text("server_stats.roles", guild_language, count=len(guild.roles) - 1)  # -1 für @everyone
            roles_channel = await guild.create_voice_channel(
                roles_text,
                category=stats_category
            )
            
            # Kanäle in der Konfiguration speichern
            self.config["stats_channels"][guild_id] = {
                "category_id": stats_category.id,
                "member_count_id": member_count_channel.id,
                "online_count_id": online_channel.id,
                "text_channels_id": text_channel.id,
                "voice_channels_id": voice_channel.id,
                "age_id": age_channel.id,
                "top_role_id": top_role_channel.id,
                "boost_count_id": boost_channel.id,
                "boost_level_id": boost_level_channel.id,
                "emoji_count_id": emoji_channel.id,
                "roles_count_id": roles_channel.id
            }
            
            self._save_config()
            
            # Berechtigungen für alle Kanäle einschränken
            all_channels = [
                member_count_channel, online_channel, text_channel, voice_channel, 
                age_channel, top_role_channel, boost_channel, boost_level_channel,
                emoji_channel, roles_channel
            ]
            for channel in all_channels:
                await channel.set_permissions(guild.default_role, connect=False)
            
            # Status-Nachricht aktualisieren mit "wird aktualisiert..."
            update_text = self.language_manager.get_text("server_stats.stats_updating", guild_language)
            update_message = await status_message.edit(content=update_text, embed=None)
            
            # Sofort die Statistiken aktualisieren
            try:
                # Aktualisiere die Statistik-Kanäle sofort
                guild_channels = self.config["stats_channels"][guild_id]
                await self._update_stats_for_guild(guild, guild_channels)
                
                # Status-Nachricht aktualisieren mit Erfolg
                title = self.language_manager.get_text("server_stats.stats_setup_title", guild_language)
                desc = self.language_manager.get_text("server_stats.stats_setup_desc", guild_language)
                embed = discord.Embed(
                    title=title,
                    description=desc,
                    color=discord.Color.green()
                )
                
                await update_message.edit(content=None, embed=embed)
            except Exception as e:
                logger.error(f"Fehler beim initialen Aktualisieren der Statistik-Kanäle: {e}")
                # Trotzdem Erfolg anzeigen, da die Statistiken in 5 Minuten automatisch aktualisiert werden
                title = self.language_manager.get_text("server_stats.stats_setup_title", guild_language)
                desc = self.language_manager.get_text("server_stats.stats_setup_desc", guild_language)
                embed = discord.Embed(
                    title=title,
                    description=desc,
                    color=discord.Color.green()
                )
                
                await update_message.edit(content=None, embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description="Der Bot hat nicht die nötigen Berechtigungen, um Kategorien und Kanäle zu erstellen.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Fehler beim Einrichten der Statistik-Kanäle: {e}")
            embed = discord.Embed(
                title="❌ Fehler",
                description=f"Beim Einrichten der Statistik-Kanäle ist ein Fehler aufgetreten: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="removestats", description="Entfernt die Server-Statistik-Kanäle / Removes the server statistics channels", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def remove_stats(self, ctx: commands.Context):
        """
        Entfernt alle Statistik-Kanäle, die mit /setupstats erstellt wurden.
        """
        guild = ctx.guild
        guild_id = str(guild.id)
        
        # Überprüfen, ob Statistik-Kanäle eingerichtet sind
        if guild_id not in self.config["stats_channels"] or not self.config["stats_channels"][guild_id]:
            embed = discord.Embed(
                title="❌ Keine Statistiken eingerichtet",
                description="Es wurden keine Statistik-Kanäle für diesen Server eingerichtet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Serversprache abrufen
            guild_language = self.language_manager.get_guild_language(guild.id)
            
            # Sende eine Nachricht, dass die Entfernung begonnen hat
            status_text = self.language_manager.get_text("server_stats.stats_updating", guild_language)
            status_message = await ctx.send(status_text)
            
            # Kanalberechtigungen abrufen
            stats_channels = self.config["stats_channels"][guild_id]
            
            # Kategorie und Kanäle löschen
            channels_to_delete = [
                "category_id", "member_count_id", "online_count_id", 
                "text_channels_id", "voice_channels_id", "age_id", "top_role_id",
                "boost_count_id", "boost_level_id", "emoji_count_id", "roles_count_id"
            ]
            
            for channel_key in channels_to_delete:
                if channel_key in stats_channels:
                    channel_id = stats_channels[channel_key]
                    channel = guild.get_channel(channel_id)
                    if channel:
                        await channel.delete()
            
            # Konfiguration aktualisieren
            del self.config["stats_channels"][guild_id]
            self._save_config()
            
            # Status-Nachricht aktualisieren
            title = self.language_manager.get_text("server_stats.stats_removed_title", guild_language)
            desc = self.language_manager.get_text("server_stats.stats_removed_desc", guild_language)
            embed = discord.Embed(
                title=title,
                description=desc,
                color=discord.Color.green()
            )
            await status_message.edit(content=None, embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description="Der Bot hat nicht die nötigen Berechtigungen, um Kanäle zu löschen.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Fehler beim Entfernen der Statistik-Kanäle: {e}")
            embed = discord.Embed(
                title="❌ Fehler",
                description=f"Beim Entfernen der Statistik-Kanäle ist ein Fehler aufgetreten: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @tasks.loop(seconds=300)
    async def update_stats_task(self):
        """Aktualisiert regelmäßig die Statistik-Kanäle."""
        await self.bot.wait_until_ready()
        
        for guild_id, channels in self.config["stats_channels"].items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            
            try:
                # Nutze die gemeinsame Methode zum Aktualisieren aller Statistiken
                await self._update_stats_for_guild(guild, channels)
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren der Statistik-Kanäle für Server {guild.name}: {e}")
                # Wir aktualisieren trotzdem weiter, um nicht alle Server zu blockieren
                continue
    
    async def _update_stats_for_guild(self, guild, channels):
        """Aktualisiert alle Statistik-Kanäle für einen bestimmten Server."""
        # Holen der Serversprache
        guild_language = self.language_manager.get_guild_language(guild.id)
        
        # Mitgliederanzahl aktualisieren
        if "member_count_id" in channels:
            channel = guild.get_channel(channels["member_count_id"])
            if channel:
                text = self.language_manager.get_text("server_stats.members", guild_language, count=guild.member_count)
                await channel.edit(name=text)
        
        # Online-Mitglieder aktualisieren
        if "online_count_id" in channels:
            channel = guild.get_channel(channels["online_count_id"])
            if channel:
                online_members = sum(1 for member in guild.members if member.status != discord.Status.offline and not member.bot)
                text = self.language_manager.get_text("server_stats.online", guild_language, count=online_members)
                await channel.edit(name=text)
        
        # Textkanäle aktualisieren
        if "text_channels_id" in channels:
            channel = guild.get_channel(channels["text_channels_id"])
            if channel:
                text_channels = len(guild.text_channels)
                text = self.language_manager.get_text("server_stats.text_channels", guild_language, count=text_channels)
                await channel.edit(name=text)
        
        # Sprachkanäle aktualisieren
        if "voice_channels_id" in channels:
            channel = guild.get_channel(channels["voice_channels_id"])
            if channel:
                voice_channels = len(guild.voice_channels)
                text = self.language_manager.get_text("server_stats.voice_channels", guild_language, count=voice_channels)
                await channel.edit(name=text)
        
        # Server-Alter aktualisieren
        if "age_id" in channels:
            channel = guild.get_channel(channels["age_id"])
            if channel:
                server_created = guild.created_at
                days_since_creation = (datetime.datetime.now(datetime.timezone.utc) - server_created).days
                text = self.language_manager.get_text("server_stats.server_age", guild_language, days=days_since_creation)
                await channel.edit(name=text)
        
        # Häufigste Rolle aktualisieren
        if "top_role_id" in channels:
            channel = guild.get_channel(channels["top_role_id"])
            if channel:
                roles = [role for role in guild.roles if not role.is_default()]
                if roles:
                    roles.sort(key=lambda r: len(r.members), reverse=True)
                    top_role = roles[0]
                    text = self.language_manager.get_text("server_stats.top_role", guild_language, 
                                                         name=top_role.name, count=len(top_role.members))
                    await channel.edit(name=text)
                else:
                    text = self.language_manager.get_text("server_stats.top_role_none", guild_language)
                    await channel.edit(name=text)
        
        # Boost-Anzahl aktualisieren
        if "boost_count_id" in channels:
            channel = guild.get_channel(channels["boost_count_id"])
            if channel:
                text = self.language_manager.get_text("server_stats.boosts", guild_language, 
                                                     count=guild.premium_subscription_count)
                await channel.edit(name=text)
        
        # Boost-Level aktualisieren
        if "boost_level_id" in channels:
            channel = guild.get_channel(channels["boost_level_id"])
            if channel:
                text = self.language_manager.get_text("server_stats.boost_level", guild_language, 
                                                     level=guild.premium_tier)
                await channel.edit(name=text)
        
        # Emojis aktualisieren
        if "emoji_count_id" in channels:
            channel = guild.get_channel(channels["emoji_count_id"])
            if channel:
                text = self.language_manager.get_text("server_stats.emojis", guild_language, 
                                                     count=len(guild.emojis))
                await channel.edit(name=text)
        
        # Rollen aktualisieren
        if "roles_count_id" in channels:
            channel = guild.get_channel(channels["roles_count_id"])
            if channel:
                text = self.language_manager.get_text("server_stats.roles", guild_language, 
                                                     count=len(guild.roles) - 1)
                await channel.edit(name=text)
    
    @update_stats_task.before_loop
    async def before_update_stats(self):
        """Warte, bis der Bot bereit ist."""
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    """Füge den ServerStats-Cog zum Bot hinzu."""
    await bot.add_cog(ServerStats(bot))
    logger.info("ServerStats cog loaded")
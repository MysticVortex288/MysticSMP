import discord
import json
import logging
import asyncio
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, List, Dict, Union

logger = logging.getLogger('discord_bot')

class ChannelLocker(commands.Cog):
    """Cog zum Sperren von Kanälen für bestimmte Zeiträume."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.locked_channels = {}
        self._load_locked_channels()
        self.check_locked_channels.start()
        logger.info("ChannelLocker cog initialized")

    def cog_unload(self):
        """Wird aufgerufen, wenn der Cog entladen wird."""
        self.check_locked_channels.cancel()

    def _load_locked_channels(self):
        """Lädt die gesperrten Kanäle aus der Datei."""
        try:
            with open('locked_channels.json', 'r') as f:
                self.locked_channels = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.locked_channels = {}
            self._save_locked_channels()
        
        # Konvertiere Datum-Strings zu datetime-Objekten
        for guild_id, channels in self.locked_channels.items():
            for channel_id, data in channels.items():
                if 'unlock_date' in data and data['unlock_date']:
                    data['unlock_date'] = datetime.datetime.fromisoformat(data['unlock_date'])

    def _save_locked_channels(self):
        """Speichert die gesperrten Kanäle in der Datei."""
        # Konvertiere datetime-Objekte zu Strings
        serializable_data = {}
        for guild_id, channels in self.locked_channels.items():
            serializable_data[guild_id] = {}
            for channel_id, data in channels.items():
                serializable_data[guild_id][channel_id] = data.copy()
                if 'unlock_date' in data and isinstance(data['unlock_date'], datetime.datetime):
                    serializable_data[guild_id][channel_id]['unlock_date'] = data['unlock_date'].isoformat()

        with open('locked_channels.json', 'w') as f:
            json.dump(serializable_data, f, indent=4)

    @tasks.loop(minutes=5)
    async def check_locked_channels(self):
        """Überprüft regelmäßig, ob gesperrte Kanäle entsperrt werden müssen."""
        logger.info("Überprüfe gesperrte Kanäle...")
        now = datetime.datetime.now()
        
        # Für jede Guild
        for guild_id, channels in list(self.locked_channels.items()):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            # Für jeden Kanal in der Guild
            for channel_id, data in list(channels.items()):
                # Überprüfe, ob ein Entsperrdatum gesetzt ist
                if 'unlock_date' in data and data['unlock_date']:
                    unlock_date = data['unlock_date']
                    
                    # Wenn das Entsperrdatum erreicht ist
                    if now >= unlock_date:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            await self._unlock_channel(guild, channel, send_message=True)
        
        # Speichere die aktualisierte Konfiguration
        self._save_locked_channels()

    @check_locked_channels.before_loop
    async def before_check_locked_channels(self):
        """Wartet, bis der Bot bereit ist, bevor die Schleife gestartet wird."""
        await self.bot.wait_until_ready()

    async def _lock_channel(self, guild: discord.Guild, channel: discord.TextChannel, 
                          reason: str = None, unlock_date: datetime.datetime = None,
                          send_message: bool = True):
        """
        Sperrt einen Kanal für alle Mitglieder.
        
        Args:
            guild: Die Discord-Guild
            channel: Der zu sperrende Kanal
            reason: Grund für die Sperrung
            unlock_date: Datum, an dem der Kanal automatisch entsperrt werden soll
            send_message: Ob eine Nachricht im Kanal gesendet werden soll
        """
        # Speichere die ursprünglichen Berechtigungen für alle Rollen
        original_permissions = {}
        for role in guild.roles:
            # Ignoriere die @everyone-Rolle (wird separat behandelt)
            if role != guild.default_role:
                overwrite = channel.overwrites_for(role)
                original_permissions[role.id] = {
                    'send_messages': overwrite.send_messages
                }
        
        # Sperre den Kanal für die @everyone-Rolle
        everyone_overwrite = channel.overwrites_for(guild.default_role)
        everyone_overwrite.send_messages = False
        await channel.set_permissions(guild.default_role, overwrite=everyone_overwrite)
        
        # Speichere die Kanaldaten
        guild_id = str(guild.id)
        channel_id = str(channel.id)
        
        if guild_id not in self.locked_channels:
            self.locked_channels[guild_id] = {}
        
        self.locked_channels[guild_id][channel_id] = {
            'original_permissions': original_permissions,
            'reason': reason,
            'unlock_date': unlock_date,
            'locked_at': datetime.datetime.now().isoformat()
        }
        
        # Speichere die aktualisierte Konfiguration
        self._save_locked_channels()
        
        # Sende eine Nachricht im Kanal, wenn gewünscht
        if send_message:
            embed = discord.Embed(
                title="Kanal gesperrt",
                description=f"Dieser Kanal wurde gesperrt.",
                color=discord.Color.red()
            )
            
            if reason:
                embed.add_field(name="Grund", value=reason, inline=False)
            
            if unlock_date:
                embed.add_field(
                    name="Automatische Entsperrung", 
                    value=f"Dieser Kanal wird am {unlock_date.strftime('%d.%m.%Y um %H:%M')} Uhr automatisch entsperrt.",
                    inline=False
                )
            
            await channel.send(embed=embed)
        
        logger.info(f"Kanal {channel.name} in Guild {guild.name} gesperrt.")

    async def _unlock_channel(self, guild: discord.Guild, channel: discord.TextChannel, 
                            send_message: bool = True):
        """
        Entsperrt einen Kanal für alle Mitglieder.
        
        Args:
            guild: Die Discord-Guild
            channel: Der zu entsperrende Kanal
            send_message: Ob eine Nachricht im Kanal gesendet werden soll
        """
        guild_id = str(guild.id)
        channel_id = str(channel.id)
        
        # Überprüfe, ob der Kanal gesperrt ist
        if (guild_id not in self.locked_channels or 
            channel_id not in self.locked_channels[guild_id]):
            return
        
        # Stelle die ursprünglichen Berechtigungen wieder her
        original_permissions = self.locked_channels[guild_id][channel_id].get('original_permissions', {})
        
        # Entsperre den Kanal für die @everyone-Rolle
        everyone_overwrite = channel.overwrites_for(guild.default_role)
        everyone_overwrite.send_messages = None  # Zurücksetzen auf Standardwert
        await channel.set_permissions(guild.default_role, overwrite=everyone_overwrite)
        
        # Stelle die Berechtigungen für andere Rollen wieder her
        for role_id, permissions in original_permissions.items():
            role = guild.get_role(int(role_id))
            if role:
                overwrite = channel.overwrites_for(role)
                overwrite.send_messages = permissions.get('send_messages')
                await channel.set_permissions(role, overwrite=overwrite)
        
        # Entferne den Kanal aus der Sperrliste
        del self.locked_channels[guild_id][channel_id]
        
        # Entferne die Guild, wenn keine Kanäle mehr gesperrt sind
        if not self.locked_channels[guild_id]:
            del self.locked_channels[guild_id]
        
        # Speichere die aktualisierte Konfiguration
        self._save_locked_channels()
        
        # Sende eine Nachricht im Kanal, wenn gewünscht
        if send_message:
            embed = discord.Embed(
                title="Kanal entsperrt",
                description="Dieser Kanal wurde entsperrt.",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        
        logger.info(f"Kanal {channel.name} in Guild {guild.name} entsperrt.")

    @commands.hybrid_command(name="lock", description="Sperrt einen Kanal bis zu einem bestimmten Datum.", default_permission=False)
    @commands.has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_channels=True)
    async def lock_channel(self, ctx: commands.Context, 
                          channel: Optional[discord.TextChannel] = None,
                          *, reason: Optional[str] = None):
        """
        Sperrt einen Kanal, sodass nur noch Administratoren schreiben können.
        
        Args:
            channel: Der zu sperrende Kanal. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
            reason: Der Grund für die Sperrung.
        """
        if channel is None:
            channel = ctx.channel
        
        # Überprüfe, ob der Bot die nötigen Berechtigungen hat
        if not channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                "Ich habe nicht die nötigen Berechtigungen, um Kanäle zu sperren. "
                "Bitte gib mir die 'Kanäle verwalten'-Berechtigung."
            )
            return
        
        # Überprüfe, ob der Kanal bereits gesperrt ist
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id in self.locked_channels and 
            channel_id in self.locked_channels[guild_id]):
            await ctx.send(f"Der Kanal {channel.mention} ist bereits gesperrt.")
            return
        
        await self._lock_channel(ctx.guild, channel, reason=reason)
        
        # Bestätige die Aktion
        await ctx.send(f"Der Kanal {channel.mention} wurde gesperrt.")

    @commands.hybrid_command(name="unlock", description="Entsperrt einen Kanal.", default_permission=False)
    @commands.has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_channels=True)
    async def unlock_channel(self, ctx: commands.Context, 
                            channel: Optional[discord.TextChannel] = None):
        """
        Entsperrt einen Kanal.
        
        Args:
            channel: Der zu entsperrende Kanal. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        if channel is None:
            channel = ctx.channel
        
        # Überprüfe, ob der Bot die nötigen Berechtigungen hat
        if not channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                "Ich habe nicht die nötigen Berechtigungen, um Kanäle zu entsperren. "
                "Bitte gib mir die 'Kanäle verwalten'-Berechtigung."
            )
            return
        
        # Überprüfe, ob der Kanal gesperrt ist
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id not in self.locked_channels or 
            channel_id not in self.locked_channels[guild_id]):
            await ctx.send(f"Der Kanal {channel.mention} ist nicht gesperrt.")
            return
        
        await self._unlock_channel(ctx.guild, channel)
        
        # Bestätige die Aktion
        await ctx.send(f"Der Kanal {channel.mention} wurde entsperrt.")

    @commands.hybrid_command(name="lockuntil", description="Sperrt einen Kanal bis zu einem bestimmten Datum.", default_permission=False)
    @commands.has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_channels=True)
    async def lock_channel_until(self, ctx: commands.Context, 
                               channel: Optional[discord.TextChannel] = None,
                               date: str = None,
                               *, reason: Optional[str] = None):
        """
        Sperrt einen Kanal bis zu einem bestimmten Datum.
        
        Args:
            channel: Der zu sperrende Kanal. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
            date: Das Datum, an dem der Kanal entsperrt werden soll (Format: TT.MM.YYYY oder TT.MM.YYYY HH:MM).
            reason: Der Grund für die Sperrung.
        """
        if channel is None:
            channel = ctx.channel
        
        # Überprüfe, ob der Bot die nötigen Berechtigungen hat
        if not channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(
                "Ich habe nicht die nötigen Berechtigungen, um Kanäle zu sperren. "
                "Bitte gib mir die 'Kanäle verwalten'-Berechtigung."
            )
            return
        
        # Überprüfe, ob ein Datum angegeben wurde
        if date is None:
            await ctx.send("Bitte gib ein Datum an, an dem der Kanal entsperrt werden soll.")
            return
        
        # Versuche, das Datum zu parsen
        try:
            # Versuche verschiedene Datumsformate
            if ' ' in date:  # Format: TT.MM.YYYY HH:MM
                date_parts = date.split(' ')
                day_month_year = date_parts[0].split('.')
                hour_minute = date_parts[1].split(':')
                
                day = int(day_month_year[0])
                month = int(day_month_year[1])
                year = int(day_month_year[2])
                hour = int(hour_minute[0])
                minute = int(hour_minute[1])
                
                unlock_date = datetime.datetime(year, month, day, hour, minute)
            else:  # Format: TT.MM.YYYY
                day_month_year = date.split('.')
                day = int(day_month_year[0])
                month = int(day_month_year[1])
                year = int(day_month_year[2])
                
                unlock_date = datetime.datetime(year, month, day, 0, 0)
        except (ValueError, IndexError):
            await ctx.send(
                "Ungültiges Datumsformat. Bitte verwende das Format TT.MM.YYYY oder TT.MM.YYYY HH:MM. "
                "Beispiel: 31.12.2024 oder 31.12.2024 18:00"
            )
            return
        
        # Überprüfe, ob das Datum in der Zukunft liegt
        if unlock_date <= datetime.datetime.now():
            await ctx.send("Das Entsperrdatum muss in der Zukunft liegen.")
            return
        
        # Überprüfe, ob der Kanal bereits gesperrt ist
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id in self.locked_channels and 
            channel_id in self.locked_channels[guild_id]):
            await ctx.send(f"Der Kanal {channel.mention} ist bereits gesperrt.")
            return
        
        await self._lock_channel(ctx.guild, channel, reason=reason, unlock_date=unlock_date)
        
        # Bestätige die Aktion
        unlock_date_str = unlock_date.strftime('%d.%m.%Y um %H:%M')
        await ctx.send(f"Der Kanal {channel.mention} wurde gesperrt und wird am {unlock_date_str} Uhr automatisch entsperrt.")

    @commands.hybrid_command(name="lockedchannels", description="Zeigt eine Liste aller gesperrten Kanäle an.", default_permission=False)
    @commands.has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_channels=True)
    async def list_locked_channels(self, ctx: commands.Context):
        """
        Zeigt eine Liste aller gesperrten Kanäle an.
        """
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.locked_channels or 
            not self.locked_channels[guild_id]):
            await ctx.send("Es sind keine Kanäle gesperrt.")
            return
        
        embed = discord.Embed(
            title="Gesperrte Kanäle",
            description="Liste aller aktuell gesperrten Kanäle:",
            color=discord.Color.blue()
        )
        
        for channel_id, data in self.locked_channels[guild_id].items():
            channel = ctx.guild.get_channel(int(channel_id))
            if not channel:
                continue
                
            # Formatiere die Informationen
            info = ""
            if 'reason' in data and data['reason']:
                info += f"**Grund:** {data['reason']}\n"
                
            if 'unlock_date' in data and data['unlock_date']:
                unlock_date_str = data['unlock_date'].strftime('%d.%m.%Y um %H:%M')
                info += f"**Entsperrung:** {unlock_date_str} Uhr\n"
                
            if 'locked_at' in data:
                locked_at = datetime.datetime.fromisoformat(data['locked_at'])
                locked_at_str = locked_at.strftime('%d.%m.%Y um %H:%M')
                info += f"**Gesperrt am:** {locked_at_str} Uhr\n"
                
            if not info:
                info = "Keine weiteren Informationen verfügbar."
                
            embed.add_field(name=f"#{channel.name}", value=info, inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="lockall", description="Sperrt alle Textkanäle auf dem Server.", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def lock_all_channels(self, ctx: commands.Context, 
                               date: Optional[str] = None,
                               *, reason: Optional[str] = None):
        """
        Sperrt alle Textkanäle auf dem Server.
        
        Args:
            date: Das Datum, an dem die Kanäle entsperrt werden sollen (Format: TT.MM.YYYY oder TT.MM.YYYY HH:MM).
            reason: Der Grund für die Sperrung.
        """
        # Parsen des Datums, wenn angegeben
        unlock_date = None
        if date:
            try:
                # Versuche verschiedene Datumsformate
                if ' ' in date:  # Format: TT.MM.YYYY HH:MM
                    date_parts = date.split(' ')
                    day_month_year = date_parts[0].split('.')
                    hour_minute = date_parts[1].split(':')
                    
                    day = int(day_month_year[0])
                    month = int(day_month_year[1])
                    year = int(day_month_year[2])
                    hour = int(hour_minute[0])
                    minute = int(hour_minute[1])
                    
                    unlock_date = datetime.datetime(year, month, day, hour, minute)
                else:  # Format: TT.MM.YYYY
                    day_month_year = date.split('.')
                    day = int(day_month_year[0])
                    month = int(day_month_year[1])
                    year = int(day_month_year[2])
                    
                    unlock_date = datetime.datetime(year, month, day, 0, 0)
                
                # Überprüfe, ob das Datum in der Zukunft liegt
                if unlock_date <= datetime.datetime.now():
                    await ctx.send("Das Entsperrdatum muss in der Zukunft liegen.")
                    return
            except (ValueError, IndexError):
                await ctx.send(
                    "Ungültiges Datumsformat. Bitte verwende das Format TT.MM.YYYY oder TT.MM.YYYY HH:MM. "
                    "Beispiel: 31.12.2024 oder 31.12.2024 18:00"
                )
                return
        
        # Bestätigungsnachricht senden
        confirm_embed = discord.Embed(
            title="Kanalsperrung bestätigen",
            description=f"Möchtest du wirklich alle Textkanäle auf dem Server sperren?",
            color=discord.Color.orange()
        )
        
        if unlock_date:
            unlock_date_str = unlock_date.strftime('%d.%m.%Y um %H:%M')
            confirm_embed.add_field(
                name="Automatische Entsperrung", 
                value=f"Alle Kanäle werden am {unlock_date_str} Uhr automatisch entsperrt.",
                inline=False
            )
        
        if reason:
            confirm_embed.add_field(name="Grund", value=reason, inline=False)
        
        # Buttons für die Bestätigung
        confirm_view = discord.ui.View(timeout=60)
        
        # Ja-Button
        @discord.ui.button(label="Ja", style=discord.ButtonStyle.danger)
        async def confirm_button(interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Du kannst diese Aktion nicht bestätigen.", ephemeral=True)
                return
                
            # Deaktiviere die Buttons
            for child in confirm_view.children:
                child.disabled = True
            
            # Aktualisiere die ursprüngliche Nachricht
            await interaction.response.edit_message(view=confirm_view)
            
            # Zähler für gesperrte Kanäle
            locked_count = 0
            
            # Status-Nachricht
            status_message = await ctx.send("Sperre Kanäle... (0%)")
            
            # Alle Textkanäle sperren
            text_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel)]
            total_channels = len(text_channels)
            
            for i, channel in enumerate(text_channels):
                # Überprüfe, ob der Kanal bereits gesperrt ist
                guild_id = str(ctx.guild.id)
                channel_id = str(channel.id)
                
                if (guild_id in self.locked_channels and 
                    channel_id in self.locked_channels[guild_id]):
                    continue
                
                # Überprüfe, ob der Bot die nötigen Berechtigungen hat
                if not channel.permissions_for(ctx.guild.me).manage_channels:
                    continue
                
                await self._lock_channel(
                    ctx.guild, 
                    channel, 
                    reason=reason, 
                    unlock_date=unlock_date,
                    send_message=i == 0  # Nur im ersten Kanal eine Nachricht senden
                )
                
                locked_count += 1
                
                # Status-Nachricht alle 5 Kanäle aktualisieren
                if (i + 1) % 5 == 0 or i == total_channels - 1:
                    progress = int((i + 1) / total_channels * 100)
                    await status_message.edit(content=f"Sperre Kanäle... ({progress}%)")
            
            # Abschlussnachricht
            final_message = f"{locked_count} Kanäle wurden gesperrt."
            if unlock_date:
                unlock_date_str = unlock_date.strftime('%d.%m.%Y um %H:%M')
                final_message += f" Sie werden am {unlock_date_str} Uhr automatisch entsperrt."
                
            await status_message.edit(content=final_message)
        
        # Nein-Button
        @discord.ui.button(label="Nein", style=discord.ButtonStyle.secondary)
        async def cancel_button(interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Du kannst diese Aktion nicht abbrechen.", ephemeral=True)
                return
                
            # Deaktiviere die Buttons
            for child in confirm_view.children:
                child.disabled = True
            
            # Aktualisiere die ursprüngliche Nachricht
            await interaction.response.edit_message(content="Kanalsperrung abgebrochen.", embed=None, view=confirm_view)
        
        # Füge die Buttons zur View hinzu
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        # Sende die Bestätigungsnachricht
        await ctx.send(embed=confirm_embed, view=confirm_view)

    @commands.hybrid_command(name="unlockall", description="Entsperrt alle gesperrten Textkanäle auf dem Server.", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def unlock_all_channels(self, ctx: commands.Context):
        """
        Entsperrt alle gesperrten Textkanäle auf dem Server.
        """
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.locked_channels or 
            not self.locked_channels[guild_id]):
            await ctx.send("Es sind keine Kanäle gesperrt.")
            return
        
        # Bestätigungsnachricht senden
        confirm_embed = discord.Embed(
            title="Kanalentspperrung bestätigen",
            description=f"Möchtest du wirklich alle gesperrten Kanäle auf dem Server entsperren?",
            color=discord.Color.orange()
        )
        
        # Buttons für die Bestätigung
        confirm_view = discord.ui.View(timeout=60)
        
        # Ja-Button
        @discord.ui.button(label="Ja", style=discord.ButtonStyle.danger)
        async def confirm_button(interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Du kannst diese Aktion nicht bestätigen.", ephemeral=True)
                return
                
            # Deaktiviere die Buttons
            for child in confirm_view.children:
                child.disabled = True
            
            # Aktualisiere die ursprüngliche Nachricht
            await interaction.response.edit_message(view=confirm_view)
            
            # Zähler für entsperrte Kanäle
            unlocked_count = 0
            
            # Status-Nachricht
            status_message = await ctx.send("Entsperre Kanäle... (0%)")
            
            # Alle gesperrten Kanäle entsperren
            locked_channels = list(self.locked_channels.get(guild_id, {}).items())
            total_channels = len(locked_channels)
            
            for i, (channel_id, _) in enumerate(locked_channels):
                channel = ctx.guild.get_channel(int(channel_id))
                if not channel:
                    continue
                
                # Überprüfe, ob der Bot die nötigen Berechtigungen hat
                if not channel.permissions_for(ctx.guild.me).manage_channels:
                    continue
                
                await self._unlock_channel(
                    ctx.guild, 
                    channel,
                    send_message=i == 0  # Nur im ersten Kanal eine Nachricht senden
                )
                
                unlocked_count += 1
                
                # Status-Nachricht alle 5 Kanäle aktualisieren
                if (i + 1) % 5 == 0 or i == total_channels - 1:
                    progress = int((i + 1) / total_channels * 100)
                    await status_message.edit(content=f"Entsperre Kanäle... ({progress}%)")
            
            # Abschlussnachricht
            await status_message.edit(content=f"{unlocked_count} Kanäle wurden entsperrt.")
        
        # Nein-Button
        @discord.ui.button(label="Nein", style=discord.ButtonStyle.secondary)
        async def cancel_button(interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Du kannst diese Aktion nicht abbrechen.", ephemeral=True)
                return
                
            # Deaktiviere die Buttons
            for child in confirm_view.children:
                child.disabled = True
            
            # Aktualisiere die ursprüngliche Nachricht
            await interaction.response.edit_message(content="Kanalentspperrung abgebrochen.", embed=None, view=confirm_view)
        
        # Füge die Buttons zur View hinzu
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        # Sende die Bestätigungsnachricht
        await ctx.send(embed=confirm_embed, view=confirm_view)

async def setup(bot: commands.Bot):
    """Fügt den ChannelLocker-Cog zum Bot hinzu."""
    await bot.add_cog(ChannelLocker(bot))
    logger.info("ChannelLocker cog loaded")
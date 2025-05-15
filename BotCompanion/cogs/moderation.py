import discord
from discord.ext import commands
import asyncio
import json
import logging
import datetime
from typing import Optional, Union, Dict, List
from datetime import timedelta

logger = logging.getLogger('discord_bot')

class ModAction:
    """Klasse für eine einzelne Moderationsaktion."""
    def __init__(self, 
                 action_type: str, 
                 user_id: int, 
                 moderator_id: int, 
                 reason: str, 
                 timestamp: datetime.datetime,
                 duration: Optional[int] = None,
                 case_id: Optional[int] = None,
                 guild_id: Optional[int] = None):
        self.action_type = action_type
        self.user_id = user_id
        self.moderator_id = moderator_id
        self.reason = reason
        self.timestamp = timestamp
        self.duration = duration  # in Sekunden
        self.case_id = case_id
        self.guild_id = guild_id
    
    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type,
            "user_id": self.user_id,
            "moderator_id": self.moderator_id,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "case_id": self.case_id,
            "guild_id": self.guild_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModAction':
        return cls(
            action_type=data["action_type"],
            user_id=data["user_id"],
            moderator_id=data["moderator_id"],
            reason=data["reason"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            duration=data.get("duration"),
            case_id=data.get("case_id"),
            guild_id=data.get("guild_id")
        )

class Moderation(commands.Cog):
    """Cog für Moderationsbefehle wie kick, ban, mute und warn."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.mod_log_channels = {}  # Server-ID zu Kanal-ID
        self.mod_actions = {}  # Server-ID zu Liste von Mod-Aktionen
        self.case_counts = {}  # Server-ID zu aktueller Fallnummer
        self._load_data()
    
    def _load_data(self):
        """Lade Moderationsdaten aus Datei."""
        try:
            with open('moderation.json', 'r') as f:
                data = json.load(f)
                self.mod_log_channels = data.get("log_channels", {})
                self.case_counts = data.get("case_counts", {})
                
                # Konvertiere IDs zu Strings
                self.mod_log_channels = {str(k): v for k, v in self.mod_log_channels.items()}
                self.case_counts = {str(k): v for k, v in self.case_counts.items()}
                
                # Lade Mod-Aktionen
                actions_data = data.get("actions", {})
                self.mod_actions = {}
                for guild_id, actions in actions_data.items():
                    self.mod_actions[guild_id] = [ModAction.from_dict(action) for action in actions]
                    
                logger.info("Moderationsdaten geladen")
        except (FileNotFoundError, json.JSONDecodeError):
            self.mod_log_channels = {}
            self.mod_actions = {}
            self.case_counts = {}
            logger.info("Keine vorhandenen Moderationsdaten gefunden, starte mit leeren Daten")
            self._save_data()
    
    def _save_data(self):
        """Speichere Moderationsdaten in Datei."""
        data = {
            "log_channels": self.mod_log_channels,
            "case_counts": self.case_counts,
            "actions": {}
        }
        
        # Konvertiere Mod-Aktionen zu serialisierbarem Format
        for guild_id, actions in self.mod_actions.items():
            data["actions"][guild_id] = [action.to_dict() for action in actions]
        
        with open('moderation.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    def _get_next_case_id(self, guild_id: int) -> int:
        """Holt die nächste Fallnummer für eine Moderationsaktion."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.case_counts:
            self.case_counts[guild_id_str] = 0
            
        self.case_counts[guild_id_str] += 1
        self._save_data()
        return self.case_counts[guild_id_str]
    
    def _add_mod_action(self, 
                       guild_id: int, 
                       action_type: str, 
                       user_id: int, 
                       moderator_id: int, 
                       reason: str, 
                       duration: Optional[int] = None) -> ModAction:
        """Fügt eine Moderationsaktion hinzu und speichert sie."""
        guild_id_str = str(guild_id)
        
        if guild_id_str not in self.mod_actions:
            self.mod_actions[guild_id_str] = []
            
        # Erstelle die Aktion mit einer neuen Fallnummer
        case_id = self._get_next_case_id(guild_id)
        action = ModAction(
            action_type=action_type,
            user_id=user_id,
            moderator_id=moderator_id,
            reason=reason,
            timestamp=datetime.datetime.utcnow(),
            duration=duration,
            case_id=case_id,
            guild_id=guild_id
        )
        
        self.mod_actions[guild_id_str].append(action)
        self._save_data()
        return action
    
    async def _send_mod_log(self, guild: discord.Guild, action: ModAction, user: discord.User) -> Optional[discord.Message]:
        """Sendet einen Logeintrag in den Moderationskanal, falls konfiguriert."""
        guild_id_str = str(guild.id)
        if guild_id_str not in self.mod_log_channels:
            return None
            
        channel_id = self.mod_log_channels[guild_id_str]
        channel = guild.get_channel(channel_id)
        
        if not channel:
            logger.warning(f"Moderations-Logkanal {channel_id} nicht gefunden in Guild {guild.name}")
            return None
            
        moderator = guild.get_member(action.moderator_id) or await self.bot.fetch_user(action.moderator_id)
        
        embed = discord.Embed(
            title=f"Moderation: {action.action_type.capitalize()}",
            description=f"**Benutzer:** {user} ({user.id})\n**Moderator:** {moderator.mention}\n**Grund:** {action.reason}",
            color=self._get_action_color(action.action_type),
            timestamp=action.timestamp
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Fall #{action.case_id}")
        
        if action.duration:
            duration_str = self._format_duration(action.duration)
            embed.add_field(name="Dauer", value=duration_str, inline=True)
            
            # Berechne Ablaufzeit
            expiry_time = action.timestamp + timedelta(seconds=action.duration)
            embed.add_field(name="Läuft ab", value=f"<t:{int(expiry_time.timestamp())}:R>", inline=True)
        
        try:
            return await channel.send(embed=embed)
        except discord.Forbidden:
            logger.error(f"Keine Berechtigung zum Senden in Kanal {channel.name} in Guild {guild.name}")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Senden des Mod-Logs: {e}")
            return None
    
    def _get_action_color(self, action_type: str) -> discord.Color:
        """Gibt die passende Farbe für den Aktionstyp zurück."""
        colors = {
            "warn": discord.Color.gold(),
            "mute": discord.Color.orange(),
            "kick": discord.Color.dark_orange(),
            "ban": discord.Color.red(),
            "unban": discord.Color.green(),
            "unmute": discord.Color.green()
        }
        return colors.get(action_type.lower(), discord.Color.blurple())
    
    def _format_duration(self, seconds: int) -> str:
        """Formatiert eine Dauer in Sekunden in ein lesbares Format."""
        if seconds is None:
            return "Permanent"
            
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0:
            parts.append(f"{days} Tag{'e' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} Stunde{'n' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} Minute{'n' if minutes != 1 else ''}")
        if seconds > 0 and not parts:  # Nur Sekunden anzeigen, wenn keine größere Einheit vorhanden ist
            parts.append(f"{seconds} Sekunde{'n' if seconds != 1 else ''}")
            
        return ", ".join(parts)
    
    async def _send_dm_notification(self, user: discord.User, action_type: str, guild_name: str, 
                                  reason: str, moderator: discord.Member = None, 
                                  duration: Optional[int] = None) -> bool:
        """Sendet eine DM-Benachrichtigung an den Benutzer über die Moderationsaktion."""
        action_messages = {
            "warn": f"Du wurdest auf **{guild_name}** verwarnt.",
            "mute": f"Du wurdest auf **{guild_name}** stummgeschaltet.",
            "kick": f"Du wurdest von **{guild_name}** gekickt.",
            "ban": f"Du wurdest von **{guild_name}** gebannt."
        }
        
        base_message = action_messages.get(action_type.lower(), f"Es wurde eine Moderationsaktion gegen dich auf **{guild_name}** durchgeführt.")
        
        embed = discord.Embed(
            title=f"Moderation: {action_type.capitalize()}",
            description=base_message,
            color=self._get_action_color(action_type),
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.add_field(name="Grund", value=reason or "Kein Grund angegeben", inline=False)
        
        if moderator:
            embed.add_field(name="Moderator", value=f"{moderator.name}", inline=True)
        
        if duration:
            duration_str = self._format_duration(duration)
            embed.add_field(name="Dauer", value=duration_str, inline=True)
            
            # Berechne Ablaufzeit
            expiry_time = datetime.datetime.utcnow() + timedelta(seconds=duration)
            embed.add_field(name="Läuft ab", value=f"<t:{int(expiry_time.timestamp())}:R>", inline=True)
        
        try:
            await user.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(f"Konnte DM nicht an {user} senden")
            return False
    
    async def _send_mod_notification(self, moderator: discord.Member, action: ModAction, target_user: discord.User) -> bool:
        """Sendet eine DM-Benachrichtigung an den Moderator über die durchgeführte Aktion."""
        embed = discord.Embed(
            title=f"Moderation: {action.action_type.capitalize()} durchgeführt",
            description=f"Du hast folgende Moderationsaktion durchgeführt:",
            color=self._get_action_color(action.action_type),
            timestamp=action.timestamp
        )
        
        embed.add_field(name="Benutzer", value=f"{target_user} ({target_user.id})", inline=False)
        embed.add_field(name="Grund", value=action.reason or "Kein Grund angegeben", inline=False)
        embed.set_footer(text=f"Fall #{action.case_id}")
        
        if action.duration:
            duration_str = self._format_duration(action.duration)
            embed.add_field(name="Dauer", value=duration_str, inline=True)
        
        try:
            await moderator.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(f"Konnte DM nicht an Moderator {moderator} senden")
            return False
    
    @commands.hybrid_command(name="setmodlog", description="Legt den Kanal für Moderationslog-Nachrichten fest")
    @commands.has_permissions(administrator=True)
    async def set_mod_log(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Legt den Kanal für Moderationslog-Nachrichten fest.
        
        Args:
            channel: Der Kanal, in dem Moderationslogs gesendet werden sollen. Wenn nicht angegeben, wird der aktuelle Kanal verwendet.
        """
        if not channel:
            channel = ctx.channel
            
        # Überprüfe Berechtigungen
        if not channel.permissions_for(ctx.guild.me).send_messages or not channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(f"❌ Ich benötige die Berechtigungen `Nachrichten senden` und `Links einbetten` in {channel.mention}.")
            return
        
        # Setze den Kanal
        self.mod_log_channels[str(ctx.guild.id)] = channel.id
        self._save_data()
        
        await ctx.send(f"✅ Moderationslog-Kanal wurde auf {channel.mention} gesetzt.")
    
    @commands.hybrid_command(name="warn", description="Verwarnt einen Benutzer")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
        """
        Verwarnt einen Benutzer und sendet ihm eine Benachrichtigung.
        
        Args:
            member: Der zu verwarnende Benutzer
            reason: Der Grund für die Verwarnung
        """
        # Überprüfe Berechtigungen & Hierarchie
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Du kannst keine Benutzer verwarnen, die eine höhere oder gleiche Rolle wie du haben.")
            return
            
        if member.bot:
            await ctx.send("❌ Bots können nicht verwarnt werden.")
            return
        
        # Füge die Warnung hinzu
        action = self._add_mod_action(
            guild_id=ctx.guild.id,
            action_type="warn",
            user_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason
        )
        
        # Sende Benachrichtigungen
        dm_sent = await self._send_dm_notification(
            user=member, 
            action_type="warn",
            guild_name=ctx.guild.name,
            reason=reason,
            moderator=ctx.author
        )
        
        # Sende Bestätigung im Kanal
        response = f"✅ **{member}** wurde verwarnt."
        if not dm_sent:
            response += "\n⚠️ Konnte keine DM an den Benutzer senden."
            
        await ctx.send(response)
        
        # Sende den Mod-Log
        await self._send_mod_log(ctx.guild, action, member)
        
        # Informiere den Moderator
        await self._send_mod_notification(ctx.author, action, member)
    
    @commands.hybrid_command(name="kick", description="Kickt einen Benutzer vom Server")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
        """
        Kickt einen Benutzer vom Server.
        
        Args:
            member: Der zu kickende Benutzer
            reason: Der Grund für den Kick
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Mitglieder zu kicken.")
            return
            
        # Überprüfe Hierarchie
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Du kannst keine Benutzer kicken, die eine höhere oder gleiche Rolle wie du haben.")
            return
            
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ Ich kann keine Benutzer kicken, die eine höhere oder gleiche Rolle wie ich haben.")
            return
            
        if member.bot and member.bot_id == self.bot.user.id:
            await ctx.send("❌ Ich kann mich nicht selbst kicken.")
            return
            
        if member.id == ctx.guild.owner_id:
            await ctx.send("❌ Der Serverbesitzer kann nicht gekickt werden.")
            return
        
        # Sende eine DM vor dem Kick
        dm_sent = await self._send_dm_notification(
            user=member, 
            action_type="kick",
            guild_name=ctx.guild.name,
            reason=reason,
            moderator=ctx.author
        )
        
        # Führe den Kick aus
        try:
            await member.kick(reason=f"{ctx.author}: {reason}")
            
            # Füge die Aktion hinzu
            action = self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="kick",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=reason
            )
            
            # Sende Bestätigung im Kanal
            response = f"✅ **{member}** wurde vom Server gekickt."
            if not dm_sent:
                response += "\n⚠️ Konnte keine DM an den Benutzer senden."
                
            await ctx.send(response)
            
            # Sende den Mod-Log
            await self._send_mod_log(ctx.guild, action, member)
            
            # Informiere den Moderator
            await self._send_mod_notification(ctx.author, action, member)
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, diesen Benutzer zu kicken.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Kicken des Benutzers: {e}")
    
    @commands.hybrid_command(name="ban", description="Bannt einen Benutzer vom Server")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, user: discord.User, delete_days: Optional[int] = 0, *, reason: str = "Kein Grund angegeben"):
        """
        Bannt einen Benutzer vom Server.
        
        Args:
            user: Der zu bannende Benutzer
            delete_days: Anzahl der Tage, für die Nachrichten gelöscht werden sollen (0-7)
            reason: Der Grund für den Bann
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Mitglieder zu bannen.")
            return
            
        # Begrenze delete_days auf 0-7 Tage
        delete_days = max(0, min(delete_days, 7))
        
        # Überprüfe, ob der Benutzer ein Mitglied des Servers ist
        member = ctx.guild.get_member(user.id)
        
        if member:
            # Überprüfe Hierarchie, wenn der Benutzer auf dem Server ist
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ Du kannst keine Benutzer bannen, die eine höhere oder gleiche Rolle wie du haben.")
                return
                
            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send("❌ Ich kann keine Benutzer bannen, die eine höhere oder gleiche Rolle wie ich haben.")
                return
                
            if member.id == ctx.guild.owner_id:
                await ctx.send("❌ Der Serverbesitzer kann nicht gebannt werden.")
                return
                
            if member.bot and member.id == self.bot.user.id:
                await ctx.send("❌ Ich kann mich nicht selbst bannen.")
                return
        
        # Sende eine DM vor dem Bann
        dm_sent = False
        if member:
            dm_sent = await self._send_dm_notification(
                user=user, 
                action_type="ban",
                guild_name=ctx.guild.name,
                reason=reason,
                moderator=ctx.author
            )
        
        # Führe den Bann aus
        try:
            await ctx.guild.ban(user, delete_message_days=delete_days, reason=f"{ctx.author}: {reason}")
            
            # Füge die Aktion hinzu
            action = self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="ban",
                user_id=user.id,
                moderator_id=ctx.author.id,
                reason=reason
            )
            
            # Sende Bestätigung im Kanal
            response = f"✅ **{user}** wurde vom Server gebannt."
            if member and not dm_sent:
                response += "\n⚠️ Konnte keine DM an den Benutzer senden."
                
            await ctx.send(response)
            
            # Sende den Mod-Log
            await self._send_mod_log(ctx.guild, action, user)
            
            # Informiere den Moderator
            await self._send_mod_notification(ctx.author, action, user)
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, diesen Benutzer zu bannen.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Bannen des Benutzers: {e}")
    
    @commands.hybrid_command(name="unban", description="Entbannt einen Benutzer vom Server")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "Kein Grund angegeben"):
        """
        Entbannt einen Benutzer vom Server.
        
        Args:
            user_id: Die ID des zu entbannenden Benutzers
            reason: Der Grund für die Entbannung
        """
        # Überprüfe, ob die Benutzer-ID gültig ist
        try:
            user_id = int(user_id.strip())
        except ValueError:
            await ctx.send("❌ Ungültige Benutzer-ID. Bitte gib eine gültige ID ein.")
            return
        
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Bans aufzuheben.")
            return
        
        # Versuche, den Benutzer zu entbannen
        try:
            # Hole den User über die API
            user = None
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send("❌ Kein Benutzer mit dieser ID gefunden.")
                return
            
            # Hole die Ban-Liste
            banned_users = [entry.user async for entry in ctx.guild.bans()]
            if user not in banned_users:
                await ctx.send("❌ Dieser Benutzer ist nicht gebannt.")
                return
            
            # Entbanne den Benutzer
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
            
            # Füge die Aktion hinzu
            action = self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="unban",
                user_id=user_id,
                moderator_id=ctx.author.id,
                reason=reason
            )
            
            # Sende Bestätigung im Kanal
            await ctx.send(f"✅ **{user}** wurde entbannt.")
            
            # Sende den Mod-Log
            await self._send_mod_log(ctx.guild, action, user)
            
            # Informiere den Moderator
            await self._send_mod_notification(ctx.author, action, user)
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Bans aufzuheben.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Entbannen des Benutzers: {e}")
    
    @commands.hybrid_command(name="mute", description="Schaltet einen Benutzer für eine bestimmte Zeit stumm")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "Kein Grund angegeben"):
        """
        Schaltet einen Benutzer stumm (Timeout).
        
        Args:
            member: Der stummzuschaltende Benutzer
            duration: Die Dauer der Stummschaltung (Beispiele: 10s, 5m, 1h, 7d)
            reason: Der Grund für die Stummschaltung
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Mitglieder zu verwalten.")
            return
            
        # Überprüfe Hierarchie
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Du kannst keine Benutzer stummschalten, die eine höhere oder gleiche Rolle wie du haben.")
            return
            
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ Ich kann keine Benutzer stummschalten, die eine höhere oder gleiche Rolle wie ich haben.")
            return
            
        if member.id == ctx.guild.owner_id:
            await ctx.send("❌ Der Serverbesitzer kann nicht stummgeschaltet werden.")
            return
            
        if member.bot:
            await ctx.send("❌ Bots können nicht stummgeschaltet werden.")
            return
        
        # Parse die Dauer
        seconds = 0
        try:
            seconds = self._parse_duration(duration)
        except ValueError:
            await ctx.send("❌ Ungültiges Dauerformat. Beispiele: 10s, 5m, 1h, 7d")
            return
            
        if seconds <= 0:
            await ctx.send("❌ Die Dauer muss positiv sein.")
            return
            
        if seconds > 60 * 60 * 24 * 28:  # Discord's maximum timeout is 28 days
            await ctx.send("❌ Die maximale Dauer für einen Timeout beträgt 28 Tage.")
            return
        
        # Berechne die Ablaufzeit
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        
        # Sende eine DM vor dem Timeout
        dm_sent = await self._send_dm_notification(
            user=member, 
            action_type="mute",
            guild_name=ctx.guild.name,
            reason=reason,
            moderator=ctx.author,
            duration=seconds
        )
        
        # Führe den Timeout aus
        try:
            await member.timeout(until, reason=f"{ctx.author}: {reason}")
            
            # Füge die Aktion hinzu
            action = self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="mute",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=reason,
                duration=seconds
            )
            
            # Sende Bestätigung im Kanal
            response = f"✅ **{member}** wurde für {self._format_duration(seconds)} stummgeschaltet."
            if not dm_sent:
                response += "\n⚠️ Konnte keine DM an den Benutzer senden."
                
            await ctx.send(response)
            
            # Sende den Mod-Log
            await self._send_mod_log(ctx.guild, action, member)
            
            # Informiere den Moderator
            await self._send_mod_notification(ctx.author, action, member)
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, diesen Benutzer stummzuschalten.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Stummschalten des Benutzers: {e}")
    
    @commands.hybrid_command(name="unmute", description="Hebt die Stummschaltung eines Benutzers auf")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Kein Grund angegeben"):
        """
        Hebt die Stummschaltung eines Benutzers auf.
        
        Args:
            member: Der Benutzer, dessen Stummschaltung aufgehoben werden soll
            reason: Der Grund für die Aufhebung
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Mitglieder zu verwalten.")
            return
            
        # Überprüfe, ob der Benutzer stummgeschaltet ist
        if member.timed_out_until is None or member.timed_out_until < discord.utils.utcnow():
            await ctx.send("❌ Dieser Benutzer ist nicht stummgeschaltet.")
            return
        
        # Hebe den Timeout auf
        try:
            await member.timeout(None, reason=f"{ctx.author}: {reason}")
            
            # Füge die Aktion hinzu
            action = self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="unmute",
                user_id=member.id,
                moderator_id=ctx.author.id,
                reason=reason
            )
            
            # Sende eine DM zur Information
            await self._send_dm_notification(
                user=member, 
                action_type="unmute",
                guild_name=ctx.guild.name,
                reason=reason,
                moderator=ctx.author
            )
            
            # Sende Bestätigung im Kanal
            await ctx.send(f"✅ Die Stummschaltung von **{member}** wurde aufgehoben.")
            
            # Sende den Mod-Log
            await self._send_mod_log(ctx.guild, action, member)
            
            # Informiere den Moderator
            await self._send_mod_notification(ctx.author, action, member)
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, die Stummschaltung dieses Benutzers aufzuheben.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Aufheben der Stummschaltung: {e}")
    
    @commands.hybrid_command(name="clear", description="Löscht eine bestimmte Anzahl von Nachrichten")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx: commands.Context, amount: int):
        """
        Löscht eine bestimmte Anzahl von Nachrichten aus dem aktuellen Kanal.
        
        Args:
            amount: Die Anzahl der zu löschenden Nachrichten (1-100)
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.manage_messages:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Nachrichten zu löschen.")
            return
            
        # Beschränke die Anzahl auf 1-100
        amount = max(1, min(amount, 100))
        
        # Lösche die Nachrichten
        try:
            # Wenn der Befehl über einen Slash-Befehl aufgerufen wurde
            if ctx.interaction:
                await ctx.send(f"🧹 Lösche {amount} Nachrichten...", ephemeral=True)
                await asyncio.sleep(1)  # Kurze Verzögerung, damit die Bestätigung sichtbar ist
                deleted = await ctx.channel.purge(limit=amount)
            else:
                # Bei normalen Textbefehlen, ignoriere die Befehlsnachricht
                deleted = await ctx.channel.purge(limit=amount + 1)
                
            # Sende eine Bestätigung, die nach 5 Sekunden verschwindet
            confirm_msg = await ctx.send(f"✅ **{len(deleted)}** Nachrichten wurden gelöscht.")
            await asyncio.sleep(5)
            try:
                await confirm_msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
                
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Nachrichten zu löschen.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Löschen der Nachrichten: {e}")
            
        # Füge die Aktion hinzu
        self._add_mod_action(
            guild_id=ctx.guild.id,
            action_type="clear",
            user_id=ctx.author.id,  # Benutzer-ID ist hier der Moderator selbst
            moderator_id=ctx.author.id,
            reason=f"{amount} Nachrichten in #{ctx.channel.name} gelöscht"
        )
            
    @commands.hybrid_command(name="allclear", description="Löscht alle Nachrichten in einem Kanal")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def allclear(self, ctx: commands.Context, confirmation: str = None):
        """
        Löscht alle Nachrichten in einem Kanal, indem der Kanal geklont und der ursprüngliche gelöscht wird.
        
        Args:
            confirmation: Bestätigung mit 'confirm', um versehentliches Löschen zu vermeiden
        """
        # Überprüfe Berechtigungen des Bots
        if not ctx.guild.me.guild_permissions.manage_channels:
            await ctx.send("❌ Ich habe nicht die Berechtigung, Kanäle zu verwalten.")
            return
            
        # Bestätigung verlangen
        if confirmation != "confirm":
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Warnung: Alle Nachrichten löschen",
                    description=
                        f"Diese Aktion löscht **ALLE** Nachrichten in {ctx.channel.mention}!\n\n"
                        f"Führe `/allclear confirm` aus, um fortzufahren.",
                    color=discord.Color.red()
                )
            )
            return
            
        # Bestätigungsnachricht
        await ctx.send("🧹 Lösche alle Nachrichten... Dies kann einen Moment dauern.")
        
        try:
            # Speichere die Kanaleigenschaften
            channel_position = ctx.channel.position
            channel_category = ctx.channel.category
            channel_permissions = ctx.channel.overwrites
            channel_name = ctx.channel.name
            channel_topic = getattr(ctx.channel, 'topic', None)
            channel_slowmode = ctx.channel.slowmode_delay
            
            # Erstelle einen neuen Kanal
            new_channel = await ctx.channel.clone(reason=f"Allclear durch {ctx.author}")
            await new_channel.edit(
                position=channel_position,
                category=channel_category,
                slowmode_delay=channel_slowmode
            )
            
            if channel_topic:
                await new_channel.edit(topic=channel_topic)
            
            # Lösche den alten Kanal
            await ctx.channel.delete(reason=f"Allclear durch {ctx.author}")
            
            # Sende eine Bestätigung im neuen Kanal
            await new_channel.send(
                embed=discord.Embed(
                    title="🧹 Kanal geleert",
                    description=f"Alle Nachrichten in diesem Kanal wurden von {ctx.author.mention} gelöscht.",
                    color=discord.Color.green()
                )
            )
            
            # Füge die Aktion hinzu
            self._add_mod_action(
                guild_id=ctx.guild.id,
                action_type="allclear",
                user_id=ctx.author.id,  # Benutzer-ID ist hier der Moderator selbst
                moderator_id=ctx.author.id,
                reason=f"Alle Nachrichten in #{channel_name} gelöscht"
            )
            
        except discord.Forbidden:
            await ctx.send("❌ Ich habe nicht die Berechtigung, diesen Kanal zu löschen oder zu klonen.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Löschen aller Nachrichten: {e}")

    @commands.hybrid_command(name="modlogs", description="Zeigt die Moderationsaktionen für einen Benutzer an")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mod_logs(self, ctx: commands.Context, user: discord.User):
        """
        Zeigt die Moderationsaktionen für einen Benutzer an.
        
        Args:
            user: Der Benutzer, dessen Logs angezeigt werden sollen
        """
        guild_id_str = str(ctx.guild.id)
        
        if guild_id_str not in self.mod_actions:
            await ctx.send(f"❌ Keine Moderationsaktionen für **{user}** gefunden.")
            return
            
        # Filtere Aktionen für den angegebenen Benutzer
        user_actions = [action for action in self.mod_actions[guild_id_str] if action.user_id == user.id]
        
        if not user_actions:
            await ctx.send(f"❌ Keine Moderationsaktionen für **{user}** gefunden.")
            return
            
        # Sortiere nach Zeitstempel (neueste zuerst)
        user_actions.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Erstelle die Embed-Nachricht
        embed = discord.Embed(
            title=f"Moderationsaktionen für {user}",
            description=f"Hier sind die Moderationsaktionen für {user.mention} (ID: {user.id}):",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for i, action in enumerate(user_actions[:10]):  # Zeige maximal 10 Aktionen
            # Hole den Moderator
            try:
                moderator = ctx.guild.get_member(action.moderator_id) or await self.bot.fetch_user(action.moderator_id)
                moderator_name = moderator.name if moderator else "Unbekannt"
            except:
                moderator_name = "Unbekannt"
                
            # Formatiere die Zeit
            time_str = f"<t:{int(action.timestamp.timestamp())}:R>"
            
            # Formatiere die Aktion
            action_str = f"**Typ:** {action.action_type.capitalize()}\n"
            action_str += f"**Moderator:** {moderator_name}\n"
            action_str += f"**Grund:** {action.reason}\n"
            action_str += f"**Zeit:** {time_str}"
            
            if action.duration:
                duration_str = self._format_duration(action.duration)
                action_str += f"\n**Dauer:** {duration_str}"
            
            embed.add_field(
                name=f"Fall #{action.case_id}",
                value=action_str,
                inline=False
            )
            
        if len(user_actions) > 10:
            embed.set_footer(text=f"Zeige 10 von {len(user_actions)} Aktionen")
            
        await ctx.send(embed=embed)
    
    def _parse_duration(self, duration_str: str) -> int:
        """Konvertiert einen Dauer-String (wie 1h, 5m, 30s) in Sekunden."""
        if not duration_str:
            raise ValueError("Keine Dauer angegeben")
            
        # Einheiten in Sekunden
        units = {
            's': 1,
            'm': 60,
            'h': 60 * 60,
            'd': 60 * 60 * 24,
            'w': 60 * 60 * 24 * 7
        }
        
        total_seconds = 0
        remaining = duration_str.lower()
        
        while remaining:
            # Finde die erste Zahl
            match = ""
            for char in remaining:
                if char.isdigit() or char == '.':
                    match += char
                else:
                    break
                    
            if not match:
                raise ValueError(f"Ungültiges Format: {duration_str}")
                
            # Versuche, den Wert zu parsen
            try:
                value = float(match)
            except ValueError:
                raise ValueError(f"Ungültiger Wert: {match}")
                
            # Entferne den Wert aus dem String
            remaining = remaining[len(match):]
            
            if not remaining:
                raise ValueError(f"Keine Einheit angegeben: {duration_str}")
                
            # Finde die Einheit
            unit = remaining[0]
            if unit not in units:
                raise ValueError(f"Ungültige Einheit: {unit}")
                
            # Berechne Sekunden und addiere zum Gesamtwert
            total_seconds += value * units[unit]
            
            # Entferne die Einheit aus dem String
            remaining = remaining[1:]
        
        return int(total_seconds)

async def setup(bot: commands.Bot):
    """Fügt den Moderation Cog zum Bot hinzu."""
    await bot.add_cog(Moderation(bot))
    logger.info("Moderation cog loaded")
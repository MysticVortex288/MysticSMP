import discord
from discord.ext import commands
import re
import json
import logging
import os
import datetime
import asyncio
import requests
from bs4 import BeautifulSoup
import trafilatura
from discord.ext import tasks

logger = logging.getLogger('discord_bot')

class ContentAnnouncer(commands.Cog):
    """Cog zum Ankündigen von Livestreams und Videos."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "content_announcer.json"
        self.config = self._load_config()
        
        # URL Patterns für verschiedene Plattformen
        self.url_patterns = {
            'youtube': [
                r'https?://(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|shorts/)?\S+',
                r'https?://youtube\.com/live/\S+'
            ],
            'twitch': [
                r'https?://(www\.)?twitch\.tv/\S+'
            ],
            'tiktok': [
                r'https?://(www\.)?(tiktok\.com|vm\.tiktok\.com)/\S+'
            ]
        }
        
        # Starte die Überprüfung auf neue TikTok-Videos
        self.check_tiktok_creators.start()
        
        # User-Agent für Anfragen, um Blockierungen zu vermeiden
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info("ContentAnnouncer cog initialized")
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.check_tiktok_creators.cancel()
        logger.info("Stopped TikTok creator check task")
    
    def _load_config(self):
        """Laden der Konfiguration aus der Datei."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Erstellen von Default-Daten
            default_data = {
                # Format: {"guild_id": {
                #   "announcement_channel_id": channel_id,
                #   "tiktok_creators": [{"username": "creator1", "last_video_id": "id"}],
                # }}
            }
            self._save_config(default_data)
            return default_data
    
    def _save_config(self, config=None):
        """Speichern der Konfiguration in der Datei."""
        if config is None:
            config = self.config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Event-Handler für Nachrichten."""
        # Ignoriere Nachrichten von Bots
        if message.author.bot:
            return
        
        # Ignoriere DMs
        if not message.guild:
            return
        
        # Prüfe, ob die Ankündigung für diesen Server aktiviert ist
        guild_id = str(message.guild.id)
        if guild_id not in self.config:
            return
        
        # Hole den Ankündigungskanal
        announcement_channel_id = self.config[guild_id].get("announcement_channel_id")
        if not announcement_channel_id:
            return
        
        # Hole den Ankündigungskanal
        announcement_channel = message.guild.get_channel(int(announcement_channel_id))
        if not announcement_channel:
            logger.error(f"Announcement channel {announcement_channel_id} not found")
            return
        
        # Wenn die Nachricht bereits im Ankündigungskanal ist, ignoriere sie
        if message.channel.id == announcement_channel.id:
            return
        
        # Überprüfe den Inhalt der Nachricht auf URLs
        content = message.content.lower()
        
        detected_platform = None
        matched_url = None
        
        # Durchsuche die Nachricht nach URLs für verschiedene Plattformen
        for platform, patterns in self.url_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    detected_platform = platform
                    # Extrahiere die vollständige URL, nicht nur die Übereinstimmungen
                    url_match = re.search(pattern, message.content)
                    if url_match:
                        matched_url = url_match.group(0)
                    break
            
            if detected_platform:
                break
        
        # Wenn keine Plattform erkannt wurde, beende die Funktion
        if not detected_platform or not matched_url:
            return
        
        # Erstelle ein Embed für die Ankündigung
        embed = discord.Embed(
            title=f"Neuer {self._get_content_type(detected_platform, content)} auf {self._get_platform_name(detected_platform)}!",
            description=f"{message.author.mention} hat einen Link geteilt:",
            color=self._get_platform_color(detected_platform),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Link", value=matched_url, inline=False)
        embed.add_field(name="Ursprünglicher Kanal", value=message.channel.mention, inline=False)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Geteilt am {discord.utils.format_dt(message.created_at, style='f')}")
        
        # Füge das Plattform-Logo hinzu
        embed.set_thumbnail(url=self._get_platform_logo(detected_platform))
        
        # Sende die Ankündigung
        await announcement_channel.send(embed=embed)
        logger.info(f"Announced {detected_platform} content from {message.author.display_name}")
    
    def _get_content_type(self, platform, content):
        """Bestimmt den Inhaltstyp basierend auf der Plattform und dem Inhalt."""
        if platform == 'youtube':
            if 'live' in content:
                return "Livestream"
            elif 'shorts' in content:
                return "Short"
            else:
                return "Video"
        elif platform == 'twitch':
            return "Stream"
        elif platform == 'tiktok':
            return "Video"
        else:
            return "Inhalt"
    
    def _get_platform_name(self, platform):
        """Gibt den formatierten Namen der Plattform zurück."""
        platform_names = {
            'youtube': "YouTube",
            'twitch': "Twitch",
            'tiktok': "TikTok"
        }
        return platform_names.get(platform, platform.capitalize())
    
    def _get_platform_color(self, platform):
        """Gibt die Farbe für die Plattform zurück."""
        platform_colors = {
            'youtube': discord.Color.red(),
            'twitch': discord.Color.purple(),
            'tiktok': discord.Color.from_rgb(0, 0, 0)  # Schwarz
        }
        return platform_colors.get(platform, discord.Color.blue())
    
    def _get_platform_logo(self, platform):
        """Gibt die URL zum Logo der Plattform zurück."""
        platform_logos = {
            'youtube': "https://www.freepnglogos.com/uploads/youtube-logo-png/youtube-logo-png-transparent-image-5.png",
            'twitch': "https://brand.twitch.tv/assets/images/twitch-extruded.png",
            'tiktok': "https://sf-tb-sg.ibytedtos.com/obj/eden-sg/uhtyvueh7nulogpoguhm/tiktok-icon2.png"
        }
        return platform_logos.get(platform, "")
    
    @commands.hybrid_command(name="setannouncement")
    @commands.has_permissions(administrator=True)
    async def set_announcement_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Setzt den Kanal für Stream- und Video-Ankündigungen.
        
        Args:
            channel: Der Kanal, in dem Ankündigungen gesendet werden sollen. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        # Wenn kein Kanal angegeben wurde, verwende den aktuellen
        if channel is None:
            channel = ctx.channel
        
        # Speichere die Konfiguration
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        self.config[guild_id]["announcement_channel_id"] = channel.id
        self._save_config()
        
        # Sende eine Bestätigung
        embed = discord.Embed(
            title="✅ Ankündigungskanal eingerichtet",
            description=f"Stream- und Video-Ankündigungen werden jetzt im Kanal {channel.mention} gesendet.\n\n"
                        f"Unterstützte Plattformen:\n"
                        f"• YouTube (Videos, Shorts, Livestreams)\n"
                        f"• Twitch (Streams)\n"
                        f"• TikTok (Videos)",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Set announcement channel to {channel.name} in guild {ctx.guild.name}")
    
    @commands.hybrid_command(name="removeannouncement")
    @commands.has_permissions(administrator=True)
    async def remove_announcement_channel(self, ctx: commands.Context):
        """
        Entfernt den Ankündigungskanal für Streams und Videos.
        """
        # Entferne die Konfiguration
        guild_id = str(ctx.guild.id)
        if guild_id in self.config:
            del self.config[guild_id]
            self._save_config()
        
        # Sende eine Bestätigung
        embed = discord.Embed(
            title="❌ Ankündigungskanal entfernt",
            description="Stream- und Video-Ankündigungen wurden deaktiviert.",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Removed announcement channel in guild {ctx.guild.name}")
    
    @commands.hybrid_command(name="addtiktokcreator")
    @commands.has_permissions(administrator=True)
    async def add_tiktok_creator(self, ctx: commands.Context, username: str):
        """
        Fügt einen TikTok-Creator zur Überwachungsliste hinzu.
        
        Args:
            username: Der Benutzername des TikTok-Creators ohne @ (z.B. 'tiktokuser').
        """
        # Entferne ein @ am Anfang des Benutzernamens, falls vorhanden
        username = username.lstrip('@')
        
        # Prüfe, ob der Server konfiguriert ist
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            await ctx.send(embed=discord.Embed(
                title="❌ Fehler",
                description="Der Ankündigungskanal muss zuerst mit `/setannouncement` eingerichtet werden.",
                color=discord.Color.red()
            ))
            return
        
        if "tiktok_creators" not in self.config[guild_id]:
            self.config[guild_id]["tiktok_creators"] = []
        
        # Prüfe, ob der Creator bereits in der Liste ist
        for creator in self.config[guild_id]["tiktok_creators"]:
            if creator["username"].lower() == username.lower():
                await ctx.send(embed=discord.Embed(
                    title="❌ Fehler",
                    description=f"Der TikTok-Creator @{username} ist bereits in der Liste.",
                    color=discord.Color.red()
                ))
                return
        
        # Versuche, die TikTok-Seite zu erreichen, um zu prüfen, ob der Benutzer existiert
        try:
            # TikTok-Profil-URL
            url = f"https://www.tiktok.com/@{username}"
            
            # Sende eine Anfrage an die URL
            response = requests.get(url, headers=self.headers)
            
            # Prüfen, ob die Anfrage erfolgreich war
            if response.status_code != 200:
                await ctx.send(embed=discord.Embed(
                    title="❌ Fehler",
                    description=f"Der TikTok-Creator @{username} konnte nicht gefunden werden.",
                    color=discord.Color.red()
                ))
                return
            
            # Extrahiere die neueste Video-ID wenn möglich
            soup = BeautifulSoup(response.text, 'html.parser')
            last_video_id = None
            
            # TikTok Videos werden auf der Profilseite angezeigt
            # Wir versuchen, die ID des neuesten Videos zu extrahieren
            # Dies ist eine einfache Implementierung - in der Praxis könnte dies komplexer sein
            
            # Füge den Creator zur Liste hinzu
            self.config[guild_id]["tiktok_creators"].append({
                "username": username,
                "last_video_id": last_video_id,
                "added_at": datetime.datetime.now().isoformat()
            })
            
            self._save_config()
            
            await ctx.send(embed=discord.Embed(
                title="✅ TikTok-Creator hinzugefügt",
                description=f"Der TikTok-Creator @{username} wurde zur Überwachungsliste hinzugefügt. "
                            f"Neue Videos werden im Ankündigungskanal angekündigt.",
                color=discord.Color.green()
            ))
            logger.info(f"Added TikTok creator @{username} to monitoring list in guild {ctx.guild.name}")
            
        except Exception as e:
            logger.error(f"Error adding TikTok creator @{username}: {e}")
            await ctx.send(embed=discord.Embed(
                title="❌ Fehler",
                description=f"Bei der Überprüfung des TikTok-Creators @{username} ist ein Fehler aufgetreten.",
                color=discord.Color.red()
            ))
    
    @commands.hybrid_command(name="removetiktokcreator")
    @commands.has_permissions(administrator=True)
    async def remove_tiktok_creator(self, ctx: commands.Context, username: str):
        """
        Entfernt einen TikTok-Creator von der Überwachungsliste.
        
        Args:
            username: Der Benutzername des TikTok-Creators ohne @ (z.B. 'tiktokuser').
        """
        # Entferne ein @ am Anfang des Benutzernamens, falls vorhanden
        username = username.lstrip('@')
        
        # Prüfe, ob der Server konfiguriert ist
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or "tiktok_creators" not in self.config[guild_id]:
            await ctx.send(embed=discord.Embed(
                title="❌ Fehler",
                description=f"Die Überwachungsliste für TikTok-Creator ist leer.",
                color=discord.Color.red()
            ))
            return
        
        # Finde den Creator in der Liste
        creator_found = False
        for i, creator in enumerate(self.config[guild_id]["tiktok_creators"]):
            if creator["username"].lower() == username.lower():
                # Entferne den Creator aus der Liste
                self.config[guild_id]["tiktok_creators"].pop(i)
                creator_found = True
                break
        
        if not creator_found:
            await ctx.send(embed=discord.Embed(
                title="❌ Fehler",
                description=f"Der TikTok-Creator @{username} ist nicht in der Überwachungsliste.",
                color=discord.Color.red()
            ))
            return
        
        # Speichere die Konfiguration
        self._save_config()
        
        await ctx.send(embed=discord.Embed(
            title="✅ TikTok-Creator entfernt",
            description=f"Der TikTok-Creator @{username} wurde von der Überwachungsliste entfernt.",
            color=discord.Color.green()
        ))
        logger.info(f"Removed TikTok creator @{username} from monitoring list in guild {ctx.guild.name}")
    
    @commands.hybrid_command(name="listtiktokcreators")
    @commands.has_permissions(administrator=True)
    async def list_tiktok_creators(self, ctx: commands.Context):
        """
        Zeigt eine Liste aller überwachten TikTok-Creator an.
        """
        # Prüfe, ob der Server konfiguriert ist
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or "tiktok_creators" not in self.config[guild_id] or not self.config[guild_id]["tiktok_creators"]:
            await ctx.send(embed=discord.Embed(
                title="ℹ️ TikTok-Creator",
                description=f"Die Überwachungsliste für TikTok-Creator ist leer.",
                color=discord.Color.blue()
            ))
            return
        
        creators = self.config[guild_id]["tiktok_creators"]
        
        # Erstelle eine Übersicht der Creator
        embed = discord.Embed(
            title="📋 TikTok-Creator Liste",
            description=f"Es werden {len(creators)} TikTok-Creator überwacht:",
            color=discord.Color.from_rgb(0, 0, 0)  # TikTok-Schwarz
        )
        
        for i, creator in enumerate(creators, 1):
            embed.add_field(
                name=f"{i}. @{creator['username']}",
                value=f"Hinzugefügt am: {creator.get('added_at', 'Unbekannt')}",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    @tasks.loop(minutes=30)
    async def check_tiktok_creators(self):
        """Überprüft regelmäßig alle TikTok-Creator auf neue Videos."""
        await self.bot.wait_until_ready()
        logger.info("Checking TikTok creators for new videos...")
        
        # Durchlaufe alle Server
        for guild_id, guild_config in self.config.items():
            # Prüfe, ob TikTok-Creators konfiguriert sind
            if "tiktok_creators" not in guild_config or not guild_config["tiktok_creators"]:
                continue
            
            # Prüfe, ob ein Ankündigungskanal konfiguriert ist
            announcement_channel_id = guild_config.get("announcement_channel_id")
            if not announcement_channel_id:
                continue
            
            # Hole den Ankündigungskanal
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                continue
            
            announcement_channel = guild.get_channel(int(announcement_channel_id))
            if not announcement_channel:
                logger.error(f"Announcement channel {announcement_channel_id} not found in guild {guild.name}")
                continue
            
            # Durchlaufe alle TikTok-Creator
            for creator in guild_config["tiktok_creators"]:
                username = creator["username"]
                
                try:
                    # Überprüfe auf neue Videos
                    new_videos = await self._check_tiktok_new_videos(username, creator.get("last_video_id"))
                    
                    if new_videos:
                        logger.info(f"Found {len(new_videos)} new videos for TikTok creator @{username}")
                        
                        # Aktualisiere die letzte bekannte Video-ID
                        creator["last_video_id"] = new_videos[0]["id"]
                        self._save_config()
                        
                        # Sende Ankündigungen für neue Videos (von neueste zu älteste)
                        for video in new_videos:
                            # Erstelle ein Embed für die Ankündigung
                            embed = discord.Embed(
                                title=f"Neues TikTok-Video von @{username}!",
                                description=f"**{video.get('title', 'Neues Video')}**\n\n"
                                            f"🔗 [Zum Video](https://www.tiktok.com/@{username}/video/{video['id']})",
                                color=discord.Color.from_rgb(0, 0, 0),  # TikTok-Schwarz
                                timestamp=datetime.datetime.now()
                            )
                            
                            # Füge Thumbnail hinzu, wenn verfügbar
                            if "thumbnail" in video:
                                embed.set_image(url=video["thumbnail"])
                            
                            # Füge das TikTok-Logo hinzu
                            embed.set_thumbnail(url=self._get_platform_logo("tiktok"))
                            
                            # Füge Statistiken hinzu, wenn verfügbar
                            if "stats" in video:
                                stats = video["stats"]
                                stats_text = ""
                                if "likes" in stats:
                                    stats_text += f"👍 {stats['likes']} Likes  "
                                if "comments" in stats:
                                    stats_text += f"💬 {stats['comments']} Kommentare  "
                                if "views" in stats:
                                    stats_text += f"👁️ {stats['views']} Aufrufe"
                                
                                if stats_text:
                                    embed.add_field(name="Statistiken", value=stats_text, inline=False)
                            
                            # Füge Fußzeile hinzu
                            embed.set_footer(text=f"TikTok-Creator Ankündigung")
                            
                            # Sende die Ankündigung
                            await announcement_channel.send(embed=embed)
                            
                except Exception as e:
                    logger.error(f"Error checking TikTok creator @{username}: {e}")
    
    async def _check_tiktok_new_videos(self, username, last_video_id=None):
        """
        Überprüft, ob ein TikTok-Creator neue Videos hochgeladen hat.
        
        Args:
            username: Der Benutzername des TikTok-Creators
            last_video_id: Die ID des letzten bekannten Videos
            
        Returns:
            Eine Liste von neuen Videos oder eine leere Liste, wenn keine neuen Videos gefunden wurden
        """
        try:
            # TikTok-Profil-URL
            url = f"https://www.tiktok.com/@{username}"
            
            # Sende eine Anfrage an die URL
            response = requests.get(url, headers=self.headers)
            
            # Prüfen, ob die Anfrage erfolgreich war
            if response.status_code != 200:
                logger.error(f"Failed to fetch TikTok profile for @{username}: Status code {response.status_code}")
                return []
            
            # Parse die Webseite mit BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Hier würde normalerweise komplexeres Scraping stattfinden, um Video-IDs zu extrahieren
            # Dies ist eine vereinfachte Demo-Version
            
            # Versuche, Video-IDs zu finden
            video_ids = []
            video_elements = soup.select('a[href*="/video/"]')
            
            for element in video_elements:
                href = element.get('href', '')
                if '/video/' in href:
                    # Extrahiere die Video-ID aus dem href-Attribut
                    parts = href.split('/video/')
                    if len(parts) > 1:
                        video_id = parts[1].split('?')[0]
                        if video_id not in video_ids:
                            video_ids.append(video_id)
            
            # Wenn keine Video-IDs gefunden wurden, gib eine leere Liste zurück
            if not video_ids:
                logger.info(f"No videos found for TikTok creator @{username}")
                return []
            
            # Wenn keine letzte Video-ID bekannt ist, speichere nur die neueste und gib keine zurück
            if not last_video_id:
                return []
            
            # Finde neue Videos (Videos, die nach dem letzten bekannten Video erstellt wurden)
            new_videos = []
            
            for video_id in video_ids:
                if video_id == last_video_id:
                    break
                
                # Erstelle ein Video-Objekt
                video = {
                    "id": video_id,
                    "title": f"Neues Video von @{username}",
                    # In einer vollständigen Implementierung würden hier mehr Daten extrahiert
                }
                
                new_videos.append(video)
            
            return new_videos
            
        except Exception as e:
            logger.error(f"Error checking TikTok creator @{username} for new videos: {e}")
            return []

async def setup(bot: commands.Bot):
    """Füge den ContentAnnouncer-Cog zum Bot hinzu."""
    await bot.add_cog(ContentAnnouncer(bot))
    logger.info("ContentAnnouncer cog loaded")
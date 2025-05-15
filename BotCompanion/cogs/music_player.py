import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import yt_dlp
import os
import json
import requests
from collections import deque
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

logger = logging.getLogger('discord_bot')

# YouTube DL options
YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class MusicPlayer(commands.Cog):
    """Cog for playing music in voice channels."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)
        self.queues = {}  # Server ID -> deque of songs
        self.now_playing = {}  # Server ID -> currently playing song info
        self.volume = {}  # Server ID -> volume (0.0 to 1.0)
        logger.info("MusicPlayer cog initialized")
    
    def init_spotify(self):
        """Initialize Spotify client if credentials are available."""
        try:
            client_id = os.environ.get("SPOTIFY_CLIENT_ID")
            client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
            
            if client_id and client_secret:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id, 
                    client_secret=client_secret
                )
                return spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            return None
        except Exception as e:
            logger.error(f"Error initializing Spotify: {e}")
            return None
    
    async def search_youtube(self, query):
        """Search for a song on YouTube and return the URL."""
        try:
            # Use YouTube Data API v3 directly
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': 1,
                'key': 'AIzaSyDJkcVwQQtKBOEKGmwX-7GQUMCjJLJAPOU'  # YouTube API key
            }
            
            # Run the API request in a separate thread to avoid blocking
            response = await self.bot.loop.run_in_executor(
                None, 
                lambda: requests.get(search_url, params=search_params)
            )
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            
            if not data.get('items'):
                return None
            
            video_id = data['items'][0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            # Fallback: use YT-DLP's search functionality
            try:
                info = await self.bot.loop.run_in_executor(
                    None,
                    lambda: self.ytdl.extract_info(f"ytsearch:{query}", download=False)
                )
                if not info or 'entries' not in info or not info['entries']:
                    return None
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
            except Exception as e2:
                logger.error(f"Error during fallback YouTube search: {e2}")
                return None
                
    async def get_spotify_track_url(self, spotify_url):
        """Get YouTube URL for a Spotify track."""
        try:
            # Initialize Spotify client
            sp = self.init_spotify()
            if not sp:
                return None, "Spotify-Anmeldedaten fehlen oder sind ungültig."
            
            # Extract track ID from URL
            track_id_match = re.search(r'track/([a-zA-Z0-9]+)', spotify_url)
            if not track_id_match:
                return None, "Ungültige Spotify-Track-URL."
            
            track_id = track_id_match.group(1)
            
            # Get track info
            track_info = sp.track(track_id)
            if not track_info:
                return None, "Konnte keine Informationen zum Spotify-Track abrufen."
            
            # Format search query for YouTube
            artist = track_info['artists'][0]['name']
            title = track_info['name']
            query = f"{artist} - {title}"
            
            # Search for the track on YouTube
            youtube_url = await self.search_youtube(query)
            
            return youtube_url, None  # Return URL and no error
            
        except Exception as e:
            logger.error(f"Error processing Spotify URL: {e}")
            return None, f"Fehler beim Verarbeiten der Spotify-URL: {e}"
            
    async def get_spotify_playlist(self, spotify_url):
        """Get tracks from a Spotify playlist."""
        try:
            # Initialize Spotify client
            sp = self.init_spotify()
            if not sp:
                return None, "Spotify-Anmeldedaten fehlen oder sind ungültig."
            
            # Extract playlist ID from URL
            playlist_id_match = re.search(r'playlist/([a-zA-Z0-9]+)', spotify_url)
            if not playlist_id_match:
                return None, "Ungültige Spotify-Playlist-URL."
            
            playlist_id = playlist_id_match.group(1)
            
            # Get playlist info
            results = sp.playlist_tracks(playlist_id)
            tracks = results['items']
            
            # Get all tracks (handling pagination)
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            
            # Extract track information
            track_queries = []
            for item in tracks:
                track = item['track']
                if track:
                    artist = track['artists'][0]['name']
                    title = track['name']
                    track_queries.append(f"{artist} - {title}")
            
            return track_queries, None  # Return tracks and no error
            
        except Exception as e:
            logger.error(f"Error processing Spotify playlist: {e}")
            return None, f"Fehler beim Verarbeiten der Spotify-Playlist: {e}"
    
    async def get_audio_source(self, url):
        """Get an audio source from a URL."""
        loop = self.bot.loop
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            # Take the first item from a playlist
            data = data['entries'][0]
        
        audio_url = data['url']
        audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        return {
            'source': audio_source,
            'title': data.get('title', 'Unknown'),
            'url': url,
            'thumbnail': data.get('thumbnail', None),
            'duration': data.get('duration', 0),
            'uploader': data.get('uploader', 'Unknown')
        }
    
    async def play_next(self, ctx):
        """Play the next song in the queue."""
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            self.now_playing[guild_id] = None
            await ctx.send("Die Warteschlange ist leer. Verlasse den Sprachkanal.")
            await ctx.voice_client.disconnect()
            return
        
        # Get the next song from the queue
        next_song = self.queues[guild_id].popleft()
        
        # Play the song
        ctx.voice_client.play(
            next_song['source'], 
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.handle_song_end(ctx, e), self.bot.loop
            )
        )
        
        # Set volume
        if guild_id in self.volume:
            ctx.voice_client.source.volume = self.volume[guild_id]
        else:
            self.volume[guild_id] = 0.5
            ctx.voice_client.source.volume = 0.5
        
        # Update now playing info
        self.now_playing[guild_id] = next_song
        
        # Send now playing message
        embed = discord.Embed(
            title="Jetzt spielt",
            description=f"[{next_song['title']}]({next_song['url']})",
            color=discord.Color.blue()
        )
        
        if next_song['thumbnail']:
            embed.set_thumbnail(url=next_song['thumbnail'])
        
        embed.add_field(name="Kanal", value=next_song['uploader'], inline=True)
        
        # Format duration
        if next_song['duration']:
            minutes, seconds = divmod(next_song['duration'], 60)
            hours, minutes = divmod(minutes, 60)
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
            embed.add_field(name="Dauer", value=duration, inline=True)
        
        # Add queue information
        if guild_id in self.queues and self.queues[guild_id]:
            next_up = self.queues[guild_id][0]['title'] if self.queues[guild_id] else "Keine"
            embed.add_field(
                name=f"Warteschlange ({len(self.queues[guild_id])})", 
                value=f"Nächster Song: {next_up[:30]}..." if len(next_up) > 30 else next_up,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def handle_song_end(self, ctx, error):
        """Handle the end of a song and play the next one."""
        if error:
            logger.error(f"Error playing song: {error}")
            await ctx.send(f"Fehler beim Abspielen: {error}")
        
        await self.play_next(ctx)
    
    @commands.hybrid_command(name="join")
    async def join(self, ctx: commands.Context):
        """Lässt den Bot deinem aktuellen Sprachkanal beitreten."""
        if not ctx.author.voice:
            await ctx.send("Du musst in einem Sprachkanal sein, damit ich beitreten kann.")
            return
        
        channel = ctx.author.voice.channel
        
        if ctx.voice_client:
            if ctx.voice_client.channel.id == channel.id:
                await ctx.send(f"Ich bin bereits in {channel.mention}.")
                return
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        
        await ctx.send(f"Bin {channel.mention} beigetreten.")
    
    @commands.hybrid_command(name="leave")
    async def leave(self, ctx: commands.Context):
        """Der Bot verlässt den aktuellen Sprachkanal."""
        if not ctx.voice_client:
            await ctx.send("Ich bin in keinem Sprachkanal.")
            return
        
        await ctx.voice_client.disconnect()
        
        # Clear the queue and now playing info
        guild_id = ctx.guild.id
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        
        self.now_playing[guild_id] = None
        
        await ctx.send("Habe den Sprachkanal verlassen.")
    
    @commands.hybrid_command(name="play")
    async def play(self, ctx: commands.Context, *, query: str):
        """
        Spielt einen Song aus YouTube oder Spotify ab.
        
        Args:
            query: Name oder URL des Songs/Playlist
        """
        # Join voice channel if not already in one
        if not ctx.voice_client:
            if not ctx.author.voice:
                await ctx.send("Du musst in einem Sprachkanal sein.")
                return
            
            await ctx.author.voice.channel.connect()
        
        # Send a typing indicator while searching
        async with ctx.typing():
            url = query
            
            # Process Spotify URLs
            if "open.spotify.com" in query:
                # Check if it's a Spotify track
                if "track" in query:
                    await ctx.send(f"🎵 Lade Spotify-Track...")
                    url, error = await self.get_spotify_track_url(query)
                    if error:
                        await ctx.send(error)
                        return
                    if not url:
                        await ctx.send("Konnte den Spotify-Track nicht finden.")
                        return
                
                # Check if it's a Spotify playlist
                elif "playlist" in query:
                    await ctx.send(f"🎵 Lade Spotify-Playlist...")
                    tracks, error = await self.get_spotify_playlist(query)
                    if error:
                        await ctx.send(error)
                        return
                    if not tracks:
                        await ctx.send("Konnte keine Tracks in der Playlist finden.")
                        return
                    
                    # Process the first track immediately and queue the rest
                    first_track = tracks[0]
                    await ctx.send(f"🔎 Suche nach: `{first_track}`")
                    url = await self.search_youtube(first_track)
                    
                    # Queue the rest of the tracks in the background
                    if len(tracks) > 1:
                        await ctx.send(f"🎵 Stelle {len(tracks)-1} weitere Songs in die Warteschlange...")
                        # Schedule the task to not block the current command
                        self.bot.loop.create_task(self.queue_spotify_tracks(ctx, tracks[1:]))
            
            # If it's not a URL, search for it on YouTube
            elif not query.startswith(('https://', 'http://')):
                await ctx.send(f"🔎 Suche nach: `{query}`")
                url = await self.search_youtube(query)
                if not url:
                    await ctx.send("Konnte keinen Song finden.")
                    return
            
            # Get the audio source for the current URL
            try:
                song = await self.get_audio_source(url)
            except Exception as e:
                logger.error(f"Error getting audio source: {e}")
                await ctx.send(f"Fehler beim Laden des Songs: {e}")
                return
            
            guild_id = ctx.guild.id
            
            # Initialize the queue if it doesn't exist
            if guild_id not in self.queues:
                self.queues[guild_id] = deque()
            
            # Add to queue and play if not already playing
            self.queues[guild_id].append(song)
            
            if not ctx.voice_client.is_playing():
                await self.play_next(ctx)
            else:
                embed = discord.Embed(
                    title="Zur Warteschlange hinzugefügt",
                    description=f"[{song['title']}]({song['url']})",
                    color=discord.Color.green()
                )
                
                if song['thumbnail']:
                    embed.set_thumbnail(url=song['thumbnail'])
                
                # Show position in queue
                position = len(self.queues[guild_id])
                embed.add_field(name="Position", value=f"{position}", inline=True)
                
                await ctx.send(embed=embed)
                
    async def queue_spotify_tracks(self, ctx, tracks):
        """Add multiple Spotify tracks to the queue."""
        guild_id = ctx.guild.id
        
        for track in tracks:
            try:
                # Search for the track on YouTube
                url = await self.search_youtube(track)
                if not url:
                    continue
                    
                # Get the audio source
                song = await self.get_audio_source(url)
                
                # Add to queue
                if guild_id not in self.queues:
                    self.queues[guild_id] = deque()
                    
                self.queues[guild_id].append(song)
                
                # Start playing if nothing is playing
                if not ctx.voice_client.is_playing() and len(self.queues[guild_id]) == 1:
                    await self.play_next(ctx)
                    
            except Exception as e:
                logger.error(f"Error adding track to queue: {e}")
                # We don't need to notify the user for every failed track in a playlist
    
    @commands.hybrid_command(name="pause")
    async def pause(self, ctx: commands.Context):
        """Pausiert die aktuelle Wiedergabe."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("Es wird nichts abgespielt.")
            return
        
        ctx.voice_client.pause()
        await ctx.send("⏸️ Wiedergabe pausiert.")
    
    @commands.hybrid_command(name="resume")
    async def resume(self, ctx: commands.Context):
        """Setzt die pausierte Wiedergabe fort."""
        if not ctx.voice_client:
            await ctx.send("Ich bin in keinem Sprachkanal.")
            return
        
        if not ctx.voice_client.is_paused():
            await ctx.send("Die Wiedergabe ist nicht pausiert.")
            return
        
        ctx.voice_client.resume()
        await ctx.send("▶️ Wiedergabe fortgesetzt.")
    
    @commands.hybrid_command(name="stop")
    async def stop(self, ctx: commands.Context):
        """Stoppt die Wiedergabe und leert die Warteschlange."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("Es wird nichts abgespielt.")
            return
        
        guild_id = ctx.guild.id
        
        # Clear the queue
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        
        # Stop the player
        ctx.voice_client.stop()
        
        await ctx.send("⏹️ Wiedergabe gestoppt und Warteschlange geleert.")
    
    @commands.hybrid_command(name="skip")
    async def skip(self, ctx: commands.Context):
        """Überspringt den aktuellen Song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("Es wird nichts abgespielt.")
            return
        
        await ctx.send("⏭️ Song übersprungen.")
        ctx.voice_client.stop()  # This will trigger the after function to play the next song
    
    @commands.hybrid_command(name="queue", aliases=["q"])
    async def queue(self, ctx: commands.Context):
        """Zeigt die aktuelle Warteschlange an."""
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            if guild_id not in self.now_playing or not self.now_playing[guild_id]:
                await ctx.send("Die Warteschlange ist leer.")
                return
            
            # Only show now playing
            now_playing = self.now_playing[guild_id]
            embed = discord.Embed(
                title="Warteschlange",
                description="Aktuell keine Songs in der Warteschlange.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Jetzt spielt",
                value=f"[{now_playing['title']}]({now_playing['url']})",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Show the queue
        embed = discord.Embed(
            title="Warteschlange",
            color=discord.Color.blue()
        )
        
        # Add now playing
        if guild_id in self.now_playing and self.now_playing[guild_id]:
            now_playing = self.now_playing[guild_id]
            embed.add_field(
                name="Jetzt spielt",
                value=f"[{now_playing['title']}]({now_playing['url']})",
                inline=False
            )
        
        # Add queue items
        queue_text = ""
        for i, song in enumerate(self.queues[guild_id], start=1):
            queue_text += f"{i}. [{song['title']}]({song['url']})\n"
            
            # Split into multiple fields if too long
            if i % 10 == 0 or len(queue_text) > 900:
                embed.add_field(
                    name=f"Warteschlange (Teil {i//10 + 1})",
                    value=queue_text,
                    inline=False
                )
                queue_text = ""
        
        if queue_text:
            embed.add_field(
                name=f"Warteschlange",
                value=queue_text,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="nowplaying", aliases=["np"])
    async def now_playing_cmd(self, ctx: commands.Context):
        """Zeigt Informationen zum aktuellen Song an."""
        guild_id = ctx.guild.id
        
        if guild_id not in self.now_playing or not self.now_playing[guild_id]:
            await ctx.send("Es wird nichts abgespielt.")
            return
        
        now_playing = self.now_playing[guild_id]
        
        embed = discord.Embed(
            title="Jetzt spielt",
            description=f"[{now_playing['title']}]({now_playing['url']})",
            color=discord.Color.blue()
        )
        
        if now_playing['thumbnail']:
            embed.set_thumbnail(url=now_playing['thumbnail'])
        
        embed.add_field(name="Kanal", value=now_playing['uploader'], inline=True)
        
        # Format duration
        if now_playing['duration']:
            minutes, seconds = divmod(now_playing['duration'], 60)
            hours, minutes = divmod(minutes, 60)
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
            embed.add_field(name="Dauer", value=duration, inline=True)
        
        # Add volume information
        if guild_id in self.volume:
            volume_percentage = int(self.volume[guild_id] * 100)
            embed.add_field(name="Lautstärke", value=f"{volume_percentage}%", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="volume", aliases=["vol"])
    async def volume_cmd(self, ctx: commands.Context, volume: int = None):
        """
        Stellt die Lautstärke ein (0-100).
        
        Args:
            volume: Lautstärke von 0 bis 100
        """
        if not ctx.voice_client:
            await ctx.send("Ich bin in keinem Sprachkanal.")
            return
        
        guild_id = ctx.guild.id
        
        # If no volume is provided, show the current volume
        if volume is None:
            if guild_id in self.volume:
                volume_percentage = int(self.volume[guild_id] * 100)
                await ctx.send(f"Aktuelle Lautstärke: {volume_percentage}%")
            else:
                await ctx.send(f"Aktuelle Lautstärke: 50%")
            return
        
        # Validate volume
        if volume < 0 or volume > 100:
            await ctx.send("Die Lautstärke muss zwischen 0 und 100 liegen.")
            return
        
        # Convert to float (0.0 to 1.0)
        volume_float = volume / 100
        
        # Store the volume setting
        self.volume[guild_id] = volume_float
        
        # Apply to current playback if something is playing
        if ctx.voice_client.is_playing():
            ctx.voice_client.source.volume = volume_float
        
        await ctx.send(f"🔊 Lautstärke auf {volume}% gesetzt.")
    
    @commands.hybrid_command(name="clear")
    async def clear(self, ctx: commands.Context):
        """Leert die Warteschlange, aber lässt den aktuellen Song weiterlaufen."""
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("Die Warteschlange ist bereits leer.")
            return
        
        queue_length = len(self.queues[guild_id])
        self.queues[guild_id].clear()
        
        await ctx.send(f"🗑️ Warteschlange geleert ({queue_length} Songs entfernt).")
    
    @commands.hybrid_command(name="remove")
    async def remove(self, ctx: commands.Context, position: int):
        """
        Entfernt einen Song aus der Warteschlange.
        
        Args:
            position: Position in der Warteschlange (beginnend bei 1)
        """
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("Die Warteschlange ist leer.")
            return
        
        if position < 1 or position > len(self.queues[guild_id]):
            await ctx.send(f"Die Position muss zwischen 1 und {len(self.queues[guild_id])} liegen.")
            return
        
        # Convert to 0-based index
        index = position - 1
        removed_song = self.queues[guild_id][index]
        del self.queues[guild_id][index]
        
        await ctx.send(f"🗑️ Entfernt: {removed_song['title']}")
    
    @commands.hybrid_command(name="shuffle")
    async def shuffle(self, ctx: commands.Context):
        """Mischt die Warteschlange zufällig durch."""
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            await ctx.send("Die Warteschlange ist leer.")
            return
        
        # Convert deque to list, shuffle, then back to deque
        queue_list = list(self.queues[guild_id])
        import random
        random.shuffle(queue_list)
        self.queues[guild_id] = deque(queue_list)
        
        await ctx.send(f"🔀 Warteschlange mit {len(self.queues[guild_id])} Songs gemischt.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates."""
        if member.id != self.bot.user.id:
            return
        
        # Bot disconnected from voice channel
        if before.channel and not after.channel:
            guild_id = before.channel.guild.id
            
            # Clear the queue and now playing info
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            
            self.now_playing[guild_id] = None
            logger.info(f"Bot disconnected from voice channel in guild {guild_id}")

async def setup(bot: commands.Bot):
    """Add the MusicPlayer cog to the bot."""
    await bot.add_cog(MusicPlayer(bot))
    logger.info("MusicPlayer cog loaded")
import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger('discord_bot')

class CountingGame(commands.Cog):
    """Cog für das Counting-Game."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "counting.json"
        self.counting_data = self._load_counting_data()
        
        logger.info("CountingGame cog initialized")
        
    def _load_counting_data(self):
        """Laden der Counting-Daten aus der Datei."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Erstellen von Default-Daten
            default_data = {
                "channels": {},  # Format: {"channel_id": {"current_count": 0, "last_user_id": None, "high_score": 0}}
            }
            self._save_counting_data(default_data)
            return default_data
    
    def _save_counting_data(self, data=None):
        """Speichern der Counting-Daten in der Datei."""
        if data is None:
            data = self.counting_data
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    @commands.hybrid_command(name="countingsetup")
    @commands.has_permissions(administrator=True)
    async def counting_setup(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Richtet einen Kanal für das Counting-Game ein.
        
        Args:
            channel: Der Kanal, der für das Counting-Game verwendet werden soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        try:
            # Wenn kein Kanal angegeben ist, verwende den aktuellen
            if channel is None:
                channel = ctx.channel
            
            # Setze Default-Werte für den Kanal
            self.counting_data["channels"][str(channel.id)] = {
                "current_count": 0,
                "last_user_id": None,
                "high_score": 0
            }
            
            self._save_counting_data()
            
            embed = discord.Embed(
                title="Counting-Game eingerichtet",
                description=f"Das Counting-Game wurde erfolgreich in {channel.mention} eingerichtet!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Spielregeln", 
                value="1. Beginne mit der Zahl 1\n"
                      "2. Jede nachfolgende Nachricht muss die nächste Zahl in der Sequenz sein\n"
                      "3. Dieselbe Person darf nicht zweimal hintereinander zählen\n"
                      "4. Wenn jemand eine falsche Zahl sendet, wird der Zähler zurückgesetzt",
                inline=False
            )
            
            info_message = await channel.send(embed=embed)
            
            # Bestätigungsnachricht an den Ausführenden des Befehls
            if ctx.channel.id != channel.id:
                await ctx.send(f"Das Counting-Game wurde erfolgreich in {channel.mention} eingerichtet!")
                
        except Exception as e:
            logger.error(f"Error in counting_setup: {e}")
            await ctx.send(f"Fehler bei der Einrichtung des Counting-Games: {e}")
    
    @commands.hybrid_command(name="countingreset")
    @commands.has_permissions(administrator=True)
    async def counting_reset(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Setzt das Counting-Game in einem Kanal zurück.
        
        Args:
            channel: Der Kanal, in dem das Counting-Game zurückgesetzt werden soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        try:
            # Wenn kein Kanal angegeben ist, verwende den aktuellen
            if channel is None:
                channel = ctx.channel
            
            channel_id = str(channel.id)
            
            # Überprüfen, ob der Kanal für das Counting-Game eingerichtet ist
            if channel_id not in self.counting_data["channels"]:
                await ctx.send(f"In {channel.mention} ist kein Counting-Game eingerichtet.")
                return
            
            # Speichere den aktuellen High-Score
            high_score = self.counting_data["channels"][channel_id]["high_score"]
            current_count = self.counting_data["channels"][channel_id]["current_count"]
            
            # Aktualisiere den High-Score, wenn nötig
            if current_count > high_score:
                high_score = current_count
                
            # Setze den Kanal zurück
            self.counting_data["channels"][channel_id] = {
                "current_count": 0,
                "last_user_id": None,
                "high_score": high_score
            }
            
            self._save_counting_data()
            
            embed = discord.Embed(
                title="Counting-Game zurückgesetzt",
                description=f"Das Counting-Game in {channel.mention} wurde zurückgesetzt.",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="High-Score", value=str(high_score), inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in counting_reset: {e}")
            await ctx.send(f"Fehler beim Zurücksetzen des Counting-Games: {e}")
    
    @commands.hybrid_command(name="countingdelete")
    @commands.has_permissions(administrator=True)
    async def counting_delete(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Entfernt das Counting-Game aus einem Kanal.
        
        Args:
            channel: Der Kanal, aus dem das Counting-Game entfernt werden soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        try:
            # Wenn kein Kanal angegeben ist, verwende den aktuellen
            if channel is None:
                channel = ctx.channel
            
            channel_id = str(channel.id)
            
            # Überprüfen, ob der Kanal für das Counting-Game eingerichtet ist
            if channel_id not in self.counting_data["channels"]:
                await ctx.send(f"In {channel.mention} ist kein Counting-Game eingerichtet.")
                return
            
            # Entferne den Kanal
            del self.counting_data["channels"][channel_id]
            
            self._save_counting_data()
            
            embed = discord.Embed(
                title="Counting-Game entfernt",
                description=f"Das Counting-Game in {channel.mention} wurde entfernt.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in counting_delete: {e}")
            await ctx.send(f"Fehler beim Entfernen des Counting-Games: {e}")
    
    @commands.hybrid_command(name="countingstatus")
    async def counting_status(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Zeigt den Status des Counting-Games in einem Kanal an.
        
        Args:
            channel: Der Kanal, für den der Status angezeigt werden soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        try:
            # Wenn kein Kanal angegeben ist, verwende den aktuellen
            if channel is None:
                channel = ctx.channel
            
            channel_id = str(channel.id)
            
            # Überprüfen, ob der Kanal für das Counting-Game eingerichtet ist
            if channel_id not in self.counting_data["channels"]:
                await ctx.send(f"In {channel.mention} ist kein Counting-Game eingerichtet.")
                return
            
            # Hole die Daten
            channel_data = self.counting_data["channels"][channel_id]
            current_count = channel_data["current_count"]
            high_score = channel_data["high_score"]
            
            # Letzte Person, die gezählt hat
            last_user_id = channel_data["last_user_id"]
            last_user = None
            if last_user_id:
                last_user = ctx.guild.get_member(last_user_id)
            
            embed = discord.Embed(
                title="Counting-Game Status",
                description=f"Status des Counting-Games in {channel.mention}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Aktuelle Zahl", value=str(current_count), inline=True)
            embed.add_field(name="Nächste Zahl", value=str(current_count + 1), inline=True)
            embed.add_field(name="High-Score", value=str(high_score), inline=True)
            
            if last_user:
                embed.add_field(name="Letzte Person", value=last_user.mention, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in counting_status: {e}")
            await ctx.send(f"Fehler beim Abrufen des Counting-Game-Status: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Event-Handler für Nachrichten im Counting-Game."""
        # Ignoriere Bot-Nachrichten
        if message.author.bot:
            return
        
        # Prüfe, ob der Kanal für das Counting-Game eingerichtet ist
        channel_id = str(message.channel.id)
        if channel_id not in self.counting_data["channels"]:
            return
        
        # Hole die Daten
        channel_data = self.counting_data["channels"][channel_id]
        current_count = channel_data["current_count"]
        last_user_id = channel_data["last_user_id"]
        high_score = channel_data["high_score"]
        
        # Versuche, die Nachricht als Zahl zu interpretieren
        try:
            count = int(message.content.strip())
            
            # Prüfe, ob es die richtige Zahl ist
            if count == current_count + 1:
                # Prüfe, ob dieselbe Person zweimal hintereinander gezählt hat
                if last_user_id == message.author.id:
                    # Speichern des aktuellen Zählerstands für die Nachricht
                    reached_count = current_count
                    
                    # Prüfe, ob ein neuer High-Score erreicht wurde
                    is_new_highscore = current_count > high_score
                    
                    # Aktualisiere den High-Score, wenn nötig
                    updated_high_score = max(current_count, high_score)
                    
                    # Setze den Zähler zurück                    
                    self.counting_data["channels"][channel_id] = {
                        "current_count": 0,
                        "last_user_id": None,
                        "high_score": updated_high_score
                    }
                    
                    self._save_counting_data()
                    
                    # Sende eine Nachricht mit dem Fehler
                    embed = discord.Embed(
                        title="❌ Counting-Game zurückgesetzt",
                        description=f"{message.author.mention} hat zweimal hintereinander gezählt!",
                        color=discord.Color.red()
                    )
                    
                    embed.add_field(name="Erreichte Zahl", value=str(reached_count), inline=True)
                    embed.add_field(name="High-Score", value=str(updated_high_score), inline=True)
                    
                    # Wenn ein neuer High-Score erreicht wurde
                    if is_new_highscore:
                        embed.add_field(
                            name="🎉 Neuer High-Score!",
                            value=f"Ihr habt einen neuen High-Score von **{reached_count}** erreicht!",
                            inline=False
                        )
                    
                    await message.channel.send(embed=embed)
                    await message.add_reaction("❌")
                    
                else:
                    # Aktualisiere den Zähler
                    self.counting_data["channels"][channel_id] = {
                        "current_count": count,
                        "last_user_id": message.author.id,
                        "high_score": max(count, high_score)  # Update High-Score wenn nötig
                    }
                    
                    self._save_counting_data()
                    
                    # Reagiere mit einem Haken
                    await message.add_reaction("✅")
                    
            else:
                # Falsche Zahl, setze den Zähler zurück
                # Speichern des aktuellen Zählerstands für die Nachricht
                reached_count = current_count
                
                # Prüfe, ob ein neuer High-Score erreicht wurde
                is_new_highscore = current_count > high_score
                
                # Aktualisiere den High-Score, wenn nötig
                updated_high_score = max(current_count, high_score)
                
                # Setze den Zähler zurück
                self.counting_data["channels"][channel_id] = {
                    "current_count": 0,
                    "last_user_id": None,
                    "high_score": updated_high_score
                }
                
                self._save_counting_data()
                
                # Sende eine Nachricht mit dem Fehler
                embed = discord.Embed(
                    title="❌ Counting-Game zurückgesetzt",
                    description=f"{message.author.mention} hat die falsche Zahl genannt!",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="Erwartete Zahl", value=str(current_count + 1), inline=True)
                embed.add_field(name="Genannte Zahl", value=str(count), inline=True)
                embed.add_field(name="Erreichte Zahl", value=str(reached_count), inline=True)
                embed.add_field(name="High-Score", value=str(updated_high_score), inline=True)
                
                # Wenn ein neuer High-Score erreicht wurde
                if is_new_highscore:
                    embed.add_field(
                        name="🎉 Neuer High-Score!",
                        value=f"Ihr habt einen neuen High-Score von **{reached_count}** erreicht!",
                        inline=False
                    )
                
                await message.channel.send(embed=embed)
                await message.add_reaction("❌")
                
        except ValueError:
            # Keine Zahl, ignoriere die Nachricht
            pass

async def setup(bot: commands.Bot):
    """Füge die CountingGame-Cog zum Bot hinzu."""
    await bot.add_cog(CountingGame(bot))
    logger.info("CountingGame cog loaded")
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import logging
import os
from datetime import datetime
import asyncio

logger = logging.getLogger('discord_bot')

class TempVoiceUI(discord.ui.View):
    def __init__(self, owner, channel, bot):
        super().__init__(timeout=None)  # Damit die Buttons nicht nach einer Zeit ungültig werden
        self.owner = owner
        self.channel = channel
        self.bot = bot
        self.locked = False
        self.hidden = False
    
    @discord.ui.button(label="Umbenennen", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="temp_voice:rename")
    async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Umbenennen des temporären Sprachkanals"""
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Nur der Besitzer des Kanals kann ihn umbenennen!", ephemeral=True)
            return
        
        # Modal zum Eingeben des neuen Namens
        class RenameModal(discord.ui.Modal, title="Kanal umbenennen"):
            new_name = discord.ui.TextInput(
                label="Neuer Name",
                placeholder="Gib einen neuen Namen für deinen Kanal ein",
                min_length=1,
                max_length=32,
                required=True
            )
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    await self.channel.edit(name=self.new_name.value)
                    await modal_interaction.response.send_message(f"Kanal umbenannt zu: {self.new_name.value}", ephemeral=True)
                except Exception as e:
                    logger.error(f"Error renaming channel: {e}")
                    await modal_interaction.response.send_message(f"Fehler beim Umbenennen des Kanals: {e}", ephemeral=True)
        
        # Channel im Modal setzen
        modal = RenameModal()
        modal.channel = self.channel
        
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Limit", style=discord.ButtonStyle.primary, emoji="👥", custom_id="temp_voice:limit")
    async def limit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Setzen des Nutzerlimits für den temporären Sprachkanal"""
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Nur der Besitzer des Kanals kann das Nutzerlimit ändern!", ephemeral=True)
            return
        
        # Modal zum Eingeben des Nutzerlimits
        class LimitModal(discord.ui.Modal, title="Nutzerlimit setzen"):
            user_limit = discord.ui.TextInput(
                label="Nutzerlimit",
                placeholder="Gib das Nutzerlimit ein (0-99, 0 für kein Limit)",
                min_length=1,
                max_length=2,
                required=True
            )
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    limit = int(self.user_limit.value)
                    if limit < 0 or limit > 99:
                        await modal_interaction.response.send_message("Das Nutzerlimit muss zwischen 0 und 99 liegen!", ephemeral=True)
                        return
                    
                    await self.channel.edit(user_limit=limit)
                    
                    if limit == 0:
                        await modal_interaction.response.send_message("Nutzerlimit entfernt", ephemeral=True)
                    else:
                        await modal_interaction.response.send_message(f"Nutzerlimit auf {limit} gesetzt", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("Bitte gib eine gültige Zahl ein!", ephemeral=True)
                except Exception as e:
                    logger.error(f"Error setting user limit: {e}")
                    await modal_interaction.response.send_message(f"Fehler beim Setzen des Nutzerlimits: {e}", ephemeral=True)
        
        # Channel im Modal setzen
        modal = LimitModal()
        modal.channel = self.channel
        
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Sperren", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="temp_voice:lock")
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Sperren/Entsperren des temporären Sprachkanals"""
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Nur der Besitzer des Kanals kann ihn sperren/entsperren!", ephemeral=True)
            return
        
        try:
            self.locked = not self.locked
            everyone_role = interaction.guild.default_role
            
            if self.locked:
                # Kanal sperren
                await self.channel.set_permissions(everyone_role, connect=False)
                button.label = "Entsperren"
                button.emoji = "🔓"
                button.style = discord.ButtonStyle.success
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Kanal gesperrt! Neue Nutzer können nicht mehr beitreten.", ephemeral=True)
            else:
                # Kanal entsperren
                await self.channel.set_permissions(everyone_role, connect=None)  # Zurücksetzen auf Standardwerte
                button.label = "Sperren"
                button.emoji = "🔒"
                button.style = discord.ButtonStyle.danger
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Kanal entsperrt! Neue Nutzer können wieder beitreten.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error toggling lock: {e}")
            await interaction.response.send_message(f"Fehler beim Sperren/Entsperren des Kanals: {e}", ephemeral=True)
    
    @discord.ui.button(label="Verstecken", style=discord.ButtonStyle.secondary, emoji="👁️", custom_id="temp_voice:hide")
    async def hide_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Verstecken/Anzeigen des temporären Sprachkanals"""
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Nur der Besitzer des Kanals kann ihn verstecken/anzeigen!", ephemeral=True)
            return
        
        try:
            self.hidden = not self.hidden
            everyone_role = interaction.guild.default_role
            
            if self.hidden:
                # Kanal verstecken
                await self.channel.set_permissions(everyone_role, view_channel=False)
                button.label = "Anzeigen"
                button.emoji = "👁️‍🗨️"
                button.style = discord.ButtonStyle.success
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Kanal versteckt! Nur Mitglieder im Kanal können ihn sehen.", ephemeral=True)
            else:
                # Kanal anzeigen
                await self.channel.set_permissions(everyone_role, view_channel=None)  # Zurücksetzen auf Standardwerte
                button.label = "Verstecken"
                button.emoji = "👁️"
                button.style = discord.ButtonStyle.secondary
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Kanal sichtbar! Alle können ihn jetzt sehen.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error toggling visibility: {e}")
            await interaction.response.send_message(f"Fehler beim Verstecken/Anzeigen des Kanals: {e}", ephemeral=True)
    
    @discord.ui.button(label="Nutzer verwalten", style=discord.ButtonStyle.primary, emoji="👤", custom_id="temp_voice:manage")
    async def manage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Verwalten von Nutzern im temporären Sprachkanal"""
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Nur der Besitzer des Kanals kann Nutzer verwalten!", ephemeral=True)
            return
        
        # Erstelle ein Select-Menü mit verschiedenen Aktionen
        select = discord.ui.Select(
            placeholder="Wähle eine Aktion",
            options=[
                discord.SelectOption(
                    label="Nutzer hinzufügen",
                    description="Erlaube einem Nutzer den Zugriff auf den Kanal",
                    emoji="➕",
                    value="add"
                ),
                discord.SelectOption(
                    label="Nutzer entfernen",
                    description="Entferne einen Nutzer aus dem Kanal",
                    emoji="➖",
                    value="remove"
                ),
                discord.SelectOption(
                    label="Nutzer stumm schalten",
                    description="Schalte einen Nutzer im Kanal stumm",
                    emoji="🔇",
                    value="mute"
                ),
                discord.SelectOption(
                    label="Stummschaltung aufheben",
                    description="Hebe die Stummschaltung eines Nutzers auf",
                    emoji="🔈",
                    value="unmute"
                )
            ]
        )
        
        async def select_callback(select_interaction):
            if select_interaction.data["values"][0] == "add":
                # Modal zum Eingeben des Nutzernamens/ID
                class AddUserModal(discord.ui.Modal, title="Nutzer hinzufügen"):
                    user_input = discord.ui.TextInput(
                        label="Nutzername oder ID",
                        placeholder="Gib den Nutzernamen oder die ID ein",
                        min_length=1,
                        required=True
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            # Versuche, den Nutzer zu finden
                            user = None
                            input_value = self.user_input.value
                            
                            # Prüfe, ob es eine ID ist
                            if input_value.isdigit():
                                user = modal_interaction.guild.get_member(int(input_value))
                            
                            # Wenn nicht gefunden, versuche nach Namen zu suchen
                            if not user:
                                for member in modal_interaction.guild.members:
                                    if input_value.lower() in member.name.lower() or (member.nick and input_value.lower() in member.nick.lower()):
                                        user = member
                                        break
                            
                            if not user:
                                await modal_interaction.response.send_message("Nutzer nicht gefunden!", ephemeral=True)
                                return
                            
                            # Erlaube dem Nutzer den Zugriff auf den Kanal
                            await self.channel.set_permissions(user, connect=True, view_channel=True)
                            await modal_interaction.response.send_message(f"{user.mention} wurde Zugriff auf den Kanal gewährt.", ephemeral=True)
                        
                        except Exception as e:
                            logger.error(f"Error adding user: {e}")
                            await modal_interaction.response.send_message(f"Fehler beim Hinzufügen des Nutzers: {e}", ephemeral=True)
                
                # Channel im Modal setzen
                modal = AddUserModal()
                modal.channel = self.channel
                
                await select_interaction.response.send_modal(modal)
            
            elif select_interaction.data["values"][0] == "remove":
                # Modal zum Eingeben des Nutzernamens/ID
                class RemoveUserModal(discord.ui.Modal, title="Nutzer entfernen"):
                    user_input = discord.ui.TextInput(
                        label="Nutzername oder ID",
                        placeholder="Gib den Nutzernamen oder die ID ein",
                        min_length=1,
                        required=True
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            # Versuche, den Nutzer zu finden
                            user = None
                            input_value = self.user_input.value
                            
                            # Prüfe, ob es eine ID ist
                            if input_value.isdigit():
                                user = modal_interaction.guild.get_member(int(input_value))
                            
                            # Wenn nicht gefunden, versuche nach Namen zu suchen
                            if not user:
                                for member in modal_interaction.guild.members:
                                    if input_value.lower() in member.name.lower() or (member.nick and input_value.lower() in member.nick.lower()):
                                        user = member
                                        break
                            
                            if not user:
                                await modal_interaction.response.send_message("Nutzer nicht gefunden!", ephemeral=True)
                                return
                            
                            # Verbiete dem Nutzer den Zugriff auf den Kanal
                            await self.channel.set_permissions(user, connect=False)
                            
                            # Wenn der Nutzer im Kanal ist, entferne ihn
                            if user.voice and user.voice.channel and user.voice.channel.id == self.channel.id:
                                try:
                                    # Versuche, den Nutzer in den AFK-Kanal zu verschieben, falls vorhanden
                                    if modal_interaction.guild.afk_channel:
                                        await user.move_to(modal_interaction.guild.afk_channel)
                                    else:
                                        # Ansonsten einfach trennen
                                        await user.move_to(None)
                                except:
                                    # Ignoriere Fehler beim Verschieben
                                    pass
                            
                            await modal_interaction.response.send_message(f"{user.mention} wurde aus dem Kanal entfernt.", ephemeral=True)
                        
                        except Exception as e:
                            logger.error(f"Error removing user: {e}")
                            await modal_interaction.response.send_message(f"Fehler beim Entfernen des Nutzers: {e}", ephemeral=True)
                
                # Channel im Modal setzen
                modal = RemoveUserModal()
                modal.channel = self.channel
                
                await select_interaction.response.send_modal(modal)
            
            elif select_interaction.data["values"][0] == "mute":
                # Modal zum Eingeben des Nutzernamens/ID
                class MuteUserModal(discord.ui.Modal, title="Nutzer stumm schalten"):
                    user_input = discord.ui.TextInput(
                        label="Nutzername oder ID",
                        placeholder="Gib den Nutzernamen oder die ID ein",
                        min_length=1,
                        required=True
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            # Versuche, den Nutzer zu finden
                            user = None
                            input_value = self.user_input.value
                            
                            # Prüfe, ob es eine ID ist
                            if input_value.isdigit():
                                user = modal_interaction.guild.get_member(int(input_value))
                            
                            # Wenn nicht gefunden, versuche nach Namen zu suchen
                            if not user:
                                for member in modal_interaction.guild.members:
                                    if input_value.lower() in member.name.lower() or (member.nick and input_value.lower() in member.nick.lower()):
                                        user = member
                                        break
                            
                            if not user:
                                await modal_interaction.response.send_message("Nutzer nicht gefunden!", ephemeral=True)
                                return
                            
                            # Prüfe, ob der Nutzer im Kanal ist
                            if not user.voice or not user.voice.channel or user.voice.channel.id != self.channel.id:
                                await modal_interaction.response.send_message(f"{user.mention} ist nicht in deinem Sprachkanal!", ephemeral=True)
                                return
                            
                            # Schalte den Nutzer stumm
                            await user.edit(mute=True)
                            await modal_interaction.response.send_message(f"{user.mention} wurde stumm geschaltet.", ephemeral=True)
                        
                        except Exception as e:
                            logger.error(f"Error muting user: {e}")
                            await modal_interaction.response.send_message(f"Fehler beim Stummschalten des Nutzers: {e}", ephemeral=True)
                
                # Channel im Modal setzen
                modal = MuteUserModal()
                modal.channel = self.channel
                
                await select_interaction.response.send_modal(modal)
            
            elif select_interaction.data["values"][0] == "unmute":
                # Modal zum Eingeben des Nutzernamens/ID
                class UnmuteUserModal(discord.ui.Modal, title="Stummschaltung aufheben"):
                    user_input = discord.ui.TextInput(
                        label="Nutzername oder ID",
                        placeholder="Gib den Nutzernamen oder die ID ein",
                        min_length=1,
                        required=True
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            # Versuche, den Nutzer zu finden
                            user = None
                            input_value = self.user_input.value
                            
                            # Prüfe, ob es eine ID ist
                            if input_value.isdigit():
                                user = modal_interaction.guild.get_member(int(input_value))
                            
                            # Wenn nicht gefunden, versuche nach Namen zu suchen
                            if not user:
                                for member in modal_interaction.guild.members:
                                    if input_value.lower() in member.name.lower() or (member.nick and input_value.lower() in member.nick.lower()):
                                        user = member
                                        break
                            
                            if not user:
                                await modal_interaction.response.send_message("Nutzer nicht gefunden!", ephemeral=True)
                                return
                            
                            # Prüfe, ob der Nutzer im Kanal ist
                            if not user.voice or not user.voice.channel or user.voice.channel.id != self.channel.id:
                                await modal_interaction.response.send_message(f"{user.mention} ist nicht in deinem Sprachkanal!", ephemeral=True)
                                return
                            
                            # Hebe die Stummschaltung auf
                            await user.edit(mute=False)
                            await modal_interaction.response.send_message(f"Stummschaltung von {user.mention} aufgehoben.", ephemeral=True)
                        
                        except Exception as e:
                            logger.error(f"Error unmuting user: {e}")
                            await modal_interaction.response.send_message(f"Fehler beim Aufheben der Stummschaltung: {e}", ephemeral=True)
                
                # Channel im Modal setzen
                modal = UnmuteUserModal()
                modal.channel = self.channel
                
                await select_interaction.response.send_modal(modal)
        
        select.callback = select_callback
        
        # Erstelle eine temporäre View nur für dieses Select-Menü
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.response.send_message("Wähle eine Aktion zur Nutzerverwaltung:", view=view, ephemeral=True)

class TempVoice(commands.Cog):
    """Cog für temporäre Sprachkanäle."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "temp_voice.json"
        self.temp_voice_data = self._load_temp_voice_data()
        self.active_temp_channels = {}  # Format: {channel_id: {"owner_id": owner_id, "control_message": message}}
        self.check_empty_channels.start()
        
        logger.info("TempVoice cog initialized")
        
    def _load_temp_voice_data(self):
        """Laden der TempVoice-Daten aus der Datei."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Erstellen von Default-Daten
            default_data = {
                "settings": {},  # Format: {"guild_id": {"category_id": category_id, "create_channel_id": create_channel_id}}
                "temp_channels": {}  # Format: {"channel_id": {"owner_id": owner_id, "guild_id": guild_id}}
            }
            self._save_temp_voice_data(default_data)
            return default_data
    
    def _save_temp_voice_data(self, data=None):
        """Speichern der TempVoice-Daten in der Datei."""
        if data is None:
            data = self.temp_voice_data
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    @commands.hybrid_command(name="setupvoice", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setup_temp_voice(self, ctx: commands.Context, category: discord.CategoryChannel = None):
        """
        Richtet temporäre Sprachkanäle ein.
        
        Args:
            category: Die Kategorie, in der die temporären Sprachkanäle erstellt werden sollen. Wenn keine angegeben ist, wird eine neue erstellt.
        """
        try:
            guild_id = str(ctx.guild.id)
            
            # Erstelle eine neue Kategorie, wenn keine angegeben wurde
            if not category:
                category = await ctx.guild.create_category("Temporäre Sprachkanäle")
            
            # Erstelle die Tempvoice-Kanäle für verschiedene Optionen
            create_channel = await ctx.guild.create_voice_channel(
                name="🎮 Tempvoice: Gaming",
                category=category
            )
            
            create_channel2 = await ctx.guild.create_voice_channel(
                name="🎵 Tempvoice: Musik",
                category=category
            )
            
            create_channel3 = await ctx.guild.create_voice_channel(
                name="🎲 Tempvoice: Allgemein",
                category=category
            )
            
            create_channel4 = await ctx.guild.create_voice_channel(
                name="👥 Tempvoice: Privat",
                category=category
            )
            
            # Speichere die Einstellungen
            if guild_id not in self.temp_voice_data["settings"]:
                self.temp_voice_data["settings"][guild_id] = {}
            
            self.temp_voice_data["settings"][guild_id]["category_id"] = category.id
            self.temp_voice_data["settings"][guild_id]["create_channels"] = [
                create_channel.id,
                create_channel2.id,
                create_channel3.id,
                create_channel4.id
            ]
            
            self._save_temp_voice_data()
            
            # Sende eine Bestätigung
            embed = discord.Embed(
                title="Temporäre Sprachkanäle eingerichtet",
                description=f"Temporäre Sprachkanäle wurden erfolgreich eingerichtet!\n\n"
                            f"Kategorie: {category.name}\n"
                            f"Tempvoice-Kanäle:\n"
                            f"• {create_channel.mention} (Gaming)\n"
                            f"• {create_channel2.mention} (Musik)\n"
                            f"• {create_channel3.mention} (Allgemein)\n"
                            f"• {create_channel4.mention} (Privat)\n\n"
                            f"Nutzer können einem dieser Kanäle beitreten, um einen temporären Sprachkanal zu erstellen.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error setting up temp voice: {e}")
            await ctx.send(f"Fehler beim Einrichten der temporären Sprachkanäle: {e}")
    
    @commands.hybrid_command(name="removevoice", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def remove_temp_voice(self, ctx: commands.Context):
        """
        Entfernt die Einrichtung für temporäre Sprachkanäle.
        """
        try:
            guild_id = str(ctx.guild.id)
            
            # Prüfe, ob temporäre Sprachkanäle eingerichtet sind
            if guild_id not in self.temp_voice_data["settings"]:
                await ctx.send("Temporäre Sprachkanäle sind nicht eingerichtet!")
                return
            
            # Lösche alle Tempvoice-Kanäle
            create_channels = self.temp_voice_data["settings"][guild_id].get("create_channels", [])
            for channel_id in create_channels:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    await channel.delete()
                    
            # Alte Kompatibilität (für alte Installationen)
            create_channel_id = self.temp_voice_data["settings"][guild_id].get("create_channel_id")
            if create_channel_id:
                create_channel = ctx.guild.get_channel(create_channel_id)
                if create_channel:
                    await create_channel.delete()
            
            # Entferne die Einstellungen
            del self.temp_voice_data["settings"][guild_id]
            
            # Entferne auch alle temporären Kanäle dieses Servers aus den Daten
            temp_channels_to_remove = []
            for channel_id, channel_data in self.temp_voice_data["temp_channels"].items():
                if channel_data.get("guild_id") == guild_id:
                    temp_channels_to_remove.append(channel_id)
            
            for channel_id in temp_channels_to_remove:
                del self.temp_voice_data["temp_channels"][channel_id]
            
            self._save_temp_voice_data()
            
            # Sende eine Bestätigung
            embed = discord.Embed(
                title="Temporäre Sprachkanäle entfernt",
                description="Die Einrichtung für temporäre Sprachkanäle wurde erfolgreich entfernt.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error removing temp voice: {e}")
            await ctx.send(f"Fehler beim Entfernen der temporären Sprachkanäle: {e}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Event-Handler für Änderungen des Voice-Status."""
        # Wenn ein Nutzer einen Sprachkanal betritt
        if after.channel and not before.channel:
            # Prüfe, ob es einer der Erstellungskanäle ist
            guild_id = str(member.guild.id)
            if guild_id in self.temp_voice_data["settings"]:
                # Prüfe zuerst die neue multi-channel Konfiguration
                create_channels = self.temp_voice_data["settings"][guild_id].get("create_channels", [])
                if after.channel.id in create_channels:
                    # Bestimme den Kanaltyp basierend auf dem Namen für individualisierte Kanäle
                    channel_name = f"{member.display_name}'s Kanal"
                    
                    if "gaming" in after.channel.name.lower():
                        channel_name = f"🎮 {member.display_name}'s Gaming-Kanal"
                    elif "musik" in after.channel.name.lower():
                        channel_name = f"🎵 {member.display_name}'s Musik-Kanal"
                    elif "allgemein" in after.channel.name.lower():
                        channel_name = f"🎲 {member.display_name}'s Kanal"
                    elif "privat" in after.channel.name.lower():
                        channel_name = f"👥 {member.display_name}'s Privater Kanal"
                    
                    # Erstelle einen temporären Sprachkanal mit angepasstem Namen
                    await self._create_temp_channel(member, custom_name=channel_name)
                    return  # Früher Exit, um die alte Konfiguration zu überspringen
                
                # Kompatibilität mit alten Konfigurationen
                create_channel_id = self.temp_voice_data["settings"][guild_id].get("create_channel_id")
                if create_channel_id and after.channel.id == create_channel_id:
                    # Erstelle einen temporären Sprachkanal
                    await self._create_temp_channel(member)
        
        # Wenn ein Nutzer einen Sprachkanal verlässt
        elif before.channel and not after.channel:
            # Prüfe, ob es ein temporärer Kanal ist und ob er leer ist
            channel_id = str(before.channel.id)
            if channel_id in self.temp_voice_data["temp_channels"]:
                # Prüfe, ob der Kanal leer ist
                if len(before.channel.members) == 0:
                    # Lösche den Kanal
                    await self._delete_temp_channel(before.channel)
        
        # Wenn ein Nutzer den Sprachkanal wechselt
        elif before.channel and after.channel and before.channel != after.channel:
            # Prüfe, ob der verlassene Kanal ein temporärer Kanal ist und ob er leer ist
            channel_id = str(before.channel.id)
            if channel_id in self.temp_voice_data["temp_channels"]:
                # Prüfe, ob der Kanal leer ist
                if len(before.channel.members) == 0:
                    # Lösche den Kanal
                    await self._delete_temp_channel(before.channel)
            
            # Prüfe, ob der betretene Kanal einer der Erstellungskanäle ist
            guild_id = str(member.guild.id)
            if guild_id in self.temp_voice_data["settings"]:
                # Prüfe zuerst die neue multi-channel Konfiguration
                create_channels = self.temp_voice_data["settings"][guild_id].get("create_channels", [])
                if after.channel.id in create_channels:
                    # Bestimme den Kanaltyp basierend auf dem Namen für individualisierte Kanäle
                    channel_name = f"{member.display_name}'s Kanal"
                    
                    if "gaming" in after.channel.name.lower():
                        channel_name = f"🎮 {member.display_name}'s Gaming-Kanal"
                    elif "musik" in after.channel.name.lower():
                        channel_name = f"🎵 {member.display_name}'s Musik-Kanal"
                    elif "allgemein" in after.channel.name.lower():
                        channel_name = f"🎲 {member.display_name}'s Kanal"
                    elif "privat" in after.channel.name.lower():
                        channel_name = f"👥 {member.display_name}'s Privater Kanal"
                    
                    # Erstelle einen temporären Sprachkanal mit angepasstem Namen
                    await self._create_temp_channel(member, custom_name=channel_name)
                    return  # Früher Exit, um die alte Konfiguration zu überspringen
                
                # Kompatibilität mit alten Konfigurationen
                create_channel_id = self.temp_voice_data["settings"][guild_id].get("create_channel_id")
                if create_channel_id and after.channel.id == create_channel_id:
                    # Erstelle einen temporären Sprachkanal
                    await self._create_temp_channel(member)
    
    async def _create_temp_channel(self, member: discord.Member, custom_name=None):
        """Erstellt einen temporären Sprachkanal für einen Nutzer."""
        try:
            guild_id = str(member.guild.id)
            
            # Hole die Kategorie
            category_id = self.temp_voice_data["settings"][guild_id].get("category_id")
            category = member.guild.get_channel(category_id)
            
            if not category:
                logger.error(f"Category not found for temp voice: {category_id}")
                return
            
            # Erstelle den Kanal mit benutzerdefiniertem Namen, wenn vorhanden
            channel_name = custom_name if custom_name else f"{member.display_name}'s Kanal"
            temp_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category
            )
            
            # Bewege den Nutzer in den neuen Kanal
            await member.move_to(temp_channel)
            
            # Speichere den Kanal in den Daten
            self.temp_voice_data["temp_channels"][str(temp_channel.id)] = {
                "owner_id": member.id,
                "guild_id": guild_id
            }
            
            self._save_temp_voice_data()
            
            # Sende eine Kontrollnachricht an den Nutzer
            control_embed = discord.Embed(
                title="Temporärer Sprachkanal erstellt",
                description=f"Du hast einen temporären Sprachkanal erstellt: {temp_channel.mention}\n\n"
                            f"Nutze die Buttons unten, um deinen Kanal zu verwalten.",
                color=discord.Color.blue()
            )
            
            # Erstelle die UI
            ui = TempVoiceUI(member, temp_channel, self.bot)
            
            # Sende die Nachricht in einem separaten TextChannel, wenn möglich, sonst als DM
            try:
                # Versuche, einen Textkanal in derselben Kategorie zu finden
                text_channel = None
                for channel in category.text_channels:
                    if "temp" in channel.name.lower() or "voice" in channel.name.lower() or "control" in channel.name.lower():
                        text_channel = channel
                        break
                
                # Wenn kein passender Textkanal gefunden wurde, erstelle einen neuen
                if not text_channel:
                    text_channel = await member.guild.create_text_channel(
                        name="voice-control",
                        category=category,
                        topic="Kontrolliere deine temporären Sprachkanäle hier"
                    )
                
                # Sende die Nachricht
                control_message = await text_channel.send(
                    content=f"{member.mention}",
                    embed=control_embed,
                    view=ui
                )
                
                # Speichere die Kontrollnachricht
                self.active_temp_channels[temp_channel.id] = {
                    "owner_id": member.id,
                    "control_message": control_message
                }
                
            except Exception as e:
                logger.error(f"Error sending control message to text channel: {e}")
                
                # Versuche, eine DM zu senden
                try:
                    control_message = await member.send(
                        embed=control_embed,
                        view=ui
                    )
                    
                    # Speichere die Kontrollnachricht
                    self.active_temp_channels[temp_channel.id] = {
                        "owner_id": member.id,
                        "control_message": control_message
                    }
                except:
                    logger.error("Could not send DM to user")
            
            logger.info(f"Created temp voice channel for {member.display_name}")
            
        except Exception as e:
            logger.error(f"Error creating temp channel: {e}")
    
    async def _delete_temp_channel(self, channel: discord.VoiceChannel):
        """Löscht einen temporären Sprachkanal."""
        try:
            channel_id = str(channel.id)
            
            # Entferne den Kanal aus den Daten
            if channel_id in self.temp_voice_data["temp_channels"]:
                del self.temp_voice_data["temp_channels"][channel_id]
                self._save_temp_voice_data()
            
            # Lösche die Kontrollnachricht, wenn vorhanden
            if channel.id in self.active_temp_channels:
                control_message = self.active_temp_channels[channel.id].get("control_message")
                if control_message:
                    try:
                        await control_message.delete()
                    except:
                        pass
                
                # Entferne den Kanal aus den aktiven Kanälen
                del self.active_temp_channels[channel.id]
            
            # Lösche den Kanal
            await channel.delete()
            
            logger.info(f"Deleted temp voice channel: {channel.name}")
            
        except Exception as e:
            logger.error(f"Error deleting temp channel: {e}")
    
    @tasks.loop(minutes=5)
    async def check_empty_channels(self):
        """Überprüft regelmäßig, ob leere temporäre Kanäle existieren."""
        try:
            # Kopiere die Daten, um Änderungen während der Iteration zu vermeiden
            temp_channels = dict(self.temp_voice_data["temp_channels"])
            
            for channel_id, channel_data in temp_channels.items():
                # Hole den Kanal
                guild_id = channel_data.get("guild_id")
                if not guild_id:
                    continue
                
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                
                channel = guild.get_channel(int(channel_id))
                
                # Wenn der Kanal nicht existiert oder leer ist, lösche ihn
                if not channel or len(channel.members) == 0:
                    if channel:
                        await self._delete_temp_channel(channel)
                    else:
                        # Wenn der Kanal nicht existiert, entferne ihn aus den Daten
                        del self.temp_voice_data["temp_channels"][channel_id]
                        self._save_temp_voice_data()
                        
                        # Entferne auch die Kontrollnachricht, wenn vorhanden
                        if int(channel_id) in self.active_temp_channels:
                            control_message = self.active_temp_channels[int(channel_id)].get("control_message")
                            if control_message:
                                try:
                                    await control_message.delete()
                                except:
                                    pass
                            
                            # Entferne den Kanal aus den aktiven Kanälen
                            del self.active_temp_channels[int(channel_id)]
            
        except Exception as e:
            logger.error(f"Error checking empty channels: {e}")
    
    @check_empty_channels.before_loop
    async def before_check_empty_channels(self):
        """Wartet, bis der Bot bereit ist, bevor die Loop gestartet wird."""
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        """Wird aufgerufen, wenn der Cog entladen wird."""
        # Stoppe die Loop
        self.check_empty_channels.cancel()

async def setup(bot: commands.Bot):
    """Füge die TempVoice-Cog zum Bot hinzu."""
    await bot.add_cog(TempVoice(bot))
    logger.info("TempVoice cog loaded")
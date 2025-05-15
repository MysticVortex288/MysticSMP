import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import logging
import os
from typing import Dict, List, Optional, Union

logger = logging.getLogger('discord_bot')

class RoleButton(ui.Button):
    """Button für das Hinzufügen/Entfernen einer Rolle."""
    
    def __init__(self, role_id: int, style: discord.ButtonStyle, emoji: str = None, label: str = None):
        super().__init__(
            style=style,
            label=label,
            emoji=emoji,
            custom_id=f"role_button:{role_id}"
        )
        self.role_id = role_id
    
    async def callback(self, interaction: discord.Interaction):
        """Wird aufgerufen, wenn der Button geklickt wird."""
        guild = interaction.guild
        user = interaction.user
        role = guild.get_role(self.role_id)
        
        if not role:
            await interaction.response.send_message(
                f"⚠️ Die Rolle konnte nicht gefunden werden. Bitte informiere einen Administrator.",
                ephemeral=True
            )
            return
        
        # Hole die Panel-Informationen
        view = self.view
        panel_id = view.panel_id if hasattr(view, 'panel_id') else None
        
        # Farb- oder andere exklusive Rollensätze behandeln
        # Dies wird für Farbrollensets verwendet
        is_exclusive_panel = False
        panel_roles = []
        
        # Lade die Konfiguration um zu prüfen, ob dies ein exklusives Panel ist
        try:
            config_file = "self_roles.json"
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Suche nach dem Panel in der Konfiguration
            for guild_id, guild_data in config.items():
                if "panels" in guild_data:
                    for panel in guild_data["panels"]:
                        if panel.get("panel_id") == panel_id:
                            # Prüfe, ob es ein exklusives Panel ist (wie Farbrollen)
                            is_exclusive_panel = panel.get("is_exclusive", False)
                            
                            # Hole alle Rollen des Panels
                            panel_roles = [guild.get_role(role_info["role_id"]) for role_info in panel["roles"] 
                                          if guild.get_role(role_info["role_id"]) is not None]
                            break
        except Exception as e:
            logger.error(f"Fehler beim Laden der Panel-Konfiguration: {e}")
            # Im Fehlerfall behandeln wir es wie ein normales Panel
        
        if role in user.roles:
            # Rolle entfernen
            # Prüfe ob es eine Farbrolle ist (beginnt mit "Farbe: ")
            is_color_role = role.name.startswith("Farbe: ")
            
            # Bei Farbrollen zeigen wir eine andere Nachricht an
            if is_color_role:
                await user.remove_roles(role)
                await interaction.response.send_message(
                    f"🎨 Die Farbmarkierung **{role.name}** wurde entfernt. Dein Name wird jetzt ohne Farbe angezeigt.",
                    ephemeral=True
                )
                logger.info(f"User {user.display_name} removed color role {role.name}")
            else:
                # Normale Rolle entfernen
                await user.remove_roles(role)
                await interaction.response.send_message(
                    f"✅ Die Rolle **{role.name}** wurde entfernt!",
                    ephemeral=True
                )
                logger.info(f"User {user.display_name} removed role {role.name}")
        else:
            # Rolle hinzufügen
            # Bei exklusiven Panels (wie Farbrollen) zuerst alle anderen Rollen dieses Panels entfernen
            if is_exclusive_panel and panel_roles:
                roles_to_remove = [r for r in panel_roles if r in user.roles]
                if roles_to_remove:
                    await user.remove_roles(*roles_to_remove)
                    logger.info(f"Entferne andere Farbrollen für {user.display_name}: {', '.join([r.name for r in roles_to_remove])}")
            
            # Prüfe ob es eine Farbrolle ist
            is_color_role = role.name.startswith("Farbe: ")
            
            await user.add_roles(role)
            
            # Bei Farbrollen zeigen wir eine angepasste Nachricht an
            if is_color_role:
                color_name = role.name.replace("Farbe: ", "")
                await interaction.response.send_message(
                    f"🎨 Die Farbe **{color_name}** wurde deinem Namen hinzugefügt!",
                    ephemeral=True
                )
                logger.info(f"User {user.display_name} added color role {role.name}")
            else:
                # Standardnachricht für normale Rollen
                await interaction.response.send_message(
                    f"✅ Die Rolle **{role.name}** wurde hinzugefügt!",
                    ephemeral=True
                )
                logger.info(f"User {user.display_name} added role {role.name}")

class RoleView(ui.View):
    """View für die Darstellung von Rollenbuttons."""
    
    def __init__(self, panel_id: str):
        super().__init__(timeout=None)
        self.panel_id = panel_id

class SelfRoles(commands.Cog):
    """Cog für Self-Roles, mit denen sich Benutzer selbst Rollen zuweisen können."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "self_roles.json"
        self.config = self._load_config()
        self.persistent_views_added = False
        self.active_sessions = {}  # Speichert aktive Erstellungssessions mit Benutzern als Schlüssel
        
        logger.info("SelfRoles cog initialized")
    
    def _load_config(self):
        """Lade die Konfiguration aus der Datei."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Erstellen von Default-Daten
            default_data = {}
            self._save_config(default_data)
            return default_data
    
    def _save_config(self, config=None):
        """Speichere die Konfiguration in der Datei."""
        if config is None:
            config = self.config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    async def _create_panel_view(self, panel):
        """Erstellt ein View für ein Rollenpanel."""
        view = RoleView(panel["panel_id"])
        
        # Wenn Kategorien existieren, organisiee die Buttons nach Kategorien
        if "categories" in panel and panel["categories"]:
            # Iteriere durch jede Kategorie und füge deren Rollen hinzu
            for category in panel["categories"]:
                for role_info in panel["roles"]:
                    if role_info.get("category_id") == category["id"]:
                        # Konvertiere den Stil-String in ButtonStyle
                        style_map = {
                            "primary": discord.ButtonStyle.primary,
                            "secondary": discord.ButtonStyle.secondary,
                            "success": discord.ButtonStyle.success,
                            "danger": discord.ButtonStyle.danger,
                            "blurple": discord.ButtonStyle.primary,
                            "grey": discord.ButtonStyle.secondary,
                            "green": discord.ButtonStyle.success,
                            "red": discord.ButtonStyle.danger
                        }
                        
                        style = style_map.get(role_info.get("style", "primary").lower(), discord.ButtonStyle.primary)
                        
                        # Erstelle den Button
                        button = RoleButton(
                            role_id=role_info["role_id"],
                            style=style,
                            emoji=role_info.get("emoji"),
                            label=role_info.get("label")
                        )
                        
                        view.add_item(button)
        else:
            # Altes Format ohne Kategorien - einfach alle Buttons hinzufügen
            for role_info in panel["roles"]:
                # Konvertiere den Stil-String in ButtonStyle
                style_map = {
                    "primary": discord.ButtonStyle.primary,
                    "secondary": discord.ButtonStyle.secondary,
                    "success": discord.ButtonStyle.success,
                    "danger": discord.ButtonStyle.danger,
                    "blurple": discord.ButtonStyle.primary,
                    "grey": discord.ButtonStyle.secondary,
                    "green": discord.ButtonStyle.success,
                    "red": discord.ButtonStyle.danger
                }
                
                style = style_map.get(role_info.get("style", "primary").lower(), discord.ButtonStyle.primary)
                
                # Erstelle den Button
                button = RoleButton(
                    role_id=role_info["role_id"],
                    style=style,
                    emoji=role_info.get("emoji"),
                    label=role_info.get("label")
                )
                
                view.add_item(button)
        
        return view
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Wird aufgerufen, wenn der Bot bereit ist."""
        if not self.persistent_views_added:
            # Füge persistente Views für alle bestehenden Panels hinzu
            for guild_id, guild_data in self.config.items():
                if "panels" in guild_data:
                    for panel in guild_data["panels"]:
                        view = await self._create_panel_view(panel)
                        self.bot.add_view(view)
            
            self.persistent_views_added = True
            logger.info("Added persistent views for role panels")
    
    @commands.hybrid_command(name="createcolors", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def create_color_roles(self, ctx: commands.Context):
        """
        Erstellt ein Panel mit verschiedenen Farbrollen für Benutzer.
        """
        guild_id = str(ctx.guild.id)
        
        # Erstelle Guild-Eintrag falls nötig
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "panels" not in self.config[guild_id]:
            self.config[guild_id]["panels"] = []
        
        # Definiere die verfügbaren Farben 
        colors = [
            {"name": "Rot", "color": discord.Color.red(), "emoji": "🔴", "style": "danger"},
            {"name": "Blau", "color": discord.Color.blue(), "emoji": "🔵", "style": "primary"},
            {"name": "Grün", "color": discord.Color.green(), "emoji": "🟢", "style": "success"},
            {"name": "Gelb", "color": discord.Color(0xFFD700), "emoji": "🟡", "style": "primary"},
            {"name": "Orange", "color": discord.Color(0xFF8C00), "emoji": "🟠", "style": "danger"},
            {"name": "Lila", "color": discord.Color.purple(), "emoji": "🟣", "style": "primary"},
            {"name": "Pink", "color": discord.Color(0xFF69B4), "emoji": "💗", "style": "danger"},
            {"name": "Türkis", "color": discord.Color.teal(), "emoji": "💙", "style": "primary"},
            {"name": "Weiß", "color": discord.Color.light_grey(), "emoji": "⚪", "style": "secondary"},
            {"name": "Schwarz", "color": discord.Color.dark_grey(), "emoji": "⚫", "style": "secondary"}
        ]
        
        await ctx.send("🎨 Erstelle Farbrollen-Panel... Dies kann einen Moment dauern.")
        
        # Erstelle oder finde die Rollen
        roles = []
        for color_info in colors:
            role_name = f"Farbe: {color_info['name']}"
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            
            if role is None:
                try:
                    # Erstelle die Rolle mit der angegebenen Farbe
                    role = await ctx.guild.create_role(
                        name=role_name,
                        color=color_info["color"],
                        reason="Farbrolle für Self-Roles Panel"
                    )
                    await ctx.send(f"✅ Rolle **{role_name}** erstellt!")
                except discord.Forbidden:
                    await ctx.send(f"❌ Ich habe keine Berechtigung, die Rolle **{role_name}** zu erstellen.")
                    continue
                except discord.HTTPException as e:
                    await ctx.send(f"❌ Fehler beim Erstellen der Rolle **{role_name}**: {e}")
                    continue
            
            roles.append({
                "role_id": role.id,
                "style": color_info["style"],
                "emoji": color_info["emoji"],
                "label": color_info["name"]
            })
        
        # Erstelle ein neues Panel mit eindeutiger ID
        panel_id = f"{guild_id}_{len(self.config[guild_id]['panels'])}"
        
        panel = {
            "panel_id": panel_id,
            "title": "Farbrollen",
            "description": "Wähle deine Lieblingsfarbe für deinen Namen! Du kannst nur eine Farbe gleichzeitig haben.",
            "roles": roles,
            "is_exclusive": True,  # Nur eine Farbrolle kann gleichzeitig ausgewählt werden
            "categories": []
        }
        
        # Frage nach dem Kanal, in dem das Panel erstellt werden soll
        await ctx.send("📝 In welchem Kanal soll das Farbrollen-Panel erstellt werden? Bitte gib den Namen oder die ID an.")
        
        # Warte auf die Kanalangabe
        channel_message = await self.bot.wait_for(
            "message", 
            timeout=60.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        
        if channel_message.content.lower() == "abbrechen":
            await ctx.send("✅ Der Vorgang wurde abgebrochen.")
            return
        
        # Versuche, den Kanal zu finden
        channel = None
        try:
            # Versuche zuerst als ID
            channel_id = int(channel_message.content.strip())
            channel = ctx.guild.get_channel(channel_id)
        except ValueError:
            # Wenn keine gültige ID, suche nach Namen
            channel_name = channel_message.content.strip()
            channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
        
        if not channel:
            await ctx.send("❌ Der angegebene Kanal konnte nicht gefunden werden. Der Vorgang wird abgebrochen.")
            return
        
        # Erstelle das Embed für das Panel
        embed = discord.Embed(
            title=panel["title"],
            description=panel["description"],
            color=discord.Color.blue()
        )
        
        # Füge Beschreibungen für die Farben hinzu
        for role_info in roles:
            role = ctx.guild.get_role(role_info["role_id"])
            embed.add_field(
                name=f"{role_info['emoji']} {role_info['label']}",
                value=f"Klicke auf den Button, um die Farbe auszuwählen.",
                inline=True
            )
        
        # Erstelle die View mit den Buttons
        view = await self._create_panel_view(panel)
        
        # Sende das Embed mit der View
        try:
            message = await channel.send(embed=embed, view=view)
            panel["channel_id"] = channel.id
            panel["message_id"] = message.id
            
            # Speichere das Panel in der Konfiguration
            self.config[guild_id]["panels"].append(panel)
            self._save_config()
            
            await ctx.send(f"✅ Farbrollen-Panel erfolgreich in {channel.mention} erstellt!")
            logger.info(f"Color roles panel created in guild {ctx.guild.name} by {ctx.author.display_name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Ich habe keine Berechtigung, Nachrichten in {channel.mention} zu senden.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Fehler beim Erstellen des Panels: {e}")
            
    @commands.hybrid_command(name="createroles", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def create_roles_panel(self, ctx: commands.Context):
        """
        Startet den Assistenten zum Erstellen eines Self-Roles-Panels mit Kategorien.
        """
        # Initialisiere die Session für diesen Benutzer
        user_id = ctx.author.id
        guild_id = str(ctx.guild.id)
        
        # Erstelle Guild-Eintrag falls nötig
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "panels" not in self.config[guild_id]:
            self.config[guild_id]["panels"] = []
        
        # Sende eine schöne Willkommensnachricht
        embed = discord.Embed(
            title="🏷️ Self-Roles Panel-Assistent",
            description="Willkommen beim Assistenten zum Erstellen eines Self-Roles Panels! Ich führe dich durch den Prozess.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Schritt 1: Titel wählen",
            value="Bitte gib einen Titel für dein Panel ein.",
            inline=False
        )
        
        embed.set_footer(text="Du kannst jederzeit 'abbrechen' eingeben, um den Vorgang abzubrechen.")
        
        await ctx.send(embed=embed)
        
        # Warte auf den Titel
        title_message = await self.bot.wait_for(
            "message", 
            timeout=120.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        
        if title_message.content.lower() == "abbrechen":
            await ctx.send("✅ Der Vorgang wurde abgebrochen.")
            return
        
        title = title_message.content
        
        # Frage nach der Beschreibung
        embed = discord.Embed(
            title="🏷️ Self-Roles Panel-Assistent",
            description=f"**Titel:** {title}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Schritt 2: Beschreibung hinzufügen",
            value="Bitte gib eine Beschreibung für dein Panel ein, oder schreibe 'keine' für keine Beschreibung.",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Warte auf die Beschreibung
        description_message = await self.bot.wait_for(
            "message", 
            timeout=240.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        
        if description_message.content.lower() == "abbrechen":
            await ctx.send("✅ Der Vorgang wurde abgebrochen.")
            return
        
        description = None if description_message.content.lower() == "keine" else description_message.content
        
        # Frage nach Kategorien
        categories = []
        
        embed = discord.Embed(
            title="🏷️ Self-Roles Panel-Assistent",
            description=f"**Titel:** {title}\n**Beschreibung:** {description or 'Keine'}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Schritt 3: Kategorien erstellen",
            value=(
                "Du kannst deine Rollen in Kategorien organisieren. Für jede Kategorie, gib den Namen ein.\n"
                "Schreibe 'weiter', wenn du keine weiteren Kategorien hinzufügen möchtest."
            ),
            inline=False
        )
        
        if not categories:
            embed.add_field(
                name="Hinweis",
                value="Wenn du keine Kategorien hinzufügst, werden alle Rollen ohne Kategorien angezeigt.",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # Sammle Kategorien
        adding_categories = True
        while adding_categories:
            category_message = await self.bot.wait_for(
                "message", 
                timeout=120.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            
            if category_message.content.lower() == "abbrechen":
                await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                return
            
            if category_message.content.lower() == "weiter":
                adding_categories = False
                continue
            
            # Erstelle eine neue Kategorie mit eindeutiger ID
            category_id = f"cat_{len(categories)}"
            category_name = category_message.content
            
            categories.append({
                "id": category_id,
                "name": category_name
            })
            
            await ctx.send(f"✅ Kategorie **{category_name}** hinzugefügt!")
        
        # Jetzt sammle die Rollen pro Kategorie
        roles = []
        
        if categories:
            for category in categories:
                embed = discord.Embed(
                    title=f"🏷️ Rollen für Kategorie: {category['name']}",
                    description=(
                        "Füge Rollen zu dieser Kategorie hinzu. Für jede Rolle, gib folgendes ein:\n"
                        "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
                        "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                        "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
                        "Wenn du fertig mit dieser Kategorie bist, schreibe `weiter`."
                    ),
                    color=discord.Color.blue()
                )
                
                await ctx.send(embed=embed)
                
                # Sammle Rollen für diese Kategorie
                adding_roles = True
                while adding_roles:
                    role_message = await self.bot.wait_for(
                        "message", 
                        timeout=180.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if role_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    if role_message.content.lower() == "weiter":
                        adding_roles = False
                        continue
                    
                    # Verarbeite die Eingabe
                    parts = role_message.content.split()
                    if len(parts) < 1:
                        await ctx.send("⚠️ Du musst mindestens einen Rollennamen angeben.")
                        continue
                    
                    # Der erste Teil ist der Rollenname
                    role_name = parts[0]
                    
                    # Extrahiere das Emoji, wenn vorhanden
                    emoji = None
                    for part in parts[1:]:
                        if len(part) == 1 or (len(part) > 1 and ord(part[0]) > 127):  # Einfacher Check auf Emoji
                            emoji = part
                            break
                    
                    # Extrahiere die Farbe, wenn vorhanden
                    color_map = {
                        "blurple": "primary",
                        "grey": "secondary",
                        "gray": "secondary",
                        "green": "success",
                        "red": "danger",
                        "primary": "primary",
                        "secondary": "secondary",
                        "success": "success",
                        "danger": "danger"
                    }
                    
                    style = "primary"  # Standard
                    button_color = discord.Color.blurple()  # Standardfarbe für die Rolle
                    
                    for part in parts:
                        lower_part = part.lower()
                        if lower_part in color_map:
                            style = color_map[lower_part]
                            # Setze die entsprechende Rollenfarbe basierend auf dem Button-Stil
                            if lower_part in ["blurple", "primary"]:
                                button_color = discord.Color.blurple()
                            elif lower_part in ["grey", "gray", "secondary"]:
                                button_color = discord.Color.light_grey()
                            elif lower_part in ["green", "success"]:
                                button_color = discord.Color.green()
                            elif lower_part in ["red", "danger"]:
                                button_color = discord.Color.red()
                            break
                    
                    # Suche nach einer vorhandenen Rolle mit dem Namen oder erstelle eine neue
                    role = discord.utils.get(ctx.guild.roles, name=role_name)
                    
                    if role is None:
                        try:
                            # Erstelle die Rolle mit dem angegebenen Namen und der Farbe
                            role = await ctx.guild.create_role(
                                name=role_name,
                                color=button_color,
                                reason=f"Self-Roles Panel erstellt von {ctx.author.display_name}"
                            )
                            await ctx.send(f"✅ Neue Rolle **{role_name}** wurde erstellt!")
                        except discord.Forbidden:
                            await ctx.send("❌ Ich habe keine Berechtigung, Rollen zu erstellen. Bitte gib mir die entsprechende Berechtigung.")
                            continue
                        except discord.HTTPException as e:
                            await ctx.send(f"❌ Fehler beim Erstellen der Rolle: {str(e)}")
                            continue
                    
                    # Füge die Rolle zur Liste hinzu
                    roles.append({
                        "role_id": role.id,
                        "style": style,
                        "emoji": emoji,
                        "label": role.name,
                        "category_id": category["id"]
                    })
                    
                    await ctx.send(f"✅ Rolle **{role.name}** mit Emoji {emoji or 'keinem'} und Farbe {style} hinzugefügt zu Kategorie **{category['name']}**!")
        else:
            # Keine Kategorien - sammle alle Rollen direkt
            embed = discord.Embed(
                title="🏷️ Rollen hinzufügen",
                description=(
                    "Füge Rollen zu deinem Panel hinzu. Für jede Rolle, gib folgendes ein:\n"
                    "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
                    "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                    "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
                    "Wenn du fertig bist, schreibe `fertig`."
                ),
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
            
            # Sammle Rollen
            adding_roles = True
            while adding_roles:
                role_message = await self.bot.wait_for(
                    "message", 
                    timeout=180.0, 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                
                if role_message.content.lower() in ["fertig", "weiter"]:
                    adding_roles = False
                    continue
                
                if role_message.content.lower() == "abbrechen":
                    await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                    return
                
                # Verarbeite die Eingabe
                parts = role_message.content.split()
                if len(parts) < 1:
                    await ctx.send("⚠️ Du musst mindestens einen Rollennamen angeben.")
                    continue
                
                # Der erste Teil ist der Rollenname
                role_name = parts[0]
                
                # Extrahiere das Emoji, wenn vorhanden
                emoji = None
                for part in parts[1:]:
                    if len(part) == 1 or (len(part) > 1 and ord(part[0]) > 127):  # Einfacher Check auf Emoji
                        emoji = part
                        break
                
                # Extrahiere die Farbe, wenn vorhanden
                color_map = {
                    "blurple": "primary",
                    "grey": "secondary",
                    "gray": "secondary",
                    "green": "success",
                    "red": "danger",
                    "primary": "primary",
                    "secondary": "secondary",
                    "success": "success",
                    "danger": "danger"
                }
                
                style = "primary"  # Standard
                button_color = discord.Color.blurple()  # Standardfarbe für die Rolle
                
                for part in parts:
                    lower_part = part.lower()
                    if lower_part in color_map:
                        style = color_map[lower_part]
                        # Setze die entsprechende Rollenfarbe basierend auf dem Button-Stil
                        if lower_part in ["blurple", "primary"]:
                            button_color = discord.Color.blurple()
                        elif lower_part in ["grey", "gray", "secondary"]:
                            button_color = discord.Color.light_grey()
                        elif lower_part in ["green", "success"]:
                            button_color = discord.Color.green()
                        elif lower_part in ["red", "danger"]:
                            button_color = discord.Color.red()
                        break
                
                # Suche nach einer vorhandenen Rolle mit dem Namen oder erstelle eine neue
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                
                if role is None:
                    try:
                        # Erstelle die Rolle mit dem angegebenen Namen und der Farbe
                        role = await ctx.guild.create_role(
                            name=role_name,
                            color=button_color,
                            reason=f"Self-Roles Panel erstellt von {ctx.author.display_name}"
                        )
                        await ctx.send(f"✅ Neue Rolle **{role_name}** wurde erstellt!")
                    except discord.Forbidden:
                        await ctx.send("❌ Ich habe keine Berechtigung, Rollen zu erstellen. Bitte gib mir die entsprechende Berechtigung.")
                        continue
                    except discord.HTTPException as e:
                        await ctx.send(f"❌ Fehler beim Erstellen der Rolle: {str(e)}")
                        continue
                
                # Füge die Rolle zur Liste hinzu
                roles.append({
                    "role_id": role.id,
                    "style": style,
                    "emoji": emoji,
                    "label": role.name
                })
                
                await ctx.send(f"✅ Rolle **{role.name}** mit Emoji {emoji or 'keinem'} und Farbe {style} hinzugefügt!")
        
        # Überprüfe, ob Rollen hinzugefügt wurden
        if not roles:
            await ctx.send("❌ Du hast keine Rollen hinzugefügt. Der Vorgang wird abgebrochen.")
            return
        
        # Erstelle das Panel
        panel_id = f"{guild_id}_{len(self.config[guild_id]['panels'])}"
        
        panel = {
            "panel_id": panel_id,
            "title": title,
            "description": description,
            "roles": roles
        }
        
        # Füge Kategorien hinzu, wenn vorhanden
        if categories:
            panel["categories"] = categories
        
        # Erstelle das Embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Füge Informationen zu jeder Rolle hinzu, organisiert nach Kategorien
        if categories:
            for category in categories:
                # Sammle Rollen für diese Kategorie
                category_roles = []
                for role_info in roles:
                    if role_info.get("category_id") == category["id"]:
                        role = ctx.guild.get_role(role_info["role_id"])
                        if role:
                            category_roles.append(f"{role_info.get('emoji', '')} **{role.name}**")
                
                if category_roles:
                    embed.add_field(
                        name=f"📂 {category['name']}",
                        value="\n".join(category_roles),
                        inline=False
                    )
        else:
            # Keine Kategorien - einfach alle Rollen hinzufügen
            for role_info in roles:
                role = ctx.guild.get_role(role_info["role_id"])
                if role:
                    embed.add_field(
                        name=f"{role_info.get('emoji', '')} {role.name}",
                        value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                        inline=True
                    )
        
        # Erstelle das View
        view = await self._create_panel_view(panel)
        
        # Sende das Panel
        embed.set_footer(text=f"Panel erstellt von {ctx.author.display_name}")
        panel_message = await ctx.send("Hier ist dein Rollenpanel:", embed=embed, view=view)
        
        # Speichere die Nachrichteninformationen
        panel["channel_id"] = panel_message.channel.id
        panel["message_id"] = panel_message.id
        
        self.config[guild_id]["panels"].append(panel)
        self._save_config()
        
        # Erfolgsbenachrichtigung
        success_embed = discord.Embed(
            title="✅ Panel erfolgreich erstellt!",
            description=f"Dein Self-Roles Panel wurde erfolgreich erstellt und ist jetzt aktiv.",
            color=discord.Color.green()
        )
        success_embed.add_field(
            name="Panel-Informationen", 
            value=f"**Titel:** {title}\n**Rollen:** {len(roles)}\n**Kategorien:** {len(categories) if categories else 0}"
        )
        await ctx.send(embed=success_embed)
        
        logger.info(f"Self-roles panel created in guild {ctx.guild.name} by {ctx.author.display_name}")

    @commands.hybrid_command(name="editroles", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def edit_roles_panel(self, ctx: commands.Context, panel_number: int = None):
        """
        Bearbeitet ein bestehendes Self-Roles-Panel.
        
        Args:
            panel_number: Die Nummer des zu bearbeitenden Panels (beginnend bei 1).
        """
        guild_id = str(ctx.guild.id)
        
        # Überprüfe, ob Panels existieren
        if guild_id not in self.config or "panels" not in self.config[guild_id] or not self.config[guild_id]["panels"]:
            await ctx.send(embed=discord.Embed(
                title="❌ Keine Panels gefunden",
                description="Es wurden keine Self-Roles-Panels in diesem Server gefunden.",
                color=discord.Color.red()
            ))
            return
        
        panels = self.config[guild_id]["panels"]
        
        # Zeige verfügbare Panels an, wenn keine Nummer angegeben wurde
        if panel_number is None:
            embed = discord.Embed(
                title="🏷️ Verfügbare Self-Roles-Panels",
                description="Wähle ein Panel zur Bearbeitung aus. Verwende `/editroles <nummer>`.",
                color=discord.Color.blue()
            )
            
            for i, panel in enumerate(panels, 1):
                categories = len(panel.get("categories", [])) if "categories" in panel else 0
                embed.add_field(
                    name=f"Panel {i}: {panel['title']}",
                    value=f"Kanal: <#{panel['channel_id']}>\nRollen: {len(panel['roles'])}\nKategorien: {categories}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        
        # Überprüfe, ob die Panelnummer gültig ist
        if panel_number < 1 or panel_number > len(panels):
            await ctx.send(embed=discord.Embed(
                title="❌ Ungültige Panel-Nummer",
                description=f"Es gibt {len(panels)} Panel(s). Bitte wähle eine Nummer zwischen 1 und {len(panels)}.",
                color=discord.Color.red()
            ))
            return
        
        panel = panels[panel_number - 1]
        
        # Zeige Bearbeitungsoptionen an
        embed = discord.Embed(
            title=f"🔧 Panel bearbeiten: {panel['title']}",
            description="Wähle eine Option zur Bearbeitung:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="1️⃣ Titel", value="Bearbeite den Titel des Panels", inline=True)
        embed.add_field(name="2️⃣ Beschreibung", value="Bearbeite die Beschreibung", inline=True)
        embed.add_field(name="3️⃣ Rollen hinzufügen", value="Füge neue Rollen hinzu", inline=True)
        embed.add_field(name="4️⃣ Rolle entfernen", value="Entferne eine Rolle aus dem Panel", inline=True)
        embed.add_field(name="5️⃣ Kategorien bearbeiten", value="Bearbeite die Kategorien", inline=True) 
        embed.add_field(name="6️⃣ Panel löschen", value="⚠️ Lösche das gesamte Panel", inline=True)
        embed.add_field(name="❌ Abbrechen", value="Bearbeitung abbrechen", inline=True)
        
        await ctx.send(embed=embed)
        
        # Warte auf Antwort
        option_message = await self.bot.wait_for(
            "message", 
            timeout=60.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        
        option = option_message.content.strip()
        
        if option == "1":
            # Titel bearbeiten
            await ctx.send(embed=discord.Embed(
                title="🔄 Titel bearbeiten",
                description="Gib den neuen Titel für das Panel ein:",
                color=discord.Color.blue()
            ))
            
            title_message = await self.bot.wait_for(
                "message", 
                timeout=60.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            
            if title_message.content.lower() == "abbrechen":
                await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                return
                
            panel["title"] = title_message.content
            await ctx.send(embed=discord.Embed(
                title="✅ Titel aktualisiert",
                description=f"Der Titel wurde zu **{panel['title']}** geändert.",
                color=discord.Color.green()
            ))
        
        elif option == "2":
            # Beschreibung bearbeiten
            await ctx.send(embed=discord.Embed(
                title="🔄 Beschreibung bearbeiten",
                description="Gib die neue Beschreibung für das Panel ein (oder 'keine' für keine Beschreibung):",
                color=discord.Color.blue()
            ))
            
            desc_message = await self.bot.wait_for(
                "message", 
                timeout=120.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            
            if desc_message.content.lower() == "abbrechen":
                await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                return
                
            panel["description"] = None if desc_message.content.lower() == "keine" else desc_message.content
            await ctx.send(embed=discord.Embed(
                title="✅ Beschreibung aktualisiert",
                description=f"Die Beschreibung wurde aktualisiert.",
                color=discord.Color.green()
            ))
        
        elif option == "3":
            # Rollen hinzufügen
            # Zuerst prüfen, ob Kategorien existieren
            has_categories = "categories" in panel and panel["categories"]
            
            if has_categories:
                # Liste der Kategorien anzeigen
                embed = discord.Embed(
                    title="🔄 Kategorie wählen",
                    description="Wähle eine Kategorie, zu der du Rollen hinzufügen möchtest:",
                    color=discord.Color.blue()
                )
                
                for i, category in enumerate(panel["categories"], 1):
                    embed.add_field(
                        name=f"{i}. {category['name']}",
                        value=f"ID: {category['id']}",
                        inline=True
                    )
                
                embed.add_field(
                    name="0. Neue Kategorie erstellen",
                    value="Erstelle eine neue Kategorie",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
                # Warte auf Kategorieauswahl
                category_choice = await self.bot.wait_for(
                    "message", 
                    timeout=60.0, 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content.isdigit() or m.content.lower() == "abbrechen")
                )
                
                if category_choice.content.lower() == "abbrechen":
                    await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                    return
                
                choice = int(category_choice.content)
                
                if choice == 0:
                    # Neue Kategorie erstellen
                    await ctx.send(embed=discord.Embed(
                        title="🆕 Neue Kategorie",
                        description="Gib einen Namen für die neue Kategorie ein:",
                        color=discord.Color.blue()
                    ))
                    
                    category_name_message = await self.bot.wait_for(
                        "message", 
                        timeout=60.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if category_name_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    category_name = category_name_message.content
                    category_id = f"cat_{len(panel['categories'])}"
                    
                    # Neue Kategorie hinzufügen
                    panel["categories"].append({
                        "id": category_id,
                        "name": category_name
                    })
                    
                    await ctx.send(f"✅ Neue Kategorie **{category_name}** erstellt!")
                    
                    # Diese Kategorie für neue Rollen verwenden
                    selected_category = panel["categories"][-1]
                elif 1 <= choice <= len(panel["categories"]):
                    selected_category = panel["categories"][choice - 1]
                else:
                    await ctx.send("❌ Ungültige Auswahl. Der Vorgang wird abgebrochen.")
                    return
                
                # Aufforderung zum Hinzufügen von Rollen zur ausgewählten Kategorie
                await ctx.send(embed=discord.Embed(
                    title=f"🏷️ Rollen für Kategorie: {selected_category['name']}",
                    description=(
                        "Füge Rollen zu dieser Kategorie hinzu. Für jede Rolle, gib folgendes ein:\n"
                        "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
                        "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                        "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
                        "Wenn du fertig mit dieser Kategorie bist, schreibe `fertig`."
                    ),
                    color=discord.Color.blue()
                ))
                
                # Sammle Rollen für diese Kategorie
                adding_roles = True
                while adding_roles:
                    role_message = await self.bot.wait_for(
                        "message", 
                        timeout=180.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if role_message.content.lower() in ["fertig", "weiter"]:
                        adding_roles = False
                        continue
                    
                    if role_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    # Verarbeite die Eingabe
                    parts = role_message.content.split()
                    if len(parts) < 1:
                        await ctx.send("⚠️ Du musst mindestens einen Rollennamen angeben.")
                        continue
                    
                    # Der erste Teil ist der Rollenname
                    role_name = parts[0]
                    
                    # Extrahiere das Emoji, wenn vorhanden
                    emoji = None
                    for part in parts[1:]:
                        if len(part) == 1 or (len(part) > 1 and ord(part[0]) > 127):
                            emoji = part
                            break
                    
                    # Extrahiere die Farbe, wenn vorhanden
                    color_map = {
                        "blurple": "primary",
                        "grey": "secondary",
                        "gray": "secondary",
                        "green": "success",
                        "red": "danger",
                        "primary": "primary",
                        "secondary": "secondary",
                        "success": "success",
                        "danger": "danger"
                    }
                    
                    style = "primary"  # Standard
                    button_color = discord.Color.blurple()  # Standardfarbe für die Rolle
                    
                    for part in parts:
                        lower_part = part.lower()
                        if lower_part in color_map:
                            style = color_map[lower_part]
                            # Setze die entsprechende Rollenfarbe basierend auf dem Button-Stil
                            if lower_part in ["blurple", "primary"]:
                                button_color = discord.Color.blurple()
                            elif lower_part in ["grey", "gray", "secondary"]:
                                button_color = discord.Color.light_grey()
                            elif lower_part in ["green", "success"]:
                                button_color = discord.Color.green()
                            elif lower_part in ["red", "danger"]:
                                button_color = discord.Color.red()
                            break
                    
                    # Suche nach einer vorhandenen Rolle mit dem Namen oder erstelle eine neue
                    role = discord.utils.get(ctx.guild.roles, name=role_name)
                    
                    if role is None:
                        try:
                            # Erstelle die Rolle mit dem angegebenen Namen und der Farbe
                            role = await ctx.guild.create_role(
                                name=role_name,
                                color=button_color,
                                reason=f"Self-Roles Panel bearbeitet von {ctx.author.display_name}"
                            )
                            await ctx.send(f"✅ Neue Rolle **{role_name}** wurde erstellt!")
                        except discord.Forbidden:
                            await ctx.send("❌ Ich habe keine Berechtigung, Rollen zu erstellen. Bitte gib mir die entsprechende Berechtigung.")
                            continue
                        except discord.HTTPException as e:
                            await ctx.send(f"❌ Fehler beim Erstellen der Rolle: {str(e)}")
                            continue
                    
                    # Überprüfe, ob die Rolle bereits im Panel existiert
                    role_exists = False
                    for existing_role in panel["roles"]:
                        if existing_role["role_id"] == role.id:
                            role_exists = True
                            await ctx.send(f"⚠️ Die Rolle **{role.name}** ist bereits im Panel vorhanden.")
                            break
                    
                    if role_exists:
                        continue
                    
                    # Füge die Rolle zur Liste hinzu
                    panel["roles"].append({
                        "role_id": role.id,
                        "style": style,
                        "emoji": emoji,
                        "label": role.name,
                        "category_id": selected_category["id"]
                    })
                    
                    await ctx.send(f"✅ Rolle **{role.name}** mit Emoji {emoji or 'keinem'} und Farbe {style} hinzugefügt zu Kategorie **{selected_category['name']}**!")
            else:
                # Keine Kategorien - füge Rollen direkt hinzu
                await ctx.send(embed=discord.Embed(
                    title="🏷️ Rollen hinzufügen",
                    description=(
                        "Füge Rollen zu deinem Panel hinzu. Für jede Rolle, gib folgendes ein:\n"
                        "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
                        "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                        "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
                        "Wenn du fertig bist, schreibe `fertig`."
                    ),
                    color=discord.Color.blue()
                ))
                
                # Sammle Rollen
                adding_roles = True
                while adding_roles:
                    role_message = await self.bot.wait_for(
                        "message", 
                        timeout=180.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if role_message.content.lower() in ["fertig", "weiter"]:
                        adding_roles = False
                        continue
                    
                    if role_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    # Verarbeite die Eingabe
                    parts = role_message.content.split()
                    if len(parts) < 1:
                        await ctx.send("⚠️ Du musst mindestens einen Rollennamen angeben.")
                        continue
                    
                    # Der erste Teil ist der Rollenname
                    role_name = parts[0]
                    
                    # Extrahiere das Emoji, wenn vorhanden
                    emoji = None
                    for part in parts[1:]:
                        if len(part) == 1 or (len(part) > 1 and ord(part[0]) > 127):
                            emoji = part
                            break
                    
                    # Extrahiere die Farbe, wenn vorhanden
                    color_map = {
                        "blurple": "primary",
                        "grey": "secondary",
                        "gray": "secondary",
                        "green": "success",
                        "red": "danger",
                        "primary": "primary",
                        "secondary": "secondary",
                        "success": "success",
                        "danger": "danger"
                    }
                    
                    style = "primary"  # Standard
                    button_color = discord.Color.blurple()  # Standardfarbe für die Rolle
                    
                    for part in parts:
                        lower_part = part.lower()
                        if lower_part in color_map:
                            style = color_map[lower_part]
                            # Setze die entsprechende Rollenfarbe basierend auf dem Button-Stil
                            if lower_part in ["blurple", "primary"]:
                                button_color = discord.Color.blurple()
                            elif lower_part in ["grey", "gray", "secondary"]:
                                button_color = discord.Color.light_grey()
                            elif lower_part in ["green", "success"]:
                                button_color = discord.Color.green()
                            elif lower_part in ["red", "danger"]:
                                button_color = discord.Color.red()
                            break
                    
                    # Suche nach einer vorhandenen Rolle mit dem Namen oder erstelle eine neue
                    role = discord.utils.get(ctx.guild.roles, name=role_name)
                    
                    if role is None:
                        try:
                            # Erstelle die Rolle mit dem angegebenen Namen und der Farbe
                            role = await ctx.guild.create_role(
                                name=role_name,
                                color=button_color,
                                reason=f"Self-Roles Panel bearbeitet von {ctx.author.display_name}"
                            )
                            await ctx.send(f"✅ Neue Rolle **{role_name}** wurde erstellt!")
                        except discord.Forbidden:
                            await ctx.send("❌ Ich habe keine Berechtigung, Rollen zu erstellen. Bitte gib mir die entsprechende Berechtigung.")
                            continue
                        except discord.HTTPException as e:
                            await ctx.send(f"❌ Fehler beim Erstellen der Rolle: {str(e)}")
                            continue
                    
                    # Überprüfe, ob die Rolle bereits im Panel existiert
                    role_exists = False
                    for existing_role in panel["roles"]:
                        if existing_role["role_id"] == role.id:
                            role_exists = True
                            await ctx.send(f"⚠️ Die Rolle **{role.name}** ist bereits im Panel vorhanden.")
                            break
                    
                    if role_exists:
                        continue
                    
                    # Füge die Rolle zur Liste hinzu
                    panel["roles"].append({
                        "role_id": role.id,
                        "style": style,
                        "emoji": emoji,
                        "label": role.name
                    })
                    
                    await ctx.send(f"✅ Rolle **{role.name}** mit Emoji {emoji or 'keinem'} und Farbe {style} hinzugefügt!")
            
            await ctx.send(embed=discord.Embed(
                title="✅ Rollen aktualisiert",
                description="Die Rollen wurden erfolgreich aktualisiert.",
                color=discord.Color.green()
            ))
        
        elif option == "4":
            # Rolle entfernen
            if not panel["roles"]:
                await ctx.send(embed=discord.Embed(
                    title="❌ Keine Rollen",
                    description="Das Panel enthält keine Rollen zum Entfernen.",
                    color=discord.Color.red()
                ))
                return
            
            embed = discord.Embed(
                title="🗑️ Rolle entfernen",
                description="Wähle eine Rolle zum Entfernen aus:",
                color=discord.Color.blue()
            )
            
            has_categories = "categories" in panel and panel["categories"]
            
            if has_categories:
                # Gruppiere nach Kategorien
                for category in panel["categories"]:
                    category_roles = []
                    role_indices = []
                    
                    for i, role_info in enumerate(panel["roles"]):
                        if role_info.get("category_id") == category["id"]:
                            role = ctx.guild.get_role(role_info["role_id"])
                            role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                            category_roles.append(f"{i+1}. {role_info.get('emoji', '')} **{role_name}**")
                            role_indices.append(i+1)
                    
                    if category_roles:
                        embed.add_field(
                            name=f"📂 {category['name']}",
                            value="\n".join(category_roles),
                            inline=False
                        )
            else:
                # Einfache Liste aller Rollen
                for i, role_info in enumerate(panel["roles"], 1):
                    role = ctx.guild.get_role(role_info["role_id"])
                    role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                    embed.add_field(
                        name=f"{i}. {role_info.get('emoji', '')} {role_name}",
                        value=f"Farbe: {role_info['style']}",
                        inline=True
                    )
            
            await ctx.send(embed=embed)
            
            # Warte auf Antwort
            role_num_message = await self.bot.wait_for(
                "message", 
                timeout=60.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content.isdigit() or m.content.lower() == "abbrechen")
            )
            
            if role_num_message.content.lower() == "abbrechen":
                await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                return
                
            role_num = int(role_num_message.content)
            
            if role_num < 1 or role_num > len(panel["roles"]):
                await ctx.send(embed=discord.Embed(
                    title="❌ Ungültige Nummer",
                    description=f"Es gibt {len(panel['roles'])} Rolle(n). Bitte wähle eine Nummer zwischen 1 und {len(panel['roles'])}.",
                    color=discord.Color.red()
                ))
                return
            
            removed_role = panel["roles"].pop(role_num - 1)
            role = ctx.guild.get_role(removed_role["role_id"])
            role_name = role.name if role else f"Unbekannte Rolle (ID: {removed_role['role_id']})"
            
            await ctx.send(embed=discord.Embed(
                title="✅ Rolle entfernt",
                description=f"Die Rolle **{role_name}** wurde aus dem Panel entfernt.",
                color=discord.Color.green()
            ))
        
        elif option == "5":
            # Kategorien bearbeiten
            has_categories = "categories" in panel and panel["categories"]
            
            if has_categories:
                # Zeige vorhandene Kategorien an
                embed = discord.Embed(
                    title="📂 Kategorien bearbeiten",
                    description="Was möchtest du mit den Kategorien tun?",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="1️⃣ Kategorie hinzufügen", value="Füge eine neue Kategorie hinzu", inline=True)
                embed.add_field(name="2️⃣ Kategorie umbenennen", value="Benenne eine vorhandene Kategorie um", inline=True)
                embed.add_field(name="3️⃣ Kategorie löschen", value="Entferne eine Kategorie (Rollen bleiben erhalten)", inline=True)
                embed.add_field(name="4️⃣ Rollen verschieben", value="Verschiebe Rollen zwischen Kategorien", inline=True)
                embed.add_field(name="❌ Abbrechen", value="Zurück zum Hauptmenü", inline=True)
                
                # Liste vorhandene Kategorien auf
                category_list = "\n".join([f"{i+1}. **{category['name']}** (ID: {category['id']})" for i, category in enumerate(panel["categories"])])
                embed.add_field(name="Vorhandene Kategorien", value=category_list, inline=False)
                
                await ctx.send(embed=embed)
                
                # Warte auf Antwort
                category_option = await self.bot.wait_for(
                    "message", 
                    timeout=60.0, 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                
                if category_option.content.lower() == "abbrechen" or category_option.content == "❌":
                    await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                    return
                
                option = category_option.content.strip()
                
                if option == "1":  # Kategorie hinzufügen
                    await ctx.send(embed=discord.Embed(
                        title="🆕 Neue Kategorie",
                        description="Gib einen Namen für die neue Kategorie ein:",
                        color=discord.Color.blue()
                    ))
                    
                    category_name_message = await self.bot.wait_for(
                        "message", 
                        timeout=60.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if category_name_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    category_name = category_name_message.content
                    category_id = f"cat_{len(panel['categories'])}"
                    
                    # Neue Kategorie hinzufügen
                    panel["categories"].append({
                        "id": category_id,
                        "name": category_name
                    })
                    
                    await ctx.send(embed=discord.Embed(
                        title="✅ Kategorie erstellt",
                        description=f"Die Kategorie **{category_name}** wurde erfolgreich erstellt.",
                        color=discord.Color.green()
                    ))
                
                elif option == "2":  # Kategorie umbenennen
                    await ctx.send(embed=discord.Embed(
                        title="🔄 Kategorie umbenennen",
                        description="Wähle die Nummer der Kategorie, die du umbenennen möchtest:",
                        color=discord.Color.blue()
                    ))
                    
                    category_num_message = await self.bot.wait_for(
                        "message", 
                        timeout=60.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content.isdigit() or m.content.lower() == "abbrechen")
                    )
                    
                    if category_num_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    category_num = int(category_num_message.content)
                    
                    if category_num < 1 or category_num > len(panel["categories"]):
                        await ctx.send(f"❌ Ungültige Kategorie-Nummer. Es gibt {len(panel['categories'])} Kategorie(n).")
                        return
                    
                    selected_category = panel["categories"][category_num - 1]
                    
                    await ctx.send(embed=discord.Embed(
                        title=f"🔄 Kategorie umbenennen: {selected_category['name']}",
                        description="Gib den neuen Namen für die Kategorie ein:",
                        color=discord.Color.blue()
                    ))
                    
                    new_name_message = await self.bot.wait_for(
                        "message", 
                        timeout=60.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if new_name_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    old_name = selected_category["name"]
                    selected_category["name"] = new_name_message.content
                    
                    await ctx.send(embed=discord.Embed(
                        title="✅ Kategorie umbenannt",
                        description=f"Die Kategorie wurde von **{old_name}** zu **{selected_category['name']}** umbenannt.",
                        color=discord.Color.green()
                    ))
                
                elif option == "3":  # Kategorie löschen
                    await ctx.send(embed=discord.Embed(
                        title="🗑️ Kategorie löschen",
                        description=(
                            "Wähle die Nummer der Kategorie, die du löschen möchtest:\n\n"
                            "⚠️ **ACHTUNG:** Die Rollen in dieser Kategorie werden dem Panel ohne Kategorie hinzugefügt."
                        ),
                        color=discord.Color.blue()
                    ))
                    
                    category_num_message = await self.bot.wait_for(
                        "message", 
                        timeout=60.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content.isdigit() or m.content.lower() == "abbrechen")
                    )
                    
                    if category_num_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    category_num = int(category_num_message.content)
                    
                    if category_num < 1 or category_num > len(panel["categories"]):
                        await ctx.send(f"❌ Ungültige Kategorie-Nummer. Es gibt {len(panel['categories'])} Kategorie(n).")
                        return
                    
                    selected_category = panel["categories"][category_num - 1]
                    category_id = selected_category["id"]
                    
                    # Entferne die Kategorie-ID von allen Rollen in dieser Kategorie
                    for role in panel["roles"]:
                        if role.get("category_id") == category_id:
                            if "category_id" in role:
                                del role["category_id"]
                    
                    # Entferne die Kategorie
                    panel["categories"].pop(category_num - 1)
                    
                    await ctx.send(embed=discord.Embed(
                        title="✅ Kategorie gelöscht",
                        description=f"Die Kategorie **{selected_category['name']}** wurde gelöscht. Alle Rollen wurden ohne Kategorie dem Panel hinzugefügt.",
                        color=discord.Color.green()
                    ))
                
                elif option == "4":  # Rollen verschieben
                    # Zeige alle Rollen ohne Kategorie an
                    uncategorized_roles = []
                    for i, role_info in enumerate(panel["roles"]):
                        if "category_id" not in role_info:
                            role = ctx.guild.get_role(role_info["role_id"])
                            role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                            uncategorized_roles.append(f"{i+1}. {role_info.get('emoji', '')} **{role_name}**")
                    
                    # Kategorien auflisten
                    categories_list = "\n".join([f"{i+1}. **{category['name']}**" for i, category in enumerate(panel["categories"])])
                    
                    embed = discord.Embed(
                        title="🔄 Rollen verschieben",
                        description=(
                            "Um eine Rolle zu verschieben, gib Folgendes ein:\n"
                            "`<Rollennummer> <Kategorienummer>`\n\n"
                            "Beispiel: `3 2` verschiebt Rolle 3 in Kategorie 2."
                        ),
                        color=discord.Color.blue()
                    )
                    
                    # Füge Kategorien hinzu
                    embed.add_field(
                        name="📂 Verfügbare Kategorien",
                        value=categories_list,
                        inline=False
                    )
                    
                    # Zeige Rollen nach Kategorien
                    for i, category in enumerate(panel["categories"]):
                        category_roles = []
                        for j, role_info in enumerate(panel["roles"]):
                            if role_info.get("category_id") == category["id"]:
                                role = ctx.guild.get_role(role_info["role_id"])
                                role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                                category_roles.append(f"{j+1}. {role_info.get('emoji', '')} **{role_name}**")
                        
                        if category_roles:
                            embed.add_field(
                                name=f"📂 {category['name']}",
                                value="\n".join(category_roles),
                                inline=False
                            )
                    
                    # Zeige Rollen ohne Kategorie
                    if uncategorized_roles:
                        embed.add_field(
                            name="📄 Rollen ohne Kategorie",
                            value="\n".join(uncategorized_roles),
                            inline=False
                        )
                    
                    embed.add_field(
                        name="⚠️ Hinweis",
                        value="Gib `0` als Kategorienummer ein, um eine Rolle aus einer Kategorie zu entfernen.",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    
                    # Warte auf Verschiebeanweisung
                    move_message = await self.bot.wait_for(
                        "message", 
                        timeout=120.0, 
                        check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                    )
                    
                    if move_message.content.lower() == "abbrechen":
                        await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                        return
                    
                    # Parse die Verschiebeanweisung
                    parts = move_message.content.split()
                    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                        await ctx.send("❌ Ungültiges Format. Bitte gib `<Rollennummer> <Kategorienummer>` ein.")
                        return
                    
                    role_num = int(parts[0])
                    cat_num = int(parts[1])
                    
                    # Überprüfe, ob die Rollennummer gültig ist
                    if role_num < 1 or role_num > len(panel["roles"]):
                        await ctx.send(f"❌ Ungültige Rollennummer. Es gibt {len(panel['roles'])} Rolle(n).")
                        return
                    
                    # Überprüfe, ob die Kategorienummer gültig ist
                    if cat_num != 0 and (cat_num < 1 or cat_num > len(panel["categories"])):
                        await ctx.send(f"❌ Ungültige Kategorienummer. Es gibt {len(panel['categories'])} Kategorie(n).")
                        return
                    
                    role_info = panel["roles"][role_num - 1]
                    role = ctx.guild.get_role(role_info["role_id"])
                    role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                    
                    if cat_num == 0:
                        # Entferne die Kategorie
                        if "category_id" in role_info:
                            # Finde den Namen der alten Kategorie
                            old_category_name = "Unbekannte Kategorie"
                            for category in panel["categories"]:
                                if category["id"] == role_info["category_id"]:
                                    old_category_name = category["name"]
                                    break
                            
                            del role_info["category_id"]
                            await ctx.send(embed=discord.Embed(
                                title="✅ Rolle verschoben",
                                description=f"Die Rolle **{role_name}** wurde aus der Kategorie **{old_category_name}** entfernt.",
                                color=discord.Color.green()
                            ))
                        else:
                            await ctx.send("⚠️ Diese Rolle ist bereits ohne Kategorie.")
                    else:
                        # Füge die Kategorie hinzu
                        category = panel["categories"][cat_num - 1]
                        role_info["category_id"] = category["id"]
                        
                        await ctx.send(embed=discord.Embed(
                            title="✅ Rolle verschoben",
                            description=f"Die Rolle **{role_name}** wurde in die Kategorie **{category['name']}** verschoben.",
                            color=discord.Color.green()
                        ))
            else:
                # Keine Kategorien vorhanden - erstelle neue
                embed = discord.Embed(
                    title="📂 Kategorien erstellen",
                    description=(
                        "Dieses Panel hat bisher keine Kategorien. Möchtest du Kategorien hinzufügen?\n\n"
                        "Mit Kategorien kannst du deine Rollen in logische Gruppen organisieren, "
                        "z.B. 'Spiele', 'Farben', 'Benachrichtigungen' usw."
                    ),
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="1️⃣ Ja, Kategorien erstellen",
                    value="Beginne mit der Erstellung von Kategorien für dieses Panel",
                    inline=False
                )
                
                embed.add_field(
                    name="2️⃣ Nein, abbrechen",
                    value="Behalte das Panel ohne Kategorien",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
                # Warte auf Antwort
                option_message = await self.bot.wait_for(
                    "message", 
                    timeout=60.0, 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                
                if option_message.content == "1":
                    # Kategorien erstellen
                    panel["categories"] = []
                    
                    await ctx.send(embed=discord.Embed(
                        title="🆕 Kategorien erstellen",
                        description=(
                            "Gib die Namen für deine Kategorien ein, eine nach der anderen.\n"
                            "Wenn du fertig bist, schreibe `fertig`."
                        ),
                        color=discord.Color.blue()
                    ))
                    
                    # Sammle Kategorien
                    adding_categories = True
                    while adding_categories:
                        category_message = await self.bot.wait_for(
                            "message", 
                            timeout=120.0, 
                            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                        )
                        
                        if category_message.content.lower() in ["fertig", "weiter"]:
                            adding_categories = False
                            continue
                        
                        if category_message.content.lower() == "abbrechen":
                            await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                            return
                        
                        # Erstelle eine neue Kategorie mit eindeutiger ID
                        category_id = f"cat_{len(panel['categories'])}"
                        category_name = category_message.content
                        
                        panel["categories"].append({
                            "id": category_id,
                            "name": category_name
                        })
                        
                        await ctx.send(f"✅ Kategorie **{category_name}** hinzugefügt!")
                    
                    if not panel["categories"]:
                        await ctx.send("❌ Du hast keine Kategorien hinzugefügt. Der Vorgang wird abgebrochen.")
                        return
                    
                    # Jetzt die vorhandenen Rollen in Kategorien einordnen
                    for category in panel["categories"]:
                        embed = discord.Embed(
                            title=f"🔄 Rollen für Kategorie: {category['name']}",
                            description=(
                                "Wähle die Rollen, die in diese Kategorie gehören sollen.\n"
                                "Gib die Nummern der Rollen ein, getrennt durch Leerzeichen (z.B. `1 3 5`).\n"
                                "Oder gib `keine` ein, wenn keine Rollen in diese Kategorie gehören sollen."
                            ),
                            color=discord.Color.blue()
                        )
                        
                        # Liste alle vorhandenen Rollen auf
                        all_roles = []
                        for i, role_info in enumerate(panel["roles"], 1):
                            role = ctx.guild.get_role(role_info["role_id"])
                            role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                            already_categorized = "category_id" in role_info
                            status = " (bereits kategorisiert)" if already_categorized else ""
                            all_roles.append(f"{i}. {role_info.get('emoji', '')} **{role_name}**{status}")
                        
                        if all_roles:
                            embed.add_field(
                                name="📄 Verfügbare Rollen",
                                value="\n".join(all_roles),
                                inline=False
                            )
                        
                        await ctx.send(embed=embed)
                        
                        # Warte auf Antwort
                        category_roles_message = await self.bot.wait_for(
                            "message", 
                            timeout=180.0, 
                            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                        )
                        
                        if category_roles_message.content.lower() == "abbrechen":
                            await ctx.send("✅ Der Vorgang wurde abgebrochen.")
                            return
                        
                        if category_roles_message.content.lower() != "keine":
                            # Verarbeite die Rollennummern
                            role_nums = []
                            for part in category_roles_message.content.split():
                                if part.isdigit():
                                    role_nums.append(int(part))
                            
                            # Füge die Kategorie-ID zu den ausgewählten Rollen hinzu
                            added_roles = []
                            for role_num in role_nums:
                                if 1 <= role_num <= len(panel["roles"]):
                                    role_info = panel["roles"][role_num - 1]
                                    role_info["category_id"] = category["id"]
                                    
                                    role = ctx.guild.get_role(role_info["role_id"])
                                    role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                                    added_roles.append(f"**{role_name}**")
                            
                            if added_roles:
                                await ctx.send(f"✅ Folgende Rollen wurden der Kategorie **{category['name']}** hinzugefügt: {', '.join(added_roles)}")
                            else:
                                await ctx.send(f"⚠️ Es wurden keine gültigen Rollen für die Kategorie **{category['name']}** ausgewählt.")
                        else:
                            await ctx.send(f"ℹ️ Keine Rollen für die Kategorie **{category['name']}** ausgewählt.")
                    
                    await ctx.send(embed=discord.Embed(
                        title="✅ Kategorien erstellt",
                        description=f"Die Kategorien wurden erfolgreich erstellt und die Rollen eingeordnet.",
                        color=discord.Color.green()
                    ))
                else:
                    await ctx.send("✅ Der Vorgang wurde abgebrochen. Das Panel bleibt ohne Kategorien.")
        
        elif option == "6":
            # Panel löschen
            embed = discord.Embed(
                title="⚠️ Panel löschen",
                description=(
                    f"Bist du sicher, dass du das Panel **{panel['title']}** löschen möchtest?\n\n"
                    "Diese Aktion kann nicht rückgängig gemacht werden!"
                ),
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Bestätigung", 
                value="Schreibe `ja` zum Bestätigen oder `nein` zum Abbrechen."
            )
            
            await ctx.send(embed=embed)
            
            # Warte auf Bestätigung
            confirm_message = await self.bot.wait_for(
                "message", 
                timeout=60.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["ja", "nein"]
            )
            
            if confirm_message.content.lower() == "ja":
                # Lösche die alte Nachricht, wenn möglich
                try:
                    channel = ctx.guild.get_channel(panel["channel_id"])
                    if channel:
                        old_message = await channel.fetch_message(panel["message_id"])
                        await old_message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass  # Ignoriere Fehler beim Löschen
                
                panels.pop(panel_number - 1)
                
                await ctx.send(embed=discord.Embed(
                    title="✅ Panel gelöscht",
                    description="Das Self-Roles Panel wurde erfolgreich gelöscht.",
                    color=discord.Color.green()
                ))
                
                self._save_config()
                return
            else:
                await ctx.send("Löschvorgang abgebrochen.")
                return
        
        elif option.lower() in ["❌", "abbrechen", "cancel"]:
            await ctx.send("Bearbeitung abgebrochen.")
            return
        
        else:
            await ctx.send(embed=discord.Embed(
                title="❌ Ungültige Option",
                description="Die gewählte Option ist ungültig. Der Vorgang wird abgebrochen.",
                color=discord.Color.red()
            ))
            return
        
        # Aktualisiere das Panel
        self._save_config()
        
        # Hole die alte Nachricht
        try:
            channel = ctx.guild.get_channel(panel["channel_id"])
            if not channel:
                await ctx.send(embed=discord.Embed(
                    title="⚠️ Kanal nicht gefunden",
                    description="Der Kanal des Panels existiert nicht mehr. Ein neues Panel wird erstellt.",
                    color=discord.Color.yellow()
                ))
                return
            
            old_message = await channel.fetch_message(panel["message_id"])
            
            # Erstelle das aktualisierte Embed
            embed = discord.Embed(
                title=panel["title"],
                description=panel["description"],
                color=discord.Color.blue()
            )
            
            # Füge Informationen zu jeder Rolle hinzu, organisiert nach Kategorien
            has_categories = "categories" in panel and panel["categories"]
            
            if has_categories:
                for category in panel["categories"]:
                    # Sammle Rollen für diese Kategorie
                    category_roles = []
                    for role_info in panel["roles"]:
                        if role_info.get("category_id") == category["id"]:
                            role = ctx.guild.get_role(role_info["role_id"])
                            if role:
                                category_roles.append(f"{role_info.get('emoji', '')} **{role.name}**")
                    
                    if category_roles:
                        embed.add_field(
                            name=f"📂 {category['name']}",
                            value="\n".join(category_roles),
                            inline=False
                        )
                
                # Füge auch Rollen ohne Kategorie hinzu, falls vorhanden
                uncategorized_roles = []
                for role_info in panel["roles"]:
                    if "category_id" not in role_info:
                        role = ctx.guild.get_role(role_info["role_id"])
                        if role:
                            uncategorized_roles.append(f"{role_info.get('emoji', '')} **{role.name}**")
                
                if uncategorized_roles:
                    embed.add_field(
                        name="📄 Weitere Rollen",
                        value="\n".join(uncategorized_roles),
                        inline=False
                    )
            else:
                # Keine Kategorien - einfach alle Rollen hinzufügen
                for role_info in panel["roles"]:
                    role = ctx.guild.get_role(role_info["role_id"])
                    if role:
                        embed.add_field(
                            name=f"{role_info.get('emoji', '')} {role.name}",
                            value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                            inline=True
                        )
            
            # Erstelle das View
            view = await self._create_panel_view(panel)
            
            # Aktualisiere die Nachricht
            embed.set_footer(text=f"Zuletzt aktualisiert: {discord.utils.utcnow().strftime('%d.%m.%Y, %H:%M')} UTC")
            await old_message.edit(content="Hier ist dein Rollenpanel:", embed=embed, view=view)
            
            await ctx.send(embed=discord.Embed(
                title="✅ Panel aktualisiert",
                description="Das Self-Roles Panel wurde erfolgreich aktualisiert!",
                color=discord.Color.green()
            ))
            
            logger.info(f"Self-roles panel updated in guild {ctx.guild.name} by {ctx.author.display_name}")
            
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            await ctx.send(embed=discord.Embed(
                title="⚠️ Fehler beim Aktualisieren",
                description=f"Die Nachricht des Panels konnte nicht gefunden werden. Ein neues Panel wird erstellt.\nFehler: {str(e)}",
                color=discord.Color.yellow()
            ))
            
            # Sende eine neue Nachricht
            embed = discord.Embed(
                title=panel["title"],
                description=panel["description"],
                color=discord.Color.blue()
            )
            
            # Füge Informationen zu jeder Rolle hinzu, organisiert nach Kategorien
            has_categories = "categories" in panel and panel["categories"]
            
            if has_categories:
                for category in panel["categories"]:
                    # Sammle Rollen für diese Kategorie
                    category_roles = []
                    for role_info in panel["roles"]:
                        if role_info.get("category_id") == category["id"]:
                            role = ctx.guild.get_role(role_info["role_id"])
                            if role:
                                category_roles.append(f"{role_info.get('emoji', '')} **{role.name}**")
                    
                    if category_roles:
                        embed.add_field(
                            name=f"📂 {category['name']}",
                            value="\n".join(category_roles),
                            inline=False
                        )
                
                # Füge auch Rollen ohne Kategorie hinzu, falls vorhanden
                uncategorized_roles = []
                for role_info in panel["roles"]:
                    if "category_id" not in role_info:
                        role = ctx.guild.get_role(role_info["role_id"])
                        if role:
                            uncategorized_roles.append(f"{role_info.get('emoji', '')} **{role.name}**")
                
                if uncategorized_roles:
                    embed.add_field(
                        name="📄 Weitere Rollen",
                        value="\n".join(uncategorized_roles),
                        inline=False
                    )
            else:
                # Keine Kategorien - einfach alle Rollen hinzufügen
                for role_info in panel["roles"]:
                    role = ctx.guild.get_role(role_info["role_id"])
                    role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                    embed.add_field(
                        name=f"{role_info.get('emoji', '')} {role_name}",
                        value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                        inline=True
                    )
            
            # Erstelle das View
            view = await self._create_panel_view(panel)
            
            # Sende das Panel
            embed.set_footer(text=f"Zuletzt aktualisiert: {discord.utils.utcnow().strftime('%d.%m.%Y, %H:%M')} UTC")
            panel_message = await ctx.send("Hier ist dein Rollenpanel:", embed=embed, view=view)
            
            # Aktualisiere die Nachrichteninformationen
            panel["channel_id"] = panel_message.channel.id
            panel["message_id"] = panel_message.id
            
            self._save_config()
            
            await ctx.send(embed=discord.Embed(
                title="✅ Panel neu erstellt",
                description="Das Self-Roles Panel wurde erfolgreich neu erstellt!",
                color=discord.Color.green()
            ))
            
            logger.info(f"Self-roles panel recreated in guild {ctx.guild.name} by {ctx.author.display_name}")

async def setup(bot: commands.Bot):
    """Füge den SelfRoles-Cog zum Bot hinzu."""
    await bot.add_cog(SelfRoles(bot))
    logger.info("SelfRoles cog loaded")
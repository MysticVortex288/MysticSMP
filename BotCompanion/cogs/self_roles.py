import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import logging
import os

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
        
        if role in user.roles:
            # Rolle entfernen
            await user.remove_roles(role)
            await interaction.response.send_message(
                f"✅ Die Rolle **{role.name}** wurde entfernt!",
                ephemeral=True
            )
            logger.info(f"User {user.display_name} removed role {role.name}")
        else:
            # Rolle hinzufügen
            await user.add_roles(role)
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
        
        logger.info("SelfRoles cog initialized")
    
    def _load_config(self):
        """Lade die Konfiguration aus der Datei."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Erstellen von Default-Daten
            default_data = {
                # Format: {"guild_id": {
                #   "panels": [
                #     {
                #       "panel_id": "unique_id",
                #       "channel_id": channel_id,
                #       "message_id": message_id,
                #       "title": "Panel Title",
                #       "description": "Panel Description",
                #       "roles": [
                #         {
                #           "role_id": role_id,
                #           "style": "blurple",
                #           "emoji": "🔵",
                #           "label": "Role Name"
                #         }
                #       ]
                #     }
                #   ]
                # }}
            }
            self._save_config(default_data)
            return default_data
    
    def _save_config(self, config=None):
        """Speichere die Konfiguration in der Datei."""
        if config is None:
            config = self.config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    async def _create_panel_view(self, panel):
        """Erstelle ein View für ein Rollenpanel."""
        view = RoleView(panel["panel_id"])
        
        # Füge Buttons für jede Rolle hinzu
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
    
    @commands.hybrid_command(name="createroles")
    @commands.has_permissions(administrator=True)
    async def create_roles_panel(self, ctx: commands.Context):
        """
        Startet den Assistenten zum Erstellen eines Self-Roles-Panels.
        """
        await ctx.send("Der Assistent zum Erstellen eines Self-Roles-Panels wurde gestartet! Bitte beantworte die folgenden Fragen.")
        
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "panels" not in self.config[guild_id]:
            self.config[guild_id]["panels"] = []
        
        # Frage nach dem Titel
        await ctx.send("Wie soll der Titel des Panels lauten?")
        title_message = await self.bot.wait_for(
            "message", 
            timeout=60.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        title = title_message.content
        
        # Frage nach der Beschreibung
        await ctx.send("Gib eine Beschreibung für das Panel ein (oder schreibe 'keine' für keine Beschreibung):")
        description_message = await self.bot.wait_for(
            "message", 
            timeout=120.0, 
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        description = None if description_message.content.lower() == "keine" else description_message.content
        
        # Sammle Rollen
        roles = []
        adding_roles = True
        
        await ctx.send(
            "Jetzt kannst du Rollen hinzufügen. Für jede Rolle, gib folgendes ein:\n"
            "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
            "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
            "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
            "Wenn du fertig bist, schreibe `fertig`."
        )
        
        while adding_roles:
            role_message = await self.bot.wait_for(
                "message", 
                timeout=180.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            
            if role_message.content.lower() == "fertig":
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
                "label": role.name
            })
            
            await ctx.send(f"✅ Rolle **{role.name}** mit Emoji {emoji or 'keinem'} und Farbe {style} hinzugefügt!")
        
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
        
        # Erstelle das Embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        
        # Füge Informationen zu jeder Rolle hinzu
        for role_info in roles:
            role = ctx.guild.get_role(role_info["role_id"])
            if role:
                embed.add_field(
                    name=f"{role_info.get('emoji', '')} {role.name}",
                    value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                    inline=False
                )
        
        # Erstelle das View
        view = await self._create_panel_view(panel)
        
        # Sende das Panel
        panel_message = await ctx.send("Hier ist dein Rollenpanel:", embed=embed, view=view)
        
        # Speichere die Nachrichteninformationen
        panel["channel_id"] = panel_message.channel.id
        panel["message_id"] = panel_message.id
        
        self.config[guild_id]["panels"].append(panel)
        self._save_config()
        
        await ctx.send("✅ Das Self-Roles-Panel wurde erfolgreich erstellt!")
        logger.info(f"Self-roles panel created in guild {ctx.guild.name} by {ctx.author.display_name}")
    
    @commands.hybrid_command(name="editroles")
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
            await ctx.send("❌ Es wurden keine Self-Roles-Panels gefunden.")
            return
        
        panels = self.config[guild_id]["panels"]
        
        # Zeige verfügbare Panels an, wenn keine Nummer angegeben wurde
        if panel_number is None:
            embed = discord.Embed(
                title="Verfügbare Self-Roles-Panels",
                description="Verwende `/editroles <nummer>`, um ein Panel zu bearbeiten.",
                color=discord.Color.blue()
            )
            
            for i, panel in enumerate(panels, 1):
                embed.add_field(
                    name=f"Panel {i}: {panel['title']}",
                    value=f"Kanal: <#{panel['channel_id']}>\nRollen: {len(panel['roles'])}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        
        # Überprüfe, ob die Panelnummer gültig ist
        if panel_number < 1 or panel_number > len(panels):
            await ctx.send(f"❌ Ungültige Panel-Nummer. Es gibt {len(panels)} Panel(s).")
            return
        
        panel = panels[panel_number - 1]
        
        # Zeige Bearbeitungsoptionen an
        embed = discord.Embed(
            title=f"Panel bearbeiten: {panel['title']}",
            description="Was möchtest du bearbeiten?",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="1️⃣ Titel", value="Bearbeite den Titel des Panels", inline=True)
        embed.add_field(name="2️⃣ Beschreibung", value="Bearbeite die Beschreibung", inline=True)
        embed.add_field(name="3️⃣ Rollen hinzufügen", value="Füge neue Rollen hinzu", inline=True)
        embed.add_field(name="4️⃣ Rolle entfernen", value="Entferne eine Rolle aus dem Panel", inline=True)
        embed.add_field(name="5️⃣ Panel löschen", value="⚠️ Lösche das gesamte Panel", inline=True)
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
            await ctx.send("Gib den neuen Titel ein:")
            title_message = await self.bot.wait_for(
                "message", 
                timeout=60.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            panel["title"] = title_message.content
            await ctx.send("✅ Titel aktualisiert!")
        
        elif option == "2":
            # Beschreibung bearbeiten
            await ctx.send("Gib die neue Beschreibung ein (oder 'keine' für keine Beschreibung):")
            desc_message = await self.bot.wait_for(
                "message", 
                timeout=120.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            panel["description"] = None if desc_message.content.lower() == "keine" else desc_message.content
            await ctx.send("✅ Beschreibung aktualisiert!")
        
        elif option == "3":
            # Rollen hinzufügen
            await ctx.send(
                "Für jede neue Rolle, gib folgendes ein:\n"
                "`Rollenname Emoji Farbe` (z.B. `Gamer 🎮 blurple`)\n\n"
                "Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                "Die Rolle wird automatisch erstellt, wenn sie noch nicht existiert!\n"
                "Wenn du fertig bist, schreibe `fertig`."
            )
            
            adding_roles = True
            while adding_roles:
                role_message = await self.bot.wait_for(
                    "message", 
                    timeout=180.0, 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                
                if role_message.content.lower() == "fertig":
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
            
            await ctx.send("✅ Rollen aktualisiert!")
        
        elif option == "4":
            # Rolle entfernen
            if not panel["roles"]:
                await ctx.send("❌ Das Panel enthält keine Rollen.")
                return
            
            embed = discord.Embed(
                title="Rolle entfernen",
                description="Wähle eine Rolle zum Entfernen aus:",
                color=discord.Color.blue()
            )
            
            for i, role_info in enumerate(panel["roles"], 1):
                role = ctx.guild.get_role(role_info["role_id"])
                role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                embed.add_field(
                    name=f"{i}. {role_info.get('emoji', '')} {role_name}",
                    value=f"Farbe: {role_info['style']}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
            # Warte auf Antwort
            role_num_message = await self.bot.wait_for(
                "message", 
                timeout=60.0, 
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            )
            
            role_num = int(role_num_message.content)
            
            if role_num < 1 or role_num > len(panel["roles"]):
                await ctx.send(f"❌ Ungültige Rollennummer. Es gibt {len(panel['roles'])} Rolle(n).")
                return
            
            removed_role = panel["roles"].pop(role_num - 1)
            role = ctx.guild.get_role(removed_role["role_id"])
            role_name = role.name if role else f"Unbekannte Rolle (ID: {removed_role['role_id']})"
            
            await ctx.send(f"✅ Rolle **{role_name}** wurde aus dem Panel entfernt!")
        
        elif option == "5":
            # Panel löschen
            await ctx.send("⚠️ Bist du sicher, dass du dieses Panel löschen möchtest? (ja/nein)")
            
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
                await ctx.send("✅ Das Panel wurde erfolgreich gelöscht!")
                self._save_config()
                return
            else:
                await ctx.send("Löschvorgang abgebrochen.")
                return
        
        elif option.lower() in ["❌", "abbrechen", "cancel"]:
            await ctx.send("Bearbeitung abgebrochen.")
            return
        
        else:
            await ctx.send("❌ Ungültige Option. Bearbeitung abgebrochen.")
            return
        
        # Aktualisiere das Panel
        self._save_config()
        
        # Hole die alte Nachricht
        try:
            channel = ctx.guild.get_channel(panel["channel_id"])
            if not channel:
                await ctx.send("⚠️ Der Kanal des Panels existiert nicht mehr. Ein neues Panel wird erstellt.")
                return
            
            old_message = await channel.fetch_message(panel["message_id"])
            
            # Erstelle das aktualisierte Embed
            embed = discord.Embed(
                title=panel["title"],
                description=panel["description"],
                color=discord.Color.blue()
            )
            
            # Füge Informationen zu jeder Rolle hinzu
            for role_info in panel["roles"]:
                role = ctx.guild.get_role(role_info["role_id"])
                role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                embed.add_field(
                    name=f"{role_info.get('emoji', '')} {role_name}",
                    value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                    inline=False
                )
            
            # Erstelle das View
            view = await self._create_panel_view(panel)
            
            # Aktualisiere die Nachricht
            await old_message.edit(content="Hier ist dein Rollenpanel:", embed=embed, view=view)
            
            await ctx.send("✅ Das Self-Roles-Panel wurde erfolgreich aktualisiert!")
            logger.info(f"Self-roles panel updated in guild {ctx.guild.name} by {ctx.author.display_name}")
            
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            await ctx.send(f"⚠️ Die Nachricht des Panels konnte nicht gefunden werden. Ein neues Panel wird erstellt: {str(e)}")
            
            # Sende eine neue Nachricht
            embed = discord.Embed(
                title=panel["title"],
                description=panel["description"],
                color=discord.Color.blue()
            )
            
            # Füge Informationen zu jeder Rolle hinzu
            for role_info in panel["roles"]:
                role = ctx.guild.get_role(role_info["role_id"])
                role_name = role.name if role else f"Unbekannte Rolle (ID: {role_info['role_id']})"
                embed.add_field(
                    name=f"{role_info.get('emoji', '')} {role_name}",
                    value="Klicke auf den Button, um diese Rolle zu erhalten/entfernen.",
                    inline=False
                )
            
            # Erstelle das View
            view = await self._create_panel_view(panel)
            
            # Sende das Panel
            panel_message = await ctx.send("Hier ist dein Rollenpanel:", embed=embed, view=view)
            
            # Aktualisiere die Nachrichteninformationen
            panel["channel_id"] = panel_message.channel.id
            panel["message_id"] = panel_message.id
            
            self._save_config()
            
            await ctx.send("✅ Das Self-Roles-Panel wurde erfolgreich neu erstellt!")
            logger.info(f"Self-roles panel recreated in guild {ctx.guild.name} by {ctx.author.display_name}")

async def setup(bot: commands.Bot):
    """Füge den SelfRoles-Cog zum Bot hinzu."""
    await bot.add_cog(SelfRoles(bot))
    logger.info("SelfRoles cog loaded")
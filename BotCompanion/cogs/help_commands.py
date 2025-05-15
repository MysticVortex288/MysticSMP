import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.embed_creator import EmbedCreator

logger = logging.getLogger('discord_bot')

class HelpCommands(commands.Cog):
    """Cog for handling help commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.embed_creator = EmbedCreator()
    
    @commands.hybrid_command(name="help", description="Get help with bot commands")
    @app_commands.describe(command="The specific command to get help with")
    async def help_command(self, ctx: commands.Context, command: str = None):
        """
        Display help information about the bot and its commands.
        
        Args:
            command: Optional specific command to get help with
        """
        prefix = self.bot.command_prefix if isinstance(self.bot.command_prefix, str) else self.bot.command_prefix[0]
        
        if command is None:
            # General help - list all command categories
            await self._send_general_help(ctx, prefix)
        else:
            # Specific command help
            await self._send_command_help(ctx, command, prefix)
    
    async def _send_general_help(self, ctx: commands.Context, prefix: str):
        """Send general help information listing all command categories."""
        # Create main help embed
        embed = discord.Embed(
            title="Bot Help",
            description=(
                f"Here are all the available command categories. Use `{prefix}help <category>` "
                f"for more information about a specific category.\n\n"
                f"You can also use `/help <command>` for help with a specific command."
            ),
            color=discord.Color.blue()
        )
        
        # Add command categories
        categories = {
            "🎯 Invite Tracking": (
                "Track who invited whom to the server\n"
                f"`{prefix}help invites`"
            ),
            "👋 Welcome Messages": (
                "Customize welcome messages for new members\n"
                f"`{prefix}help welcome`"
            ),
            "⬆️ Level System": (
                "Level up by being active in the server\n"
                f"`{prefix}help level`"
            ),
            "🎫 Ticket System": (
                "Create support tickets for users\n"
                f"`{prefix}help ticket`"
            ),
            "🛠️ Admin Commands": (
                "Server and bot administration commands\n"
                f"`{prefix}help admin`"
            ),
            "🔢 Counting Game": (
                "Ein Spiel, bei dem gemeinsam gezählt wird\n"
                f"`{prefix}help counting`"
            ),
            "🎙️ Temporäre Sprachkanäle": (
                "Erstelle und verwalte temporäre Sprachkanäle\n"
                f"`{prefix}help voice`"
            ),
            "🔒 Verifizierung": (
                "Verifizierungssystem mit Rollen-Vergabe\n"
                f"`{prefix}help verify`"
            ),
            "📢 Content-Ankündigungen": (
                "Ankündigung von YouTube/Twitch/TikTok-Links\n"
                f"`{prefix}help announce`"
            ),
            "🏷️ Self-Roles": (
                "Erlaube Nutzern, sich selbst Rollen zuzuweisen\n"
                f"`{prefix}help roles`"
            ),
            "❓ Bot-Assistent": (
                "Stelle Fragen über den Bot und erhalte Antworten\n"
                f"`{prefix}help assistant`"
            ),
            "📊 Server-Statistiken": (
                "Zeigt automatisch aktualisierte Server-Statistiken\n"
                f"`{prefix}help stats`"
            ),
            "🌐 Spracheinstellungen": (
                "Ändere die Sprache des Bots für dich oder den Server\n"
                f"`{prefix}help language`"
            ),
            "🔐 Kanalsperrung": (
                "Sperre Kanäle für bestimmte Zeiträume (z.B. Ferien)\n"
                f"`{prefix}help lock`"
            ),
            "😀 Emoji-Stealer": (
                "Kopiere Emojis von anderen Servern\n"
                f"`{prefix}help emojis`"
            ),
            "🔒 Captcha-Verifizierung": (
                "Captcha-Verifizierung für neue Mitglieder\n"
                f"`{prefix}help captcha`"
            ),
            "⚒️ Moderation": (
                "Moderationsbefehle wie Kick, Ban, Mute und Warnen\n"
                f"`{prefix}help mod`"
            ),
            "💰 Economy": (
                "Verdiene und verwende Credits mit Daily, Work, Beg, Rob usw.\n"
                f"`{prefix}help economy`"
            )
        }
        
        for category, description in categories.items():
            embed.add_field(name=category, value=description, inline=False)
        
        # Add general information
        embed.set_footer(text=f"Type {prefix}help <command> for detailed help on a command")
        
        await ctx.send(embed=embed)
    
    async def _send_command_help(self, ctx: commands.Context, command_name: str, prefix: str):
        """Send help information for a specific command or category."""
        # Lower the command name for easier comparison
        command_name = command_name.lower()
        
        # Check if it's a category help request
        if command_name in ["invites", "invite", "invite-tracking"]:
            await self._send_invites_help(ctx, prefix)
            return
        elif command_name in ["welcome", "welcomes", "welcome-messages"]:
            await self._send_welcome_help(ctx, prefix)
            return
        elif command_name in ["level", "levels", "level-system", "leveling", "rank"]:
            await self._send_level_help(ctx, prefix)
            return
        elif command_name in ["ticket", "tickets", "ticket-system", "support"]:
            await self._send_ticket_help(ctx, prefix)
            return
        elif command_name in ["admin", "administration", "admin-commands"]:
            await self._send_admin_help(ctx, prefix)
            return
        elif command_name in ["counting", "count", "counting-game", "zahlen"]:
            await self._send_counting_help(ctx, prefix)
            return
        elif command_name in ["voice", "tempvoice", "temp-voice", "tempvc", "temp"]:
            await self._send_voice_help(ctx, prefix)
            return
        elif command_name in ["verify", "verification", "verifizierung"]:
            await self._send_verify_help(ctx, prefix)
            return
        elif command_name in ["announce", "announcer", "content", "content-announcer"]:
            await self._send_announce_help(ctx, prefix)
            return
        elif command_name in ["roles", "selfroles", "self-roles", "role"]:
            await self._send_roles_help(ctx, prefix)
            return
        elif command_name in ["assistant", "bot-assistant", "fragen", "hilfe", "assistent"]:
            await self._send_assistant_help(ctx, prefix)
            return
        elif command_name in ["stats", "statistics", "server-stats", "status", "statistiken"]:
            await self._send_stats_help(ctx, prefix)
            return
        elif command_name in ["language", "languages", "sprache", "sprachen"]:
            await self._send_language_help(ctx, prefix)
            return
        elif command_name in ["lock", "channel-lock", "kanalsperrung", "lockchannel", "kanalsperre"]:
            await self._send_lock_help(ctx, prefix)
            return
        elif command_name in ["emojis", "emoji", "steal", "emoji-stealer", "stealemoji", "emojisteal"]:
            await self._send_emoji_help(ctx, prefix)
            return
        elif command_name in ["captcha", "captcha-verification", "verification-captcha", "verifycaptcha"]:
            await self._send_captcha_help(ctx, prefix)
            return
        elif command_name in ["mod", "moderation", "moderieren", "kick", "ban", "mute", "warn"]:
            await self._send_moderation_help(ctx, prefix)
            return
        elif command_name in ["economy", "eco", "money", "credits", "currency", "wirtschaft"]:
            await self._send_economy_help(ctx, prefix)
            return
        
        # Try to find the command
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Command Not Found",
                f"No command called '{command_name}' was found. Type `{prefix}help` for a list of commands."
            ))
            return
        
        # Create command help embed
        embed = discord.Embed(
            title=f"Command: {prefix}{command.name}",
            description=command.help or "No description provided.",
            color=discord.Color.blue()
        )
        
        # Add command usage
        usage = f"{prefix}{command.name}"
        if command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        
        # Add aliases if any
        if command.aliases:
            aliases = ", ".join([f"{prefix}{alias}" for alias in command.aliases])
            embed.add_field(name="Aliases", value=aliases, inline=False)
        
        # Add subcommands if any
        if isinstance(command, commands.Group):
            subcommands = []
            for subcommand in command.commands:
                subcommands.append(f"`{prefix}{command.name} {subcommand.name}` - {subcommand.help.split('.')[0] if subcommand.help else 'No description'}")
            
            if subcommands:
                embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
        
        await ctx.send(embed=embed)
    
    async def _send_invites_help(self, ctx: commands.Context, prefix: str):
        """Send help information for invite tracking commands."""
        commands_dict = {
            f"{prefix}invites [member]": "Show how many people you or another member have invited to the server.",
            f"{prefix}invite-leaderboard": "Display a leaderboard of members with the most invites."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Invite Tracking Commands",
            description=(
                "These commands allow you to track and view information about server invites. "
                "The bot automatically tracks who invited whom to the server."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
    
    async def _send_welcome_help(self, ctx: commands.Context, prefix: str):
        """Send help information for welcome message commands."""
        commands_dict = {
            f"{prefix}welcome channel <channel>": "Set the channel for welcome messages.",
            f"{prefix}welcome message <message>": "Set the welcome message. Use variables like {user_mention}, {inviter}, etc.",
            f"{prefix}welcome toggle": "Toggle welcome messages on or off.",
            f"{prefix}welcome embed": "Toggle whether to use embeds for welcome messages.",
            f"{prefix}welcome color <hex>": "Set the color for welcome message embeds.",
            f"{prefix}welcome test": "Test the current welcome message settings.",
            f"{prefix}welcome variables": "Show available variables for welcome messages.",
            f"{prefix}welcome settings": "Show current welcome message settings."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Welcome Message Commands",
            description=(
                "These commands allow you to configure and customize welcome messages for new members. "
                "Welcome messages can include information about who invited the new member."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
    
    async def _send_admin_help(self, ctx: commands.Context, prefix: str):
        """Send help information for admin commands."""
        commands_dict = {
            f"{prefix}prefix <new_prefix>": "Change the bot's command prefix.",
            f"{prefix}sync": "Sync slash commands with Discord (admin only)."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Admin Commands",
            description=(
                "These commands are for server administrators to configure the bot."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
    
    async def _send_level_help(self, ctx: commands.Context, prefix: str):
        """Send help information for level system commands."""
        commands_dict = {
            f"{prefix}setuplevel": "Richtet das Level-System ein und zeigt die Einstellungen an.",
            f"{prefix}leaderboard": "Zeigt die Top-10 Nutzer mit den höchsten Levels an.",
            f"{prefix}rank [member]": "Zeigt den Rang und XP-Fortschritt eines Nutzers an.",
            f"{prefix}setlevelrole <level> <rolle>": "Legt eine Rolle fest, die bei einem Level vergeben wird.",
            f"{prefix}setxprange <min> <max>": "Legt den XP-Bereich pro Nachricht fest.",
            f"{prefix}setleaderboardchannel": "Richtet ein automatisch aktualisierendes Leaderboard im aktuellen Kanal ein."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Level-System Befehle",
            description=(
                "Diese Befehle ermöglichen das Leveln durch Aktivität im Server. "
                "Nutzer erhalten XP für Nachrichten und können Level aufsteigen, "
                "wodurch sie automatisch bestimmte Rollen bekommen können."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
        
    async def _send_ticket_help(self, ctx: commands.Context, prefix: str):
        """Send help information for ticket system commands."""
        commands_dict = {
            f"{prefix}setupticket [category] [support_role]": "Richtet das Ticket-System ein.",
            f"{prefix}addsupportrole <role>": "Fügt eine Rolle zur Liste der Support-Rollen hinzu.",
            f"{prefix}removesupportrole <role>": "Entfernt eine Rolle aus der Liste der Support-Rollen.",
            f"{prefix}listsupportroles": "Zeigt eine Liste aller Support-Rollen an.",
            f"{prefix}ticketpanel [message]": "Erstellt ein Panel mit Button zum Erstellen von Tickets.",
            f"{prefix}closeticket": "Schließt das aktuelle Ticket.",
            f"{prefix}addtoticket <user>": "Fügt einen Benutzer zum aktuellen Ticket hinzu.",
            f"{prefix}setticketmessage <message>": "Legt die Nachricht fest, die beim Erstellen eines Tickets angezeigt wird.",
            f"{prefix}setlogchannel <channel>": "Legt den Kanal fest, in dem Ticket-Aktionen protokolliert werden."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Ticket-System Befehle",
            description=(
                "Diese Befehle ermöglichen die Einrichtung und Verwaltung von Support-Tickets. "
                "Nutzer können Tickets erstellen, um Hilfe zu erhalten, und der Support-Staff kann "
                "diese verwalten und beantworten. Mehrere Support-Rollen können Zugriff auf Tickets haben."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)
        
    async def _send_counting_help(self, ctx: commands.Context, prefix: str):
        """Send help information for counting game commands."""
        commands_dict = {
            f"{prefix}countingsetup [channel]": "Richtet das Counting-Game in einem Kanal ein.",
            f"{prefix}countingreset [channel]": "Setzt das Counting-Game in einem Kanal zurück.",
            f"{prefix}countingdelete [channel]": "Entfernt das Counting-Game aus einem Kanal.",
            f"{prefix}countingstatus [channel]": "Zeigt den aktuellen Status des Counting-Games in einem Kanal an."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Counting-Game Befehle",
            description=(
                "Diese Befehle ermöglichen das Einrichten und Verwalten des Counting-Games. "
                "Im Counting-Game müssen Mitglieder gemeinsam in der richtigen Reihenfolge zählen. "
                "Der Bot überwacht die Zahlenfolge und stellt sicher, dass keine Fehler gemacht werden."
            ),
            commands=commands_dict
        )
        
        # Spielregeln hinzufügen
        embed.add_field(
            name="Spielregeln", 
            value=(
                "1. Beginne mit der Zahl 1\n"
                "2. Jede nachfolgende Nachricht muss die nächste Zahl in der Sequenz sein\n"
                "3. Dieselbe Person darf nicht zweimal hintereinander zählen\n"
                "4. Wenn jemand eine falsche Zahl sendet, wird der Zähler zurückgesetzt"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _send_voice_help(self, ctx: commands.Context, prefix: str):
        """Send help information for temporary voice channel commands."""
        commands_dict = {
            f"{prefix}setupvoice [category]": "Richtet temporäre Sprachkanäle ein.",
            f"{prefix}removevoice": "Entfernt die Einrichtung für temporäre Sprachkanäle."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Temporäre Sprachkanäle Befehle",
            description=(
                "Diese Befehle ermöglichen die Einrichtung und Verwaltung von temporären Sprachkanälen. "
                "Nutzer können eigene Sprachkanäle erstellen, indem sie einem speziellen Kanal beitreten. "
                "Diese Kanäle werden automatisch gelöscht, wenn sie leer sind."
            ),
            commands=commands_dict
        )
        
        # Funktionen hinzufügen
        embed.add_field(
            name="Funktionen für Kanalbesitzer", 
            value=(
                "Als Besitzer eines temporären Sprachkanals kannst du:\n"
                "• Den Kanal umbenennen\n"
                "• Das Nutzerlimit ändern\n"
                "• Den Kanal sperren/entsperren\n"
                "• Den Kanal verstecken/anzeigen\n"
                "• Nutzer hinzufügen, entfernen oder stumm schalten"
            ), 
            inline=False
        )
        
        # Wie es funktioniert
        embed.add_field(
            name="Wie es funktioniert", 
            value=(
                "1. Ein Administrator richtet die temporären Sprachkanäle mit `/setupvoice` ein\n"
                "2. Nutzer treten dem '➕ Erstelle einen Sprachkanal' Kanal bei\n"
                "3. Ein eigener Sprachkanal wird erstellt und der Nutzer wird hinein verschoben\n"
                "4. Eine Kontrollnachricht mit Buttons wird gesendet\n"
                "5. Der Kanal wird automatisch gelöscht, wenn er leer ist"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _send_verify_help(self, ctx: commands.Context, prefix: str):
        """Send help information for verification commands."""
        commands_dict = {
            f"{prefix}verify [message]": "Sendet eine Verifizierungsnachricht mit einem Button.",
            f"{prefix}setupverify [message]": "Richtet das Verifizierungssystem ein und sendet eine Nachricht."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Verifizierung Befehle",
            description=(
                "Diese Befehle ermöglichen die Einrichtung eines Verifizierungssystems. "
                "Nutzer können sich verifizieren, indem sie auf einen Button klicken, um die Member-Rolle zu erhalten."
            ),
            commands=commands_dict
        )
        
        # Wie es funktioniert
        embed.add_field(
            name="Wie es funktioniert", 
            value=(
                "1. Ein Administrator sendet eine Verifizierungsnachricht mit `/verify` oder `/setupverify`\n"
                "2. Die Nachricht enthält einen Button zur Verifizierung\n"
                "3. Nutzer klicken auf den Button und erhalten die Member-Rolle\n"
                "4. Die Member-Rolle wird automatisch erstellt, wenn sie nicht existiert"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _send_announce_help(self, ctx: commands.Context, prefix: str):
        """Send help information for content announcement commands."""
        commands_dict = {
            f"{prefix}setannouncement [channel]": "Setzt den Kanal für Stream- und Video-Ankündigungen",
            f"{prefix}removeannouncement": "Entfernt den Ankündigungskanal für Streams und Videos",
            f"{prefix}addtiktokcreator <username>": "Fügt einen TikTok-Creator zur Überwachungsliste hinzu",
            f"{prefix}removetiktokcreator <username>": "Entfernt einen TikTok-Creator von der Überwachungsliste",
            f"{prefix}listtiktokcreators": "Zeigt eine Liste aller überwachten TikTok-Creator an"
        }
        
        embed = discord.Embed(
            title="📢 Content-Announcer Hilfe",
            description="Der Content-Announcer bietet zwei Hauptfunktionen:",
            color=discord.Color.from_rgb(255, 0, 128)  # Pink/Magenta-Farbe für Content
        )
        
        # Erste Funktion: Link-Erkennung
        embed.add_field(
            name="📎 Funktion 1: Link-Erkennung",
            value=(
                "Der Bot erkennt automatisch Links zu unterstützten Plattformen in Nachrichten und "
                "kündigt diese im festgelegten Ankündigungskanal an."
            ),
            inline=False
        )
        
        # Zweite Funktion: TikTok-Creator-Tracking
        embed.add_field(
            name="📱 Funktion 2: TikTok-Creator-Tracking",
            value=(
                "Der Bot kann ausgewählte TikTok-Creator überwachen und automatisch neue Videos ankündigen, "
                "sobald diese hochgeladen werden (Überprüfung alle 30 Minuten)."
            ),
            inline=False
        )
        
        # Befehle hinzufügen
        embed.add_field(
            name="⌨️ Verfügbare Befehle",
            value="\n".join([f"• `{cmd}` - {desc}" for cmd, desc in commands_dict.items()]),
            inline=False
        )
        
        # Unterstützte Plattformen mit Emojis
        embed.add_field(
            name="🌐 Unterstützte Plattformen", 
            value=(
                "🔴 **YouTube** - Videos, Shorts und Livestreams\n"
                "🟣 **Twitch** - Live-Streams\n"
                "⚫ **TikTok** - Videos und Creator-Tracking"
            ), 
            inline=False
        )
        
        # Beispiele mit Emojis
        embed.add_field(
            name="📋 Beispiele", 
            value=(
                "**Link-Erkennung:**\n"
                "1️⃣ `/setannouncement #ankündigungen`\n"
                "2️⃣ Ein Nutzer teilt einen YouTube-Link\n"
                "3️⃣ Der Bot sendet eine Ankündigung im #ankündigungen Kanal\n\n"
                "**TikTok-Creator-Tracking:**\n"
                "1️⃣ `/setannouncement #tiktok-videos`\n"
                "2️⃣ `/addtiktokcreator tiktoker123`\n"
                "3️⃣ Der Bot überwacht den Creator und kündigt neue Videos an"
            ), 
            inline=False
        )
        
        # TikTok-Creator-Verwaltung
        embed.add_field(
            name="🔍 TikTok-Creator-Verwaltung", 
            value=(
                "• Füge einen Creator hinzu: `/addtiktokcreator username`\n"
                "• Zeige alle überwachten Creator: `/listtiktokcreators`\n"
                "• Entferne einen Creator: `/removetiktokcreator username`\n"
                "• Der Bot überprüft automatisch alle 30 Minuten auf neue Videos"
            ), 
            inline=False
        )
        
        # Fußzeile mit Tipp
        embed.set_footer(text=f"Tipp: Verwende {prefix}setannouncement in dem Kanal, in dem Ankündigungen erscheinen sollen!")
        
        await ctx.send(embed=embed)
        
    async def _send_music_help(self, ctx: commands.Context, prefix: str):
        """Send help information for music player commands."""
        commands_dict = {
            f"{prefix}join": "Lässt den Bot deinem aktuellen Sprachkanal beitreten.",
            f"{prefix}leave": "Der Bot verlässt den aktuellen Sprachkanal.",
            f"{prefix}play <query>": "Spielt einen Song aus YouTube ab oder fügt ihn zur Warteschlange hinzu.",
            f"{prefix}pause": "Pausiert die aktuelle Wiedergabe.",
            f"{prefix}resume": "Setzt die pausierte Wiedergabe fort.",
            f"{prefix}stop": "Stoppt die Wiedergabe und leert die Warteschlange.",
            f"{prefix}skip": "Überspringt den aktuellen Song.",
            f"{prefix}queue": "Zeigt die aktuelle Warteschlange an.",
            f"{prefix}nowplaying": "Zeigt Informationen zum aktuellen Song an.",
            f"{prefix}volume [0-100]": "Stellt die Lautstärke ein oder zeigt sie an.",
            f"{prefix}clear": "Leert die Warteschlange.",
            f"{prefix}remove <position>": "Entfernt einen Song aus der Warteschlange.",
            f"{prefix}shuffle": "Mischt die Warteschlange zufällig durch."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Musik-Player Befehle",
            description=(
                "Diese Befehle ermöglichen das Abspielen von Musik in Sprachkanälen. "
                "Der Bot sucht automatisch auf YouTube nach dem gewünschten Song und spielt ihn ab."
            ),
            commands=commands_dict
        )
        
        await ctx.send(embed=embed)

    async def _send_roles_help(self, ctx: commands.Context, prefix: str):
        """Send help information for self-roles commands."""
        commands_dict = {
            f"{prefix}createroles": "Startet den Assistenten zum Erstellen eines Self-Roles Panels.",
            f"{prefix}createcolors": "Erstellt ein vorgefertigtes Panel mit Farbrollen für Benutzer.",
            f"{prefix}editroles [panel_number]": "Bearbeitet ein bestehendes Self-Roles Panel oder zeigt alle verfügbaren Panels an."
        }
        
        embed = discord.Embed(
            title="🏷️ Self-Roles System",
            description=(
                "Mit dem Self-Roles System können Benutzer selbst entscheiden, welche Rollen sie haben möchten. "
                "Administratoren können interaktive Panels mit Knöpfen erstellen, die es den Benutzern ermöglichen, "
                "Rollen einfach per Klick hinzuzufügen oder zu entfernen."
            ),
            color=discord.Color.from_rgb(114, 137, 218)  # Discord Blurple
        )
        
        # Befehle hinzufügen
        embed.add_field(
            name="⌨️ Verfügbare Befehle",
            value="\n".join([f"• `{cmd}` - {desc}" for cmd, desc in commands_dict.items()]),
            inline=False
        )
        
        # Wie man ein Panel erstellt
        embed.add_field(
            name="🔧 Ein Rollen-Panel erstellen",
            value=(
                "1. Verwende den Befehl `/createroles`\n"
                "2. Folge dem Assistenten, um Titel und Beschreibung einzugeben\n"
                "3. Erstelle Kategorien für deine Rollen (optional)\n"
                "4. Füge Rollen mit dem Format `Rollenname Emoji Farbe` hinzu\n"
                "5. Verfügbare Farben: `blurple`, `grey`, `green`, `red`\n"
                "6. Rollen werden automatisch erstellt, wenn sie nicht existieren\n"
                "7. Beende die Rolleneingabe mit `fertig`"
            ),
            inline=False
        )
        
        # Beispiel
        embed.add_field(
            name="📋 Beispiel für die Rolleneingabe",
            value=(
                "`Spieler 🎮 green` - Erstellt einen grünen Button und Rolle\n"
                "`News 📰 blurple` - Erstellt einen blauen Button und Rolle\n"
                "`Events 🎉 red` - Erstellt einen roten Button und Rolle\n\n"
                "**NEU:** Rollen können jetzt in Kategorien organisiert werden!"
            ),
            inline=False
        )
        
        # Vorteile
        embed.add_field(
            name="✨ Vorteile des Systems",
            value=(
                "• Benutzer können Rollen selbst hinzufügen/entfernen\n"
                "• Visuelle, leicht verständliche Oberfläche mit Buttons\n"
                "• Organisation der Rollen in Kategorien möglich\n"
                "• Anpassbare Button-Farben und Emojis\n"
                "• Automatische Erstellung neuer Rollen\n"
                "• Schöner interaktiver Assistent mit Embeds\n"
                "• Persistente Panels, die auch nach Neustarts funktionieren"
            ),
            inline=False
        )
        
        # Fußzeile
        embed.set_footer(text="Hinweis: Nur Administratoren können Self-Roles Panels erstellen und bearbeiten.")
        
        await ctx.send(embed=embed)

    async def _send_assistant_help(self, ctx: commands.Context, prefix: str):
        """Send help information for bot assistant commands."""
        commands_dict = {
            f"{prefix}fragebot <frage>": "Stelle eine Frage über den Bot und erhalte eine Antwort.",
            f"{prefix}kategorie <kategorie>": "Zeigt alle Fragen einer bestimmten Kategorie an.",
            f"{prefix}allfragen": "Zeigt alle verfügbaren FAQ-Kategorien an (nur für Administratoren).",
            f"{prefix}addfaq <frage> <antwort> <kategorie> [aliase]": "Fügt eine neue FAQ hinzu (nur für Administratoren).",
            f"{prefix}removefaq <frage>": "Entfernt eine FAQ (nur für Administratoren).",
            f"{prefix}setupassistant [channel]": "Richtet einen Kanal ein, in dem der Bot automatisch auf Fragen antwortet (ohne Befehle).",
            f"{prefix}removeassistant [channel]": "Entfernt den Bot-Assistenten aus einem Kanal.",
            f"{prefix}listassistant": "Zeigt eine Liste aller Assistenten-Kanäle an."
        }
        
        embed = discord.Embed(
            title="❓ Bot-Assistent Befehle",
            description=(
                "Der Bot-Assistent kann Fragen über den Bot beantworten und hilft dir, "
                "den Bot besser zu verstehen und zu nutzen."
            ),
            color=discord.Color.blue()
        )
        
        # Befehle hinzufügen
        for cmd, desc in commands_dict.items():
            embed.add_field(name=cmd, value=desc, inline=False)
        
        # Beispiele hinzufügen
        embed.add_field(
            name="📋 Beispielfragen",
            value=(
                "• `Wie funktioniert das Level-System?`\n"
                "• `Was kann dieser Bot alles?`\n"
                "• `Wie erstelle ich ein Ticket?`\n"
                "• `Wie bekomme ich Rollen?`"
            ),
            inline=False
        )
        
        # Kategorien
        embed.add_field(
            name="🗂️ Verfügbare Kategorien",
            value=(
                "• Allgemein\n"
                "• Level-System\n"
                "• Ticket-System\n"
                "• Self-Roles\n"
                "• Temp-Voice\n"
                "• Counting-Game\n"
                "• Verifizierung\n"
                "• Content-Announcer\n"
                "• Invite-Tracking\n"
                "• Willkommensnachrichten"
            ),
            inline=False
        )
        
        # Hinweis
        embed.set_footer(text="Verwende /fragebot gefolgt von deiner Frage, um Hilfe zu erhalten.")
        
        await ctx.send(embed=embed)
        
    async def _send_stats_help(self, ctx: commands.Context, prefix: str):
        """Send help information for server stats commands."""
        commands_dict = {
            f"{prefix}setupstats": "Richtet automatisch aktualisierte Statistik-Kanäle ein.",
            f"{prefix}removestats": "Entfernt alle Statistik-Kanäle, die mit setupstats erstellt wurden."
        }
        
        embed = discord.Embed(
            title="📊 Server-Statistiken Befehle",
            description=(
                "Mit diesen Befehlen kannst du automatisch aktualisierte Statistik-Kanäle einrichten, "
                "die verschiedene Informationen über den Server anzeigen. Diese werden alle 5 Minuten aktualisiert."
            ),
            color=discord.Color.blue()
        )
        
        # Befehle hinzufügen
        for cmd, desc in commands_dict.items():
            embed.add_field(name=cmd, value=desc, inline=False)
        
        # Verfügbare Statistiken hinzufügen
        embed.add_field(
            name="📋 Verfügbare Statistiken",
            value=(
                "• 👥 Mitgliederanzahl\n"
                "• 🟢 Online-Mitglieder\n"
                "• 💬 Anzahl der Textkanäle\n"
                "• 🔊 Anzahl der Sprachkanäle\n"
                "• 🎂 Server-Alter in Tagen\n"
                "• 👑 Häufigste Rolle\n"
                "• 🚀 Anzahl der Server-Boosts\n"
                "• ⭐ Boost-Level des Servers\n"
                "• 😄 Anzahl der Emojis\n"
                "• 🔰 Anzahl der Rollen"
            ),
            inline=False
        )
        
        # Hinweis hinzufügen
        embed.add_field(
            name="ℹ️ Hinweis",
            value=(
                "Die Statistik-Kanäle werden als Sprachkanäle erstellt, die nicht betreten werden können. "
                "Die Statistiken werden automatisch aktualisiert, ohne dass weitere Eingriffe notwendig sind."
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def _send_lock_help(self, ctx: commands.Context, prefix: str):
        """Send help information for channel locking commands."""
        commands_dict = {
            f"{prefix}lock [channel] [reason]": "Sperrt einen Kanal, sodass nur noch Administratoren schreiben können.",
            f"{prefix}unlock [channel]": "Entsperrt einen zuvor gesperrten Kanal.",
            f"{prefix}lockuntil [channel] <datum> [reason]": "Sperrt einen Kanal bis zu einem bestimmten Datum (Format: TT.MM.YYYY oder TT.MM.YYYY HH:MM).",
            f"{prefix}lockedchannels": "Zeigt eine Liste aller gesperrten Kanäle mit Informationen an.",
            f"{prefix}lockall [datum] [reason]": "Sperrt alle Textkanäle auf dem Server (für z.B. Ferien).",
            f"{prefix}unlockall": "Entsperrt alle gesperrten Kanäle auf dem Server."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Kanalsperrung Befehle",
            description=(
                "Diese Befehle ermöglichen das Sperren und Entsperren von Kanälen für bestimmte Zeiträume, "
                "wie z.B. während der Weihnachtsferien oder anderen Ferienzeiten. "
                "Während ein Kanal gesperrt ist, können nur Administratoren darin schreiben."
            ),
            commands=commands_dict
        )
        
        # Hinweise hinzufügen
        embed.add_field(
            name="Datumsformat", 
            value=(
                "Verwende eines der folgenden Formate für das Datum:\n"
                "• TT.MM.YYYY (z.B. 31.12.2025) - Entsperrung um Mitternacht\n"
                "• TT.MM.YYYY HH:MM (z.B. 31.12.2025 18:00) - Entsperrung zur angegebenen Zeit"
            ), 
            inline=False
        )
        
        embed.add_field(
            name="Beispiele", 
            value=(
                f"`{prefix}lock #ankündigungen Wartungsarbeiten` - Sperrt den Ankündigungskanal\n"
                f"`{prefix}lockuntil #allgemein 24.12.2025 Weihnachtsferien` - Sperrt bis Heiligabend\n"
                f"`{prefix}lockall 01.01.2026 Neujahrsferien` - Sperrt alle Kanäle bis zum Neujahr"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    async def _send_emoji_help(self, ctx: commands.Context, prefix: str):
        """Send help information for emoji stealer commands."""
        commands_dict = {
            f"{prefix}steal <emoji> [name]": "Kopiert ein benutzerdefiniertes Emoji von einem anderen Server.",
            f"{prefix}stealall <emojis...>": "Kopiert mehrere Emojis auf einmal.",
            f"{prefix}liststolen [limit]": "Zeigt eine Liste der zuletzt kopierten Emojis an.",
            f"{prefix}searchemojiurl <emoji>": "Gibt die URL eines benutzerdefinierten Emojis zurück."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Emoji-Stealer Befehle",
            description=(
                "Diese Befehle ermöglichen das Kopieren von Emojis von anderen Servern. "
                "Du kannst sowohl einzelne Emojis als auch mehrere auf einmal kopieren. "
                "Um Emojis stehlen zu können, benötigst du die 'Emojis verwalten'-Berechtigung."
            ),
            commands=commands_dict
        )
        
        # Hinweise hinzufügen
        embed.add_field(
            name="Wie man Emojis kopiert", 
            value=(
                "1. Finde ein Emoji auf einem anderen Server, das du kopieren möchtest\n"
                "2. Schreibe `\\` vor dem Emoji (z.B. `\\:cooles_emoji:`) und sende die Nachricht\n"
                "3. Das Emoji wird als Code angezeigt, z.B. `<:cooles_emoji:123456789012345678>`\n"
                "4. Kopiere diesen Code und verwende ihn mit dem `steal`-Befehl"
            ), 
            inline=False
        )
        
        embed.add_field(
            name="Beispiele", 
            value=(
                f"`{prefix}steal <:cooles_emoji:123456789012345678>` - Kopiert das Emoji mit seinem Originalnamen\n"
                f"`{prefix}steal <:cooles_emoji:123456789012345678> mein_emoji` - Kopiert das Emoji mit neuem Namen\n"
                f"`{prefix}stealall <:emoji1:123456789012345678> <:emoji2:987654321098765432>` - Kopiert beide Emojis"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def _send_captcha_help(self, ctx: commands.Context, prefix: str):
        """Send help information for captcha verification commands."""
        commands_dict = {
            f"{prefix}setupcaptcha [enabled] [role]": "Aktiviert oder deaktiviert die Captcha-Verifizierung und legt die Rolle fest.",
            f"{prefix}testcaptcha": "Testet das Captcha-System, indem ein Captcha an dich gesendet wird."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Captcha-Verifizierung Befehle",
            description=(
                "Diese Befehle ermöglichen die Einrichtung eines Captcha-Verifizierungssystems für neue Mitglieder. "
                "Nach dem Beitritt erhalten Nutzer eine DM mit einem Captcha, das sie lösen müssen, um Zugang zum Server zu erhalten. "
                "Nach erfolgreicher Verifizierung erhalten sie automatisch die Member-Rolle."
            ),
            commands=commands_dict
        )
        
        # Funktionsweise hinzufügen
        embed.add_field(
            name="Funktionsweise", 
            value=(
                "1. Wenn ein neuer Nutzer dem Server beitritt, erhält er eine DM mit einem Captcha\n"
                "2. Der Nutzer muss den Captcha-Code korrekt eingeben, um sich zu verifizieren\n"
                "3. Nach erfolgreicher Verifizierung erhält der Nutzer automatisch die Member-Rolle\n"
                "4. Wenn die Member-Rolle nicht existiert, wird sie automatisch erstellt\n"
                "5. Nach mehreren falschen Versuchen oder nach Ablauf des Captchas muss der Nutzer den Server erneut betreten"
            ), 
            inline=False
        )
        
        # Einrichtung hinzufügen
        embed.add_field(
            name="Einrichtung", 
            value=(
                f"1. Aktiviere das System mit `{prefix}setupcaptcha true`\n"
                f"2. Optional kannst du eine andere Rolle festlegen: `{prefix}setupcaptcha true @Verifiziert`\n"
                f"3. Du kannst das System jederzeit deaktivieren mit `{prefix}setupcaptcha false`"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    async def _send_language_help(self, ctx: commands.Context, prefix: str):
        """Send help information for language settings commands."""
        commands_dict = {
            f"{prefix}language [language]": "Ändere deine bevorzugte Sprache oder zeige deine aktuelle Sprache an.",
            f"{prefix}serverlanguage [language]": "Ändere die Standardsprache des Servers oder zeige die aktuelle Serversprache an (nur für Administratoren)."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Spracheinstellungen Befehle",
            description=(
                "Diese Befehle ermöglichen es dir, die Sprache des Bots für dich persönlich oder für den gesamten Server zu ändern. "
                "Unterstützte Sprachen sind Deutsch (de) und Englisch (en)."
            ),
            commands=commands_dict
        )
        
        # Hinzufügen von Beispielen
        embed.add_field(
            name="Beispiele", 
            value=(
                f"`{prefix}language de` - Stellt deine Sprache auf Deutsch ein\n"
                f"`{prefix}language en` - Sets your language to English\n"
                f"`{prefix}language` - Zeigt deine aktuelle Spracheinstellung an\n"
                f"`{prefix}serverlanguage de` - Stellt die Serversprache auf Deutsch ein (nur für Administratoren)"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def _send_moderation_help(self, ctx: commands.Context, prefix: str):
        """Send help information for moderation commands."""
        commands_dict = {
            f"{prefix}setmodlog [channel]": "Legt den Kanal für Moderationslog-Nachrichten fest.",
            f"{prefix}warn <member> [reason]": "Verwarnt einen Benutzer und sendet ihm eine DM.",
            f"{prefix}kick <member> [reason]": "Kickt einen Benutzer vom Server.",
            f"{prefix}ban <user> [delete_days] [reason]": "Bannt einen Benutzer vom Server.",
            f"{prefix}unban <user_id> [reason]": "Entbannt einen Benutzer vom Server.",
            f"{prefix}mute <member> <duration> [reason]": "Schaltet einen Benutzer für eine bestimmte Zeit stumm.",
            f"{prefix}unmute <member> [reason]": "Hebt die Stummschaltung eines Benutzers auf.",
            f"{prefix}modlogs <user>": "Zeigt die Moderationsaktionen für einen Benutzer an.",
            f"{prefix}clear <amount>": "Löscht eine bestimmte Anzahl von Nachrichten (1-100).",
            f"{prefix}allclear [confirm]": "Löscht alle Nachrichten in einem Kanal (Administrator)."
        }
        
        embed = self.embed_creator.create_help_embed(
            title="Moderationsbefehle",
            description=(
                "Diese Befehle dienen zur Moderation des Servers und zum Verwalten von "
                "Regelbrüchen. Bei Verwendung werden Benachrichtigungen an die betroffenen Benutzer gesendet "
                "und Aktionen protokolliert."
            ),
            commands=commands_dict
        )
        
        # Hinweise zur Verwendung
        embed.add_field(
            name="Hinweise",
            value=(
                "- Für alle Befehle werden entsprechende Berechtigungen benötigt\n"
                "- Benutzer erhalten automatisch DM-Benachrichtigungen\n"
                "- Moderatoren erhalten eine Bestätigung über die durchgeführte Aktion\n"
                "- Alle Aktionen werden in der `modlogs`-Historie gespeichert\n"
                "- Nutze `/setmodlog` um einen Kanal für Moderationslogs festzulegen"
            ),
            inline=False
        )
        
        # Erklärung der Dauer-Parameter
        embed.add_field(
            name="Dauer-Formate",
            value=(
                "Für den `mute`-Befehl werden folgende Zeitformate unterstützt:\n"
                "- `s` für Sekunden (z.B. 30s)\n"
                "- `m` für Minuten (z.B. 5m)\n"
                "- `h` für Stunden (z.B. 2h)\n"
                "- `d` für Tage (z.B. 7d)\n"
                "Beispiel: `/mute @Benutzer 3h Spam im Chat`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def _send_economy_help(self, ctx: commands.Context, prefix: str):
        """Send help information for economy commands."""
        commands_dict = {
            f"{prefix}balance [user]": "Zeigt deinen Kontostand oder den eines anderen Nutzers an.",
            f"{prefix}daily": "Hole deine tägliche Belohnung ab. Längere Streaks geben Bonuscredits!",
            f"{prefix}work": "Arbeite, um Credits zu verdienen. Verschiedene Jobs geben unterschiedliche Belohnungen.",
            f"{prefix}beg": "Bettle um ein paar Credits. Kann erfolgreich sein oder nicht.",
            f"{prefix}pay <user> <amount>": "Überweise Credits an einen anderen Nutzer.",
            f"{prefix}rob <user>": "Versuche, einen anderen Nutzer auszurauben. Kann mit einer Strafe enden!",
            f"{prefix}richlist": "Zeigt eine Rangliste der reichsten Nutzer auf dem Server an.",
            f"{prefix}economy_help": "Zeigt diese Hilfeseite speziell für Economy-Befehle an."
        }
        
        # Füge Admin-Befehle hinzu, wenn der Nutzer Admin-Rechte hat
        if ctx.author.guild_permissions.administrator:
            commands_dict[f"{prefix}economy_settings [setting] [value]"] = "**[Admin]** Verwaltet Economy-Einstellungen wie Chancen, Cooldowns und Beträge."
        
        embed = self.embed_creator.create_help_embed(
            title="💰 Economy-Befehle",
            description=(
                "Die Economy-Befehle ermöglichen es dir, Credits zu verdienen, auszugeben und mit anderen Nutzern zu handeln. "
                "Benutze diese Befehle, um virtuelle Währung auf dem Server zu verdienen und zu verwenden."
            ),
            commands=commands_dict
        )
        
        # Grundlegende Informationen
        embed.add_field(
            name="Wie man Credits verdient", 
            value=(
                "• Täglich: `/daily` für eine tägliche Belohnung\n"
                "• Arbeiten: `/work` um in verschiedenen Jobs zu arbeiten\n"
                "• Betteln: `/beg` um nach Credits zu fragen\n"
                "• Rauben: `/rob` um andere Nutzer auszurauben (riskant!)"
            ), 
            inline=False
        )
        
        # Tipps
        embed.add_field(
            name="Tipps und Strategien", 
            value=(
                "• Hole deine tägliche Belohnung regelmäßig ab, um einen Streak-Bonus zu erhalten\n"
                "• Versuche dich an verschiedenen Arbeiten, da einige mehr zahlen können\n"
                "• Sei vorsichtig beim Ausrauben anderer Spieler - du könntest bestraft werden!\n"
                "• Überprüfe regelmäßig die Rangliste, um zu sehen, wo du stehst"
            ), 
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add the HelpCommands cog to the bot."""
    await bot.add_cog(HelpCommands(bot))
    logger.info("HelpCommands cog loaded")

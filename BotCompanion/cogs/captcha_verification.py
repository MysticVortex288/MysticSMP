import discord
import json
import logging
import asyncio
import random
import string
import io
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from discord import app_commands
from typing import Dict, Optional, Union, Tuple
import os

logger = logging.getLogger('discord_bot')

# Konstanten für das Captcha
CAPTCHA_LENGTH = 6  # Länge des Captcha-Codes
CAPTCHA_EXPIRY = 300  # Ablaufzeit in Sekunden (5 Minuten)
MAX_ATTEMPTS = 3  # Maximale Anzahl an Versuchen

# Farbpalette für Captchas
COLORS = [
    (255, 0, 0),    # Rot
    (0, 0, 255),    # Blau
    (0, 128, 0),    # Grün
    (128, 0, 128),  # Lila
    (255, 165, 0),  # Orange
    (0, 128, 128),  # Türkis
]

class CaptchaVerification(commands.Cog):
    """Cog für die Captcha-Verifizierung neuer Mitglieder."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_captchas = {}  # guild_id -> {user_id -> {"code": str, "attempts": int, "expiry": float}}
        self.settings = {}  # guild_id -> {"enabled": bool, "role_id": int}
        self._load_settings()
        logger.info("CaptchaVerification cog initialized")

    def _load_settings(self):
        """Lädt die Einstellungen aus der Datei."""
        try:
            with open('captcha_settings.json', 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
            self._save_settings()

    def _save_settings(self):
        """Speichert die Einstellungen in der Datei."""
        with open('captcha_settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)

    def _generate_captcha_code(self) -> str:
        """Generiert einen zufälligen Captcha-Code."""
        # Verwende Großbuchstaben und Zahlen, aber keine leicht zu verwechselnden Zeichen (0, O, 1, I)
        chars = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
        return ''.join(random.choice(chars) for _ in range(CAPTCHA_LENGTH))

    def _create_captcha_image(self, code: str) -> discord.File:
        """Erstellt ein Captcha-Bild mit dem angegebenen Code."""
        # Erstelle ein neues Bild
        width, height = 280, 100
        image = Image.new('RGB', (width, height), color=(30, 30, 30))
        draw = ImageDraw.Draw(image)

        # Versuche, eine Schriftart zu laden, oder verwende die Standardschriftart
        try:
            # Versuche mehrere Schriftarten, je nach Verfügbarkeit
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf',     # macOS
                'C:\\Windows\\Fonts\\arialbd.ttf',                        # Windows
            ]
            
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, 50)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Zeichne den Code
        for i, char in enumerate(code):
            # Wähle eine zufällige Farbe und Position
            color = random.choice(COLORS)
            pos = (35 * i + 20 + random.randint(-5, 5), 25 + random.randint(-10, 10))
            
            # Zeichne den Buchstaben/die Zahl
            draw.text(pos, char, font=font, fill=color)

        # Füge Störlinien hinzu
        for _ in range(8):
            start = (random.randint(0, width), random.randint(0, height))
            end = (random.randint(0, width), random.randint(0, height))
            color = random.choice(COLORS)
            draw.line([start, end], fill=color, width=2)

        # Füge Rauschen (Punkte) hinzu
        for _ in range(400):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            color = random.choice(COLORS)
            draw.point((x, y), fill=color)

        # Konvertiere das Bild in einen Discord-File
        image_binary = io.BytesIO()
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        
        return discord.File(image_binary, filename='captcha.png')

    async def send_captcha(self, member: discord.Member) -> None:
        """Sendet ein Captcha an ein Mitglied."""
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        # Generiere einen neuen Captcha-Code
        code = self._generate_captcha_code()
        
        # Erstelle ein Captcha-Bild
        captcha_file = self._create_captcha_image(code)
        
        # Setze die Ablaufzeit
        expiry = asyncio.get_event_loop().time() + CAPTCHA_EXPIRY
        
        # Speichere das Captcha
        if guild_id not in self.active_captchas:
            self.active_captchas[guild_id] = {}
        
        self.active_captchas[guild_id][user_id] = {
            "code": code,
            "attempts": 0,
            "expiry": expiry
        }
        
        # Erstelle eine Embed-Nachricht
        embed = discord.Embed(
            title="Willkommen bei " + member.guild.name + "!",
            description=(
                "Um Zugang zum Server zu erhalten, löse bitte das Captcha unten. "
                "Gib die Zeichen genauso ein, wie sie im Bild angezeigt werden.\n\n"
                f"Du hast {MAX_ATTEMPTS} Versuche und {CAPTCHA_EXPIRY // 60} Minuten Zeit."
            ),
            color=discord.Color.blue()
        )
        
        embed.set_image(url="attachment://captcha.png")
        embed.set_footer(text="Antworte auf diese Nachricht mit dem Captcha-Code.")
        
        try:
            # Sende das Captcha per DM
            captcha_message = await member.send(file=captcha_file, embed=embed)
            
            # Starte einen Timer für die Ablaufzeit
            self.bot.loop.create_task(self._handle_captcha_expiry(member, expiry))
            
            logger.info(f"Captcha an {member.name} (ID: {member.id}) auf Server {member.guild.name} gesendet.")
        except discord.Forbidden:
            logger.warning(f"Konnte keine DM an {member.name} (ID: {member.id}) senden. DMs sind gesperrt.")
            
            # Versuche, im System-Kanal zu benachrichtigen
            system_channel = member.guild.system_channel
            if system_channel and system_channel.permissions_for(member.guild.me).send_messages:
                await system_channel.send(
                    f"{member.mention}, ich konnte dir keine direkte Nachricht senden. "
                    f"Bitte erlaube private Nachrichten von Servermitgliedern in deinen Discord-Einstellungen und verlasse "
                    f"und betrete den Server erneut, um das Captcha zu erhalten."
                )

    async def _handle_captcha_expiry(self, member: discord.Member, expiry_time: float):
        """Behandelt den Ablauf eines Captchas."""
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        # Warte, bis die Ablaufzeit erreicht ist
        await asyncio.sleep(max(0, expiry_time - asyncio.get_event_loop().time()))
        
        # Überprüfe, ob das Captcha noch aktiv ist
        if (guild_id in self.active_captchas and 
            user_id in self.active_captchas[guild_id]):
            
            # Entferne das Captcha
            self.active_captchas[guild_id].pop(user_id, None)
            
            try:
                # Benachrichtige das Mitglied
                await member.send(
                    "Dein Captcha ist abgelaufen. Bitte verlasse und betrete den Server erneut, "
                    "um ein neues Captcha zu erhalten."
                )
                
                logger.info(f"Captcha für {member.name} (ID: {member.id}) ist abgelaufen.")
            except discord.Forbidden:
                logger.warning(f"Konnte keine DM an {member.name} (ID: {member.id}) senden. DMs sind gesperrt.")

    async def check_captcha(self, member: discord.Member, code: str) -> bool:
        """Überprüft einen Captcha-Code."""
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        # Überprüfe, ob das Captcha noch aktiv ist
        if (guild_id in self.active_captchas and 
            user_id in self.active_captchas[guild_id]):
            
            captcha_data = self.active_captchas[guild_id][user_id]
            
            # Überprüfe, ob das Captcha abgelaufen ist
            if asyncio.get_event_loop().time() > captcha_data["expiry"]:
                # Entferne das Captcha
                self.active_captchas[guild_id].pop(user_id, None)
                
                # Benachrichtige das Mitglied
                await member.send(
                    "Dein Captcha ist abgelaufen. Bitte verlasse und betrete den Server erneut, "
                    "um ein neues Captcha zu erhalten."
                )
                
                logger.info(f"Captcha für {member.name} (ID: {member.id}) ist abgelaufen.")
                return False
            
            # Prüfe den Code
            if code.upper() == captcha_data["code"]:
                # Entferne das Captcha
                self.active_captchas[guild_id].pop(user_id, None)
                
                # Verifiziere das Mitglied
                success = await self._verify_member(member)
                
                # Benachrichtige das Mitglied
                if success:
                    await member.send(
                        "Captcha korrekt! Du hast nun Zugang zum Server."
                    )
                else:
                    await member.send(
                        "Captcha korrekt! Leider konnte ich dir keine Rolle zuweisen. Ein Administrator wurde informiert und wird dies manuell erledigen."
                    )
                    
                    # Sende eine Nachricht im System-Kanal
                    system_channel = member.guild.system_channel
                    if system_channel and system_channel.permissions_for(member.guild.me).send_messages:
                        await system_channel.send(
                            f"⚠️ **Achtung:** {member.mention} hat das Captcha erfolgreich gelöst, aber ich konnte "
                            f"die Rolle nicht zuweisen. Bitte überprüfe meine Berechtigungen und weise die Rolle manuell zu."
                        )
                
                logger.info(f"{member.name} (ID: {member.id}) hat das Captcha erfolgreich gelöst.")
                return True
            else:
                # Erhöhe die Anzahl der Versuche
                captcha_data["attempts"] += 1
                
                # Prüfe, ob die maximale Anzahl an Versuchen erreicht wurde
                if captcha_data["attempts"] >= MAX_ATTEMPTS:
                    # Entferne das Captcha
                    self.active_captchas[guild_id].pop(user_id, None)
                    
                    # Benachrichtige das Mitglied
                    await member.send(
                        "Du hast die maximale Anzahl an Versuchen erreicht. Bitte verlasse und betrete den Server erneut, "
                        "um ein neues Captcha zu erhalten."
                    )
                    
                    logger.info(f"{member.name} (ID: {member.id}) hat die maximale Anzahl an Versuchen erreicht.")
                else:
                    # Benachrichtige das Mitglied
                    await member.send(
                        f"Falscher Code. Du hast noch {MAX_ATTEMPTS - captcha_data['attempts']} Versuche."
                    )
                    
                    logger.info(f"{member.name} (ID: {member.id}) hat einen falschen Code eingegeben.")
                
                return False
        else:
            # Kein aktives Captcha
            await member.send(
                "Es gibt kein aktives Captcha für dich. Bitte verlasse und betrete den Server erneut, "
                "um ein neues Captcha zu erhalten."
            )
            
            logger.info(f"Kein aktives Captcha für {member.name} (ID: {member.id})")
            return False

    async def _verify_member(self, member: discord.Member) -> bool:
        """
        Gibt einem Mitglied die Member-Rolle.
        
        Returns:
            bool: True, wenn die Rolle erfolgreich vergeben wurde, False sonst.
        """
        guild_id = str(member.guild.id)
        
        # Überprüfe, ob die Verifizierung für diesen Server aktiviert ist
        if guild_id not in self.settings or not self.settings[guild_id].get("enabled", False):
            logger.warning(f"Verifizierung ist für Server {member.guild.name} nicht aktiviert.")
            return False
        
        # Überprüfe Bot-Berechtigungen
        if not member.guild.me.guild_permissions.manage_roles:
            logger.error(f"Der Bot hat nicht die 'Rollen verwalten' Berechtigung auf Server {member.guild.name}.")
            system_channel = member.guild.system_channel
            if system_channel and system_channel.permissions_for(member.guild.me).send_messages:
                await system_channel.send(
                    f"⚠️ **Achtung:** Ich konnte {member.mention} keine Rolle zuweisen, da mir die Berechtigung "
                    f"'Rollen verwalten' fehlt. Bitte gib mir diese Berechtigung oder weise die Rolle manuell zu."
                )
            return False
        
        # Hole die Member-Rolle
        role_id = self.settings[guild_id].get("role_id")
        role = None
        
        if role_id:
            role = member.guild.get_role(role_id)
        
        # Wenn keine Rolle gefunden wurde, versuche sie zu erstellen
        if not role:
            # Suche nach einer Rolle namens "Member"
            role = discord.utils.get(member.guild.roles, name="Member")
            
            # Wenn keine Rolle gefunden wurde, erstelle sie
            if not role:
                try:
                    # Erstelle die Rolle
                    role = await member.guild.create_role(
                        name="Member",
                        colour=discord.Colour.green(),
                        reason="Automatisch erstellt für Captcha-Verifizierung"
                    )
                    
                    # Setze die Rollen-ID in den Einstellungen
                    self.settings[guild_id]["role_id"] = role.id
                    self._save_settings()
                    
                    logger.info(f"Member-Rolle für Server {member.guild.name} erstellt.")
                except discord.Forbidden:
                    logger.error(f"Keine Berechtigung, um eine Rolle auf Server {member.guild.name} zu erstellen.")
                    return False
            else:
                # Setze die Rollen-ID in den Einstellungen
                self.settings[guild_id]["role_id"] = role.id
                self._save_settings()
        
        # Überprüfe, ob das Mitglied die Rolle bereits hat
        if role in member.roles:
            logger.info(f"{member.name} (ID: {member.id}) hat bereits die Member-Rolle.")
            return True
        
        # Überprüfe, ob der Bot die Rolle vergeben kann (Bot-Rolle muss höher sein als die zu vergebende Rolle)
        if member.guild.me.top_role <= role:
            logger.error(f"Die Bot-Rolle ist nicht höher als die Rolle '{role.name}' auf Server {member.guild.name}.")
            system_channel = member.guild.system_channel
            if system_channel and system_channel.permissions_for(member.guild.me).send_messages:
                await system_channel.send(
                    f"⚠️ **Achtung:** Ich konnte {member.mention} die Rolle '{role.name}' nicht zuweisen, da meine "
                    f"höchste Rolle nicht höher ist als diese Rolle. Bitte verschiebe meine Rolle in der Rollenliste "
                    f"nach oben oder weise die Rolle manuell zu."
                )
            return False
        
        # Gib dem Mitglied die Rolle
        try:
            await member.add_roles(role, reason="Captcha bestanden")
            logger.info(f"{member.name} (ID: {member.id}) hat die Member-Rolle erhalten.")
            return True
        except discord.Forbidden:
            logger.error(f"Keine Berechtigung, um {member.name} (ID: {member.id}) eine Rolle zu geben.")
            return False

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event wird aufgerufen, wenn ein Mitglied einem Server beitritt."""
        guild_id = str(member.guild.id)
        
        # Überprüfe, ob die Verifizierung für diesen Server aktiviert ist
        if guild_id in self.settings and self.settings[guild_id].get("enabled", False):
            # Sende ein Captcha
            await self.send_captcha(member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Event wird aufgerufen, wenn eine Nachricht gesendet wird."""
        # Ignoriere Nachrichten von Bots
        if message.author.bot:
            return
        
        # Prüfe, ob die Nachricht eine DM ist
        if not isinstance(message.channel, discord.DMChannel):
            return
        
        # Prüfe, ob die Nachricht eine Antwort auf eine Bot-Nachricht ist (optional)
        if message.reference and message.reference.resolved:
            referenced_message = message.reference.resolved
            if hasattr(referenced_message, 'author') and hasattr(referenced_message.author, 'id') and referenced_message.author.id != self.bot.user.id:
                return
        
        # Durchsuche alle Server, auf denen der Benutzer und der Bot sind
        for guild in self.bot.guilds:
            member = guild.get_member(message.author.id)
            
            if member:
                # Prüfe, ob es ein aktives Captcha für diesen Benutzer gibt
                guild_id = str(guild.id)
                user_id = str(member.id)
                
                if (guild_id in self.active_captchas and 
                    user_id in self.active_captchas[guild_id]):
                    
                    # Prüfe das Captcha
                    await self.check_captcha(member, message.content)
                    
                    # Wir haben ein Captcha gefunden und geprüft, also können wir die Schleife beenden
                    break

    @commands.hybrid_command(name="setupcaptcha", description="Aktiviert oder deaktiviert die Captcha-Verifizierung.", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setup_captcha(self, ctx: commands.Context, enabled: Optional[bool] = None, role: Optional[discord.Role] = None):
        """
        Aktiviert oder deaktiviert die Captcha-Verifizierung für neue Mitglieder.
        
        Args:
            enabled: Ob die Verifizierung aktiviert werden soll (True) oder deaktiviert (False). Wenn nicht angegeben, wird der aktuelle Status angezeigt.
            role: Die Rolle, die nach erfolgreicher Verifizierung vergeben werden soll. Wenn nicht angegeben, wird die "Member"-Rolle verwendet.
        """
        # Stelle sicher, dass ein Guild (Server) vorhanden ist
        if not ctx.guild:
            await ctx.send("Dieser Befehl kann nur auf einem Server verwendet werden.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Wenn keine Parameter angegeben wurden, zeige den aktuellen Status
        if enabled is None:
            if guild_id in self.settings:
                status = "aktiviert" if self.settings[guild_id].get("enabled", False) else "deaktiviert"
                role_id = self.settings[guild_id].get("role_id")
                role_mention = f"<@&{role_id}>" if role_id else "keine"
                
                await ctx.send(f"Die Captcha-Verifizierung ist derzeit **{status}**. Rolle nach Verifizierung: {role_mention}")
            else:
                await ctx.send("Die Captcha-Verifizierung ist derzeit **deaktiviert**.")
            
            return
        
        # Aktualisiere die Einstellungen
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        
        self.settings[guild_id]["enabled"] = enabled
        
        if role:
            self.settings[guild_id]["role_id"] = role.id
        
        # Speichere die Einstellungen
        self._save_settings()
        
        # Sende eine Bestätigung
        status = "aktiviert" if enabled else "deaktiviert"
        role_text = f" mit Rolle {role.mention}" if role and enabled else ""
        
        await ctx.send(f"Die Captcha-Verifizierung wurde **{status}**{role_text}.")

    @commands.hybrid_command(name="testcaptcha", description="Testet das Captcha-System.", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def test_captcha(self, ctx: commands.Context):
        """
        Testet das Captcha-System, indem ein Captcha an den Benutzer gesendet wird.
        """
        await ctx.send("Ich sende dir ein Test-Captcha per DM.")
        
        # Sende ein Captcha, aber nur wenn der Kontext einen Guild hat
        if ctx.guild:
            member = ctx.guild.get_member(ctx.author.id)
            if member:
                await self.send_captcha(member)
            else:
                await ctx.send("Fehler: Konnte dich nicht als Mitglied auf diesem Server finden.")
        else:
            await ctx.send("Dieser Befehl kann nur auf einem Server verwendet werden.")

async def setup(bot: commands.Bot):
    """Fügt den CaptchaVerification-Cog zum Bot hinzu."""
    await bot.add_cog(CaptchaVerification(bot))
    logger.info("CaptchaVerification cog loaded")
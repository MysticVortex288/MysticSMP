import discord
import io
import aiohttp
import logging
import re
from discord.ext import commands
from typing import Optional, List

logger = logging.getLogger('discord_bot')


class EmojiStealer(commands.Cog):
    """Cog zum Kopieren von Emojis von anderen Servern"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        logger.info("EmojiStealer cog initialized")

    def cog_unload(self):
        """Wird aufgerufen, wenn die Cog entladen wird."""
        self.bot.loop.create_task(self.session.close())

    @commands.hybrid_command(
        name="steal", description="Kopiert ein Emoji von einer Nachricht.")
    @commands.has_permissions(manage_emojis=True)
    async def steal_emoji(self,
                          ctx: commands.Context,
                          emoji: str,
                          name: Optional[str] = None):
        """
        Kopiert ein Emoji und fügt es zum Server hinzu.
        
        Args:
            emoji: Das zu kopierende Emoji, kann ein Standard-, Custom- oder URL-Emoji sein
            name: Der Name für das neue Emoji. Wenn keiner angegeben ist, wird der ursprüngliche Name verwendet
        """
        # Überprüfe, ob der Bot die nötigen Berechtigungen hat
        if not ctx.guild.me.guild_permissions.manage_emojis:
            await ctx.send(
                "Ich habe nicht die nötigen Berechtigungen, um Emojis zu verwalten. Bitte gib mir die 'Emojis verwalten'-Berechtigung."
            )
            return

        # Custom Emoji-Muster: <:name:id> oder <a:name:id>
        custom_emoji_pattern = r'<(a)?:([a-zA-Z0-9_]+):(\d+)>'
        match = re.match(custom_emoji_pattern, emoji)

        emoji_url = None
        emoji_name = name

        if match:
            # Es ist ein Custom Emoji
            is_animated = bool(match.group(1))
            extracted_name = match.group(2)
            emoji_id = match.group(3)

            if not emoji_name:
                emoji_name = extracted_name

            # Emoji-URL erstellen
            emoji_type = "gif" if is_animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{emoji_type}?quality=lossless"
        elif emoji.startswith(('http://', 'https://')):
            # Es ist eine URL
            emoji_url = emoji

            if not emoji_name:
                # Versuche, den Dateinamen aus der URL zu extrahieren
                filename = emoji_url.split('/')[-1].split('?')[0]
                emoji_name = filename.split('.')[0]

                # Stelle sicher, dass der Name den Discord-Anforderungen entspricht
                emoji_name = re.sub(r'[^a-zA-Z0-9_]', '', emoji_name)
                if not emoji_name:
                    emoji_name = "stolen_emoji"
        else:
            # Wenn es kein Custom Emoji oder URL ist, muss es ein Unicode Emoji sein
            await ctx.send(
                "Bitte gib ein benutzerdefiniertes Discord-Emoji oder eine URL an. Standard-Emojis können nicht gestohlen werden, da sie bereits überall verfügbar sind."
            )
            return

        # Überprüfe, ob der Name gültig ist
        if not emoji_name or len(emoji_name) < 2 or len(emoji_name) > 32:
            await ctx.send(
                "Der Emoji-Name muss zwischen 2 und 32 Zeichen lang sein.")
            return

        # Lade das Emoji herunter
        try:
            async with self.session.get(emoji_url) as response:
                if response.status != 200:
                    await ctx.send(
                        f"Konnte das Emoji nicht herunterladen: {response.status} {response.reason}"
                    )
                    return

                emoji_bytes = await response.read()
        except Exception as e:
            await ctx.send(f"Fehler beim Herunterladen des Emojis: {str(e)}")
            return

        # Erstelle das Emoji
        try:
            new_emoji = await ctx.guild.create_custom_emoji(name=emoji_name,
                                                            image=emoji_bytes)
            await ctx.send(
                f"Emoji {new_emoji} erfolgreich zum Server hinzugefügt!")
        except discord.Forbidden:
            await ctx.send(
                "Ich habe nicht die Berechtigung, Emojis zu erstellen.")
        except discord.HTTPException as e:
            if e.code == 30008:
                await ctx.send(
                    "Der Server hat das maximale Limit an Emojis erreicht.")
            elif e.code == 50035:
                await ctx.send(
                    "Das Bild ist zu groß. Discord-Emojis müssen kleiner als 256 KB sein."
                )
            else:
                await ctx.send(f"Fehler beim Erstellen des Emojis: {e.text}")

    @commands.hybrid_command(
        name="stealall", description="Kopiert alle Emojis aus einer Liste.")
    @commands.has_permissions(manage_emojis=True)
    async def stealall_emojis(self, ctx: commands.Context, *, emojis: str):
        """
        Kopiert mehrere Emojis gleichzeitig und fügt sie zum Server hinzu.
        
        Args:
            emojis: Liste von Emojis, durch Leerzeichen getrennt
        """
        # Überprüfe, ob der Bot die nötigen Berechtigungen hat
        if not ctx.guild.me.guild_permissions.manage_emojis:
            await ctx.send(
                "Ich habe nicht die nötigen Berechtigungen, um Emojis zu verwalten. Bitte gib mir die 'Emojis verwalten'-Berechtigung."
            )
            return

        # Custom Emoji-Muster: <:name:id> oder <a:name:id>
        custom_emoji_pattern = r'<(a)?:([a-zA-Z0-9_]+):(\d+)>'
        matches = re.finditer(custom_emoji_pattern, emojis)

        if not matches:
            await ctx.send(
                "Keine gültigen benutzerdefinierten Emojis gefunden. Bitte stelle sicher, dass du Discord Custom Emojis verwendest."
            )
            return

        status_message = await ctx.send(
            "Beginne mit dem Kopieren der Emojis...")

        success_count = 0
        error_count = 0

        for match in re.finditer(custom_emoji_pattern, emojis):
            is_animated = bool(match.group(1))
            emoji_name = match.group(2)
            emoji_id = match.group(3)

            # Emoji-URL erstellen
            emoji_type = "gif" if is_animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{emoji_type}?quality=lossless"

            # Lade das Emoji herunter
            try:
                async with self.session.get(emoji_url) as response:
                    if response.status != 200:
                        error_count += 1
                        continue

                    emoji_bytes = await response.read()
            except Exception:
                error_count += 1
                continue

            # Erstelle das Emoji
            try:
                await ctx.guild.create_custom_emoji(name=emoji_name,
                                                    image=emoji_bytes)
                success_count += 1

                # Aktualisiere die Statusnachricht alle 5 Emojis
                if success_count % 5 == 0 or success_count + error_count == len(
                        list(re.finditer(custom_emoji_pattern, emojis))):
                    await status_message.edit(
                        content=
                        f"Kopiere Emojis... {success_count} erfolgreich, {error_count} fehlgeschlagen"
                    )
            except discord.Forbidden:
                await ctx.send(
                    "Ich habe nicht die Berechtigung, Emojis zu erstellen.")
                return
            except discord.HTTPException as e:
                if e.code == 30008:
                    await ctx.send(
                        "Der Server hat das maximale Limit an Emojis erreicht."
                    )
                    return
                else:
                    error_count += 1

        # Abschlussnachricht
        if success_count > 0:
            await ctx.send(
                f"Fertig! {success_count} Emojis wurden erfolgreich kopiert, {error_count} sind fehlgeschlagen."
            )
        else:
            await ctx.send("Es konnten keine Emojis kopiert werden.")

    @commands.hybrid_command(
        name="liststolen",
        description="Zeigt eine Liste der zuletzt gestohlenen Emojis.")
    @commands.has_permissions(manage_emojis=True)
    async def list_stolen_emojis(self, ctx: commands.Context, limit: int = 20):
        """
        Zeigt eine Liste der zuletzt erstellten Emojis auf dem Server.
        
        Args:
            limit: Maximale Anzahl der anzuzeigenden Emojis (Standard: 20)
        """
        emojis = sorted(ctx.guild.emojis,
                        key=lambda e: e.created_at,
                        reverse=True)[:limit]

        if not emojis:
            await ctx.send(
                "Dieser Server hat keine benutzerdefinierten Emojis.")
            return

        embed = discord.Embed(
            title="Zuletzt hinzugefügte Emojis",
            description=
            f"Die {len(emojis)} zuletzt hinzugefügten Emojis auf diesem Server:",
            color=discord.Color.blue())

        emoji_chunks = [emojis[i:i + 10] for i in range(0, len(emojis), 10)]

        for i, chunk in enumerate(emoji_chunks):
            emoji_list = []
            for emoji in chunk:
                created_at = emoji.created_at.strftime("%d.%m.%Y %H:%M")
                emoji_list.append(
                    f"{emoji} - `:{emoji.name}:` (erstellt am {created_at})")

            embed.add_field(name=f"Emojis {i*10+1}-{i*10+len(chunk)}",
                            value="\n".join(emoji_list),
                            inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="searchemojiurl",
        description="Gibt die URL eines benutzerdefinierten Emojis zurück.")
    async def search_emoji_url(self, ctx: commands.Context, emoji: str):
        """
        Gibt die URL eines benutzerdefinierten Emojis zurück.
        
        Args:
            emoji: Das Emoji, dessen URL zurückgegeben werden soll
        """
        # Custom Emoji-Muster: <:name:id> oder <a:name:id>
        custom_emoji_pattern = r'<(a)?:([a-zA-Z0-9_]+):(\d+)>'
        match = re.match(custom_emoji_pattern, emoji)

        if not match:
            await ctx.send(
                "Bitte gib ein benutzerdefiniertes Discord-Emoji an. Standard-Emojis haben keine URL."
            )
            return

        is_animated = bool(match.group(1))
        emoji_name = match.group(2)
        emoji_id = match.group(3)

        # Emoji-URL erstellen
        emoji_type = "gif" if is_animated else "png"
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{emoji_type}?quality=lossless"

        embed = discord.Embed(
            title=f"Emoji: {emoji_name}",
            description=f"Hier ist die URL für das Emoji {emoji}:",
            color=discord.Color.blue())
        embed.add_field(name="URL", value=emoji_url, inline=False)
        embed.set_image(url=emoji_url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Fügt den EmojiStealer-Cog zum Bot hinzu."""
    await bot.add_cog(EmojiStealer(bot))
    logger.info("EmojiStealer cog loaded")

import discord
from discord.ext import commands
from discord import app_commands
import os

# Intents einstellen (benötigt, um Nachrichteninhalte zu lesen)
intents = discord.Intents.default()
intents.message_content = True

# Bot erstellen mit dem Prefix "!" und Unterstützung für Slash-Commands
bot = commands.Bot(command_prefix="!", intents=intents, application_id="1355262227929891027")

# Event: Wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"✅ Bot ist online! Eingeloggt als {bot.user}")

    # Slash-Commands in allen Servern registrieren (synchronisieren)
    try:
        print("Synchronisiere Slash-Commands...")
        await bot.tree.sync()  # Sync von Slash-Commands mit Discord
        print("Slash-Commands erfolgreich synchronisiert!")
    except Exception as e:
        print(f"Fehler beim Synchronisieren der Slash-Commands: {e}")

# Prefixed Command (z.B. !ping)
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Slash-Command (z.B. /ping)
@bot.tree.command(name="ping", description="Antwortet mit Pong!")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# Weitere Beispiele für Prefixed- und Slash-Commands:

# Prefixed Command (z.B. !hello)
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hallo {ctx.author.mention}! Ich bin ein Bot!")

# Slash-Command (z.B. /hello)
@bot.tree.command(name="hello", description="Begrüßt den Benutzer!")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hallo {interaction.user.mention}! Ich bin ein Bot!")

# Hier holen wir den Token aus den Umgebungsvariablen
TOKEN = os.environ.get("DISCORD_TOKEN")

# Sicherstellen, dass der Token vorhanden ist
if TOKEN is None:
    raise ValueError("Kein Token gefunden! Stelle sicher, dass die Umgebungsvariable 'DISCORD_TOKEN' gesetzt ist.")

# Bot starten
bot.run(TOKEN)

import discord
from discord.ext import commands
import os

# Intents einstellen (benötigt, um Nachrichteninhalte zu lesen)
intents = discord.Intents.default()
intents.members = True
intents.invites = True
bot = commands.Bot(command_prefix="!", intents=intents)



# Bot erstellen mit dem Prefix "!" (nur Prefixed-Commands)
bot = commands.Bot(command_prefix="!", intents=intents)
# Cog laden
async def load_cogs():
    await bot.load_extension("invite-tracker")  # Ohne .py am Ende!

# Event: Wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"✅ Bot ist online! Eingeloggt als {bot.user}")

# Prefixed Command (z.B. !ping)
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Weitere Beispielbefehle:
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hallo {ctx.author.mention}! Ich bin ein Bot!")

# Hier holen wir den Token aus den Umgebungsvariablen
TOKEN = os.environ.get("DISCORD_TOKEN")

# Sicherstellen, dass der Token vorhanden ist
if TOKEN is None:
    raise ValueError("Kein Token gefunden! Stelle sicher, dass die Umgebungsvariable 'DISCORD_TOKEN' gesetzt ist.")

# Bot starten
bot.run(TOKEN)

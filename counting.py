import discord
from discord.ext import commands
from collections import deque

# Spiel-Daten
counting_channel_id = None  # Der Kanal, in dem das Zählen stattfindet
current_number = 0  # Die aktuelle Zahl im Spiel
players_queue = deque()  # Spieler-Warteschlange (abwechselnd zählen)
game_started = False  # Status, ob das Spiel gestartet wurde

# Cog erstellen
class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def countingsetup(self, ctx, channel: discord.TextChannel):
        """Admin-Befehl, um den Kanal für das Zahlenspiel festzulegen."""
        global counting_channel_id
        counting_channel_id = channel.id  # Speichern der Kanal-ID
        await ctx.send(f"✅ Der Zahlenspiel-Kanal wurde auf {channel.mention} gesetzt!")

    @commands.Cog.listener()
    async def on_message(self, message):
        global current_number, players_queue, game_started

        if message.author.bot:
            return

        # Wenn der Kanal für das Spiel nicht gesetzt ist oder das Spiel nicht läuft, ignorieren
        if not counting_channel_id or not game_started:
            return

        # Sicherstellen, dass es der richtige Kanal ist
        if message.channel.id != counting_channel_id:
            return

        # Prüfen, ob die Nachricht die nächste Zahl im Spiel ist
        try:
            number = int(message.content)
        except ValueError:
            return  # Ignorieren, wenn keine Zahl gesendet wurde

        if number == current_number + 1:  # Richtig gezählt
            current_number = number
            players_queue.append(message.author)  # Der Spieler hat die Zahl richtig gezählt

            # Nächsten Spieler in der Warteschlange auswählen
            next_player = players_queue[0] if players_queue else message.author
            await message.channel.send(f"✅ {message.author.mention} hat {current_number} erreicht! Jetzt ist {next_player.mention} dran!")
        else:  # Fehler, das Spiel beginnt von vorne
            await message.channel.send(f"❌ {message.author.mention}, du hast einen Fehler gemacht! Das Spiel beginnt wieder bei 1.")
            current_number = 0
            players_queue.clear()  # Warteschlange zurücksetzen
            players_queue.append(message.author)  # Der Spieler beginnt jetzt das Spiel

    @commands.command()
    async def startcounting(self, ctx):
        """Startet das Zahlenspiel."""
        global game_started, current_number, players_queue
        if game_started:
            await ctx.send("❌ Das Zahlenspiel läuft bereits!")
        else:
            game_started = True
            current_number = 0
            players_queue.clear()
            await ctx.send("✅ Das Zahlenspiel wurde gestartet! Beginne mit dem Zählen.")
            players_queue.append(ctx.author)  # Der erste Spieler ist der, der den Befehl gibt

    @commands.command()
    async def stopcounting(self, ctx):
        """Stoppt das Zahlenspiel."""
        global game_started, current_number, players_queue
        if not game_started:
            await ctx.send("❌ Das Zahlenspiel ist noch nicht gestartet!")
        else:
            game_started = False
            current_number = 0
            players_queue.clear()
            await ctx.send("✅ Das Zahlenspiel wurde gestoppt!")

# Cog laden
async def setup(bot):
    await bot.add_cog(CountingCog(bot))  # Cog hinzufügen

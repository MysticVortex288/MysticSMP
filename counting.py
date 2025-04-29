
import discord
from discord.ext import commands

class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counting_channel_id = None
        self.last_number = 0
        self.last_user_id = None

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def countingsetup(self, ctx, channel: discord.TextChannel):
        """Admin-Befehl zum Einrichten des Zählkanals"""
        self.counting_channel_id = channel.id
        self.last_number = 0
        await ctx.send(f"✅ Zählkanal wurde auf {channel.mention} gesetzt!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.counting_channel_id:
            return

        if message.channel.id != self.counting_channel_id:
            return

        try:
            number = int(message.content)
            
            # Prüfen ob es die richtige Zahl ist
            if number == self.last_number + 1:
                # Prüfen ob der gleiche User zweimal zählt
                if message.author.id == self.last_user_id:
                    await message.add_reaction('❌')
                    await message.reply("❌ Du kannst nicht zweimal hintereinander zählen!")
                    return

                await message.add_reaction('✅')
                self.last_number = number
                self.last_user_id = message.author.id
            else:
                await message.add_reaction('❌')
                await message.reply(f"❌ Falsche Zahl! Die nächste Zahl hätte {self.last_number + 1} sein müssen.")
                self.last_number = 0
                self.last_user_id = None

        except ValueError:
            await message.add_reaction('❌')
            await message.reply("❌ Bitte gib nur Zahlen ein!")

async def setup(bot):
    await bot.add_cog(CountingCog(bot))

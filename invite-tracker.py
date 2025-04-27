import discord
from discord.ext import commands

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Einladungen abrufen
        invites = await member.guild.invites()

        # Überprüfen, wer die Einladung gemacht hat
        for invite in invites:
            if invite.uses > invite.max_uses:
                print(f"{member.name} wurde von {invite.inviter} eingeladen.")
                break
        else:
            print(f"{member.name} wurde nicht von jemandem eingeladen.")

    # Leaderboard für Einladungen
    @commands.command()
    async def leaderboard(self, ctx):
        invites = await ctx.guild.invites()
        invites = sorted(invites, key=lambda invite: invite.uses, reverse=True)  # Sorting by most uses
        leaderboard_message = ""

        for i, invite in enumerate(invites):
            leaderboard_message += f"{i+1}. {invite.inviter} - {invite.uses} Einladungen\n"

        await ctx.send(leaderboard_message)

# Cog laden
def setup(bot):
    bot.add_cog(InviteTracker(bot))

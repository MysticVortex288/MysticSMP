import discord
from discord.ext import commands

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # View bleibt aktiv

    @discord.ui.button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Member")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Du bist jetzt verifiziert und hast die Rolle 'Member'!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Die Rolle 'Member' wurde nicht gefunden.", ephemeral=True)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(VerifyButton())  # Button-View registrieren

    @commands.command(name="verify")
    @commands.has_permissions(administrator=True)  # Nur Admins dürfen den Befehl benutzen
    async def send_verify_message(self, ctx):
        embed = discord.Embed(
            title="Willkommen auf dem Server! 🎉",
            description="Klicke auf **✅ Verifizieren**, um Zugang zu erhalten!",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed, view=VerifyButton())

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

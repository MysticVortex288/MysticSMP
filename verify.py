import discord
from discord.ext import commands

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def verify(self, ctx):
        """Admin-Befehl, um die Verifizierungsnachricht zu senden."""
        embed = discord.Embed(
            title="🎉 Willkommen auf dem Server!",
            description="👉 Bitte klicke auf den Button unten, um dich zu verifizieren!",
            color=discord.Color.blue()
        )

        view = VerificationView()
        await ctx.send(embed=embed, view=view)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Kein Timeout

        self.add_item(discord.ui.Button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button"))

    @discord.ui.button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Member")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Du bist jetzt verifiziert!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Die Rolle 'Member' wurde nicht gefunden.", ephemeral=True)

# Cog laden
async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

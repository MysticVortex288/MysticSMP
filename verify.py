import discord
from discord.ext import commands

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # View bleibt für immer aktiv

    @discord.ui.button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Member")  # Rolle "Member" holen
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Du hast die Rolle **Member** erhalten!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Die Rolle **Member** wurde nicht gefunden.", ephemeral=True)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerificationView())  # GANZ wichtig: View registrieren

    @commands.command()
    @commands.has_permissions(administrator=True)  # Nur Admins dürfen den Command benutzen
    async def verify(self, ctx):
        """Sende die Verifizierungs-Nachricht."""
        embed = discord.Embed(
            title="🎉 Willkommen!",
            description="Bitte klicke auf den Button unten, um dich zu verifizieren!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, view=VerificationView())

# Cog Setup
async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

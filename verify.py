
import discord
from discord.ext import commands

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_role = discord.utils.get(interaction.guild.roles, name="Member")
        if not member_role:
            # Erstelle die Rolle, wenn sie nicht existiert
            try:
                member_role = await interaction.guild.create_role(name="Member", color=discord.Color.blue())
            except discord.Forbidden:
                await interaction.response.send_message("❌ Ich habe keine Berechtigung, Rollen zu erstellen!", ephemeral=True)
                return

        try:
            await interaction.user.add_roles(member_role)
            await interaction.response.send_message("✅ Du hast die Rolle **Member** erhalten!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Ich habe keine Berechtigung, die Rolle zu vergeben!", ephemeral=True)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerificationView())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def verify(self, ctx):
        """Sende die Verifizierungs-Nachricht."""
        try:

        embed = discord.Embed(
            title="🎉 Willkommen!",
            description="Bitte klicke auf den Button unten, um dich zu verifizieren!",
            color=discord.Color.green()
        )
            await ctx.send(embed=embed, view=VerificationView())
        except discord.Forbidden:
            await ctx.send("❌ Ich habe keine ausreichenden Berechtigungen!", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Ein Fehler ist aufgetreten: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

import discord
from discord.ext import commands

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # WICHTIG: timeout=None = Persistent View

    @discord.ui.button(label="✅ Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Member")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Du bist jetzt verifiziert!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Die Rolle 'Member' wurde nicht gefunden.", ephemeral=True)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(VerifyButton())  # WICHTIG: View einmal registrieren beim Start

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"{member} ist dem Server beigetreten!")  # Debug

        embed = discord.Embed(
            title="Willkommen auf dem Server! 🎉",
            description="Bitte klicke auf den ✅ Button, um dich zu verifizieren.",
            color=discord.Color.blue()
        )

        view = VerifyButton()

        try:
            await member.send(embed=embed, view=view)
            print("✅ DM erfolgreich gesendet!")
        except discord.Forbidden:
            print("⚠️ Konnte DM nicht senden.")
            channel = discord.utils.get(member.guild.text_channels, name="allgemein")
            if channel:
                await channel.send(f"{member.mention}, bitte aktiviere deine DMs, um dich verifizieren zu können!")

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

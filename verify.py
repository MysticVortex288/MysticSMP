import discord
from discord.ext import commands

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Kein Timeout

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            embed = discord.Embed(
                title="Willkommen auf dem Server!",
                description="Bitte klicke auf den **Button** unten, um dich zu verifizieren!",
                color=discord.Color.blue()
            )

            view = VerifyButton()  # Unsere eigene View benutzen
            await member.send(embed=embed, view=view)

        except discord.Forbidden:
            general_channel = discord.utils.get(member.guild.text_channels, name='allgemein')
            if general_channel:
                await general_channel.send(f"{member.mention}, bitte aktiviere deine DMs, um dich zu verifizieren!")

# Cog laden
async def setup(bot):
    await bot.add_cog(VerificationCog(bot))

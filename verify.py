import discord
from discord.ext import commands

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Überprüfen, ob der Bot dem Mitglied eine DM senden kann
        try:
            embed = discord.Embed(
                title="Willkommen auf dem Server!",
                description="Bitte klicke auf den Knopf, um zu verifizieren.",
                color=discord.Color.blue()
            )

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify"))

            # Sende die Nachricht an den Benutzer
            await member.send(embed=embed, view=view)

        except discord.Forbidden:
            # Falls der Bot keine DM senden kann, eine Nachricht im allgemeinen Kanal
            general_channel = discord.utils.get(member.guild.text_channels, name='allgemein')
            if general_channel:
                await general_channel.send(f"{member.mention}, bitte aktiviere deine DMs für diesen Server, um die Verifizierung abzuschließen.")

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.custom_id == "verify":  # Wenn der "Verify"-Button geklickt wird
            role = discord.utils.get(interaction.guild.roles, name="Member")  # Rolle "Member" suchen
            if role:
                await interaction.user.add_roles(role)  # Rolle zuweisen
                await interaction.response.send_message("Du bist nun verifiziert!", ephemeral=True)  # Bestätigung
            else:
                await interaction.response.send_message("Die Rolle 'Member' konnte nicht gefunden werden.", ephemeral=True)

# Cog laden
async def setup(bot):
    await bot.add_cog(VerificationCog(bot))  # Cog hinzufügen

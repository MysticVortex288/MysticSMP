  import discord
  from discord.ext import commands

  class VerificationCog(commands.Cog):
      def __init__(self, bot):
          self.bot = bot

      @commands.Cog.listener()
      async def on_member_join(self, member):
          # Nachricht und Button
          embed = discord.Embed(
              title="Willkommen auf dem Server!",
              description="Bitte klicke auf den Knopf, um zu verifizieren.",
              color=discord.Color.blue()
          )

          view = discord.ui.View()
          view.add_item(discord.ui.Button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify"))

          # Nachricht an den Benutzer senden
          await member.send(embed=embed, view=view)

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


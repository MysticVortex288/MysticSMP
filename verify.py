
import discord
from discord.ext import commands

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify-button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_role = discord.utils.get(interaction.guild.roles, name="Member")
        
        if not member_role:
            try:
                member_role = await interaction.guild.create_role(name="Member")
            except:
                await interaction.response.send_message("❌ Konnte die Member-Rolle nicht erstellen!", ephemeral=True)
                return
                
        try:
            await interaction.user.add_roles(member_role)
            await interaction.response.send_message("✅ Du wurdest erfolgreich verifiziert!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Konnte dir die Rolle nicht geben!", ephemeral=True)

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerifyButton())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def verify(self, ctx):
        embed = discord.Embed(
            title="Verifizierung",
            description="Klicke auf den Button unten um dich zu verifizieren!",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed, view=VerifyButton())

async def setup(bot):
    await bot.add_cog(Verify(bot))

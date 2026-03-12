import nextcord
from nextcord import Interaction
from nextcord.ext import commands

class Server(commands.Cog):
    """
    Global error handler for slash commands.
    Sends a friendly message to users when something goes wrong.
    """
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_slash_command_error(self, interaction: Interaction, error: Exception):
        if interaction.response.is_done(): # Avoid double responses if the command already sent one
            try:
                await interaction.followup.send("An unexpected error occurred!", ephemeral=False,)
            except Exception:
                pass
        else:
            try:
                await interaction.response.send_message("An unexpected error occurred!", ephemeral=False,)
            except Exception:
                pass

        raise error # Re-raise to preserve traceback for logs/debugging

def setup(client: commands.Bot):
    client.add_cog(Server(client))
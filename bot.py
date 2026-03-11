import json, nextcord, os
from dotenv import load_dotenv
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from pathlib import Path

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
COG_DIR = os.getenv('COG_DIR')
COG_CODE = os.getenv('COG_CODE')
OWNER_ID = int(os.getenv('OWNER_ID'))

intents = nextcord.Intents.default()
# intents.members = True              # Enable if using on_member_join / on_member_remove
# intents.message_content = True      # Enable if using on_message or prefix commands
# intents.presences = False           # Optional, disable if not used

client = commands.Bot(description="Community Starter Discord Bot", owner_id=OWNER_ID, case_insensitive=True, intents=intents)
client.remove_command('help')
client.webup = '0'

def discover_cog_files() -> dict[str, str]:
    """
    Returns a mapping of:
        cog_name -> package_name
    Example:
        {"start": "cogs", "twitch": "cogs_optional"}
    """
    discovered: dict[str, str] = {}

    for folder in ("cogs", "cogs_optional"):
        base = Path(folder)
        if not base.exists():
            continue

        for file in sorted(base.glob("*.py")):
            if file.name.startswith("_"):
                continue
            discovered[file.stem.lower()] = folder

    return discovered

def get_load_choices() -> dict[str, str]:
    """
    Build slash choices for all available cog files.
    Label shows folder for clarity.
    """
    discovered = discover_cog_files()
    return {
        f"{name} ({folder})": name
        for name, folder in discovered.items()
    }

def get_loaded_choices() -> dict[str, str]:
    """
    Build slash choices from currently loaded extensions.
    """
    loaded: dict[str, str] = {}

    for extension in sorted(client.extensions.keys()):
        cog_name = extension.split(".")[-1]
        loaded[cog_name] = cog_name

    return loaded

def find_loaded_extension(cog_name: str) -> str | None:
    """
    Find the fully qualified loaded extension name for a cog.
    Example:
        "twitch" -> "cogs_optional.twitch"
    """
    cog_name = cog_name.lower()

    for extension in client.extensions.keys():
        if extension.split(".")[-1].lower() == cog_name:
            return extension

    return None

@client.slash_command(name="load", description="Loads a cog")
async def load(interaction: Interaction, cog: str = SlashOption(name="cog", description="Choose the cog.", required=True, choices=get_load_choices()), passwd: str = SlashOption(name="passwd", description="Enter the passwd.", required=True,),):
    await interaction.response.defer(ephemeral=True)
    if passwd != COG_CODE:
        await interaction.followup.send("Denied!", ephemeral=True)
        return

    cog_name = cog.lower()
    discovered = discover_cog_files()
    package = discovered.get(cog_name)

    if not package:
        await interaction.followup.send(f"Cog `{cog_name}` not found.", ephemeral=True)
        return

    extension_name = f"{package}.{cog_name}"

    if extension_name in client.extensions:
        await interaction.followup.send(f"`{cog_name}` is already loaded.", ephemeral=True)
        return

    try:
        client.load_extension(extension_name)
        await interaction.followup.send(f"Loaded `{cog_name}` from `{package}`.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to load `{cog_name}`: `{e}`", ephemeral=True)

@client.slash_command(name='reload', description='Reloads a COG')
async def reload(interaction: Interaction, cog: str = SlashOption(name='cog', description='Choose the cog.', required=True, choices=get_loaded_choices()), passwd: str = SlashOption(name='passwd', description='Enter the passwd.', required=True)):
    await interaction.response.defer(ephemeral=True)
    if passwd != COG_CODE:
        await interaction.followup.send("Denied!", ephemeral=True)
        return

    cog_name = cog.lower()
    loaded_extension = find_loaded_extension(cog_name)

    if not loaded_extension:
        await interaction.followup.send(f"Cog `{cog_name}` is not currently loaded.", ephemeral=True)
        return

    try:
        client.reload_extension(loaded_extension)
        await interaction.followup.send(f"Reloaded `{cog_name}`.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to reload `{cog_name}`: `{e}`", ephemeral=True)

@client.slash_command(name='unload', description='Unloads a COG') 
async def unload(interaction: Interaction, cog: str = SlashOption(name='cog', description='Choose the cog.', required=True, choices=get_loaded_choices()), passwd: str = SlashOption(name='passwd', description='Enter the passwd.', required=True)):
    await interaction.response.defer(ephemeral=True)
    if passwd != COG_CODE:
        await interaction.followup.send("Denied!", ephemeral=True)
        return

    cog_name = cog.lower()
    loaded_extension = find_loaded_extension(cog_name)

    if not loaded_extension:
        await interaction.followup.send(f"Cog `{cog_name}` is not currently loaded.", ephemeral=True)
        return

    try:
        client.unload_extension(loaded_extension)
        await interaction.followup.send(f"Unloaded `{cog_name}`.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to unload `{cog_name}`: `{e}`", ephemeral=True)

# Load only core cogs from the main cogs folder on startup
for filename in os.listdir(COG_DIR):
    if filename.endswith(".py") and not filename.startswith("_"):
        client.load_extension(f"cogs.{filename[:-3]}")

client.run(BOT_TOKEN)
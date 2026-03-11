import json, nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from pathlib import Path
from typing import Dict

USER_RESPONSES_FILE = Path("data/user_responses.json")

class User(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

        # Responses file load
        self.responses_path = Path(USER_RESPONSES_FILE)
        self.responses_path.parent.mkdir(parents=True, exist_ok=True)

        self.responses_data: Dict = self.load_responses_file()
        self.user_responses: Dict[str, str] = self.responses_data.get("user_responses", {})

    # Commands
    @nextcord.slash_command(name="seeresponse", description="See your current custom response")
    async def see_response(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        user_id = str(interaction.user.id)
        response = self.user_responses.get(user_id, "You havent set a custom response yet!")
        await interaction.followup.send(f"{interaction.user.mention}, your response is: {response}", ephemeral=False)

    @nextcord.slash_command(name="setresponse", description="Set your custom response")
    async def set_response(self, interaction: Interaction, response: str = SlashOption(description="Your custom response", required=False)):
        await interaction.response.defer(ephemeral=False)
        user_id = str(interaction.user.id)
        self.user_responses[user_id] = response
        self.save_responses_file()
        await interaction.followup.send(f"Custom response set for {interaction.user.mention}, your response is: {response}", ephemeral=False)

    @nextcord.slash_command(name="wiperesponse", description="Wipe your custom response")
    async def wipe_response(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)
        user_id = str(interaction.user.id)
        if user_id in self.user_responses:
            del self.user_responses[user_id]
            self.save_responses_file()
            await interaction.followup.send(f"Custom response wiped for {interaction.user.mention}", ephemeral=False)
        else:
            await interaction.followup.send(f"{interaction.user.mention}, you don't have a custom response set.", ephemeral=False)

    # Listeners & Functions/Helpers
    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        # Requires Intents.message_content = True
        if message.author.bot:
            return

        # Disables Self User Pinging
        if f"<@{message.author.id}>" in message.content or f"<@!{message.author.id}>" in message.content:
            return

        # quick path: if no custom responses, skip
        if not self.user_responses:
            return

        content = message.content
        if not content:
            return

        # Mentions can be <@id> or <@!id>
        for user_id, response in self.user_responses.items():
            if f"<@{user_id}>" in content or f"<@!{user_id}>" in content:
                try:
                    await message.channel.send(f"{message.author.mention}, {response}", delete_after=30)
                except Exception as e:
                    print(f"[ERROR-MEMBER] Failed to send mention response: {e}")
                break

    def load_responses_file(self) -> Dict:
        try:
            if self.responses_path.exists():
                with self.responses_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ERROR-USER] Failed to load {self.responses_path}: {e}")
        return {"user_responses": {}}

    def save_responses_file(self) -> None:
        try:
            self.responses_data["user_responses"] = self.user_responses
            with self.responses_path.open("w", encoding="utf-8") as f:
                json.dump(self.responses_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR-USER] Failed to save {self.responses_path}: {e}")

def setup(client: commands.Bot):
    client.add_cog(User(client))
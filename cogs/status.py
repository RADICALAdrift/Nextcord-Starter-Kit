import json, nextcord, random
from nextcord.ext import commands, tasks
from pathlib import Path

STATUS_FILE_PATH = Path("data/bot_status.json")

class Status(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.statuses_data = self.load_statuses_file()
        self.change_status.start()

    def cog_unload(self):
        # ensure the task stops on /reload or /unload
        self.change_status.cancel()

    @tasks.loop(minutes=15)
    async def change_status(self):
        statuses_list = self.statuses_data.get("statuses", [])
        if statuses_list:
            response = random.choice(statuses_list)
            await self.client.change_presence(
                status=nextcord.Status.idle,
                activity=nextcord.CustomActivity(name=response)
            )

    @change_status.before_loop
    async def before_change_status(self):
        await self.client.wait_until_ready()

    def load_statuses_file(self):
        try:
            with open(STATUS_FILE_PATH, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"[ERROR-STATUS] Missing {STATUS_FILE_PATH}; using empty list.")
        except json.JSONDecodeError as e:
            print(f"[ERROR-STATUS] JSON error in {STATUS_FILE_PATH}: {e}")
        except Exception as e:
            print(f"[ERROR-STATUS] Failed to load statuses: {e}")
        return {"statuses": []}

def setup(client):
    client.add_cog(Status(client))
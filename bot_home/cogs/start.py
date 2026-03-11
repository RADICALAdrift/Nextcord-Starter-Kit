import nextcord
from nextcord.ext import commands

class Start(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in as', self.client.user)
        print(f'Guilds: {len(self.client.guilds)} Shards: {getattr(self.client, "shard_count", 1) or 1}')
        print(f'Latency: {self.client.latency*1000:.0f} ms')
        print('------')

def setup(client):
    client.add_cog(Start(client))
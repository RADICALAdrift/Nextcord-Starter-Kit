import nextcord, random, re
from nextcord.ext import commands
from pathlib import Path

class Responder(commands.Cog):
    """
    A simple automatic responder for casual greetings and keywords.
    """
    def __init__(self, client: commands.Bot):
        self.client = client

        # Text responses (case-insensitive)
        self.responses = {
            "hi": "Hi!", "hey": "Hey!", "hello": "Hello!",
            "sup": "Sup, Cool Dude! :sunglasses:",
            "bye": "Bye :wave:",
            "shock": "Zip Zap Motherfucker!",
        }

        # Image responses (keyword -> file path)
        # Adjust path to wherever you store the meme image
        self.image_responses = {
            "horse": ["data/assets/horse.webp", "data/assets/horse_1.webp", "data/assets/horse_2.webp", "data/assets/horse_3.webp"],
            "pickles": ["data/assets/pickles_1.webp", "data/assets/pickles_2.webp", "data/assets/pickles_3.webp", "data/assets/pickles_4.webp", "data/assets/pickles_5.webp"]
        }

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.bot: # Ignore bots
            return

        msg = message.content.lower().strip()
        if not msg:
            return

        msg_clean = re.sub(r"[^\w\s]", "", msg) # Strip punctuation for cleaner matching
        words = msg_clean.split()

        for keyword, images in self.image_responses.items(): # 1) Image keyword match first
            if keyword in words:
                try:
                    chosen_image = random.choice(images)
                    file_path = Path(chosen_image)
                    
                    if file_path.is_file():
                        await message.channel.send(file=nextcord.File(str(file_path)), delete_after=30)
                    else:
                        print(f"[ERROR-RESPONDER] Missing file: {file_path}")
                except Exception as e:
                    print(f"[ERROR-RESPONDER] Error sending image: {e}")
                break
        else:
            for keyword, reply in self.responses.items(): # 2) Text keyword match
                if keyword in words:
                    try:
                        await message.channel.send(reply, delete_after=15)
                    except Exception as e:
                        print(f"[ERROR-RESPONDER] Failed to send message: {e}")
                    break

        await self.client.process_commands(message) # Pass through to other commands

def setup(client: commands.Bot):
    client.add_cog(Responder(client))
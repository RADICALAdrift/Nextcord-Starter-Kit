import asyncio, git, os, shutil, tempfile
from nextcord.ext import commands, tasks
from pathlib import Path

class AutoUpdater(commands.Cog):
    """
    Periodically pulls Nexic-Data and updates local files, then reloads cogs.
    Heavy I/O (git + filesystem) is moved off the event loop via asyncio.to_thread.
    """
    def __init__(self, client: commands.Bot):
        self.client = client

        self.repo_branch = os.getenv("NEXIC_DATA_BRANCH", "main")
        self.repo_url = os.getenv("NEXIC_DATA_REPO", "")
       
        self.repo_target_path = Path("./data") # Destinations
        self.channel_maps_dst = self.repo_target_path / "twitch_cog_files" / "channel_maps" # Changable by the user
        self.status_dst = self.repo_target_path / "bot_status.json"                         # Changable by the user

        self.repo_target_path.mkdir(parents=True, exist_ok=True) # Ensure target root exists

        self.update_repo.start() # Starts the loop

    @tasks.loop(hours=1) # Schedule Logic
    async def update_repo(self):
        try:
            await asyncio.to_thread(self._do_update_once) # do all the heavy lifting in a worker thread

            for ext in ("cogs.status", "cogs.twitch"): # best-effort cog reload; only if currently loaded
                if ext in self.client.extensions:
                    try:
                        self.client.reload_extension(ext)
                        print(f"[DEBUG-UPDATER] reloaded {ext}")
                    except Exception as e:
                        print(f"[DEBUG-UPDATER] reload failed for {ext}: {e}")
                else:
                    print(f"[DEBUG-UPDATER] {ext} not loaded; skipping reload.")
        except Exception as e:
            print(f"[ERROR-UPDATER] Failed to update repo: {e}")

    @update_repo.before_loop
    async def _before_update_repo(self):
        await self.client.wait_until_ready() # wait for bot ready + small jitter so we don't contend with other startup jobs
        await asyncio.sleep(1.0)

    def cog_unload(self):
        self.update_repo.cancel()

    def _do_update_once(self): # core work (runs in thread)
        """
        Clone repo to a temp dir (shallow), copy needed files into place atomically,
        then remove temp. Designed to be idempotent and fast.
        """
        tmp_parent = Path(tempfile.gettempdir())
        tmp_dir = Path(tempfile.mkdtemp(prefix="nexic-data-", dir=tmp_parent))

        try:
            print("[DEBUG-UPDATER] Cloning Nexic-Data repo (shallow)...")
            git.Repo.clone_from(self.repo_url, tmp_dir, branch=self.repo_branch, depth=1, single_branch=True,)

            src_channel_maps = tmp_dir / "data" / "channel_maps" # Paths in the repo
            src_status = tmp_dir / "data" / "bot_status.json"

            if not src_channel_maps.exists(): # Validate expected files exist
                raise FileNotFoundError(f"Missing channel_maps in repo: {src_channel_maps}")
            if not src_status.exists():
                raise FileNotFoundError(f"Missing bot_status.json in repo: {src_status}")

            self.repo_target_path.mkdir(parents=True, exist_ok=True) # Prepare destination root

            if self.channel_maps_dst.exists(): # Replace channel_maps directory
                print("[DEBUG-UPDATER] Clearing existing channel_maps...")
                shutil.rmtree(self.channel_maps_dst, ignore_errors=True)

            print("[DEBUG-UPDATER] Copying channel_maps...")
            shutil.copytree(src_channel_maps, self.channel_maps_dst)

            print("[DEBUG-UPDATER] Updating bot_status.json...") # Replace bot_status.json atomically
            tmp_status = self.status_dst.with_suffix(".json.tmp")
            shutil.copy2(src_status, tmp_status)
            os.replace(tmp_status, self.status_dst) # atomic on same filesystem

            print("[DEBUG-UPDATER] Repo update complete.")

        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True) # clean temp
            except Exception as e:
                print(f"[DEBUG-UPDATER] temp cleanup skipped: {e}")

def setup(client: commands.Bot):
    client.add_cog(AutoUpdater(client))
    print("[DEBUG-UPDATER] AutoUpdater cog setup complete.")
import aiohttp, asyncio, json, os
from datetime import datetime, timedelta
from nextcord.ext import commands, tasks
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ANNOUNCE_EVERY_MIN = 120
ANNOUNCE_GRACE_MIN = 5 # small separation to avoid back-to-back posts
CHECK_INTERVAL_SECONDS = 60

BASE_PATH = Path("data/twitch_cog_files")
CATEGORY_TARGETS_FILE = BASE_PATH / "twitch_category_targets.json"
LIVE_STATUS_FILE = BASE_PATH / "twitch_live_status.json"

AUTOLIVE_CHANNEL_ID = os.getenv("AUTOLIVE_CHANNEL_ID", "")
AUTOLIVE_CHANNEL_ID_VTUBER = os.getenv("AUTOLIVE_CHANNEL_ID_VTUBER", "")
AUTOLIVE_ROLE_ID_MAIN = os.getenv("AUTOLIVE_ROLE_ID_MAIN", "")
AUTOLIVE_ROLE_ID_VTUBER = os.getenv("ROLE_ID_VTUBER", "")

# Twitch credentials
TWITCH_CLIENT_ID = os.getenv("TWITCHLIVE_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCHLIVE_CLIENT_SECRET", "")
TWITCH_TOKEN = os.getenv("TWITCHLIVE_TOKEN", "")
TWITCH_TOKEN_EXPIRES_AT = os.getenv("TWITCHLIVE_TOKEN_EXPIRES_AT", "")

# Custom messages (kept)
CUSTOM_MESSAGES = {
    "example_name": (
        "example_custom_message"
    ),
}

# Channel map loaders (unchanged semantics)
def _load_channel_map_file(name: str) -> dict:
    path = BASE_PATH / "channel_maps" / name
    try:
        print(f"[DEBUG-TWITCH] Loading channel map from {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR-TWITCH] Failed to load {name}: {e}")
        return {}

def _discover_channel_maps() -> Dict[str, dict]:
    maps: Dict[str, dict] = {}
    base = BASE_PATH / "channel_maps"

    if not base.exists():
        print(f"[DEBUG-TWITCH] Channel maps folder does not exist: {base}")
        return maps

    for path in sorted(base.glob("twitch*.json")):
        name = path.name

        if name == "twitch_nexus.json":
            category = "main"
        else:
            category = path.stem.removeprefix("twitch_")

        try:
            print(f"[DEBUG-TWITCH] Loading channel map from {path}")
            maps[category] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR-TWITCH] Failed to load {name}: {e}")
            maps[category] = {}

    return maps

def _default_target_for_category(category: str) -> Tuple[Optional[int], Optional[int]]:
    if category == "main":
        return AUTOLIVE_CHANNEL_ID, AUTOLIVE_ROLE_ID_MAIN

    return AUTOLIVE_CHANNEL_ID_VTUBER, AUTOLIVE_ROLE_ID_VTUBER

def _load_category_targets() -> Dict[str, dict]:
    return _load_json(CATEGORY_TARGETS_FILE)

def _save_category_targets(data: Dict[str, dict]) -> None:
    _save_json(CATEGORY_TARGETS_FILE, data)

def _merge_missing_category_targets(discovered_categories: List[str]) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
    saved = _load_category_targets()
    changed = False

    for category in discovered_categories:
        if category not in saved:
            channel_id, role_id = _default_target_for_category(category)
            saved[category] = {
                "channel_id": channel_id,
                "role_id": role_id,
            }
            print(
                f"[DEBUG-TWITCH] Added new category target for '{category}' "
                f"-> channel={channel_id}, role={role_id}"
            )
            changed = True

    if changed:
        _save_category_targets(saved)

    return {
        category: (
            cfg.get("channel_id"),
            cfg.get("role_id"),
        )
        for category, cfg in saved.items()
    }

# Target channels
def _get_int(name: str) -> Optional[int]:
    v = os.getenv(name)
    try:
        return int(v) if v else None
    except Exception:
        return None

# Utilities
def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_json(path: Path, data: dict):
    try:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False, default=str), encoding="utf-8")
    except Exception as e:
        print(f"[ERROR-TWITCH] Failed saving {path}: {e}")

def _safe_dt(s: Optional[str]) -> datetime:
    if not s:
        return datetime.fromisoformat("2000-01-01T00:00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.fromisoformat("2000-01-01T00:00:00")

def _update_env_token(new_token: str, new_expires_at: str):
    env_path = find_dotenv()
    if not env_path:
        print("[ERROR-TWITCH] .env not found; token persistence skipped.")
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(env_path, "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("TWITCHLIVE_TOKEN="):
                    f.write(f"TWITCHLIVE_TOKEN={new_token}\n")
                elif line.startswith("TWITCHLIVE_TOKEN_EXPIRES_AT="):
                    f.write(f"TWITCHLIVE_TOKEN_EXPIRES_AT={new_expires_at}\n")
                else:
                    f.write(line)
    except Exception as e:
        print(f"[ERROR-TWITCH] Failed to update .env: {e}")

# Core Cog
class Twitch(commands.Cog):
    """
    Single-task Twitch watcher with batched Helix calls and one aiohttp session.
    - Scans all categories every minute
    - Batches up to 100 user_logins per Helix request
    - Announces initially (with role ping once), then every 120 mins
    """
    def __init__(self, client: commands.Bot):
        self.client = client

        self.channel_maps = _discover_channel_maps()
        print(f"[DEBUG-TWITCH] Discovered categories: {list(self.channel_maps.keys())}")
        self.category_targets = _merge_missing_category_targets(list(self.channel_maps.keys()))

        # Live-status store (persisted)
        self.live_status: Dict[str, dict] = _load_json(LIVE_STATUS_FILE)

        # HTTP & token
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = TWITCH_TOKEN or None
        self._token_expiry: datetime = _safe_dt(TWITCH_TOKEN_EXPIRES_AT)

        # Build a flat list of channels to watch with targets
        self.watch_list: Dict[str, dict] = {}
        for category, cmap in self.channel_maps.items():
            channel_id, role_id = self.category_targets.get(category, (None, None))
            
            if not channel_id:
                print(f"[DEBUG-TWITCH] No channel_id for category {category}, skipping its entries.")
                continue
            
            for full_name, creator in (cmap or {}).items():
                if not isinstance(creator, dict):
                    raise TypeError(
                        f"Invalid creator format in category '{category}' for '{full_name}'. "
                        f"Expected dict, got {type(creator).__name__}: {creator!r}"
                    )

                nickname = creator.get("nickname")
                friendly = nickname or full_name
                platforms = creator.get("platforms", [])

                if not isinstance(platforms, list):
                    raise TypeError(
                        f"Invalid platforms format in category '{category}' for '{full_name}'. "
                        f"Expected list, got {type(platforms).__name__}: {platforms!r}"                        
                    )
                
                for platform in platforms:
                    if not isinstance(platform, dict):
                        raise TypeError(
                            f"Invalid platform entry in category '{category}' for '{full_name}'. "
                            f"Expected dict, got {type(platform).__name__}: {platform!r}"
                        )

                    if platform.get("type") != "twitch":
                        continue

                    login = platform.get("identifier")
                    if not login:
                        continue

                    self.watch_list[login.lower()] = {
                        "friendly": friendly,
                        "channel_id": channel_id,
                        "role_id": role_id,
                    }

        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            raise RuntimeError("TWITCHLIVE_CLIENT_ID and TWITCHLIVE_CLIENT_SECRET must be set.")

        # kick off the loop
        self.check_live_status.start()

    # lifecycle
    def cog_unload(self):
        self.check_live_status.cancel()
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())
        print("[DEBUG-TWITCH] Twitch cog unloaded; session closed and task cancelled.")

    @tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
    async def check_live_status(self):
        try:
            # lazily make session
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15), trust_env=True)
                print("[DEBUG-TWITCH] aiohttp session initialized.")

            # ensure token
            await self._ensure_token()

            # fetch & announce
            await self._scan_all()
        except Exception as e:
            print(f"[ERROR-TWITCH] check_live_status error: {e}")

    @check_live_status.before_loop
    async def _before(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(1)

    # Token handling
    async def _ensure_token(self):
        # refresh 5 minutes before expiry or if missing
        now = datetime.now()
        if self._token and (self._token_expiry - now) > timedelta(minutes=5):
            return

        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        try:
            async with self._session.post(url, params=params) as resp:
                if resp.status != 200:
                    print(f"[ERROR-TWITCH] Token refresh failed: {resp.status}")
                    self._token = None
                    return
                data = await resp.json()
        except Exception as e:
            print(f"[ERROR-TWITCH] Token refresh exception: {e}")
            self._token = None
            return

        self._token = data.get("access_token")
        expires_in = data.get("expires_in", 0)
        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
        os.environ["TWITCHLIVE_TOKEN"] = self._token or ""
        os.environ["TWITCHLIVE_TOKEN_EXPIRES_AT"] = self._token_expiry.isoformat()
        _update_env_token(self._token or "", self._token_expiry.isoformat())
        print("[DEBUG-TWITCH] Token refreshed and persisted.")

    # Scanning & announcements
    async def _scan_all(self):
        if not self.watch_list:
            return
        logins = list(self.watch_list.keys())

        # Helix: up to 100 user_login per call
        chunks = [logins[i : i + 100] for i in range(0, len(logins), 100)]
        live_now: Dict[str, dict] = {}

        for chunk in chunks:
            params = [("user_login", l) for l in chunk]
            try:
                async with self._session.get(
                    "https://api.twitch.tv/helix/streams",
                    params=params,
                    headers={"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {self._token}"},
                ) as resp:
                    if resp.status != 200:
                        print(f"[ERROR-TWITCH] Helix fetch failed: {resp.status}")
                        continue
                    payload = await resp.json()
            except Exception as e:
                print(f"[ERROR-TWITCH] Helix fetch exception: {e}")
                continue

            for item in payload.get("data", []):
                login = item.get("user_login", "").lower()
                if login:
                    live_now[login] = item

        # Merge with previous + announce
        changed = False
        now = datetime.now()

        for login, meta in self.watch_list.items():
            prev = self.live_status.get(login, {})
            was_live = prev.get("is_live", False)
            is_live = login in live_now

            # transition: offline -> live
            if is_live and not was_live:
                friendly = meta["friendly"]
                url = f"https://www.twitch.tv/{login}"
                game = live_now[login].get("game_name", "Unknown")
                title = live_now[login].get("title", "Untitled")
                msg = CUSTOM_MESSAGES.get(login, f"{friendly} is live!\nTitle: {title}\nPlaying: {game}\nWatch now: {url}")
                await self._notify(meta["channel_id"], msg, role_id=meta["role_id"])
                self.live_status[login] = {
                    "is_live": True,
                    "last_announced": now.isoformat(),
                    "first_ping_time": now.isoformat(),
                    "periodic_message_time": now.isoformat(),
                    "ping_sent": True,
                }
                changed = True
                continue

            # still live: periodic reminders
            if is_live and was_live:
                last_announced = _safe_dt(prev.get("last_announced"))
                periodic_time = _safe_dt(prev.get("periodic_message_time"))
                if (now - periodic_time) >= timedelta(minutes=ANNOUNCE_EVERY_MIN) and (now - last_announced) >= timedelta(minutes=ANNOUNCE_EVERY_MIN + ANNOUNCE_GRACE_MIN):
                    friendly = meta["friendly"]
                    url = f"https://www.twitch.tv/{login}"
                    await self._notify(meta["channel_id"], f"{friendly} is still live! {url}")
                    prev["periodic_message_time"] = now.isoformat()
                    self.live_status[login] = prev
                    changed = True

            # transition: live -> offline
            if not is_live and was_live:
                self.live_status[login] = {
                    "is_live": False,
                    "last_announced": None,
                    "first_ping_time": None,
                    "periodic_message_time": None,
                    "ping_sent": False,
                }
                changed = True

        if changed:
            _save_json(LIVE_STATUS_FILE, self.live_status)

    async def _notify(self, channel_id: Optional[int], message: str, role_id: Optional[int] = None):
        if not channel_id:
            return
        ch = self.client.get_channel(channel_id)
        if not ch:
            try:
                ch = await self.client.fetch_channel(channel_id)
            except Exception as e:
                print(f"[ERROR-TWITCH] Cannot fetch channel {channel_id}: {e}")
                return
        try:
            if role_id:
                await ch.send(f"<@&{role_id}> {message}")
            else:
                await ch.send(message)
        except Exception as e:
            print(f"[ERROR-TWITCH] Failed to send message to {channel_id}: {e}")

def setup(client: commands.Bot):
    client.add_cog(Twitch(client))
    print("[DEBUG-TWITCH] Twitch cog setup complete.")
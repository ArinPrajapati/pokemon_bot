import asyncio
import websockets
import json
import random
import string
from typing import Optional
import logging
import requests
import hashlib
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SHOWDOWN_WS_URL = "ws://localhost:8000/showdown/websocket"


def generate_random_username():
    """Generate a random username that doesn't start with 'guest'"""
    prefixes = ["Bot", "Player", "Trainer", "Fighter", "Battle", "Poke", "Duel", "Arena"]
    prefix = random.choice(prefixes)
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}{suffix}"


class ShowdownBot:
    def __init__(self, username: str = None, ws_url: str = None, battle_format: str = "gen9randombattle"):
        self.username = username or generate_random_username()
        self.battle_format = battle_format
        self.ws_url = ws_url or SHOWDOWN_WS_URL 
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.battle_room: Optional[str] = None
        self.logged_in = False
        self.battle_started = False
        self.fainted_slots: set[int] = set()
        self.team: list[dict] = []
        self.current_request = None
        self.is_official_server = "psim.us" in (ws_url or "")

    async def connect_and_run(self):
        try:
            # Add proper headers for official server
            extra_headers = {}
            if self.is_official_server:
                extra_headers = {
                    'Origin': 'https://play.pokemonshowdown.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            
            async with websockets.connect(
                self.ws_url, 
            ) as ws:
                self.ws = ws
                print(f"✅ Connected as {self.username}")
                await self.initialize()
                await self.main_loop()
        except Exception as e:
            print(f"❌ Connection error for {self.username}: {e}")

    async def initialize(self):
        """Initialize connection and login"""
        # Don't send nick command immediately, wait for challstr
        print(f"🔗 {self.username}: Waiting for server initialization...")
        
        # Wait for login confirmation
        while not self.logged_in:
            msg = await self.ws.recv()
            await self.handle_message(msg)
        
        # Start searching for battles
        await self.search_battle()

    async def main_loop(self):
        while True:
            try:
                msg = await self.ws.recv()
                await self.handle_message(msg)
            except websockets.exceptions.ConnectionClosed:
                print(f"{self.username} disconnected")
                break
            except Exception as e:
                print(f"Error for {self.username}: {e}")

    async def handle_message(self, msg: str):
        for line in msg.split("\n"):
            if line.startswith("|challstr|"):
                await self.handle_challstr(line)
            elif "|updateuser|" in line and self.username.lower() in line.lower():
                self.logged_in = True
                print(f"✅ Logged in as {self.username}")
            elif "|updatesearch|" in line:
                print(f"🔍 {self.username} searching...")
            elif line.startswith(">battle-"):
                room_id = line.split(">")[1].strip()
                self.battle_room = room_id
                self.battle_started = True
                print(f"⚔️ {self.username} joined: {self.battle_room}")
            elif "|request|" in line:
                try:
                    await asyncio.wait_for(self.handle_battle_request(line), timeout=30)
                except asyncio.TimeoutError:
                    print(f"⏰ {self.username}: Move timed out, skipping turn.")
            elif "|win|" in line:
                winner = line.split("|win|")[1].strip()
                print(f"🏆 {self.username} sees winner: {winner}")
            elif "|turn|" in msg:
                print(f"🔄 {self.username}: New turn started")
            elif "|pm|" in msg and "/challenge" in msg:
                try:
                    parts = msg.split("|pm|")[1].split("|")
                    challenger = parts[0].strip()
                    print(f"📬 Challenge received from {challenger}")
                    await self.ws.send(f"|/accept {challenger}")
                    print(f"✅ Accepted challenge from {challenger}")
                except Exception as e:
                    print(f"❌ Failed to parse challenge: {e}")
            elif line.startswith("|faint|"):
                await self.handle_faint(line)
            elif "|error|" in line:
                print(f"🚨 ERROR for {self.username}: {line}")
                await self.debug_team_state()
            elif "|nametaken|" in line:
                print(f"❌ Name taken: {line}")
                # Generate new username and retry
                self.username = generate_random_username()
                print(f"🔄 Trying new username: {self.username}")
            else:
                if line.strip() and not line.startswith("|c|"):  # Filter out chat messages
                    print(f"📬 {self.username} received: {line.strip()}")

    async def handle_faint(self, line: str):
        """Better faint handling with proper slot tracking"""
        try:
            faint_data = line.strip().split("|faint|")[1].strip()
            print(f"🔍 {self.username}: Raw faint data: {faint_data}")
            
            if ":" in faint_data:
                ident = faint_data.split(":")[0].strip()
            else:
                ident = faint_data.strip()
            
            if len(ident) >= 3:
                player = ident[1]
                slot_char = ident[2]
                
                our_player = '1' if self.username.endswith('1') else '2'
                
                if player == our_player:
                    fainted_index = ord(slot_char) - ord("a")
                    self.fainted_slots.add(fainted_index)
                    print(f"☠️ {self.username}: Our Pokémon in slot {fainted_index} ({slot_char}) fainted.")
                else:
                    print(f"💀 {self.username}: Opponent's Pokémon fainted: {ident}")
        except Exception as e:
            print(f"❌ {self.username}: Error parsing faint: {e} | Line: {line}")

    async def debug_team_state(self):
        """Debug function to log current team state"""
        print(f"🔍 {self.username} DEBUG - Team State:")
        print(f"   Fainted slots: {self.fainted_slots}")
        if self.current_request:
            side = self.current_request.get("side", {})
            pokemon_list = side.get("pokemon", [])
            for i, mon in enumerate(pokemon_list):
                condition = mon.get("condition", "unknown")
                active = mon.get("active", False)
                ident = mon.get("ident", f"slot_{i}")
                print(f"   Slot {i}: {ident} - Condition: {condition} - Active: {active}")

    async def handle_challstr(self, line: str):
        """Handle challstr and authenticate properly"""
        try:
            challstr_data = line.strip().split("|challstr|")[1]
            print(f"🔑 {self.username}: Received challstr: {challstr_data[:50]}...")
            
            if self.is_official_server:
                await self.authenticate_official_server(challstr_data)
            else:
                # Local server - simple authentication
                await self.ws.send(f"|/trn {self.username},0")
                print(f"🔐 {self.username}: Sent simple login")
                
        except Exception as e:
            print(f"❌ Error in handle_challstr for {self.username}: {e}")

    async def authenticate_official_server(self, challstr_data):
        """Authenticate with official Pokémon Showdown server"""
        try:
            # Use the correct login server URL
            login_url = "https://play.pokemonshowdown.com/~~showdown/action.php"
            
            # Prepare authentication data
            userid = self.username.lower().replace(' ', '')
            
            # Make sure username doesn't start with guest
            if userid.startswith('guest'):
                self.username = generate_random_username()
                userid = self.username.lower().replace(' ', '')
                print(f"🔄 {self.username}: Generated new username to avoid 'guest' restriction")
            
            data = {
                'act': 'getassertion',
                'userid': userid,
                'challstr': challstr_data,
                'pass': ''  # Empty password for guest login
            }
            
            print(f"🔐 {self.username}: Requesting authentication...")
            
            # Make request with proper headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://play.pokemonshowdown.com',
                'Referer': 'https://play.pokemonshowdown.com/'
            }
            
            response = requests.post(login_url, data=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                assertion = response.text.strip()
                
                if assertion.startswith(';;'):
                    # Error message from server
                    print(f"❌ {self.username}: Server error: {assertion}")
                    await self.fallback_guest_login()
                    return
                
                if len(assertion) > 10:  # Valid assertion should be longer
                    print(f"✅ {self.username}: Received valid assertion")
                    await self.ws.send(f"|/trn {self.username},0,{assertion}")
                    print(f"🔐 {self.username}: Sent authentication with assertion")
                else:
                    print(f"❌ {self.username}: Invalid assertion received: {assertion}")
                    await self.fallback_guest_login()
            else:
                print(f"❌ {self.username}: HTTP error {response.status_code}")
                await self.fallback_guest_login()
                
        except Exception as e:
            print(f"❌ {self.username}: Authentication error: {e}")
            await self.fallback_guest_login()

    async def fallback_guest_login(self):
        """Fallback authentication method"""
        try:
            print(f"🔄 {self.username}: Trying fallback authentication...")
            
            # Try different approaches
            approaches = [
                f"|/trn {self.username},0",
                f"|/nick {self.username}",
                f"|/trn {generate_random_username()},0"
            ]
            
            for approach in approaches:
                await self.ws.send(approach)
                await asyncio.sleep(1)
                print(f"🔄 {self.username}: Tried: {approach}")
                
        except Exception as e:
            print(f"❌ {self.username}: Fallback failed: {e}")

    async def search_battle(self):
        """Start searching for battles"""
        await self.ws.send(f"|/search {self.battle_format}")
        print(f"🔍 {self.username}: Started searching for {self.battle_format} battles")
        
        # Fallback challenge system for testing
        if not self.is_official_server:
            asyncio.create_task(self.fallback_battle())

    async def handle_battle_request(self, line: str):
        try:
            request_json = json.loads(line.split("|request|")[1])
            self.current_request = request_json
            
            # Initialize team data
            if not self.team and "side" in request_json:
                self.team = request_json["side"].get("pokemon", [])
                print(f"📋 {self.username}: Team initialized with {len(self.team)} Pokémon")

            # Handle forced switch
            if request_json.get("forceSwitch"):
                await self.choose_switch(request_json)
                return
                
            if not request_json.get("active"):
                print(f"⚠️ {self.username}: No active pokemon data")
                return

            active = request_json["active"][0]
            side = request_json.get("side", {})
            pokemon_list = side.get("pokemon", [])
            
            if not pokemon_list:
                print(f"⚠️ {self.username}: No pokemon in side data")
                return
                
            current_pokemon = pokemon_list[0]
            pokemon_name = current_pokemon.get("details", "???").split(",")[0]
            condition = current_pokemon.get("condition", "100/100")
            
            # Parse HP
            try:
                if "/" in condition:
                    current_hp = int(condition.split("/")[0].split(" ")[-1])
                else:
                    current_hp = 0 if condition == "0 fnt" else 100
            except (ValueError, IndexError):
                current_hp = 100

            moves = active.get("moves", [])
            
            # Decide whether to switch
            should_switch = (
                current_hp <= 20 or 
                not any(not m.get("disabled", False) for m in moves)
            )
            
            if should_switch:
                valid_switch = await self.find_valid_switch_target(pokemon_list)
                if valid_switch is not None:
                    await self.ws.send(f"{self.battle_room}|/choose switch {valid_switch}")
                    print(f"🔄 {self.username}: Switched to slot {valid_switch}")
                    return

            # Choose a move
            legal_moves = [
                i for i, move in enumerate(moves) if not move.get("disabled", False)
            ]
            
            if legal_moves:
                choice_index = random.choice(legal_moves)
                move_name = moves[choice_index]["move"]
                await self.ws.send(f"{self.battle_room}|/choose move {choice_index + 1}")
                print(f"⚡ {self.username}: Used {move_name}")
            else:
                print(f"❌ {self.username}: No legal moves available!")
                
        except Exception as e:
            print(f"❌ {self.username}: Battle request error: {e}")

    async def find_valid_switch_target(self, pokemon_list):
        """Find a pokemon to switch to"""
        for i, mon in enumerate(pokemon_list):
            condition = mon.get("condition", "")
            active = mon.get("active", False)
            
            if active or condition.startswith("0") or "fnt" in condition.lower():
                continue
                
            print(f"🎯 {self.username}: Valid switch target - Slot {i+1}")
            return i + 1
            
        return None

    async def choose_switch(self, request_json):
        """Handle forced switches"""
        print(f"🔄 {self.username}: Forced to switch!")
        
        side = request_json.get("side", {})
        pokemon_list = side.get("pokemon", [])
        
        valid_switch = await self.find_valid_switch_target(pokemon_list)
        if valid_switch is not None:
            await self.ws.send(f"{self.battle_room}|/choose switch {valid_switch}")
            print(f"✅ {self.username}: Switched to slot {valid_switch}")
        else:
            # Emergency switch
            await self.ws.send(f"{self.battle_room}|/choose switch 2")
            print(f"🆘 {self.username}: Emergency switch to slot 2")

    async def fallback_battle(self):
        """Fallback battle system for local testing"""
        await asyncio.sleep(15)
        if not self.battle_started:
            print(f"⚠️ {self.username}: No battle found, this is normal on official server")


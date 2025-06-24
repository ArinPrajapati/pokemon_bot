# showdown_bot.py
import asyncio
import websockets
import json
import random
from typing import Optional
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SHOWDOWN_WS_URL = "ws://localhost:8000/showdown/websocket"


class ShowdownBot:
    def __init__(self, username: str, battle_format: str = "gen9randombattle"):
        self.username = username
        self.battle_format = battle_format
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.battle_room: Optional[str] = None
        self.logged_in = False
        self.battle_started = False
        self.team_logged = False

    async def connect_and_run(self):
        try:
            async with websockets.connect(SHOWDOWN_WS_URL) as ws:
                self.ws = ws
                print(f"Connected as {self.username}")
                await self.initialize()
                await self.main_loop()
        except Exception as e:
            print(f"Connection error for {self.username}: {e}")

    async def initialize(self):
        await self.ws.send(f"|/nick {self.username}")
        while not self.logged_in:
            msg = await self.ws.recv()
            await self.handle_message(msg)
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
            elif "|updateuser|" in line and self.username in line:
                self.logged_in = True
                print(f"Logged in as {self.username}")
            elif "|updatesearch|" in line:
                print(f"{self.username} searching...")
            elif line.startswith(">battle-"):
                lines = msg.split("\n")
                for l in lines:
                    if l.startswith(">battle-"):
                        room_id = l.split(">")[1].strip()
                        if not self.battle_room:
                            self.battle_room = room_id
                            self.battle_started = True
                            print(f"{self.username} joined: {self.battle_room}")

            elif "|request|" in line:
                await self.handle_battle_request(line)
            elif "|win|" in line:
                winner = line.split("|win|")[1].strip()
                print(f"{self.username} sees winner: {winner}")
            elif "|turn|" in msg:
                # It's a new turn, do nothing, wait for |request| to decide
                print(f"{self.username}: New turn started")
            elif msg.startswith(">battle-") and not self.battle_started:
                self.battle_started = True
                self.battle_room = ...
            elif "|pm|" in msg and "/challenge" in msg:
                try:
                    parts = msg.split("|pm|")[1].split("|")
                    challenger = parts[0].strip()
                    print(f"Challenge received from {challenger}")
                    await self.ws.send(f"|/accept {challenger}")
                    print(f"Accepted challenge from {challenger}")
                except Exception as e:
                    print(f"Failed to parse challenge: {e}")

            else:
                print(f"{self.username} received: {line.strip()} msg:{msg}")

    async def handle_challstr(self, line: str):
        try:
            chall_id, chall_token = line.strip().split("|challstr|")[1].split("|")
            print(f"Received challstr for {self.username}: {chall_id}")
            await self.ws.send(f"|/trn {self.username},0")
            print(f"Sent guest login request for {self.username}")
        except Exception as e:
            print(f"Error in handle_challstr for {self.username}: {e}")

    async def search_battle(self):
        if self.battle_started:
            return
        await self.ws.send(f"|/search {self.battle_format}")
        print(f"{self.username} searching")

    async def handle_battle_request(self, line: str):
        try:
            request_json = json.loads(line.split("|request|")[1])
            if request_json.get("forceSwitch"):
                await self.choose_switch(request_json)
                return
            if not request_json.get("active"):
                return

            active = request_json["active"][0]
            pokemon_name = (
                request_json.get("side", {})
                .get("pokemon", [{}])[0]
                .get("details", "???")
                .split(",")[0]
            )
            if not hasattr(self, "team_logged"):
                self.save_team_to_file(request_json["side"]["pokemon"])
                self.team_logged = True
            moves = active.get("moves", [])
            condition = (
                request_json.get("side", {})
                .get("pokemon", [{}])[0]
                .get("condition", "100/100")
            )
            current_hp = int(
                condition.split("/")[0].split(" ")[-1]
            )  # Clean any status like 45/100 psn

            if current_hp <= 20 or not any(not m.get("disabled", False) for m in moves):
                await self.ws.send(f"{self.battle_room}|/choose switch 2")
                print(f"{self.username}: {pokemon_name} switched to Pokémon 2")
                return

            legal_moves = [
                i for i, move in enumerate(moves) if not move.get("disabled", False)
            ]
            if legal_moves:
                choice_index = random.choice(legal_moves)
                move_name = moves[choice_index]["move"]
                await self.ws.send(
                    f"{self.battle_room}|/choose move {choice_index + 1}"
                )
                await asyncio.sleep(1)
                print(f"{self.username}: {pokemon_name} used {move_name}")
        except Exception as e:
            print(f"{self.username} failed to choose move: {e}")

    async def choose_switch(self, request_json):
        side = request_json.get("side", {})
        pokemon_list = side.get("pokemon", [])

        for i, mon in enumerate(pokemon_list):
            is_active = mon.get("active", False)
            condition = mon.get("condition", "")
            hp_part = condition.split(" ")[0]
            if not is_active and not hp_part.startswith("0"):
                await self.ws.send(f"{self.battle_room}|/choose switch {i + 1}")
                print(
                    f"{self.username}: Switching to {mon.get('ident', f'Pokemon {i+1}')}"
                )
                return

        print(f"{self.username}: No valid Pokémon to switch to.")

    async def fallback_battle(self):
        await asyncio.sleep(20)
        if not self.battle_started and self.username == "mrbot1":
            await self.ws.send("|/challenge mrbot2, gen9randombattle")
            print(" No match fount ,sent manual challege to mrbot2")

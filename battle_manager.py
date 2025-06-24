import asyncio
from showdown_bot import ShowdownBot

class BattleManager:
    def __init__(self):
        self.bot1 = ShowdownBot("mrbot1")
        self.bot2 = ShowdownBot("mrbot2")

    async def run_battle(self):
        await asyncio.gather(
            self.bot1.connect_and_run(),
            self.bot2.connect_and_run()
        )


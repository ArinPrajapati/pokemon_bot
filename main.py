# main.py
import asyncio
from battle_manager import BattleManager
from battle_manager_online import OfficialBattleManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    i = input("Mode : ")
    if i == "0":
        manager = BattleManager()
        await manager.run_battle()
    elif i == "1":
        manager = OfficialBattleManager()
        await manager.test_against_real_players()

if __name__ == "__main__":
    asyncio.run(main())


# main.py
import asyncio
from battle_manager import BattleManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    manager = BattleManager()
    await manager.run_battle()

if __name__ == "__main__":
    asyncio.run(main())


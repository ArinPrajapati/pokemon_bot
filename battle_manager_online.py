import asyncio
import random
import string
from showdown_bot import ShowdownBot,generate_random_username


class OfficialBattleManager:
    def __init__(self):
        # Official Pokémon Showdown WebSocket URL
        self.official_ws_url = "wss://sim3.psim.us/showdown/websocket"
        
        # Generate a proper username
        self.bot_name = generate_random_username()
        
        # Create bot with official server URL
        self.bot = ShowdownBot(self.bot_name, ws_url=self.official_ws_url)
    
    async def test_against_real_players(self):
        """Test bot against real players on official server"""
        print(f"🚀 Starting bot: {self.bot_name}")
        print(f"🌐 Connecting to official Pokémon Showdown server")
        print(f"🎯 Will search for random battles...")
        print(f"🔗 Server: {self.official_ws_url}")
        
        try:
            await self.bot.connect_and_run()
        except KeyboardInterrupt:
            print(f"\n⏹️ {self.bot_name}: Stopped by user")
        except Exception as e:
            print(f"❌ {self.bot_name}: Error: {e}")



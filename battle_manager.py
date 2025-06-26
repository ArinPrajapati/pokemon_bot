import asyncio
from showdown_bot import ShowdownBot

class BattleManager:
    def __init__(self):
        self.bot1 = ShowdownBot("mrbot1",packed_team="gen9vgc2025regi]test|Slaking||lifeorb|truant|gigaimpact,earthquake,nightslash,protect|Adamant|4,252,,,,252|||||,,,,,Normal]Gardevoir||focussash|trace|skillswap,helpinghand,protect,moonblast|Timid|252,,,4,,252|||||,,,,,Fairy]Amoonguss||rockyhelmet|regenerator|ragepowder,spore,pollenpuff,protect|Relaxed|252,,172,,84,||,0,,,,0|||,,,,,Water]Chi-Yu||safetygoggles|beadsofruin|heatwave,darkpulse,snarl,protect|Timid|4,,,252,,252|||||,,,,,Ghost]Flutter Mane||covertcloak|protosynthesis|moonblast,shadowball,protect,icywind|Timid|4,,,252,,252|||||,,,,,Fairy]Iron Bundle||boosterenergy|quarkdrive|icywind,hydropump,freezedry,protect|Timid|4,,,252,,252|||||,,,,,Ice",battle_format="gen9nationaldexmonotype")
        self.bot2 = ShowdownBot("mrbot2",packed_team="gen9vgc2025regi]test|Slaking||lifeorb|truant|gigaimpact,earthquake,nightslash,protect|Adamant|4,252,,,,252|||||,,,,,Normal]Gardevoir||focussash|trace|skillswap,helpinghand,protect,moonblast|Timid|252,,,4,,252|||||,,,,,Fairy]Amoonguss||rockyhelmet|regenerator|ragepowder,spore,pollenpuff,protect|Relaxed|252,,172,,84,||,0,,,,0|||,,,,,Water]Chi-Yu||safetygoggles|beadsofruin|heatwave,darkpulse,snarl,protect|Timid|4,,,252,,252|||||,,,,,Ghost]Flutter Mane||covertcloak|protosynthesis|moonblast,shadowball,protect,icywind|Timid|4,,,252,,252|||||,,,,,Fairy]Iron Bundle||boosterenergy|quarkdrive|icywind,hydropump,freezedry,protect|Timid|4,,,252,,252|||||,,,,,Ice",battle_format="gen9nationaldexmonotype")
    async def run_battle(self):
        await asyncio.gather(
            self.bot1.connect_and_run(),
            self.bot2.connect_and_run()
        )


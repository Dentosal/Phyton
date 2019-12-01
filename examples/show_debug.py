import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

class MyBot(sc2.BotAI):
    async def on_step(self, iteration):
        for unit in self.units:
            self._client.debug_text_world(
                "\n".join([
                    f"{unit.type_id.name}:{unit.type_id.value}",
                    f"({unit.position.x:.2f},{unit.position.y:.2f})",
                    f"{unit.build_progress:.2f}",
                ] + [repr(x) for x in unit.orders]),
                unit.position3d,
                color=(0, 255, 0),
                size=12,
            )

        await self._client.send_debug()

def main():
    run_game(maps.get("Abyssal Reef LE"), [
        Bot(Race.Terran, MyBot()),
        Computer(Race.Protoss, Difficulty.Medium)
    ], realtime=True)

if __name__ == '__main__':
    main()

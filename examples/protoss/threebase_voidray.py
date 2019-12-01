import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.ids.buff_id import BuffId
from sc2.player import Bot, Computer

class ThreebaseVoidrayBot(sc2.BotAI):
    def select_target(self, state):
        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures)

        return self.enemy_start_locations[0]

    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(glhf)")

        if not self.units(NEXUS).ready.exists:
            for worker in self.workers:
                await self.do(worker.attack(self.enemy_start_locations[0]))
            return
        else:
            nexus = self.units(NEXUS).ready.random

        if not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
            abilities = await self.get_available_abilities(nexus)
            if AbilityId.EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                await self.do(nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus))

        for idle_worker in self.workers.idle:
            mf = self.state.mineral_field.closest_to(idle_worker)
            await self.do(idle_worker.gather(mf))

        if self.units(VOIDRAY).amount > 10 and iteration % 50 == 0:
            for vr in self.units(VOIDRAY).idle:
                await self.do(vr.attack(self.select_target(self.state)))

        for a in self.units(ASSIMILATOR):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        if self.supply_left < 2 and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, near=nexus)
            return

        if self.workers.amount < self.units(NEXUS).amount*15 and nexus.is_idle:
            if self.can_afford(PROBE):
                await self.do(nexus.train(PROBE))

        elif not self.units(PYLON).exists and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, near=nexus)

        if self.units(NEXUS).amount < 3 and not self.already_pending(NEXUS):
            if self.can_afford(NEXUS):
                await self.expand_now()

        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random
            if self.units(GATEWAY).ready.exists:
                if not self.units(CYBERNETICSCORE).exists:
                    if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                        await self.build(CYBERNETICSCORE, near=pylon)
            else:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

        for nexus in self.units(NEXUS).ready:
            vgs = self.state.vespene_geyser.closer_than(20.0, nexus)
            for vg in vgs:
                if not self.can_afford(ASSIMILATOR):
                    break

                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break

                if not self.units(ASSIMILATOR).closer_than(1.0, vg).exists:
                    await self.do(worker.build(ASSIMILATOR, vg))

        if self.units(PYLON).ready.exists and self.units(CYBERNETICSCORE).ready.exists:
            pylon = self.units(PYLON).ready.random
            if self.units(STARGATE).amount < 3 and not self.already_pending(STARGATE):
                if self.can_afford(STARGATE):
                    await self.build(STARGATE, near=pylon)

        for sg in self.units(STARGATE).ready.idle:
            if self.can_afford(VOIDRAY):
                await self.do(sg.train(VOIDRAY))

def main():
    sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
        Bot(Race.Protoss, ThreebaseVoidrayBot()),
        Computer(Race.Protoss, Difficulty.Easy)
    ], realtime=False)

if __name__ == '__main__':
    main()

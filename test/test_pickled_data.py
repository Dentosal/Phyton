import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sc2.game_data import GameData
from sc2.game_info import GameInfo
from sc2.game_info import Ramp
from sc2.game_state import GameState
from sc2.bot_ai import BotAI
from sc2.units import Units
from sc2.unit import Unit
from sc2.unit import UnitGameData
from sc2.position import Point2, Point3, Size, Rect

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.effect_id import EffectId

from sc2.data import Race

import pickle, pytest, random, math, lzma
from hypothesis import given, event, settings, strategies as st

from typing import Iterable


"""
You can execute this test running the following command from the root python-sc2 folder:
pipenv run pytest test/test_pickled_data.py

This test/script uses the pickle files located in "python-sc2/test/pickle_data" generated by "generate_pickle_files_bot.py" file, which is a bot that starts a game on each of the maps defined in the main function.

It will load the pickle files, recreate the bot object from scratch and tests most of the bot properties and functions.
All functions that require some kind of query or interaction with the API directly will have to be tested in the "autotest_bot.py" in a live game.
"""


def get_map_specific_bots() -> Iterable[BotAI]:
    folder = os.path.dirname(__file__)
    subfolder_name = "pickle_data"
    pickle_folder_path = os.path.join(folder, subfolder_name)
    files = os.listdir(pickle_folder_path)
    for file in (f for f in files if f.endswith(".xz")):
        with lzma.open(os.path.join(folder, subfolder_name, file), "rb") as f:
            raw_game_data, raw_game_info, raw_observation = pickle.load(f)

        # Build fresh bot object, and load the pickle'd data into the bot object
        bot = BotAI()
        game_data = GameData(raw_game_data.data)
        game_info = GameInfo(raw_game_info.game_info)
        game_state = GameState(raw_observation)
        UnitGameData._game_data = game_data
        bot._prepare_start(client=None, player_id=1, game_info=game_info, game_data=game_data)
        bot._prepare_step(state=game_state, proto_game_info=raw_game_info)

        yield bot


# From https://docs.pytest.org/en/latest/example/parametrize.html#a-quick-port-of-testscenarios
def pytest_generate_tests(metafunc):
    idlist = []
    argvalues = []
    for scenario in metafunc.cls.scenarios:
        idlist.append(scenario[0])
        items = scenario[1].items()
        argnames = [x[0] for x in items]
        argvalues.append(([x[1] for x in items]))
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="class")


# Global bot object that is used in TestClass.test_position_*
random_bot_object = next(get_map_specific_bots())


class TestClass:
    # Load all pickle files and convert them into bot objects from raw data (game_data, game_info, game_state)
    scenarios = [(bot_obj.game_info.map_name, {"bot": bot_obj}) for bot_obj in get_map_specific_bots()]

    def test_bot_ai(self, bot: BotAI):
        # Test initial bot attributes at game start

        # Properties from _prepare_start
        assert 1 <= bot.player_id <= 2
        assert isinstance(bot.race, Race)
        assert isinstance(bot.enemy_race, Race)

        # Properties from _prepare_step
        assert bot.units.amount == bot.townhalls.amount + bot.workers.amount
        assert bot.workers.amount == 12
        assert bot.townhalls.amount == 1
        assert bot.geysers.amount == 0
        assert bot.minerals == 50
        assert bot.vespene == 0
        assert bot.supply_army == 0
        assert bot.supply_workers == 12
        assert bot.supply_cap == 15
        assert bot.supply_used == 12
        assert bot.supply_left == 3
        assert bot.idle_worker_count == 0
        assert bot.army_count == 0

        # Test bot_ai functions
        assert bot.time == 0
        assert bot.time_formatted in {"0:00", "00:00"}
        assert bot.start_location is None  # Is populated by main.py
        bot._game_info.player_start_location = bot.townhalls.random.position
        assert bot.townhalls.random.position not in bot.enemy_start_locations
        assert bot.known_enemy_units == Units([])
        assert bot.known_enemy_structures == Units([])
        bot._game_info.map_ramps, bot._game_info.vision_blockers = bot._game_info._find_ramps_and_vision_blockers()
        assert bot.main_base_ramp  # Test if any ramp was found
        # TODO: Cache all expansion positions for a map and check if it is the same
        assert len(bot.expansion_locations) >= 10
        # On N player maps, it is expected that there are N*X bases because of symmetry, at least for 1vs1 maps
        assert (
            len(bot.expansion_locations) % (len(bot.enemy_start_locations) + 1) == 0
        ), f"{set(bot.expansion_locations.keys())}"
        # Test if bot start location is in expansion locations
        assert bot.townhalls.random.position in set(
            bot.expansion_locations.keys()
        ), f'This error might occur if you are running the tests locally using command "pytest test/", possibly because you are using an outdated cache.py version, but it should not occur when using docker and pipenv.\n{bot.townhalls.random.position}, {set(bot.expansion_locations.keys())}'
        # Test if enemy start locations are in expansion locations
        for location in bot.enemy_start_locations:
            assert location in set(bot.expansion_locations.keys()), f"{location}, {bot.expansion_locations.keys()}"

        # The following functions need to be tested by autotest_bot.py because they use API query which isn't available here as this file only uses the pickle files and is not able to interact with the API as SC2 is not running while this test runs
        # get_available_abilities
        # expand_now
        # get_next_expansion
        # distribute_workers
        assert bot.owned_expansions == {bot.townhalls.first.position: bot.townhalls.first}
        assert bot.can_feed(UnitTypeId.MARINE)
        assert bot.can_feed(UnitTypeId.SIEGETANK)
        assert not bot.can_feed(UnitTypeId.THOR)
        assert not bot.can_feed(UnitTypeId.BATTLECRUISER)
        assert not bot.can_feed(UnitTypeId.IMMORTAL)
        assert bot.can_afford(UnitTypeId.SCV)
        assert bot.can_afford(UnitTypeId.MARINE)
        assert not bot.can_afford(UnitTypeId.SIEGETANK)
        assert not bot.can_afford(UnitTypeId.BATTLECRUISER)
        assert not bot.can_afford(UnitTypeId.MARAUDER)
        # can_cast
        worker = bot.workers.random
        assert bot.select_build_worker(worker.position) == worker
        for w in bot.workers:
            if w == worker:
                continue
            assert bot.select_build_worker(w.position) != worker
        # can_place
        # find_placement
        assert bot.already_pending_upgrade(UpgradeId.STIMPACK) == 0
        assert bot.already_pending(UpgradeId.STIMPACK) == 0
        assert bot.already_pending(UnitTypeId.SCV) == 0
        # build
        # do
        # do_actions
        # chat_send
        assert 0 < bot.get_terrain_height(worker)
        assert bot.in_placement_grid(worker)
        assert bot.in_pathing_grid(worker)
        assert not bot.is_visible(worker)
        # The pickle data was created by a terran bot, so there is no creep under any worker
        assert not bot.has_creep(worker)

    def test_game_info(self, bot: BotAI):
        # Test if main base ramp works
        game_info: GameInfo = bot._game_info

        bot._game_info.player_start_location = bot.townhalls.random.position

        # Test game info object
        assert len(game_info.players) == 2
        assert game_info.map_name
        assert game_info.local_map_path
        assert game_info.map_size
        assert game_info.pathing_grid
        assert game_info.terrain_height
        assert game_info.placement_grid
        assert game_info.playable_area
        assert game_info.map_center
        assert game_info.map_ramps
        assert game_info.player_races
        assert game_info.start_locations
        assert game_info.player_start_location

    def test_main_base_ramp(self, bot: BotAI):
        # Test if main ramp works for one of the opponent
        game_info: GameInfo = bot._game_info

        for spawn in bot._game_info.start_locations + [bot.townhalls.random.position]:
            # Remove cached ramp
            if hasattr(bot, "cached_main_base_ramp"):
                del bot.cached_main_base_ramp
            # Set start location as one of the opponent spawns
            bot._game_info.player_start_location = spawn
            # Find main base ramp for opponent
            ramp: Ramp = bot.main_base_ramp
            # On the map HonorgroundsLE, the main base is large and it would take a bit of effort to fix, so it returns None or empty set
            if len(ramp.upper) in {2, 5}:
                assert ramp.barracks_correct_placement
                assert ramp.barracks_in_middle
                assert ramp.depot_in_middle
                assert len(ramp.corner_depots) == 2
                assert ramp.upper2_for_ramp_wall
            else:
                # On maps it is unable to find valid wall positions (Honorgrounds LE) it should return None
                assert ramp.barracks_correct_placement is None
                assert ramp.barracks_in_middle is None
                assert ramp.depot_in_middle is None
                assert ramp.corner_depots == set()
            assert ramp.top_center
            assert ramp.bottom_center
            assert ramp.size
            assert ramp.points
            assert ramp.upper
            assert ramp.lower
            # Test if ramp was detected far away
            distance = ramp.top_center.distance_to(bot._game_info.player_start_location)
            assert distance < 30, f"Distance from spawn to main ramp was detected as {distance:.2f}, which is too far. Spawn: {spawn}, Ramp: {ramp.top_center}"


    def test_game_data(self, bot: BotAI):
        game_data = bot._game_data
        assert game_data.abilities
        assert game_data.units
        assert game_data.upgrades
        assert len(game_data.unit_types) == 2  # Filled with CC and SCV from previous tests

    def test_game_state(self, bot: BotAI):
        state = bot.state

        assert not state.actions
        assert not state.action_errors
        assert not state.dead_units
        assert not state.alerts
        assert not state.player_result
        assert not state.chat
        assert state.common
        assert state.psionic_matrix
        assert state.game_loop == 0
        assert state.score
        assert state.own_units == bot.units
        assert not state.enemy_units
        assert state.mineral_field
        assert state.vespene_geyser
        assert state.resources
        # There may be maps without destructables
        assert isinstance(state.destructables, (list, set, dict))
        assert state.units
        assert not state.upgrades
        assert not state.dead_units
        assert not state.blips
        assert state.visibility
        assert state.creep
        assert not state.effects

    def test_pixelmap(self, bot: BotAI):
        # TODO
        pass

    def test_score(self, bot: BotAI):
        # TODO
        pass

    def test_unit(self, bot: BotAI):
        scv: Unit = random_bot_object.workers.random
        townhall: Unit = random_bot_object.townhalls.first

        assert scv.name
        assert scv.race
        assert scv.tag
        assert not scv.is_structure
        assert townhall.is_structure
        assert scv.is_light
        assert not townhall.is_light
        assert not scv.is_armored
        assert townhall.is_armored
        assert scv.is_biological
        assert not townhall.is_biological
        assert scv.is_mechanical
        assert townhall.is_mechanical
        assert not scv.is_massive
        assert not townhall.is_massive
        assert not scv.is_psionic
        assert not townhall.is_psionic
        assert scv.tech_alias is None
        assert townhall.tech_alias is None
        assert scv.unit_alias is None
        assert townhall.unit_alias is None
        assert scv.can_attack
        assert not townhall.can_attack
        assert scv.can_attack_ground
        assert not townhall.can_attack_ground
        assert scv.ground_dps
        assert not townhall.ground_dps
        assert scv.ground_range
        assert not townhall.ground_range
        assert not scv.can_attack_air
        assert not townhall.can_attack_air
        assert not scv.air_dps
        assert not townhall.air_dps
        assert not scv.air_range
        assert not townhall.air_range
        assert not scv.bonus_damage
        assert not townhall.bonus_damage
        assert not scv.armor
        assert townhall.armor
        assert scv.sight_range
        assert townhall.sight_range
        assert scv.movement_speed
        assert not townhall.movement_speed
        assert not scv.is_mineral_field
        assert not townhall.is_mineral_field
        assert not scv.is_vespene_geyser
        assert not townhall.is_vespene_geyser
        assert scv.health
        assert townhall.health
        assert scv.health_max
        assert townhall.health_max
        assert scv.health_percentage
        assert townhall.health_percentage
        assert not scv.shield
        assert not townhall.shield
        assert not scv.shield_max
        assert not townhall.shield_max
        assert not scv.shield_percentage
        assert not townhall.shield_percentage
        assert not scv.energy
        assert not townhall.energy
        assert not scv.energy_max
        assert not townhall.energy_max
        assert not scv.energy_percentage
        assert not townhall.energy_percentage
        assert not scv.is_snapshot
        assert not townhall.is_snapshot
        assert scv.is_visible
        assert townhall.is_visible
        assert scv.alliance
        assert townhall.alliance
        assert scv.is_mine
        assert townhall.is_mine
        assert not scv.is_enemy
        assert not townhall.is_enemy
        assert scv.owner_id
        assert townhall.owner_id
        assert scv.position
        assert townhall.position
        assert scv.position3d
        assert townhall.position3d
        assert scv.distance_to(townhall)
        assert townhall.distance_to(scv)
        # assert scv.facing
        assert townhall.facing
        assert scv.radius
        assert townhall.radius
        assert scv.build_progress
        assert townhall.build_progress
        assert scv.is_ready
        assert townhall.is_ready
        # assert not scv.cloak
        # assert not townhall.cloak
        assert not scv.is_cloaked
        assert not townhall.is_cloaked
        assert not scv.buffs
        assert not townhall.buffs
        assert not scv.is_carrying_minerals
        assert not townhall.is_carrying_minerals
        assert not scv.is_carrying_vespene
        assert not townhall.is_carrying_vespene
        assert not scv.is_carrying_resource
        assert not townhall.is_carrying_resource
        assert not scv.detect_range
        assert not townhall.detect_range
        assert not scv.radar_range
        assert not townhall.radar_range
        assert not scv.is_selected
        assert not townhall.is_selected
        assert scv.is_on_screen
        assert townhall.is_on_screen
        assert not scv.is_blip
        assert not townhall.is_blip
        assert not scv.is_powered
        assert not townhall.is_powered
        assert scv.is_active
        assert not townhall.is_active
        assert not scv.mineral_contents
        assert not townhall.mineral_contents
        assert not scv.vespene_contents
        assert not townhall.vespene_contents
        assert not scv.has_vespene
        assert not townhall.has_vespene
        assert not scv.is_flying
        assert not townhall.is_flying
        assert not scv.is_burrowed
        assert not townhall.is_burrowed
        assert not scv.is_hallucination
        assert not townhall.is_hallucination
        assert scv.orders
        assert not townhall.orders
        assert scv.order_target
        assert not townhall.order_target
        assert not scv.is_idle
        assert townhall.is_idle
        assert not scv.is_using_ability(AbilityId.TERRANBUILD_SUPPLYDEPOT)
        assert not townhall.is_using_ability(AbilityId.COMMANDCENTERTRAIN_SCV)
        assert not scv.is_moving
        assert not townhall.is_moving
        assert not scv.is_attacking
        assert not townhall.is_attacking
        assert not scv.is_patrolling
        assert not townhall.is_patrolling
        assert scv.is_gathering
        assert not townhall.is_gathering
        assert not scv.is_returning
        assert not townhall.is_returning
        assert scv.is_collecting
        assert not townhall.is_collecting
        assert not scv.is_constructing_scv
        assert not townhall.is_constructing_scv
        assert not scv.is_repairing
        assert not townhall.is_repairing
        assert not scv.add_on_tag
        assert not townhall.add_on_tag
        assert not scv.has_add_on
        assert not townhall.has_add_on
        assert scv.add_on_land_position
        assert townhall.add_on_land_position
        assert not scv.passengers
        assert not townhall.passengers
        assert not scv.passengers_tags
        assert not townhall.passengers_tags
        assert not scv.cargo_used
        assert not townhall.cargo_used
        assert not scv.has_cargo
        assert not townhall.has_cargo
        assert scv.cargo_size
        assert not townhall.cargo_size
        assert not scv.cargo_max
        assert not townhall.cargo_max
        assert not scv.cargo_left
        assert not townhall.cargo_left
        assert not scv.assigned_harvesters
        assert townhall.assigned_harvesters == 12
        assert not scv.ideal_harvesters
        assert townhall.ideal_harvesters == 16
        assert not scv.surplus_harvesters
        assert townhall.surplus_harvesters == -4
        assert not scv.weapon_cooldown
        assert townhall.weapon_cooldown == -1
        assert not scv.engaged_target_tag
        assert not townhall.engaged_target_tag
        assert not scv.is_detector
        assert not townhall.is_detector
        # assert not scv.target_in_range(townhall)
        assert not townhall.target_in_range(scv)
        # assert not scv.has_buff(buff ID)
        # assert not townhall.has_buff(buff ID)

    def test_units(self, bot: BotAI):
        scvs = bot.workers
        townhalls = bot.townhalls

        assert scvs.amount
        assert townhalls.amount
        assert not scvs.empty
        assert not townhalls.empty
        assert scvs.exists
        assert townhalls.exists
        assert scvs.find_by_tag(scvs.random.tag)
        assert not townhalls.find_by_tag(0)
        assert scvs.first
        assert townhalls.first
        assert scvs.take(11)
        assert townhalls.take(1)
        assert scvs.random
        assert townhalls.random
        assert scvs.random_or(1)
        assert townhalls.random_or(0)
        assert scvs.random_group_of(11)
        assert not scvs.random_group_of(0)
        assert not townhalls.random_group_of(0)
        # assert not scvs.in_attack_range_of(townhalls.first)
        # assert not townhalls.in_attack_range_of(scvs.first)
        assert scvs.closest_distance_to(townhalls.first)
        assert townhalls.closest_distance_to(scvs.first)
        assert scvs.furthest_distance_to(townhalls.first)
        assert townhalls.furthest_distance_to(scvs.first)
        assert scvs.closest_to(townhalls.first)
        assert townhalls.closest_to(scvs.first)
        assert scvs.furthest_to(townhalls.first)
        assert townhalls.furthest_to(scvs.first)
        assert scvs.closer_than(10, townhalls.first)
        assert townhalls.closer_than(10, scvs.first)
        assert scvs.further_than(0, townhalls.first)
        assert townhalls.further_than(0, scvs.first)
        assert scvs.subgroup(scvs)
        assert townhalls.subgroup(townhalls)
        assert scvs.filter(pred=lambda x: x.type_id == UnitTypeId.SCV)
        assert not townhalls.filter(pred=lambda x: x.type_id == UnitTypeId.NEXUS)
        assert scvs.sorted
        assert townhalls.sorted
        assert scvs.sorted_by_distance_to(townhalls.first)
        assert townhalls.sorted_by_distance_to(scvs.first)
        assert scvs.tags_in(scvs.tags)
        assert not townhalls.tags_in({0, 1, 2})
        assert not scvs.tags_not_in(scvs.tags)
        assert townhalls.tags_not_in({0, 1, 2})
        assert scvs.of_type(UnitTypeId.SCV)
        assert townhalls.of_type({UnitTypeId.COMMANDCENTER, UnitTypeId.COMMANDCENTERFLYING})
        assert not scvs.exclude_type(UnitTypeId.SCV)
        assert townhalls.exclude_type({UnitTypeId.COMMANDCENTERFLYING})
        assert not scvs.same_tech(UnitTypeId.PROBE)
        assert townhalls.same_tech({UnitTypeId.ORBITALCOMMAND})
        assert scvs.same_unit(UnitTypeId.SCV)
        assert townhalls.same_unit({UnitTypeId.COMMANDCENTERFLYING})
        assert scvs.center
        assert townhalls.center == townhalls.first.position
        assert not scvs.selected
        assert not townhalls.selected
        assert scvs.tags
        assert townhalls.tags
        assert scvs.ready
        assert townhalls.ready
        assert not scvs.not_ready
        assert not townhalls.not_ready
        assert not scvs.idle
        assert townhalls.idle
        assert scvs.owned
        assert townhalls.owned
        assert not scvs.enemy
        assert not townhalls.enemy
        assert not scvs.flying
        assert not townhalls.flying
        assert scvs.not_flying
        assert townhalls.not_flying
        assert not scvs.structure
        assert townhalls.structure
        assert scvs.not_structure
        assert not townhalls.not_structure
        assert scvs.gathering
        assert not townhalls.gathering
        assert not scvs.returning
        assert not townhalls.returning
        assert scvs.collecting
        assert not townhalls.collecting
        assert scvs.visible
        assert townhalls.visible
        assert not scvs.mineral_field
        assert not townhalls.mineral_field
        assert not scvs.vespene_geyser
        assert not townhalls.vespene_geyser
        assert scvs.prefer_idle
        assert townhalls.prefer_idle

    @given(
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
    )
    @settings(max_examples=500)
    def test_position_pointlike(self, bot: BotAI, x1, y1, x2, y2, x3, y3):
        pos1 = Point2((x1, y1))
        pos2 = Point2((x2, y2))
        pos3 = Point2((x3, y3))
        epsilon = 1e-3
        assert pos1.position == pos1
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        assert abs(pos1.distance_to(pos2) - dist) <= epsilon
        assert abs(pos1.distance_to_point2(pos2) - dist) <= epsilon
        assert abs(pos1._distance_squared(pos2) ** 0.5 - dist) <= epsilon

        if epsilon < dist < 1e5:
            assert pos1.is_closer_than(dist + epsilon, pos2)
            assert pos1.is_further_than(dist - epsilon, pos2)

        points = {pos2, pos3}
        points2 = {pos1, pos2, pos3}
        # All 3 points need to be different
        if len(points2) == 3:
            assert pos1.sort_by_distance(points2) == sorted(points2, key=lambda p: pos1._distance_squared(p))
            assert pos1.closest(points2) == pos1
            closest_point = min(points, key=lambda p: p._distance_squared(pos1))
            dist_closest_point = pos1._distance_squared(closest_point) ** 0.5
            furthest_point = max(points, key=lambda p: p._distance_squared(pos1))
            dist_furthest_point = pos1._distance_squared(furthest_point) ** 0.5

            # Distances between pos1-pos2 and pos1-pos3 might be the same, so the sorting might still be different, that's why I use a set here
            assert pos1.closest(points) in {p for p in points2 if abs(pos1.distance_to(p) - dist_closest_point) < epsilon}
            assert abs(pos1.distance_to_closest(points) - pos1._distance_squared(closest_point) ** 0.5) < epsilon
            assert pos1.furthest(points) in {p for p in points2 if abs(pos1.distance_to(p) - dist_furthest_point) < epsilon}
            assert abs(pos1.distance_to_furthest(points) - pos1._distance_squared(furthest_point) ** 0.5) < epsilon
            assert pos1.offset(pos2) == Point2((pos1.x + pos2.x, pos1.y + pos2.y))
            if pos1 != pos2:
                assert pos1.unit_axes_towards(pos2) != Point2((0, 0))

            if 0 < x3:
                temp_pos = pos1.towards(pos2, x3)
                if x3 <= pos1.distance_to(pos2):
                    # Using "towards" function to go between pos1 and pos2
                    dist1 = pos1.distance_to(temp_pos) + pos2.distance_to(temp_pos)
                    dist2 = pos1.distance_to(pos2)
                    assert abs(dist1 - dist2) <= epsilon
                else:
                    # Using "towards" function to go past pos2
                    dist1 = pos1.distance_to(pos2) + pos2.distance_to(temp_pos)
                    dist2 = pos1.distance_to(temp_pos)
                    assert abs(dist1 - dist2) <= epsilon
            elif x3 < 0:
                # Using "towards" function with a negative value
                temp_pos = pos1.towards(pos2, x3)
                dist1 = temp_pos.distance_to(pos1) + pos1.distance_to(pos2)
                dist2 = pos2.distance_to(temp_pos)
                assert abs(dist1 - dist2) <= epsilon

        assert pos1 == pos1
        assert pos2 == pos2
        assert pos3 == pos3
        assert isinstance(hash(pos1), int)
        assert isinstance(hash(pos2), int)
        assert isinstance(hash(pos3), int)

    @given(
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
    )
    @settings(max_examples=500)
    def test_position_point2(self, bot: BotAI, x1, y1, x2, y2):
        pos1 = Point2((x1, y1))
        pos2 = Point2((x2, y2))
        assert pos1.x == x1
        assert pos1.y == y1
        assert pos1.to2 == pos1
        assert pos1.to3 == Point3((x1, y1, 0))
        assert pos1.distance2_to(pos2) == pos1._distance_squared(pos2)
        if 0 < x2:
            assert pos1.random_on_distance(x2) != pos1
            assert pos1.towards_with_random_angle(pos2, x2) != pos1
        assert pos1.towards_with_random_angle(pos2) != pos1
        if pos1 != pos2:
            dist = pos1.distance_to(pos2)
            intersections1 = pos1.circle_intersection(pos2, r=dist / 2)
            assert len(intersections1) == 1
            intersections2 = pos1.circle_intersection(pos2, r=dist * 2 / 3)
            assert len(intersections2) == 2
        neighbors4 = pos1.neighbors4
        assert len(neighbors4) == 4
        neighbors8 = pos1.neighbors8
        assert len(neighbors8) == 8

        assert pos1 + pos2 == Point2((x1 + x2, y1 + y2))
        assert pos1 - pos2 == Point2((x1 - x2, y1 - y2))
        assert pos1 * pos2 == Point2((x1 * x2, y1 * y2))
        if 0 not in {x2, y2}:
            assert pos2
            assert pos1 / pos2 == Point2((x1 / x2, y1 / y2))

        if pos1._distance_squared(pos2) < 0.1:
            assert pos1.is_same_as(pos2, dist=0.1)

        assert pos1.unit_axes_towards(pos2) == pos1.direction_vector(pos2)

    @given(
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
    )
    @settings(max_examples=10)
    def test_position_point2(self, bot: BotAI, x1, y1, z1):
        pos1 = Point3((x1, y1, z1))
        assert pos1.z == z1
        assert pos1.to3 == pos1

    @given(st.integers(min_value=-1e5, max_value=1e5), st.integers(min_value=-1e5, max_value=1e5))
    @settings(max_examples=20)
    def test_position_size(self, bot: BotAI, w, h):
        size = Size((w, h))
        assert size.width == w
        assert size.height == h

    @given(
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
        st.integers(min_value=-1e5, max_value=1e5),
    )
    @settings(max_examples=20)
    def test_position_rect(self, bot: BotAI, x, y, w, h):
        rect = Rect((x, y, w, h))
        assert rect.x == x
        assert rect.y == y
        assert rect.width == w
        assert rect.height == h
        assert rect.size == Size((w, h))
        assert rect.center == Point2((rect.x + rect.width / 2, rect.y + rect.height / 2))
        assert rect.offset((1, 1)) == Rect((x + 1, y + 1, w, h))

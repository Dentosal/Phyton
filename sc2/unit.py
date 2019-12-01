import warnings
from typing import Any, Dict, List, Optional, Set, Tuple, Union  # mypy type checking

from . import unit_command
from .cache import property_immutable_cache, property_mutable_cache
from .constants import transforming
from .data import Alliance, Attribute, CloakState, DisplayType, Race, TargetType, warpgate_abilities
from .ids.ability_id import AbilityId
from .ids.buff_id import BuffId
from .ids.unit_typeid import UnitTypeId
from .position import Point2, Point3

warnings.simplefilter("once")


class UnitGameData:
    """ Populated by sc2/main.py on game launch.
    Used in PassengerUnit, Unit, Units and UnitOrder. """

    # TODO: When doing bot vs bot, the same _game_data is currently accessed if the laddermanager
    # is not being used and the bots access the same sc2 library
    # Could use inspect for that: Loop over i for "calframe[i].frame.f_locals["self"]"
    # until an instance of BotAi is found
    _game_data = None
    _bot_object = None


class UnitOrder:
    @classmethod
    def from_proto(cls, proto):
        return cls(
            UnitGameData._game_data.abilities[proto.ability_id],
            (proto.target_world_space_pos if proto.HasField("target_world_space_pos") else proto.target_unit_tag),
            proto.progress,
        )

    def __init__(self, ability, target, progress=None):
        self.ability = ability
        self.target = target
        self.progress = progress

    def __repr__(self) -> str:
        return f"UnitOrder({self.ability}, {self.target}, {self.progress})"


class Unit:
    def __init__(self, proto_data):
        self._proto = proto_data
        self.cache = {}

    def __repr__(self) -> str:
        """ Returns string of this form: PassengerUnit(name='SCV', tag=4396941328). """
        return f"{self.__class__.__name__}(name={self.name !r}, tag={self.tag})"

    @property_immutable_cache
    def type_id(self) -> UnitTypeId:
        """ UnitTypeId found in sc2/ids/unit_typeid.
        Caches all type_ids of the same unit type. """
        unit_type = self._proto.unit_type
        if unit_type not in UnitGameData._game_data.unit_types:
            UnitGameData._game_data.unit_types[unit_type] = UnitTypeId(unit_type)
        return UnitGameData._game_data.unit_types[unit_type]

    @property_immutable_cache
    def _type_data(self) -> "UnitTypeData":
        """ Provides the unit type data. """
        return UnitGameData._game_data.units[self._proto.unit_type]

    @property
    def name(self) -> str:
        """ Returns the name of the unit. """
        return self._type_data.name

    @property
    def race(self) -> Race:
        """ Returns the race of the unit """
        return Race(self._type_data._proto.race)

    @property_immutable_cache
    def tag(self) -> int:
        """ Returns the unique tag of the unit. """
        return self._proto.tag

    @property
    def is_structure(self) -> bool:
        """ Checks if the unit is a structure. """
        return Attribute.Structure.value in self._type_data.attributes

    @property
    def is_light(self) -> bool:
        """ Checks if the unit has the 'light' attribute. """
        return Attribute.Light.value in self._type_data.attributes

    @property
    def is_armored(self) -> bool:
        """ Checks if the unit has the 'armored' attribute. """
        return Attribute.Armored.value in self._type_data.attributes

    @property
    def is_biological(self) -> bool:
        """ Checks if the unit has the 'biological' attribute. """
        return Attribute.Biological.value in self._type_data.attributes

    @property
    def is_mechanical(self) -> bool:
        """ Checks if the unit has the 'mechanical' attribute. """
        return Attribute.Mechanical.value in self._type_data.attributes

    @property
    def is_massive(self) -> bool:
        """ Checks if the unit has the 'massive' attribute. """
        return Attribute.Massive.value in self._type_data.attributes

    @property
    def is_psionic(self) -> bool:
        """ Checks if the unit has the 'psionic' attribute. """
        return Attribute.Psionic.value in self._type_data.attributes

    @property
    def tech_alias(self) -> Optional[List[UnitTypeId]]:
        """ Building tech equality, e.g. OrbitalCommand is the same as CommandCenter
        For Hive, this returns [UnitTypeId.Hatchery, UnitTypeId.Lair]
        For SCV, this returns None """
        return self._type_data.tech_alias

    @property
    def unit_alias(self) -> Optional[UnitTypeId]:
        """ Building type equality, e.g. FlyingOrbitalCommand is the same as OrbitalCommand
        For flying OrbitalCommand, this returns UnitTypeId.OrbitalCommand
        For SCV, this returns None """
        return self._type_data.unit_alias

    @property_immutable_cache
    def _weapons(self):
        """ Returns the weapons of the unit. """
        try:
            return self._type_data._proto.weapons
        except:
            return None

    @property_immutable_cache
    def can_attack(self) -> bool:
        """ Checks if the unit can attack at all. """
        # TODO BATTLECRUISER doesnt have weapons in proto?!
        return bool(self._weapons) or self.type_id == UnitTypeId.BATTLECRUISER

    @property_immutable_cache
    def can_attack_both(self) -> bool:
        """ Checks if the unit can attack both ground and air units. """
        return self.can_attack_ground and self.can_attack_air

    @property_immutable_cache
    def can_attack_ground(self) -> bool:
        """ Checks if the unit can attack ground units. """
        if self._weapons:
            return any(weapon.type in {TargetType.Ground.value, TargetType.Any.value} for weapon in self._weapons)
        return False

    @property_immutable_cache
    def ground_dps(self) -> Union[int, float]:
        """ Returns the dps against ground units. Does not include upgrades. """
        if self.can_attack_ground:
            weapon = next(
                (weapon for weapon in self._weapons if weapon.type in {TargetType.Ground.value, TargetType.Any.value}),
                None,
            )
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @property_immutable_cache
    def ground_range(self) -> Union[int, float]:
        """ Returns the range against ground units. Does not include upgrades. """
        if self.can_attack_ground:
            weapon = next(
                (weapon for weapon in self._weapons if weapon.type in {TargetType.Ground.value, TargetType.Any.value}),
                None,
            )
            if weapon:
                return weapon.range
        return 0

    @property_immutable_cache
    def can_attack_air(self) -> bool:
        """ Checks if the unit can air attack at all. Does not include upgrades. """
        if self._weapons:
            return any(weapon.type in {TargetType.Air.value, TargetType.Any.value} for weapon in self._weapons)
        return False

    @property_immutable_cache
    def air_dps(self) -> Union[int, float]:
        """ Returns the dps against air units. Does not include upgrades. """
        if self.can_attack_air:
            weapon = next(
                (weapon for weapon in self._weapons if weapon.type in {TargetType.Air.value, TargetType.Any.value}),
                None,
            )
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @property_immutable_cache
    def air_range(self) -> Union[int, float]:
        """ Returns the range against air units. Does not include upgrades. """
        if self.can_attack_air:
            weapon = next(
                (weapon for weapon in self._weapons if weapon.type in {TargetType.Air.value, TargetType.Any.value}),
                None,
            )
            if weapon:
                return weapon.range
        return 0

    @property_immutable_cache
    def bonus_damage(self):
        """ Returns a tuple of form '(bonus damage, armor type)' if unit does 'bonus damage' against 'armor type'.
        Possible armor typs are: 'Light', 'Armored', 'Biological', 'Mechanical', 'Psionic', 'Massive', 'Structure'. """
        # TODO Consider unit with ability attacks like Oracle, Thor, Baneling.
        if self._weapons:
            for weapon in self._weapons:
                if weapon.damage_bonus:
                    b = weapon.damage_bonus[0]
                    return (b.bonus, Attribute(b.attribute).name)
        else:
            return None

    @property
    def armor(self) -> Union[int, float]:
        """ Returns the armor of the unit. Does not include upgrades """
        return self._type_data._proto.armor

    @property
    def sight_range(self) -> Union[int, float]:
        """ Returns the sight range of the unit. """
        return self._type_data._proto.sight_range

    @property
    def movement_speed(self) -> Union[int, float]:
        """ Returns the movement speed of the unit. Does not include upgrades or buffs. """
        return self._type_data._proto.movement_speed

    @property
    def is_mineral_field(self) -> bool:
        """ Checks if the unit is a mineral field. """
        return self._type_data.has_minerals

    @property
    def is_vespene_geyser(self) -> bool:
        """ Checks if the unit is a non-empty vespene geyser. """
        return self._type_data.has_vespene

    @property_immutable_cache
    def health(self) -> Union[int, float]:
        """ Returns the health of the unit. Does not include shields. """
        return self._proto.health

    @property_immutable_cache
    def health_max(self) -> Union[int, float]:
        """ Returns the maximum health of the unit. Does not include shields. """
        return self._proto.health_max

    @property_immutable_cache
    def health_percentage(self) -> Union[int, float]:
        """ Returns the percentage of health the unit has. Does not include shields. """
        if self._proto.health_max == 0:
            return 0
        return self._proto.health / self._proto.health_max

    @property_immutable_cache
    def shield(self) -> Union[int, float]:
        """ Returns the shield points the unit has. Returns 0 for non-protoss units. """
        return self._proto.shield

    @property_immutable_cache
    def shield_max(self) -> Union[int, float]:
        """ Returns the maximum shield points the unit can have. Returns 0 for non-protoss units. """
        return self._proto.shield_max

    @property_immutable_cache
    def shield_percentage(self) -> Union[int, float]:
        """ Returns the percentage of shield points the unit has. Returns 0 for non-protoss units. """
        if self._proto.shield_max == 0:
            return 0
        return self._proto.shield / self._proto.shield_max

    @property_immutable_cache
    def energy(self) -> Union[int, float]:
        """ Returns the amount of energy the unit has. Returns 0 for units without energy. """
        return self._proto.energy

    @property_immutable_cache
    def energy_max(self) -> Union[int, float]:
        """ Returns the maximum amount of energy the unit can have. Returns 0 for units without energy. """
        return self._proto.energy_max

    @property_immutable_cache
    def energy_percentage(self) -> Union[int, float]:
        """ Returns the percentage of amount of energy the unit has. Returns 0 for units without energy. """
        if self._proto.energy_max == 0:
            return 0
        return self._proto.energy / self._proto.energy_max

    @property_immutable_cache
    def is_snapshot(self) -> bool:
        """ Checks if the unit is only available as a snapshot for the bot.
        Enemy buildings that have been scouted and are in the fog of war or
        attacking enemy units on higher, not visible ground appear this way. """
        return self._proto.display_type == DisplayType.Snapshot.value

    @property_immutable_cache
    def is_visible(self) -> bool:
        """ Checks if the unit is visible for the bot.
        NOTE: This means the bot has vision of the position of the unit!
        It does not give any information about the cloak status of the unit."""
        return self._proto.display_type == DisplayType.Visible.value

    @property_immutable_cache
    def alliance(self) -> Alliance:
        """ Returns the team the unit belongs to. """
        return self._proto.alliance

    @property_immutable_cache
    def is_mine(self) -> bool:
        """ Checks if the unit is controlled by the bot. """
        return self._proto.alliance == Alliance.Self.value

    @property_immutable_cache
    def is_enemy(self) -> bool:
        """ Checks if the unit is hostile. """
        return self._proto.alliance == Alliance.Enemy.value

    @property_immutable_cache
    def owner_id(self) -> int:
        """ Returns the owner of the unit. """
        return self._proto.owner

    @property_immutable_cache
    def position(self) -> Point2:
        """ Returns the 2d position of the unit. """
        return Point2.from_proto(self._proto.pos)

    @property_immutable_cache
    def position3d(self) -> Point3:
        """ Returns the 3d position of the unit. """
        return Point3.from_proto(self._proto.pos)

    def distance_to(self, p: Union["Unit", Point2, Point3]) -> Union[int, float]:
        """ Using the 2d distance between self and p.
        To calculate the 3d distance, use unit.position3d.distance_to(p) """
        return self.position.distance_to_point2(p.position)

    @property_immutable_cache
    def facing(self) -> Union[int, float]:
        """ Returns direction the unit is facing as a float in range [0,2π). 0 is in direction of x axis."""
        return self._proto.facing

    @property_immutable_cache
    def radius(self) -> Union[int, float]:
        """ Half of unit size. See https://liquipedia.net/starcraft2/Unit_Statistics_(Legacy_of_the_Void) """
        return self._proto.radius

    @property_immutable_cache
    def build_progress(self) -> Union[int, float]:
        """ Returns completion in range [0,1]."""
        return self._proto.build_progress

    @property_immutable_cache
    def is_ready(self) -> bool:
        """ Checks if the unit is completed. """
        return self.build_progress == 1

    @property_immutable_cache
    def cloak(self) -> CloakState:
        """ Returns cloak state.
        See https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_unit.h#L95 """
        return self._proto.cloak

    @property_immutable_cache
    def is_cloaked(self) -> bool:
        """ Checks if the unit is cloaked. """
        return self._proto.cloak in {
            CloakState.Cloaked.value,
            CloakState.CloakedDetected.value,
            CloakState.CloakedAllied.value,
        }

    @property_immutable_cache
    def is_revealed(self) -> bool:
        """ Checks if the unit is revealed. """
        return self._proto.cloak is CloakState.CloakedDetected.value

    @property_immutable_cache
    def can_be_attacked(self) -> bool:
        """ Checks if the unit is revealed or not cloaked and therefore can be attacked """
        return self._proto.cloak in {CloakState.NotCloaked.value, CloakState.CloakedDetected.value}

    @property_immutable_cache
    def buffs(self) -> Set:
        """ Returns the set of current buffs the unit has. """
        return {BuffId(buff_id) for buff_id in self._proto.buff_ids}

    @property_immutable_cache
    def is_carrying_minerals(self) -> bool:
        """ Checks if a worker or MULE is carrying (gold-)minerals. """
        return not {BuffId.CARRYMINERALFIELDMINERALS, BuffId.CARRYHIGHYIELDMINERALFIELDMINERALS}.isdisjoint(self.buffs)

    @property_immutable_cache
    def is_carrying_vespene(self) -> bool:
        """ Checks if a worker is carrying vespene gas. """
        return not {
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGAS,
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGASPROTOSS,
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGASZERG,
        }.isdisjoint(self.buffs)

    @property_immutable_cache
    def is_carrying_resource(self) -> bool:
        """ Checks if a worker is carrying a resource. """
        return not {
            BuffId.CARRYMINERALFIELDMINERALS,
            BuffId.CARRYHIGHYIELDMINERALFIELDMINERALS,
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGAS,
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGASPROTOSS,
            BuffId.CARRYHARVESTABLEVESPENEGEYSERGASZERG,
        }.isdisjoint(self.buffs)

    @property_immutable_cache
    def detect_range(self) -> Union[int, float]:
        """ Returns the detection distance of the unit. """
        return self._proto.detect_range

    @property_immutable_cache
    def radar_range(self) -> Union[int, float]:
        return self._proto.radar_range

    @property_immutable_cache
    def is_selected(self) -> bool:
        """ Checks if the unit is currently selected. """
        return self._proto.is_selected

    @property_immutable_cache
    def is_on_screen(self) -> bool:
        """ Checks if the unit is on the screen. """
        return self._proto.is_on_screen

    @property_immutable_cache
    def is_blip(self) -> bool:
        """ Checks if the unit is detected by a sensor tower. """
        return self._proto.is_blip

    @property_immutable_cache
    def is_powered(self) -> bool:
        """ Checks if the unit is powered by a pylon or warppism. """
        return self._proto.is_powered

    @property_immutable_cache
    def is_active(self) -> bool:
        """ Checks if the unit is currently training or researching. """
        return self._proto.is_active

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR SNAPSHOTS

    @property_immutable_cache
    def mineral_contents(self) -> int:
        """ Returns the amount of minerals rmaining in a mineral field. """
        return self._proto.mineral_contents

    @property_immutable_cache
    def vespene_contents(self) -> int:
        """ Returns the amount of gas remaining in a geyser. """
        return self._proto.vespene_contents

    @property_immutable_cache
    def has_vespene(self) -> bool:
        """ Checks if a geyser has any gas remaining.
        You can't build extractors on empty geysers. """
        return bool(self._proto.vespene_contents)

    @property_immutable_cache
    def is_flying(self) -> bool:
        """ Checks if the unit is flying. """
        return self._proto.is_flying

    @property_immutable_cache
    def is_burrowed(self) -> bool:
        """ Checks if the unit is burrowed. """
        return self._proto.is_burrowed

    @property_immutable_cache
    def is_hallucination(self) -> bool:
        """ Returns True if the unit is your own hallucination or detected. """
        return self._proto.is_hallucination

    @property_immutable_cache
    def attack_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units attack. """
        # TODO: what does this return for units without a weapon?
        # TODO: somehow store all weapon/armor/shield upgrades of the enemy to
        # always have it available and update if you see a higher value
        return self._proto.attack_upgrade_level

    @property_immutable_cache
    def armor_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units armor. """
        return self._proto.armor_upgrade_level

    @property_immutable_cache
    def shield_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units shield. """
        # TODO: what does this return for units without a shield?
        return self._proto.shield_upgrade_level

    @property_immutable_cache
    def buff_duration_remain(self) -> int:
        """ ??? """
        # TODO what does this actually show?
        # is it for all buffs or just the remaning life time indicator
        # TODO what does this and the max value show for units without an indicator?
        return self._proto.buff_duration_remain

    @property_immutable_cache
    def buff_duration_max(self) -> int:
        """ ??? """
        # TODO what does this actually show?
        # is it for all buffs or just the remaning life time indicator
        # TODO what does this show for units without an indicator?
        return self._proto.buff_duration_max

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR ENEMIES

    @property_mutable_cache
    def orders(self) -> List[UnitOrder]:
        """ Returns the a list of the current orders. """
        return [UnitOrder.from_proto(order) for order in self._proto.orders]

    @property_immutable_cache
    def order_target(self) -> Optional[Union[int, Point2]]:
        """ Returns the target tag (if it is a Unit) or Point2 (if it is a Position)
        from the first order, returns None if the unit is idle """
        if self.orders:
            if isinstance(self.orders[0].target, int):
                return self.orders[0].target
            else:
                return Point2.from_proto(self.orders[0].target)
        return None

    @property_immutable_cache
    def noqueue(self) -> bool:
        """ Checks if the unit is idle. """
        warnings.warn("noqueue will be removed soon, please use is_idle instead", DeprecationWarning, stacklevel=2)
        return self.is_idle

    @property_immutable_cache
    def is_idle(self) -> bool:
        """ Checks if unit is idle. """
        return not self.orders

    def is_using_ability(self, abilities: Union[AbilityId, Set[AbilityId]]) -> bool:
        """ Check if the unit is using one of the given abilities.
        Only works for own units. """
        if not self.orders:
            return False
        if isinstance(abilities, AbilityId):
            abilities = {abilities}
        return self.orders[0].ability.id in abilities

    @property_immutable_cache
    def is_moving(self) -> bool:
        """ Checks if the unit is moving.
        Only works for own units. """
        return self.is_using_ability(AbilityId.MOVE)

    @property_immutable_cache
    def is_attacking(self) -> bool:
        """ Checks if the unit is attacking.
        Only works for own units. """
        return self.is_using_ability(
            {
                AbilityId.ATTACK,
                AbilityId.ATTACK_ATTACK,
                AbilityId.ATTACK_ATTACKTOWARDS,
                AbilityId.ATTACK_ATTACKBARRAGE,
                AbilityId.SCAN_MOVE,
            }
        )

    @property_immutable_cache
    def is_patrolling(self) -> bool:
        """ Checks if a unit is patrolling.
        Only works for own units. """
        return self.is_using_ability(AbilityId.PATROL)

    @property_immutable_cache
    def is_gathering(self) -> bool:
        """ Checks if a unit is on its way to a mineral field or vespene geyser to mine.
        Only works for own units. """
        return self.is_using_ability(AbilityId.HARVEST_GATHER)

    @property_immutable_cache
    def is_returning(self) -> bool:
        """ Checks if a unit is returning from mineral field or vespene geyser to deliver resources to townhall.
        Only works for own units. """
        return self.is_using_ability(AbilityId.HARVEST_RETURN)

    @property_immutable_cache
    def is_collecting(self) -> bool:
        """ Checks if a unit is gathering or returning.
        Only works for own units. """
        return self.is_using_ability({AbilityId.HARVEST_GATHER, AbilityId.HARVEST_RETURN})

    @property_immutable_cache
    def is_constructing_scv(self) -> bool:
        """ Checks if the unit is an SCV that is currently building.
        Only works for own units. """
        return self.is_using_ability(
            {
                AbilityId.TERRANBUILD_ARMORY,
                AbilityId.TERRANBUILD_BARRACKS,
                AbilityId.TERRANBUILD_BUNKER,
                AbilityId.TERRANBUILD_COMMANDCENTER,
                AbilityId.TERRANBUILD_ENGINEERINGBAY,
                AbilityId.TERRANBUILD_FACTORY,
                AbilityId.TERRANBUILD_FUSIONCORE,
                AbilityId.TERRANBUILD_GHOSTACADEMY,
                AbilityId.TERRANBUILD_MISSILETURRET,
                AbilityId.TERRANBUILD_REFINERY,
                AbilityId.TERRANBUILD_SENSORTOWER,
                AbilityId.TERRANBUILD_STARPORT,
                AbilityId.TERRANBUILD_SUPPLYDEPOT,
            }
        )

    @property_immutable_cache
    def is_transforming(self) -> bool:
        """ Checks if the unit transforming.
        Only works for own units. """
        return self.type_id in transforming and self.is_using_ability(transforming[self.type_id])

    @property_immutable_cache
    def is_repairing(self) -> bool:
        """ Checks if the unit is an SCV or MULE that is currently repairing.
        Only works for own units. """
        return self.is_using_ability(
            {AbilityId.EFFECT_REPAIR, AbilityId.EFFECT_REPAIR_MULE, AbilityId.EFFECT_REPAIR_SCV}
        )

    @property_immutable_cache
    def add_on_tag(self) -> int:
        """ Returns the tag of the addon of unit. """
        return self._proto.add_on_tag

    @property_immutable_cache
    def has_add_on(self) -> bool:
        """ Checks if unit has an addon attached. """
        return bool(self.add_on_tag)

    @property_immutable_cache
    def add_on_land_position(self) -> Point2:
        """ If unit is addon (techlab or reactor), returns the position
        where a terran building has to land to connect to addon """
        return self.position.offset(Point2((-2.5, 0.5)))

    @property_mutable_cache
    def passengers(self) -> Set["Unit"]:
        """ Returns the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism. """
        return {Unit(unit) for unit in self._proto.passengers}

    @property_mutable_cache
    def passengers_tags(self) -> Set[int]:
        """ Returns the tags of the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism. """
        return {unit.tag for unit in self._proto.passengers}

    @property_immutable_cache
    def cargo_used(self) -> Union[float, int]:
        """ Returns how much cargo space is currently used in the unit.
        Note that some units take up more than one space. """
        return self._proto.cargo_space_taken

    @property_immutable_cache
    def has_cargo(self) -> bool:
        """ Checks if this unit has any units loaded. """
        return bool(self._proto.cargo_space_taken)

    @property
    def cargo_size(self) -> Union[float, int]:
        """ Returns the amount of cargo space the unit needs. """
        return self._type_data.cargo_size

    @property_immutable_cache
    def cargo_max(self) -> Union[float, int]:
        """ How much cargo space is available at maximum. """
        return self._proto.cargo_space_max

    @property_immutable_cache
    def cargo_left(self) -> Union[float, int]:
        """ Returns how much cargo space is currently left in the unit. """
        return self._proto.cargo_space_max - self._proto.cargo_space_taken

    @property_immutable_cache
    def assigned_harvesters(self) -> int:
        """ Returns the number of workers currently gathering resources at a geyser or mining base."""
        return self._proto.assigned_harvesters

    @property_immutable_cache
    def ideal_harvesters(self) -> int:
        """ Returns the ideal harverster count for unit.
        3 for geysers, 2*n for n mineral patches on that base."""
        return self._proto.ideal_harvesters

    @property_immutable_cache
    def surplus_harvesters(self) -> int:
        """ Returns a positive int if unit has too many harvesters mining,
        a negative int if it has too few mining."""
        return self._proto.assigned_harvesters - self._proto.ideal_harvesters

    @property_immutable_cache
    def weapon_cooldown(self) -> Union[int, float]:
        """ Returns the time until the unit can fire again,
        returns -1 for units that can't attack.
        Usage:
        if unit.weapon_cooldown == 0:
            self.actions.append(unit.attack(target))
        elif unit.weapon_cooldown < 0:
            self.actions.append(unit.move(closest_allied_unit_because_cant_attack))
        else:
            self.actions.append(unit.move(retreatPosition))
        """
        if self.can_attack:
            return self._proto.weapon_cooldown
        return -1

    @property_immutable_cache
    def engaged_target_tag(self) -> int:
        # TODO What does this do?
        return self._proto.engaged_target_tag

    @property_immutable_cache
    def is_detector(self) -> bool:
        """ Checks if the unit is a detector. Has to be completed
        in order to detect and Photoncannons also need to be powered. """
        return self.is_ready and (
            self.type_id
            in {
                UnitTypeId.OBSERVER,
                UnitTypeId.OBSERVERSIEGEMODE,
                UnitTypeId.RAVEN,
                UnitTypeId.MISSILETURRET,
                UnitTypeId.OVERSEER,
                UnitTypeId.OVERSEERSIEGEMODE,
                UnitTypeId.SPORECRAWLER,
            }
            or self.type_id == UnitTypeId.PHOTONCANNON
            and self.is_powered
        )

    # Unit functions

    def target_in_range(self, target: "Unit", bonus_distance: Union[int, float] = 0) -> bool:
        """ Checks if the target is in range.
        Includes the target's radius when calculating distance to target. """
        if self.can_attack_ground and not target.is_flying:
            unit_attack_range = self.ground_range
        elif self.can_attack_air and (target.is_flying or target.type_id == UnitTypeId.COLOSSUS):
            unit_attack_range = self.air_range
        else:
            return False
        return self.distance_to(target) <= self.radius + target.radius + unit_attack_range + bonus_distance

    def has_buff(self, buff) -> bool:
        """ Checks if unit has buff 'buff'. """
        assert isinstance(buff, BuffId), f"{buff} is no BuffId"
        return buff in self.buffs

    def train(self, unit, queue=False) -> UnitOrder:
        """ Orders unit to train another 'unit'.
        Usage: self.actions.append(COMMANDCENTER.train(SCV)) """
        return self(UnitGameData._game_data.units[unit.value].creation_ability.id, queue=queue)

    def build(self, unit, position=None, queue=False) -> UnitOrder:
        """ Orders unit to build another 'unit' at 'position'.
        Usage: self.actions.append(SCV.build(COMMANDCENTER, position)) """
        return self(UnitGameData._game_data.units[unit.value].creation_ability.id, target=position, queue=queue)

    def research(self, upgrade, queue=False) -> UnitOrder:
        """ Orders unit to research 'upgrade'.
        Requires UpgradeId to be passed instead of AbilityId. """
        return self(UnitGameData._game_data.upgrades[upgrade.value].research_ability.id, queue=queue)

    def warp_in(self, unit, position) -> UnitOrder:
        """ Orders Warpgate to warp in 'unit' at 'position'. """
        normal_creation_ability = UnitGameData._game_data.units[unit.value].creation_ability.id
        return self(warpgate_abilities[normal_creation_ability], target=position)

    def attack(self, target, queue=False) -> UnitOrder:
        """ Orders unit to attack. Target can be a Unit or Point2.
        Attacking a position will make the unit move there and attack everything on its way. """
        return self(AbilityId.ATTACK, target=target, queue=queue)

    def gather(self, target, queue=False) -> UnitOrder:
        """ Orders a unit to gather minerals or gas.
        'Target' must be a mineral patch or a gas extraction building. """
        return self(AbilityId.HARVEST_GATHER, target=target, queue=queue)

    def return_resource(self, target=None, queue=False) -> UnitOrder:
        """ Orders the unit to return resource. Does not need a 'target'. """
        return self(AbilityId.HARVEST_RETURN, target=target, queue=queue)

    def move(self, position, queue=False) -> UnitOrder:
        """ Orders the unit to move to 'position'.
        Target can be a Unit (to follow that unit) or Point2. """
        return self(AbilityId.MOVE, target=position, queue=queue)

    def scan_move(self, *args, **kwargs) -> UnitOrder:
        """ TODO: What does this do? """
        return self(AbilityId.SCAN_MOVE, *args, **kwargs)

    def hold_position(self, queue=False) -> UnitOrder:
        """ Orders a unit to stop moving. It will not move until it gets new orders. """
        return self(AbilityId.HOLDPOSITION, queue=queue)

    def stop(self, queue=False) -> UnitOrder:
        """ Orders a unit to stop, but can start to move on its own
        if it is attacked, enemy unit is in range or other friendly
        units need the space. """
        return self(AbilityId.STOP, queue=queue)

    def patrol(self, position, queue=False) -> UnitOrder:
        """ Orders a unit to patrol between position it has when the command starts and the target position.
        Can be queued up to seven patrol points. If the last point is the same as the starting
        point, the unit will patrol in a circle. """
        return self(AbilityId.PATROL, target=position, queue=queue)

    def repair(self, repair_target, queue=False) -> UnitOrder:
        """ Order an SCV or MULE to repair. """
        return self(AbilityId.EFFECT_REPAIR, target=repair_target, queue=queue)

    def __hash__(self):
        return self.tag

    def __eq__(self, other):
        try:
            return self.tag == other.tag
        except:
            return False

    def __call__(self, ability, target=None, queue=False):
        return unit_command.UnitCommand(ability, self, target=target, queue=queue)

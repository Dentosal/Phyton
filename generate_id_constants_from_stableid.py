import json
from pathlib import Path
import platform

HEADER = f"# DO NOT EDIT!\n# This file was automatically generated by \"{__file__}\"\n"


PF = platform.system()

HOME_DIR = str(Path.home())
DATA_JSON = {
    "Darwin": HOME_DIR + "/Library/Application Support/Blizzard/StarCraft II/stableid.json",
    "Windows": HOME_DIR + "/Documents/StarCraft II/stableid.json"
}

ENUM_TRANSLATE = {
    "Units": "UnitTypeId",
    "Abilities": "AbilityId",
    "Upgrades": "UpgradeId",
    "Buffs": "BuffId",
    "Effects": "EffectId"
}

FILE_TRANSLATE = {
    "Units": "unit_typeid",
    "Abilities": "ability_id",
    "Upgrades": "upgrade_id",
    "Buffs": "buff_id",
    "Effects": "effect_id"
}


def clike_enum_parse(data):
    enums = {}
    for d in data:  # Units, Abilities, Upgrades, Buffs, Effects
        body = {}
        for v in data[d]:
            key = v['name']
            if not key:
                continue
            if key[0].isdigit():
                key = "_" + key

            key = key.upper().replace(" ", "_")

            if 'index' in v and v['index'] > 0:
                continue

            # it looks like SC2 is only using abilities with index 0. Needs further verification.
            body[key] = v['id']
        enums[d] = body

    enums['Abilities']['SMART'] = 1
    return enums


def generate_python_code(enums):
    assert {"Units", "Abilities", "Upgrades", "Buffs", "Effects"} <= enums.keys()

    sc2dir = Path("sc2/")
    idsdir = (sc2dir / "ids")
    idsdir.mkdir(exist_ok=True)

    with (idsdir / "__init__.py").open("w") as f:
        f.write("\n".join([
            HEADER,
            f"__all__ = {[n.lower() for n in enums.keys()] !r}\n"
        ]))

    for name, body in enums.items():
        class_name = ENUM_TRANSLATE[name]

        code = [
            HEADER,
            "import enum",
            "",
            f"class {class_name}(enum.Enum):"
        ]

        for key, value in sorted(body.items(), key=lambda p: p[1]):

            code.append(f"    {key} = {value}")

        code += [
            "",
            f"for item in {class_name}:",
            f"    globals()[item.name] = item",
            ""
        ]

        with (idsdir / FILE_TRANSLATE[name]).with_suffix(".py").open("w") as f:
            f.write("\n".join(code))


if __name__ == '__main__':
    with open(DATA_JSON[PF], encoding='utf-8') as data_file:
        data = json.loads(data_file.read())
        generate_python_code(clike_enum_parse(data))

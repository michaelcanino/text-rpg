import os
import platform
import json
import random
import copy
from models import Player, Potion, OffensiveItem, EffectPotion, Skill, ActiveAbility, PlayerClass

__all__ = [
    'LevelUpManager', 'LevelUpChoice', 'SkillTreeManager', 'ClassManager',
    'save_game', 'load_player_from_save',
    'select_from_menu', 'display_menu_and_state', 'get_available_actions', 'clear_screen'
]

class LevelUpChoice:
    def __init__(self, id, text, apply_effect):
        self.id = id
        self.name = text
        self.text = text
        self.apply_effect = apply_effect

class LevelUpManager:
    def __init__(self):
        pass

    def _get_levelup_choices(self, player):
        choices = [
            LevelUpChoice(
                id="hp",
                text="Increase Max HP by 10",
                apply_effect=lambda p: setattr(p, 'base_max_hp', p.base_max_hp + 10)
            ),
            LevelUpChoice(
                id="attack",
                text="Increase Attack Power by 2",
                apply_effect=lambda p: setattr(p, 'base_attack_power', p.base_attack_power + 2)
            ),
            LevelUpChoice(
                id="crit",
                text="Increase Critical Chance by 5%",
                apply_effect=lambda p: setattr(p, 'base_critical_chance', p.base_critical_chance + 0.05)
            )
        ]
        return choices

    def present_levelup_choices(self, player, skill_tree_manager, class_manager):
        level_up_message = f"You are now level {player.level}! You have {player.skill_points} skill point(s)."

        clear_screen()
        print("=" * 50)
        print(f"| {player.name:<10} | Lvl: {player.level:<2} | HP: {player.hp:<3}/{player.max_hp:<3} | XP: {player.xp:<4}/{player.xp_to_next_level:<4} |")
        print(f"| Location: {player.current_location.name:<37} |")
        print("=" * 50)
        print(f"\n{level_up_message}\n")

        level_up_choices = self._get_levelup_choices(player)
        chosen_upgrade = select_from_menu("Choose your upgrade:", level_up_choices)

        if chosen_upgrade:
            chosen_upgrade.apply_effect(player)
            player.skill_points -= 1
            player.recalculate_stats(skill_tree_manager, class_manager)
            return f"You chose: {chosen_upgrade.text}. Your power grows!"
        else:
            return "You decided to save your skill point for later."

class SkillTreeManager:
    def __init__(self, skills_data):
        self.skills = {}
        for skill_id, data in skills_data.items():
            data['skill_type'] = data.pop('type')
            self.skills[skill_id] = Skill(id=skill_id, **data)

    def get_available_skills(self, player, class_manager):
        available = []
        skill_pool = set(self.skills.keys())
        if player.class_id:
            player_class = class_manager.classes.get(player.class_id)
            if player_class:
                general_skills = {sid for sid, s in self.skills.items() if not any(sid in c.skill_pool for c in class_manager.classes.values())}
                skill_pool = general_skills.union(set(player_class.skill_pool))

        for skill_id in skill_pool:
            skill = self.skills.get(skill_id)
            if not skill or skill_id in player.unlocked_skills:
                continue

            reqs_met = True
            for req in skill.requirements:
                if req['type'] == 'level' and player.level < req['value']:
                    reqs_met = False
                    break
                if req['type'] == 'skill' and req['id'] not in player.unlocked_skills:
                    reqs_met = False
                    break

            if reqs_met:
                available.append(skill)
        return available

    def unlock_skill(self, player, skill_id, class_manager, free=False):
        if skill_id not in self.skills:
            return "Skill not found."

        skill = self.skills[skill_id]

        if skill_id in player.unlocked_skills:
            return "You have already unlocked this skill."

        if not free and player.skill_points < skill.cost:
            return "You don't have enough skill points."

        for req in skill.requirements:
            if req['type'] == 'level' and player.level < req['value']:
                return f"You do not meet the level requirement of {req['value']}."
            if req['type'] == 'skill' and req['id'] not in player.unlocked_skills:
                required_skill = self.skills.get(req['id'])
                return f"You need to unlock '{required_skill.name if required_skill else req['id']}' first."

        if not free:
            player.skill_points -= skill.cost
        player.unlocked_skills.append(skill_id)

        if skill.skill_type == 'active':
            player.active_abilities.append(ActiveAbility(skill))

        return f"You have unlocked: {skill.name}!"

class ClassManager:
    def __init__(self, classes_data):
        self.classes = {class_id: PlayerClass(id=class_id, **data) for class_id, data in classes_data.items()}

def save_game(player):
    """Saves the player's current state to a JSON file."""
    save_data = {
        "name": player.name, "hp": player.hp,
        "base_max_hp": player.base_max_hp, "base_attack_power": player.base_attack_power,
        "base_critical_chance": player.base_critical_chance,
        "current_location_id": player.current_location.id,
        "inventory_ids": [item.id for item in player.inventory],
        "quests": player.quests, "discovered_locations": list(player.discovered_locations),
        "level": player.level, "xp": player.xp, "xp_to_next_level": player.xp_to_next_level,
        "skill_points": player.skill_points, "unlocked_skills": player.unlocked_skills,
        "class_id": player.class_id
    }
    with open("save_data.json", 'w') as f:
        json.dump(save_data, f, indent=2)
    print("Your progress has been saved.")

def load_player_from_save(save_data, all_locations, all_items, skill_tree_manager, class_manager):
    """Creates a player object from save data."""
    start_location = all_locations[save_data["current_location_id"]]
    # Use .get for backward compatibility with saves that don't have base stats
    base_hp = save_data.get("base_max_hp", save_data.get("hp", 20))
    base_attack = save_data.get("base_attack_power", save_data.get("attack_power", 5))
    base_crit = save_data.get("base_critical_chance", 0.0)

    player = Player(
        "player",
        save_data["name"],
        start_location,
        save_data["hp"],
        base_hp,
        base_attack
    )
    player.base_critical_chance = base_crit

    player.inventory = [copy.deepcopy(all_items[item_id]) for item_id in save_data["inventory_ids"]]
    player.quests = save_data.get("quests", {})
    player.discovered_locations = set(save_data.get("discovered_locations", [start_location.id]))
    player.level = save_data.get("level", 1)
    player.xp = save_data.get("xp", 0)
    player.xp_to_next_level = save_data.get("xp_to_next_level", 100)
    player.skill_points = save_data.get("skill_points", 0)
    player.unlocked_skills = save_data.get("unlocked_skills", [])
    player.class_id = save_data.get("class_id")

    player.recalculate_stats(skill_tree_manager, class_manager)
    for skill_id in player.unlocked_skills:
        skill = skill_tree_manager.skills.get(skill_id)
        if skill and skill.skill_type == 'active':
            player.active_abilities.append(ActiveAbility(skill))

    player.hp = min(player.hp, player.max_hp)

    return player

def clear_screen():
    """Clears the console screen."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def select_from_menu(prompt, options, display_key='name'):
    """Displays a numbered menu of options and returns the selected option or None."""
    print(prompt)
    for i, option in enumerate(options):
        print(f"  {i + 1}. {getattr(option, display_key)}")
    print(f"  {len(options) + 1}. Cancel")

    while True:
        choice = input("> ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(options):
                return options[choice_index]
            elif choice_index == len(options):
                return None
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def display_menu_and_state(player, message, actions, game_mode, class_manager):
    """Clears the screen, displays player status, a message, and a numbered action menu."""
    clear_screen()

    class_name = class_manager.classes[player.class_id].name if player.class_id else "None"
    print("=" * 50)
    print(f"| {player.name:<10} | Lvl: {player.level:<2} | HP: {player.hp:<3}/{player.max_hp:<3} | XP: {player.xp:<4}/{player.xp_to_next_level:<4} |")
    print(f"| Class: {class_name:<10} | Location: {player.current_location.name:<22} |")
    print("=" * 50)

    print(f"\n{message}\n")

    print("-" * 40)
    print("What do you do?")
    for i, action in enumerate(actions):
        print(f"  {i + 1}. {action['text']}")
    print("-" * 40)

def get_available_actions(player, game_mode, menus, all_locations):
    """Generates a list of available actions for the player based on JSON menu definitions."""
    actions = []
    menu_definitions = menus.get(game_mode, []) + menus.get("always", [])

    for definition in menu_definitions:
        if "iterate" not in definition and "condition" not in definition:
            actions.append(definition.copy())
            continue

        if "condition" in definition and "iterate" not in definition:
            if definition["condition"] == "player.inventory" and not player.inventory:
                continue
            if definition["condition"] == "has_usable_item" and not any(isinstance(item, (Potion, OffensiveItem, EffectPotion)) for item in player.inventory):
                continue
            actions.append(definition.copy())

        if "iterate" in definition:
            iterator_key = definition["iterate"]
            source_list = []
            if iterator_key == "location.exits":
                source_list = player.current_location.exits.items()
            elif iterator_key == "location.npcs":
                source_list = player.current_location.npcs
            elif iterator_key == "location.items":
                source_list = player.current_location.items
            elif iterator_key == "player.inventory":
                source_list = player.inventory
            elif iterator_key == "location.monsters":
                source_list = player.current_location.monsters

            for it in source_list:
                if "condition" in definition:
                    if definition["condition"] == "is_potion" and not isinstance(it, (Potion, EffectPotion)):
                        continue
                    if definition["condition"] == "is_usable_in_combat" and not isinstance(it, (Potion, OffensiveItem, EffectPotion)):
                        continue

                action = definition.copy()
                if iterator_key == "location.exits":
                    direction, dest = it
                    action['text'] = definition["text"].format(direction=direction, destination=dest)
                    action['command'] = definition["command"].format(direction=direction)
                else:
                    # Generic formatter for npc, item, monster, etc.
                    key_name = iterator_key.split('.')[-1][:-1]
                    if iterator_key == "player.inventory":
                        key_name = "item"
                    action['text'] = definition["text"].format(**{key_name: it})
                    action['command'] = definition["command"].format(**{key_name: it})

                actions.append(action)

    for c_exit in player.current_location.conditional_exits:
        if player.check_conditions(c_exit.conditions):
            actions.append({
                "text": f"Go {c_exit.direction} -> {c_exit.destination.name}",
                "command": f"go {c_exit.direction}",
            })

    if game_mode == "combat":
        for ability in player.active_abilities:
            cooldown_text = f" (CD: {ability.cooldown})" if ability.cooldown > 0 else ""
            actions.append({
                "text": f"Use Ability: {ability.name}{cooldown_text}",
                "command": f"ability {ability.id}"
            })

    return actions

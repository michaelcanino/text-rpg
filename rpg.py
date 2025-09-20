class Character:
    def __init__(self, id, name, hp=0, attack_power=0, inventory=None):
        self.id = id
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack_power = attack_power
        self.inventory = inventory if inventory is not None else []

    def is_alive(self):
        return self.hp > 0

class NPC(Character):
    def __init__(self, id, name, dialogue, hp=0, attack_power=0, inventory=None, gives_items_on_talk=None, healing_dialogue=None):
        super().__init__(id, name, hp, attack_power, inventory)
        self.dialogue = dialogue
        self.gives_items_on_talk = gives_items_on_talk if gives_items_on_talk is not None else []
        self.healing_dialogue = healing_dialogue

class Monster(Character):
    def __init__(self, id, name, monster_type, hp, attack_power, drops=None, completes_quest_id=None, xp_reward=0):
        super().__init__(id, name, hp, attack_power)
        self.monster_type = monster_type
        self.drops = drops if drops is not None else []
        self.completes_quest_id = completes_quest_id
        self.xp_reward = xp_reward

class Item:
    def __init__(self, id, name, description, value=0):
        self.id = id
        self.name = name
        self.description = description
        self.value = value

    def use(self, target):
        return f"You can't use {self.name}."

class Potion(Item):
    def __init__(self, id, name, description, value, heal_amount):
        super().__init__(id, name, description, value)
        self.heal_amount = heal_amount

    def use(self, target):
        heal_amount = self.heal_amount
        old_hp = target.hp
        target.hp = min(target.hp + heal_amount, target.max_hp)
        healed_for = target.hp - old_hp
        if healed_for > 0:
            return f"{target.name} uses the {self.name} and heals for {healed_for} HP. (HP: {target.hp}/{target.max_hp})"
        else:
            return f"{target.name} uses the {self.name}, but their health is already full."

class EffectPotion(Item):
    def __init__(self, id, name, description, value, effect, duration):
        super().__init__(id, name, description, value)
        self.effect = effect
        self.duration = duration

    def use(self, target):
        # Effects are dictionaries on the player, e.g. {'fire_resistance': 5}
        target.status_effects[self.effect] = self.duration
        return f"{target.name} uses the {self.name}. You feel a strange energy course through you."

class OffensiveItem(Item):
    def __init__(self, id, name, description, value, damage_amount):
        super().__init__(id, name, description, value)
        self.damage_amount = damage_amount

    def use(self, target):
        target.hp -= self.damage_amount
        return f"You use the {self.name} on {target.name}, dealing {self.damage_amount} damage!"

class Container(Item):
    def __init__(self, id, name, description, value, contained_items=None):
        super().__init__(id, name, description, value)
        self.contained_items = contained_items if contained_items is not None else []

    def use(self, target_player):
        if not self.contained_items:
            return f"You open the {self.name}, but it's empty."

        message = f"You open the {self.name} and find:\n"
        for item in self.contained_items:
            target_player.inventory.append(item)
            message += f"- {item.name}\n"

        self.contained_items = []
        return message

class Location:
    def __init__(self, id, name, description, exits=None, npcs=None, monsters=None, items=None, spawns_on_defeat=None):
        self.id = id
        self.name = name
        self.description = description
        self.exits = exits if exits is not None else {}
        self.npcs = npcs if npcs is not None else []
        self.monsters = monsters if monsters is not None else []
        self.items = items if items is not None else []
        self.conditional_exits = []
        self.spawns_on_defeat = spawns_on_defeat if spawns_on_defeat is not None else {}

    def describe(self, player):
        description = f"**{self.name}**\n"
        description += f"{self.description}\n"
        for c_exit in self.conditional_exits:
            if player.check_conditions(c_exit.conditions):
                description += c_exit.description + "\n"
        if self.npcs:
            description += "You see: " + ", ".join(npc.name for npc in self.npcs) + "\n"
        if self.monsters:
            description += "DANGER: " + ", ".join(monster.name for monster in self.monsters) + " is here!\n"
        if self.items:
            description += "On the ground: " + ", ".join(item.name for item in self.items) + "\n"
        return description

class CityLocation(Location):
    pass

class WildernessLocation(Location):
    def __init__(self, id, name, description, exits=None, npcs=None, monsters=None, items=None, spawns_on_defeat=None, spawn_chance=0.0):
        super().__init__(id, name, description, exits, npcs, monsters, items, spawns_on_defeat)
        self.spawn_chance = spawn_chance

class DungeonLocation(Location):
    def __init__(self, id, name, description, exits=None, npcs=None, monsters=None, items=None, spawns_on_defeat=None, hazard_description=""):
        super().__init__(id, name, description, exits, npcs, monsters, items, spawns_on_defeat)
        self.hazard_description = hazard_description

    def describe(self, player):
        base_description = super().describe(player)
        return base_description + self.hazard_description + "\n"

class SwampLocation(WildernessLocation):
    def __init__(self, id, name, description, exits=None, npcs=None, monsters=None, items=None, spawns_on_defeat=None, spawn_chance=0.0, hidden_description=""):
        super().__init__(id, name, description, exits, npcs, monsters, items, spawns_on_defeat, spawn_chance)
        self.hidden_description = hidden_description

    def describe(self, player):
        has_lantern = any(item.name == "Lantern" for item in player.inventory)
        if has_lantern:
            return super().describe(player)
        else:
            return self.hidden_description

class VolcanicLocation(WildernessLocation):
    pass

class Skill:
    def __init__(self, id, name, description, skill_type, cost, requirements, effect):
        self.id = id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.cost = cost
        self.requirements = requirements
        self.effect = effect

class ActiveAbility:
    def __init__(self, skill):
        self.id = skill.id
        self.name = skill.name
        self.effect = skill.effect
        self.cooldown = 0
        self.max_cooldown = skill.effect.get('combat_ability', {}).get("cooldown", 1)

class Player(Character):
    def __init__(self, id, name, current_location, hp=20, max_hp=20, attack_power=5):
        super().__init__(id, name, hp, attack_power)

        # Base stats that are not affected by temporary modifiers
        self.base_max_hp = max_hp
        self.base_attack_power = attack_power
        self.base_critical_chance = 0.0

        # Live stats that include modifiers
        self.max_hp = max_hp
        self.attack_power = attack_power
        self.critical_chance = 0.0

        self.current_location = current_location
        self.previous_location = current_location
        self.status_effects = {}
        self.quests = {}
        self.discovered_locations = set()
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.skill_points = 0
        self.unlocked_skills = []
        self.active_abilities = []
        self.class_id = None

    def move(self, direction):
        moved = False
        if direction in self.current_location.exits:
            self.previous_location = self.current_location
            self.current_location = self.current_location.exits[direction]
            moved = True
        else:
            # Check conditional exits
            for c_exit in self.current_location.conditional_exits:
                if c_exit.direction == direction:
                    if self.check_conditions(c_exit.conditions):
                        self.previous_location = self.current_location
                        self.current_location = c_exit.destination
                        moved = True
                        break

        if moved:
            self.discovered_locations.add(self.current_location.id)
            return True

        return False

    def retreat(self):
        self.current_location = self.previous_location

    def check_conditions(self, conditions):
        """Checks if the player meets a list of conditions."""
        for condition in conditions:
            if condition['type'] == 'has_item':
                if not any(item.id == condition['item_id'] for item in self.inventory):
                    return False
            elif condition['type'] == 'quest_completed':
                # Check the 'state' of the quest
                if self.quests.get(condition['quest_id'], {}).get('state') != 'completed':
                    return False
            elif condition['type'] == 'quest_active':
                quest = self.quests.get(condition['quest_id'])
                if not quest or quest.get('state') != 'active':
                    return False
            # Add other condition types here in the future
        return True

    def add_xp(self, amount):
        self.xp += amount
        leveled_up = False
        class_choice_pending = False
        message = f"You gain {amount} XP."
        while self.xp >= self.xp_to_next_level:
            leveled_up, class_choice_triggered = self.level_up()
            if class_choice_triggered:
                class_choice_pending = True
            message += f"\n**LEVEL UP!** You are now level {self.level}!"
        return message, leveled_up, class_choice_pending

    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
        self.base_max_hp += 5
        self.base_attack_power += 1
        self.skill_points += 1
        self.hp = self.max_hp # Fully heal on level up

        class_choice_triggered = self.level == 10 and self.class_id is None
        return True, class_choice_triggered

    def recalculate_stats(self, skill_tree_manager, class_manager):
        """Recalculates all player stats based on base stats, skills, and class."""
        # Reset to base stats, but use the live stat as the starting point
        # in case there are other temporary effects not from skills/class
        self.max_hp = self.base_max_hp
        self.attack_power = self.base_attack_power
        self.critical_chance = self.base_critical_chance

        # Apply class modifiers to the base
        if self.class_id:
            player_class = class_manager.classes.get(self.class_id)
            if player_class:
                for stat, value in player_class.base_mods.items():
                    # This modifies the live stat, not the base
                    setattr(self, stat, getattr(self, stat) + value)

        # Apply passive skill modifiers
        for skill_id in self.unlocked_skills:
            skill = skill_tree_manager.skills.get(skill_id)
            if skill and skill.skill_type == 'passive':
                for stat, mod in skill.effect.get('stat_mod', {}).items():
                    # This also modifies the live stat
                    setattr(self, stat, getattr(self, stat) + mod)

        # Ensure HP is not above the new max
        self.hp = min(self.hp, self.max_hp)

import os
import platform
import json


class AsciiMap:
    def __init__(self, all_locations, player):
        self.all_locations = all_locations
        self.player = player
        self.grid = {}
        self.min_x, self.max_x, self.min_y, self.max_y = 0, 0, 0, 0
        self._build_grid()

    def _build_grid(self):
        q = collections.deque([(self.player.current_location, 0, 0)])
        visited = {self.player.current_location.id}
        self.grid[(0, 0)] = self.player.current_location

        while q:
            loc, x, y = q.popleft()

            self.min_x = min(self.min_x, x)
            self.max_x = max(self.max_x, x)
            self.min_y = min(self.min_y, y)
            self.max_y = max(self.max_y, y)

            # Check both normal and conditional exits
            all_exits = {**loc.exits, **{c.direction: c.destination for c in loc.conditional_exits}}

            for direction, dest_loc in all_exits.items():
                if dest_loc and dest_loc.id not in visited:
                    nx, ny = x, y
                    if direction == 'north': ny -= 1
                    elif direction == 'south': ny += 1
                    elif direction == 'east':  nx += 1
                    elif direction == 'west':  nx -= 1

                    if (nx, ny) not in self.grid:
                        visited.add(dest_loc.id)
                        self.grid[(nx, ny)] = dest_loc
                        q.append((dest_loc, nx, ny))

    def generate(self):
        if not self.grid: return "Map data is not available."

        map_str = "\n--- World Map ---\n"

        offset_x = -self.min_x
        offset_y = -self.min_y
        width = self.max_x - self.min_x + 1
        height = self.max_y - self.min_y + 1

        char_grid = [[' ' for _ in range(width * 4)] for _ in range(height * 2)]

        for (x, y), loc in self.grid.items():
            gx, gy = (x + offset_x) * 4, (y + offset_y) * 2

            symbol = '?'
            if loc.id in self.player.discovered_locations:
                if loc.id == self.player.current_location.id:
                    symbol = 'P'
                elif isinstance(loc, CityLocation): symbol = 'C'
                elif isinstance(loc, DungeonLocation): symbol = 'D'
                elif isinstance(loc, WildernessLocation): symbol = 'W'
                else: symbol = 'R'

            char_grid[gy][gx:gx+3] = f"[{symbol}]"

            # Draw connections
            all_exits = {**loc.exits, **{c.direction: c.destination for c in loc.conditional_exits}}
            for direction, dest_loc in all_exits.items():
                if dest_loc:
                    for (nx, ny), neighbor_loc in self.grid.items():
                        if neighbor_loc.id == dest_loc.id:
                            # Draw connections only if the neighbor is also in the grid
                            if ny < y: # North
                                if char_grid[gy - 1][gx + 1] == ' ': char_grid[gy - 1][gx + 1] = '|'
                            elif ny > y: # South
                                if char_grid[gy + 1][gx + 1] == ' ': char_grid[gy + 1][gx + 1] = '|'
                            elif nx > x: # East
                                if char_grid[gy][gx + 3] == ' ': char_grid[gy][gx + 3] = '-'
                            elif nx < x: # West
                                if char_grid[gy][gx - 1] == ' ': char_grid[gy][gx - 1] = '-'
                            break

        for row in char_grid:
            map_str += "".join(row).rstrip() + "\n"

        map_str += "\n[P]layer, [C]ity, [W]ilderness, [D]ungeon, [R]oom, ? Undiscovered\n"
        return map_str


class LevelUpChoice:
    def __init__(self, id, text, apply_effect):
        self.id = id
        self.name = text # Use 'name' for display in menus
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

    def unlock_skill(self, player, skill_id, class_manager):
        if skill_id not in self.skills:
            return "Skill not found."

        skill = self.skills[skill_id]

        if skill_id in player.unlocked_skills:
            return "You have already unlocked this skill."

        if player.skill_points < skill.cost:
            return "You don't have enough skill points."

        for req in skill.requirements:
            if req['type'] == 'level' and player.level < req['value']:
                return f"You do not meet the level requirement of {req['value']}."
            if req['type'] == 'skill' and req['id'] not in player.unlocked_skills:
                required_skill = self.skills.get(req['id'])
                return f"You need to unlock '{required_skill.name if required_skill else req['id']}' first."

        player.skill_points -= skill.cost
        player.unlocked_skills.append(skill_id)

        if skill.skill_type == 'active':
            player.active_abilities.append(ActiveAbility(skill))

        return f"You have unlocked: {skill.name}!"

class ClassManager:
    def __init__(self, classes_data):
        self.classes = {class_id: PlayerClass(id=class_id, **data) for class_id, data in classes_data.items()}

import random
import copy
import collections

ConditionalExit = collections.namedtuple('ConditionalExit', ['direction', 'destination', 'description', 'conditions'])

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
                return None # Cancel
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

def get_available_actions(player, game_mode, menus):
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
                elif iterator_key == "location.npcs":
                    action['text'] = definition["text"].format(npc=it)
                    action['command'] = definition["command"].format(npc=it)
                elif iterator_key == "location.items":
                    action['text'] = definition["text"].format(item=it)
                    action['command'] = definition["command"].format(item=it)
                elif iterator_key == "player.inventory":
                    action['text'] = definition["text"].format(item=it)
                    action['command'] = definition["command"].format(item=it)
                elif iterator_key == "location.monsters":
                    action['text'] = definition["text"].format(monster=it)
                    action['command'] = definition["command"].format(monster=it)

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

def load_game_data(filepath):
    """Loads game data from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def load_world_from_data(game_data):
    """Creates all game objects from the normalized data and links them."""
    all_items = {}
    for item_id, item_data in game_data.get("items", {}).items():
        item_type = item_data.get("item_type", "Item")
        if item_type == "Potion":
            all_items[item_id] = Potion(item_id, item_data["name"], item_data["description"], item_data.get("value", 0), item_data.get("heal_amount", 0))
        elif item_type == "EffectPotion":
            all_items[item_id] = EffectPotion(item_id, item_data["name"], item_data["description"], item_data.get("value", 0), item_data.get("effect"), item_data.get("duration"))
        elif item_type == "Container":
            all_items[item_id] = Container(item_id, item_data["name"], item_data["description"], item_data.get("value", 0))
        elif item_type == "OffensiveItem":
            all_items[item_id] = OffensiveItem(item_id, item_data["name"], item_data["description"], item_data.get("value", 0), item_data.get("damage_amount", 0))
        else:
            all_items[item_id] = Item(item_id, item_data["name"], item_data["description"], item_data.get("value", 0))

    all_monsters = {}
    for monster_id, monster_data in game_data.get("monsters", {}).items():
        all_monsters[monster_id] = Monster(
            monster_id, monster_data["name"], monster_data["monster_type"],
            monster_data["hp"], monster_data["attack_power"],
            completes_quest_id=monster_data.get("completes_quest_id"),
            xp_reward=monster_data.get("xp_reward", 0)
        )

    all_npcs = {}
    for npc_id, npc_data in game_data.get("npcs", {}).items():
        all_npcs[npc_id] = NPC(
            npc_id, npc_data["name"], npc_data.get("dialogue", ""),
            npc_data["hp"], npc_data["attack_power"],
            gives_items_on_talk=npc_data.get("gives_items_on_talk"),
            healing_dialogue=npc_data.get("healing_dialogue")
        )

    all_locations = {}
    for loc_id, loc_data in game_data.get("locations", {}).items():
        loc_type = loc_data.get("location_type", "base")
        common_args = {
            "id": loc_id,
            "name": loc_data["name"],
            "description": loc_data["description"],
            "spawns_on_defeat": loc_data.get("spawns_on_defeat")
        }
        if loc_type == "City":
            all_locations[loc_id] = CityLocation(**common_args)
        elif loc_type == "Wilderness":
            all_locations[loc_id] = WildernessLocation(**common_args, spawn_chance=loc_data.get("spawn_chance", 0.0))
        elif loc_type == "Dungeon":
            all_locations[loc_id] = DungeonLocation(**common_args, hazard_description=loc_data.get("hazard_description", ""))
        elif loc_type == "Swamp":
            all_locations[loc_id] = SwampLocation(**common_args, spawn_chance=loc_data.get("spawn_chance", 0.0), hidden_description=loc_data.get("hidden_description", ""))
        elif loc_type == "Volcanic":
            all_locations[loc_id] = VolcanicLocation(**common_args, spawn_chance=loc_data.get("spawn_chance", 0.0))
        else:
            all_locations[loc_id] = Location(**common_args)

    for monster_id, monster_data in game_data.get("monsters", {}).items():
        monster = all_monsters[monster_id]
        monster.drops = [all_items[item_id] for item_id in monster_data.get("drop_ids", [])]

    for item_id, item_data in game_data.get("items", {}).items():
        if item_data.get("item_type") == "Container":
            container = all_items[item_id]
            container.contained_items = [all_items[i_id] for i_id in item_data.get("contained_item_ids", [])]

    monster_instance_counter = {}
    for loc_id, loc_data in game_data.get("locations", {}).items():
        location = all_locations[loc_id]
        location.exits = {direction: all_locations[dest_id] for direction, dest_id in loc_data.get("exits", {}).items()}
        location.npcs = [copy.deepcopy(all_npcs[npc_id]) for npc_id in loc_data.get("npc_ids", [])]
        location.monsters = []
        for monster_id in loc_data.get("monster_ids", []):
            proto_monster = all_monsters[monster_id]
            new_monster = copy.deepcopy(proto_monster)
            instance_count = monster_instance_counter.get(monster_id, 0)
            new_monster.id = f"{monster_id}:{instance_count}"
            monster_instance_counter[monster_id] = instance_count + 1
            location.monsters.append(new_monster)
        location.items = [all_items[item_id] for item_id in loc_data.get("item_ids", [])]
        location.conditional_exits = []
        for c_exit_data in loc_data.get("conditional_exits", []):
            destination_location = all_locations[c_exit_data['destination_id']]
            c_exit = ConditionalExit(direction=c_exit_data['direction'], destination=destination_location, description=c_exit_data['description'], conditions=c_exit_data['conditions'])
            location.conditional_exits.append(c_exit)

    player_data = game_data["player"]
    start_location = all_locations[player_data["start_location_id"]]
    inventory = [all_items[item_id] for item_id in player_data.get("inventory", [])]
    player = Player("player", player_data["name"], start_location, player_data["hp"], player_data.get("max_hp", player_data["hp"]), player_data["attack_power"])
    player.inventory = inventory
    player.quests = player_data.get("quests", {})
    player.discovered_locations.add(start_location.id)

    return player, game_data.get("menus", {}), all_locations, all_items, all_monsters

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
    player = Player("player", save_data["name"], start_location, save_data["hp"], save_data.get("base_max_hp", 20), save_data.get("base_attack_power", 5))
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

class PlayerClass:
    def __init__(self, id, name, short_description, base_mods, starting_skills, skill_pool):
        self.id = id
        self.name = name
        self.short_description = short_description
        self.base_mods = base_mods
        self.starting_skills = starting_skills
        self.skill_pool = skill_pool

def handle_class_choice(player, class_manager, skill_tree_manager):
    """Handles the UI and logic for the one-time class choice."""
    clear_screen()
    print("*" * 20)
    print("Time to Specialize!")
    print("*" * 20)
    print("\nYou have reached level 10! You must now choose a class.")
    print("This choice is permanent and will shape your future adventures.\n")

    choices = list(class_manager.classes.values())

    for i, p_class in enumerate(choices):
        print(f"--- {i+1}. {p_class.name} ---")
        print(f"  {p_class.short_description}")
        print("  Bonuses:")
        for stat, value in p_class.base_mods.items():
            current_stat = getattr(player, f"base_{stat}", getattr(player, stat))
            print(f"    - {stat.replace('_', ' ').title()}: {current_stat} -> {current_stat + value}")
        for skill_id in p_class.starting_skills:
            skill = skill_tree_manager.skills.get(skill_id)
            if skill:
                print(f"    - Starts with skill: {skill.name}")
        print()

    chosen_class = select_from_menu("Choose your path:", choices)

    if chosen_class:
        player.class_id = chosen_class.id
        for skill_id in chosen_class.starting_skills:
            skill_to_unlock = skill_tree_manager.skills.get(skill_id)
            if skill_to_unlock and skill_id not in player.unlocked_skills:
                player.skill_points += skill_to_unlock.cost
                skill_tree_manager.unlock_skill(player, skill_id, class_manager)

        player.recalculate_stats(skill_tree_manager, class_manager)

        return f"You have chosen the path of the {chosen_class.name}! Your journey continues."
    else:
        return handle_class_choice(player, class_manager, skill_tree_manager)


def main():
    game_data = load_game_data("game_data.json")
    _, menus, all_locations, all_items, all_monsters = load_world_from_data(game_data)
    skill_tree_manager = SkillTreeManager(game_data.get("skills", {}))
    class_manager = ClassManager(game_data.get("classes", {}))

    player = None
    if os.path.exists("save_data.json"):
        print("A previous voyage has been saved.")
        while True:
            choice = input("Would you like to (1) Continue or (2) Start a New Adventure? ")
            if choice == "1":
                with open("save_data.json", 'r') as f:
                    save_data = json.load(f)
                player = load_player_from_save(save_data, all_locations, all_items, skill_tree_manager, class_manager)
                print("Welcome back, brave adventurer!")
                break
            elif choice == "2":
                player, menus, all_locations, all_items, all_monsters = load_world_from_data(game_data)
                print("A new adventure begins!")
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    else:
        player, menus, all_locations, all_items, all_monsters = load_world_from_data(game_data)


    game_mode = "explore"
    previous_game_mode = "explore"
    message = player.current_location.describe(player)
    level_up_manager = LevelUpManager()

    while player.is_alive():
        if game_mode == "class_choice":
            message = handle_class_choice(player, class_manager, skill_tree_manager)
            game_mode = "explore"
            continue

        if game_mode == "level_up":
            if player.skill_points > 0:
                message = level_up_manager.present_levelup_choices(player, skill_tree_manager, class_manager)
            game_mode = previous_game_mode
            continue

        if game_mode == "skills_menu":
            clear_screen()
            print(f"--- Skill Tree --- (Skill Points: {player.skill_points})\n")

            unlocked_skills = [skill_tree_manager.skills[skill_id] for skill_id in player.unlocked_skills]
            available_skills = skill_tree_manager.get_available_skills(player, class_manager)

            print("--- Unlocked Skills ---")
            if not unlocked_skills:
                print("None")
            else:
                for skill in unlocked_skills:
                    print(f"- {skill.name}: {skill.description}")

            print("\n--- Available Skills ---")
            if not available_skills:
                print("None")
            else:
                for i, skill in enumerate(available_skills):
                    req_str = ", ".join([f"{req['type']} {req.get('value', '') or req.get('id', '')}" for req in skill.requirements])
                    print(f"  {i + 1}. {skill.name} (Cost: {skill.cost}) - {skill.description} [Req: {req_str or 'None'}]")

            print("\n--------------------")
            print("Enter the number of a skill to unlock it, or 'exit' to return.")
            choice = input("> ")

            if choice.lower() == 'exit':
                game_mode = "explore"
                message = "You return to your senses."
                continue

            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(available_skills):
                    skill_to_unlock = available_skills[choice_index]
                    message = skill_tree_manager.unlock_skill(player, skill_to_unlock.id, class_manager)
                else:
                    message = "Invalid skill number."
            except ValueError:
                message = "Invalid input."

            game_mode = "skills_menu"
            continue


        if game_mode == "explore" and player.current_location.monsters:
            game_mode = "combat"
            monster_names = " and a ".join(m.name for m in player.current_location.monsters)
            message = f"You step into the {player.current_location.name}... {monster_names} block(s) your way!"

        available_actions = get_available_actions(player, game_mode, menus)
        display_menu_and_state(player, message, available_actions, game_mode, class_manager)

        choice = input("> ")
        try:
            choice_index = int(choice) - 1
            if not (0 <= choice_index < len(available_actions)):
                message = "Invalid choice."
                continue
            command = available_actions[choice_index]['command']
        except ValueError:
            message = "Please enter a number."
            continue

        parts = command.split()
        verb = parts[0]
        message = ""
        player_turn_taken = False

        if verb == "quit":
            save_game(player)
            print("Thanks for playing!")
            break

        if game_mode == "explore":
            player_turn_taken = True
            if verb == "look":
                message = player.current_location.describe(player)
            elif verb == "map":
                mapper = AsciiMap(all_locations, player)
                message = mapper.generate()
                player_turn_taken = False
            elif verb == "skills":
                game_mode = "skills_menu"
                player_turn_taken = False
                continue
            elif verb == "go":
                direction = parts[1]
                if player.move(direction):
                    message = f"You go {direction}."
                else:
                    message = "You can't go that way."
            elif verb == "get":
                item_id = parts[1]
                item = next((i for i in player.current_location.items if i.id == item_id), None)
                if item:
                    player.inventory.append(item)
                    player.current_location.items.remove(item)
                    message = f"You pick up the {item.name}."
                else:
                    message = "You don't see that here."
            elif verb == "inventory":
                message = "You are carrying:\n" + "\n".join(f"- {item.name}" for item in player.inventory) if player.inventory else "Your inventory is empty."
            elif verb == "talk":
                npc_id = parts[1]
                npc = next((n for n in player.current_location.npcs if n.id == npc_id), None)
                if not npc:
                    message = "There is no one here by that name."
                else:
                    dialogue_to_use = None
                    for dialogue_entry in npc.dialogue:
                        if player.check_conditions(dialogue_entry.get('conditions', [])):
                            dialogue_to_use = dialogue_entry
                            break

                    if npc.healing_dialogue:
                        if player.hp < player.max_hp:
                            message = f'**{npc.name} says:** "{npc.healing_dialogue["pre_heal"]}"'
                            player.hp = player.max_hp
                            message += f'\n\n**{npc.name} says:** "{npc.healing_dialogue["post_heal"]}"'
                        else:
                            message = f'**{npc.name} says:** "{npc.healing_dialogue["default"]}"'
                    elif not dialogue_to_use:
                        message = f"{npc.name} has nothing to say to you right now."
                    else:
                        message = f'**{npc.name} says:** "{dialogue_to_use["text"]}"'

                        quest_id_to_give = dialogue_to_use.get("gives_quest_id")
                        if quest_id_to_give and quest_id_to_give not in player.quests:
                            quest_template = game_data["quests"].get(quest_id_to_give)
                            if quest_template:
                                player.quests[quest_id_to_give] = copy.deepcopy(quest_template)
                                player.quests[quest_id_to_give]['state'] = 'active'
                                message += f"\n\n  New Quest: {quest_template['name']}"

                                items_to_give = dialogue_to_use.get("gives_items")
                                if items_to_give:
                                    given_items_names = []
                                    for item_id_to_give in items_to_give:
                                        item_proto = all_items.get(item_id_to_give)
                                        if item_proto:
                                            player.inventory.append(copy.deepcopy(item_proto))
                                            given_items_names.append(item_proto.name)

                                    if given_items_names:
                                        message += f"\n  You received: {', '.join(given_items_names)}!"
                                    dialogue_to_use["gives_items"] = []

            elif verb == "use":
                item_id = parts[1]
                item = next((i for i in player.inventory if i.id == item_id), None)
                if item:
                    message = item.use(player)
                    if isinstance(item, (Potion, Container, EffectPotion)):
                        player.inventory.remove(item)
                else:
                    message = "You don't have that item."

        elif game_mode == "combat":
            active_monsters = player.current_location.monsters

            if verb == "attack":
                monster_id = parts[1]
                target = next((m for m in active_monsters if m.id == monster_id), None)
                if target:
                    message = f"You attack the {target.name}, dealing {player.attack_power} damage."
                    target.hp -= player.attack_power
                    player_turn_taken = True
                else:
                    message = "That monster isn't here."

            elif verb == "ability":
                ability_id = parts[1]
                ability = next((a for a in player.active_abilities if a.id == ability_id), None)
                if not ability:
                    message = "You don't have that ability."
                elif ability.cooldown > 0:
                    message = f"{ability.name} is on cooldown for {ability.cooldown} more turns."
                else:
                    target = select_from_menu(f"\nUse {ability.name} on which enemy?", active_monsters)
                    if target:
                        damage_bonus = ability.effect['combat_ability'].get('damage_bonus', 0)
                        total_damage = player.attack_power + damage_bonus
                        target.hp -= total_damage
                        ability.cooldown = ability.max_cooldown
                        message = f"You use {ability.name} on {target.name}, dealing {total_damage} damage!"
                        player_turn_taken = True
                    else:
                        message = "You decided not to use the ability."


            elif verb == "use":
                item_id = parts[1]
                item_to_use = next((i for i in player.inventory if i.id == item_id), None)

                if item_to_use:
                    if isinstance(item_to_use, OffensiveItem):
                        target = select_from_menu(f"\nUse {item_to_use.name} on which enemy?", active_monsters)
                        if target:
                            message = item_to_use.use(target)
                            player.inventory.remove(item_to_use)
                            player_turn_taken = True
                        else:
                            message = "You decided not to use the item."
                    elif isinstance(item_to_use, (Potion, EffectPotion)):
                        message = item_to_use.use(player)
                        player.inventory.remove(item_to_use)
                        player_turn_taken = True
                    else:
                        message = f"You can't use {item_to_use.name} in combat."
                else:
                    message = "You don't have that item."

            elif verb == "retreat":
                retreat_message = "You flee from combat!"
                monsters_left_behind = player.current_location.monsters[:]

                for monster in monsters_left_behind:
                    if random.random() < 0.5:
                        player.hp -= monster.attack_power
                        retreat_message += f"\nThe {monster.name} strikes you for {monster.attack_power} damage as you escape!"
                    else:
                        retreat_message += f"\nThe {monster.name} swipes at you but misses!"

                if player.is_alive():
                    threat_summary = f"The {player.current_location.name} still harbors danger: " + ", ".join(f"{m.name} ({m.hp} HP)" for m in monsters_left_behind)
                    player.retreat()
                    message = f"{retreat_message}\n\nYou escaped back to {player.current_location.name}.\n\n{threat_summary}"
                else:
                    message = retreat_message

                game_mode = "explore"
                player_turn_taken = True

            if player_turn_taken:
                defeated_monsters = [m for m in active_monsters if not m.is_alive()]
                if defeated_monsters:
                    unique_item_ids = {'lantern_1', 'amulet_of_seeing_1'}
                    for m in defeated_monsters:
                        message += f"\nYou have defeated the {m.name}!"
                        xp_message, leveled_up, class_choice_pending = player.add_xp(m.xp_reward)
                        message += f"\n  {xp_message}"
                        if class_choice_pending:
                            previous_game_mode = game_mode
                            game_mode = "class_choice"
                        elif leveled_up:
                            previous_game_mode = game_mode
                            game_mode = "level_up"

                        if m.completes_quest_id and m.completes_quest_id in player.quests:
                            if player.quests[m.completes_quest_id].get('state') != 'completed':
                                player.quests[m.completes_quest_id]['state'] = 'completed'
                                message += f"\n  Quest Completed: {player.quests[m.completes_quest_id]['name']}!"

                        if m.drops:
                            items_dropped_this_monster = []
                            for item in m.drops:
                                is_unique = item.id in unique_item_ids
                                has_in_inventory = any(i.id == item.id for i in player.inventory)
                                on_ground_here = any(i.id == item.id for i in player.current_location.items)
                                if is_unique and (has_in_inventory or on_ground_here):
                                    continue
                                player.current_location.items.append(item)
                                items_dropped_this_monster.append(item.name)
                            if items_dropped_this_monster:
                                loot_message = " It dropped "
                                if "Amulet of Seeing" in items_dropped_this_monster:
                                    loot_message += "the Amulet of Seeing."
                                else:
                                    article = "an" if items_dropped_this_monster[0].lower().startswith(('a', 'e', 'i', 'o', 'u')) else "a"
                                    if len(items_dropped_this_monster) == 1:
                                        loot_message += f"{article} {items_dropped_this_monster[0]}."
                                    else:
                                        loot_message += f": {', '.join(items_dropped_this_monster)}."
                                message += loot_message

                        monster_proto_id = m.id.split(':')[0]
                        if monster_proto_id in player.current_location.spawns_on_defeat:
                            spawn_data = player.current_location.spawns_on_defeat[monster_proto_id]
                            monster_to_spawn_id = spawn_data["monster_id_to_spawn"]

                            new_monster_proto = all_monsters.get(monster_to_spawn_id)
                            if new_monster_proto:
                                new_monster = copy.deepcopy(new_monster_proto)
                                instance_count = sum(1 for mon in player.current_location.monsters if mon.id.startswith(monster_to_spawn_id))
                                new_monster.id = f"{monster_to_spawn_id}:{instance_count}"

                                player.current_location.monsters.append(new_monster)
                                message += f'\n{spawn_data["message"]}'


                    player.current_location.monsters = [m for m in active_monsters if m.is_alive()]

                if not player.current_location.monsters:
                    message += f"\n\nVictory! You have defeated all enemies in the {player.current_location.name}."
                    game_mode = "explore"
                elif game_mode == "combat":
                    enemy_turn_message = ""
                    for monster in player.current_location.monsters:
                        player.hp -= monster.attack_power
                        enemy_turn_message += f"\nThe {monster.name} attacks you, dealing {monster.attack_power} damage."
                    message += enemy_turn_message

            if player_turn_taken and player.is_alive():
                if isinstance(player.current_location, VolcanicLocation):
                    has_fire_armor = any(item.name == "Fireproof Armor" for item in player.inventory)
                    has_fire_resistance = 'fire_resistance' in player.status_effects

                    if not has_fire_armor and not has_fire_resistance:
                        fire_damage = 3
                        player.hp -= fire_damage
                        message += f"\nThe searing heat of the volcano burns you for {fire_damage} damage!"

                effects_to_remove = []
                if player.status_effects:
                    for effect, duration in player.status_effects.items():
                        player.status_effects[effect] -= 1
                        if player.status_effects[effect] <= 0:
                            effects_to_remove.append(effect)

                    for effect in effects_to_remove:
                        del player.status_effects[effect]
                        message += f"\nThe effect of {effect.replace('_', ' ')} has worn off."

                for ability in player.active_abilities:
                    if ability.cooldown > 0:
                        ability.cooldown -= 1

    if not player.is_alive():
        print(f"\n{message}")
        print("\nYou have been defeated. Game Over.")

if __name__ == "__main__":
    main()

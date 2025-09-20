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
    def __init__(self, id, name, dialogue, hp=0, attack_power=0, inventory=None, gives_items_on_talk=None):
        super().__init__(id, name, hp, attack_power, inventory)
        self.dialogue = dialogue
        self.gives_items_on_talk = gives_items_on_talk if gives_items_on_talk is not None else []

class Monster(Character):
    def __init__(self, id, name, monster_type, hp, attack_power, drops=None, completes_quest_id=None):
        super().__init__(id, name, hp, attack_power)
        self.monster_type = monster_type
        self.drops = drops if drops is not None else []
        self.completes_quest_id = completes_quest_id

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
        target.hp += self.heal_amount
        return f"{target.name} uses the {self.name} and heals for {self.heal_amount} HP."

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

class Player(Character):
    def __init__(self, id, name, current_location, hp=20, attack_power=5):
        super().__init__(id, name, hp, attack_power)
        self.current_location = current_location
        self.previous_location = current_location
        self.status_effects = {}
        self.quests = {}
        self.discovered_locations = set()

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

import os
import platform
import json
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

def display_menu_and_state(player, message, actions, game_mode):
    """Clears the screen, displays player status, a message, and a numbered action menu."""
    clear_screen()

    print("=" * 40)
    print(f"| {player.name:<10} | HP: {player.hp:<4} | Location: {player.current_location.name:<15} |")
    print("=" * 40)

    print(f"\n{message}\n")

    print("-" * 40)
    print("What do you do?")
    for i, action in enumerate(actions):
        print(f"  {i + 1}. {action['text']}")
    print("-" * 40)

def get_available_actions(player, game_mode, menus):
    """Generates a list of available actions for the player based on JSON menu definitions."""
    actions = []
    # The 'encounter' mode is removed, so we only check for 'explore' and 'combat'
    menu_definitions = menus.get(game_mode, []) + menus.get("always", [])

    for definition in menu_definitions:
        # Simple action, no conditions or iterations
        if "iterate" not in definition and "condition" not in definition:
            actions.append(definition.copy())
            continue

        # Check condition for non-iterated actions
        if "condition" in definition and "iterate" not in definition:
            if definition["condition"] == "player.inventory" and not player.inventory:
                continue
            if definition["condition"] == "has_usable_item" and not any(isinstance(item, (Potion, OffensiveItem, EffectPotion)) for item in player.inventory):
                continue
            actions.append(definition.copy())

        # Handle iterated actions
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
                # Check condition for iterated actions
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

    # Add conditional exits to actions if conditions are met
    for c_exit in player.current_location.conditional_exits:
        if player.check_conditions(c_exit.conditions):
            action = {
                "text": f"Go {c_exit.direction} -> {c_exit.destination.name}",
                "command": f"go {c_exit.direction}",
            }
            actions.append(action)

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
            completes_quest_id=monster_data.get("completes_quest_id")
        )

    all_npcs = {}
    for npc_id, npc_data in game_data.get("npcs", {}).items():
        all_npcs[npc_id] = NPC(
            npc_id, npc_data["name"], npc_data.get("dialogue", ""),
            npc_data["hp"], npc_data["attack_power"],
            gives_items_on_talk=npc_data.get("gives_items_on_talk")
        )

    all_locations = {}
    for loc_id, loc_data in game_data.get("locations", {}).items():
        loc_type = loc_data.get("location_type", "base")
        # A bit of repetition here, but it's clear
        common_args = {
            "id": loc_id,
            "name": loc_data["name"],
            "description": loc_data["description"],
            "spawns_on_defeat": loc_data.get("spawns_on_defeat")
        }
        if loc_type == "City":
            all_locations[loc_id] = CityLocation(**common_args)
        elif loc_type == "Wilderness":
            all_locations[loc_id] = WildernessLocation(
                **common_args,
                spawn_chance=loc_data.get("spawn_chance", 0.0)
            )
        elif loc_type == "Dungeon":
            all_locations[loc_id] = DungeonLocation(
                **common_args,
                hazard_description=loc_data.get("hazard_description", "")
            )
        elif loc_type == "Swamp":
            all_locations[loc_id] = SwampLocation(
                **common_args,
                spawn_chance=loc_data.get("spawn_chance", 0.0),
                hidden_description=loc_data.get("hidden_description", "")
            )
        elif loc_type == "Volcanic":
            all_locations[loc_id] = VolcanicLocation(
                **common_args,
                spawn_chance=loc_data.get("spawn_chance", 0.0)
            )
        else:
            all_locations[loc_id] = Location(**common_args)

    # --- Linking Pass ---
    # Link monster drops and container items first
    for monster_id, monster_data in game_data.get("monsters", {}).items():
        monster = all_monsters[monster_id]
        monster.drops = [all_items[item_id] for item_id in monster_data.get("drop_ids", [])]

    for item_id, item_data in game_data.get("items", {}).items():
        if item_data.get("item_type") == "Container":
            container = all_items[item_id]
            container.contained_items = [all_items[i_id] for i_id in item_data.get("contained_item_ids", [])]

    # Link locations
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

        # Load conditional exits
        location.conditional_exits = []
        for c_exit_data in loc_data.get("conditional_exits", []):
            destination_location = all_locations[c_exit_data['destination_id']]
            c_exit = ConditionalExit(
                direction=c_exit_data['direction'],
                destination=destination_location,
                description=c_exit_data['description'],
                conditions=c_exit_data['conditions']
            )
            location.conditional_exits.append(c_exit)

    # --- Player Creation ---
    player_data = game_data["player"]
    start_location = all_locations[player_data["start_location_id"]]
    inventory = [all_items[item_id] for item_id in player_data.get("inventory", [])]
    player = Player(
        "player", player_data["name"], start_location, player_data["hp"], player_data["attack_power"]
    )
    player.inventory = inventory
    player.quests = player_data.get("quests", {})
    player.discovered_locations.add(start_location.id)

    return player, game_data.get("menus", {}), all_locations, all_items, all_monsters

class AsciiMap:
    def __init__(self, all_locations, player):
        self.all_locations = all_locations
        self.player = player
        self.accessible_graph = {}
        self.coords = {}

    def generate(self):
        self._build_accessible_graph()
        if not self.accessible_graph:
            return "You are lost in an unknown place."

        self._assign_coordinates()
        visible_ids = self._get_visible_locations()
        return self._render_map(visible_ids)

    def _build_accessible_graph(self):
        start_id = self.player.current_location.id
        q = collections.deque([start_id])
        visited = {start_id}

        while q:
            current_id = q.popleft()
            if current_id not in self.all_locations: continue
            location = self.all_locations[current_id]
            self.accessible_graph[current_id] = {}

            exits = dict(location.exits.items())
            for c_exit in location.conditional_exits:
                if self.player.check_conditions(c_exit.conditions):
                    exits[c_exit.direction] = c_exit.destination

            for direction, dest_loc in exits.items():
                self.accessible_graph[current_id][direction] = dest_loc.id
                if dest_loc.id not in visited:
                    visited.add(dest_loc.id)
                    q.append(dest_loc.id)

    def _assign_coordinates(self):
        start_id = self.player.current_location.id
        q = collections.deque([start_id])
        self.coords = {start_id: (0, 0)}

        while q:
            current_id = q.popleft()
            cx, cy = self.coords[current_id]

            exits = self.accessible_graph.get(current_id, {})
            for direction, neighbor_id in exits.items():
                if neighbor_id in self.coords:
                    continue

                dx, dy = 0, 0
                if direction == 'north': dy = -1
                elif direction == 'south': dy = 1
                elif direction == 'east':  dx = 1
                elif direction == 'west':  dx = -1
                else: continue

                nx, ny = cx + dx, cy + dy

                while (nx, ny) in self.coords.values():
                    nx += 1 # Simple collision avoidance

                self.coords[neighbor_id] = (nx, ny)
                q.append(neighbor_id)

    def _get_visible_locations(self):
        visible = set(self.player.discovered_locations)
        for loc_id in list(self.player.discovered_locations):
            if loc_id in self.accessible_graph:
                for neighbor_id in self.accessible_graph[loc_id].values():
                    visible.add(neighbor_id)
        return visible

    def _render_map(self, visible_ids):
        if not self.coords: return "Map is empty."

        visible_coords = {loc_id: pos for loc_id, pos in self.coords.items() if loc_id in visible_ids}
        if not visible_coords: return "You haven't discovered enough to draw a map."

        min_x = min(x for x, y in visible_coords.values())
        min_y = min(y for x, y in visible_coords.values())
        norm_coords = {loc_id: (x - min_x, y - min_y) for loc_id, (x, y) in visible_coords.items()}

        max_x = max(x for x, y in norm_coords.values()) if norm_coords else 0
        max_y = max(y for x, y in norm_coords.values()) if norm_coords else 0

        grid = [[None for _ in range(max_x + 1)] for _ in range(max_y + 1)]
        for loc_id, (x, y) in norm_coords.items():
            grid[y][x] = loc_id

        max_width = len("[ ??? ]")
        for loc_id in visible_ids:
            if loc_id in self.player.discovered_locations:
                name = self.all_locations[loc_id].name
                max_width = max(max_width, len(name) + 4)

        output_lines = []
        for y, row in enumerate(grid):
            node_line = ""
            conn_line = ""
            for x, loc_id in enumerate(row):
                if loc_id is None:
                    node_line += " " * (max_width + 3)
                    conn_line += " " * (max_width + 3)
                    continue

                if loc_id in self.player.discovered_locations:
                    loc = self.all_locations[loc_id]
                    name = f"*{loc.name}*" if loc.id == self.player.current_location.id else loc.name
                    node_str = f"[{name}]"
                else:
                    node_str = "[ ??? ]"
                node_line += node_str.center(max_width)

                exits = self.accessible_graph.get(loc_id, {})
                east_neighbor = exits.get('east')
                if east_neighbor and east_neighbor in visible_ids and east_neighbor in norm_coords and norm_coords[east_neighbor][0] > x:
                    node_line += "---"
                else:
                    node_line += "   "

                south_neighbor = exits.get('south')
                if south_neighbor and south_neighbor in visible_ids and south_neighbor in norm_coords and norm_coords[south_neighbor][1] > y:
                    conn_line += "|".center(max_width) + "   "
                else:
                    conn_line += " " * (max_width + 3)

            output_lines.append(node_line.rstrip())
            if conn_line.strip():
                output_lines.append(conn_line.rstrip())

        return "\n".join(output_lines)

def main():
    game_data = load_game_data("game_data.json")
    player, menus, all_locations, all_items, all_monsters = load_world_from_data(game_data)
    game_mode = "explore"
    message = player.current_location.describe(player)

    while player.is_alive():
        # --- State Transition Check ---
        if game_mode == "explore" and player.current_location.monsters:
            game_mode = "combat"
            monster_names = " and a ".join(m.name for m in player.current_location.monsters)
            message = f"You step into the {player.current_location.name}... {monster_names} block(s) your way!"

        # --- UI and Input ---
        available_actions = get_available_actions(player, game_mode, menus)
        display_menu_and_state(player, message, available_actions, game_mode)

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
        message = "" # Reset message each turn
        player_turn_taken = False

        # --- Command Processing ---
        if verb == "quit":
            print("Thanks for playing!")
            break

        # --- EXPLORE MODE ---
        if game_mode == "explore":
            player_turn_taken = True # Most explore actions take a "turn"
            if verb == "look":
                message = player.current_location.describe(player)
            elif verb == "map":
                mapper = AsciiMap(all_locations, player)
                message = mapper.generate()
                player_turn_taken = False # Viewing the map shouldn't take a turn
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
                    # Find the first dialogue entry whose conditions are met
                    for dialogue_entry in npc.dialogue:
                        if player.check_conditions(dialogue_entry.get('conditions', [])):
                            dialogue_to_use = dialogue_entry
                            break

                    if not dialogue_to_use:
                        message = f"{npc.name} has nothing to say to you right now."
                    else:
                        message = f'**{npc.name} says:** "{dialogue_to_use["text"]}"'

                        # Check if this dialogue gives a quest
                        quest_id_to_give = dialogue_to_use.get("gives_quest_id")
                        if quest_id_to_give and quest_id_to_give not in player.quests:
                            # Get quest template from the main game data
                            quest_template = game_data["quests"].get(quest_id_to_give)
                            if quest_template:
                                player.quests[quest_id_to_give] = copy.deepcopy(quest_template)
                                player.quests[quest_id_to_give]['state'] = 'active'
                                message += f"\n\n  New Quest: {quest_template['name']}"

                        # Check if this dialogue gives items (and only if the quest was just given)
                        items_to_give = dialogue_to_use.get("gives_items")
                        if quest_id_to_give and items_to_give and player.quests.get(quest_id_to_give, {}).get('state') == 'active':
                            # To prevent re-giving, we can check if the quest state was not 'active' before this conversation
                            # A simple way is to check if the quest ID is in the player's log. If not, give items.
                            # Since we just added it, this logic works for the first time only.
                            given_items_names = []
                            for item_id_to_give in items_to_give:
                                item_proto = all_items.get(item_id_to_give)
                                if item_proto:
                                    player.inventory.append(copy.deepcopy(item_proto))
                                    given_items_names.append(item_proto.name)

                            if given_items_names:
                                message += f"\n  You received: {', '.join(given_items_names)}!"
                            # To ensure items are only given once, we can clear the list from the NPC instance
                            dialogue_to_use["gives_items"] = []
                npc_id = parts[1]
                npc = next((n for n in player.current_location.npcs if n.id == npc_id), None)
                if not npc:
                    message = "There is no one here by that name."
                else:
                    dialogue_to_use = None
                    # Find the first dialogue entry whose conditions are met
                    for dialogue_entry in npc.dialogue:
                        if player.check_conditions(dialogue_entry.get('conditions', [])):
                            dialogue_to_use = dialogue_entry
                            break

                    if not dialogue_to_use:
                        message = f"{npc.name} has nothing to say to you right now."
                    else:
                        message = f'**{npc.name} says:** "{dialogue_to_use["text"]}"'

                        # Check if this dialogue gives a quest
                        quest_id_to_give = dialogue_to_use.get("gives_quest_id")
                        if quest_id_to_give and quest_id_to_give not in player.quests:
                            # Get quest template from the main game data
                            quest_template = game_data["quests"].get(quest_id_to_give)
                            if quest_template:
                                player.quests[quest_id_to_give] = copy.deepcopy(quest_template)
                                player.quests[quest_id_to_give]['state'] = 'active'
                                message += f"\n\n  New Quest: {quest_template['name']}"

                        # Check if this dialogue gives items
                        items_to_give = dialogue_to_use.get("gives_items")
                        if items_to_give:
                            # A simple way is to check if the quest ID is in the player's log. If not, give items.
                            # Since we just added it, this logic works for the first time only.
                            given_items_names = []
                            for item_id_to_give in items_to_give:
                                item_proto = all_items.get(item_id_to_give)
                                if item_proto:
                                    # Create a unique copy for each potion
                                    player.inventory.append(copy.deepcopy(item_proto))
                                    given_items_names.append(item_proto.name)

                            if given_items_names:
                                message += f"\n  You received: {', '.join(given_items_names)}!"
                            # To ensure items are only given once, we can clear the list from the NPC instance
                            # This modifies the in-memory object for this game session
                            dialogue_to_use["gives_items"] = []
                npc_id = parts[1]
                npc = next((n for n in player.current_location.npcs if n.id == npc_id), None)
                if not npc:
                    message = "There is no one here by that name."
                else:
                    dialogue_to_use = None
                    # Find the first dialogue entry whose conditions are met
                    for dialogue_entry in npc.dialogue:
                        if player.check_conditions(dialogue_entry.get('conditions', [])):
                            dialogue_to_use = dialogue_entry
                            break

                    if not dialogue_to_use:
                        message = f"{npc.name} has nothing to say to you right now."
                    else:
                        message = f'**{npc.name} says:** "{dialogue_to_use["text"]}"'

                        # Check if this dialogue gives a quest
                        quest_id_to_give = dialogue_to_use.get("gives_quest_id")
                        if quest_id_to_give and quest_id_to_give not in player.quests:
                            # Get quest template from the main game data
                            quest_template = game_data["quests"].get(quest_id_to_give)
                            if quest_template:
                                player.quests[quest_id_to_give] = copy.deepcopy(quest_template)
                                player.quests[quest_id_to_give]['state'] = 'active'
                                message += f"\n\n  New Quest: {quest_template['name']}"

                        # Check if this dialogue gives items (and only if the quest was just given)
                        items_to_give = dialogue_to_use.get("gives_items")
                        if quest_id_to_give and items_to_give:
                            # To prevent re-giving, we can check if the quest state was not 'active' before this conversation
                            # A simple way is to check if the quest ID is in the player's log. If not, give items.
                            # Since we just added it, this logic works for the first time only.
                            given_items_names = []
                            for item_id_to_give in items_to_give:
                                # A simple check to avoid giving the same item twice if the player somehow already has it
                                if not any(p_item.id == item_id_to_give for p_item in player.inventory):
                                    item_proto = all_items.get(item_id_to_give)
                                    if item_proto:
                                        player.inventory.append(copy.deepcopy(item_proto))
                                        given_items_names.append(item_proto.name)

                            if given_items_names:
                                message += f"\n  You received: {', '.join(given_items_names)}!"
                            # To ensure items are only given once, we can clear the list from the NPC instance
                            dialogue_to_use["gives_items"] = []
                npc_id = parts[1]
                npc = next((n for n in player.current_location.npcs if n.id == npc_id), None)
                if npc:
                    # First, handle item giving
                    if npc.gives_items_on_talk:
                        given_items = []
                        for item_id_to_give in npc.gives_items_on_talk:
                            if not any(p_item.id == item_id_to_give for p_item in player.inventory):
                                item_proto = all_items.get(item_id_to_give)
                                if item_proto:
                                    player.inventory.append(copy.deepcopy(item_proto))
                                    given_items.append(item_proto.name)
                        if given_items:
                            message += f"You received: {', '.join(given_items)}!\n"
                        npc.gives_items_on_talk = [] # Clear after giving

                    # Then, handle dialogue
                    dialogue_text = ""
                    if isinstance(npc.dialogue, list):
                        for dialogue_entry in npc.dialogue:
                            if player.check_conditions(dialogue_entry.get('conditions', [])):
                                dialogue_text = dialogue_entry["text"]
                                break
                        else:
                            dialogue_text = f"{npc.name} has nothing to say to you right now."
                    elif isinstance(npc.dialogue, str):
                        dialogue_text = npc.dialogue
                    else:
                        dialogue_text = f"{npc.name} has nothing to say."

                    message += f'**{npc.name} says:** "{dialogue_text}"'
                else:
                    message = "There is no one here by that name."

            elif verb == "use":
                item_id = parts[1]
                item = next((i for i in player.inventory if i.id == item_id), None)
                if item:
                    message = item.use(player)
                    if isinstance(item, (Potion, Container, EffectPotion)):
                        player.inventory.remove(item)
                else:
                    message = "You don't have that item."

        # --- COMBAT MODE ---
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
                    if random.random() < 0.5: # 50% chance
                        player.hp -= monster.attack_power
                        retreat_message += f"\nThe {monster.name} strikes you for {monster.attack_power} damage as you escape!"
                    else:
                        retreat_message += f"\nThe {monster.name} swipes at you but misses!"

                if player.is_alive():
                    # Create summary before moving
                    threat_summary = f"The {player.current_location.name} still harbors danger: " + ", ".join(f"{m.name} ({m.hp} HP)" for m in monsters_left_behind)
                    player.retreat()
                    message = f"{retreat_message}\n\nYou escaped back to {player.current_location.name}.\n\n{threat_summary}"
                else:
                    message = retreat_message # Let the main loop handle death

                game_mode = "explore"
                player_turn_taken = True

            # --- Post-Action Resolution ---
            if player_turn_taken:
                defeated_monsters = [m for m in active_monsters if not m.is_alive()]
                if defeated_monsters:
                    unique_item_ids = {'lantern_1', 'amulet_of_seeing_1'}
                    for m in defeated_monsters:
                        message += f"\nYou have defeated the {m.name}!"

                        # Check for quest completion
                        if m.completes_quest_id and m.completes_quest_id in player.quests:
                            if player.quests[m.completes_quest_id].get('state') != 'completed':
                                player.quests[m.completes_quest_id]['state'] = 'completed'
                                message += f"\n  Quest Completed: {player.quests[m.completes_quest_id]['name']}!"

                        # Handle loot drops
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
                                    # A simple heuristic for "a" vs "an"
                                    article = "an" if items_dropped_this_monster[0].lower().startswith(('a', 'e', 'i', 'o', 'u')) else "a"
                                    if len(items_dropped_this_monster) == 1:
                                        loot_message += f"{article} {items_dropped_this_monster[0]}."
                                    else:
                                        loot_message += f": {', '.join(items_dropped_this_monster)}."
                                message += loot_message

                        # Handle sequential spawning
                        monster_proto_id = m.id.split(':')[0]
                        if monster_proto_id in player.current_location.spawns_on_defeat:
                            spawn_data = player.current_location.spawns_on_defeat[monster_proto_id]
                            monster_to_spawn_id = spawn_data["monster_id_to_spawn"]

                            new_monster_proto = all_monsters.get(monster_to_spawn_id)
                            if new_monster_proto:
                                new_monster = copy.deepcopy(new_monster_proto)
                                # Find a unique instance ID
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

    if not player.is_alive():
        print(f"\n{message}")
        print("\nYou have been defeated. Game Over.")

if __name__ == "__main__":
    main()

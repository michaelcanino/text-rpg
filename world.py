import json
import copy
import collections

from models import (
    Item, Potion, EffectPotion, Container, OffensiveItem,
    Monster, NPC, Player,
    Location, CityLocation, WildernessLocation, DungeonLocation, SwampLocation, VolcanicLocation
)

__all__ = ['load_game_data', 'load_world_from_data', 'ConditionalExit', 'AsciiMap']

ConditionalExit = collections.namedtuple('ConditionalExit', ['direction', 'destination', 'description', 'conditions'])

def load_game_data(filepath):
    """Loads game data from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def load_world_from_data(game_data):
    """Creates all game objects from the normalized data and links them."""
    all_items = {}
    for item_id, item_data in game_data.get("items", {}).items():
        item_type = item_data.get("item_type", "Item")
        item_class_map = {
            "Potion": Potion, "EffectPotion": EffectPotion,
            "Container": Container, "OffensiveItem": OffensiveItem
        }
        item_class = item_class_map.get(item_type, Item)

        # Common arguments for all item types
        item_args = {
            'id': item_id,
            'name': item_data["name"],
            'description': item_data["description"],
            'value': item_data.get("value", 0),
            'teaches_skills': item_data.get("teaches_skills")
        }
        # Add type-specific arguments
        if item_type == "Potion":
            item_args['heal_amount'] = item_data.get("heal_amount", 0)
        elif item_type == "EffectPotion":
            item_args['effect'] = item_data.get("effect")
            item_args['duration'] = item_data.get("duration")
        elif item_type == "OffensiveItem":
            item_args['damage_amount'] = item_data.get("damage_amount", 0)

        all_items[item_id] = item_class(**item_args)

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
        npc_type = npc_data.get("npc_type", "NPC")
        inventory = [all_items[item_id] for item_id in npc_data.get("inventory_ids", [])] if "inventory_ids" in npc_data else []

        if npc_type == "Merchant":
            from models import Merchant
            all_npcs[npc_id] = Merchant(
                id=npc_id,
                name=npc_data["name"],
                dialogue=npc_data.get("dialogue", ""),
                hp=npc_data["hp"],
                attack_power=npc_data["attack_power"],
                inventory=inventory,
                gold=npc_data.get("gold", 0)
            )
        else:
            all_npcs[npc_id] = NPC(
                id=npc_id,
                name=npc_data["name"],
                dialogue=npc_data.get("dialogue", ""),
                hp=npc_data["hp"],
                attack_power=npc_data["attack_power"],
                inventory=inventory,
                gives_items_on_talk=npc_data.get("gives_items_on_talk"),
                healing_dialogue=npc_data.get("healing_dialogue"),
                teaches_skills=npc_data.get("teaches_skills")
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

    return player, game_data.get("menus", {}), all_locations, all_items, all_monsters, all_npcs

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

            all_exits = {**loc.exits, **{c.direction: c.destination for c in loc.conditional_exits}}
            for direction, dest_loc in all_exits.items():
                if dest_loc:
                    for (nx, ny), neighbor_loc in self.grid.items():
                        if neighbor_loc.id == dest_loc.id:
                            if ny < y:
                                if char_grid[gy - 1][gx + 1] == ' ': char_grid[gy - 1][gx + 1] = '|'
                            elif ny > y:
                                if char_grid[gy + 1][gx + 1] == ' ': char_grid[gy + 1][gx + 1] = '|'
                            elif nx > x:
                                if char_grid[gy][gx + 3] == ' ': char_grid[gy][gx + 3] = '-'
                            elif nx < x:
                                if char_grid[gy][gx - 1] == ' ': char_grid[gy][gx - 1] = '-'
                            break

        for row in char_grid:
            map_str += "".join(row).rstrip() + "\n"

        map_str += "\n[P]layer, [C]ity, [W]ilderness, [D]ungeon, [R]oom, ? Undiscovered\n"
        return map_str

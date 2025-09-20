__all__ = [
    'Character', 'NPC', 'Monster',
    'Item', 'Potion', 'EffectPotion', 'OffensiveItem', 'Container',
    'Location', 'CityLocation', 'WildernessLocation', 'DungeonLocation', 'SwampLocation', 'VolcanicLocation',
    'Skill', 'ActiveAbility', 'Player', 'PlayerClass'
]

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
    def __init__(self, id, name, dialogue, hp=0, attack_power=0, inventory=None, gives_items_on_talk=None, healing_dialogue=None, teaches_skills=None):
        super().__init__(id, name, hp, attack_power, inventory)
        self.dialogue = dialogue
        self.gives_items_on_talk = gives_items_on_talk if gives_items_on_talk is not None else []
        self.healing_dialogue = healing_dialogue
        self.teaches_skills = teaches_skills if teaches_skills is not None else []

class Monster(Character):
    def __init__(self, id, name, monster_type, hp, attack_power, drops=None, completes_quest_id=None, xp_reward=0):
        super().__init__(id, name, hp, attack_power)
        self.monster_type = monster_type
        self.drops = drops if drops is not None else []
        self.completes_quest_id = completes_quest_id
        self.xp_reward = xp_reward

class Item:
    def __init__(self, id, name, description, value=0, teaches_skills=None):
        self.id = id
        self.name = name
        self.description = description
        self.value = value
        self.teaches_skills = teaches_skills if teaches_skills is not None else []

    def use(self, target):
        return f"You can't use {self.name}."

class Potion(Item):
    def __init__(self, id, name, description, value, heal_amount, **kwargs):
        super().__init__(id, name, description, value, **kwargs)
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
    def __init__(self, id, name, description, value, effect, duration, **kwargs):
        super().__init__(id, name, description, value, **kwargs)
        self.effect = effect
        self.duration = duration

    def use(self, target):
        target.status_effects[self.effect] = self.duration
        return f"{target.name} uses the {self.name}. You feel a strange energy course through you."

class OffensiveItem(Item):
    def __init__(self, id, name, description, value, damage_amount, **kwargs):
        super().__init__(id, name, description, value, **kwargs)
        self.damage_amount = damage_amount

    def use(self, target):
        target.hp -= self.damage_amount
        return f"You use the {self.name} on {target.name}, dealing {self.damage_amount} damage!"

class Container(Item):
    def __init__(self, id, name, description, value, contained_items=None, **kwargs):
        super().__init__(id, name, description, value, **kwargs)
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

        self.base_max_hp = max_hp
        self.base_attack_power = attack_power
        self.base_critical_chance = 0.0

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
        for condition in conditions:
            if condition['type'] == 'has_item':
                if not any(item.id == condition['item_id'] for item in self.inventory):
                    return False
            elif condition['type'] == 'quest_completed':
                if self.quests.get(condition['quest_id'], {}).get('state') != 'completed':
                    return False
            elif condition['type'] == 'quest_active':
                quest = self.quests.get(condition['quest_id'])
                if not quest or quest.get('state') != 'active':
                    return False
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
        self.hp = self.max_hp

        class_choice_triggered = self.level == 10 and self.class_id is None
        return True, class_choice_triggered

    def recalculate_stats(self, skill_tree_manager, class_manager):
        self.max_hp = self.base_max_hp
        self.attack_power = self.base_attack_power
        self.critical_chance = self.base_critical_chance

        if self.class_id:
            player_class = class_manager.classes.get(self.class_id)
            if player_class:
                for stat, value in player_class.base_mods.items():
                    setattr(self, stat, getattr(self, stat) + value)

        for skill_id in self.unlocked_skills:
            skill = skill_tree_manager.skills.get(skill_id)
            if skill and skill.skill_type == 'passive':
                for stat, mod in skill.effect.get('stat_mod', {}).items():
                    setattr(self, stat, getattr(self, stat) + mod)

        self.hp = min(self.hp, self.max_hp)

class PlayerClass:
    def __init__(self, id, name, short_description, base_mods, starting_skills, skill_pool):
        self.id = id
        self.name = name
        self.short_description = short_description
        self.base_mods = base_mods
        self.starting_skills = starting_skills
        self.skill_pool = skill_pool

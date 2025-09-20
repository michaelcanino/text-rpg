import os
import copy
import random
import json

from models import Player, Potion, Container, OffensiveItem, EffectPotion, VolcanicLocation
from world import load_game_data, load_world_from_data, AsciiMap
from managers import (
    LevelUpManager, SkillTreeManager, ClassManager,
    save_game, load_player_from_save,
    select_from_menu, display_menu_and_state, get_available_actions, clear_screen
)

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
            skill_tree_manager.unlock_skill(player, skill_id, class_manager, free=True)

        player.recalculate_stats(skill_tree_manager, class_manager)

        return f"You have chosen the path of the {chosen_class.name}! Your journey continues."
    else:
        # Force the player to choose
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
                player, _, _, _, _ = load_world_from_data(game_data)
                print("A new adventure begins!")
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    else:
        player, _, _, _, _ = load_world_from_data(game_data)

    # Migration for old saves: if player is >= level 10 and has no class, trigger choice
    if player.level >= 10 and player.class_id is None:
        message = handle_class_choice(player, class_manager, skill_tree_manager)
        save_game(player)
    else:
        message = player.current_location.describe(player)

    game_mode = "explore"
    previous_game_mode = "explore"
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
            if not unlocked_skills: print("None")
            else:
                for skill in unlocked_skills: print(f"- {skill.name}: {skill.description}")

            print("\n--- Available Skills ---")
            if not available_skills: print("None")
            else:
                for i, skill in enumerate(available_skills):
                    req_str = ", ".join([f"{req['type']} {req.get('value', '') or req.get('id', '')}" for req in skill.requirements])
                    print(f"  {i + 1}. {skill.name} (Cost: {skill.cost}) - {skill.description} [Req: {req_str or 'None'}]")

            print("\n--------------------")
            choice = input("Enter the number of a skill to unlock it, or 'exit' to return.\n> ")

            if choice.lower() == 'exit':
                game_mode = "explore"
                message = "You return to your senses."
                continue

            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(available_skills):
                    skill_to_unlock = available_skills[choice_index]
                    message = skill_tree_manager.unlock_skill(player, skill_to_unlock.id, class_manager)
                    player.recalculate_stats(skill_tree_manager, class_manager)
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

        available_actions = get_available_actions(player, game_mode, menus, all_locations)
        display_menu_and_state(player, message, available_actions, game_mode, class_manager)

        choice = input("> ")
        try:
            choice_index = int(choice) - 1
            if not (0 <= choice_index < len(available_actions)):
                message = "Invalid choice."
                continue
            command = available_actions[choice_index]['command']
        except (ValueError, IndexError):
            message = "Please enter a valid number."
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
                item_id = " ".join(parts[1:])
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
                npc_id = " ".join(parts[1:])
                npc = next((n for n in player.current_location.npcs if n.id == npc_id), None)
                if not npc:
                    message = "There is no one here by that name."
                else:
                    dialogue_to_use = None
                    if npc.healing_dialogue:
                        if player.hp < player.max_hp:
                            message = f'**{npc.name} says:** "{npc.healing_dialogue["pre_heal"]}"'
                            player.hp = player.max_hp
                            message += f'\n\n**{npc.name} says:** "{npc.healing_dialogue["post_heal"]}"'
                        else:
                            message = f'**{npc.name} says:** "{npc.healing_dialogue["default"]}"'
                    else:
                        for dialogue_entry in npc.dialogue:
                            if player.check_conditions(dialogue_entry.get('conditions', [])):
                                dialogue_to_use = dialogue_entry
                                break

                        if not dialogue_to_use:
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
                item_id = " ".join(parts[1:])
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
                monster_id = " ".join(parts[1:])
                target = next((m for m in active_monsters if m.id == monster_id), None)
                if target:
                    message = f"You attack the {target.name}, dealing {player.attack_power} damage."
                    target.hp -= player.attack_power
                    player_turn_taken = True
                else:
                    message = "That monster isn't here."

            elif verb == "ability":
                ability_id = " ".join(parts[1:])
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
                item_id = " ".join(parts[1:])
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
                for monster in player.current_location.monsters:
                    if random.random() < 0.5:
                        player.hp -= monster.attack_power
                        retreat_message += f"\nThe {monster.name} strikes you for {monster.attack_power} damage as you escape!"
                    else:
                        retreat_message += f"\nThe {monster.name} swipes at you but misses!"

                if player.is_alive():
                    player.retreat()
                    message = f"{retreat_message}\n\nYou escaped back to {player.current_location.name}."
                else:
                    message = retreat_message
                game_mode = "explore"
                player_turn_taken = False

            if player_turn_taken:
                defeated_monsters = [m for m in active_monsters if not m.is_alive()]
                if defeated_monsters:
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
                            for item in m.drops:
                                player.current_location.items.append(item)
                                message += f"\n  It dropped a {item.name}."

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
                    message += f"\n\nVictory! You have cleared the {player.current_location.name}."
                    game_mode = "explore"
                elif game_mode == "combat":
                    enemy_turn_message = ""
                    for monster in player.current_location.monsters:
                        player.hp -= monster.attack_power
                        enemy_turn_message += f"\nThe {monster.name} attacks you, dealing {monster.attack_power} damage."
                    message += enemy_turn_message

            if player_turn_taken and player.is_alive():
                if isinstance(player.current_location, VolcanicLocation):
                    if not any(item.name == "Fireproof Armor" for item in player.inventory) and 'fire_resistance' not in player.status_effects:
                        fire_damage = 3
                        player.hp -= fire_damage
                        message += f"\nThe searing heat of the volcano burns you for {fire_damage} damage!"

                effects_to_remove = []
                for effect, duration in list(player.status_effects.items()):
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

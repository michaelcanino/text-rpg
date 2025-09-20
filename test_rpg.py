import unittest
import json
import os
from unittest.mock import patch

from models import Player, Potion, NPC
from world import load_game_data, load_world_from_data
from managers import SkillTreeManager, ClassManager, save_game, load_player_from_save
from main import handle_class_choice

class TestRPGSystem(unittest.TestCase):

    def setUp(self):
        """Set up a fresh game state for each test."""
        self.game_data = load_game_data("game_data.json")

        self.skill_tree_manager = SkillTreeManager(self.game_data.get("skills", {}))
        self.class_manager = ClassManager(self.game_data.get("classes", {}))

        # Note: We get back menus, all_locations, etc. but we only need some for the tests
        self.player, _, self.all_locations, self.all_items, _ = load_world_from_data(self.game_data)

        self.player.current_location = self.all_locations["oakhaven"]
        self.player.hp = self.player.max_hp

        if os.path.exists("save_data.json"):
            os.remove("save_data.json")

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists("save_data.json"):
            os.remove("save_data.json")

    def test_potion_healing_cap(self):
        """Ensure potions cannot heal above max_hp."""
        self.player.max_hp = 50
        self.player.hp = 49
        # We can instantiate a Potion directly for this test
        potion = Potion("test_potion", "Test Potion", "Desc", 10, 20)

        message = potion.use(self.player)

        self.assertEqual(self.player.hp, self.player.max_hp)
        self.assertIn("heals for 1 HP", message)

    def test_healer_npc_dialogue_and_healing(self):
        """Test Sister Elira's healing functionality."""
        sister_elira = next((n for n in self.player.current_location.npcs if n.id == "sister_elira"), None)
        self.assertIsNotNone(sister_elira, "Sister Elira not found in Oakhaven")

        # Test dialogue at full health
        self.player.hp = self.player.max_hp
        message = ""
        if sister_elira.healing_dialogue and self.player.hp >= self.player.max_hp:
            message = sister_elira.healing_dialogue["default"]
        self.assertEqual(message, "The temple is a sanctuary from the chaos outside. May peace find you here.")

        # Test healing when wounded
        self.player.hp = 1
        original_max_hp = self.player.max_hp

        pre_heal_msg, post_heal_msg = "", ""
        if sister_elira.healing_dialogue and self.player.hp < self.player.max_hp:
            pre_heal_msg = sister_elira.healing_dialogue["pre_heal"]
            self.player.hp = self.player.max_hp  # Simulate healing
            post_heal_msg = sister_elira.healing_dialogue["post_heal"]

        self.assertEqual(pre_heal_msg, "You look weary, let me heal your wounds.")
        self.assertEqual(post_heal_msg, "There, much better. May the light guide your path.")
        self.assertEqual(self.player.hp, original_max_hp)

    def test_save_load_preserves_base_stats(self):
        """Test that base stats are saved and correctly reloaded."""
        self.player.base_max_hp += 15
        self.player.recalculate_stats(self.skill_tree_manager, self.class_manager)
        expected_max_hp = self.player.max_hp

        with patch('builtins.print'):  # Suppress print output from save_game
            save_game(self.player)

        self.assertTrue(os.path.exists("save_data.json"))

        with open("save_data.json", 'r') as f:
            save_data = json.load(f)

        loaded_player = load_player_from_save(save_data, self.all_locations, self.all_items, self.skill_tree_manager, self.class_manager)

        self.assertEqual(loaded_player.base_max_hp, self.player.base_max_hp)
        self.assertEqual(loaded_player.max_hp, expected_max_hp)

    @patch('main.clear_screen')
    @patch('main.select_from_menu')
    def test_class_evolution_flow(self, mock_select, mock_clear):
        """Test the entire class evolution process at level 10."""
        # Mock the menu selection to automatically choose the Knight
        mock_select.return_value = self.class_manager.classes['knight']

        # Level up player to level 10
        self.player.level = 9
        self.player.xp = self.player.xp_to_next_level - 1
        _, _, class_choice_pending = self.player.add_xp(1)

        self.assertTrue(class_choice_pending)
        self.assertEqual(self.player.level, 10)

        base_hp_before = self.player.base_max_hp
        base_ap_before = self.player.base_attack_power

        # Handle the class choice
        message = handle_class_choice(self.player, self.class_manager, self.skill_tree_manager)

        # Verify the changes
        self.assertEqual(self.player.class_id, 'knight')
        self.assertIn("You have chosen the path of the Knight!", message)

        self.assertIn('toughness_1', self.player.unlocked_skills)

        knight_class = self.class_manager.classes['knight']
        hp_bonus = knight_class.base_mods.get('max_hp', 0)
        ap_bonus = knight_class.base_mods.get('attack_power', 0)

        toughness_skill = self.skill_tree_manager.skills['toughness_1']
        hp_skill_bonus = toughness_skill.effect['stat_mod'].get('max_hp', 0)

        expected_max_hp = base_hp_before + hp_bonus + hp_skill_bonus
        expected_ap = base_ap_before + ap_bonus

        self.assertEqual(self.player.max_hp, expected_max_hp)
        self.assertEqual(self.player.attack_power, expected_ap)

        # Verify skill availability
        available_skills = self.skill_tree_manager.get_available_skills(self.player, self.class_manager)
        available_skill_ids = [s.id for s in available_skills]

        # At level 10, the Knight should have access to their new skill
        self.assertIn('knights_valor', available_skill_ids)
        # And should not have access to other classes' skills
        self.assertNotIn('twin_shot', available_skill_ids)
        self.assertNotIn('fireball', available_skill_ids)

if __name__ == '__main__':
    unittest.main()

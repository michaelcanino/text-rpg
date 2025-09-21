# AGENTS.md

## Overview
This project is a **text-based RPG framework**.  
The codebase is organized into **agents** (classes, managers, systems) that handle world simulation, player actions, combat, and progression.  

Each agent has a clear role and interacts with others to create the game loop.

---

## Core Agents

### Player
| Role | Tracks and manages the player character. |
|------|-------------------------------------------|
| **Stats** | `hp`, `attack_power`, `level`, `xp`, `class_id`, `critical_chance` |
| **Systems** | Inventory, quests, skills, discovered locations |
| **Key Methods** | `move(direction)`, `retreat()`, `check_conditions(…)`, `add_xp(amount)`, `recalculate_stats(…)` |

---

### NPC (Non-Player Character)
| Role | Characters the player can talk to. |
|------|-------------------------------------|
| **Data Source** | Defined in `game_data.json` |
| **Abilities** | Give quests, items, or healing; teach skills; provide dialogue based on quest state |

---

### Merchant (subclass of NPC)
| Role | An NPC who buys and sells items. |
|------|-----------------------------------|
| **Data Source** | Defined in `game_data.json` with `npc_type: "Merchant"` |
| **Attributes** | `inventory`, `gold`, `item_sell_counts` |
| **Behavior** | Prices for items sold by the player decrease as the merchant's stock of that item increases. Inventory restocks after a set number of turns. |

---

### Monster
| Role | Enemy characters the player can fight. |
|------|-----------------------------------------|
| **Data Source** | Defined in `game_data.json` |
| **Attributes** | `hp`, `attack_power`, `xp_reward`, optional drops |
| **Special** | Can complete quests or spawn new monsters on defeat |

---

### Items
| Type | Function |
|------|----------|
| **Potion** | Restores HP |
| **EffectPotion** | Grants temporary status effects |
| **OffensiveItem** | Deals damage to enemies |
| **Container** | Stores other items |
| **Special** | Some items can teach skills (e.g., Ancient Tome) |

---

### Locations
| Type | Behavior |
|------|----------|
| **City** | Safe hub with NPCs |
| **Wilderness** | Spawns monsters randomly |
| **Dungeon** | May include hazards (e.g., Goblin Cave stench) |
| **Swamp** | Requires a lantern to see full description |
| **Volcanic** | Inflicts fire damage unless protected |
| **Shared Features** | Contain exits, NPCs, monsters, items, conditional exits |

---

## Manager Agents

### SkillTreeManager
- Stores all skills.  
- Checks prerequisites before learning (`level`, other skills).  
- Unlocks skills, applies effects, links active abilities to the player.  

### ClassManager
- Manages player classes (Knight, Ranger, Mage).  
- Each class has:
  - Base stat bonuses.  
  - Starting skills.  
  - A unique skill pool.  
- Class choice is forced at **level 10** and is permanent.  

### LevelUpManager
- Presents stat upgrade choices:
  - +10 Max HP  
  - +2 Attack Power  
  - +5% Critical Chance  
- Applies the chosen effect and updates stats.  

### TimeManager
- Tracks the number of turns that have passed in the game.
- Triggers events at set intervals, such as merchant restocking.

### World Builder (`world.py`)
- Loads all **items, monsters, NPCs, and locations** from `game_data.json`.  
- Connects exits and conditional exits.  
- Creates `Player` at starting location.  
- Generates ASCII world map for exploration.  

---

## Conventions

- **Dialogue**: Driven by quest state (e.g., `quest_active`, `quest_completed`).  
- **Skills**: Defined with `requirements`, `cost`, `effect`. Can be passive (stat boosts) or active (combat abilities).  
- **Combat**:
  - Player chooses actions (attack, ability, use item).  
  - Monsters auto-attack each turn.  
  - Status effects and cooldowns tick down.  
- **Persistence**: Player state saved in `save_data.json`.  

---

## Example Gameplay Flow

1. **Exploration**
   - Player starts in a **City (Oakhaven)**.  
   - They see NPCs (Old Man Willow, Sister Elira).  
   - They can look around, view the map, or talk to NPCs.  

2. **Quest**
   - Talking to Old Man Willow triggers a **quest** (`Clear the Sunken Swamp`).  
   - The NPC may also give starting items (lantern, potions).  

3. **Skill Learning**
   - Player visits Sage Rowan.  
   - If requirements are met (e.g., Level 10 for Fireball), Sage can **teach skills**.  

4. **Combat**
   - Entering the **Whispering Woods** spawns monsters (Goblin).  
   - Player chooses to attack, use a skill, or consume an item.  
   - Monsters retaliate automatically.  
   - Victory may drop loot or progress quests.  

5. **Level Up**
   - Defeating monsters grants XP.  
   - Upon leveling, the **LevelUpManager** offers stat upgrade choices.  
   - At Level 10, the **ClassManager** forces a permanent class choice (Knight, Ranger, Mage).  

6. **World Hazards**
   - Entering the **Ashen Peaks (Volcanic)** applies fire damage unless the player has **Fireproof Armor** or an active **fire resistance effect**.  
   - Exploring the **Swamp** requires a lantern to see its full description.  

7. **Progression**
   - Player completes quests, discovers hidden areas (e.g., Hidden Shrine), unlocks skills, and grows stronger.  
   - Game progress is saved into `save_data.json` and can be resumed later.  

---

## Maintenance Notes
- Update this file when adding:
  - New NPC behaviors (e.g., teaching methods).  
  - New managers (e.g., `FactionManager`, `EconomyManager`).  
  - New skill or item conventions.

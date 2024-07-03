SHOCKLANDS = ["Hallowed Fountain", "Godless Shrine", "Sacred Foundry", "Temple Garden", "Watery Grave", "Steam Vents",
              "Breeding Pool", "Blood Crypt", "Overgrown Tomb", "Stomping Ground"]

FETCHLANDS = ["Flooded Strand", "Marsh Flats", "Arid Mesa", "Windswept Heath", "Polluted Delta", "Scalding Tarn",
              "Misty Rainforest", "Bloodstained Mire", "Verdant Catacombs", "Wooded Foothills"]

BASIC_LANDS = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

MODERN_METAGAME_5_2024 = ["Amulet of Vigor", "Urza's Tower", "Goblin Guide", "Yawgmoth, Thran Physician", "Hedron Crab",
                   "Indomitable Creativity", "Not Dead After All", "Omnath, Locus of Creation", "Living End",
                   "Goryo's Vengeance", "Murktide Regent", "Slickshot Show-Off"]

MODERN_METAGAME_7_2024 = ["Nadu, Winged Wisdom", "Necrodominance", "Ruby Medallion", "Living End", "Guide of Souls",
                   "Tune the Narrative", "Goryo's Vengeance", "Murktide Regent", "Through the Breach", "Slickshot Show-Off"]

MODERN_EXILE_REMOVAL = ["Path to Exile", "Leyline Binding", "Celestial Purge", "Prismatic Ending", "Dispatch"
                        "Vanishing Verse", "March of Otherworldly Light"]

MODERN_ALL_CREATURE_REMOVAL = MODERN_EXILE_REMOVAL + ["Fatal Push", "Dismember", "Lightning Bolt", "Unholy Heat",
                                                     "Sheoldred's Edict", "Flare of Malice"]

MODERN_ARTIFACT_HATE = ["Meltdown", "Shattering Spree", "Disenchant", "Force of Vigor"]

MODERN_COUNTERS = ["Counterspell", "Spell Pierce", "Stubborn Denial", "Stern Scolding", "Force of Negation", "Flare of Denial",
                   "Remand", "Reprieve", "Flusterstorm", "Consign to Memory", "No More Lies"]

MODERN_GRAVEYARD_HATE = ["Leyline of the Void", "Surgical Extraction", "Unlicensed Hearse", "Endurance", "Soul-Guide Lantern",
                         "Relic of Progenitus", "Rest in Peace", "Dauthi Voidwalker", "Crypt Incursion"]

MH2_ELEMENTALS = ["Solitude", "Subtlety", "Grief", "Fury", "Endurance"]



# Store these lists in a gui so they can be accessed easily via the GUI
CARD_GROUP_DICT: dict[str: list[str]] = {"Shocklands": SHOCKLANDS,
                                         "Fetchlands": FETCHLANDS,
                                         "Basic Lands": BASIC_LANDS,
                                         "Modern Metagame 5-2024 (Pre-MH3)": MODERN_METAGAME_5_2024,
                                         "Modern Metagame 7-2024 (Post-MH3)": MODERN_METAGAME_7_2024,
                                         "Modern Exile Removal": MODERN_EXILE_REMOVAL,
                                         "Modern ALl Creature Removal": MODERN_ALL_CREATURE_REMOVAL,
                                         "Modern Artifact Hate": MODERN_ARTIFACT_HATE,
                                         "Modern Counters": MODERN_COUNTERS,
                                         "Modern Graveyard Hate": MODERN_GRAVEYARD_HATE,
                                         "MH2 Elementals": MH2_ELEMENTALS
                                         }
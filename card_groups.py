SHOCKLANDS = [
    "Hallowed Fountain", "Godless Shrine", "Sacred Foundry", "Temple Garden", "Watery Grave", "Steam Vents",
    "Breeding Pool", "Blood Crypt", "Overgrown Tomb", "Stomping Ground"
]

FETCHLANDS = [
    "Flooded Strand", "Marsh Flats", "Arid Mesa", "Windswept Heath", "Polluted Delta", "Scalding Tarn",
    "Misty Rainforest", "Bloodstained Mire", "Verdant Catacombs", "Wooded Foothills"
]

BASIC_LANDS = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

MH2_ELEMENTALS = ["Solitude", "Subtlety", "Grief", "Fury", "Endurance"]


class Modern:
    """Collections of cards specifically utilized in Modern."""

    EXILE_REMOVAL = [
        "Path to Exile", "Leyline Binding", "Celestial Purge", "Prismatic Ending", "Dispatch", "Vanishing Verse",
        "March of Otherworldly Light"
    ]

    WRATHS = [
        "Supreme Verdict", "Damn", "Wrath of the Skies", "Kozilek's Return", "Pyroclasm", "Hurkyl's Recall",
        "Whipflare"
    ]

    ALL_CREATURE_REMOVAL = WRATHS + EXILE_REMOVAL + [
        "Fatal Push", "Dismember", "Lightning Bolt", "Unholy Heat", "Sheoldred's Edict", "Flare of Malice"
    ]

    ARTIFACT_HATE = ["Meltdown", "Shattering Spree", "Disenchant", "Force of Vigor"]

    COUNTERS = [
        "Counterspell", "Spell Pierce", "Stubborn Denial", "Stern Scolding", "Force of Negation", "Flare of Denial",
        "Remand", "Reprieve", "Flusterstorm", "Consign to Memory", "No More Lies"
    ]

    GRAVEYARD_HATE = [
        "Leyline of the Void", "Surgical Extraction", "Unlicensed Hearse", "Endurance", "Soul-Guide Lantern",
        "Relic of Progenitus", "Rest in Peace", "Dauthi Voidwalker", "Crypt Incursion"
    ]


# Store these lists in a gui so they can be accessed easily via the GUI
CARD_GROUP_DICT: dict[str, list[str]] = {

    "Shocklands": SHOCKLANDS,
    "Fetchlands": FETCHLANDS,
    "Basic Lands": BASIC_LANDS,
    "Modern Exile Removal": Modern.EXILE_REMOVAL,
    "Modern All Creature Removal": Modern.ALL_CREATURE_REMOVAL,
    "Modern Artifact Hate": Modern.ARTIFACT_HATE,
    "Modern Counters": Modern.COUNTERS,
    "Modern Graveyard Hate": Modern.GRAVEYARD_HATE,
    "MH2 Elementals": MH2_ELEMENTALS
}

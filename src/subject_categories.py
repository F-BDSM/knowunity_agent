"""Subject categorization and cognitive level definitions."""

from enum import Enum
from typing import Dict, List


class SubjectCategory(str, Enum):
    """Major subject categories."""
    HARD_SCIENCES = "Hard Sciences"
    HUMANITIES = "Humanities"
    INTERPRETIVE_ARTS = "Interpretive Arts"


class CognitiveLevel(str, Enum):
    """Cognitive complexity levels based on Bloom's taxonomy."""
    RECALL = "Recall & Facts"
    PROCEDURAL = "Procedural"
    CONCEPTUAL = "Conceptual"
    APPLICATION = "Application"
    SYNTHESIS = "Synthesis"


# Subject to category mapping
SUBJECT_CATEGORIES: Dict[str, SubjectCategory] = {
    # Hard Sciences
    "Math": SubjectCategory.HARD_SCIENCES,
    "Mathematics": SubjectCategory.HARD_SCIENCES,
    "Physics": SubjectCategory.HARD_SCIENCES,
    "Chemistry": SubjectCategory.HARD_SCIENCES,
    "Biology": SubjectCategory.HARD_SCIENCES,
    
    # Humanities
    "History": SubjectCategory.HUMANITIES,
    "Geography": SubjectCategory.HUMANITIES,
    "English": SubjectCategory.HUMANITIES,
    "Social Studies": SubjectCategory.HUMANITIES,
    
    # Interpretive Arts
    "German Literature": SubjectCategory.INTERPRETIVE_ARTS,
    "English Literature": SubjectCategory.INTERPRETIVE_ARTS,
    "Literature": SubjectCategory.INTERPRETIVE_ARTS,
    "Art": SubjectCategory.INTERPRETIVE_ARTS,
    "Music": SubjectCategory.INTERPRETIVE_ARTS,
}


# Cognitive level progression mapping
LEVEL_CONFIG = {
    1: {
        "level": CognitiveLevel.RECALL,
        "turns": (1, 2),
        "description": "Simple definitions. 'What is X?'",
        "rating_on_success": 1,
        "next_turn_on_success": 3,
    },
    2: {
        "level": CognitiveLevel.PROCEDURAL,
        "turns": (3, 4),
        "description": "Standard execution. 'Calculate this.' 'List the events.'",
        "rating_on_success": 2,
        "next_turn_on_success": 5,
    },
    3: {
        "level": CognitiveLevel.CONCEPTUAL,
        "turns": (5, 6),
        "description": "The 'Why'. 'Why does this step work?'",
        "rating_on_success": 3,
        "next_turn_on_success": 7,
    },
    4: {
        "level": CognitiveLevel.APPLICATION,
        "turns": (7, 8),
        "description": "Nuance/Word Problems. 'Apply this to a weird situation.'",
        "rating_on_success": 4,
        "next_turn_on_success": 9,
    },
    5: {
        "level": CognitiveLevel.SYNTHESIS,
        "turns": (9, 10),
        "description": "Transfer/Creation. 'Connect this to [Other Subject] or create a rule.'",
        "rating_on_success": 5,
        "next_turn_on_success": None,  # Final level
    },
}


def get_subject_category(subject_name: str) -> SubjectCategory:
    """Get the category for a subject name."""
    return SUBJECT_CATEGORIES.get(subject_name, SubjectCategory.HARD_SCIENCES)


def get_level_for_turn(turn_number: int) -> int:
    """Determine which cognitive level corresponds to a turn number."""
    for level_num, config in LEVEL_CONFIG.items():
        min_turn, max_turn = config["turns"]
        if min_turn <= turn_number <= max_turn:
            return level_num
    # Default to highest level if beyond turn 10
    return 5


def get_level_config(level_num: int) -> Dict:
    """Get configuration for a specific level."""
    return LEVEL_CONFIG.get(level_num, LEVEL_CONFIG[5])


def get_all_subjects_by_category() -> Dict[SubjectCategory, List[str]]:
    """Group all subjects by their category."""
    result: Dict[SubjectCategory, List[str]] = {
        SubjectCategory.HARD_SCIENCES: [],
        SubjectCategory.HUMANITIES: [],
        SubjectCategory.INTERPRETIVE_ARTS: [],
    }
    
    for subject, category in SUBJECT_CATEGORIES.items():
        result[category].append(subject)
    
    return result

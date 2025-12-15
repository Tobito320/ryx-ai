"""
Intelligent Rubric Generator - Stage 4

Generates domain-aware, flexible rubrics for exam questions based on:
- Question type (MC, short answer, scenario, etc.)
- Educational context (ITIL, IT Service, vocational level)
- Difficulty level
- Expected competencies

Rubrics define success at multiple levels (not just right/wrong) and
account for partial understanding, paraphrasing, and German language conventions.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class RubricLevel(str, Enum):
    """Rubric scoring levels"""
    FULL_POINTS = "full_points"
    PARTIAL_75 = "partial_points_75_percent"
    PARTIAL_50 = "partial_points_50_percent"
    MINIMAL = "minimal_points"
    ZERO = "zero_points"


@dataclass
class RubricCriterion:
    """Single criterion within a rubric"""
    name: str
    description: str
    max_points: float
    keywords: List[str] = None  # Optional expected keywords


@dataclass
class RubricLevel:
    """Scoring level within a rubric"""
    score: float
    criteria: List[str]  # What must be present
    notes: Optional[str] = None


@dataclass
class IntelligentRubric:
    """Complete rubric for a question"""
    question_id: str
    question_text: str
    question_type: str
    max_points: int
    difficulty: int  # 1-5
    
    # Rubric levels
    full_points: Dict[str, Any]
    partial_75: Optional[Dict[str, Any]] = None
    partial_50: Optional[Dict[str, Any]] = None
    minimal: Optional[Dict[str, Any]] = None
    zero_points: Dict[str, Any] = None
    
    # Additional metadata
    auto_gradable: bool = False
    partial_credit_allowed: bool = True
    acceptable_answers: List[str] = None  # For validation
    common_misconceptions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return asdict(self)


async def generate_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int = 5,
    difficulty: int = 3,
    subject_context: str = "it_service",
    model_answer: Optional[str] = None
) -> IntelligentRubric:
    """
    Generate intelligent rubric for a question.
    
    Args:
        question_id: Unique question identifier
        question_text: Full question text
        question_type: Type of question (MC, ShortAnswer, etc.)
        max_points: Maximum points available
        difficulty: 1-5 difficulty level
        subject_context: Domain context (it_service, wbl, etc.)
        model_answer: Optional model answer for reference
    
    Returns:
        IntelligentRubric with multi-level scoring criteria
    """
    
    logger.info(f"Generating rubric for {question_id} ({question_type})")
    
    # Route to specialized generator based on question type
    if question_type.startswith("MC"):
        return _generate_mc_rubric(
            question_id, question_text, question_type, max_points
        )
    elif question_type in ["ShortAnswer", "Explanation"]:
        return await _generate_open_rubric(
            question_id, question_text, question_type, max_points,
            difficulty, subject_context, model_answer
        )
    elif question_type == "CaseStudy":
        return await _generate_scenario_rubric(
            question_id, question_text, max_points, difficulty, subject_context
        )
    elif question_type == "Calculation":
        return _generate_calculation_rubric(
            question_id, question_text, max_points
        )
    else:
        # Generic rubric
        return _generate_generic_rubric(
            question_id, question_text, question_type, max_points
        )


def _generate_mc_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int
) -> IntelligentRubric:
    """Generate rubric for multiple choice questions (deterministic)"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=1,  # MC is usually easier
        full_points={
            "score": max_points,
            "criteria": ["Correct option(s) selected"],
            "notes": "Multiple choice - all or nothing"
        },
        zero_points={
            "score": 0,
            "criteria": ["Incorrect option(s) selected or no answer"]
        },
        auto_gradable=True,
        partial_credit_allowed=False,  # Typically no partial credit for MC
        common_misconceptions=[]
    )


async def _generate_open_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int,
    difficulty: int,
    subject_context: str,
    model_answer: Optional[str]
) -> IntelligentRubric:
    """
    Generate rubric for open-ended questions using domain knowledge.
    
    This is where AI-powered rubric generation shines - we analyze the
    question to determine what constitutes good/partial/poor answers.
    """
    
    # Extract key concepts from question
    concepts = _extract_key_concepts(question_text, subject_context)
    
    # Build rubric based on question characteristics
    if _is_definition_question(question_text):
        return _build_definition_rubric(
            question_id, question_text, question_type, max_points, concepts
        )
    elif _is_enumeration_question(question_text):
        return _build_enumeration_rubric(
            question_id, question_text, question_type, max_points, concepts
        )
    elif _is_explanation_question(question_text):
        return _build_explanation_rubric(
            question_id, question_text, question_type, max_points, concepts, difficulty
        )
    else:
        # Generic open answer rubric
        return _build_generic_open_rubric(
            question_id, question_text, question_type, max_points, concepts
        )


def _extract_key_concepts(question_text: str, subject_context: str) -> List[str]:
    """Extract key concepts that should appear in answer"""
    
    concepts = []
    text_lower = question_text.lower()
    
    # ITIL/IT Service concepts
    if subject_context == "it_service":
        itil_concepts = {
            'incident': ['incident', 'störung', 'fehler', 'ausfall'],
            'problem': ['problem', 'ursache', 'root cause'],
            'change': ['change', 'änderung', 'änderungsmanagement'],
            'sla': ['sla', 'service level', 'vereinbarung', 'kennzahl'],
            'ticket': ['ticket', 'meldung', 'anfrage'],
            'escalation': ['eskalation', 'eskalieren', 'weiterleitung'],
            'priority': ['priorität', 'dringlichkeit', 'impact'],
            'service_desk': ['service desk', 'helpdesk', 'support']
        }
        
        for concept, keywords in itil_concepts.items():
            if any(kw in text_lower for kw in keywords):
                concepts.append(concept)
    
    # WBL concepts
    elif subject_context == "wbl":
        wbl_concepts = {
            'marketing': ['marketing', 'markt', '4p', 'produkt', 'preis'],
            'marktforschung': ['marktforschung', 'analyse', 'studie'],
            'primär': ['primärforschung', 'primär', 'befragung'],
            'sekundär': ['sekundärforschung', 'sekundär', 'daten']
        }
        
        for concept, keywords in wbl_concepts.items():
            if any(kw in text_lower for kw in keywords):
                concepts.append(concept)
    
    return concepts


def _is_definition_question(question_text: str) -> bool:
    """Check if question asks for definition"""
    keywords = ['was ist', 'was versteht man', 'definieren sie', 'erklären sie den begriff']
    return any(kw in question_text.lower() for kw in keywords)


def _is_enumeration_question(question_text: str) -> bool:
    """Check if question asks for list/enumeration"""
    keywords = ['nennen sie', 'listen sie', 'zählen sie', 'welche']
    return any(kw in question_text.lower() for kw in keywords)


def _is_explanation_question(question_text: str) -> bool:
    """Check if question asks for detailed explanation"""
    keywords = ['erläutern sie', 'beschreiben sie', 'begründen sie', 'erklären sie']
    return any(kw in question_text.lower() for kw in keywords)


def _build_definition_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int,
    concepts: List[str]
) -> IntelligentRubric:
    """Build rubric for definition questions"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=2,
        full_points={
            "score": max_points,
            "criteria": [
                "Vollständige, korrekte Definition gegeben",
                "Fachbegriffe korrekt verwendet",
                "Alle relevanten Aspekte erwähnt",
                "Klare, verständliche Formulierung"
            ],
            "notes": "Vollständige Definition mit allen Komponenten"
        },
        partial_75={
            "score": max_points * 0.75,
            "criteria": [
                "Definition im Kern korrekt",
                "Ein oder zwei Aspekte fehlen",
                "Fachbegriffe größtenteils korrekt"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                "Grundverständnis erkennbar",
                "Definition unvollständig oder vage",
                "Einige Fachbegriffe fehlen"
            ]
        },
        minimal={
            "score": max_points * 0.25,
            "criteria": [
                "Ansatz erkennbar",
                "Große Lücken in der Definition",
                "Vage oder falsche Formulierungen"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": [
                "Keine Antwort oder völlig falsch",
                "Kein Verständnis erkennbar"
            ]
        },
        auto_gradable=False,
        partial_credit_allowed=True,
        acceptable_answers=[
            "Paraphrasierte Definition akzeptabel",
            "Eigene Worte erlaubt wenn Verständnis klar"
        ],
        common_misconceptions=[
            "Verwechslung mit ähnlichen Begriffen"
        ]
    )


def _build_enumeration_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int,
    concepts: List[str]
) -> IntelligentRubric:
    """Build rubric for enumeration/listing questions"""
    
    # Extract expected count (e.g., "nennen Sie 5")
    import re
    count_match = re.search(r'(\d+)', question_text)
    expected_count = int(count_match.group(1)) if count_match else 3
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=2,
        full_points={
            "score": max_points,
            "criteria": [
                f"Alle {expected_count} geforderten Punkte genannt",
                "Alle Punkte korrekt und relevant",
                "Fachbegriffe korrekt verwendet"
            ],
            "notes": f"Alle {expected_count} Punkte vollständig"
        },
        partial_75={
            "score": max_points * 0.75,
            "criteria": [
                f"Mindestens {expected_count - 1} Punkte genannt",
                "Alle genannten Punkte korrekt"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                f"Etwa die Hälfte der Punkte genannt",
                "Größtenteils korrekt"
            ]
        },
        minimal={
            "score": max_points * 0.25,
            "criteria": [
                "Weniger als die Hälfte genannt",
                "Einige korrekte Punkte vorhanden"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": ["Keine oder nur falsche Punkte genannt"]
        },
        auto_gradable=False,
        partial_credit_allowed=True
    )


def _build_explanation_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int,
    concepts: List[str],
    difficulty: int
) -> IntelligentRubric:
    """Build rubric for explanation questions (most complex)"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=difficulty,
        full_points={
            "score": max_points,
            "criteria": [
                "Vollständige, strukturierte Erklärung",
                "Alle relevanten Aspekte adressiert",
                "Logischer Zusammenhang erkennbar",
                "Fachterminologie korrekt angewendet",
                "Beispiele/Kontext gegeben (falls verlangt)"
            ],
            "notes": "Umfassende Erklärung mit Tiefe"
        },
        partial_75={
            "score": max_points * 0.75,
            "criteria": [
                "Erklärung im Kern korrekt",
                "Die meisten Aspekte behandelt",
                "Kleinere Lücken oder Ungenauigkeiten"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                "Grundverständnis vorhanden",
                "Wesentliche Punkte fehlen oder vage",
                "Erklärung unvollständig"
            ]
        },
        minimal={
            "score": max_points * 0.25,
            "criteria": [
                "Ansatz erkennbar",
                "Große Wissenslücken",
                "Erklärung unklar oder fehlerhaft"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": [
                "Keine Antwort oder völlig irrelevant",
                "Kein Verständnis erkennbar"
            ]
        },
        auto_gradable=False,
        partial_credit_allowed=True,
        acceptable_answers=[
            "Paraphrasierung akzeptabel wenn korrekt",
            "Eigene Beispiele erlaubt",
            "Verschiedene Erklärungsansätze möglich"
        ]
    )


def _build_generic_open_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int,
    concepts: List[str]
) -> IntelligentRubric:
    """Generic rubric for unclassified open questions"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=3,
        full_points={
            "score": max_points,
            "criteria": [
                "Frage vollständig beantwortet",
                "Inhaltlich korrekt",
                "Angemessene Detailtiefe"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                "Teilweise beantwortet",
                "Grundverständnis erkennbar"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": ["Keine oder falsche Antwort"]
        },
        auto_gradable=False,
        partial_credit_allowed=True
    )


async def _generate_scenario_rubric(
    question_id: str,
    question_text: str,
    max_points: int,
    difficulty: int,
    subject_context: str
) -> IntelligentRubric:
    """Generate rubric for case study/scenario questions"""
    
    # Scenarios typically assess application of knowledge
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type="CaseStudy",
        max_points=max_points,
        difficulty=difficulty,
        full_points={
            "score": max_points,
            "criteria": [
                "Situation vollständig analysiert",
                "Lösungsansatz entwickelt und begründet",
                "Fachkonzepte korrekt angewendet",
                "Praxisbezug hergestellt",
                "Alternative Ansätze erwähnt (falls relevant)"
            ],
            "notes": "Umfassende Bearbeitung mit Anwendung"
        },
        partial_75={
            "score": max_points * 0.75,
            "criteria": [
                "Analyse größtenteils korrekt",
                "Lösung entwickelt, aber mit Lücken",
                "Fachkonzepte angewendet"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                "Situation teilweise verstanden",
                "Lösungsansatz vorhanden, aber unvollständig",
                "Einige Fachkonzepte angewendet"
            ]
        },
        minimal={
            "score": max_points * 0.25,
            "criteria": [
                "Grundverständnis der Situation",
                "Lösungsansatz vage oder fehlerhaft"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": ["Keine Bearbeitung oder völlig am Thema vorbei"]
        },
        auto_gradable=False,
        partial_credit_allowed=True,
        acceptable_answers=[
            "Verschiedene Lösungsansätze akzeptabel wenn begründet",
            "Kreative Ansätze werden honoriert"
        ]
    )


def _generate_calculation_rubric(
    question_id: str,
    question_text: str,
    max_points: int
) -> IntelligentRubric:
    """Generate rubric for calculation questions"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type="Calculation",
        max_points=max_points,
        difficulty=3,
        full_points={
            "score": max_points,
            "criteria": [
                "Korrekte Formel verwendet",
                "Rechnung nachvollziehbar dargestellt",
                "Ergebnis korrekt",
                "Einheiten korrekt angegeben"
            ],
            "notes": "Vollständige Rechnung mit richtigem Ergebnis"
        },
        partial_75={
            "score": max_points * 0.75,
            "criteria": [
                "Formel korrekt, kleiner Rechenfehler",
                "Oder: Rechnung korrekt, Formel minimal falsch"
            ]
        },
        partial_50={
            "score": max_points * 0.5,
            "criteria": [
                "Richtiger Ansatz erkennbar",
                "Formel oder Rechnung teilweise korrekt"
            ]
        },
        minimal={
            "score": max_points * 0.25,
            "criteria": [
                "Ansatz vorhanden",
                "Wesentliche Fehler in Formel oder Rechnung"
            ]
        },
        zero_points={
            "score": 0,
            "criteria": ["Keine Rechnung oder völlig falsch"]
        },
        auto_gradable=False,
        partial_credit_allowed=True,
        acceptable_answers=[
            "Zwischenschritte müssen nachvollziehbar sein",
            "Rundungsfehler akzeptabel"
        ]
    )


def _generate_generic_rubric(
    question_id: str,
    question_text: str,
    question_type: str,
    max_points: int
) -> IntelligentRubric:
    """Fallback generic rubric"""
    
    return IntelligentRubric(
        question_id=question_id,
        question_text=question_text[:200],
        question_type=question_type,
        max_points=max_points,
        difficulty=3,
        full_points={
            "score": max_points,
            "criteria": ["Vollständig und korrekt beantwortet"]
        },
        zero_points={
            "score": 0,
            "criteria": ["Nicht beantwortet oder falsch"]
        },
        auto_gradable=False,
        partial_credit_allowed=True
    )

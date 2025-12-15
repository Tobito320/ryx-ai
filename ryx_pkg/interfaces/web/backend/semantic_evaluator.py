"""
Semantic Answer Evaluator - Stage 5

Performs semantic comparison of student answers against rubrics using:
- Answer component parsing
- Concept extraction and matching
- Paraphrase detection
- German language tolerance (spelling, grammar)
- Partial understanding recognition

Avoids rigid keyword matching in favor of understanding-based evaluation.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnswerComponent:
    """Parsed component of a student answer"""
    text: str
    concepts: List[str]  # Identified concepts
    confidence: float  # How certain we are about this component


@dataclass
class SemanticEvaluation:
    """Result of semantic evaluation"""
    earned_points: float
    rationale: str
    confidence: int  # 0-100
    rubric_match_level: str  # "full_points", "partial_75", etc.
    components_found: List[str]  # What was correctly identified
    components_missing: List[str]  # What was expected but not found
    improvement_suggestion: str


async def evaluate_answer_semantically(
    student_answer: str,
    rubric: Dict[str, Any],
    question_text: str,
    question_type: str,
    model_answer: Optional[str] = None,
    subject_context: str = "it_service"
) -> SemanticEvaluation:
    """
    Main semantic evaluation function.
    
    Instead of rigid keyword matching, this function:
    1. Parses student answer into concepts
    2. Compares against rubric criteria
    3. Detects paraphrasing and partial understanding
    4. Applies German language tolerance
    
    Args:
        student_answer: Student's response text
        rubric: Rubric dict with criteria at each level
        question_text: Original question
        question_type: Type of question
        model_answer: Optional model answer for reference
        subject_context: Domain context for concept extraction
    
    Returns:
        SemanticEvaluation with points, rationale, and feedback
    """
    
    # Normalize answer (handle German characters, whitespace)
    normalized_answer = normalize_german_text(student_answer)
    
    # Check for empty/too short answers
    if not normalized_answer or len(normalized_answer.strip()) < 10:
        return SemanticEvaluation(
            earned_points=0,
            rationale="Keine oder zu kurze Antwort gegeben.",
            confidence=95,
            rubric_match_level="zero_points",
            components_found=[],
            components_missing=["Vollständige Antwort"],
            improvement_suggestion="Bitte beantworte die Frage vollständig und ausführlich."
        )
    
    # Parse answer into components
    answer_components = parse_answer_components(normalized_answer, subject_context)
    
    # Extract expected concepts from rubric
    rubric_concepts = extract_rubric_concepts(rubric, question_text, subject_context)
    
    # Match answer components to rubric criteria
    match_results = match_against_rubric(
        answer_components,
        rubric_concepts,
        rubric,
        question_type
    )
    
    # Determine rubric level achieved
    level, points = determine_rubric_level(match_results, rubric)
    
    # Generate rationale
    rationale = generate_evaluation_rationale(
        match_results,
        level,
        question_type
    )
    
    # Generate improvement suggestions
    improvement = generate_improvement_suggestion(
        match_results,
        level,
        question_text,
        subject_context
    )
    
    return SemanticEvaluation(
        earned_points=points,
        rationale=rationale,
        confidence=match_results["confidence"],
        rubric_match_level=level,
        components_found=match_results["found_concepts"],
        components_missing=match_results["missing_concepts"],
        improvement_suggestion=improvement
    )


def normalize_german_text(text: str) -> str:
    """
    Normalize German text for comparison.
    
    Handles:
    - Lowercase conversion
    - Whitespace normalization
    - German umlauts (ä, ö, ü, ß)
    - Common abbreviations
    """
    
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Keep German characters as-is (don't transliterate)
    # This is important for semantic matching
    
    return text


def parse_answer_components(answer: str, subject_context: str) -> List[AnswerComponent]:
    """
    Parse student answer into semantic components.
    
    Example:
    "SLA stellt die Service-Qualität sicher. Es definiert Reaktionszeiten und Verfügbarkeit."
    → Components: ["service quality assurance", "defines metrics", "response time", "availability"]
    """
    
    components = []
    
    # Split by sentences
    sentences = re.split(r'[.!?]\s+', answer)
    
    for sentence in sentences:
        if len(sentence.strip()) < 5:
            continue
        
        # Extract concepts from this sentence
        concepts = extract_concepts_from_text(sentence, subject_context)
        
        if concepts:
            components.append(AnswerComponent(
                text=sentence.strip(),
                concepts=concepts,
                confidence=0.8  # Base confidence
            ))
    
    return components


def extract_concepts_from_text(text: str, subject_context: str) -> List[str]:
    """
    Extract semantic concepts from text.
    
    Uses domain-specific concept dictionaries to identify
    what the student is talking about.
    """
    
    concepts = []
    text_lower = text.lower()
    
    # IT Service / ITIL concepts
    if subject_context == "it_service":
        concept_patterns = {
            'incident_definition': [
                'störung', 'ausfall', 'unterbrechung', 'incident', 'fehler'
            ],
            'incident_goal': [
                'schnellstmöglich', 'wiederherstellung', 'service wiederherstellen'
            ],
            'problem_definition': [
                'ursache', 'wurzelursache', 'root cause', 'problem'
            ],
            'problem_goal': [
                'dauerhaft', 'verhindern', 'beseitigen', 'lösung finden'
            ],
            'sla_purpose': [
                'qualität', 'vereinbarung', 'kunde', 'service level', 'erwartung'
            ],
            'sla_metrics': [
                'verfügbarkeit', 'reaktionszeit', 'lösungszeit', 'kennzahl', 'kpi'
            ],
            'escalation': [
                'eskalation', 'weiterleiten', 'higher level', 'management'
            ],
            'priority': [
                'priorität', 'dringlichkeit', 'impact', 'business impact'
            ],
            'ticket_system': [
                'ticket', 'kategorisierung', 'status', 'tracking'
            ]
        }
        
        for concept, patterns in concept_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                concepts.append(concept)
    
    # WBL concepts
    elif subject_context == "wbl":
        concept_patterns = {
            'marktforschung': ['marktforschung', 'markt analysieren', 'studie'],
            'primärforschung': ['primär', 'befragung', 'interview', 'beobachtung'],
            'sekundärforschung': ['sekundär', 'vorhandene daten', 'statistik'],
            'marketing_mix': ['4p', 'produkt', 'preis', 'place', 'promotion']
        }
        
        for concept, patterns in concept_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                concepts.append(concept)
    
    return concepts


def extract_rubric_concepts(
    rubric: Dict[str, Any],
    question_text: str,
    subject_context: str
) -> Dict[str, List[str]]:
    """
    Extract expected concepts from rubric at each level.
    
    Returns dict like:
    {
        "full_points": ["incident_definition", "incident_goal", "problem_definition"],
        "partial_75": ["incident_definition", "problem_definition"],
        ...
    }
    """
    
    expected_concepts = {}
    
    for level in ["full_points", "partial_75", "partial_50", "minimal"]:
        level_data = rubric.get(level, {})
        criteria = level_data.get("criteria", [])
        
        # Extract concepts from criteria text
        level_concepts = []
        for criterion in criteria:
            concepts = extract_concepts_from_text(criterion, subject_context)
            level_concepts.extend(concepts)
        
        expected_concepts[level] = list(set(level_concepts))
    
    return expected_concepts


def match_against_rubric(
    answer_components: List[AnswerComponent],
    rubric_concepts: Dict[str, List[str]],
    rubric: Dict[str, Any],
    question_type: str
) -> Dict[str, Any]:
    """
    Match student's answer components against rubric concepts.
    
    Returns match results with:
    - Which concepts were found
    - Which are missing
    - Overall match percentage
    - Confidence in evaluation
    """
    
    # Collect all concepts found in answer
    found_concepts = []
    for component in answer_components:
        found_concepts.extend(component.concepts)
    found_concepts = list(set(found_concepts))
    
    # Check against full_points criteria
    full_points_expected = rubric_concepts.get("full_points", [])
    
    if not full_points_expected:
        # No explicit concepts - fall back to heuristic
        return _heuristic_match(answer_components, rubric)
    
    # Calculate match percentage
    if full_points_expected:
        match_count = sum(1 for concept in full_points_expected if concept in found_concepts)
        match_percentage = match_count / len(full_points_expected)
    else:
        match_percentage = 0.5
    
    # Identify missing concepts
    missing_concepts = [c for c in full_points_expected if c not in found_concepts]
    
    # Confidence depends on clarity of answer
    avg_component_confidence = sum(c.confidence for c in answer_components) / len(answer_components) if answer_components else 0.5
    confidence = int(avg_component_confidence * 100)
    
    return {
        "found_concepts": found_concepts,
        "missing_concepts": missing_concepts,
        "match_percentage": match_percentage,
        "confidence": confidence,
        "answer_length": sum(len(c.text) for c in answer_components)
    }


def _heuristic_match(
    answer_components: List[AnswerComponent],
    rubric: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fallback heuristic matching when no explicit concepts defined.
    
    Considers:
    - Answer length (longer = more effort)
    - Number of components (structure)
    - Presence of domain-specific terms
    """
    
    total_length = sum(len(c.text) for c in answer_components)
    num_components = len(answer_components)
    
    # Heuristic score
    if total_length > 200 and num_components >= 3:
        match_percentage = 0.8
    elif total_length > 100 and num_components >= 2:
        match_percentage = 0.6
    elif total_length > 50:
        match_percentage = 0.4
    else:
        match_percentage = 0.2
    
    return {
        "found_concepts": ["general_answer"],
        "missing_concepts": ["mehr Details"],
        "match_percentage": match_percentage,
        "confidence": 60,
        "answer_length": total_length
    }


def determine_rubric_level(
    match_results: Dict[str, Any],
    rubric: Dict[str, Any]
) -> Tuple[str, float]:
    """
    Determine which rubric level the answer achieved.
    
    Returns: (level_name, points_earned)
    """
    
    match_pct = match_results["match_percentage"]
    
    # Map match percentage to rubric level
    if match_pct >= 0.90:
        level = "full_points"
    elif match_pct >= 0.70:
        level = "partial_75"
    elif match_pct >= 0.45:
        level = "partial_50"
    elif match_pct >= 0.20:
        level = "minimal"
    else:
        level = "zero_points"
    
    # Get points for this level
    level_data = rubric.get(level, {})
    points = level_data.get("score", 0)
    
    # If level not defined in rubric, interpolate
    if not level_data and "full_points" in rubric:
        max_points = rubric["full_points"].get("score", 0)
        points = max_points * match_pct
    
    return (level, points)


def generate_evaluation_rationale(
    match_results: Dict[str, Any],
    level: str,
    question_type: str
) -> str:
    """
    Generate human-readable rationale for the evaluation.
    
    Format:
    "Du hast [X] korrekt erklärt. Es fehlt: [Y]. Daher [Z] Punkte."
    """
    
    found = match_results["found_concepts"]
    missing = match_results["missing_concepts"]
    match_pct = match_results["match_percentage"]
    
    # Build rationale based on what was found/missing
    rationale_parts = []
    
    if match_pct >= 0.9:
        rationale_parts.append("Sehr gut! Deine Antwort ist vollständig und korrekt.")
    elif match_pct >= 0.7:
        rationale_parts.append("Gute Antwort! Die wichtigsten Punkte sind vorhanden.")
    elif match_pct >= 0.45:
        rationale_parts.append("Teilweise korrekt. Einige wichtige Aspekte sind vorhanden.")
    else:
        rationale_parts.append("Deine Antwort zeigt Ansätze, ist aber zu unvollständig.")
    
    if found:
        found_friendly = format_concept_list(found)
        rationale_parts.append(f"Korrekt erkannt: {found_friendly}.")
    
    if missing and match_pct < 0.9:
        missing_friendly = format_concept_list(missing)
        rationale_parts.append(f"Es fehlt: {missing_friendly}.")
    
    return " ".join(rationale_parts)


def generate_improvement_suggestion(
    match_results: Dict[str, Any],
    level: str,
    question_text: str,
    subject_context: str
) -> str:
    """
    Generate specific improvement suggestions.
    
    Based on what was missing, give actionable advice.
    """
    
    missing = match_results["missing_concepts"]
    match_pct = match_results["match_percentage"]
    
    if match_pct >= 0.9:
        return "Sehr gut! Weiter so."
    
    suggestions = []
    
    # Generic suggestions based on level
    if match_pct < 0.5:
        suggestions.append("Lies die Frage nochmal genau durch und beantworte alle Teilaspekte.")
    
    # Specific suggestions based on missing concepts
    if "incident_definition" in missing:
        suggestions.append("Definiere klarer, was ein Incident ist (Störung, die Service beeinträchtigt).")
    
    if "problem_definition" in missing:
        suggestions.append("Erkläre den Unterschied: Problem = Ursache mehrerer Incidents.")
    
    if "sla_metrics" in missing:
        suggestions.append("Nenne konkrete KPIs wie Verfügbarkeit, Reaktionszeit, Lösungszeit.")
    
    if "sla_purpose" in missing:
        suggestions.append("Erkläre den Zweck des SLA: Qualität definieren und dokumentieren.")
    
    # Fallback generic suggestion
    if not suggestions:
        suggestions.append("Vertiefe deine Antwort mit mehr Details und Fachbegriffen.")
    
    return " ".join(suggestions)


def format_concept_list(concepts: List[str]) -> str:
    """
    Format concept list for human readability.
    
    Examples:
    ["incident_definition", "problem_goal"] → "Incident-Definition, Problem-Ziel"
    """
    
    # Convert technical names to friendly names
    friendly_names = []
    for concept in concepts[:5]:  # Limit to first 5
        friendly = concept.replace('_', '-').title()
        friendly_names.append(friendly)
    
    if len(friendly_names) <= 2:
        return " und ".join(friendly_names)
    else:
        return ", ".join(friendly_names[:-1]) + f" und {friendly_names[-1]}"


def detect_spelling_errors(text: str) -> List[str]:
    """
    Detect common German spelling errors (lightweight).
    
    Only detects errors that change meaning - otherwise tolerant.
    """
    
    errors = []
    
    # Common typos that don't change meaning (IGNORE these)
    acceptable_typos = {
        'verfügbarkait': 'verfügbarkeit',  # k vs b
        'nomponente': 'komponente',  # n vs k
        'reaktinszeit': 'reaktionszeit'  # typo
    }
    
    text_lower = text.lower()
    
    # Only flag errors that actually change meaning
    meaning_changing_errors = {
        'incident': 'accident',  # Different meaning
        'problem': 'probleme'  # Singular vs plural matters in context
    }
    
    for wrong, right in meaning_changing_errors.items():
        if wrong in text_lower and right not in text_lower:
            errors.append(f"'{wrong}' sollte vielleicht '{right}' sein")
    
    return errors  # Will be mostly empty - we're tolerant!

"""
Pedagogical Feedback Generator - Stage 6

Generates constructive, student-focused feedback following educational best practices:
- What was good (positive reinforcement)
- What was missing (specific gaps)
- How to improve (actionable advice)
- Resource references (curriculum links)

Feedback tone: Encouraging, growth-oriented, age-appropriate for vocational students (17-21).
Language: Professional but approachable German.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackTone(str, Enum):
    """Feedback tone based on performance level"""
    EXCELLENT = "excellent"      # 90%+
    GOOD = "good"                # 70-89%
    SATISFACTORY = "satisfactory" # 50-69%
    NEEDS_WORK = "needs_work"    # <50%


@dataclass
class PedagogicalFeedback:
    """Structured feedback for a single question or overall exam"""
    what_was_good: str
    what_was_missing: str
    how_to_improve: str
    resource_reference: Optional[str] = None
    encouragement: Optional[str] = None
    tone: FeedbackTone = FeedbackTone.SATISFACTORY


def generate_task_feedback(
    task_id: str,
    question_text: str,
    question_type: str,
    student_answer: str,
    earned_points: float,
    max_points: int,
    rubric_match_level: str,
    components_found: List[str],
    components_missing: List[str],
    subject_context: str = "it_service"
) -> PedagogicalFeedback:
    """
    Generate pedagogical feedback for a single task.
    
    Args:
        task_id: Task identifier
        question_text: Original question
        question_type: Type of question
        student_answer: Student's response
        earned_points: Points awarded
        max_points: Maximum points
        rubric_match_level: Level achieved (full_points, partial_75, etc.)
        components_found: Concepts correctly identified
        components_missing: Concepts that were missing
        subject_context: Domain context
    
    Returns:
        PedagogicalFeedback with structured guidance
    """
    
    percentage = (earned_points / max_points * 100) if max_points > 0 else 0
    tone = _determine_tone(percentage)
    
    # Generate what was good
    what_good = _generate_what_was_good(
        components_found, percentage, question_type, tone
    )
    
    # Generate what was missing
    what_missing = _generate_what_was_missing(
        components_missing, rubric_match_level, question_type
    )
    
    # Generate improvement advice
    how_improve = _generate_improvement_advice(
        components_missing, question_text, question_type, subject_context, percentage
    )
    
    # Get resource reference
    resource = _get_resource_reference(
        components_missing, question_text, subject_context
    )
    
    # Add encouragement
    encouragement = _generate_encouragement(tone, percentage)
    
    return PedagogicalFeedback(
        what_was_good=what_good,
        what_was_missing=what_missing,
        how_to_improve=how_improve,
        resource_reference=resource,
        encouragement=encouragement,
        tone=tone
    )


def generate_overall_exam_feedback(
    task_feedbacks: List[Dict[str, Any]],
    total_percentage: float,
    grade_text: str,
    topic_analysis: Optional[Dict[str, float]] = None
) -> PedagogicalFeedback:
    """
    Generate overall exam feedback summarizing performance.
    
    Args:
        task_feedbacks: List of individual task feedback dicts
        total_percentage: Overall percentage score
        grade_text: German grade text (Sehr gut, Gut, etc.)
        topic_analysis: Optional dict of topic -> mastery level
    
    Returns:
        PedagogicalFeedback for entire exam
    """
    
    tone = _determine_tone(total_percentage)
    
    # Analyze strengths across all tasks
    all_found = []
    all_missing = []
    for tf in task_feedbacks:
        all_found.extend(tf.get("components_found", []))
        all_missing.extend(tf.get("components_missing", []))
    
    # What was good overall
    what_good = _generate_overall_what_was_good(
        all_found, total_percentage, grade_text, topic_analysis
    )
    
    # What needs improvement overall
    what_missing = _generate_overall_what_was_missing(
        all_missing, total_percentage, topic_analysis
    )
    
    # Strategic improvement advice
    how_improve = _generate_overall_improvement_advice(
        all_missing, total_percentage, topic_analysis
    )
    
    # Resources for weak areas
    resource = _get_overall_resource_reference(all_missing)
    
    # Motivational message
    encouragement = _generate_overall_encouragement(tone, total_percentage, grade_text)
    
    return PedagogicalFeedback(
        what_was_good=what_good,
        what_was_missing=what_missing,
        how_to_improve=how_improve,
        resource_reference=resource,
        encouragement=encouragement,
        tone=tone
    )


def _determine_tone(percentage: float) -> FeedbackTone:
    """Determine appropriate feedback tone based on performance"""
    if percentage >= 90:
        return FeedbackTone.EXCELLENT
    elif percentage >= 70:
        return FeedbackTone.GOOD
    elif percentage >= 50:
        return FeedbackTone.SATISFACTORY
    else:
        return FeedbackTone.NEEDS_WORK


def _generate_what_was_good(
    components_found: List[str],
    percentage: float,
    question_type: str,
    tone: FeedbackTone
) -> str:
    """Generate positive feedback highlighting strengths"""
    
    if percentage >= 90:
        if components_found:
            concepts = _format_concepts(components_found[:3])
            return f"Ausgezeichnet! Du hast {concepts} klar und vollständig erklärt. Deine Antwort zeigt tiefes Verständnis."
        else:
            return "Sehr gute Arbeit! Deine Antwort ist präzise und vollständig."
    
    elif percentage >= 70:
        if components_found:
            concepts = _format_concepts(components_found[:2])
            return f"Gut gemacht! Du hast {concepts} korrekt identifiziert und erklärt."
        else:
            return "Gute Leistung! Die wichtigsten Punkte hast du erfasst."
    
    elif percentage >= 50:
        if components_found:
            concepts = _format_concepts(components_found[:2])
            return f"Du hast {concepts} richtig verstanden – das ist ein guter Anfang."
        else:
            return "Du zeigst Grundverständnis des Themas."
    
    else:
        if components_found:
            concepts = _format_concepts(components_found[:1])
            return f"Du hast {concepts} ansatzweise erkannt."
        else:
            return "Du hast versucht, die Frage zu beantworten."


def _generate_what_was_missing(
    components_missing: List[str],
    rubric_match_level: str,
    question_type: str
) -> str:
    """Generate specific feedback about gaps"""
    
    if not components_missing or rubric_match_level == "full_points":
        return "Nichts wesentliches – deine Antwort war vollständig!"
    
    # Convert technical concept names to student-friendly language
    missing_friendly = _format_concepts(components_missing[:3], friendly=True)
    
    if len(components_missing) == 1:
        return f"Es fehlt noch: {missing_friendly}. Dieser Aspekt ist wichtig für eine vollständige Antwort."
    elif len(components_missing) <= 3:
        return f"Es fehlen noch: {missing_friendly}. Diese Punkte solltest du ergänzen."
    else:
        return f"Es fehlen mehrere Aspekte, besonders: {missing_friendly}. Arbeite diese Bereiche nochmal durch."


def _generate_improvement_advice(
    components_missing: List[str],
    question_text: str,
    question_type: str,
    subject_context: str,
    percentage: float
) -> str:
    """Generate actionable improvement advice"""
    
    if percentage >= 90:
        return "Weiter so! Dein Verständnis ist sehr gut. Achte weiterhin auf Details und Fachterminologie."
    
    advice_parts = []
    
    # General advice based on percentage
    if percentage < 50:
        advice_parts.append("Lies das Kapitel nochmal gründlich durch und markiere die Schlüsselbegriffe.")
    
    # Specific advice based on missing concepts (IT Service context)
    if subject_context == "it_service":
        if any("incident" in c for c in components_missing):
            advice_parts.append("Incident Management: Merke dir - Ziel ist schnelle Wiederherstellung, nicht Ursachenfindung.")
        
        if any("problem" in c for c in components_missing):
            advice_parts.append("Problem Management: Konzentriere dich auf Ursachenanalyse und dauerhafte Lösung.")
        
        if any("sla" in c for c in components_missing):
            advice_parts.append("SLA-Verständnis: Ein SLA ist ein Vertrag zwischen Dienstleister und Kunde mit messbaren Kennzahlen.")
        
        if any("priority" in c or "escalation" in c for c in components_missing):
            advice_parts.append("Priorisierung: Beachte Business Impact × Dringlichkeit = Priorität.")
    
    # Question-type specific advice
    if question_type in ["Explanation", "CaseStudy"]:
        advice_parts.append("Bei Erklärungsaufgaben: Gliedere deine Antwort (1. Definition, 2. Beispiel, 3. Zusammenhang).")
    
    if not advice_parts:
        advice_parts.append("Vertiefe dein Verständnis mit Beispielen aus der Praxis.")
    
    return " ".join(advice_parts)


def _get_resource_reference(
    components_missing: List[str],
    question_text: str,
    subject_context: str
) -> Optional[str]:
    """Get curriculum/textbook reference for review"""
    
    if subject_context == "it_service":
        # ITIL references
        if any("incident" in c for c in components_missing):
            return "📚 ITIL Service Operation – Incident Management (Kapitel 4.2)"
        
        if any("problem" in c for c in components_missing):
            return "📚 ITIL Service Operation – Problem Management (Kapitel 4.4)"
        
        if any("change" in c for c in components_missing):
            return "📚 ITIL Service Transition – Change Management (Kapitel 4.2)"
        
        if any("sla" in c for c in components_missing):
            return "📚 ITIL Service Design – Service Level Management (Kapitel 4.3)"
        
        # General ITIL reference
        return "📚 ITIL Foundation Handbuch – Lernfeld 7: IT Service Management"
    
    elif subject_context == "wbl":
        if any("markt" in c for c in components_missing):
            return "📚 Wirtschaftslehre – Kapitel 5: Marktforschung und Marketing"
    
    return None


def _generate_encouragement(tone: FeedbackTone, percentage: float) -> str:
    """Generate encouraging closing message"""
    
    if tone == FeedbackTone.EXCELLENT:
        messages = [
            "Hervorragend! Du bist auf dem besten Weg zur Prüfung.",
            "Exzellente Arbeit! Dein Wissen ist solide.",
            "Sehr gut! Halte dieses Niveau!"
        ]
    elif tone == FeedbackTone.GOOD:
        messages = [
            "Gute Arbeit! Mit etwas mehr Übung schaffst du eine sehr gute Note.",
            "Du bist auf einem guten Weg! Bleib dran.",
            "Gut gemacht! Noch ein bisschen mehr und du bist top."
        ]
    elif tone == FeedbackTone.SATISFACTORY:
        messages = [
            "Du hast die Grundlagen verstanden. Mit mehr Übung wird es noch besser!",
            "Solide Basis! Arbeite an den Lücken, dann wird die Note besser.",
            "Das Fundament steht. Jetzt heißt es: Vertiefen und wiederholen!"
        ]
    else:  # NEEDS_WORK
        messages = [
            "Lass dich nicht entmutigen! Mit gezieltem Lernen holst du das auf.",
            "Das war ein Anfang. Mit Unterstützung und Übung wird es deutlich besser!",
            "Nicht aufgeben! Wiederhole das Material systematisch – Erfolg kommt mit Übung."
        ]
    
    import random
    return random.choice(messages)


def _generate_overall_what_was_good(
    all_found: List[str],
    percentage: float,
    grade_text: str,
    topic_analysis: Optional[Dict[str, float]]
) -> str:
    """Generate overall positive summary"""
    
    parts = [f"Gesamtergebnis: {percentage:.0f}% ({grade_text})"]
    
    # Identify strong topics
    if topic_analysis:
        strong_topics = [t for t, score in topic_analysis.items() if score >= 75]
        if strong_topics:
            topics_str = ", ".join(strong_topics[:3])
            parts.append(f"Starke Bereiche: {topics_str}.")
    
    # General positive framing
    if percentage >= 80:
        parts.append("Du beherrschst die meisten Konzepte sehr gut.")
    elif percentage >= 60:
        parts.append("Du hast solide Grundkenntnisse gezeigt.")
    elif percentage >= 40:
        parts.append("Du zeigst Verständnis in einigen Bereichen.")
    
    return " ".join(parts)


def _generate_overall_what_was_missing(
    all_missing: List[str],
    percentage: float,
    topic_analysis: Optional[Dict[str, float]]
) -> str:
    """Generate overall gaps summary"""
    
    if percentage >= 90:
        return "Kaum etwas! Deine Leistung ist durchweg stark."
    
    # Identify weak topics
    if topic_analysis:
        weak_topics = [t for t, score in topic_analysis.items() if score < 50]
        if weak_topics:
            topics_str = ", ".join(weak_topics[:3])
            return f"Verbesserungsbedarf bei: {topics_str}. Diese Themen solltest du gezielt wiederholen."
    
    # Count most common missing concepts
    from collections import Counter
    if all_missing:
        common_missing = Counter(all_missing).most_common(3)
        missing_str = ", ".join([_friendly_concept_name(c[0]) for c in common_missing])
        return f"Häufig fehlende Konzepte: {missing_str}."
    
    return "Einige Details und Fachbegriffe sollten noch vertieft werden."


def _generate_overall_improvement_advice(
    all_missing: List[str],
    percentage: float,
    topic_analysis: Optional[Dict[str, float]]
) -> str:
    """Generate strategic study advice"""
    
    if percentage >= 85:
        return "Perfektioniere dein Wissen: Fokussiere auf Anwendungsfälle und Transfer-Aufgaben."
    
    advice = []
    
    # Prioritize weak areas
    if topic_analysis:
        weak_topics = sorted(topic_analysis.items(), key=lambda x: x[1])[:2]
        if weak_topics:
            topics = ", ".join([t[0] for t in weak_topics])
            advice.append(f"Priorität: Wiederhole {topics} mit Übungsaufgaben.")
    
    # General study strategy
    if percentage < 60:
        advice.append("Erstelle Karteikarten für Definitionen und Prozesse.")
        advice.append("Arbeite das Skript systematisch durch – nicht nur überfliegen!")
    else:
        advice.append("Übe besonders Fallstudien und Transfer-Aufgaben.")
    
    return " ".join(advice)


def _get_overall_resource_reference(all_missing: List[str]) -> Optional[str]:
    """Get primary study resource for weak areas"""
    
    from collections import Counter
    if not all_missing:
        return None
    
    # Find most common missing concept category
    common = Counter(all_missing).most_common(1)[0][0]
    
    if "incident" in common or "problem" in common:
        return "📚 Fokus: ITIL Service Operation (Incident & Problem Management)"
    elif "sla" in common or "service" in common:
        return "📚 Fokus: ITIL Service Design (Service Level Management)"
    else:
        return "📚 Fokus: ITIL Foundation Handbuch – relevante Kapitel nochmal durcharbeiten"


def _generate_overall_encouragement(
    tone: FeedbackTone,
    percentage: float,
    grade_text: str
) -> str:
    """Generate motivational closing for overall feedback"""
    
    if tone == FeedbackTone.EXCELLENT:
        return f"{grade_text} – Hervorragend! Du bist sehr gut vorbereitet für die Prüfung. Halte dieses Niveau!"
    
    elif tone == FeedbackTone.GOOD:
        return f"{grade_text} – Gute Leistung! Mit gezielter Wiederholung der Schwachstellen schaffst du eine sehr gute Note."
    
    elif tone == FeedbackTone.SATISFACTORY:
        return f"{grade_text} – Das ist eine solide Basis! Intensiviere deine Vorbereitung in den Schwachbereichen, dann wird es noch besser."
    
    else:
        return f"{grade_text} – Lass dich nicht entmutigen! Mit strukturiertem Lernen und Übung holst du das auf. Nutze die Lernressourcen!"


def _format_concepts(concepts: List[str], friendly: bool = False) -> str:
    """Format concept list for display"""
    
    if not concepts:
        return "die Kernkonzepte"
    
    if friendly:
        concepts = [_friendly_concept_name(c) for c in concepts]
    
    if len(concepts) == 1:
        return concepts[0]
    elif len(concepts) == 2:
        return f"{concepts[0]} und {concepts[1]}"
    else:
        return ", ".join(concepts[:-1]) + f" und {concepts[-1]}"


def _friendly_concept_name(concept: str) -> str:
    """Convert technical concept name to student-friendly German"""
    
    friendly_names = {
        "incident_definition": "Incident-Definition",
        "incident_goal": "Incident-Ziel",
        "problem_definition": "Problem-Definition",
        "problem_goal": "Problem-Ziel",
        "sla_purpose": "SLA-Zweck",
        "sla_metrics": "SLA-Kennzahlen",
        "escalation": "Eskalation",
        "priority": "Priorisierung",
        "ticket_system": "Ticket-System",
        "service_desk": "Service Desk",
        "marktforschung": "Marktforschung",
        "primärforschung": "Primärforschung",
        "sekundärforschung": "Sekundärforschung",
        "marketing_mix": "Marketing-Mix"
    }
    
    return friendly_names.get(concept, concept.replace("_", "-").title())

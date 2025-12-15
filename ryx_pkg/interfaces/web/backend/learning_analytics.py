"""
Learning Analytics Engine - Stage 7

Tracks student mastery across topics, generates personalized recommendations,
and provides insights into learning progress over time.

Features:
- Topic-level mastery tracking
- Concept retention analysis
- Personalized study recommendations
- Progress over time
- Strength/weakness identification
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class MasteryLevel(str, Enum):
    """Mastery levels for topics"""
    EXPERT = "expert"           # 90%+
    PROFICIENT = "proficient"   # 75-89%
    DEVELOPING = "developing"   # 50-74%
    EMERGING = "emerging"       # 25-49%
    NEEDS_FOCUS = "needs_focus" # <25%


@dataclass
class TopicMastery:
    """Mastery data for a single topic"""
    topic_name: str
    mastery_percentage: float  # 0-100
    mastery_level: MasteryLevel
    questions_answered: int
    questions_correct: int
    avg_confidence: float
    last_assessed: str  # ISO datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LearningRecommendation:
    """Personalized study recommendation"""
    priority: int  # 1 = highest priority
    topic: str
    reason: str
    action: str  # What student should do
    resource: Optional[str] = None
    estimated_time: Optional[str] = None  # "15 min", "1 hour"


@dataclass
class LearningAnalytics:
    """Complete learning analytics for a student"""
    student_id: Optional[str]
    exam_id: str
    overall_percentage: float
    grade: float
    grade_text: str
    
    # Topic-level analysis
    topic_masteries: List[TopicMastery]
    strengths: List[str]  # Topics with high mastery
    weaknesses: List[str]  # Topics needing improvement
    
    # Recommendations
    recommendations: List[LearningRecommendation]
    
    # Progress indicators
    improvement_potential: float  # How much can be improved (0-100)
    next_milestone: str  # "Reach 75% for 'Gut'"
    
    # Metadata
    generated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "exam_id": self.exam_id,
            "overall_percentage": self.overall_percentage,
            "grade": self.grade,
            "grade_text": self.grade_text,
            "topic_masteries": [tm.to_dict() for tm in self.topic_masteries],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": [asdict(r) for r in self.recommendations],
            "improvement_potential": self.improvement_potential,
            "next_milestone": self.next_milestone,
            "generated_at": self.generated_at
        }


def generate_learning_analytics(
    attempt_id: str,
    student_id: Optional[str],
    exam_id: str,
    task_grades: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    overall_percentage: float,
    grade: float,
    grade_text: str
) -> LearningAnalytics:
    """
    Generate comprehensive learning analytics from grading results.
    
    Args:
        attempt_id: Attempt identifier
        student_id: Student identifier (optional)
        exam_id: Exam identifier
        task_grades: List of TaskGrade dicts with rationale, confidence
        tasks: List of task dicts with question metadata
        overall_percentage: Overall score percentage
        grade: Numeric grade
        grade_text: German grade text
    
    Returns:
        LearningAnalytics with topic mastery, recommendations, etc.
    """
    
    # Extract topics from tasks
    topic_performance = _calculate_topic_performance(task_grades, tasks)
    
    # Generate topic masteries
    topic_masteries = _generate_topic_masteries(topic_performance)
    
    # Identify strengths and weaknesses
    strengths, weaknesses = _identify_strengths_weaknesses(topic_masteries)
    
    # Generate personalized recommendations
    recommendations = _generate_recommendations(
        topic_masteries, overall_percentage, grade_text
    )
    
    # Calculate improvement potential
    improvement_potential = _calculate_improvement_potential(overall_percentage)
    
    # Determine next milestone
    next_milestone = _determine_next_milestone(overall_percentage, grade)
    
    return LearningAnalytics(
        student_id=student_id,
        exam_id=exam_id,
        overall_percentage=overall_percentage,
        grade=grade,
        grade_text=grade_text,
        topic_masteries=topic_masteries,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        improvement_potential=improvement_potential,
        next_milestone=next_milestone,
        generated_at=datetime.utcnow().isoformat()
    )


def _calculate_topic_performance(
    task_grades: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate performance metrics per topic.
    
    Returns dict: {topic_name: {earned: X, max: Y, count: Z, confidences: [...]}}
    """
    
    topic_data = defaultdict(lambda: {
        "earned": 0.0,
        "max": 0,
        "count": 0,
        "confidences": []
    })
    
    # Map task_id to task for metadata lookup
    task_map = {t["id"]: t for t in tasks}
    
    for tg in task_grades:
        task_id = tg.get("task_id")
        task = task_map.get(task_id, {})
        
        # Extract topic from task metadata (or infer from question)
        topics = _extract_topics_from_task(task)
        
        earned = tg.get("earned_points", 0)
        max_points = tg.get("max_points", 0)
        confidence = tg.get("confidence", 0)
        
        for topic in topics:
            topic_data[topic]["earned"] += earned
            topic_data[topic]["max"] += max_points
            topic_data[topic]["count"] += 1
            topic_data[topic]["confidences"].append(confidence)
    
    return dict(topic_data)


def _extract_topics_from_task(task: Dict[str, Any]) -> List[str]:
    """
    Extract topics/concepts from a task.
    
    Looks in task metadata, question text for topic keywords.
    """
    
    topics = []
    
    # Check explicit tags
    if "topics" in task:
        topics.extend(task["topics"])
    
    if "thema" in task:
        topics.append(task["thema"])
    
    # Infer from question text
    question_text = task.get("question_text", "").lower()
    
    # ITIL/IT Service topics
    topic_keywords = {
        "Incident Management": ["incident", "störung", "ausfall", "ticket"],
        "Problem Management": ["problem", "ursache", "root cause", "dauerhaft"],
        "Change Management": ["change", "änderung", "änderungsmanagement"],
        "Service Level Management": ["sla", "service level", "kennzahl", "verfügbarkeit"],
        "ITIL Grundlagen": ["itil", "service", "prozess", "best practice"],
        "IT-Sicherheit": ["sicherheit", "security", "verschlüsselung", "firewall"],
        "Compliance": ["dsgvo", "iso", "compliance", "audit", "gesetz"]
    }
    
    for topic, keywords in topic_keywords.items():
        if any(kw in question_text for kw in keywords):
            topics.append(topic)
    
    # If no topics found, use generic
    if not topics:
        task_type = task.get("type", "General")
        topics.append(f"Allgemein ({task_type})")
    
    return list(set(topics))  # Deduplicate


def _generate_topic_masteries(
    topic_performance: Dict[str, Dict[str, Any]]
) -> List[TopicMastery]:
    """Generate TopicMastery objects from performance data"""
    
    masteries = []
    
    for topic, data in topic_performance.items():
        earned = data["earned"]
        max_points = data["max"]
        count = data["count"]
        confidences = data["confidences"]
        
        percentage = (earned / max_points * 100) if max_points > 0 else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        mastery_level = _determine_mastery_level(percentage)
        
        masteries.append(TopicMastery(
            topic_name=topic,
            mastery_percentage=round(percentage, 1),
            mastery_level=mastery_level,
            questions_answered=count,
            questions_correct=int(earned / (max_points / count)) if max_points > 0 else 0,
            avg_confidence=round(avg_confidence, 1),
            last_assessed=datetime.utcnow().isoformat()
        ))
    
    # Sort by percentage (worst first for priority)
    masteries.sort(key=lambda m: m.mastery_percentage)
    
    return masteries


def _determine_mastery_level(percentage: float) -> MasteryLevel:
    """Map percentage to mastery level"""
    if percentage >= 90:
        return MasteryLevel.EXPERT
    elif percentage >= 75:
        return MasteryLevel.PROFICIENT
    elif percentage >= 50:
        return MasteryLevel.DEVELOPING
    elif percentage >= 25:
        return MasteryLevel.EMERGING
    else:
        return MasteryLevel.NEEDS_FOCUS


def _identify_strengths_weaknesses(
    topic_masteries: List[TopicMastery]
) -> Tuple[List[str], List[str]]:
    """Identify strong and weak topics"""
    
    strengths = []
    weaknesses = []
    
    for tm in topic_masteries:
        if tm.mastery_level in [MasteryLevel.EXPERT, MasteryLevel.PROFICIENT]:
            strengths.append(tm.topic_name)
        elif tm.mastery_level in [MasteryLevel.NEEDS_FOCUS, MasteryLevel.EMERGING]:
            weaknesses.append(tm.topic_name)
    
    return strengths, weaknesses


def _generate_recommendations(
    topic_masteries: List[TopicMastery],
    overall_percentage: float,
    grade_text: str
) -> List[LearningRecommendation]:
    """Generate prioritized learning recommendations"""
    
    recommendations = []
    priority = 1
    
    # Focus on weakest topics first
    weak_topics = [tm for tm in topic_masteries if tm.mastery_percentage < 60]
    
    for tm in weak_topics[:3]:  # Top 3 priorities
        action = _generate_topic_specific_action(tm.topic_name, tm.mastery_level)
        resource = _get_topic_resource(tm.topic_name)
        
        recommendations.append(LearningRecommendation(
            priority=priority,
            topic=tm.topic_name,
            reason=f"Nur {tm.mastery_percentage:.0f}% Beherrschung – kritischer Bereich",
            action=action,
            resource=resource,
            estimated_time="30-45 min"
        ))
        priority += 1
    
    # Add strategic recommendations
    if overall_percentage < 50:
        recommendations.append(LearningRecommendation(
            priority=priority,
            topic="Lernstrategie",
            reason="Gesamtleistung unter 50% – grundlegende Wiederholung nötig",
            action="Erstelle eine Zusammenfassung aller Kernkonzepte mit eigenen Worten. Nutze Karteikarten für Definitionen.",
            resource="📚 Komplettes Skript durcharbeiten",
            estimated_time="2-3 Stunden"
        ))
        priority += 1
    
    # Intermediate performance
    elif overall_percentage < 75:
        recommendations.append(LearningRecommendation(
            priority=priority,
            topic="Transfer-Fähigkeiten",
            reason="Grundlagen vorhanden, aber Anwendung üben",
            action="Bearbeite 5-10 Fallstudien und erkläre deine Lösungswege.",
            resource="📝 Übungsaufgaben aus dem Lehrbuch",
            estimated_time="1-2 Stunden"
        ))
    
    # High performance
    else:
        recommendations.append(LearningRecommendation(
            priority=priority,
            topic="Perfektionierung",
            reason="Sehr gute Basis – Details optimieren",
            action="Fokussiere auf komplexe Szenarien und Randfälle. Wiederhole Schwachstellen.",
            estimated_time="30 min"
        ))
    
    return recommendations


def _generate_topic_specific_action(topic: str, mastery_level: MasteryLevel) -> str:
    """Generate specific action for a topic"""
    
    # Topic-specific study actions
    topic_actions = {
        "Incident Management": "Lerne den 8-Stufen-Prozess auswendig: Detect→Log→Categorize→Prioritize→Diagnose→Resolve→Close→Review",
        "Problem Management": "Verstehe den Unterschied zu Incident: Problem = Ursache mehrerer Incidents. Fokus auf Root Cause Analysis.",
        "Service Level Management": "Merke dir: SLA = Vertrag zwischen Provider und Kunde. Enthält KPIs wie Verfügbarkeit, Reaktionszeit, Lösungszeit.",
        "Change Management": "RFC-Prozess verstehen: Request→Assess→Approve→Implement→Review",
        "ITIL Grundlagen": "Wiederhole die 5 Service Lifecycle-Phasen: Strategy→Design→Transition→Operation→Improvement"
    }
    
    specific_action = topic_actions.get(topic)
    if specific_action:
        return specific_action
    
    # Generic action based on mastery level
    if mastery_level == MasteryLevel.NEEDS_FOCUS:
        return f"Beginne mit Grundlagen: Lies das Kapitel zu {topic} komplett durch und markiere Schlüsselbegriffe."
    elif mastery_level == MasteryLevel.EMERGING:
        return f"Vertiefe dein Wissen: Erstelle eine Mindmap zu {topic} mit allen wichtigen Konzepten."
    else:
        return f"Übe Anwendung: Bearbeite 3-5 Fallstudien zu {topic}."


def _get_topic_resource(topic: str) -> Optional[str]:
    """Get learning resource for topic"""
    
    resources = {
        "Incident Management": "📚 ITIL Service Operation, Kapitel 4.2",
        "Problem Management": "📚 ITIL Service Operation, Kapitel 4.4",
        "Change Management": "📚 ITIL Service Transition, Kapitel 4.2",
        "Service Level Management": "📚 ITIL Service Design, Kapitel 4.3",
        "ITIL Grundlagen": "📚 ITIL Foundation Handbuch",
        "IT-Sicherheit": "📚 IT-Sicherheit Skript, Kapitel 3",
        "Compliance": "📚 Compliance & Datenschutz, Kapitel 5"
    }
    
    return resources.get(topic, f"📚 Lehrbuch: {topic}")


def _calculate_improvement_potential(overall_percentage: float) -> float:
    """Calculate how much student can realistically improve"""
    
    # If already at 90%+, potential is limited
    if overall_percentage >= 90:
        return round(100 - overall_percentage, 1)
    
    # Realistic improvement potential (not always to 100%)
    if overall_percentage >= 75:
        return round((90 - overall_percentage), 1)
    elif overall_percentage >= 60:
        return round((80 - overall_percentage), 1)
    else:
        # Lower scores have higher potential but need more work
        return round(min(30, 75 - overall_percentage), 1)


def _determine_next_milestone(overall_percentage: float, grade: float) -> str:
    """Determine next achievable milestone"""
    
    # German grading scale milestones
    if overall_percentage >= 92:
        return "Du hast bereits 1.0 (Sehr gut) erreicht! Halte dieses Niveau."
    elif overall_percentage >= 81:
        return "Ziel: 92% für Note 1.0 (Sehr gut) – nur noch wenige Punkte!"
    elif overall_percentage >= 70:
        return "Ziel: 81% für Note 2.0 (Gut) erreichen"
    elif overall_percentage >= 59:
        return "Ziel: 70% für Note 3.0 (Befriedigend) erreichen"
    elif overall_percentage >= 50:
        return "Ziel: 59% für Note 4.0 (Ausreichend) sichern"
    else:
        return "Ziel: Mindestens 50% für Note 4.5 (Ausreichend) erreichen – intensive Vorbereitung nötig!"


def calculate_class_analytics(
    all_attempts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate class-level analytics (teacher view).
    
    Args:
        all_attempts: List of all grading attempts
    
    Returns:
        Dict with class-wide statistics
    """
    
    if not all_attempts:
        return {"error": "No attempts to analyze"}
    
    # Extract scores
    scores = [a.get("percentage", 0) for a in all_attempts]
    grades = [a.get("grade", 0) for a in all_attempts]
    
    # Calculate statistics
    avg_score = sum(scores) / len(scores) if scores else 0
    median_score = sorted(scores)[len(scores) // 2] if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0
    
    # Grade distribution
    grade_distribution = _calculate_grade_distribution(grades)
    
    # Common weak topics
    all_topic_data = []
    for attempt in all_attempts:
        analytics = attempt.get("learning_analytics", {})
        weaknesses = analytics.get("weaknesses", [])
        all_topic_data.extend(weaknesses)
    
    from collections import Counter
    common_weaknesses = Counter(all_topic_data).most_common(5)
    
    return {
        "total_students": len(all_attempts),
        "average_score": round(avg_score, 1),
        "median_score": round(median_score, 1),
        "min_score": round(min_score, 1),
        "max_score": round(max_score, 1),
        "grade_distribution": grade_distribution,
        "common_weaknesses": [{"topic": t, "count": c} for t, c in common_weaknesses],
        "pass_rate": round(len([s for s in scores if s >= 50]) / len(scores) * 100, 1) if scores else 0
    }


def _calculate_grade_distribution(grades: List[float]) -> Dict[str, int]:
    """Calculate how many students got each grade"""
    
    distribution = {
        "1.0-1.5": 0,  # Sehr gut
        "2.0-2.5": 0,  # Gut
        "3.0-3.5": 0,  # Befriedigend
        "4.0-4.5": 0,  # Ausreichend
        "5.0-5.5": 0,  # Mangelhaft
        "6.0": 0       # Ungenügend
    }
    
    for grade in grades:
        if grade <= 1.5:
            distribution["1.0-1.5"] += 1
        elif grade <= 2.5:
            distribution["2.0-2.5"] += 1
        elif grade <= 3.5:
            distribution["3.0-3.5"] += 1
        elif grade <= 4.5:
            distribution["4.0-4.5"] += 1
        elif grade <= 5.5:
            distribution["5.0-5.5"] += 1
        else:
            distribution["6.0"] += 1
    
    return distribution

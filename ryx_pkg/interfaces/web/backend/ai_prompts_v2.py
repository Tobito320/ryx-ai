"""
AI Prompts for RyxHub Exam System V2

Contains structured prompts for:
- OCR Post-Processing
- Classification (Subject/Thema/Teacher)
- Exam Generation
- Answer Grading

All prompts follow a consistent structure:
- System context (German Berufsschule)
- JSON output schema
- Examples where helpful
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json

# ============================================================================
# OCR Post-Processing Prompt
# ============================================================================

OCR_POST_PROCESS_SYSTEM = """Du bist ein Experte für die Analyse von deutschen Berufsschul-Klassenarbeiten.
Deine Aufgabe ist es, rohen OCR-Text zu strukturieren und wichtige Informationen zu extrahieren.

KONTEXT:
- Deutsche Berufsschule (Cuno Berufskolleg Hagen, SIHK-Region)
- Ausbildungsberufe: Einzelhandel, Bürokaufleute, IT-Kaufleute, etc.
- Typische Fächer: WBL, BWL, Deutsch, Mathe, IT-Systeme, Englisch

AUFGABE:
Analysiere den OCR-Text und extrahiere strukturierte Informationen.
Gib NUR valides JSON zurück, keine Erklärungen.
"""

OCR_POST_PROCESS_USER_TEMPLATE = """Analysiere folgenden OCR-Text einer Klassenarbeit:

---OCR TEXT START---
{ocr_text}
---OCR TEXT END---

Extrahiere folgende Informationen als JSON:
{{
  "header_info": {{
    "detected_teacher": "Name oder null",
    "detected_subject": "Fachkürzel oder null (z.B. WBL, BWL, IT)",
    "detected_date": "YYYY-MM-DD oder null",
    "detected_class": "z.B. EH23a oder null",
    "detected_title": "Titel der Arbeit oder null",
    "exam_type": "Klassenarbeit|Test|Übung|Probe|unknown",
    "total_points": Zahl oder null,
    "duration_minutes": Zahl oder null
  }},
  "detected_topics": [
    {{"name": "Themenname", "confidence": 0-100}}
  ],
  "tasks": [
    {{
      "task_number": 1,
      "raw_text": "Originaltext der Aufgabe",
      "points": Zahl oder null,
      "suggested_type": "MC_SingleChoice|ShortAnswer|CaseStudy|Calculation|DiagramAnalysis|FillInBlank|Matching|Explanation",
      "has_sub_tasks": true/false,
      "sub_task_count": Zahl
    }}
  ],
  "overall_confidence": 0-100,
  "warnings": ["Liste von Problemen beim Parsen"]
}}
"""

# ============================================================================
# Classification Prompt
# ============================================================================

CLASSIFICATION_SYSTEM = """Du bist ein KI-System zur Klassifikation von Berufsschul-Prüfungen.
Du erhältst strukturierte Informationen aus einer OCR-Analyse und musst:
1. Das Fach bestimmen
2. Die Hauptthemen identifizieren
3. Den Lehrer-Stil analysieren (falls erkennbar)

WICHTIGE REGELN:
- "IT Service", "IT-Systeme", "EDV" → Fach: "it" (NICHT WBL!)
- "Marktforschung", "Marketing", "Preisbildung" → Fach: "wbl" 
- "Buchführung", "Bilanz", "GuV" → Fach: "bwl"
- "Rechtschreibung", "Grammatik", "Aufsatz" → Fach: "deutsch"

BEKANNTE LEHRER (Cuno Berufskolleg):
- Herr Hakim: IT, WBL
- Frau Müller: Deutsch
- Herr Schmidt: BWL
"""

CLASSIFICATION_USER_TEMPLATE = """Klassifiziere diese Klassenarbeit:

HEADER-INFO:
{header_info}

ERKANNTE THEMEN:
{detected_topics}

AUFGABEN-ÜBERSICHT:
{task_overview}

---

Gib folgendes JSON zurück:
{{
  "subject": {{
    "id": "wbl|bwl|it|deutsch|mathe|englisch",
    "name": "Vollständiger Name",
    "confidence": 0-100,
    "reasoning": "Warum dieses Fach?"
  }},
  "main_thema": {{
    "id": "thema-slug",
    "name": "Themenname",
    "confidence": 0-100
  }},
  "additional_themas": [
    {{"id": "slug", "name": "Name", "confidence": 0-100}}
  ],
  "teacher": {{
    "id": "teacher-id oder null",
    "name": "Name oder null",
    "is_new": true/false,
    "confidence": 0-100
  }},
  "exam_characteristics": {{
    "difficulty_estimate": 1-5,
    "task_type_distribution": {{
      "MC_SingleChoice": Prozent,
      "ShortAnswer": Prozent,
      "CaseStudy": Prozent,
      ...
    }},
    "focus_areas": ["Liste der Schwerpunkte"]
  }},
  "requires_review": true/false,
  "review_reasons": ["Gründe falls unsicher"]
}}
"""

# ============================================================================
# Exam Generation Prompt
# ============================================================================

EXAM_GENERATION_SYSTEM = """Du bist ein Experte für die Erstellung von IHK-konformen Prüfungsaufgaben für deutsche Berufsschulen.

DEINE AUFGABE:
Erstelle realistische Übungsklausuren basierend auf:
- Gewählten Themen
- Freitext-Beschreibung des Nutzers
- Optional: Stil eines bestimmten Lehrers
- Optional: Kontext aus hochgeladenen Klassenarbeiten

AUFGABENTYPEN die du verwenden MUSST (Mix je nach Anforderung):
1. MC_SingleChoice - Multiple Choice mit einer richtigen Antwort
2. MC_MultipleChoice - Multiple Choice mit mehreren richtigen Antworten
3. ShortAnswer - Kurze Textantwort (1-3 Sätze)
4. Explanation - Ausführliche Erklärung (5+ Sätze)
5. CaseStudy - Fallstudie mit Situation und Aufgaben
6. Calculation - Berechnung mit Formel und Zahlen
7. DiagramAnalysis - Diagramm interpretieren (Bar, Pie, Line)
8. FillInBlank - Lückentext
9. Matching - Zuordnungsaufgabe
10. Justification - Begründungsaufgabe

QUALITÄTSKRITERIEN:
- Realistisch für Berufsschulniveau
- Klare, eindeutige Fragestellung
- Faire Punkteverteilung
- Sinnvolle Schwierigkeitsprogression
- Rubrik für objektive Bewertung

OUTPUT FORMAT:
Gib NUR valides JSON zurück, keine Kommentare oder Erklärungen.
"""

EXAM_GENERATION_USER_TEMPLATE = """Erstelle eine Übungsklausur mit folgenden Parametern:

FACH: {subject_name}
THEMEN: {thema_names}
SCHWIERIGKEIT: {difficulty}/5
ANZAHL AUFGABEN: {task_count}
BEARBEITUNGSZEIT: {duration_minutes} Minuten

{teacher_pattern_section}

{free_prompt_section}

{context_section}

---

Generiere eine Klausur als JSON:
{{
  "title": "Titel der Klausur",
  "description": "Kurze Beschreibung",
  "tasks": [
    {{
      "id": "task-1",
      "type": "MC_SingleChoice|MC_MultipleChoice|ShortAnswer|Explanation|CaseStudy|Calculation|DiagramAnalysis|FillInBlank|Matching|Justification",
      "task_number": 1,
      "question_text": "Vollständige Fragestellung",
      "points": Punkte (1-15),
      "difficulty": 1-5,
      "time_estimate_minutes": Geschätzte Zeit,
      
      // Für MC-Aufgaben:
      "options": [
        {{"id": "A", "text": "Option A", "is_correct": false}},
        {{"id": "B", "text": "Option B", "is_correct": true}},
        ...
      ],
      
      // Für Calculation:
      "calculation_data": {{
        "formula": "Formel",
        "given_values": [{{"name": "Variable", "value": 100, "unit": "€"}}],
        "expected_answer": 150,
        "expected_unit": "€",
        "tolerance_percent": 5,
        "steps": [
          {{"description": "Schritt 1", "formula": "x = ...", "result": 50}}
        ]
      }},
      
      // Für DiagramAnalysis:
      "diagram_data": {{
        "type": "bar|pie|line",
        "title": "Diagrammtitel",
        "data_points": [
          {{"label": "Q1", "value": 25, "color": "#3b82f6"}}
        ],
        "x_label": "X-Achse",
        "y_label": "Y-Achse",
        "expected_analysis": "Was soll erkannt werden"
      }},
      
      // Für Matching:
      "matching_pairs": [
        {{"id": "1", "left": "Begriff", "right": "Definition"}}
      ],
      
      // Für FillInBlank:
      "fill_in_blanks": [
        {{"id": "1", "position": 15, "correct_answers": ["Antwort1", "Antwort2"]}}
      ],
      "question_text_with_blanks": "Der ___ ist wichtig für ___.",
      
      // Bewertung:
      "correct_answer": "Für MC: A oder [A, C]",
      "model_answer": "Für offene Fragen: Musterlösung",
      "grading_rubric": {{
        "max_points": Punkte,
        "auto_gradable": true/false,
        "partial_credit_allowed": true/false,
        "criteria": [
          {{
            "name": "Kriterium",
            "description": "Was wird bewertet",
            "max_points": Punkte,
            "keywords": ["Schlüsselwörter für Auto-Grading"]
          }}
        ]
      }},
      
      "hints": ["Optional: Hinweise"],
      "related_themas": ["thema-id"]
    }}
  ],
  "total_points": Summe aller Punkte,
  "section_breakdown": {{
    "knowledge": {{
      "points": Wissensfragen-Punkte,
      "task_ids": ["task-1", "task-2"]
    }},
    "application": {{
      "points": Anwendungsfragen-Punkte,
      "task_ids": ["task-3", "task-4"]
    }}
  }}
}}
"""

# Helper sections for exam generation
def get_teacher_pattern_section(teacher_pattern: Optional[Dict]) -> str:
    if not teacher_pattern:
        return "LEHRER-STIL: Standard IHK-Format"
    
    return f"""LEHRER-STIL von {teacher_pattern.get('teacher_name', 'Unbekannt')}:
- Aufgabentyp-Verteilung: {json.dumps(teacher_pattern.get('question_type_distribution', {}), ensure_ascii=False)}
- Durchschnittliche Schwierigkeit: {teacher_pattern.get('avg_difficulty', 3)}/5
- Bewertungsstil: {teacher_pattern.get('grading_style', 'Standard')}
"""

def get_free_prompt_section(free_prompt: Optional[str]) -> str:
    if not free_prompt:
        return ""
    return f"""NUTZER-ANFORDERUNGEN:
{free_prompt}
"""

def get_context_section(context_texts: List[str]) -> str:
    if not context_texts:
        return ""
    
    combined = "\n---\n".join(context_texts[:3])  # Max 3 context docs
    return f"""KONTEXT-MATERIAL (verwende diese Informationen):
{combined}
"""

# ============================================================================
# Grading Prompt
# ============================================================================

GRADING_SYSTEM = """Du bist ein erfahrener Prüfer für deutsche Berufsschul-Prüfungen.
Deine Aufgabe ist die faire, objektive Bewertung von Schülerantworten.

BEWERTUNGSPRINZIPIEN:
1. Objektiv und nachvollziehbar
2. Teilpunkte wenn angemessen
3. Konstruktives Feedback
4. Konfidenz-Angabe bei Unsicherheit

KONFIDENZ-BEWERTUNG:
- 90-100%: Klare Richtig/Falsch-Entscheidung
- 70-89%: Wahrscheinlich korrekt bewertet
- 50-69%: Unsicher, manuelle Prüfung empfohlen
- <50%: Manuelle Prüfung erforderlich

Bei Multiple-Choice: Immer 100% Konfidenz (objektiv prüfbar)
Bei offenen Fragen: Konfidenz basierend auf Eindeutigkeit der Antwort
"""

GRADING_USER_TEMPLATE = """Bewerte folgende Antwort:

AUFGABE:
Typ: {task_type}
Frage: {question_text}
Punkte: {max_points}
Musterlösung: {model_answer}

BEWERTUNGSRUBRIK:
{rubric_json}

SCHÜLERANTWORT:
{user_answer}

---

Gib folgendes JSON zurück:
{{
  "earned_points": Punkte (0 bis {max_points}),
  "max_points": {max_points},
  "is_correct": true/false,
  "is_partially_correct": true/false,
  "confidence": 0-100,
  
  "feedback": "Konstruktives Feedback auf Deutsch",
  "feedback_type": "correct|partial|incorrect|needs_review",
  
  "criteria_scores": [
    {{
      "criterion_name": "Name aus Rubrik",
      "earned_points": Punkte,
      "max_points": Max aus Rubrik,
      "comment": "Begründung"
    }}
  ],
  
  "detailed_feedback": {{
    "strengths": ["Was gut war"],
    "weaknesses": ["Was fehlte"],
    "suggestions": ["Verbesserungsvorschläge"]
  }},
  
  "needs_manual_review": true/false,
  "review_reason": "Grund falls unsicher"
}}
"""

# ============================================================================
# Batch Grading for Efficiency
# ============================================================================

BATCH_GRADING_SYSTEM = GRADING_SYSTEM

BATCH_GRADING_USER_TEMPLATE = """Bewerte alle folgenden Aufgaben einer Klausur:

KLAUSUR: {exam_title}
GESAMTPUNKTE: {total_points}

AUFGABEN UND ANTWORTEN:
{tasks_and_answers_json}

---

Gib ein JSON-Array mit Bewertungen für JEDE Aufgabe zurück:
{{
  "task_results": [
    {{
      "task_id": "task-id",
      "earned_points": Punkte,
      "max_points": Max,
      "is_correct": true/false,
      "confidence": 0-100,
      "feedback": "Kurzes Feedback",
      "feedback_type": "correct|partial|incorrect|needs_review",
      "needs_manual_review": true/false
    }}
  ],
  "overall": {{
    "total_earned": Gesamtpunkte,
    "total_max": {total_points},
    "percentage": Prozent,
    "grade": "1.0 bis 6.0",
    "grade_text": "Sehr gut|Gut|Befriedigend|Ausreichend|Mangelhaft|Ungenügend",
    "overall_feedback": "Gesamtfeedback",
    "strengths": ["Stärken"],
    "areas_for_improvement": ["Verbesserungspotential"]
  }}
}}
"""

# ============================================================================
# Prompt Builder Functions
# ============================================================================

def build_ocr_prompt(ocr_text: str) -> tuple[str, str]:
    """Build OCR post-processing prompt."""
    return OCR_POST_PROCESS_SYSTEM, OCR_POST_PROCESS_USER_TEMPLATE.format(
        ocr_text=ocr_text
    )

def build_classification_prompt(
    header_info: Dict,
    detected_topics: List[Dict],
    task_overview: str
) -> tuple[str, str]:
    """Build classification prompt."""
    return CLASSIFICATION_SYSTEM, CLASSIFICATION_USER_TEMPLATE.format(
        header_info=json.dumps(header_info, ensure_ascii=False, indent=2),
        detected_topics=json.dumps(detected_topics, ensure_ascii=False, indent=2),
        task_overview=task_overview
    )

def build_exam_generation_prompt(
    subject_name: str,
    thema_names: List[str],
    difficulty: int,
    task_count: int,
    duration_minutes: int,
    teacher_pattern: Optional[Dict] = None,
    free_prompt: Optional[str] = None,
    context_texts: Optional[List[str]] = None
) -> tuple[str, str]:
    """Build exam generation prompt."""
    return EXAM_GENERATION_SYSTEM, EXAM_GENERATION_USER_TEMPLATE.format(
        subject_name=subject_name,
        thema_names=", ".join(thema_names),
        difficulty=difficulty,
        task_count=task_count,
        duration_minutes=duration_minutes,
        teacher_pattern_section=get_teacher_pattern_section(teacher_pattern),
        free_prompt_section=get_free_prompt_section(free_prompt),
        context_section=get_context_section(context_texts or [])
    )

def build_grading_prompt(
    task_type: str,
    question_text: str,
    max_points: int,
    model_answer: str,
    rubric: Dict,
    user_answer: str
) -> tuple[str, str]:
    """Build single task grading prompt."""
    return GRADING_SYSTEM, GRADING_USER_TEMPLATE.format(
        task_type=task_type,
        question_text=question_text,
        max_points=max_points,
        model_answer=model_answer,
        rubric_json=json.dumps(rubric, ensure_ascii=False, indent=2),
        user_answer=user_answer
    )

def build_batch_grading_prompt(
    exam_title: str,
    total_points: int,
    tasks_and_answers: List[Dict]
) -> tuple[str, str]:
    """Build batch grading prompt for entire exam."""
    return BATCH_GRADING_SYSTEM, BATCH_GRADING_USER_TEMPLATE.format(
        exam_title=exam_title,
        total_points=total_points,
        tasks_and_answers_json=json.dumps(tasks_and_answers, ensure_ascii=False, indent=2)
    )

# ============================================================================
# JSON Schema Definitions for Validation
# ============================================================================

class OCRPostProcessResult(BaseModel):
    """Schema for OCR post-processing result."""
    
    class HeaderInfo(BaseModel):
        detected_teacher: Optional[str] = None
        detected_subject: Optional[str] = None
        detected_date: Optional[str] = None
        detected_class: Optional[str] = None
        detected_title: Optional[str] = None
        exam_type: str = "unknown"
        total_points: Optional[int] = None
        duration_minutes: Optional[int] = None
    
    class DetectedTopic(BaseModel):
        name: str
        confidence: int = Field(ge=0, le=100)
    
    class ExtractedTask(BaseModel):
        task_number: int
        raw_text: str
        points: Optional[int] = None
        suggested_type: str = "ShortAnswer"
        has_sub_tasks: bool = False
        sub_task_count: int = 0
    
    header_info: HeaderInfo
    detected_topics: List[DetectedTopic] = []
    tasks: List[ExtractedTask] = []
    overall_confidence: int = Field(ge=0, le=100)
    warnings: List[str] = []

class ClassificationResult(BaseModel):
    """Schema for classification result."""
    
    class SubjectInfo(BaseModel):
        id: str
        name: str
        confidence: int = Field(ge=0, le=100)
        reasoning: str = ""
    
    class ThemaInfo(BaseModel):
        id: str
        name: str
        confidence: int = Field(ge=0, le=100)
    
    class TeacherInfo(BaseModel):
        id: Optional[str] = None
        name: Optional[str] = None
        is_new: bool = True
        confidence: int = Field(ge=0, le=100, default=0)
    
    class ExamCharacteristics(BaseModel):
        difficulty_estimate: int = Field(ge=1, le=5, default=3)
        task_type_distribution: Dict[str, int] = {}
        focus_areas: List[str] = []
    
    subject: SubjectInfo
    main_thema: ThemaInfo
    additional_themas: List[ThemaInfo] = []
    teacher: TeacherInfo = TeacherInfo()
    exam_characteristics: ExamCharacteristics = ExamCharacteristics()
    requires_review: bool = False
    review_reasons: List[str] = []

class GradingResultSchema(BaseModel):
    """Schema for grading result."""
    
    class CriteriaScore(BaseModel):
        criterion_name: str
        earned_points: float
        max_points: float
        comment: str = ""
    
    class DetailedFeedback(BaseModel):
        strengths: List[str] = []
        weaknesses: List[str] = []
        suggestions: List[str] = []
    
    earned_points: float = Field(ge=0)
    max_points: float = Field(ge=0)
    is_correct: bool = False
    is_partially_correct: bool = False
    confidence: int = Field(ge=0, le=100)
    feedback: str = ""
    feedback_type: str = "needs_review"
    criteria_scores: List[CriteriaScore] = []
    detailed_feedback: DetailedFeedback = DetailedFeedback()
    needs_manual_review: bool = False
    review_reason: Optional[str] = None

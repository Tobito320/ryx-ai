"""
AI Prompts Module for RyxHub Exam System

Contains structured prompts and JSON schemas for:
- Upload Pipeline (OCR + Classification)
- Exam Generation Pipeline
- Grading Pipeline

All prompts are designed for Claude Opus 4.5 / Sonnet but can be adapted for other models.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

# ============================================================================
# Upload Pipeline Prompts
# ============================================================================

UPLOAD_CLASSIFICATION_SYSTEM_PROMPT = """Du bist ein Experte für deutsche Berufsschul-Prüfungen (IHK/SIHK Hagen, Cuno Berufskolleg).
Deine Aufgabe ist es, aus OCR-Text einer hochgeladenen Klassenarbeit folgende Informationen zu extrahieren:

1. **Fach** (subject): Bestimme das Hauptfach basierend auf Inhalt UND Kontext
   - WBL = Wirtschaft und Betriebslehre (Marketing, Marktforschung, Kundenakquisition, etc.)
   - BWL = Betriebswirtschaftslehre (Buchhaltung, Bilanz, Kostenrechnung, etc.)
   - IT = Informatik/IT-Systeme (Netzwerke, Hardware, Software, IT-Service, etc.)
   - Deutsch = Deutsch/Kommunikation (Textanalyse, Briefe, Erörterung, etc.)
   - Mathe = Mathematik (Berechnungen, Prozent, Zins, etc.)
   - Englisch = Wirtschaftsenglisch

2. **Hauptthema** (mainThema): Das zentrale Thema der Klassenarbeit
   - Achte auf Überschriften, wiederkehrende Begriffe, Aufgabenkontext

3. **Lehrer** (teacher): Name des Lehrers falls erkennbar
   - Oft in "Herr/Frau [Name]" oder "Klassenarbeit [Name]" Format

4. **Datum**: Datum der Klassenarbeit falls erkennbar

5. **Aufgaben**: Extrahiere alle erkennbaren Aufgaben mit:
   - Aufgabennummer
   - Fragetext
   - Punktzahl (falls angegeben)
   - Vorgeschlagener Aufgabentyp

WICHTIG:
- "IT Service" oder "IT-Service" gehört zum Fach IT, NICHT zu WBL/Marktforschung
- "Kundenakquisition" und "Marketing" gehören zu WBL
- Sei dir bei der Fachzuordnung sicher basierend auf dem GESAMTEN Inhalt
- Gib Konfidenzwerte (0-100) für jede Extraktion an
- Wenn Konfidenz < 85%, setze requiresReview: true

Antworte NUR mit validem JSON im folgenden Format:"""

UPLOAD_CLASSIFICATION_JSON_SCHEMA = {
    "type": "object",
    "required": ["subject", "mainThema", "teacher", "examDate", "examType", "totalPoints", "extractedTasks", "overallConfidence", "requiresReview", "reviewReasons"],
    "properties": {
        "subject": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "enum": ["wbl", "bwl", "it", "deutsch", "mathe", "englisch"]},
                "name": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 100}
            },
            "required": ["id", "name", "confidence"]
        },
        "mainThema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 100}
            },
            "required": ["id", "name", "confidence"]
        },
        "additionalThemas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        },
        "teacher": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "isNew": {"type": "boolean"},
                "confidence": {"type": "number"}
            },
            "required": ["name", "isNew", "confidence"]
        },
        "examDate": {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "number"}
            }
        },
        "examType": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "enum": ["Klassenarbeit", "Test", "Übung", "Probe", "unknown"]},
                "confidence": {"type": "number"}
            }
        },
        "totalPoints": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "null"]},
                "confidence": {"type": "number"}
            }
        },
        "extractedTasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "taskNumber": {"type": "number"},
                    "questionText": {"type": "string"},
                    "points": {"type": ["number", "null"]},
                    "suggestedType": {
                        "type": "string",
                        "enum": ["MC_SingleChoice", "MC_MultipleChoice", "ShortAnswer", "CaseStudy", "FillInBlank", "Calculation", "DiagramAnalysis", "Matching", "Essay"]
                    },
                    "confidence": {"type": "number"}
                },
                "required": ["taskNumber", "questionText", "suggestedType", "confidence"]
            }
        },
        "overallConfidence": {"type": "number", "minimum": 0, "maximum": 100},
        "requiresReview": {"type": "boolean"},
        "reviewReasons": {"type": "array", "items": {"type": "string"}}
    }
}

def build_classification_prompt(ocr_text: str, existing_subjects: List[str], existing_teachers: List[str]) -> str:
    """Build the classification prompt with context."""
    return f"""{UPLOAD_CLASSIFICATION_SYSTEM_PROMPT}

```json
{json.dumps(UPLOAD_CLASSIFICATION_JSON_SCHEMA, indent=2)}
```

Bekannte Fächer: {', '.join(existing_subjects)}
Bekannte Lehrer: {', '.join(existing_teachers)}

--- OCR-TEXT DER KLASSENARBEIT ---
{ocr_text}
--- ENDE OCR-TEXT ---

Analysiere den Text und extrahiere die Informationen. Antworte NUR mit dem JSON:"""


# ============================================================================
# Exam Generation Pipeline Prompts
# ============================================================================

EXAM_GENERATION_SYSTEM_PROMPT = """Du bist ein Experte für die Erstellung von Prüfungsaufgaben für deutsche Berufsschulen (IHK/SIHK-Standard).
Deine Aufgabe ist es, eine realistische Übungsklausur zu erstellen basierend auf:
- Ausgewählten Themen
- Schwierigkeitsgrad (1-5)
- Gewünschter Aufgabenzahl und Dauer
- Optional: Stil eines bestimmten Lehrers
- Optional: Kontext aus alten Klassenarbeiten oder Lernmaterial

AUFGABENTYPEN:
1. **MC_SingleChoice**: Multiple Choice mit genau einer richtigen Antwort (4 Optionen)
2. **MC_MultipleChoice**: Multiple Choice mit mehreren richtigen Antworten
3. **ShortAnswer**: Kurzantwort (1-3 Sätze erwartet)
4. **CaseStudy**: Fallstudie mit Situationsbeschreibung und mehrteiligen Fragen
5. **FillInBlank**: Lückentext zum Ausfüllen
6. **Calculation**: Rechenaufgabe mit Formeln und Zahlen
7. **DiagramAnalysis**: Analyse eines Diagramms (Balken, Kreis, Linien)
8. **Matching**: Zuordnungsaufgabe (Begriffe zu Definitionen)
9. **Essay**: Längere Textaufgabe (Erörterung, Stellungnahme)

DIAGRAMM-AUFGABEN:
- Erstelle realistische Daten für Diagramme
- Balkendiagramme: Umsatz, Marktanteile, Vergleiche
- Kreisdiagramme: Prozentuale Verteilungen
- Die Daten müssen zur Frage passen und analysierbar sein

BEWERTUNGSKRITERIEN (Rubrics):
- Jede Aufgabe braucht klare Bewertungskriterien
- Bei offenen Aufgaben: Keywords und Erwartungen definieren
- Teilpunkte ermöglichen wo sinnvoll

WICHTIG:
- Aufgaben müssen zum IHK/Berufsschul-Niveau passen
- Deutsche Sprache, professioneller Ton
- Realistische Szenarien aus der Wirtschaft
- Punkteverteilung muss zur Schwierigkeit passen
- Gesamtpunktzahl sollte zur Dauer passen (~1 Punkt/Minute)

Antworte NUR mit validem JSON im MockExam-Format:"""

EXAM_GENERATION_JSON_SCHEMA = {
    "type": "object",
    "required": ["title", "description", "tasks", "totalPoints", "estimatedDurationMinutes", "difficultyLevel"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "taskNumber", "questionText", "points", "difficulty", "timeEstimateMinutes", "gradingRubric"],
                "properties": {
                    "type": {"type": "string"},
                    "taskNumber": {"type": "number"},
                    "questionText": {"type": "string"},
                    "questionImage": {"type": ["string", "null"]},
                    "options": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "isCorrect": {"type": "boolean"}
                            }
                        }
                    },
                    "correctAnswer": {"type": ["string", "null"]},
                    "modelAnswer": {"type": ["string", "null"]},
                    "calculationData": {
                        "type": ["object", "null"],
                        "properties": {
                            "formula": {"type": "string"},
                            "variables": {"type": "object"},
                            "expectedResult": {"type": "number"},
                            "tolerance": {"type": "number"}
                        }
                    },
                    "diagramSpec": {
                        "type": ["object", "null"],
                        "properties": {
                            "type": {"type": "string", "enum": ["bar", "pie", "line", "scatter"]},
                            "title": {"type": "string"},
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "value": {"type": "number"},
                                        "color": {"type": "string"}
                                    }
                                }
                            },
                            "xLabel": {"type": "string"},
                            "yLabel": {"type": "string"}
                        }
                    },
                    "matchingPairs": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "left": {"type": "string"},
                                "right": {"type": "string"}
                            }
                        }
                    },
                    "blanks": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "correctText": {"type": "string"},
                                "position": {"type": "number"}
                            }
                        }
                    },
                    "points": {"type": "number"},
                    "difficulty": {"type": "number", "minimum": 1, "maximum": 5},
                    "timeEstimateMinutes": {"type": "number"},
                    "gradingRubric": {
                        "type": "object",
                        "properties": {
                            "maxPoints": {"type": "number"},
                            "criteria": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "maxPoints": {"type": "number"}
                                    }
                                }
                            },
                            "autoGradable": {"type": "boolean"},
                            "partialCreditAllowed": {"type": "boolean"},
                            "keywords": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        },
        "totalPoints": {"type": "number"},
        "estimatedDurationMinutes": {"type": "number"},
        "difficultyLevel": {"type": "number"}
    }
}

def build_exam_generation_prompt(
    subject_name: str,
    thema_names: List[str],
    difficulty: int,
    task_count: int,
    duration_minutes: int,
    teacher_pattern: Optional[Dict[str, Any]] = None,
    free_prompt: Optional[str] = None,
    context_texts: Optional[List[str]] = None
) -> str:
    """Build the exam generation prompt with all context."""
    
    context_section = ""
    if context_texts:
        context_section = "\n\n--- KONTEXT-MATERIAL ---\n"
        for i, text in enumerate(context_texts, 1):
            context_section += f"\n[Material {i}]:\n{text[:2000]}...\n"  # Truncate long texts
        context_section += "--- ENDE KONTEXT ---\n"
    
    teacher_section = ""
    if teacher_pattern:
        teacher_section = f"""
--- LEHRER-STIL ---
Dieser Lehrer bevorzugt:
- Aufgabentyp-Verteilung: {json.dumps(teacher_pattern.get('question_type_distribution', {}), ensure_ascii=False)}
- Durchschnittliche Schwierigkeit: {teacher_pattern.get('avg_difficulty', 3)}
- Bewertungsstil: {teacher_pattern.get('grading_rubric_inference', {})}
--- ENDE LEHRER-STIL ---
"""
    
    free_prompt_section = ""
    if free_prompt:
        free_prompt_section = f"""
--- ZUSÄTZLICHE ANFORDERUNGEN ---
{free_prompt}
--- ENDE ANFORDERUNGEN ---
"""
    
    return f"""{EXAM_GENERATION_SYSTEM_PROMPT}

AUFGABE: Erstelle eine Übungsklausur mit folgenden Parametern:

Fach: {subject_name}
Themen: {', '.join(thema_names)}
Schwierigkeit: {difficulty}/5
Aufgabenanzahl: {task_count}
Bearbeitungszeit: {duration_minutes} Minuten
{teacher_section}
{free_prompt_section}
{context_section}

ANFORDERUNGEN:
- Mix verschiedener Aufgabentypen (MC, Kurzantwort, Fallstudie, etc.)
- Mindestens 1 Diagramm-Aufgabe wenn Schwierigkeit >= 3
- Mindestens 1 Rechenaufgabe wenn Thema es erlaubt
- Klare Bewertungskriterien für jede Aufgabe
- Realistische Fallbeispiele aus der deutschen Wirtschaft

Antworte NUR mit dem MockExam-JSON:"""


# ============================================================================
# Grading Pipeline Prompts
# ============================================================================

GRADING_SYSTEM_PROMPT = """Du bist ein erfahrener Prüfer für deutsche Berufsschul-Klausuren (IHK/SIHK-Standard).
Deine Aufgabe ist es, Schülerantworten fair und präzise zu bewerten.

BEWERTUNGSPRINZIPIEN:
1. **Objektivität**: Bewerte nach den vorgegebenen Kriterien, nicht nach Bauchgefühl
2. **Teilpunkte**: Vergib Teilpunkte für teilweise richtige Antworten
3. **Fachsprache**: Achte auf korrekte Verwendung von Fachbegriffen
4. **Vollständigkeit**: Prüfe ob alle geforderten Aspekte behandelt wurden
5. **Struktur**: Bei längeren Antworten auch Gliederung bewerten

KONFIDENZ-RICHTLINIEN:
- 90-100%: Antwort ist eindeutig richtig/falsch bewertbar
- 70-89%: Antwort ist größtenteils klar, kleine Unsicherheiten
- 50-69%: Antwort ist unklar, mehrere Interpretationen möglich
- <50%: Manuelle Überprüfung dringend empfohlen

FEEDBACK-RICHTLINIEN:
- Konstruktiv und ermutigend formulieren
- Konkrete Verbesserungsvorschläge geben
- Bei Fehlern erklären, was die richtige Antwort wäre
- Deutsche Sprache, professioneller Ton

Antworte NUR mit validem JSON im Grading-Format:"""

GRADING_JSON_SCHEMA = {
    "type": "object",
    "required": ["taskResults", "totalEarnedPoints", "totalMaxPoints", "percentage", "grade", "gradeText", "overallFeedback", "overallConfidence"],
    "properties": {
        "taskResults": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["taskId", "earnedPoints", "maxPoints", "isCorrect", "confidence", "feedback", "needsManualReview"],
                "properties": {
                    "taskId": {"type": "string"},
                    "earnedPoints": {"type": "number"},
                    "maxPoints": {"type": "number"},
                    "percentage": {"type": "number"},
                    "isCorrect": {"type": "boolean"},
                    "isPartiallyCorrect": {"type": "boolean"},
                    "autoGraded": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 100},
                    "feedback": {"type": "string"},
                    "feedbackType": {"type": "string", "enum": ["correct", "partial", "incorrect", "needs_review"]},
                    "detailedFeedback": {
                        "type": ["object", "null"],
                        "properties": {
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "weaknesses": {"type": "array", "items": {"type": "string"}},
                            "suggestions": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "criteriaScores": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "criterionName": {"type": "string"},
                                "earnedPoints": {"type": "number"},
                                "maxPoints": {"type": "number"},
                                "comment": {"type": "string"}
                            }
                        }
                    },
                    "needsManualReview": {"type": "boolean"},
                    "reviewReason": {"type": ["string", "null"]}
                }
            }
        },
        "totalEarnedPoints": {"type": "number"},
        "totalMaxPoints": {"type": "number"},
        "percentage": {"type": "number"},
        "grade": {"type": "number", "minimum": 1, "maximum": 6},
        "gradeText": {"type": "string"},
        "overallFeedback": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "areasForImprovement": {"type": "array", "items": {"type": "string"}},
        "studyRecommendations": {"type": "array", "items": {"type": "string"}},
        "overallConfidence": {"type": "number", "minimum": 0, "maximum": 100},
        "tasksNeedingReview": {"type": "array", "items": {"type": "string"}}
    }
}

def build_grading_prompt(tasks_with_answers: List[Dict[str, Any]]) -> str:
    """Build the grading prompt with all tasks and answers."""
    
    tasks_section = ""
    for task in tasks_with_answers:
        tasks_section += f"""
--- AUFGABE {task['taskNumber']} ---
Typ: {task['type']}
Frage: {task['questionText']}
Maximale Punkte: {task['points']}

Bewertungskriterien:
{json.dumps(task.get('gradingRubric', {}), indent=2, ensure_ascii=False)}

"""
        if task.get('correctAnswer'):
            tasks_section += f"Richtige Antwort: {task['correctAnswer']}\n"
        if task.get('modelAnswer'):
            tasks_section += f"Musterlösung: {task['modelAnswer']}\n"
        
        tasks_section += f"""
SCHÜLER-ANTWORT:
{task.get('userAnswer', '[Keine Antwort]')}
--- ENDE AUFGABE {task['taskNumber']} ---
"""
    
    return f"""{GRADING_SYSTEM_PROMPT}

BEWERTUNGSAUFTRAG:
Bewerte die folgenden Aufgaben und Schüler-Antworten.

{tasks_section}

NOTENBERECHNUNG (IHK-Standard):
- 92-100% = 1 (Sehr gut)
- 81-91% = 2 (Gut)  
- 67-80% = 3 (Befriedigend)
- 50-66% = 4 (Ausreichend)
- 30-49% = 5 (Mangelhaft)
- 0-29% = 6 (Ungenügend)

Antworte NUR mit dem Grading-JSON:"""


# ============================================================================
# Model Calling Helpers
# ============================================================================

async def call_classification_model(
    ocr_text: str,
    existing_subjects: List[str],
    existing_teachers: List[str],
    model_client: Any  # OllamaClient or AnthropicClient
) -> Dict[str, Any]:
    """Call the classification model and parse response."""
    prompt = build_classification_prompt(ocr_text, existing_subjects, existing_teachers)
    
    response = await model_client.generate(
        prompt=prompt,
        temperature=0.1,  # Low temperature for consistent classification
        max_tokens=4000
    )
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse classification JSON: {e}",
            "raw_response": response
        }
    
    return {"error": "No JSON found in response", "raw_response": response}


async def call_exam_generator_model(
    subject_name: str,
    thema_names: List[str],
    difficulty: int,
    task_count: int,
    duration_minutes: int,
    model_client: Any,
    teacher_pattern: Optional[Dict[str, Any]] = None,
    free_prompt: Optional[str] = None,
    context_texts: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Call the exam generator model and parse response."""
    prompt = build_exam_generation_prompt(
        subject_name=subject_name,
        thema_names=thema_names,
        difficulty=difficulty,
        task_count=task_count,
        duration_minutes=duration_minutes,
        teacher_pattern=teacher_pattern,
        free_prompt=free_prompt,
        context_texts=context_texts
    )
    
    response = await model_client.generate(
        prompt=prompt,
        temperature=0.7,  # Higher temperature for creative task generation
        max_tokens=16000  # Longer output for full exam
    )
    
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse exam JSON: {e}",
            "raw_response": response
        }
    
    return {"error": "No JSON found in response", "raw_response": response}


async def call_grading_model(
    tasks_with_answers: List[Dict[str, Any]],
    model_client: Any
) -> Dict[str, Any]:
    """Call the grading model and parse response."""
    prompt = build_grading_prompt(tasks_with_answers)
    
    response = await model_client.generate(
        prompt=prompt,
        temperature=0.2,  # Low temperature for consistent grading
        max_tokens=8000
    )
    
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse grading JSON: {e}",
            "raw_response": response
        }
    
    return {"error": "No JSON found in response", "raw_response": response}

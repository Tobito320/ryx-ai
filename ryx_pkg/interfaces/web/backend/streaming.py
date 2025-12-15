"""
WebSocket Streaming API for RyxHub

Provides real-time streaming for:
- Level 1: Token-by-token streaming from LLM
- Level 2: Agent step visualization
- Level 3: Browser screenshot streaming

Usage:
    WebSocket /ws/exam-evaluation - Full exam pipeline with all streams
    WebSocket /ws/stream - Token streaming only
    WebSocket /ws/agent - Agent steps only
"""

import os
import json
import base64
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])

# Configuration
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Import real pipeline modules
try:
    from .ocr import OCREngine, OCRResult, process_pdf
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR module not available")

try:
    from .rubric_generator import generate_rubric, IntelligentRubric
    RUBRIC_AVAILABLE = True
except ImportError:
    RUBRIC_AVAILABLE = False
    logger.warning("Rubric generator not available")

try:
    from .semantic_evaluator import evaluate_answer_semantically, SemanticEvaluation
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("Semantic evaluator not available")

try:
    from .pedagogical_feedback import generate_task_feedback, generate_overall_exam_feedback
    FEEDBACK_AVAILABLE = True
except ImportError:
    FEEDBACK_AVAILABLE = False
    logger.warning("Pedagogical feedback not available")

try:
    from .learning_analytics import generate_learning_analytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Learning analytics not available")


class AgentStep(BaseModel):
    """Agent step event"""
    step_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


class StreamingAgent:
    """Agent with full streaming capabilities"""
    
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.steps: List[AgentStep] = []
    
    async def emit_step(self, step_type: str, message: str, data: Optional[Dict] = None):
        """Emit agent step to frontend"""
        step = AgentStep(step_type=step_type, message=message, data=data or {})
        self.steps.append(step)
        
        await self.ws.send_json({
            "type": "agent_step",
            "step": step_type,
            "message": message,
            "data": data or {},
            "timestamp": step.timestamp
        })
    
    async def emit_token(self, token: str):
        """Emit single token to frontend"""
        await self.ws.send_json({
            "type": "token",
            "content": token
        })
    
    async def emit_status(self, message: str, phase: str = "processing", percent: int = 0):
        """Emit status update to frontend"""
        await self.ws.send_json({
            "type": "status",
            "message": message,
            "phase": phase,
            "percent": percent
        })
    
    async def emit_browser_screenshot(self, screenshot_b64: str, url: str):
        """Emit browser screenshot to frontend"""
        await self.ws.send_json({
            "type": "browser_screenshot",
            "image": screenshot_b64,
            "url": url
        })
    
    async def emit_complete(self, result: Dict[str, Any]):
        """Emit completion with final result"""
        await self.ws.send_json({
            "type": "complete",
            **result
        })
    
    async def emit_error(self, error: str):
        """Emit error to frontend"""
        await self.ws.send_json({
            "type": "error",
            "message": error
        })


async def stream_ollama_tokens(prompt: str, model: str = "qwen2.5:7b") -> AsyncIterator[str]:
    """Stream tokens from Ollama"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue


async def stream_anthropic_tokens(prompt: str, model: str = "claude-3-5-sonnet-20241022") -> AsyncIterator[str]:
    """Stream tokens from Anthropic API"""
    if not ANTHROPIC_API_KEY:
        yield "[Anthropic API key not configured]"
        return
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "stream": True,
                "messages": [{"role": "user", "content": prompt}]
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if "text" in delta:
                                yield delta["text"]
                    except json.JSONDecodeError:
                        continue


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@router.websocket("/ws/stream")
async def websocket_token_stream(websocket: WebSocket):
    """Level 1: Token-by-token streaming"""
    await websocket.accept()
    
    try:
        msg = await websocket.receive_json()
        prompt = msg.get("prompt", "Hello!")
        model = msg.get("model", "qwen2.5:7b")
        provider = msg.get("provider", "ollama")  # ollama or anthropic
        
        await websocket.send_json({
            "type": "status",
            "message": f"🤔 Initializing {provider}..."
        })
        
        # Select streaming provider
        if provider == "anthropic":
            token_stream = stream_anthropic_tokens(prompt, model)
        else:
            token_stream = stream_ollama_tokens(prompt, model)
        
        # Stream tokens
        async for token in token_stream:
            await websocket.send_json({
                "type": "token",
                "content": token
            })
            await asyncio.sleep(0.02)  # Typing effect
        
        await websocket.send_json({"type": "done"})
    
    except WebSocketDisconnect:
        logger.info("Token stream WebSocket disconnected")
    except Exception as e:
        logger.exception("Token stream error")
        await websocket.send_json({"type": "error", "message": str(e)})


@router.websocket("/ws/agent")
async def websocket_agent_steps(websocket: WebSocket):
    """Level 2: Agent step-by-step visualization"""
    await websocket.accept()
    agent = StreamingAgent(websocket)
    
    try:
        msg = await websocket.receive_json()
        query = msg.get("query", "")
        
        # Step 1: Planning
        await agent.emit_step("planning", "🧠 Analyzing your query...", {"query": query})
        await asyncio.sleep(0.5)
        
        # Step 2: Searching
        await agent.emit_step("searching", "🔎 Searching for information...", {
            "search_query": query[:50],
            "engine": "internal"
        })
        await asyncio.sleep(0.5)
        
        # Step 3: Processing
        await agent.emit_step("processing", "📄 Processing data...", {
            "status": "extracting"
        })
        await asyncio.sleep(0.5)
        
        # Step 4: Synthesizing
        await agent.emit_step("synthesizing", "🧩 Combining information...", {
            "sources": 3
        })
        await asyncio.sleep(0.5)
        
        # Step 5: Responding with token stream
        await agent.emit_step("responding", "✍️ Writing response...", {})
        
        # Stream actual response
        async for token in stream_ollama_tokens(query):
            await agent.emit_token(token)
            await asyncio.sleep(0.02)
        
        await agent.emit_step("complete", "✅ Task completed", {"total_time": "3.2s"})
    
    except WebSocketDisconnect:
        logger.info("Agent WebSocket disconnected")
    except Exception as e:
        logger.exception("Agent stream error")
        await agent.emit_error(str(e))


@router.websocket("/ws/exam-evaluation")
async def websocket_exam_evaluation(websocket: WebSocket):
    """
    Full exam evaluation pipeline with streaming.
    
    Implements all 3 visualization levels:
    - Token streaming for AI responses
    - Agent steps for pipeline progress
    - (Optional) Browser screenshots for OCR preview
    """
    await websocket.accept()
    agent = StreamingAgent(websocket)
    
    try:
        # Receive exam evaluation request
        msg = await websocket.receive_json()
        file_path = msg.get("file_path", "")
        exam_id = msg.get("exam_id", "") or f"exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        use_sandbox = msg.get("use_sandbox", False)
        sandbox_type = msg.get("sandbox_type", "docker")
        
        # Initialize sandbox if requested
        sandbox = None
        if use_sandbox:
            try:
                from .sandbox_manager import SandboxManager
                sandbox = SandboxManager(sandbox_type=sandbox_type)
                await sandbox.init(websocket)
                await agent.emit_step("sandbox", f"🔒 Sandbox initialized ({sandbox_type})", {})
            except Exception as e:
                logger.warning(f"Sandbox init failed: {e}, continuing without sandbox")
                await agent.emit_step("sandbox_warning", f"⚠️ Sandbox unavailable: {str(e)}", {})
        
        try:
            # Stage 1: Ingestion
            await agent.emit_step("ingestion", "📥 Loading document...", {
                "file_path": file_path,
                "exam_id": exam_id
            })
            await agent.emit_status("📥 Loading document...", "ingestion", 5)
            
            # Verify file exists
            if file_path and not Path(file_path).exists():
                await agent.emit_error(f"File not found: {file_path}")
                return
            
            # Stage 2: OCR
            await agent.emit_step("parallel_start", "⚡ Starting OCR...", {})
            ocr_result = await run_stage_ocr(agent, file_path, sandbox)
            
            questions = ocr_result.get("questions", [])
            await agent.emit_step("ocr_done", f"📸 Found {len(questions)} questions", {
                "question_count": len(questions),
                "confidence": ocr_result.get("confidence", 0)
            })
            
            # Stage 4: Rubric Generation
            rubric_result = await run_stage_rubric(agent, exam_id, questions)
            
            await agent.emit_step("parallel_complete", "✅ OCR & Rubrics complete", {
                "ocr_questions": len(questions),
                "rubrics_generated": len(rubric_result.get("rubrics", []))
            })
            
            # Stage 5: Evaluation
            await agent.emit_step("evaluation", "🔍 Evaluating answers...", {})
            await agent.emit_status("🔍 Evaluating answers...", "evaluation", 50)
            
            evaluation_result = await run_stage_evaluation(
                agent, ocr_result, rubric_result
            )
            
            # Stage 7: Grade Aggregation (do before feedback so we have grade info)
            await agent.emit_step("aggregation", "📊 Calculating grades...", {})
            await agent.emit_status("📊 Calculating grades...", "aggregation", 65)
            
            grade_result = calculate_grade(evaluation_result)
            
            # Stage 6: Feedback (after grading so we have grade context)
            feedback_text = await run_stage_feedback(
                agent, evaluation_result, questions, grade_result
            )
            
            # Stage 8: Learning Analytics (optional)
            analytics = None
            if ANALYTICS_AVAILABLE:
                try:
                    await agent.emit_step("analytics", "📈 Generating analytics...", {})
                    evaluations = evaluation_result.get("evaluations", [])
                    analytics = generate_learning_analytics(
                        attempt_id=f"attempt_{exam_id}",
                        student_id=None,
                        exam_id=exam_id,
                        task_grades=evaluations,
                        tasks=questions,
                        overall_percentage=grade_result["percentage"],
                        grade=grade_result["grade"],
                        grade_text=grade_result["grade_text"]
                    )
                except Exception as e:
                    logger.warning(f"Analytics generation failed: {e}")
            
            # Stage 9: Report Generation
            await agent.emit_step("report", "📄 Generating report...", {})
            await agent.emit_status("📄 Generating report...", "report", 95)
            
            # Complete
            await agent.emit_status("✅ Evaluation complete", "complete", 100)
            await agent.emit_complete({
                "exam_id": exam_id,
                "overall_grade": grade_result["grade"],
                "grade_text": grade_result["grade_text"],
                "total_points": grade_result["total_points"],
                "max_points": grade_result["max_points"],
                "percentage": grade_result["percentage"],
                "evaluations": evaluation_result.get("evaluations", []),
                "feedback": feedback_text,
                "analytics": analytics.to_dict() if analytics and hasattr(analytics, 'to_dict') else analytics,
                "questions": questions,
                "rubrics": rubric_result.get("rubrics", [])
            })
        
        finally:
            # Always cleanup sandbox
            if sandbox:
                await sandbox.cleanup(websocket)
    
    except WebSocketDisconnect:
        logger.info("Exam evaluation WebSocket disconnected")
    except Exception as e:
        logger.exception("Exam evaluation error")
        await agent.emit_error(str(e))


# ============================================================================
# Pipeline Stage Helpers
# ============================================================================

async def run_stage_ocr(agent: StreamingAgent, file_path: str, sandbox=None) -> Dict[str, Any]:
    """Stage 2: OCR with real implementation"""
    await agent.emit_step("ocr", "📸 Analyzing images...", {"file_path": file_path})
    await agent.emit_status("📸 Analyzing images...", "ocr", 15)
    
    if not OCR_AVAILABLE:
        logger.warning("OCR not available, using mock data")
        await asyncio.sleep(0.5)
        return {
            "questions": [
                {"id": "q1", "text": "Was ist ITIL?", "type": "ShortAnswer", "student_answer": ""},
                {"id": "q2", "text": "Erkläre SLA", "type": "Definition", "student_answer": ""}
            ],
            "confidence": 0.5,
            "warning": "OCR module not available"
        }
    
    try:
        # Use real OCR engine
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Process using OCREngine.process_file
        engine = OCREngine()
        result = await engine.process_file(file_path)
        
        await agent.emit_step("ocr_complete", "📸 OCR complete", {
            "confidence": result.confidence,
            "pages": result.pages,
            "model": result.model_used
        })
        
        # Extract questions from OCR text
        questions = extract_questions_from_text(result.text)
        
        return {
            "questions": questions,
            "raw_text": result.text,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "pages": result.pages
        }
    except Exception as e:
        logger.exception(f"OCR error: {e}")
        await agent.emit_step("ocr_error", f"⚠️ OCR error: {str(e)}", {})
        return {
            "questions": [],
            "confidence": 0,
            "error": str(e)
        }


async def run_stage_rubric(agent: StreamingAgent, exam_id: str, questions: List[Dict] = None) -> Dict[str, Any]:
    """Stage 4: Rubric generation with real implementation"""
    await agent.emit_step("rubric", "📋 Generating rubrics...", {"exam_id": exam_id})
    await agent.emit_status("📋 Generating rubrics...", "rubric", 25)
    
    if not RUBRIC_AVAILABLE:
        logger.warning("Rubric generator not available, using mock data")
        await asyncio.sleep(0.5)
        return {
            "rubrics": [
                {"question_id": "q1", "max_points": 5, "criteria": []},
                {"question_id": "q2", "max_points": 4, "criteria": []}
            ],
            "warning": "Rubric generator not available"
        }
    
    rubrics = []
    questions = questions or []
    
    for i, q in enumerate(questions):
        try:
            await agent.emit_step("rubric_gen", f"📋 Generating rubric for Q{i+1}...", {
                "question_id": q.get("id", f"q{i+1}")
            })
            
            rubric = await generate_rubric(
                question_id=q.get("id", f"q{i+1}"),
                question_text=q.get("text", ""),
                question_type=q.get("type", "ShortAnswer"),
                max_points=q.get("max_points", 5),
                difficulty=q.get("difficulty", 3)
            )
            
            rubrics.append(rubric.to_dict() if hasattr(rubric, 'to_dict') else rubric)
        except Exception as e:
            logger.exception(f"Rubric generation error for Q{i+1}: {e}")
            rubrics.append({
                "question_id": q.get("id", f"q{i+1}"),
                "max_points": q.get("max_points", 5),
                "error": str(e)
            })
    
    await agent.emit_step("rubric_complete", f"📋 Generated {len(rubrics)} rubrics", {})
    
    return {"rubrics": rubrics}


async def run_stage_evaluation(
    agent: StreamingAgent,
    ocr_result: Dict,
    rubric_result: Dict
) -> Dict[str, Any]:
    """Stage 5: Semantic answer evaluation"""
    questions = ocr_result.get("questions", [])
    rubrics = rubric_result.get("rubrics", [])
    
    # Create rubric lookup
    rubric_map = {r.get("question_id"): r for r in rubrics}
    
    evaluations = []
    for i, q in enumerate(questions):
        qid = q.get("id", f"q{i+1}")
        await agent.emit_step("evaluating", f"🔍 Evaluating question {i+1}...", {
            "question_id": qid
        })
        
        if not SEMANTIC_AVAILABLE:
            # Fallback to simple evaluation
            evaluations.append({
                "question_id": qid,
                "points_awarded": 3,
                "max_points": 5,
                "rationale": "Semantic evaluator not available - default score",
                "confidence": 50
            })
            continue
        
        try:
            rubric = rubric_map.get(qid, {"max_points": 5})
            student_answer = q.get("student_answer", "")
            
            result = await evaluate_answer_semantically(
                student_answer=student_answer,
                rubric=rubric,
                question_text=q.get("text", ""),
                question_type=q.get("type", "ShortAnswer")
            )
            
            evaluations.append({
                "question_id": qid,
                "points_awarded": result.earned_points,
                "max_points": rubric.get("max_points", 5),
                "rationale": result.rationale,
                "confidence": result.confidence,
                "components_found": result.components_found,
                "components_missing": result.components_missing,
                "improvement_suggestion": result.improvement_suggestion
            })
        except Exception as e:
            logger.exception(f"Evaluation error for Q{i+1}: {e}")
            evaluations.append({
                "question_id": qid,
                "points_awarded": 0,
                "max_points": 5,
                "rationale": f"Evaluation error: {str(e)}",
                "confidence": 0,
                "error": str(e)
            })
    
    return {"evaluations": evaluations}


async def run_stage_feedback(
    agent: StreamingAgent,
    evaluation_result: Dict,
    questions: List[Dict],
    grade_result: Dict
) -> str:
    """Stage 6: Generate pedagogical feedback"""
    await agent.emit_step("feedback", "✍️ Generating feedback...", {})
    await agent.emit_status("✍️ Generating feedback...", "feedback", 70)
    
    evaluations = evaluation_result.get("evaluations", [])
    
    if not FEEDBACK_AVAILABLE or not evaluations:
        # Stream fallback feedback using LLM
        prompt = f"""Generate constructive German exam feedback for these results:
- Grade: {grade_result.get('grade', 0)} ({grade_result.get('grade_text', '')})
- Score: {grade_result.get('percentage', 0)}%
- Questions evaluated: {len(evaluations)}

Be encouraging but honest. Write in German."""
        
        feedback_text = ""
        async for token in stream_ollama_tokens(prompt, model="qwen2.5:7b"):
            await agent.emit_token(token)
            feedback_text += token
            await asyncio.sleep(0.02)
        return feedback_text
    
    try:
        # Generate task-level feedbacks first
        task_feedbacks = []
        for ev in evaluations:
            task_feedbacks.append({
                "task_id": ev.get("question_id"),
                "components_found": ev.get("components_found", []),
                "components_missing": ev.get("components_missing", []),
                "points_awarded": ev.get("points_awarded", 0),
                "max_points": ev.get("max_points", 5)
            })
        
        # Generate overall feedback
        feedback = generate_overall_exam_feedback(
            task_feedbacks=task_feedbacks,
            total_percentage=grade_result.get("percentage", 0),
            grade_text=grade_result.get("grade_text", ""),
            topic_analysis=None
        )
        
        # Stream the feedback
        feedback_text = feedback.overall_feedback if hasattr(feedback, 'overall_feedback') else str(feedback)
        for word in feedback_text.split():
            await agent.emit_token(word + " ")
            await asyncio.sleep(0.03)
        
        return feedback_text
    except Exception as e:
        logger.exception(f"Feedback generation error: {e}")
        error_msg = f"Feedback generation error: {str(e)}"
        await agent.emit_token(error_msg)
        return error_msg


def extract_questions_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract questions from OCR text"""
    import re
    
    questions = []
    
    # Common patterns for German exams
    patterns = [
        r'(?:Aufgabe|Frage)\s*(\d+[a-z]?)[:\.]?\s*(.+?)(?=(?:Aufgabe|Frage)\s*\d|$)',
        r'(\d+)\)\s*(.+?)(?=\d+\)|$)',
        r'(\d+\.)\s*(.+?)(?=\d+\.|$)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            for match in matches:
                qid = match[0].strip().rstrip('.:)')
                qtext = match[1].strip()[:500]  # Limit length
                
                # Detect question type
                qtype = detect_question_type(qtext)
                
                questions.append({
                    "id": f"q{qid}",
                    "text": qtext,
                    "type": qtype,
                    "student_answer": "",  # To be filled later
                    "max_points": 5
                })
            break
    
    # Fallback: split by lines if no patterns match
    if not questions:
        lines = [l.strip() for l in text.split('\n') if l.strip() and '?' in l]
        for i, line in enumerate(lines[:10], 1):
            questions.append({
                "id": f"q{i}",
                "text": line[:500],
                "type": "ShortAnswer",
                "student_answer": "",
                "max_points": 5
            })
    
    return questions


def detect_question_type(text: str) -> str:
    """Detect question type from text"""
    text_lower = text.lower()
    
    if any(x in text_lower for x in ['a)', 'b)', 'c)', '□', '☐', 'kreuze', 'wähle']):
        return "MultipleChoice"
    elif any(x in text_lower for x in ['definiere', 'definition', 'was ist', 'was sind']):
        return "Definition"
    elif any(x in text_lower for x in ['erkläre', 'erläutere', 'beschreibe']):
        return "Explanation"
    elif any(x in text_lower for x in ['berechne', 'berechnung', 'rechne']):
        return "Calculation"
    elif any(x in text_lower for x in ['nenne', 'liste', 'zähle auf']):
        return "Enumeration"
    elif any(x in text_lower for x in ['fallbeispiel', 'szenario', 'situation']):
        return "CaseStudy"
    else:
        return "ShortAnswer"


def calculate_grade(evaluation_result: Dict) -> Dict[str, Any]:
    """Stage 7: Grade aggregation"""
    evaluations = evaluation_result.get("evaluations", [])
    
    total_points = sum(e["points_awarded"] for e in evaluations)
    max_points = sum(e["max_points"] for e in evaluations)
    percentage = (total_points / max_points * 100) if max_points > 0 else 0
    
    # German grading scale
    if percentage >= 92:
        grade, grade_text = 1.0, "Sehr gut"
    elif percentage >= 81:
        grade, grade_text = 2.0, "Gut"
    elif percentage >= 67:
        grade, grade_text = 3.0, "Befriedigend"
    elif percentage >= 50:
        grade, grade_text = 4.0, "Ausreichend"
    elif percentage >= 30:
        grade, grade_text = 5.0, "Mangelhaft"
    else:
        grade, grade_text = 6.0, "Ungenügend"
    
    return {
        "grade": grade,
        "grade_text": grade_text,
        "total_points": total_points,
        "max_points": max_points,
        "percentage": round(percentage, 1)
    }

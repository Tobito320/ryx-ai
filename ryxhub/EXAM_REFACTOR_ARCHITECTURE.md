# RyxHub Exam System Refactoring Architecture

## 🎯 Problem Analysis

### Current Issues
1. **Wrong Classification**: "IT Service" test classified as "Marktforschung"
2. **Hardcoded Tasks**: `generate_sample_tasks()` returns static questions, ignoring actual context
3. **Fake Grading**: Open questions get `task.points // 2` mock scores
4. **No Prompt Input**: MockExamGenerator doesn't accept free-form prompts
5. **Missing Diagram Tasks**: DiagramAnalysis exists in types but not in generation
6. **No Multi-Model Pipeline**: OCR/Classification/Generation happens instantly without real AI

## 🏗️ New Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE (React)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  TestUploadDialog    │  MockExamGenerator    │  ExamTakingView              │
│  + Pipeline Steps    │  + Free Prompt        │  + All TaskTypes             │
│  + Review Dialog     │  + Context Upload     │  + Real-time Grading         │
└──────────┬───────────┴──────────┬────────────┴──────────┬───────────────────┘
           │                      │                        │
           ▼                      ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ UPLOAD PIPELINE  │  │ EXAM GENERATOR   │  │ GRADING PIPELINE │           │
│  │                  │  │                  │  │                  │           │
│  │ 1. Vision/OCR    │  │ 1. Context Build │  │ 1. Task Analysis │           │
│  │    - PaddleOCR   │  │ 2. Prompt Build  │  │ 2. AI Grading    │           │
│  │    - Fallback    │  │ 3. AI Generate   │  │ 3. Confidence    │           │
│  │ 2. Classifier    │  │ 4. Validation    │  │ 4. Aggregation   │           │
│  │    - Local 8B    │  │ 5. User Preview  │  │                  │           │
│  │ 3. User Review   │  │                  │  │                  │           │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘           │
│           │                     │                      │                     │
│           ▼                     ▼                      ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      AI MODEL ROUTER                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │   │
│  │  │  Ollama    │  │  Claude    │  │  Local     │  │  Vision    │      │   │
│  │  │  8B/14B    │  │  Opus 4.5  │  │  OCR       │  │  LLM       │      │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 File Changes Overview

### Backend (Python)

| File | Change |
|------|--------|
| `exam_api_v2.py` | Complete rewrite with pipeline architecture |
| `ai_prompts.py` | New prompts for OCR, Classification, Generation, Grading |
| `pipeline_service.py` | New: Pipeline orchestration |
| `model_router.py` | New: Multi-model routing |
| `ocr_service.py` | New: OCR with PaddleOCR + fallbacks |

### Frontend (TypeScript)

| File | Change |
|------|--------|
| `types/exam.ts` | Add new TaskTypes, extend existing types |
| `types/ai-pipeline.ts` | Already has good pipeline types |
| `MockExamGenerator.tsx` | Add free prompt, context upload, task preview |
| `TestUploadDialog.tsx` | Add pipeline steps visualization |
| `ExamTakingView.tsx` | Support all TaskTypes generically |
| `context/ExamContext.tsx` | Connect to real backend pipelines |

## 🔧 Implementation Plan

### Phase 1: Backend Pipeline Infrastructure

1. **Create `pipeline_service.py`**
   - Pipeline state management
   - Step execution with retries
   - WebSocket progress updates

2. **Create `model_router.py`**
   - Model selection based on task
   - Fallback chains
   - Load balancing

3. **Create `ocr_service.py`**
   - PaddleOCR integration
   - Tesseract fallback
   - Text block extraction

### Phase 2: AI Prompts

1. **OCR Post-Processing Prompt**
   - Extract structured data from raw OCR text
   - Identify task boundaries

2. **Classification Prompt**
   - Subject/Thema detection
   - Teacher style inference
   - Task type classification

3. **Exam Generation Prompt**
   - Accept context + free prompt
   - Generate structured JSON
   - Include all TaskTypes

4. **Grading Prompt**
   - Rubric-based evaluation
   - Partial credit calculation
   - Confidence scoring

### Phase 3: Backend Endpoints

1. **`POST /api/exam/v2/upload-test`**
   - Returns analysis_id immediately
   - Streams pipeline progress via SSE
   - Returns classification with confidence

2. **`POST /api/exam/v2/upload-test/{id}/confirm`**
   - Accept user corrections
   - Persist ClassTest

3. **`POST /api/exam/v2/generate-exam`**
   - Accept context + prompt
   - Stream generation progress
   - Return preview for editing

4. **`POST /api/exam/v2/grade-attempt`**
   - AI grading with confidence
   - Flag low-confidence for review

### Phase 4: Frontend Updates

1. **MockExamGenerator**
   - Free prompt textarea
   - Upload context materials
   - Task type distribution sliders
   - Preview generated tasks

2. **TestUploadDialog**
   - Step-by-step pipeline view
   - Real-time progress
   - Classification review dialog

3. **ExamTakingView**
   - Generic task renderer
   - Support all TaskTypes
   - Real grading integration

## 📝 Data Models

### Enhanced Task Types

```typescript
// New in types/exam.ts
export type TaskType =
  | "MC_SingleChoice"
  | "MC_MultipleChoice"
  | "ShortAnswer"
  | "FillInBlank"
  | "Matching"
  | "CaseStudy"
  | "DiagramAnalysis_Bar"      // NEW: specific diagram types
  | "DiagramAnalysis_Pie"      // NEW
  | "DiagramAnalysis_Line"     // NEW
  | "DiagramAnalysis_SWOT"     // NEW
  | "Calculation"
  | "Explanation"
  | "Justification"
  | "Ordering";                 // NEW: put items in correct order
```

### Exam Generation Request

```typescript
interface ExamGenerationRequest {
  subjectId: string;
  themaIds: string[];
  
  // Settings
  difficulty: 1 | 2 | 3 | 4 | 5;
  taskCount: number;
  durationMinutes: number;
  
  // Optional teacher pattern
  teacherId?: string;
  useTeacherPattern: boolean;
  
  // FREE PROMPT (NEW!)
  freePrompt?: string;
  
  // Context materials (NEW!)
  contextClassTestIds?: string[];
  contextText?: string;          // Pasted Perplexity text
  contextFiles?: File[];         // Additional uploads
  
  // Task distribution (optional)
  taskTypeDistribution?: Partial<Record<TaskType, number>>;
  
  // Diagram settings
  includeDiagrams: boolean;
  diagramTypes?: DiagramType[];
}
```

### Grading Result with Confidence

```typescript
interface TaskGradingResult {
  taskId: string;
  earnedPoints: number;
  maxPoints: number;
  
  // Confidence-based
  confidence: number;           // 0-100
  needsManualReview: boolean;
  reviewReason?: string;
  
  // Feedback
  feedback: string;
  rubricBreakdown?: {
    criterionName: string;
    score: number;
    maxScore: number;
    comment: string;
  }[];
  
  // For improvement
  suggestions?: string[];
  relatedStudyTopics?: string[];
}
```

## 🔐 Guardrails

1. **No persisting low-confidence classifications**
   - Threshold: 75% minimum
   - Below threshold → User review required

2. **Type-safe throughout**
   - Pydantic models with validation
   - TypeScript strict mode

3. **Graceful fallbacks**
   - OCR: PaddleOCR → Tesseract → Error
   - Generation: Claude → Ollama → Error
   - Grading: AI → Rule-based for MC → Manual

4. **User always has control**
   - Can edit generated tasks
   - Can correct classifications
   - Can request re-grading

## 📊 Success Metrics

1. **Classification Accuracy**
   - IT Service test → IT subject (not Marktforschung)
   - Confidence > 85% for clear cases

2. **Generation Quality**
   - Uses actual context
   - Responds to free prompt
   - Includes all requested TaskTypes

3. **Grading Accuracy**
   - MC: 100% (deterministic)
   - Open: Confidence correlates with accuracy
   - Low confidence triggers review

4. **UX Quality**
   - Clear pipeline progress
   - < 30s for upload processing
   - < 60s for exam generation

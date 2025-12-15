/**
 * AI Pipeline Types for RyxHub Exam System
 * 
 * Defines types for multi-model processing pipelines:
 * - Upload Pipeline (Vision/OCR → NLP Classifier → User Review)
 * - Exam Generation Pipeline (Context → Generator → Preview)
 * - Grading Pipeline (Attempt → Grader → Scores)
 */

// ============================================================================
// Pipeline Status & Progress
// ============================================================================

export type PipelineStatus = 
  | 'idle'
  | 'running'
  | 'waiting_review'  // Needs user confirmation
  | 'completed'
  | 'failed';

export type ModelPhase = 
  | 'vision_ocr'       // PDF/Image → Text extraction
  | 'nlp_classifier'   // Text → Thema/Fach/Lehrer classification
  | 'exam_generator'   // Context → MockExam JSON
  | 'grader'           // Answers → Scores + Feedback
  | 'aggregator';      // Combine results

export interface PipelineStep {
  id: string;
  phase: ModelPhase;
  label: string;           // German label for UI
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  error?: string;
  confidence?: number;     // 0-100
  output?: unknown;        // Phase-specific output
}

export interface PipelineProgress {
  pipelineId: string;
  status: PipelineStatus;
  currentPhase: ModelPhase | null;
  steps: PipelineStep[];
  startedAt: string;
  completedAt?: string;
  totalDurationMs?: number;
}

// ============================================================================
// Upload Pipeline Types
// ============================================================================

export interface OCRBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  pageIndex: number;
}

export interface OCRTextBlock {
  text: string;
  confidence: number;
  boundingBox?: OCRBoundingBox;
  type: 'heading' | 'paragraph' | 'list_item' | 'table_cell' | 'handwriting' | 'unknown';
}

export interface OCRResult {
  success: boolean;
  rawText: string;
  blocks: OCRTextBlock[];
  pageCount: number;
  language: string;
  overallConfidence: number;  // 0-100
  processingTimeMs: number;
  modelUsed: string;
  warnings?: string[];
}

export interface ExtractedTask {
  taskNumber: number;
  questionText: string;
  points?: number;
  suggestedType: string;    // TaskType suggestion
  confidence: number;
  rawBlock?: string;        // Original OCR block
}

export interface ClassificationResult {
  // Subject/Topic Classification
  subject: {
    id: string;
    name: string;
    confidence: number;
  };
  mainThema: {
    id: string;
    name: string;
    confidence: number;
  };
  additionalThemas: Array<{
    id: string;
    name: string;
    confidence: number;
  }>;
  
  // Teacher Detection
  teacher: {
    id: string | null;
    name: string | null;
    isNew: boolean;
    confidence: number;
  };
  
  // Metadata
  examDate: {
    value: string | null;
    confidence: number;
  };
  examType: {
    value: 'Klassenarbeit' | 'Test' | 'Übung' | 'Probe' | 'unknown';
    confidence: number;
  };
  totalPoints: {
    value: number | null;
    confidence: number;
  };
  duration: {
    value: number | null;  // minutes
    confidence: number;
  };
  
  // Extracted Tasks
  extractedTasks: ExtractedTask[];
  
  // Overall
  overallConfidence: number;
  requiresReview: boolean;
  reviewReasons: string[];
  modelUsed: string;
  processingTimeMs: number;
}

export interface UploadAnalysisResult {
  analysisId: string;
  filename: string;
  fileHash: string;
  ocr: OCRResult;
  classification: ClassificationResult;
  pipeline: PipelineProgress;
  
  // For user review
  suggestedCorrections?: Array<{
    field: string;
    currentValue: string;
    suggestedValue: string;
    reason: string;
  }>;
}

export interface UploadConfirmRequest {
  analysisId: string;
  corrections: {
    subjectId?: string;
    mainThemaId?: string;
    additionalThemaIds?: string[];
    teacherId?: string;
    teacherName?: string;  // If creating new teacher
    examDate?: string;
    examType?: string;
    totalPoints?: number;
  };
  skipTasks?: number[];  // Task numbers to exclude
}

// ============================================================================
// Exam Generation Pipeline Types
// ============================================================================

export interface ExamGenerationContext {
  // Required
  subjectId: string;
  themaIds: string[];
  
  // Generation Settings
  difficulty: number;        // 1-5
  taskCount: number;         // 10-30
  durationMinutes: number;   // 30-180
  
  // Optional Teacher Pattern
  teacherId?: string;
  useTeacherPattern: boolean;
  
  // Free-form Prompt
  freePrompt?: string;       // User's description of what they want
  
  // Context Materials
  contextClassTestIds?: string[];   // Previously uploaded tests
  contextDocumentIds?: string[];    // Study documents
  contextText?: string;             // Pasted text (e.g. from Perplexity)
  
  // Task Type Distribution (optional, AI decides if not specified)
  taskTypeDistribution?: Partial<Record<string, number>>;
  
  // Diagram Settings
  includeDiagrams: boolean;
  diagramTypes?: ('bar' | 'pie' | 'line' | 'scatter')[];
}

export interface GeneratedTask {
  id: string;
  type: string;  // TaskType
  taskNumber: number;
  questionText: string;
  questionImage?: string;          // Base64 or URL for diagrams
  
  // Type-specific fields
  options?: Array<{
    id: string;
    text: string;
    isCorrect: boolean;
  }>;
  correctAnswer?: string;
  modelAnswer?: string;            // For open questions
  calculationData?: {
    formula: string;
    variables: Record<string, number>;
    expectedResult: number;
    tolerance?: number;
  };
  diagramSpec?: {
    type: 'bar' | 'pie' | 'line' | 'scatter';
    title: string;
    data: Array<{ label: string; value: number; color?: string }>;
    xLabel?: string;
    yLabel?: string;
  };
  matchingPairs?: Array<{
    left: string;
    right: string;
  }>;
  blanks?: Array<{
    id: string;
    correctText: string;
    position: number;
  }>;
  
  // Grading
  points: number;
  difficulty: number;
  timeEstimateMinutes: number;
  gradingRubric: {
    maxPoints: number;
    criteria: Array<{
      name: string;
      description: string;
      maxPoints: number;
    }>;
    autoGradable: boolean;
    partialCreditAllowed: boolean;
    keywords?: string[];           // For auto-grading open questions
  };
  
  // Meta
  generatedBy: string;
  confidence: number;
  sourceContext?: string;          // Which context material was used
}

export interface ExamGenerationResult {
  generationId: string;
  status: 'preview' | 'confirmed' | 'failed';
  mockExam: {
    id: string;
    title: string;
    description: string;
    subjectId: string;
    themaIds: string[];
    tasks: GeneratedTask[];
    totalPoints: number;
    estimatedDurationMinutes: number;
    difficultyLevel: number;
    teacherPatternUsed?: string;
    generatedAt: string;
  };
  pipeline: PipelineProgress;
  
  // For preview/editing
  taskPreviews?: Array<{
    taskId: string;
    preview: string;
    canEdit: boolean;
    canDelete: boolean;
    canRegenerate: boolean;
  }>;
  
  // Suggestions
  suggestedAdditions?: Array<{
    type: string;
    reason: string;
  }>;
}

// ============================================================================
// Grading Pipeline Types
// ============================================================================

export interface TaskGradingInput {
  taskId: string;
  taskType: string;
  questionText: string;
  userAnswer: string | string[] | Record<string, string>;
  correctAnswer?: string;
  modelAnswer?: string;
  gradingRubric: GeneratedTask['gradingRubric'];
  points: number;
}

export interface TaskGradingResult {
  taskId: string;
  earnedPoints: number;
  maxPoints: number;
  percentage: number;
  
  // Grading Details
  isCorrect: boolean;
  isPartiallyCorrect: boolean;
  autoGraded: boolean;
  confidence: number;             // 0-100
  
  // Feedback
  feedback: string;
  feedbackType: 'correct' | 'partial' | 'incorrect' | 'needs_review';
  detailedFeedback?: {
    strengths: string[];
    weaknesses: string[];
    suggestions: string[];
  };
  
  // For rubric-based grading
  criteriaScores?: Array<{
    criterionName: string;
    earnedPoints: number;
    maxPoints: number;
    comment: string;
  }>;
  
  // For review
  needsManualReview: boolean;
  reviewReason?: string;
  
  // Meta
  modelUsed: string;
  processingTimeMs: number;
}

export interface AttemptGradingResult {
  attemptId: string;
  mockExamId: string;
  
  // Scores
  totalEarnedPoints: number;
  totalMaxPoints: number;
  percentage: number;
  grade: number;                  // 1.0 - 6.0
  gradeText: string;              // "Sehr gut", "Gut", etc.
  
  // Task Results
  taskResults: TaskGradingResult[];
  
  // Breakdown by Type
  typeBreakdown: Record<string, {
    earnedPoints: number;
    maxPoints: number;
    percentage: number;
    taskCount: number;
  }>;
  
  // Overall Analysis
  overallFeedback: string;
  strengths: string[];
  areasForImprovement: string[];
  studyRecommendations: string[];
  
  // Confidence & Review
  overallConfidence: number;
  tasksNeedingReview: string[];   // Task IDs
  
  // Timing
  attemptDurationSeconds: number;
  gradingDurationMs: number;
  
  // Pipeline Info
  pipeline: PipelineProgress;
}

// ============================================================================
// Model Configuration
// ============================================================================

export interface ModelConfig {
  id: string;
  name: string;
  provider: 'ollama' | 'anthropic' | 'openai' | 'local';
  modelName: string;
  endpoint?: string;
  capabilities: ModelPhase[];
  maxTokens: number;
  temperature: number;
  costPer1kTokens?: number;
  priority: number;              // Lower = preferred
  fallbackModelId?: string;
}

export interface PipelineConfig {
  uploadPipeline: {
    ocrModel: string;
    classifierModel: string;
    minConfidenceThreshold: number;
    requireReviewBelowConfidence: number;
  };
  examGenerationPipeline: {
    generatorModel: string;
    maxRetries: number;
    defaultTaskCount: number;
    defaultDifficulty: number;
  };
  gradingPipeline: {
    graderModel: string;
    minConfidenceThreshold: number;
    requireReviewBelowConfidence: number;
    allowPartialCredit: boolean;
  };
}

// ============================================================================
// Helper Types for UI
// ============================================================================

export interface PipelineUIState {
  isRunning: boolean;
  currentStep: number;
  totalSteps: number;
  currentPhaseLabel: string;
  progress: number;              // 0-100
  estimatedRemainingSeconds?: number;
  canCancel: boolean;
}

export function getPipelineUIState(pipeline: PipelineProgress): PipelineUIState {
  const completedSteps = pipeline.steps.filter(s => s.status === 'completed').length;
  const totalSteps = pipeline.steps.length;
  const currentStep = pipeline.steps.find(s => s.status === 'running');
  
  return {
    isRunning: pipeline.status === 'running',
    currentStep: completedSteps + 1,
    totalSteps,
    currentPhaseLabel: currentStep?.label || '',
    progress: Math.round((completedSteps / totalSteps) * 100),
    canCancel: pipeline.status === 'running',
  };
}

export function getPhaseLabel(phase: ModelPhase): string {
  const labels: Record<ModelPhase, string> = {
    vision_ocr: 'Vision-Modell (OCR)',
    nlp_classifier: 'NLP-Klassifikation',
    exam_generator: 'Klausur-Generator',
    grader: 'Bewertungs-KI',
    aggregator: 'Ergebnisse zusammenführen',
  };
  return labels[phase];
}

export function getConfidenceLevel(confidence: number): {
  level: 'high' | 'medium' | 'low';
  color: string;
  label: string;
} {
  if (confidence >= 85) {
    return { level: 'high', color: 'text-green-400', label: 'Hohe Sicherheit' };
  } else if (confidence >= 60) {
    return { level: 'medium', color: 'text-yellow-400', label: 'Mittlere Sicherheit' };
  } else {
    return { level: 'low', color: 'text-red-400', label: 'Niedrige Sicherheit' };
  }
}

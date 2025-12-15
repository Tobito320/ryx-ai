/**
 * Exam System Types for RyxHub
 * 
 * German Berufsschule (vocational school) exam preparation system
 * Aligned with SIHK Hagen / Cuno Berufskolleg / IHK standards
 */

// ============================================================================
// Core Entity Types
// ============================================================================

export interface School {
  id: string;
  name: string; // e.g., "Cuno Berufskolleg Hagen"
  location: string;
  subjects: Subject[];
  createdAt: string;
  updatedAt: string;
}

export interface Subject {
  id: string;
  schoolId: string;
  name: string; // e.g., "WBL", "Betriebswirtschaft", "Deutsch"
  fullName?: string; // e.g., "Wirtschaft und Betriebslehre"
  teachers: Teacher[];
  themas: Thema[];
  studyContent?: StudyContent; // Cached AI-generated content
  examPatterns?: ExamPattern[]; // Learned patterns per teacher
  createdAt: string;
  updatedAt: string;
}

export interface Teacher {
  id: string;
  name: string; // e.g., "Herr Hakim"
  subjectIds: string[];
  examPatternProfile?: TeacherPattern;
  testsCount: number; // Number of uploaded tests
  createdAt: string;
  updatedAt: string;
}

export interface TeacherPattern {
  teacherId: string;
  subjectId: string;
  questionTypeDistribution: {
    multipleChoice: number; // Percentage 0-100
    shortAnswer: number;
    caseStudy: number;
    diagramAnalysis: number;
    calculation: number;
    fillInBlank: number;
    matching: number;
  };
  avgDifficulty: number; // 1-5 scale
  avgPointsPerTest: number;
  avgDurationMinutes: number;
  pointDistribution: {
    knowledgeSection: number; // Percentage
    applicationSection: number;
  };
  gradingRubricInference: {
    caseStudy?: string;
    shortAnswer?: string;
    diagramAnalysis?: string;
  };
  confidence: number; // 0-100
  testsAnalyzed: number;
  lastUpdated: string;
}

export interface Thema {
  id: string;
  subjectId: string;
  name: string; // e.g., "Marktforschung", "Preismanagement"
  parentThemaId?: string; // For hierarchical structure
  subtopics: Thema[];
  extractedFromTests: string[]; // ClassTest IDs
  frequency: number; // Occurrence count in uploaded tests
  studyContent?: StudyContent;
  createdAt: string;
  updatedAt: string;
}

// ============================================================================
// Class Test Types (Uploaded Tests)
// ============================================================================

export interface ClassTest {
  id: string;
  subjectId: string;
  teacherId: string;
  uploadedAt: string;
  examDate?: string; // YYYY-MM-DD if extracted
  themaIds: string[];
  rawContent: string; // OCR'd text
  extractedImages?: string[]; // Base64 or URLs
  extractedTasks: ExtractedTask[];
  isDuplicate: boolean;
  duplicateOf?: string; // ClassTest ID if duplicate
  confidenceScore: number; // 0-100
  ocrConfidence: number;
  metadata: ClassTestMetadata;
  status: "processing" | "ready" | "error";
  errorMessage?: string;
}

export interface ClassTestMetadata {
  originalFileName: string;
  fileType: "pdf" | "image";
  fileSize: number;
  pageCount?: number;
  detectedTeacher?: string;
  detectedSubject?: string;
  detectedDate?: string;
  detectedThemas?: string[];
  totalPoints?: number;
  duration?: number; // Minutes
}

export interface ExtractedTask {
  id: string;
  classTestId: string;
  taskNumber: number;
  type: TaskType;
  questionText: string;
  questionImage?: string;
  options?: TaskOption[]; // For MC
  correctAnswer?: string;
  pointsValue?: number;
  difficulty?: number; // 1-5
  extractionConfidence: number;
}

// ============================================================================
// Mock Exam Types
// ============================================================================

export interface MockExam {
  id: string;
  subjectId: string;
  themaIds: string[];
  generatedAt: string;
  studyContentUsed?: string; // Snapshot reference
  teacherPatternUsed?: string; // Teacher ID
  tasks: Task[];
  totalPoints: number;
  estimatedDurationMinutes: number;
  difficultyLevel: number; // 1-5
  title: string;
  description?: string;
  status: "draft" | "ready" | "archived";
}

export type TaskType =
  | "MC_SingleChoice"
  | "MC_MultipleChoice"
  | "ShortAnswer"
  | "FillInBlank"
  | "Matching"
  | "CaseStudy"
  | "DiagramAnalysis"
  | "Calculation"
  | "Explanation"
  | "Justification";

export interface Task {
  id: string;
  mockExamId?: string;
  type: TaskType;
  taskNumber: number;
  questionText: string;
  questionImage?: string;
  questionImageAlt?: string; // Accessibility
  options?: TaskOption[]; // For MC
  matchingPairs?: MatchingPair[]; // For Matching
  fillInBlanks?: FillInBlank[]; // For FillInBlank
  diagramData?: DiagramData; // For DiagramAnalysis
  calculationData?: CalculationData; // For Calculation
  difficulty: number; // 1-5
  points: number;
  timeEstimateMinutes: number;
  correctAnswer: string | string[]; // For MC/FillInBlank
  modelAnswer?: string; // For open-ended
  gradingRubric: GradingRubric;
  rationale?: string; // Explanation for correct answer
  source: "uploaded_test" | "ai_generated" | "teacher_library";
  hints?: string[];
  relatedThemas?: string[];
}

export interface TaskOption {
  id: string;
  text: string;
  isCorrect: boolean;
}

export interface MatchingPair {
  id: string;
  left: string;
  right: string;
}

export interface FillInBlank {
  id: string;
  position: number; // Index in text
  correctAnswers: string[]; // Accept multiple correct variants
}

export interface DiagramData {
  type: "bar" | "pie" | "line" | "flow" | "organization" | "swot" | "porter" | "table";
  title: string;
  imageUrl?: string;
  imageBase64?: string;
  description: string; // Alt text / analysis context
  dataPoints?: DataPoint[];
  expectedAnalysis: string;
}

export interface DataPoint {
  label: string;
  value: number;
  unit?: string;
  color?: string;
}

export interface CalculationData {
  formula?: string;
  givenValues: { name: string; value: number; unit?: string }[];
  expectedAnswer: number;
  expectedUnit?: string;
  tolerancePercent?: number; // Accept answers within X%
  steps: CalculationStep[];
}

export interface CalculationStep {
  description: string;
  formula?: string;
  result?: number;
}

export interface GradingRubric {
  maxPoints: number;
  criteria: RubricCriterion[];
  autoGradable: boolean;
  partialCreditAllowed: boolean;
}

export interface RubricCriterion {
  name: string;
  description: string;
  maxPoints: number;
  keywords?: string[]; // For auto-grading detection
}

// ============================================================================
// Attempt Types (User's exam attempts)
// ============================================================================

export interface Attempt {
  id: string;
  mockExamId: string;
  userId: string;
  startedAt: string;
  finishedAt?: string;
  durationSeconds: number;
  taskResponses: TaskResponse[];
  totalScore: number;
  totalPoints: number;
  grade: number; // German 1-6 scale
  gradeText: GradeText;
  percentage: number;
  savedState?: string; // Serialized UI state for resume
  annotations?: string; // User notes
  overallFeedback?: string; // AI-generated
  sectionBreakdown: SectionBreakdown;
  flagsForReview: string[]; // Task IDs flagged for teacher review
  status: "in_progress" | "submitted" | "graded" | "reviewed";
}

export interface TaskResponse {
  taskId: string;
  userAnswer: string | string[]; // Text, MC selection(s), etc.
  userDrawing?: string; // Base64 for diagram tasks
  answeredAt: string;
  timeSpentSeconds: number;
  maxPoints: number;
  earnedPoints: number;
  autoGraded: boolean;
  confidence: number; // AI confidence 0-100
  feedback?: string;
  criteriaScores?: { criterionName: string; score: number; maxScore: number }[];
  isCorrect?: boolean; // For MC
  flaggedForReview: boolean;
}

export interface SectionBreakdown {
  knowledgeSection: { max: number; earned: number; percentage: number };
  applicationSection: { max: number; earned: number; percentage: number };
  byTaskType?: { [key in TaskType]?: { max: number; earned: number; percentage: number } };
}

export type GradeText =
  | "Sehr gut"      // 1.0-1.5 (90-100%)
  | "Gut"           // 2.0-2.5 (80-89%)
  | "Befriedigend"  // 3.0-3.5 (70-79%)
  | "Ausreichend"   // 4.0-4.5 (55-69%)
  | "Mangelhaft"    // 5.0-5.5 (40-54%)
  | "Ungenügend";   // 6.0 (<40%)

// ============================================================================
// Study Content Types
// ============================================================================

export interface StudyContent {
  id: string;
  subjectId: string;
  themaId?: string;
  title: string;
  content: string; // Markdown
  wordCount: number;
  generatedAt: string;
  generatedBy: "perplexity" | "ollama" | "claude";
  cacheExpiry: string;
  sections: StudySection[];
}

export interface StudySection {
  title: string;
  content: string;
  order: number;
}

// ============================================================================
// Exam Pattern Types (Learned patterns)
// ============================================================================

export interface ExamPattern {
  id: string;
  teacherId: string;
  subjectId: string;
  themaId?: string;
  questionTypeDistribution: { [key in TaskType]?: number };
  difficultyProgression: number[]; // Per task position
  pointAllocation: { [key: string]: number };
  timeAllocation: number; // Minutes per 100 points
  patterns: PatternInsight[];
  confidence: number;
  basedOnTests: string[]; // ClassTest IDs
  createdAt: string;
  updatedAt: string;
}

export interface PatternInsight {
  type: "question_type" | "difficulty" | "topic" | "structure" | "grading";
  description: string;
  confidence: number;
  examples?: string[];
}

// ============================================================================
// OCR & Upload Types
// ============================================================================

export interface UploadResult {
  success: boolean;
  sessionId?: string;  // V2: Session ID for review flow
  classTestId?: string;
  error?: string;
  ocrText?: string;
  confidenceScore?: number;
  extractedMetadata?: ClassTestMetadata;
  suggestedThemas?: string[];
  requiresVerification: boolean;
  verificationPrompts?: VerificationPrompt[];
}

export interface VerificationPrompt {
  field: string;
  detected: string;
  confidence: number;
  suggestions?: string[];
  required: boolean;
}

export interface OCRResult {
  text: string;
  confidence: number;
  language: string;
  pages: OCRPage[];
}

export interface OCRPage {
  pageNumber: number;
  text: string;
  confidence: number;
  regions: OCRRegion[];
}

export interface OCRRegion {
  type: "text" | "handwriting" | "table" | "diagram" | "formula";
  bounds: { x: number; y: number; width: number; height: number };
  content: string;
  confidence: number;
}

// ============================================================================
// Auto-Grading Types
// ============================================================================

export interface GradingResult {
  attemptId: string;
  totalScore: number;
  totalPoints: number;
  grade: number;
  gradeText: GradeText;
  percentage: number;
  taskGrades: TaskGrade[];
  sectionBreakdown: SectionBreakdown;
  overallFeedback: string;
  strengths: string[];
  areasForImprovement: string[];
  flaggedTasks: string[];
  processingTimeMs: number;
  // V2 fields
  graderModel?: string;
  graderConfidence?: number;
  manualReviewFlagged?: boolean;
}

export interface TaskGrade {
  taskId: string;
  earnedPoints: number;
  maxPoints: number;
  autoGraded: boolean;
  confidence: number;
  feedback: string;
  isCorrect?: boolean;
  criteriaBreakdown?: { name: string; score: number; max: number; feedback: string }[];
  suggestedReview: boolean;
  reviewReason?: string;
  // V2 fields
  improvementSuggestion?: string;
  rubricBreakdown?: Array<{
    criterion: string;
    earned: number;
    max: number;
    comment: string;
  }>;
}

// ============================================================================
// Filter & Search Types
// ============================================================================

export interface ExamFilter {
  subjectIds?: string[];
  teacherIds?: string[];
  themaIds?: string[];
  difficultyRange?: [number, number];
  dateRange?: [string, string];
  status?: string[];
}

export interface AttemptFilter {
  mockExamIds?: string[];
  dateRange?: [string, string];
  gradeRange?: [number, number];
  status?: Attempt["status"][];
}

// ============================================================================
// Statistics Types
// ============================================================================

export interface ExamStatistics {
  totalMockExams: number;
  totalAttempts: number;
  averageGrade: number;
  averagePercentage: number;
  totalStudyTimeMinutes: number;
  bySubject: { [subjectId: string]: SubjectStats };
  byThema: { [themaId: string]: ThemaStats };
  progressOverTime: ProgressPoint[];
  strengthsAndWeaknesses: {
    strengths: { area: string; score: number }[];
    weaknesses: { area: string; score: number }[];
  };
}

export interface SubjectStats {
  subjectId: string;
  name: string;
  attempts: number;
  averageGrade: number;
  bestGrade: number;
  lastAttempt: string;
}

export interface ThemaStats {
  themaId: string;
  name: string;
  attempts: number;
  averagePercentage: number;
  improvement: number; // % change over time
}

export interface ProgressPoint {
  date: string;
  grade: number;
  percentage: number;
  subjectId?: string;
  themaId?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

export function calculateGrade(percentage: number): { grade: number; text: GradeText } {
  if (percentage >= 90) return { grade: 1.0, text: "Sehr gut" };
  if (percentage >= 85) return { grade: 1.5, text: "Sehr gut" };
  if (percentage >= 80) return { grade: 2.0, text: "Gut" };
  if (percentage >= 75) return { grade: 2.5, text: "Gut" };
  if (percentage >= 70) return { grade: 3.0, text: "Befriedigend" };
  if (percentage >= 65) return { grade: 3.5, text: "Befriedigend" };
  if (percentage >= 60) return { grade: 4.0, text: "Ausreichend" };
  if (percentage >= 55) return { grade: 4.5, text: "Ausreichend" };
  if (percentage >= 50) return { grade: 5.0, text: "Mangelhaft" };
  if (percentage >= 40) return { grade: 5.5, text: "Mangelhaft" };
  return { grade: 6.0, text: "Ungenügend" };
}

export function getTaskTypeLabel(type: TaskType): string {
  const labels: Record<TaskType, string> = {
    MC_SingleChoice: "Multiple Choice (Einfach)",
    MC_MultipleChoice: "Multiple Choice (Mehrfach)",
    ShortAnswer: "Kurzbeantwortung",
    FillInBlank: "Lückentext",
    Matching: "Zuordnung",
    CaseStudy: "Fallstudie",
    DiagramAnalysis: "Diagrammanalyse",
    Calculation: "Berechnung",
    Explanation: "Erläuterung",
    Justification: "Begründung",
  };
  return labels[type] || type;
}

export function getDifficultyLabel(difficulty: number): string {
  const labels = ["", "Leicht", "Einfach", "Mittel", "Schwer", "Sehr schwer"];
  return labels[Math.min(Math.max(Math.round(difficulty), 1), 5)];
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours} Std. ${mins} Min.` : `${hours} Std.`;
}

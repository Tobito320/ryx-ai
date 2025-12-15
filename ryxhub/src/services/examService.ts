/**
 * RyxHub Exam Service
 * 
 * API client for the German Berufsschule exam preparation system.
 * Communicates with the FastAPI backend at /api/exam/*
 */

import type {
  School,
  Subject,
  Teacher,
  Thema,
  MockExam,
  Attempt,
  ClassTest,
  Task,
  TaskResponse,
} from '../types/exam';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8420';

// ============================================================================
// SSE Job Helpers (V2)
// ============================================================================

export interface JobStartResponse {
  job_id: string;
}

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type JobType = 'generate_exam' | 'grade_attempt';

export interface JobResultResponse {
  job_id: string;
  status: JobStatus;
  job_type: JobType;
  result?: Record<string, any>;
  error?: string;
  created_at: string;
  finished_at?: string;
}

export interface JobEventPayload {
  type: 'start' | 'progress' | 'error' | 'done';
  status?: JobStatus;
  job_type?: JobType;
  phase?: string;
  percent?: number;
  message?: string;
  task_id?: string;
  error?: boolean;
}

export function getJobEventsUrl(jobId: string): string {
  return `${API_BASE}/api/exam/v2/jobs/${encodeURIComponent(jobId)}/events`;
}

// ============================================================================
// Types for API Responses
// ============================================================================

interface OCRResult {
  success: boolean;
  class_test_id?: string;
  confidence_score?: number;
  extracted_text?: string;
  detected_metadata?: {
    teacher?: string;
    subject?: string;
    date?: string;
  };
  suggested_themas?: string[];
  requires_verification: boolean;
  verification_prompts?: Array<{
    field: string;
    detected: string;
    confidence: number;
    suggestions?: string[];
    required: boolean;
  }>;
  error?: string;
}

interface GradingResult {
  attempt_id: string;
  total_score: number;
  total_points: number;
  grade: number;
  grade_text: string;
  percentage: number;
  task_grades: Array<{
    task_id: string;
    earned_points: number;
    max_points: number;
    auto_graded: boolean;
    confidence: number;
    feedback: string;
    is_correct: boolean;
  }>;
  overall_feedback: string;
  strengths: string[];
  areas_for_improvement: string[];
}

interface TeacherPattern {
  teacher_id: string;
  pattern_available: boolean;
  tests_needed?: number;
  message?: string;
  pattern?: {
    question_type_distribution: Record<string, number>;
    avg_difficulty: number;
    avg_points_per_test: number;
    avg_duration_minutes: number;
    point_distribution: Record<string, number>;
    grading_rubric_inference: Record<string, string>;
    confidence: number;
    tests_analyzed: number;
  };
}

interface Statistics {
  total_attempts: number;
  average_grade: number;
  average_percentage: number;
  best_grade: number;
  total_study_time_minutes: number;
  progress_over_time?: Array<{
    date: string;
    grade: number;
    percentage: number;
  }>;
}

// ============================================================================
// API Helper
// ============================================================================

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// School & Subject APIs
// ============================================================================

export async function getSchools(): Promise<School[]> {
  const data = await apiRequest<{ schools: School[] }>('/api/exam/schools');
  return data.schools;
}

export async function getSchool(schoolId: string): Promise<School> {
  return apiRequest<School>(`/api/exam/schools/${schoolId}`);
}

export async function getSubjects(schoolId?: string): Promise<Subject[]> {
  const params = schoolId ? `?school_id=${schoolId}` : '';
  const data = await apiRequest<{ subjects: Subject[] }>(`/api/exam/subjects${params}`);
  return data.subjects;
}

export async function getSubject(subjectId: string): Promise<Subject> {
  return apiRequest<Subject>(`/api/exam/subjects/${subjectId}`);
}

// ============================================================================
// Thema APIs
// ============================================================================

export async function getThemas(subjectId?: string): Promise<Thema[]> {
  const params = subjectId ? `?subject_id=${subjectId}` : '';
  const data = await apiRequest<{ themas: Thema[] }>(`/api/exam/themas${params}`);
  return data.themas;
}

// ============================================================================
// Teacher APIs
// ============================================================================

export async function getTeachers(subjectId?: string): Promise<Teacher[]> {
  const params = subjectId ? `?subject_id=${subjectId}` : '';
  const data = await apiRequest<{ teachers: Teacher[] }>(`/api/exam/teachers${params}`);
  return data.teachers;
}

export async function createTeacher(name: string, subjectIds: string[]): Promise<Teacher> {
  const params = new URLSearchParams({
    name,
    subject_ids: subjectIds.join(','),
  });
  return apiRequest<Teacher>(`/api/exam/teachers?${params}`, {
    method: 'POST',
  });
}

export async function getTeacherPattern(teacherId: string): Promise<TeacherPattern> {
  return apiRequest<TeacherPattern>(`/api/exam/teachers/${teacherId}/pattern`);
}

export async function learnTeacherPattern(teacherId: string): Promise<TeacherPattern> {
  return apiRequest<TeacherPattern>(`/api/exam/teachers/${teacherId}/learn-pattern`, {
    method: 'POST',
  });
}

// ============================================================================
// Test Upload & OCR APIs
// ============================================================================

export async function uploadTest(
  file: File,
  subjectId?: string
): Promise<OCRResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (subjectId) {
    formData.append('subject_id', subjectId);
  }

  const url = `${API_BASE}/api/exam/upload-test`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export async function verifyTest(
  classTestId: string,
  corrections: Record<string, string>
): Promise<{ success: boolean; class_test_id: string }> {
  return apiRequest(`/api/exam/verify-test/${classTestId}`, {
    method: 'POST',
    body: JSON.stringify(corrections),
  });
}

// ============================================================================
// Mock Exam APIs
// ============================================================================

export interface CreateMockExamRequest {
  subject_id: string;
  thema_ids: string[];
  teacher_id?: string;
  difficulty_level?: number;
  task_count?: number;
  duration_minutes?: number;
}

export async function generateMockExam(request: CreateMockExamRequest): Promise<MockExam> {
  return apiRequest<MockExam>('/api/exam/generate-exam', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getMockExams(subjectId?: string, themaId?: string): Promise<MockExam[]> {
  const params = new URLSearchParams();
  if (subjectId) params.append('subject_id', subjectId);
  if (themaId) params.append('thema_id', themaId);
  const query = params.toString() ? `?${params}` : '';
  
  const data = await apiRequest<{ mock_exams: MockExam[] }>(`/api/exam/mock-exams${query}`);
  return data.mock_exams;
}

export async function getMockExam(examId: string): Promise<MockExam> {
  return apiRequest<MockExam>(`/api/exam/mock-exams/${examId}`);
}

// ============================================================================
// Attempt & Grading APIs
// ============================================================================

export async function startAttempt(examId: string): Promise<Attempt> {
  return apiRequest<Attempt>(`/api/exam/start-attempt/${examId}`, {
    method: 'POST',
  });
}

export async function submitAnswer(
  attemptId: string,
  taskId: string,
  userAnswer: string | string[] | Record<string, string>
): Promise<{ success: boolean }> {
  return apiRequest(`/api/exam/attempts/${attemptId}/submit-answer`, {
    method: 'POST',
    body: JSON.stringify({
      task_id: taskId,
      user_answer: userAnswer,
    }),
  });
}

export async function finishAttempt(attemptId: string): Promise<GradingResult> {
  return apiRequest<GradingResult>(`/api/exam/attempts/${attemptId}/finish`, {
    method: 'POST',
  });
}

export async function getAttempts(mockExamId?: string): Promise<Attempt[]> {
  const params = mockExamId ? `?mock_exam_id=${mockExamId}` : '';
  const data = await apiRequest<{ attempts: Attempt[] }>(`/api/exam/attempts${params}`);
  return data.attempts;
}

export async function getAttempt(attemptId: string): Promise<Attempt> {
  return apiRequest<Attempt>(`/api/exam/attempts/${attemptId}`);
}

// ============================================================================
// Statistics APIs
// ============================================================================

export async function getStatistics(subjectId?: string, themaId?: string): Promise<Statistics> {
  const params = new URLSearchParams();
  if (subjectId) params.append('subject_id', subjectId);
  if (themaId) params.append('thema_id', themaId);
  const query = params.toString() ? `?${params}` : '';
  
  return apiRequest<Statistics>(`/api/exam/statistics${query}`);
}

// ============================================================================
// V2 API Functions - Real AI Pipeline
// ============================================================================

/**
 * Upload test with AI classification (V2 Pipeline)
 */
export interface UploadV2Response {
  session_id: string;
  status: 'processing' | 'review_required' | 'success' | 'error';
  ocr_text?: string;
  classification?: {
    teacher?: string;
    subject: string;
    subject_name: string;
    exam_date?: string;
    main_thema: string;
    sub_themas: string[];
    reasoning?: string;
  };
  confidence_scores?: {
    teacher: number;
    subject: number;
    exam_date: number;
    main_thema: number;
    overall: number;
  };
  requires_review: boolean;
  class_test_id?: string;
  error?: string;
}

export async function uploadTestV2(
  file: File,
  subjectHint?: string
): Promise<UploadV2Response> {
  const formData = new FormData();
  formData.append('file', file);
  
  let url = `${API_BASE}/api/exam/v2/upload-test`;
  if (subjectHint && subjectHint !== 'auto') {
    url += `?subject_hint=${encodeURIComponent(subjectHint)}`;
  }
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Confirm upload with user corrections (V2)
 */
export interface UploadReviewRequest {
  teacher_id?: string;
  teacher_name?: string;
  subject_id: string;
  exam_date?: string;
  main_thema: string;
  sub_themas: string[];
}

export async function confirmUploadV2(
  sessionId: string,
  corrections: UploadReviewRequest
): Promise<{ status: string; class_test_id: string; message: string }> {
  return apiRequest(`/api/exam/v2/upload-session/${sessionId}/review`, {
    method: 'POST',
    body: JSON.stringify(corrections),
  });
}

/**
 * Generate mock exam with free prompt (V2)
 */
export interface GenerateExamV2Request {
  subject_id: string;
  thema_ids: string[];
  difficulty?: number;
  task_count?: number;
  duration_minutes?: number;
  teacher_id?: string;
  use_teacher_pattern?: boolean;
  free_prompt?: string;  // NEW: User's custom instructions
  context_texts?: string[];  // NEW: Pasted context
  include_diagrams?: boolean;
}

export interface GenerateExamV2Response {
  status: string;
  mock_exam_id: string;
  mock_exam: MockExam & {
    free_prompt_used?: string;
    generated_at: string;
  };
}

export async function generateMockExamV2(
  request: GenerateExamV2Request
): Promise<GenerateExamV2Response> {
  return apiRequest<GenerateExamV2Response>('/api/exam/v2/generate-exam', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function startGenerateMockExamJobV2(
  request: GenerateExamV2Request
): Promise<JobStartResponse> {
  return apiRequest<JobStartResponse>('/api/exam/v2/jobs/generate-exam', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Grade attempt with AI (V2)
 */
export interface GradeAttemptV2Request {
  attempt_id: string;
  task_responses: Array<{
    task_id: string;
    user_answer: string | string[] | Record<string, string>;
  }>;
}

export interface TaskGradeV2 {
  task_id: string;
  task_type: string;
  earned_points: number;
  max_points: number;
  rationale: string;
  confidence: number;
  rubric_breakdown?: Array<{
    criterion: string;
    earned: number;
    max: number;
    comment: string;
  }>;
  improvement_suggestion?: string;
}

export interface GradingResultV2 {
  attempt_id: string;
  mock_exam_id: string;
  total_score: number;
  total_points: number;
  percentage: number;
  grade: number;
  grade_text: string;
  task_grades: TaskGradeV2[];
  overall_feedback: string;
  grader_model: string;
  grader_confidence: number;
  manual_review_flagged: boolean;
  tasks_needing_review: string[];
  created_at: string;
}

export async function gradeAttemptV2(
  request: GradeAttemptV2Request
): Promise<GradingResultV2> {
  return apiRequest<GradingResultV2>('/api/exam/v2/grade-attempt', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function startGradeAttemptJobV2(
  request: GradeAttemptV2Request
): Promise<JobStartResponse> {
  return apiRequest<JobStartResponse>('/api/exam/v2/jobs/grade-attempt', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getJobResultV2(jobId: string): Promise<JobResultResponse> {
  return apiRequest<JobResultResponse>(`/api/exam/v2/jobs/${encodeURIComponent(jobId)}/result`);
}

// ============================================================================
// Manual Review Queue (V2)
// ============================================================================

export interface ManualReviewQueueItemV2 {
  attempt_id: string;
  mock_exam_id: string;
  grading_result: Record<string, any>;
  mock_exam: Record<string, any>;
  task_responses: Array<{ task_id: string; user_answer: any }>;
}

export interface ManualReviewOverrideRequestV2 {
  attempt_id: string;
  task_id: string;
  earned_points: number;
  rationale?: string;
  confidence?: number;
}

export async function getManualReviewQueueV2(): Promise<ManualReviewQueueItemV2[]> {
  return apiRequest<ManualReviewQueueItemV2[]>('/api/exam/v2/manual-review/queue');
}

export async function overrideManualReviewV2(
  request: ManualReviewOverrideRequestV2
): Promise<GradingResultV2> {
  return apiRequest<GradingResultV2>('/api/exam/v2/manual-review/override', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Attempt results payload (V2)
 */
export interface AttemptResultTaskResponse {
  task_id: string;
  user_answer: string | string[] | Record<string, any>;
}

export interface AttemptResultsV2Response {
  attempt: Record<string, any>;
  grading_result: GradingResultV2;
  mock_exam: Record<string, any>;
  task_responses: AttemptResultTaskResponse[];
}

export async function getAttemptResultsV2(attemptId: string): Promise<AttemptResultsV2Response> {
  return apiRequest<AttemptResultsV2Response>(`/api/exam/v2/attempts/${attemptId}/results`);
}

/**
 * Start attempt (V2)
 */
export async function startAttemptV2(examId: string): Promise<Attempt> {
  return apiRequest<Attempt>(`/api/exam/v2/attempts/start/${examId}`, {
    method: 'POST',
  });
}

/**
 * Get V2 API health
 */
export async function getV2Health(): Promise<{ status: string; ollama_available: boolean; version: string }> {
  return apiRequest('/api/exam/v2/health');
}

/**
 * Get subjects (V2)
 */
export async function getSubjectsV2(): Promise<{ subjects: Array<{ id: string; name: string; full_name: string }> }> {
  return apiRequest('/api/exam/v2/subjects');
}

/**
 * Get themas (V2)
 */
export async function getThemasV2(subjectId?: string): Promise<{ themas: Array<{ id: string; subject_id: string; name: string }> }> {
  const params = subjectId ? `?subject_id=${subjectId}` : '';
  return apiRequest(`/api/exam/v2/themas${params}`);
}

// ============================================================================
// Export Types
// ============================================================================

export type { 
  OCRResult, 
  GradingResult, 
  TeacherPattern, 
  Statistics,
};

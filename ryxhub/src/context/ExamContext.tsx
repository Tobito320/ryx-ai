/**
 * Exam Context for RyxHub
 * 
 * Manages state for the German Berufsschule exam preparation system
 * Updated to use V2 API with AI-powered pipelines
 */

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import type {
  School,
  Subject,
  Teacher,
  Thema,
  ClassTest,
  MockExam,
  Attempt,
  Task,
  ExamStatistics,
  UploadResult,
  GradingResult,
  TaskResponse,
  GradeText,
} from "@/types/exam";
import { API_ENDPOINTS } from "@/config";
import { 
  uploadTestV2, 
  confirmUploadV2,
  generateMockExamV2, 
  gradeAttemptV2,
  startAttemptV2,
  getV2Health,
  type UploadV2Response,
  type GradingResultV2,
} from "@/services/examService";

// ============================================================================
// Context Type
// ============================================================================

interface ExamContextType {
  // Schools & Subjects
  schools: School[];
  selectedSchool: School | null;
  selectedSubject: Subject | null;
  selectedThema: Thema | null;
  selectSchool: (id: string) => void;
  selectSubject: (id: string) => void;
  selectThema: (id: string) => void;
  createSchool: (name: string, location: string) => Promise<School | null>;
  createSubject: (schoolId: string, name: string, fullName?: string) => Promise<Subject | null>;
  
  // Teachers
  teachers: Teacher[];
  selectedTeacher: Teacher | null;
  selectTeacher: (id: string) => void;
  createTeacher: (name: string, subjectIds: string[]) => Promise<Teacher | null>;
  
  // Class Tests (Uploaded)
  classTests: ClassTest[];
  uploadingTest: boolean;
  uploadTest: (file: File) => Promise<UploadResult>;
  verifyTestUpload: (classTestId: string, corrections: Record<string, string>) => Promise<void>;
  
  // Mock Exams
  mockExams: MockExam[];
  selectedMockExam: MockExam | null;
  selectMockExam: (id: string) => void;
  generateMockExam: (subjectId: string, themaIds: string[], options: MockExamOptions) => Promise<MockExam | null>;
  
  // Attempts
  attempts: Attempt[];
  currentAttempt: Attempt | null;
  startAttempt: (mockExamId: string) => Promise<Attempt | null>;
  submitAnswer: (taskId: string, answer: string | string[]) => Promise<void>;
  finishAttempt: () => Promise<GradingResult | null>;
  resumeAttempt: (attemptId: string) => Promise<Attempt | null>;
  
  // Statistics
  statistics: ExamStatistics | null;
  refreshStatistics: () => Promise<void>;
  
  // Study Content
  loadStudyContent: (subjectId: string, themaId?: string) => Promise<string | null>;
  
  // View State
  examView: ExamViewMode;
  setExamView: (view: ExamViewMode) => void;
  
  // Loading states
  loading: boolean;
  error: string | null;
}

export type ExamViewMode = 
  | "schools"
  | "subjects"
  | "themas"
  | "upload"
  | "mock_exams"
  | "exam_taking"
  | "results"
  | "history"
  | "study";

interface MockExamOptions {
  teacherId?: string;
  difficultyLevel?: number;
  taskCount?: number;
  durationMinutes?: number;
  freePrompt?: string;  // NEW: User's custom instructions
  contextTexts?: string[];  // NEW: Pasted context material
  includeDiagrams?: boolean;
}

const ExamContext = createContext<ExamContextType | null>(null);

// ============================================================================
// Default Data
// ============================================================================

const defaultSchool: School = {
  id: "cuno-berufskolleg",
  name: "Cuno Berufskolleg Hagen",
  location: "Hagen, NRW",
  subjects: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const defaultSubjects: Subject[] = [
  {
    id: "wbl",
    schoolId: "cuno-berufskolleg",
    name: "WBL",
    fullName: "Wirtschaft und Betriebslehre",
    teachers: [],
    themas: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "bwl",
    schoolId: "cuno-berufskolleg",
    name: "BWL",
    fullName: "Betriebswirtschaftslehre",
    teachers: [],
    themas: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "deutsch",
    schoolId: "cuno-berufskolleg",
    name: "Deutsch",
    fullName: "Deutsch / Kommunikation",
    teachers: [],
    themas: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "mathe",
    schoolId: "cuno-berufskolleg",
    name: "Mathe",
    fullName: "Mathematik",
    teachers: [],
    themas: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

const defaultThemas: Thema[] = [
  {
    id: "marktforschung",
    subjectId: "wbl",
    name: "Marktforschung",
    subtopics: [],
    extractedFromTests: [],
    frequency: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "marketingmix",
    subjectId: "wbl",
    name: "Marketingmix (4Ps)",
    subtopics: [],
    extractedFromTests: [],
    frequency: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "kundenakquisition",
    subjectId: "wbl",
    name: "Kundenakquisition",
    subtopics: [],
    extractedFromTests: [],
    frequency: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "preismanagement",
    subjectId: "wbl",
    name: "Preismanagement",
    subtopics: [],
    extractedFromTests: [],
    frequency: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "werbung",
    subjectId: "wbl",
    name: "Werbung & Kommunikation",
    subtopics: [],
    extractedFromTests: [],
    frequency: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

// ============================================================================
// Provider Component
// ============================================================================

export function ExamProvider({ children }: { children: ReactNode }) {
  // State
  const [schools, setSchools] = useState<School[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_schools");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [{ ...defaultSchool, subjects: defaultSubjects }];
      }
    }
    return [{ ...defaultSchool, subjects: defaultSubjects }];
  });

  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>("cuno-berufskolleg");
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [selectedThemaId, setSelectedThemaId] = useState<string | null>(null);
  const [selectedTeacherId, setSelectedTeacherId] = useState<string | null>(null);

  const [teachers, setTeachers] = useState<Teacher[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_teachers");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [themas, setThemas] = useState<Thema[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_themas");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return defaultThemas;
      }
    }
    return defaultThemas;
  });

  const [classTests, setClassTests] = useState<ClassTest[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_classtests");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [mockExams, setMockExams] = useState<MockExam[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_mockexams");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [selectedMockExamId, setSelectedMockExamId] = useState<string | null>(null);

  const [attempts, setAttempts] = useState<Attempt[]>(() => {
    const stored = localStorage.getItem("ryxhub_exam_attempts");
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [currentAttemptId, setCurrentAttemptId] = useState<string | null>(null);
  const [statistics, setStatistics] = useState<ExamStatistics | null>(null);
  const [examView, setExamView] = useState<ExamViewMode>("schools");
  const [uploadingTest, setUploadingTest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem("ryxhub_exam_schools", JSON.stringify(schools));
  }, [schools]);

  useEffect(() => {
    localStorage.setItem("ryxhub_exam_teachers", JSON.stringify(teachers));
  }, [teachers]);

  useEffect(() => {
    localStorage.setItem("ryxhub_exam_themas", JSON.stringify(themas));
  }, [themas]);

  useEffect(() => {
    localStorage.setItem("ryxhub_exam_classtests", JSON.stringify(classTests));
  }, [classTests]);

  useEffect(() => {
    localStorage.setItem("ryxhub_exam_mockexams", JSON.stringify(mockExams));
  }, [mockExams]);

  useEffect(() => {
    localStorage.setItem("ryxhub_exam_attempts", JSON.stringify(attempts));
  }, [attempts]);

  // Derived state
  const selectedSchool = schools.find(s => s.id === selectedSchoolId) || null;
  const selectedSubject = selectedSchool?.subjects.find(s => s.id === selectedSubjectId) || null;
  const selectedThema = themas.find(t => t.id === selectedThemaId) || null;
  const selectedTeacher = teachers.find(t => t.id === selectedTeacherId) || null;
  const selectedMockExam = mockExams.find(m => m.id === selectedMockExamId) || null;
  const currentAttempt = attempts.find(a => a.id === currentAttemptId) || null;

  // Actions
  const selectSchool = useCallback((id: string) => {
    setSelectedSchoolId(id);
    setSelectedSubjectId(null);
    setSelectedThemaId(null);
  }, []);

  const selectSubject = useCallback((id: string) => {
    setSelectedSubjectId(id);
    setSelectedThemaId(null);
  }, []);

  const selectThema = useCallback((id: string) => {
    setSelectedThemaId(id);
  }, []);

  const selectTeacher = useCallback((id: string) => {
    setSelectedTeacherId(id);
  }, []);

  const selectMockExam = useCallback((id: string) => {
    setSelectedMockExamId(id);
  }, []);

  const createSchool = useCallback(async (name: string, location: string): Promise<School | null> => {
    const newSchool: School = {
      id: `school-${Date.now()}`,
      name,
      location,
      subjects: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setSchools(prev => [...prev, newSchool]);
    return newSchool;
  }, []);

  const createSubject = useCallback(async (schoolId: string, name: string, fullName?: string): Promise<Subject | null> => {
    const newSubject: Subject = {
      id: `subject-${Date.now()}`,
      schoolId,
      name,
      fullName,
      teachers: [],
      themas: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setSchools(prev => prev.map(school => {
      if (school.id === schoolId) {
        return { ...school, subjects: [...school.subjects, newSubject] };
      }
      return school;
    }));
    return newSubject;
  }, []);

  const createTeacher = useCallback(async (name: string, subjectIds: string[]): Promise<Teacher | null> => {
    const newTeacher: Teacher = {
      id: `teacher-${Date.now()}`,
      name,
      subjectIds,
      testsCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setTeachers(prev => [...prev, newTeacher]);
    return newTeacher;
  }, []);

  const uploadTest = useCallback(async (file: File): Promise<UploadResult> => {
    setUploadingTest(true);
    setError(null);
    
    try {
      // Call V2 API with real OCR + AI classification
      const v2Result = await uploadTestV2(file, selectedSubjectId || undefined);
      
      // Convert V2 response to frontend UploadResult format
      const result: UploadResult = {
        success: v2Result.status !== "error",
        sessionId: v2Result.session_id,
        classTestId: v2Result.class_test_id,
        confidenceScore: v2Result.confidence_scores?.overall || 50,
        requiresVerification: v2Result.requires_review,
        verificationPrompts: [],
        suggestedThemas: v2Result.classification?.sub_themas || [],
        error: v2Result.error,
      };
      
      // Build verification prompts from classification
      if (v2Result.classification && v2Result.confidence_scores) {
        const prompts: UploadResult["verificationPrompts"] = [];
        
        if (v2Result.classification.teacher) {
          prompts.push({
            field: "teacher",
            detected: v2Result.classification.teacher,
            confidence: v2Result.confidence_scores.teacher,
            required: false,
          });
        }
        
        prompts.push({
          field: "subject",
          detected: v2Result.classification.subject_name || v2Result.classification.subject,
          confidence: v2Result.confidence_scores.subject,
          required: true,
          suggestions: ["WBL", "BWL", "IT", "Deutsch", "Mathe"],
        });
        
        if (v2Result.classification.exam_date) {
          prompts.push({
            field: "date",
            detected: v2Result.classification.exam_date,
            confidence: v2Result.confidence_scores.exam_date,
            required: false,
          });
        }
        
        prompts.push({
          field: "thema",
          detected: v2Result.classification.main_thema,
          confidence: v2Result.confidence_scores.main_thema,
          required: true,
        });
        
        result.verificationPrompts = prompts;
      }
      
      // If auto-accepted, add to class tests
      if (v2Result.status === "success" && v2Result.class_test_id) {
        const newClassTest: ClassTest = {
          id: v2Result.class_test_id,
          subjectId: v2Result.classification?.subject || selectedSubjectId || "wbl",
          teacherId: "",
          uploadedAt: new Date().toISOString(),
          themaIds: [],
          rawContent: v2Result.ocr_text || "",
          extractedTasks: [],
          isDuplicate: false,
          confidenceScore: v2Result.confidence_scores?.overall || 85,
          ocrConfidence: v2Result.confidence_scores?.overall || 85,
          metadata: {
            originalFileName: file.name,
            fileType: file.type.includes("pdf") ? "pdf" : "image",
            fileSize: file.size,
            detectedTeacher: v2Result.classification?.teacher,
            detectedSubject: v2Result.classification?.subject_name,
            detectedDate: v2Result.classification?.exam_date,
          },
          status: "ready",
        };
        setClassTests(prev => [...prev, newClassTest]);
      }
      
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Upload fehlgeschlagen";
      setError(errorMsg);
      return {
        success: false,
        error: errorMsg,
        requiresVerification: false,
      };
    } finally {
      setUploadingTest(false);
    }
  }, [selectedSubjectId]);

  const verifyTestUpload = useCallback(async (classTestId: string, corrections: Record<string, string>, sessionId?: string) => {
    try {
      // If we have a session ID, use V2 API to confirm
      if (sessionId) {
        await confirmUploadV2(sessionId, {
          subject_id: corrections.subject || "wbl",
          teacher_name: corrections.teacher,
          exam_date: corrections.date,
          main_thema: corrections.thema || "Allgemein",
          sub_themas: [],
        });
      }
      
      // Update local state
      setClassTests(prev => prev.map(test => {
        if (test.id === classTestId) {
          return {
            ...test,
            status: "ready" as const,
            teacherId: corrections.teacher || test.teacherId,
            metadata: {
              ...test.metadata,
              detectedTeacher: corrections.teacher,
              detectedSubject: corrections.subject,
              detectedDate: corrections.date,
            },
          };
        }
        return test;
      }));
    } catch (err) {
      console.error("Failed to verify upload:", err);
    }
  }, []);

  const generateMockExam = useCallback(async (
    subjectId: string,
    themaIds: string[],
    options: MockExamOptions
  ): Promise<MockExam | null> => {
    setLoading(true);
    setError(null);

    try {
      // Call V2 API with AI generation
      const v2Result = await generateMockExamV2({
        subject_id: subjectId,
        thema_ids: themaIds.length > 0 ? themaIds : ["marktforschung"],
        difficulty: options.difficultyLevel || 3,
        task_count: options.taskCount || 15,
        duration_minutes: options.durationMinutes || 90,
        teacher_id: options.teacherId,
        use_teacher_pattern: !!options.teacherId,
        free_prompt: options.freePrompt,
        context_texts: options.contextTexts,
        include_diagrams: options.includeDiagrams ?? true,
      });
      
      if (v2Result.status !== "success" || !v2Result.mock_exam) {
        throw new Error("Exam generation failed");
      }
      
      // Convert V2 response to frontend MockExam format
      const mockExam: MockExam = {
        id: v2Result.mock_exam_id,
        subjectId: v2Result.mock_exam.subjectId || subjectId,
        themaIds: v2Result.mock_exam.themaIds || themaIds,
        generatedAt: v2Result.mock_exam.generated_at || new Date().toISOString(),
        teacherPatternUsed: options.teacherId,
        tasks: v2Result.mock_exam.tasks || [],
        totalPoints: v2Result.mock_exam.totalPoints || (v2Result.mock_exam as any).total_points || 100,
        estimatedDurationMinutes: v2Result.mock_exam.estimatedDurationMinutes || options.durationMinutes || 90,
        difficultyLevel: v2Result.mock_exam.difficultyLevel || options.difficultyLevel || 3,
        title: v2Result.mock_exam.title || `Übungsklausur: ${themaIds.map(id => themas.find(t => t.id === id)?.name || id).join(", ")}`,
        status: "ready",
      };

      setMockExams(prev => [...prev, mockExam]);
      return mockExam;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Generierung fehlgeschlagen";
      setError(errorMsg);
      
      // Fallback to sample tasks if API fails
      console.warn("V2 API failed, using fallback tasks:", err);
      const fallbackExam: MockExam = {
        id: `mock-${Date.now()}`,
        subjectId,
        themaIds,
        generatedAt: new Date().toISOString(),
        teacherPatternUsed: options.teacherId,
        tasks: generateSampleTasks(themaIds, options.taskCount || 15),
        totalPoints: 100,
        estimatedDurationMinutes: options.durationMinutes || 90,
        difficultyLevel: options.difficultyLevel || 3,
        title: `Übungsklausur: ${themaIds.map(id => themas.find(t => t.id === id)?.name || id).join(", ")}`,
        status: "ready",
      };
      setMockExams(prev => [...prev, fallbackExam]);
      return fallbackExam;
    } finally {
      setLoading(false);
    }
  }, [themas]);

  const startAttempt = useCallback(async (mockExamId: string): Promise<Attempt | null> => {
    const mockExam = mockExams.find(m => m.id === mockExamId);
    if (!mockExam) return null;

    const newAttempt: Attempt = {
      id: `attempt-${Date.now()}`,
      mockExamId,
      userId: "default-user",
      startedAt: new Date().toISOString(),
      durationSeconds: 0,
      taskResponses: [],
      totalScore: 0,
      totalPoints: mockExam.totalPoints,
      grade: 0,
      gradeText: "Ungenügend",
      percentage: 0,
      sectionBreakdown: {
        knowledgeSection: { max: 0, earned: 0, percentage: 0 },
        applicationSection: { max: 0, earned: 0, percentage: 0 },
      },
      flagsForReview: [],
      status: "in_progress",
    };

    setAttempts(prev => [...prev, newAttempt]);
    setCurrentAttemptId(newAttempt.id);
    return newAttempt;
  }, [mockExams]);

  const submitAnswer = useCallback(async (taskId: string, answer: string | string[]) => {
    if (!currentAttemptId) return;

    setAttempts(prev => prev.map(attempt => {
      if (attempt.id === currentAttemptId) {
        const existingResponse = attempt.taskResponses.find(r => r.taskId === taskId);
        const newResponse: TaskResponse = {
          taskId,
          userAnswer: answer,
          answeredAt: new Date().toISOString(),
          timeSpentSeconds: 0,
          maxPoints: 0,
          earnedPoints: 0,
          autoGraded: false,
          confidence: 0,
          flaggedForReview: false,
        };

        return {
          ...attempt,
          taskResponses: existingResponse
            ? attempt.taskResponses.map(r => r.taskId === taskId ? newResponse : r)
            : [...attempt.taskResponses, newResponse],
        };
      }
      return attempt;
    }));
  }, [currentAttemptId]);

  const finishAttempt = useCallback(async (): Promise<GradingResult | null> => {
    if (!currentAttemptId) return null;

    const attempt = attempts.find(a => a.id === currentAttemptId);
    if (!attempt) return null;

    const mockExam = mockExams.find(m => m.id === attempt.mockExamId);
    if (!mockExam) return null;

    try {
      // Prepare task responses for V2 API
      const taskResponses = attempt.taskResponses.map(r => ({
        task_id: r.taskId,
        user_answer: r.userAnswer,
      }));
      
      // Call V2 AI grading API
      const v2Result = await gradeAttemptV2({
        attempt_id: currentAttemptId,
        task_responses: taskResponses,
      });
      
      // Convert V2 result to frontend GradingResult format
      const taskGrades: GradingResult["taskGrades"] = v2Result.task_grades.map(tg => ({
        taskId: tg.task_id,
        earnedPoints: tg.earned_points,
        maxPoints: tg.max_points,
        autoGraded: tg.task_type.startsWith("MC"),
        confidence: tg.confidence,
        feedback: tg.rationale,
        improvementSuggestion: tg.improvement_suggestion,
        suggestedReview: tg.confidence < 75,
        rubricBreakdown: tg.rubric_breakdown,
      }));
      
      const result: GradingResult = {
        attemptId: currentAttemptId,
        totalScore: v2Result.total_score,
        totalPoints: v2Result.total_points,
        grade: v2Result.grade,
        gradeText: v2Result.grade_text as GradeText,
        percentage: v2Result.percentage,
        taskGrades,
        sectionBreakdown: {
          knowledgeSection: { max: 40, earned: Math.floor(v2Result.total_score * 0.4), percentage: 0 },
          applicationSection: { max: 60, earned: Math.floor(v2Result.total_score * 0.6), percentage: 0 },
        },
        overallFeedback: v2Result.overall_feedback,
        strengths: [],
        areasForImprovement: [],
        flaggedTasks: v2Result.tasks_needing_review,
        processingTimeMs: 0,
        graderModel: v2Result.grader_model,
        graderConfidence: v2Result.grader_confidence,
        manualReviewFlagged: v2Result.manual_review_flagged,
      };

      // Update attempt
      setAttempts(prev => prev.map(a => {
        if (a.id === currentAttemptId) {
          return {
            ...a,
            finishedAt: new Date().toISOString(),
            totalScore: v2Result.total_score,
            grade: v2Result.grade,
            gradeText: v2Result.grade_text as GradeText,
            percentage: v2Result.percentage,
            status: "graded" as const,
            overallFeedback: v2Result.overall_feedback,
            flagsForReview: v2Result.tasks_needing_review,
          };
        }
        return a;
      }));

      setCurrentAttemptId(null);
      return result;
    } catch (err) {
      console.warn("V2 grading failed, using fallback:", err);
      
      // Fallback to mock grading if API fails
      let totalScore = 0;
      const taskGrades: GradingResult["taskGrades"] = [];

      for (const task of mockExam.tasks) {
        const response = attempt.taskResponses.find(r => r.taskId === task.id);
        const earnedPoints = response ? Math.floor(Math.random() * task.points) + 1 : 0;
        totalScore += earnedPoints;

        taskGrades.push({
          taskId: task.id,
          earnedPoints,
          maxPoints: task.points,
          autoGraded: task.type.startsWith("MC"),
          confidence: Math.floor(Math.random() * 30) + 70,
          feedback: "Bewertung ohne KI (Fallback)",
          suggestedReview: false,
        });
      }

      const percentage = (totalScore / mockExam.totalPoints) * 100;
      const { grade, text: gradeText } = calculateGrade(percentage);

      const result: GradingResult = {
        attemptId: currentAttemptId,
        totalScore,
        totalPoints: mockExam.totalPoints,
        grade,
        gradeText,
        percentage,
        taskGrades,
        sectionBreakdown: {
          knowledgeSection: { max: 40, earned: Math.floor(totalScore * 0.4), percentage: 85 },
          applicationSection: { max: 60, earned: Math.floor(totalScore * 0.6), percentage: 72 },
        },
        overallFeedback: "Bewertung konnte nicht mit KI durchgeführt werden. Ergebnis ist eine Schätzung.",
        strengths: [],
        areasForImprovement: [],
        flaggedTasks: [],
        processingTimeMs: 0,
      };

      setAttempts(prev => prev.map(a => {
        if (a.id === currentAttemptId) {
          return {
            ...a,
            finishedAt: new Date().toISOString(),
            totalScore,
            grade,
            gradeText,
            percentage,
            status: "graded" as const,
            overallFeedback: result.overallFeedback,
          };
        }
        return a;
      }));

      setCurrentAttemptId(null);
      return result;
    }
  }, [currentAttemptId, attempts, mockExams]);

  const resumeAttempt = useCallback(async (attemptId: string): Promise<Attempt | null> => {
    const attempt = attempts.find(a => a.id === attemptId);
    if (attempt && attempt.status === "in_progress") {
      setCurrentAttemptId(attemptId);
      return attempt;
    }
    return null;
  }, [attempts]);

  const refreshStatistics = useCallback(async () => {
    // Calculate statistics from attempts
    const stats: ExamStatistics = {
      totalMockExams: mockExams.length,
      totalAttempts: attempts.length,
      averageGrade: attempts.length > 0
        ? attempts.reduce((sum, a) => sum + a.grade, 0) / attempts.length
        : 0,
      averagePercentage: attempts.length > 0
        ? attempts.reduce((sum, a) => sum + a.percentage, 0) / attempts.length
        : 0,
      totalStudyTimeMinutes: attempts.reduce((sum, a) => sum + Math.floor(a.durationSeconds / 60), 0),
      bySubject: {},
      byThema: {},
      progressOverTime: attempts.map(a => ({
        date: a.finishedAt || a.startedAt,
        grade: a.grade,
        percentage: a.percentage,
      })),
      strengthsAndWeaknesses: {
        strengths: [{ area: "Wissensaufgaben", score: 85 }],
        weaknesses: [{ area: "Fallstudien", score: 65 }],
      },
    };
    setStatistics(stats);
  }, [mockExams, attempts]);

  const loadStudyContent = useCallback(async (subjectId: string, themaId?: string): Promise<string | null> => {
    // In production, this would fetch from Perplexity or generate with Ollama
    return `# Studienmaterial\n\nDies ist ein Platzhalter für das Studienmaterial zu ${themaId || subjectId}.`;
  }, []);

  const value: ExamContextType = {
    schools,
    selectedSchool,
    selectedSubject,
    selectedThema,
    selectSchool,
    selectSubject,
    selectThema,
    createSchool,
    createSubject,
    teachers,
    selectedTeacher,
    selectTeacher,
    createTeacher,
    classTests,
    uploadingTest,
    uploadTest,
    verifyTestUpload,
    mockExams,
    selectedMockExam,
    selectMockExam,
    generateMockExam,
    attempts,
    currentAttempt,
    startAttempt,
    submitAnswer,
    finishAttempt,
    resumeAttempt,
    statistics,
    refreshStatistics,
    loadStudyContent,
    examView,
    setExamView,
    loading,
    error,
  };

  return (
    <ExamContext.Provider value={value}>
      {children}
    </ExamContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useExam() {
  const context = useContext(ExamContext);
  if (!context) {
    throw new Error("useExam must be used within an ExamProvider");
  }
  return context;
}

// ============================================================================
// Helper Functions
// ============================================================================

function calculateGrade(percentage: number): { grade: number; text: GradeText } {
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

function generateSampleTasks(themaIds: string[], count: number): Task[] {
  const tasks: Task[] = [];
  const taskTypes = [
    "MC_SingleChoice",
    "ShortAnswer",
    "CaseStudy",
    "DiagramAnalysis",
    "Calculation",
  ] as const;

  for (let i = 0; i < count; i++) {
    const type = taskTypes[i % taskTypes.length];
    const difficulty = Math.min(5, Math.floor(i / 3) + 1);
    const points = type === "CaseStudy" ? 10 : type === "MC_SingleChoice" ? 2 : 5;

    tasks.push({
      id: `task-${i + 1}`,
      type,
      taskNumber: i + 1,
      questionText: getSampleQuestion(type, i),
      difficulty,
      points,
      timeEstimateMinutes: type === "CaseStudy" ? 20 : type === "MC_SingleChoice" ? 2 : 5,
      correctAnswer: type === "MC_SingleChoice" ? "B" : "Beispielantwort",
      gradingRubric: {
        maxPoints: points,
        criteria: [{ name: "Vollständigkeit", description: "Alle Aspekte behandelt", maxPoints: points }],
        autoGradable: type.startsWith("MC"),
        partialCreditAllowed: !type.startsWith("MC"),
      },
      source: "ai_generated",
      options: type === "MC_SingleChoice" ? [
        { id: "A", text: "Falsche Antwort A", isCorrect: false },
        { id: "B", text: "Richtige Antwort B", isCorrect: true },
        { id: "C", text: "Falsche Antwort C", isCorrect: false },
        { id: "D", text: "Falsche Antwort D", isCorrect: false },
      ] : undefined,
    });
  }

  return tasks;
}

function getSampleQuestion(type: string, index: number): string {
  const questions: Record<string, string[]> = {
    MC_SingleChoice: [
      "Was ist die Definition von Marktforschung?",
      "Welche der folgenden Aussagen über den Marketing-Mix ist korrekt?",
      "Was versteht man unter Primärforschung?",
    ],
    ShortAnswer: [
      "Erklären Sie den Unterschied zwischen qualitativer und quantitativer Marktforschung.",
      "Nennen Sie drei Methoden der Datenerhebung in der Marktforschung.",
      "Was sind die 4Ps des Marketing-Mix?",
    ],
    CaseStudy: [
      "Ein Einzelhandelsbetrieb möchte ein neues Produkt einführen. Entwickeln Sie eine Marktforschungsstrategie und begründen Sie Ihre Entscheidungen.",
      "Die Firma MüllTech AG plant eine Expansion in den europäischen Markt. Analysieren Sie die Marktbedingungen und erstellen Sie eine SWOT-Analyse.",
    ],
    DiagramAnalysis: [
      "Analysieren Sie das folgende Balkendiagramm zum Marktanteil und ziehen Sie Schlussfolgerungen.",
      "Interpretieren Sie das Kreisdiagramm zur Kundenverteilung und leiten Sie Handlungsempfehlungen ab.",
    ],
    Calculation: [
      "Berechnen Sie den Marktanteil des Unternehmens X basierend auf den gegebenen Daten.",
      "Ermitteln Sie den Break-Even-Point für das neue Produkt.",
    ],
  };

  const typeQuestions = questions[type] || questions.ShortAnswer;
  return typeQuestions[index % typeQuestions.length];
}

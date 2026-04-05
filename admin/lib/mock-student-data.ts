// ─── Student Detail Mock Data ────────────────────────────────────────────────
// Rich student profiles mirroring the actual DB schema:
//   users + telegram_identities + student_course_state + question_attempts
//   + student_question_srs + question_reports + analytics_events

export type StudentProfile = {
  user_id: string;
  display_name: string;
  telegram_user_id: string;
  telegram_username: string;
  faculty_code: string;
  faculty_name: string;
  program_code: string;
  program_name: string;
  level_code: string;
  semester_code: string;
  preferred_course_code: string;
  onboarding_completed: boolean;
  created_at: string;
  last_active_at: string;
  current_streak: number;
  longest_streak: number;
  total_questions_answered: number;
  total_correct: number;
  total_quizzes_completed: number;
  reports_filed: number;
};

export type StudentCoursePerformance = {
  course_id: string;
  course_name: string;
  overall_skill: number;
  phase: "cold_start" | "warm" | "established";
  topic_skills: Record<string, number>;
  cognitive_profile: Record<string, number>;
  processing_profile: Record<string, number>;
  misconception_flags: { topic: string; description: string; severity: "low" | "medium" | "high" }[];
  total_quizzes_completed: number;
  total_attempts: number;
  total_correct: number;
  avg_time_per_question: number;
  exam_date: string | null;
};

export type SrsDistribution = {
  course_id: string;
  course_name: string;
  box_0: number;
  box_1: number;
  box_2: number;
  box_3: number;
  box_4: number;
  box_5: number;
};

export type WeeklyProgress = {
  week: string;
  attempts: number;
  correct: number;
  accuracy: number;
  avg_time: number;
};

export type DailyActivity = {
  date: string;
  questions_count: number;
};

export type RecentAttempt = {
  question_key: string;
  course_name: string;
  is_correct: boolean;
  time_taken_seconds: number;
  created_at: string;
};

// ─── Full Student Detail Data ────────────────────────────────────────────────

export type StudentDetailData = {
  profile: StudentProfile;
  courses: StudentCoursePerformance[];
  srs: SrsDistribution[];
  weekly_progress: WeeklyProgress[];
  daily_activity: DailyActivity[];
  recent_attempts: RecentAttempt[];
};

// ─── Helper to look up by user_id ────────────────────────────────────────────

export function getStudentDetail(userId: string): StudentDetailData | undefined {
  return MOCK_STUDENT_DETAILS[userId];
}

// ─── Student 1: bright_kofi (Top performer, established) ─────────────────────

const STUDENT_1: StudentDetailData = {
  profile: {
    user_id: "1001",
    display_name: "Bright Kofi Mensah",
    telegram_user_id: "9812345",
    telegram_username: "bright_kofi",
    faculty_code: "FOE",
    faculty_name: "Faculty of Engineering",
    program_code: "EEE",
    program_name: "Electrical and Electronics Engineering",
    level_code: "L200",
    semester_code: "S2",
    preferred_course_code: "DIFF_EQ",
    onboarding_completed: true,
    created_at: "2026-01-12T08:30:00Z",
    last_active_at: "2026-04-04T14:22:00Z",
    current_streak: 21,
    longest_streak: 34,
    total_questions_answered: 847,
    total_correct: 698,
    total_quizzes_completed: 142,
    reports_filed: 3,
  },
  courses: [
    {
      course_id: "DIFF_EQ", course_name: "Differential Equations",
      overall_skill: 3.8, phase: "established",
      topic_skills: {
        order_of_differential_equation: 4.2,
        ordinary_differential_equations: 3.9,
        exact_differential_equation: 3.5,
        separable_differential_equation: 4.0,
        integrating_factor: 3.2,
        linear_first_order: 3.7,
      },
      cognitive_profile: { Remembering: 4.1, Understanding: 3.8, Applying: 3.6, Analyzing: 3.2 },
      processing_profile: { low: 4.2, medium: 3.5, high: 2.8 },
      misconception_flags: [],
      total_quizzes_completed: 68, total_attempts: 412, total_correct: 350,
      avg_time_per_question: 42.3, exam_date: "2026-05-15T09:00:00Z",
    },
    {
      course_id: "LIN_ELEC", course_name: "Linear Electronics",
      overall_skill: 3.4, phase: "warm",
      topic_skills: {
        op_amp_basics: 3.8,
        inverting_amplifier: 3.2,
        non_inverting_amplifier: 3.5,
        summing_amplifier: 2.9,
        differential_amplifier: 2.7,
      },
      cognitive_profile: { Remembering: 3.6, Understanding: 3.4, Applying: 3.1, Analyzing: 2.8 },
      processing_profile: { low: 3.8, medium: 3.2, high: 2.5 },
      misconception_flags: [
        { topic: "differential_amplifier", description: "Confuses CMRR with voltage gain", severity: "medium" },
      ],
      total_quizzes_completed: 45, total_attempts: 280, total_correct: 224,
      avg_time_per_question: 38.7, exam_date: "2026-05-20T09:00:00Z",
    },
    {
      course_id: "GEN_PSY", course_name: "General Psychology",
      overall_skill: 3.1, phase: "warm",
      topic_skills: {
        definition_of_psychology: 3.8,
        origin_of_psychology: 3.5,
        psychosexual_stages: 2.9,
        clinical_psychology: 3.2,
        adversity_quotient: 2.7,
      },
      cognitive_profile: { Remembering: 3.4, Understanding: 3.0, Applying: 2.6, Analyzing: 2.4 },
      processing_profile: { low: 3.6, medium: 2.8, high: 2.2 },
      misconception_flags: [
        { topic: "psychosexual_stages", description: "Mixes up latency and phallic stage characteristics", severity: "low" },
      ],
      total_quizzes_completed: 29, total_attempts: 155, total_correct: 124,
      avg_time_per_question: 25.1, exam_date: null,
    },
  ],
  srs: [
    { course_id: "DIFF_EQ", course_name: "Differential Equations", box_0: 5, box_1: 12, box_2: 18, box_3: 25, box_4: 30, box_5: 22 },
    { course_id: "LIN_ELEC", course_name: "Linear Electronics", box_0: 8, box_1: 15, box_2: 20, box_3: 18, box_4: 12, box_5: 7 },
    { course_id: "GEN_PSY", course_name: "General Psychology", box_0: 12, box_1: 18, box_2: 14, box_3: 10, box_4: 6, box_5: 2 },
  ],
  weekly_progress: [
    { week: "W1", attempts: 45, correct: 32, accuracy: 71.1, avg_time: 48.2 },
    { week: "W2", attempts: 52, correct: 39, accuracy: 75.0, avg_time: 45.1 },
    { week: "W3", attempts: 60, correct: 47, accuracy: 78.3, avg_time: 44.0 },
    { week: "W4", attempts: 58, correct: 46, accuracy: 79.3, avg_time: 42.8 },
    { week: "W5", attempts: 72, correct: 58, accuracy: 80.6, avg_time: 41.5 },
    { week: "W6", attempts: 68, correct: 56, accuracy: 82.4, avg_time: 40.2 },
    { week: "W7", attempts: 75, correct: 63, accuracy: 84.0, avg_time: 39.8 },
    { week: "W8", attempts: 80, correct: 66, accuracy: 82.5, avg_time: 41.0 },
    { week: "W9", attempts: 85, correct: 72, accuracy: 84.7, avg_time: 38.5 },
    { week: "W10", attempts: 78, correct: 65, accuracy: 83.3, avg_time: 39.2 },
    { week: "W11", attempts: 90, correct: 76, accuracy: 84.4, avg_time: 37.8 },
    { week: "W12", attempts: 84, correct: 72, accuracy: 85.7, avg_time: 36.5 },
  ],
  daily_activity: generateDailyActivity(30, 18, 35),
  recent_attempts: [
    { question_key: "DIFF_EQ_001", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 35, created_at: "2026-04-04T14:22:00Z" },
    { question_key: "DIFF_EQ_005", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 52, created_at: "2026-04-04T14:18:00Z" },
    { question_key: "LIN_ELEC_002", course_name: "Linear Electronics", is_correct: false, time_taken_seconds: 61, created_at: "2026-04-04T13:50:00Z" },
    { question_key: "DIFF_EQ_003", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 44, created_at: "2026-04-04T13:45:00Z" },
    { question_key: "GEN_PSY_003", course_name: "General Psychology", is_correct: true, time_taken_seconds: 22, created_at: "2026-04-03T20:15:00Z" },
    { question_key: "DIFF_EQ_006", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 68, created_at: "2026-04-03T20:10:00Z" },
    { question_key: "LIN_ELEC_001", course_name: "Linear Electronics", is_correct: true, time_taken_seconds: 30, created_at: "2026-04-03T19:55:00Z" },
    { question_key: "GEN_PSY_001", course_name: "General Psychology", is_correct: true, time_taken_seconds: 18, created_at: "2026-04-03T19:48:00Z" },
    { question_key: "DIFF_EQ_004", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 55, created_at: "2026-04-02T21:30:00Z" },
    { question_key: "LIN_ELEC_003", course_name: "Linear Electronics", is_correct: true, time_taken_seconds: 28, created_at: "2026-04-02T21:22:00Z" },
    { question_key: "DIFF_EQ_002", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 40, created_at: "2026-04-02T21:15:00Z" },
    { question_key: "GEN_PSY_005", course_name: "General Psychology", is_correct: false, time_taken_seconds: 33, created_at: "2026-04-01T18:40:00Z" },
    { question_key: "DIFF_EQ_007", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 47, created_at: "2026-04-01T18:32:00Z" },
    { question_key: "LIN_ELEC_001", course_name: "Linear Electronics", is_correct: true, time_taken_seconds: 25, created_at: "2026-04-01T18:25:00Z" },
    { question_key: "GEN_PSY_002", course_name: "General Psychology", is_correct: true, time_taken_seconds: 20, created_at: "2026-03-31T17:00:00Z" },
    { question_key: "DIFF_EQ_001", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 32, created_at: "2026-03-31T16:50:00Z" },
    { question_key: "LIN_ELEC_002", course_name: "Linear Electronics", is_correct: true, time_taken_seconds: 42, created_at: "2026-03-30T15:20:00Z" },
    { question_key: "DIFF_EQ_006", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 58, created_at: "2026-03-30T15:12:00Z" },
    { question_key: "GEN_PSY_004", course_name: "General Psychology", is_correct: true, time_taken_seconds: 15, created_at: "2026-03-29T12:00:00Z" },
    { question_key: "DIFF_EQ_005", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 70, created_at: "2026-03-29T11:50:00Z" },
  ],
};

// ─── Student 2: ama_scholar (Strong, established) ────────────────────────────

const STUDENT_2: StudentDetailData = {
  profile: {
    user_id: "1002", display_name: "Ama Scholastica Mensah", telegram_user_id: "9823456", telegram_username: "ama_scholar",
    faculty_code: "FOE", faculty_name: "Faculty of Engineering", program_code: "EEE", program_name: "Electrical and Electronics Engineering",
    level_code: "L200", semester_code: "S2", preferred_course_code: "GEN_PSY",
    onboarding_completed: true, created_at: "2026-01-18T10:15:00Z", last_active_at: "2026-04-04T11:30:00Z",
    current_streak: 18, longest_streak: 25, total_questions_answered: 723, total_correct: 572, total_quizzes_completed: 121, reports_filed: 1,
  },
  courses: [
    {
      course_id: "GEN_PSY", course_name: "General Psychology", overall_skill: 3.6, phase: "established",
      topic_skills: { definition_of_psychology: 4.0, origin_of_psychology: 3.8, psychosexual_stages: 3.5, clinical_psychology: 3.7, adversity_quotient: 3.3 },
      cognitive_profile: { Remembering: 3.9, Understanding: 3.6, Applying: 3.2, Analyzing: 2.9 },
      processing_profile: { low: 4.0, medium: 3.4, high: 2.6 },
      misconception_flags: [],
      total_quizzes_completed: 55, total_attempts: 340, total_correct: 278, avg_time_per_question: 21.4, exam_date: "2026-05-12T09:00:00Z",
    },
    {
      course_id: "DIFF_EQ", course_name: "Differential Equations", overall_skill: 3.2, phase: "warm",
      topic_skills: { order_of_differential_equation: 3.6, ordinary_differential_equations: 3.3, exact_differential_equation: 2.8, separable_differential_equation: 3.4, integrating_factor: 2.6 },
      cognitive_profile: { Remembering: 3.5, Understanding: 3.2, Applying: 2.9, Analyzing: 2.5 },
      processing_profile: { low: 3.6, medium: 3.0, high: 2.4 },
      misconception_flags: [{ topic: "integrating_factor", description: "Forgets to divide by leading coefficient before computing µ(x)", severity: "medium" }],
      total_quizzes_completed: 42, total_attempts: 245, total_correct: 188, avg_time_per_question: 48.2, exam_date: "2026-05-15T09:00:00Z",
    },
    {
      course_id: "THERMO", course_name: "Thermodynamics", overall_skill: 2.8, phase: "warm",
      topic_skills: { first_law: 3.2, second_law: 2.7, entropy: 2.4, carnot_cycle: 2.9, ideal_gas: 3.1 },
      cognitive_profile: { Remembering: 3.0, Understanding: 2.7, Applying: 2.5, Analyzing: 2.2 },
      processing_profile: { low: 3.2, medium: 2.6, high: 2.0 },
      misconception_flags: [{ topic: "entropy", description: "Conflates entropy change of system vs surroundings", severity: "high" }],
      total_quizzes_completed: 24, total_attempts: 138, total_correct: 106, avg_time_per_question: 52.8, exam_date: null,
    },
  ],
  srs: [
    { course_id: "GEN_PSY", course_name: "General Psychology", box_0: 3, box_1: 8, box_2: 15, box_3: 22, box_4: 28, box_5: 18 },
    { course_id: "DIFF_EQ", course_name: "Differential Equations", box_0: 10, box_1: 18, box_2: 22, box_3: 15, box_4: 8, box_5: 4 },
    { course_id: "THERMO", course_name: "Thermodynamics", box_0: 15, box_1: 20, box_2: 12, box_3: 8, box_4: 3, box_5: 1 },
  ],
  weekly_progress: [
    { week: "W1", attempts: 40, correct: 28, accuracy: 70.0, avg_time: 45.0 },
    { week: "W2", attempts: 48, correct: 35, accuracy: 72.9, avg_time: 43.2 },
    { week: "W3", attempts: 55, correct: 42, accuracy: 76.4, avg_time: 40.5 },
    { week: "W4", attempts: 50, correct: 39, accuracy: 78.0, avg_time: 39.8 },
    { week: "W5", attempts: 62, correct: 49, accuracy: 79.0, avg_time: 38.5 },
    { week: "W6", attempts: 58, correct: 46, accuracy: 79.3, avg_time: 37.2 },
    { week: "W7", attempts: 65, correct: 52, accuracy: 80.0, avg_time: 36.8 },
    { week: "W8", attempts: 70, correct: 56, accuracy: 80.0, avg_time: 36.0 },
    { week: "W9", attempts: 68, correct: 55, accuracy: 80.9, avg_time: 35.5 },
    { week: "W10", attempts: 72, correct: 58, accuracy: 80.6, avg_time: 35.0 },
    { week: "W11", attempts: 75, correct: 61, accuracy: 81.3, avg_time: 34.2 },
    { week: "W12", attempts: 60, correct: 49, accuracy: 81.7, avg_time: 33.8 },
  ],
  daily_activity: generateDailyActivity(30, 14, 28),
  recent_attempts: [
    { question_key: "GEN_PSY_003", course_name: "General Psychology", is_correct: true, time_taken_seconds: 18, created_at: "2026-04-04T11:30:00Z" },
    { question_key: "DIFF_EQ_006", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 65, created_at: "2026-04-04T11:22:00Z" },
    { question_key: "GEN_PSY_001", course_name: "General Psychology", is_correct: true, time_taken_seconds: 20, created_at: "2026-04-04T11:15:00Z" },
    { question_key: "THERMO_001", course_name: "Thermodynamics", is_correct: true, time_taken_seconds: 45, created_at: "2026-04-03T19:40:00Z" },
    { question_key: "DIFF_EQ_002", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 50, created_at: "2026-04-03T19:30:00Z" },
    { question_key: "GEN_PSY_005", course_name: "General Psychology", is_correct: true, time_taken_seconds: 16, created_at: "2026-04-03T19:22:00Z" },
    { question_key: "DIFF_EQ_004", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 72, created_at: "2026-04-02T20:15:00Z" },
    { question_key: "THERMO_002", course_name: "Thermodynamics", is_correct: true, time_taken_seconds: 48, created_at: "2026-04-02T20:05:00Z" },
    { question_key: "GEN_PSY_002", course_name: "General Psychology", is_correct: true, time_taken_seconds: 14, created_at: "2026-04-01T18:30:00Z" },
    { question_key: "DIFF_EQ_001", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 38, created_at: "2026-04-01T18:20:00Z" },
  ],
};

// ─── Student 7: nana_b (Struggling, cold_start) ─────────────────────────────

const STUDENT_7: StudentDetailData = {
  profile: {
    user_id: "1007", display_name: "Nana Barima Osei", telegram_user_id: "9878901", telegram_username: "nana_b",
    faculty_code: "FOE", faculty_name: "Faculty of Engineering", program_code: "EEE", program_name: "Electrical and Electronics Engineering",
    level_code: "L200", semester_code: "S2", preferred_course_code: "TRANS_DC",
    onboarding_completed: true, created_at: "2026-03-01T14:00:00Z", last_active_at: "2026-04-02T16:45:00Z",
    current_streak: 5, longest_streak: 8, total_questions_answered: 434, total_correct: 286, total_quizzes_completed: 72, reports_filed: 0,
  },
  courses: [
    {
      course_id: "TRANS_DC", course_name: "Transformers and DC Machines", overall_skill: 2.3, phase: "cold_start",
      topic_skills: { transformer_basics: 2.8, dc_motor_types: 2.1, power_losses: 1.8, efficiency: 2.5, equivalent_circuit: 1.6 },
      cognitive_profile: { Remembering: 2.8, Understanding: 2.2, Applying: 1.9, Analyzing: 1.5 },
      processing_profile: { low: 2.9, medium: 2.0, high: 1.4 },
      misconception_flags: [
        { topic: "power_losses", description: "Confuses copper loss with iron loss mechanisms", severity: "high" },
        { topic: "equivalent_circuit", description: "Incorrect referred impedance calculations", severity: "high" },
      ],
      total_quizzes_completed: 35, total_attempts: 210, total_correct: 128, avg_time_per_question: 58.4, exam_date: "2026-05-22T09:00:00Z",
    },
    {
      course_id: "DIFF_EQ", course_name: "Differential Equations", overall_skill: 2.1, phase: "cold_start",
      topic_skills: { order_of_differential_equation: 2.8, ordinary_differential_equations: 2.2, exact_differential_equation: 1.7, separable_differential_equation: 2.0, integrating_factor: 1.5 },
      cognitive_profile: { Remembering: 2.5, Understanding: 2.0, Applying: 1.7, Analyzing: 1.3 },
      processing_profile: { low: 2.6, medium: 1.8, high: 1.2 },
      misconception_flags: [
        { topic: "exact_differential_equation", description: "Does not verify exactness condition before solving", severity: "medium" },
        { topic: "integrating_factor", description: "Applies wrong formula for µ(y) vs µ(x)", severity: "high" },
      ],
      total_quizzes_completed: 22, total_attempts: 142, total_correct: 88, avg_time_per_question: 62.1, exam_date: "2026-05-15T09:00:00Z",
    },
    {
      course_id: "WORKSHOP", course_name: "Workshop Technology and Practice", overall_skill: 2.6, phase: "warm",
      topic_skills: { safety_procedures: 3.2, hand_tools: 2.8, measuring_instruments: 2.5, welding_basics: 2.2, machining: 2.0 },
      cognitive_profile: { Remembering: 3.0, Understanding: 2.5, Applying: 2.2, Analyzing: 1.8 },
      processing_profile: { low: 3.0, medium: 2.4, high: 1.6 },
      misconception_flags: [],
      total_quizzes_completed: 15, total_attempts: 82, total_correct: 58, avg_time_per_question: 35.2, exam_date: null,
    },
  ],
  srs: [
    { course_id: "TRANS_DC", course_name: "Transformers and DC Machines", box_0: 25, box_1: 22, box_2: 12, box_3: 5, box_4: 2, box_5: 0 },
    { course_id: "DIFF_EQ", course_name: "Differential Equations", box_0: 30, box_1: 18, box_2: 8, box_3: 4, box_4: 1, box_5: 0 },
    { course_id: "WORKSHOP", course_name: "Workshop Technology and Practice", box_0: 10, box_1: 14, box_2: 10, box_3: 6, box_4: 3, box_5: 1 },
  ],
  weekly_progress: [
    { week: "W1", attempts: 20, correct: 10, accuracy: 50.0, avg_time: 65.0 },
    { week: "W2", attempts: 25, correct: 14, accuracy: 56.0, avg_time: 62.5 },
    { week: "W3", attempts: 30, correct: 18, accuracy: 60.0, avg_time: 60.0 },
    { week: "W4", attempts: 28, correct: 17, accuracy: 60.7, avg_time: 59.2 },
    { week: "W5", attempts: 35, correct: 22, accuracy: 62.9, avg_time: 58.0 },
    { week: "W6", attempts: 38, correct: 24, accuracy: 63.2, avg_time: 57.5 },
    { week: "W7", attempts: 40, correct: 26, accuracy: 65.0, avg_time: 56.0 },
    { week: "W8", attempts: 42, correct: 28, accuracy: 66.7, avg_time: 55.2 },
    { week: "W9", attempts: 38, correct: 25, accuracy: 65.8, avg_time: 56.8 },
    { week: "W10", attempts: 45, correct: 30, accuracy: 66.7, avg_time: 55.0 },
    { week: "W11", attempts: 48, correct: 33, accuracy: 68.8, avg_time: 53.5 },
    { week: "W12", attempts: 45, correct: 31, accuracy: 68.9, avg_time: 52.8 },
  ],
  daily_activity: generateDailyActivity(30, 8, 20),
  recent_attempts: [
    { question_key: "TRANS_DC_001", course_name: "Transformers and DC Machines", is_correct: false, time_taken_seconds: 72, created_at: "2026-04-02T16:45:00Z" },
    { question_key: "DIFF_EQ_003", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 80, created_at: "2026-04-02T16:35:00Z" },
    { question_key: "WORKSHOP_001", course_name: "Workshop Technology and Practice", is_correct: true, time_taken_seconds: 28, created_at: "2026-04-02T16:28:00Z" },
    { question_key: "TRANS_DC_002", course_name: "Transformers and DC Machines", is_correct: true, time_taken_seconds: 55, created_at: "2026-04-01T20:10:00Z" },
    { question_key: "DIFF_EQ_001", course_name: "Differential Equations", is_correct: true, time_taken_seconds: 45, created_at: "2026-04-01T20:02:00Z" },
    { question_key: "TRANS_DC_003", course_name: "Transformers and DC Machines", is_correct: false, time_taken_seconds: 68, created_at: "2026-03-31T19:30:00Z" },
    { question_key: "DIFF_EQ_006", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 75, created_at: "2026-03-31T19:20:00Z" },
    { question_key: "WORKSHOP_002", course_name: "Workshop Technology and Practice", is_correct: true, time_taken_seconds: 22, created_at: "2026-03-30T18:00:00Z" },
    { question_key: "TRANS_DC_001", course_name: "Transformers and DC Machines", is_correct: true, time_taken_seconds: 60, created_at: "2026-03-30T17:50:00Z" },
    { question_key: "DIFF_EQ_004", course_name: "Differential Equations", is_correct: false, time_taken_seconds: 82, created_at: "2026-03-29T16:15:00Z" },
  ],
};

// ─── Helper: generate daily activity ─────────────────────────────────────────

function generateDailyActivity(days: number, min: number, max: number): DailyActivity[] {
  const result: DailyActivity[] = [];
  const now = new Date("2026-04-04");
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const isWeekend = d.getDay() === 0 || d.getDay() === 6;
    const base = isWeekend ? Math.floor(min * 0.5) : min;
    const top = isWeekend ? Math.floor(max * 0.6) : max;
    const count = Math.floor(Math.random() * (top - base + 1)) + base;
    result.push({ date: d.toISOString().slice(0, 10), questions_count: Math.max(0, count) });
  }
  return result;
}

// ─── Lookup Map ──────────────────────────────────────────────────────────────
// We provide detailed data for students 1, 2, and 7 (top, mid, struggling).
// Others fall back to a generated profile built from the leaderboard.

const MOCK_STUDENT_DETAILS: Record<string, StudentDetailData> = {
  "1001": STUDENT_1,
  "1002": STUDENT_2,
  "1007": STUDENT_7,
};

// ─── Fallback generator for students without full detail data ────────────────

export function getStudentDetailOrGenerate(
  userId: string,
  leaderboard: { user_id: string; telegram_username: string; telegram_id: string; questions_answered: number; daily_streak: number; accuracy: number; overall_skill: number; phase: "cold_start" | "warm" | "established"; top_course: string }[],
): StudentDetailData | undefined {
  const detailed = MOCK_STUDENT_DETAILS[userId];
  if (detailed) return detailed;

  const entry = leaderboard.find((e) => e.user_id === userId);
  if (!entry) return undefined;

  const totalCorrect = Math.round(entry.questions_answered * (entry.accuracy / 100));
  const profile: StudentProfile = {
    user_id: entry.user_id,
    display_name: entry.telegram_username.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    telegram_user_id: entry.telegram_id,
    telegram_username: entry.telegram_username,
    faculty_code: "FOE", faculty_name: "Faculty of Engineering",
    program_code: "EEE", program_name: "Electrical and Electronics Engineering",
    level_code: "L200", semester_code: "S2",
    preferred_course_code: entry.top_course.toUpperCase().replace(/ /g, "_").slice(0, 12),
    onboarding_completed: true,
    created_at: "2026-02-01T10:00:00Z",
    last_active_at: "2026-04-03T15:00:00Z",
    current_streak: entry.daily_streak,
    longest_streak: entry.daily_streak + 5,
    total_questions_answered: entry.questions_answered,
    total_correct: totalCorrect,
    total_quizzes_completed: Math.round(entry.questions_answered / 6),
    reports_filed: 0,
  };

  const course: StudentCoursePerformance = {
    course_id: profile.preferred_course_code,
    course_name: entry.top_course,
    overall_skill: entry.overall_skill,
    phase: entry.phase,
    topic_skills: { general_topic_a: entry.overall_skill + 0.2, general_topic_b: entry.overall_skill - 0.3, general_topic_c: entry.overall_skill },
    cognitive_profile: { Remembering: entry.overall_skill + 0.3, Understanding: entry.overall_skill, Applying: entry.overall_skill - 0.3, Analyzing: entry.overall_skill - 0.5 },
    processing_profile: { low: entry.overall_skill + 0.4, medium: entry.overall_skill - 0.2, high: entry.overall_skill - 0.6 },
    misconception_flags: [],
    total_quizzes_completed: profile.total_quizzes_completed,
    total_attempts: entry.questions_answered,
    total_correct: totalCorrect,
    avg_time_per_question: 40,
    exam_date: null,
  };

  return {
    profile,
    courses: [course],
    srs: [{ course_id: course.course_id, course_name: course.course_name, box_0: 15, box_1: 20, box_2: 15, box_3: 10, box_4: 5, box_5: 2 }],
    weekly_progress: Array.from({ length: 12 }, (_, i) => ({
      week: `W${i + 1}`,
      attempts: Math.round(entry.questions_answered / 12 + (Math.random() - 0.5) * 10),
      correct: Math.round((entry.questions_answered / 12) * (entry.accuracy / 100) + (Math.random() - 0.5) * 5),
      accuracy: entry.accuracy + (Math.random() - 0.5) * 6,
      avg_time: 38 + (Math.random() - 0.5) * 10,
    })),
    daily_activity: generateDailyActivity(30, 8, 22),
    recent_attempts: [
      { question_key: "Q_001", course_name: entry.top_course, is_correct: true, time_taken_seconds: 35, created_at: "2026-04-03T15:00:00Z" },
      { question_key: "Q_002", course_name: entry.top_course, is_correct: false, time_taken_seconds: 55, created_at: "2026-04-03T14:50:00Z" },
      { question_key: "Q_003", course_name: entry.top_course, is_correct: true, time_taken_seconds: 30, created_at: "2026-04-02T20:00:00Z" },
      { question_key: "Q_004", course_name: entry.top_course, is_correct: true, time_taken_seconds: 42, created_at: "2026-04-02T19:50:00Z" },
      { question_key: "Q_005", course_name: entry.top_course, is_correct: false, time_taken_seconds: 65, created_at: "2026-04-01T18:30:00Z" },
    ],
  };
}

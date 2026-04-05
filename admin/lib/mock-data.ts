// ─── Staff ──────────────────────────────────────────────────────────────────
export type StaffUser = {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
  permissions: string[];
  created_at: string;
};

export const MOCK_STAFF: StaffUser[] = [
  {
    id: 1,
    email: "kwame.asante@staff.adarkwa.edu",
    display_name: "Kwame Asante",
    is_active: true,
    roles: ["super_admin"],
    permissions: ["staff.manage", "catalog.write", "questions.write", "analytics.read"],
    created_at: "2026-01-15T09:00:00Z",
  },
  {
    id: 2,
    email: "ama.mensah@staff.adarkwa.edu",
    display_name: "Ama Mensah",
    is_active: true,
    roles: ["editor"],
    permissions: ["questions.write", "questions.read"],
    created_at: "2026-02-10T14:30:00Z",
  },
  {
    id: 3,
    email: "yaw.boateng@staff.adarkwa.edu",
    display_name: "Yaw Boateng",
    is_active: true,
    roles: ["catalog_manager"],
    permissions: ["catalog.write", "catalog.read"],
    created_at: "2026-02-22T11:00:00Z",
  },
  {
    id: 4,
    email: "akua.darko@staff.adarkwa.edu",
    display_name: "Akua Darko",
    is_active: false,
    roles: ["viewer"],
    permissions: ["analytics.read"],
    created_at: "2026-03-01T08:45:00Z",
  },
  {
    id: 5,
    email: "kofi.addo@staff.adarkwa.edu",
    display_name: "Kofi Addo",
    is_active: true,
    roles: ["editor"],
    permissions: ["questions.write", "questions.read", "analytics.read"],
    created_at: "2026-03-05T16:20:00Z",
  },
];

export const MOCK_ROLES = [
  { code: "super_admin", name: "Super Admin", description: "Full system access" },
  { code: "editor", name: "Editor", description: "Manage questions and content" },
  { code: "catalog_manager", name: "Catalog Manager", description: "Manage academic catalog" },
  { code: "viewer", name: "Viewer", description: "Read-only analytics access" },
];

export const MOCK_PERMISSIONS = [
  { code: "staff.manage", name: "Manage Staff" },
  { code: "catalog.read", name: "View Catalog" },
  { code: "catalog.write", name: "Edit Catalog" },
  { code: "questions.read", name: "View Questions" },
  { code: "questions.write", name: "Edit Questions" },
  { code: "analytics.read", name: "View Analytics" },
];

// ─── Catalog ────────────────────────────────────────────────────────────────
export type CatalogEntry = {
  code: string;
  name: string;
  active: boolean;
  children?: CatalogEntry[];
};

export const MOCK_CATALOG: CatalogEntry[] = [
  {
    code: "FCMS",
    name: "Faculty of Computing and Mathematical Sciences",
    active: true,
  },
  {
    code: "FOE",
    name: "Faculty of Engineering",
    active: true,
    children: [
      {
        code: "EEE",
        name: "Electrical and Electronics Engineering",
        active: true,
        children: [
          {
            code: "L200",
            name: "Level 200",
            active: true,
            children: [
              { code: "DIFF_EQ", name: "Differential Equations", active: true },
              { code: "GEN_PSY", name: "General Psychology", active: true },
              { code: "LIN_ELEC", name: "Linear Electronics", active: true },
              { code: "LABVIEW", name: "Programming in LabVIEW", active: true },
              { code: "MATLAB", name: "Programming in MATLAB/Simulink", active: true },
              { code: "THERMO", name: "Thermodynamics", active: true },
              { code: "TRANS_DC", name: "Transformers and DC Machines", active: true },
              { code: "WORKSHOP", name: "Workshop Technology and Practice", active: true },
            ],
          },
        ],
      },
      {
        code: "ME",
        name: "Mechanical Engineering",
        active: true,
      },
      {
        code: "REE",
        name: "Renewable Energy Engineering",
        active: true,
      },
    ],
  },
  {
    code: "FGES",
    name: "Faculty of Geosciences and Environmental Studies",
    active: true,
  },
  {
    code: "FIMS",
    name: "Faculty of Integrated and Mathematical Science",
    active: true,
  },
  {
    code: "FMMT",
    name: "Faculty of Minerals and Minerals Technology",
    active: true,
  },
  {
    code: "SP",
    name: "School of Petroleum",
    active: true,
  },
];

// ─── Questions ──────────────────────────────────────────────────────────────
export type Question = {
  id: number;
  question_key: string;
  course_code: string;
  course_name: string;
  topic_id: string;
  question_text: string;
  options: string[];
  option_count: number;
  correct_option: number;
  correct_option_text: string;
  short_explanation: string;
  question_type: string;
  band: number;
  cognitive_level: string;
  has_latex: boolean;
  base_score: number;
  note_reference: number;
  distractor_complexity: number;
  processing_complexity: number;
  negative_stem: number;
  raw_score: number;
  scaled_score: number;
  status: string;
  updated_at: string;
};

export const MOCK_QUESTIONS: Question[] = [
  // Differential Equations
  {
    id: 1,
    question_key: "DIFF_EQ_001",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "order_of_differential_equation",
    question_text: "What is the order of the differential equation below? $x^{2}y^{\\prime\\prime}+y(y^{\\prime})^{3}-xy^{4}=0$",
    options: ["3", "4", "0", "none"],
    option_count: 4,
    correct_option: 3,
    correct_option_text: "none",
    short_explanation: "The order of a differential equation is the order of the highest derivative appearing in it. Since the highest derivative is $y^{\\prime\\prime}$, it is a second-order equation, making 'none' the correct option.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Applying",
    has_latex: true,
    base_score: 1.6,
    note_reference: 1.0,
    distractor_complexity: 1.2,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.92,
    scaled_score: 1.5,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 2,
    question_key: "DIFF_EQ_002",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "ordinary_differential_equations",
    question_text: "How many solutions does the differential equation $\\frac{dy}{dx}=x^{4}cos~x+xe^{x}-3$ have?",
    options: ["one", "three", "infinitely many", "None of the above"],
    option_count: 4,
    correct_option: 2,
    correct_option_text: "infinitely many",
    short_explanation: "Integrating a first-order differential equation yields a general solution containing an arbitrary constant C. Because C can take any value, it represents an infinite family of particular solutions.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Understanding",
    has_latex: true,
    base_score: 1.3,
    note_reference: 1.0,
    distractor_complexity: 1.2,
    processing_complexity: 1.5,
    negative_stem: 1.0,
    raw_score: 2.34,
    scaled_score: 1.7,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 3,
    question_key: "DIFF_EQ_003",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "exact_differential_equation",
    question_text: "Which of the following equations is exact?",
    options: ["$yy^{\\prime}+2xy=yx^{2}$", "$xe^{x}-x^{2}y^{\\prime}=2yx$", "$y^{\\prime}-y=0$", "None of the above"],
    option_count: 4,
    correct_option: 1,
    correct_option_text: "$xe^{x}-x^{2}y^{\\prime}=2yx$",
    short_explanation: "Rearranging gives $(2yx - xe^x)dx + x^2dy = 0$. The partial derivative of M with respect to y is $2x$, and the partial derivative of N with respect to x is $2x$, fulfilling the necessary condition for exactness.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Applying",
    has_latex: true,
    base_score: 1.6,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.5,
    negative_stem: 1.0,
    raw_score: 2.4,
    scaled_score: 1.7,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 4,
    question_key: "DIFF_EQ_004",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "separable_differential_equation",
    question_text: "Which of the following differential equations is separable? I. $xy^{\\prime}=x^{2}y+3y$ II. $xy^{\\prime}=x-y$ III. $e^{x}y^{\\prime}=xy-x$",
    options: ["I only", "II and III", "III only", "I and III"],
    option_count: 4,
    correct_option: 3,
    correct_option_text: "I and III",
    short_explanation: "Equation I factors to $x y' = y(x^2+3)$ and Equation III factors to $e^x y' = x(y-1)$, allowing separation of variables. Equation II cannot be separated into a product of a function of x and a function of y.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Analyzing",
    has_latex: true,
    base_score: 2.0,
    note_reference: 1.2,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 2.4,
    scaled_score: 1.7,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 5,
    question_key: "DIFF_EQ_005",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "ordinary_differential_equations",
    question_text: "The general solution of $(x^{2}-ay)dx=(ax-y^{2})dy$ is",
    options: ["$x^{3}-y^{3}=axy+c$", "$x^{3}+y^{3}=3axy+c$", "$x^{3}-y^{3}=3axy+c$", "None of the above"],
    option_count: 4,
    correct_option: 1,
    correct_option_text: "$x^{3}+y^{3}=3axy+c$",
    short_explanation: "Rearranging gives $(x^2-ay)dx + (y^2-ax)dy = 0$. It is exact since $\\partial M/\\partial y = -a = \\partial N/\\partial x$. Grouping terms and integrating yields $x^3/3 + y^3/3 - axy = C$, simplifying to $x^3 + y^3 = 3axy + c$.",
    question_type: "mcq",
    band: 2,
    cognitive_level: "Applying",
    has_latex: true,
    base_score: 1.6,
    note_reference: 1.2,
    distractor_complexity: 1.2,
    processing_complexity: 1.4,
    negative_stem: 1.0,
    raw_score: 3.226,
    scaled_score: 2.1,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 6,
    question_key: "DIFF_EQ_006",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "integrating_factor",
    question_text: "The integrating factor of $(1+x^{2})\\frac{dy}{dx}+xy=(1+x^{2})^{3}$ is",
    options: ["$\\sqrt{1+x^{2}}$", "$ln(1+x^{2})$", "$e^{tan^{-1}x}$", "None of the above"],
    option_count: 4,
    correct_option: 0,
    correct_option_text: "$\\sqrt{1+x^{2}}$",
    short_explanation: "Dividing by $(1+x^2)$ gives the standard linear form with $P(x) = \\frac{x}{1+x^2}$. The integrating factor is $\\mu(x) = e^{\\int P(x)dx} = e^{\\frac{1}{2}\\ln(1+x^2)} = \\sqrt{1+x^2}$.",
    question_type: "mcq",
    band: 2,
    cognitive_level: "Applying",
    has_latex: true,
    base_score: 1.6,
    note_reference: 1.2,
    distractor_complexity: 1.2,
    processing_complexity: 1.4,
    negative_stem: 1.0,
    raw_score: 3.226,
    scaled_score: 2.1,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 7,
    question_key: "DIFF_EQ_007",
    course_code: "DIFF_EQ",
    course_name: "Differential Equations",
    topic_id: "exact_differential_equation",
    question_text: "Which of the following equation is an exact differential equation?",
    options: ["$(x^{2}+1)dx-xydy=0$", "$xdy+(3x-3y)dx=0$", "$2xydx+(2+x^{2})dy=0$", "$x^{2}ydy-ydx=0$"],
    option_count: 4,
    correct_option: 2,
    correct_option_text: "$2xydx+(2+x^{2})dy=0$",
    short_explanation: "In this equation, $M = 2xy$ and $N = 2+x^2$. The partial derivative $\\partial M/\\partial y$ is $2x$, matching $\\partial N/\\partial x = 2x$, making it exact.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Applying",
    has_latex: true,
    base_score: 1.6,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.5,
    negative_stem: 1.0,
    raw_score: 2.4,
    scaled_score: 1.7,
    status: "needs_review",
    updated_at: "2026-03-29T12:00:00Z",
  },
  // Linear Electronics
  {
    id: 8,
    question_key: "LIN_ELEC_001",
    course_code: "LIN_ELEC",
    course_name: "Linear Electronics",
    topic_id: "op_amp_basics",
    question_text: "An ideal op-amp is characterised by",
    options: [
      "an infinite voltage gain, zero input resistance and an infinite output resistance",
      "an infinite voltage gain, an infinite input resistance and zero output resistance",
      "an infinite voltage gain, an infinite input resistance and an infinite output resistance",
      "an infinite voltage gain, zero input resistance and zero output resistance"
    ],
    option_count: 4,
    correct_option: 1,
    correct_option_text: "an infinite voltage gain, an infinite input resistance and zero output resistance",
    short_explanation: "An ideal op-amp is defined by having infinite open-loop voltage gain, infinite input resistance (so no current enters the input), and zero output resistance (so it can drive any load without voltage drop).",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Understanding",
    has_latex: false,
    base_score: 1.3,
    note_reference: 1.0,
    distractor_complexity: 1.5,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.95,
    scaled_score: 1.5,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 9,
    question_key: "LIN_ELEC_002",
    course_code: "LIN_ELEC",
    course_name: "Linear Electronics",
    topic_id: "op_amp_basics",
    question_text: "In which of the following is an operational amplifier used?",
    options: ["instrumentation circuits", "oscillators", "filters", "all of them"],
    option_count: 4,
    correct_option: 3,
    correct_option_text: "all of them",
    short_explanation: "The handout lists op-amp applications such as instrumentation and control systems, oscillator circuits, and filters. Therefore all listed options are correct.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Understanding",
    has_latex: false,
    base_score: 1.3,
    note_reference: 1.2,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.56,
    scaled_score: 1.3,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 10,
    question_key: "LIN_ELEC_003",
    course_code: "LIN_ELEC",
    course_name: "Linear Electronics",
    topic_id: "op_amp_basics",
    question_text: "What is the level of the voltage between the input terminals of an op-amp?",
    options: ["Virtually zero", "– 5 V", "5 V", "Infinite"],
    option_count: 4,
    correct_option: 0,
    correct_option_text: "Virtually zero",
    short_explanation: "For an ideal op-amp operating with negative feedback, the differential input voltage between the two input terminals is virtually zero because of the virtual short concept.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Understanding",
    has_latex: false,
    base_score: 1.3,
    note_reference: 1.2,
    distractor_complexity: 1.5,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 2.34,
    scaled_score: 1.7,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  // General Psychology
  {
    id: 11,
    question_key: "GEN_PSY_001",
    course_code: "GEN_PSY",
    course_name: "General Psychology",
    topic_id: "adversity_quotient",
    question_text: "The measure of your ability to withstand difficult and challenging as well as turbulent situations in life without losing your head and move to the state of depression is......",
    options: ["Intelligence Quotient (IQ)", "Emotional Quotient (EQ)", "Social Quotient (SQ)", "Adversity Quotient (AQ)"],
    option_count: 4,
    correct_option: 3,
    correct_option_text: "Adversity Quotient (AQ)",
    short_explanation: "Adversity Quotient (AQ) measures your ability to withstand difficult and challenging life situations without losing your head or moving into a state of depression.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Remembering",
    has_latex: false,
    base_score: 1.0,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.0,
    scaled_score: 1.0,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 12,
    question_key: "GEN_PSY_002",
    course_code: "GEN_PSY",
    course_name: "General Psychology",
    topic_id: "psychosexual_stages",
    question_text: "According to the psychosexual theory, which stage does the child resort to playing friends and become socialble....",
    options: ["Oral stage", "Anal stage", "Phallic stage", "Latency stage"],
    option_count: 4,
    correct_option: 3,
    correct_option_text: "Latency stage",
    short_explanation: "During the latency stage, the child represses all interest in sexuality and develops social and intellectual skills .",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Remembering",
    has_latex: false,
    base_score: 1.0,
    note_reference: 1.0,
    distractor_complexity: 1.2,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.2,
    scaled_score: 1.1,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 13,
    question_key: "GEN_PSY_003",
    course_code: "GEN_PSY",
    course_name: "General Psychology",
    topic_id: "definition_of_psychology",
    question_text: "What is the best definition of psychology?",
    options: ["The study of social behavior in groups", "The scientific study of behavior and mental processes", "The study of emotions only", "The analysis of chemical reactions in the brain"],
    option_count: 4,
    correct_option: 1,
    correct_option_text: "The scientific study of behavior and mental processes",
    short_explanation: "Psychology is defined as an academic discipline that uses scientific methods to study the human mind, thoughts, emotions, and behavior.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Understanding",
    has_latex: false,
    base_score: 1.3,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.3,
    scaled_score: 1.2,
    status: "needs_review",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 14,
    question_key: "GEN_PSY_004",
    course_code: "GEN_PSY",
    course_name: "General Psychology",
    topic_id: "origin_of_psychology",
    question_text: "The term 'psychology' originates from which language?",
    options: ["Latin", "French", "Greek", "Arabic"],
    option_count: 4,
    correct_option: 2,
    correct_option_text: "Greek",
    short_explanation: "The word psychology comes from the Greek words 'psyche' meaning mind and 'logo' meaning study.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Remembering",
    has_latex: false,
    base_score: 1.0,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.0,
    scaled_score: 1.0,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  },
  {
    id: 15,
    question_key: "GEN_PSY_005",
    course_code: "GEN_PSY",
    course_name: "General Psychology",
    topic_id: "clinical_psychology",
    question_text: "Which sub-discipline of psychology focuses on diagnosing and treating mental illness?",
    options: ["Cognitive psychology", "Developmental psychology", "Clinical psychology", "Social psychology"],
    option_count: 4,
    correct_option: 2,
    correct_option_text: "Clinical psychology",
    short_explanation: "Clinical psychology involves the study, diagnosis, and treatment of psychological, mental, emotional, and behavioral disorders.",
    question_type: "mcq",
    band: 1,
    cognitive_level: "Remembering",
    has_latex: false,
    base_score: 1.0,
    note_reference: 1.0,
    distractor_complexity: 1.0,
    processing_complexity: 1.0,
    negative_stem: 1.0,
    raw_score: 1.0,
    scaled_score: 1.0,
    status: "active",
    updated_at: "2026-03-29T12:00:00Z",
  }
];

// ─── Analytics ──────────────────────────────────────────────────────────────
export type AnalyticsKPI = {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "flat";
};

export const MOCK_KPIS: AnalyticsKPI[] = [
  { label: "Active Bot Users (24h)", value: "342", change: "+12%", trend: "up" },
  { label: "Questions Served", value: "8,471", change: "+5.3%", trend: "up" },
  { label: "Global Accuracy", value: "67.2%", change: "-1.8%", trend: "down" },
  { label: "Avg. Daily Streak", value: "4.2", change: "+0.4", trend: "up" },
];

export type DailyUsage = {
  date: string;
  users: number;
  questions: number;
};

export const MOCK_DAILY_USAGE: DailyUsage[] = [
  { date: "Mon", users: 280, questions: 1420 },
  { date: "Tue", users: 310, questions: 1580 },
  { date: "Wed", users: 295, questions: 1490 },
  { date: "Thu", users: 342, questions: 1710 },
  { date: "Fri", users: 328, questions: 1650 },
  { date: "Sat", users: 190, questions: 980 },
  { date: "Sun", users: 165, questions: 840 },
];

export type LeaderboardEntry = {
  rank: number;
  user_id: string;
  telegram_username: string;
  telegram_id: string;
  questions_answered: number;
  daily_streak: number;
  accuracy: number;
  overall_skill: number;
  phase: "cold_start" | "warm" | "established";
  top_course: string;
};

export const MOCK_LEADERBOARD: LeaderboardEntry[] = [
  { rank: 1, user_id: "1001", telegram_username: "bright_kofi", telegram_id: "9812345", questions_answered: 847, daily_streak: 21, accuracy: 82.4, overall_skill: 3.8, phase: "established", top_course: "Differential Equations" },
  { rank: 2, user_id: "1002", telegram_username: "ama_scholar", telegram_id: "9823456", questions_answered: 723, daily_streak: 18, accuracy: 79.1, overall_skill: 3.4, phase: "established", top_course: "General Psychology" },
  { rank: 3, user_id: "1003", telegram_username: "yaw_dev", telegram_id: "9834567", questions_answered: 691, daily_streak: 15, accuracy: 74.8, overall_skill: 3.1, phase: "warm", top_course: "Linear Electronics" },
  { rank: 4, user_id: "1004", telegram_username: "akosua_m", telegram_id: "9845678", questions_answered: 584, daily_streak: 12, accuracy: 71.2, overall_skill: 2.9, phase: "warm", top_course: "Thermodynamics" },
  { rank: 5, user_id: "1005", telegram_username: "kwesi_eng", telegram_id: "9856789", questions_answered: 512, daily_streak: 9, accuracy: 68.5, overall_skill: 2.7, phase: "warm", top_course: "Programming in LabVIEW" },
  { rank: 6, user_id: "1006", telegram_username: "efua_sci", telegram_id: "9867890", questions_answered: 489, daily_streak: 7, accuracy: 76.3, overall_skill: 3.2, phase: "warm", top_course: "Programming in MATLAB/Simulink" },
  { rank: 7, user_id: "1007", telegram_username: "nana_b", telegram_id: "9878901", questions_answered: 434, daily_streak: 5, accuracy: 65.9, overall_skill: 2.3, phase: "cold_start", top_course: "Transformers and DC Machines" },
  { rank: 8, user_id: "1008", telegram_username: "adjoa_k", telegram_id: "9889012", questions_answered: 398, daily_streak: 3, accuracy: 72.1, overall_skill: 2.8, phase: "warm", top_course: "Workshop Technology and Practice" },
];

// ─── Reports ────────────────────────────────────────────────────────────────
export type Report = {
  id: number;
  question_id: number;
  question_key: string;
  question_text: string;
  course_name: string;
  student_username: string;
  student_reasoning: string;
  status: "open" | "resolved" | "dismissed";
  created_at: string;
};

export const MOCK_REPORTS: Report[] = [
  {
    id: 1,
    question_id: 3,
    question_key: "DIFF_EQ_003",
    question_text: "Which of the following equations is exact?",
    course_name: "Differential Equations",
    student_username: "ama_scholar",
    student_reasoning: "The correct answer should be different. Please verify.",
    status: "open",
    created_at: "2026-03-29T08:30:00Z",
  },
  {
    id: 2,
    question_id: 10,
    question_key: "LIN_ELEC_003",
    question_text: "What is the level of the voltage between the input terminals of an op-amp?",
    course_name: "Linear Electronics",
    student_username: "bright_kofi",
    student_reasoning: "Isn't the voltage supposed to be 5V? Please clarify.",
    status: "open",
    created_at: "2026-03-28T15:45:00Z",
  },
  {
    id: 3,
    question_id: 11,
    question_key: "GEN_PSY_001",
    question_text: "The measure of your ability to withstand difficult and challenging...",
    course_name: "General Psychology",
    student_username: "kwesi_eng",
    student_reasoning: "This sounds a bit too long.",
    status: "resolved",
    created_at: "2026-03-27T10:10:00Z",
  },
  {
    id: 4,
    question_id: 15,
    question_key: "GEN_PSY_005",
    question_text: "Which sub-discipline of psychology focuses on diagnosing and treating mental illness?",
    course_name: "General Psychology",
    student_username: "akosua_m",
    student_reasoning: "Just checking if the answer is accurate.",
    status: "dismissed",
    created_at: "2026-03-26T12:00:00Z",
  },
];

// ─── Current User ───────────────────────────────────────────────────────────
export const MOCK_CURRENT_USER = {
  staff_user_id: 1,
  email: "kwame.asante@staff.adarkwa.edu",
  display_name: "Kwame Asante",
  roles: ["super_admin"],
  must_change_password: false,
};

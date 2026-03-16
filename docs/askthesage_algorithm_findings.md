# Question Selection Algorithm & Time Allocation in AskTheSage

Based on a review of the `AskTheSage` codebase, here is a detailed breakdown of how the bot selects questions for quizzes and allocates time to each question.

## 1. Question Selection Algorithm
The bot uses a sophisticated Adaptive Learning System (`UniversalQuestionSelector`) to select questions for quizzes, with a legacy fallback mechanism if adaptive mode is disabled. 

### a) Adaptive Mode (Primary)
When `ADAPTIVE_QUIZ_ENABLED` is true, the `AdaptiveQuizService` orchestrates question selection:

- **New Users / No History:** 
  - If a user has no prior performance history, the system checks the proportion of scored questions in the course pool.
  - If >80% of questions are scored, it uses a **'difficulty_ramp'** strategy: It allocates 25% easy questions, 25% hard questions, and 50% medium questions to evaluate the user's initial skill level. The difficulty bands are defined as easy (≤1.5), medium (1.5-3.0), and hard (>3.0).
  - Otherwise, it falls back to a **'random'** strategy, simply shuffling available questions.
  
- **Users with Performance History:**
  - The system estimates a `user_skill_level` (0.0 - 1.0) based on the last 10 correct attempts, weighting recent successes more heavily.
  - Questions are evaluated and given a priority score based on several criteria defined in `UniversalQuestionSelector`:
    1. **Weakness (100+ weight):** Prioritizes questions the user answered incorrectly in the past. Higher error rates increase the score further.
    2. **New Questions (50 weight):** Questions the user hasn't attempted yet. This is weighted by an "appropriateness_multiplier" which penalizes questions whose relative difficulty is too far from the user's estimated skill level.
    3. **SRS Due (30+ weight):** Spaced Repetition System logic prioritizes review based on a sequence of intervals (`[1, 3, 7, 14, 30...]` days). Overdue questions get an extra bonus based on how many days overdue they are.
    4. **Difficulty Progression (20+ weight):** Prioritizes questions that are just slightly above the user's skill level, offering a sweet spot for a challenge.
    5. **Random Review (5 weight):** Lowest priority bucket, primarily for questions the user already knows well.
  - Finally, a distribution control mechanism enforces target percentages for each type: e.g., 60% weakness questions, 25% new, 15% SRS review (this is configurable per course).

### b) Legacy Mode (Fallback)
If adaptive mode is disabled, the `start_new_quiz` function runs a simpler scoring mechanism:
- It queries the user's latest attempt for each question:
  - `100` points for incorrectly answered questions.
  - `50` points for unattempted questions.
  - `1` point for correctly answered questions.
- It sorts the questions by this score descending and selects the top `quiz_length` questions.

---

## 2. Time Allocation
The time allocated to answer each question is calculated dynamically based on its difficulty score using the `calculate_question_time_limit` function in `src/services/scoring_service.py`.

The `TIME_LIMIT_CONFIG` (in `src/config.py`) defines a **base time of 45 seconds** and a tier-based multiplier system:
- **Difficulty Score ≤ 1.5:** 1.0x multiplier (45 seconds)
- **Difficulty Score ≤ 3.0:** 1.5x multiplier (68 seconds)
- **Difficulty Score ≤ 4.5:** 2.0x multiplier (90 seconds)
- **Difficulty Score ≤ 6.75:** 2.5x multiplier (113 seconds)

**Key behaviors:**
- Higher scores (above 6.75) use the maximum defined multiplier (2.5x).
- Unscored questions fall back to the base time of 45 seconds.
- The final allocated time limit is calculated by multiplying the base time by the appropriate multiplier and rounding to the nearest whole second.
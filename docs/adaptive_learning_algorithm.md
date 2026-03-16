# Adaptive Learning Algorithm v2 — Full Specification

## 1. Student Skill Model

The old system used a single `user_skill_level` (0.0–1.0) derived from the last 10 attempts. The new model is **multi-dimensional**.

### 1.1 Per-Student State Object

For each `(student, course)` pair, maintain:

```json
{
  "student_id": "abc123",
  "course_id": "diff_eq_101",
  "overall_skill": 2.5,
  "topic_skills": {
    "separable_differential_equation": 3.1,
    "homogeneous_differential_equation": 1.8
  },
  "cognitive_profile": {
    "Remembering": 3.5,
    "Understanding": 3.0,
    "Applying": 2.2,
    "Analyzing": 1.5,
    "Evaluating": 1.0
  },
  "processing_profile": {
    "single_step": 3.2,
    "multi_step": 2.0,
    "symbolic": 1.8,
    "visual": 1.5
  },
  "misconception_flags": [
    {
      "topic_id": "separable_differential_equation",
      "question_id": "q_042",
      "selected_distractor": "option_a",
      "times_selected": 2,
      "resolved": false
    }
  ],
  "phase": "cold_start",
  "total_quizzes_completed": 0,
  "total_attempts": 0,
  "exam_date": null
}
```

All skill values live on the **same 1.0–5.0 scale** as your `scaled_score`, making comparison direct.

### 1.2 Skill Update Formula (Elo-Inspired)

After every attempt, update the relevant skill dimensions using the same core formula:

$$\text{expected} = \frac{1}{1 + e^{\,(d - s)}}$$

where \( d \) = question's `scaled_score`, \( s \) = student's current skill estimate in that dimension.

$$\text{update} = K \times (\text{actual} - \text{expected})$$

where `actual` = 1.0 if correct, 0.0 if wrong.

$$s_{\text{new}} = \text{clamp}(s + \text{update},\; 1.0,\; 5.0)$$

**K-values** (learning rate) differ by dimension to control volatility:

| Dimension | K | Rationale |
|---|---|---|
| `topic_skills[topic_id]` | 0.5 | Most granular, updates fastest — small pool of questions per topic |
| `cognitive_profile[level]` | 0.3 | Cross-topic, more data points, update moderately |
| `processing_profile[type]` | 0.3 | Same as cognitive — cross-topic aggregate |
| `overall_skill` | 0.2 | Slowest — represents global ability, shouldn't swing wildly |

### 1.3 Time-Weighted Performance Classification

Every attempt is classified into one of six categories using `time_ratio`:

$$\text{time\_ratio} = \frac{\text{time\_taken\_seconds}}{\text{time\_allocated\_seconds}}$$

| Correctness | time\_ratio < 0.5 (Fast) | 0.5 ≤ ratio < 0.85 (Normal) | ratio ≥ 0.85 (Slow) |
|---|---|---|---|
| **Correct** | `MASTERED` | `LEARNED` | `DEVELOPING` |
| **Wrong** | `CARELESS_OR_MISCONCEPTION` | `KNOWLEDGE_GAP` | `SIGNIFICANT_GAP` |

This classification modifies the K-value per attempt:

```python
K_MODIFIER = {
    "MASTERED":                  1.2,   # strong signal, boost update
    "LEARNED":                   1.0,   # standard
    "DEVELOPING":                0.7,   # they got it but struggled
    "CARELESS_OR_MISCONCEPTION": 0.5,   # might not reflect true skill
    "KNOWLEDGE_GAP":             1.0,   # standard negative signal
    "SIGNIFICANT_GAP":           1.2,   # strong negative signal
}

effective_K = base_K * K_MODIFIER[classification]
```

**Special rule for `CARELESS_OR_MISCONCEPTION`:** If `distractor_complexity ≥ 1.5` on that question, reclassify as `MISCONCEPTION` and log it to `misconception_flags`. If `distractor_complexity < 1.5`, keep as `CARELESS` — lower K dampens the penalty since it likely wasn't a real gap.

### 1.4 Skill Decay

If a student hasn't practiced a topic in a while, their skill drifts toward the course average:

```python
days_inactive = days_since_last_attempt(student, topic)
if days_inactive > 3:
    decay = 0.02 * (days_inactive - 3)  # starts after 3 days
    decay = min(decay, 0.5)             # cap at 0.5 drop
    topic_skills[topic] = max(
        1.0,
        topic_skills[topic] - decay
    )
```

This is applied **lazily** — compute it when selecting questions for a new quiz, not on a cron job.

---

## 2. Phase Detection

The student's `phase` determines weight profiles, quiz composition rules, and selection strategies.

```python
def get_phase(student_state):
    q = student_state["total_quizzes_completed"]
    if q <= 2:
        return "cold_start"      # Diagnostic
    elif q <= 8:
        return "warm"            # Calibration
    else:
        return "established"     # Full personalization
```

---

## 3. Question Selection Algorithm

### 3.1 Candidate Pool

Start with all questions in the course. Apply hard filters:

```python
def get_candidates(course_questions, student_state, quiz_length):
    candidates = []
    for q in course_questions:
        # Never repeat a question within the same session
        if q.id in current_session_question_ids:
            continue
        # Never show a question answered correctly in last 24h
        if q.last_correct_attempt and hours_since(q.last_correct_attempt) < 24:
            continue
        candidates.append(q)
    return candidates
```

### 3.2 Priority Scoring

For each candidate question, compute six component scores and a weighted sum.

#### Component 1 — Weakness Score

```python
def weakness_score(q, student_state):
    history = get_attempts(student_state.id, q.id)
    if not history:
        return 0.0

    wrong = sum(1 for a in history if not a.is_correct)
    total = len(history)
    if wrong == 0:
        return 0.0

    error_rate = wrong / total
    days_since_last_wrong = days_since(last_wrong_attempt(history))
    recency = math.exp(-days_since_last_wrong / 7.0)

    return error_rate * recency  # 0.0 to 1.0
```

#### Component 2 — New Question Score

```python
def new_question_score(q, student_state):
    if has_been_attempted(student_state.id, q.id):
        return 0.0

    topic_skill = student_state.topic_skills.get(q.topic_id, 2.5)
    target = topic_skill + 0.5  # slightly above current skill

    # How appropriate is this question's difficulty for the student?
    distance = abs(q.scaled_score - target)
    appropriateness = max(0.1, 1.0 - distance / 4.0)

    return appropriateness  # 0.1 to 1.0
```

#### Component 3 — SRS Score

```python
SRS_INTERVALS = [0, 1, 3, 7, 14, 30, 60]  # days, index = box number

def srs_score(q, student_state):
    box = get_srs_box(student_state.id, q.id)
    if box is None:
        return 0.0  # never answered correctly, handled by weakness/new

    interval = SRS_INTERVALS[min(box, len(SRS_INTERVALS) - 1)]
    days_since = days_since_last_correct(student_state.id, q.id)

    if days_since < interval:
        return 0.0  # not due yet

    overdue_ratio = min(2.0, days_since / max(interval, 1))
    return 0.5 + 0.5 * overdue_ratio  # 0.5 to 1.5
```

**SRS box transitions:**
- Correct → box + 1 (max 6)
- Wrong → box = 0
- If overdue by > 2× interval → box = max(0, box - 1) before presenting

#### Component 4 — Zone of Proximal Development (ZPD)

```python
def zpd_score(q, student_state):
    topic_skill = student_state.topic_skills.get(q.topic_id, 2.5)
    sweet_spot = topic_skill + 0.5  # slightly above skill

    distance = abs(q.scaled_score - sweet_spot)
    score = max(0.0, 1.0 - distance / 3.0)
    return score  # 0.0 to 1.0
```

#### Component 5 — Topic Coverage

```python
def coverage_score(q, selected_so_far, quiz_length):
    topic_count = sum(
        1 for s in selected_so_far if s.topic_id == q.topic_id
    )
    max_per_topic = math.ceil(quiz_length / 3)
    if topic_count >= max_per_topic:
        return -10.0  # hard penalty, effectively blocks selection

    return 1.0 - (topic_count / max_per_topic)  # 1.0 to 0.0
```

#### Component 6 — Misconception Targeting

```python
def misconception_score(q, student_state):
    for flag in student_state.misconception_flags:
        if flag["topic_id"] == q.topic_id and not flag["resolved"]:
            if q.distractor_complexity >= 1.2:
                return 1.5  # high priority
            return 0.8
    return 0.0
```

### 3.3 Dynamic Weights

```python
WEIGHT_PROFILES = {
    "cold_start": {
        "weakness":      0.10,
        "new":           0.40,
        "srs":           0.00,
        "zpd":           0.20,
        "coverage":      0.25,
        "misconception": 0.05
    },
    "warm": {
        "weakness":      0.30,
        "new":           0.20,
        "srs":           0.10,
        "zpd":           0.15,
        "coverage":      0.12,
        "misconception": 0.13
    },
    "established": {
        "weakness":      0.25,
        "new":           0.10,
        "srs":           0.20,
        "zpd":           0.13,
        "coverage":      0.10,
        "misconception": 0.22
    }
}
```

**Exam proximity modifier** (applied multiplicatively if `exam_date` is set):

```python
def apply_exam_modifier(weights, days_to_exam):
    if days_to_exam is None or days_to_exam > 14:
        return weights  # no change

    w = weights.copy()
    if days_to_exam <= 7:
        w["weakness"]      *= 1.5
        w["srs"]           *= 1.5
        w["new"]           *= 0.3
        w["misconception"] *= 1.3
    elif days_to_exam <= 14:
        w["weakness"]      *= 1.3
        w["srs"]           *= 1.2
        w["new"]           *= 0.6

    # Re-normalize to sum to 1.0
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}
```

### 3.4 Final Selection

```python
def select_questions(course_questions, student_state, quiz_length):
    candidates = get_candidates(course_questions, student_state, quiz_length)
    phase = get_phase(student_state)
    weights = WEIGHT_PROFILES[phase]
    weights = apply_exam_modifier(weights, days_to_exam(student_state))

    selected = []

    for _ in range(quiz_length):
        scored = []
        for q in candidates:
            priority = (
                weights["weakness"]      * weakness_score(q, student_state)
              + weights["new"]           * new_question_score(q, student_state)
              + weights["srs"]           * srs_score(q, student_state)
              + weights["zpd"]           * zpd_score(q, student_state)
              + weights["coverage"]      * coverage_score(q, selected, quiz_length)
              + weights["misconception"] * misconception_score(q, student_state)
            )
            scored.append((q, priority))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Top-3 weighted random pick to prevent deterministic quizzes
        top_n = scored[:3]
        total_priority = sum(p for _, p in top_n)
        if total_priority <= 0:
            chosen = random.choice(candidates)
        else:
            probs = [p / total_priority for _, p in top_n]
            chosen = random.choices(
                [q for q, _ in top_n], weights=probs, k=1
            )[0]

        selected.append(chosen)
        candidates.remove(chosen)

    return selected
```

### 3.5 Cold Start — First Quiz Override

On the very first quiz (0 history), bypass the priority system entirely:

```python
def cold_start_selection(course_questions, quiz_length):
    topics = group_by(course_questions, key="topic_id")
    selected = []

    # Phase 1: one question per topic (round-robin), prefer band 1-2
    for topic_id, questions in topics.items():
        easy = [q for q in questions if q.band <= 2]
        if easy:
            selected.append(random.choice(easy))
        else:
            selected.append(random.choice(questions))
        if len(selected) >= quiz_length:
            break

    # Phase 2: fill remaining with difficulty ramp
    remaining = quiz_length - len(selected)
    if remaining > 0:
        pool = [q for q in course_questions if q not in selected]
        easy   = [q for q in pool if q.band <= 2]
        medium = [q for q in pool if q.band == 3]
        hard   = [q for q in pool if q.band >= 4]

        allocation = {
            "easy":   round(remaining * 0.40),
            "medium": round(remaining * 0.40),
            "hard":   remaining - round(remaining * 0.40) - round(remaining * 0.40)
        }

        for bucket, count in [("easy", easy), ("medium", medium), ("hard", hard)]:
            sample = random.sample(count, min(allocation[bucket], len(count)))
            selected.extend(sample)

    return selected[:quiz_length]
```

---

## 4. Quiz Ordering

Once questions are selected, order them within the quiz to optimize engagement:

```python
def order_quiz(selected_questions, student_state):
    easy   = [q for q in selected_questions if q.scaled_score <= student_overall_skill(student_state)]
    medium = [q for q in selected_questions if student_overall_skill(student_state) < q.scaled_score <= student_overall_skill(student_state) + 1.0]
    hard   = [q for q in selected_questions if q.scaled_score > student_overall_skill(student_state) + 1.0]

    random.shuffle(easy)
    random.shuffle(medium)
    random.shuffle(hard)

    # Warm-up → Challenge → Cool-down
    n = len(selected_questions)
    warmup_count   = max(1, round(n * 0.2))
    cooldown_count = max(1, round(n * 0.15))

    ordered = []
    ordered.extend(easy[:warmup_count])         # start confident
    ordered.extend(hard)                         # hardest in the middle
    ordered.extend(medium)                       # transition
    ordered.extend(easy[warmup_count:])          # remaining easy
    # move one easy to the end as cooldown
    if len(ordered) > cooldown_count:
        cooldown = [q for q in ordered if q in easy][-cooldown_count:]
        for q in cooldown:
            ordered.remove(q)
            ordered.append(q)

    return ordered
```

This follows the **Warm-up → Challenge → Cool-down** pattern that keeps students from quitting after a hard opener and ending on a frustrating note.

---

## 5. Option Arrangement Strategy

### 5.1 Non-LaTeX Questions

```python
def arrange_options_non_latex(question):
    options = question.options.copy()
    random.shuffle(options)
    arrangement_hash = "-".join(
        [chr(65 + question.options.index(opt)) for opt in options]
    )  # e.g., "C-A-D-B"
    return options, arrangement_hash
```

Shuffle every single time. No exceptions. Store `arrangement_hash` on the attempt.

### 5.2 LaTeX Questions

```python
def arrange_options_latex(question, student_state):
    previous_configs = get_previous_config_indices(
        student_state.id, question.id
    )
    available = set(range(question.option_count)) - set(previous_configs)

    if not available:
        # All configs used — restart, but avoid the most recent
        available = set(range(question.option_count)) - {previous_configs[-1]}

    config_index = random.choice(list(available))
    return config_index
```

### 5.3 Position Memorization Detection

```python
def detect_position_memorization(student_id, question_id):
    attempts = get_attempts(student_id, question_id)
    if len(attempts) < 2:
        return False

    # Check: correct with one arrangement, wrong with another
    correct_arrangements = {a.arrangement_hash for a in attempts if a.is_correct}
    wrong_arrangements   = {a.arrangement_hash for a in attempts if not a.is_correct}

    if correct_arrangements and wrong_arrangements:
        # Different arrangements led to different outcomes
        return True
    return False
```

If detected → reset SRS box to 0 for that question, override mastery classification to `DEVELOPING` at best.

---

## 6. Misconception Detection and Resolution

### 6.1 Logging Misconceptions

```python
def process_wrong_answer(attempt, question, student_state):
    if question.question_type != "MCQ":
        return

    classification = classify_attempt(attempt)  # from Section 1.3

    if classification in ("CARELESS_OR_MISCONCEPTION", "KNOWLEDGE_GAP", "SIGNIFICANT_GAP"):
        if question.distractor_complexity >= 1.2:
            existing = find_misconception_flag(
                student_state, question.topic_id, question.id
            )
            if existing:
                existing["times_selected"] += 1
            else:
                student_state.misconception_flags.append({
                    "topic_id": question.topic_id,
                    "question_id": question.id,
                    "selected_distractor": attempt.selected_option_id,
                    "times_selected": 1,
                    "resolved": False
                })
```

### 6.2 Resolving Misconceptions

A misconception is marked `resolved: True` when:

```python
def check_misconception_resolution(student_state, question, attempt):
    for flag in student_state.misconception_flags:
        if flag["question_id"] == question.id and attempt.is_correct:
            # Must get it right twice with different arrangements
            correct_attempts = get_correct_attempts_with_different_arrangements(
                student_state.id, question.id
            )
            if len(correct_attempts) >= 2:
                flag["resolved"] = True
```

Two correct answers with different option arrangements = genuine understanding, not position recall.

---

## 7. Self-Improving Mechanisms

### 7.1 Empirical Difficulty Calibration

```python
def recalibrate_question_difficulty(question, all_student_attempts):
    """Run periodically (e.g., weekly or after every 30 attempts on a question)"""
    attempts = [a for a in all_student_attempts if a.question_id == question.id]

    if len(attempts) < 10:
        return  # not enough data

    success_rate = sum(1 for a in attempts if a.is_correct) / len(attempts)
    empirical_difficulty = 1.0 + (1.0 - success_rate) * 4.0  # map to 1-5

    divergence = abs(empirical_difficulty - question.scaled_score)

    if divergence > 1.0:
        flag_for_review(
            question.id,
            reason=f"Scored difficulty: {question.scaled_score}, "
                   f"Empirical: {empirical_difficulty:.1f}, "
                   f"Divergence: {divergence:.1f}",
            suggestion="Re-evaluate scoring parameters or question quality"
        )
```

This doesn't auto-change scores — it flags questions where your rubric-based score diverges significantly from real-world performance, letting you refine the scoring prompts over time.

### 7.2 Distractor Analytics (Population-Level)

```python
def analyze_distractor_patterns(question, all_attempts):
    """Flag questions where one distractor is selected disproportionately"""
    wrong_attempts = [a for a in all_attempts if not a.is_correct]
    if len(wrong_attempts) < 15:
        return

    distractor_counts = Counter(a.selected_option_id for a in wrong_attempts)
    total_wrong = len(wrong_attempts)

    for option_id, count in distractor_counts.items():
        if count / total_wrong > 0.60:
            flag_for_review(
                question.id,
                reason=f"Distractor '{option_id}' selected by "
                       f"{count}/{total_wrong} ({count/total_wrong:.0%}) "
                       f"of wrong answers",
                suggestion="Common misconception detected — consider "
                           "adding targeted explanation or related questions"
            )
```

### 7.3 Time Allocation Refinement

```python
def refine_time_allocation(question, all_attempts):
    """Adjust time limits based on actual student performance"""
    times = [a.time_taken_seconds for a in all_attempts if a.question_id == question.id]
    if len(times) < 15:
        return

    median_time = sorted(times)[len(times) // 2]
    current_limit = calculate_question_time_limit(question.scaled_score)

    if median_time < current_limit * 0.4:
        flag_for_review(
            question.id,
            reason=f"Median completion time ({median_time}s) is <40% of "
                   f"limit ({current_limit}s)",
            suggestion="Question may be over-timed or easier than scored"
        )
    elif sum(1 for t in times if t >= current_limit * 0.95) / len(times) > 0.30:
        flag_for_review(
            question.id,
            reason=f">30% of students used >95% of time limit",
            suggestion="Question may be under-timed or harder than scored"
        )
```

---

## 8. Updated Time Allocation

Keep your existing tier system but use the sub-scores for precision:

```python
def calculate_question_time_limit(question):
    BASE_TIME = 45

    # Primary: scaled_score tiers (existing logic)
    if question.scaled_score <= 1.5:
        multiplier = 1.0
    elif question.scaled_score <= 3.0:
        multiplier = 1.5
    elif question.scaled_score <= 4.5:
        multiplier = 2.0
    else:
        multiplier = 2.5

    # Bonus: processing complexity adds time for computation-heavy Qs
    if question.processing_complexity >= 1.4:  # symbolic/algebraic
        multiplier += 0.25
    if question.processing_complexity >= 1.5:  # visual/diagrammatic
        multiplier += 0.25

    # Bonus: multi-reference questions need more reading time
    if question.note_reference >= 1.5:
        multiplier += 0.15

    return round(BASE_TIME * multiplier)
```

---

## 9. Complete Flow Summary

```text
Student opens quiz
       │
       ▼
┌─────────────────┐
│  Get Phase       │ ← total_quizzes_completed
│  (cold/warm/est) │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐     ┌──────────────────┐
│ Cold Start?          │─Yes─▶│ cold_start_       │
│ (quizzes ≤ 2)       │     │ selection()       │
└────────┬────────────┘     └──────────────────┘
         │ No
         ▼
┌─────────────────────┐
│ Apply skill decay    │ ← lazy, per-topic
│ for inactive topics  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Get candidates       │ ← hard filters (no repeats, 24h cooldown)
│ Score each with 6    │
│ weighted components  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Select quiz_length   │ ← top-3 weighted random per slot
│ questions            │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Order: warm-up →     │
│ challenge → cooldown │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Arrange options      │ ← shuffle (non-LaTeX) or config cycle (LaTeX)
│ Calculate time limit │
└────────┬────────────┘
         │
         ▼
     Student takes quiz
         │
         ▼ (per question)
┌─────────────────────┐
│ Record attempt       │ ← selected_option_id, time, arrangement
│ Classify performance │ ← MASTERED/LEARNED/.../SIGNIFICANT_GAP
│ Update skill model   │ ← Elo update on 4 dimensions
│ Update SRS box       │
│ Check misconception  │
│ Check position memo  │
└─────────────────────┘
         │
         ▼ (periodic, background)
┌─────────────────────┐
│ Recalibrate          │ ← empirical difficulty vs scored
│ Distractor analytics │ ← population-level patterns
│ Time refinement      │
└─────────────────────┘
```

---

This gives you all four goals in balance — SRS handles retention, weakness targeting closes gaps, ZPD + quiz ordering maintains engagement, and the misconception system catches and corrects deep misunderstandings. The self-improving layer ensures the system gets better as you accumulate data.

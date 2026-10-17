# PHASE 9B.8.4 IMPLEMENTATION REPORT
## Deterministic Personalized Exercise Recommendation Foundation

**Status**: Implemented & Verified  
**Date**: September 14, 2026  
**Scope Boundary**: Deterministic Candidate Generation & Ranking Decision Engine (Zero Gemini/LLM, Zero Vector DB, Zero ML)  

---

### 1. Executive Summary

Phase 9B.8.4 delivers the deterministic, catalog-backed exercise recommendation decision engine for the Fitness App. It establishes the computational bridge between:
1. The **100-exercise knowledge catalog** (Phase 9B.8.2)
2. The **exercise relationship graph** (Phase 9B.8.3)
3. The **authoritative corrective guidance mappings** (Phase 9B.8.3)

and structured user constraints (fitness goals, available equipment, environment, fitness level, and technique issues).

The engine operates strictly as a decision and candidate generation layer:
- It enforces strict binary hard gates (equipment compatibility, environment, exclusions, canonical CV support).
- It generates candidates strictly scoped by request intent (`GENERAL`, `PROGRESSION`, `REGRESSION`, `SUBSTITUTION`, `COMPLEMENT`, `CORRECTIVE`).
- It scores candidates using mathematically normalized signals ($[0.0, 1.0]$) and intent-specific weight profiles that sum to exactly $1.00$, producing final scores bounded in $[0.0, 100.0]$.
- It provides intent-aware diversity post-processing, stable multi-tiered tie-breaking, and deterministic templated explanations of positive signals.
- It exposes a read-only endpoint (`POST /api/v1/exercises/recommendations`) with zero Firestore persistence, zero external network calls, and zero LLM dependencies.

---

### 2. Files Created & Modified

#### Files Created
1. `backend/app/services/exercise_recommendation_service.py`: Core recommendation decision engine providing strict candidate generation, hard eligibility filtering, bounded mathematical scoring, deterministic reason generation, intent-aware diversity, and stable tie-breaking.
2. `backend/app/api/v1/endpoints/exercise_recommendations.py`: Read-only FastAPI endpoint exposing `POST /api/v1/exercises/recommendations`.
3. `backend/tests/test_exercise_recommendations.py`: Comprehensive test suite containing 39 tests covering the 16 mandatory test plan corrections, 15 concrete evaluation scenarios, multi-equipment subset semantics, hard gate boundaries, tie-breaking, non-medical safeguards, and API endpoint integration.
4. `PHASE_9B_8_4_IMPLEMENTATION_REPORT.md`: This document.

#### Files Modified
1. `backend/app/schemas/exercise.py`: Added `RecommendationIntent`, `ExerciseRecommendationRequest`, `ExerciseRecommendationNode`, and updated `ExerciseRecommendationResponse` maintaining 100% backward compatibility with Phase 9B.8.1 schemas.
2. `backend/app/schemas/__init__.py`: Exported new recommendation models and enums.
3. `backend/app/api/v1/router.py`: Mounted `exercise_recommendations_router` under prefix `/exercises/recommendations` before `/exercises` to avoid route shadowing.
4. `PHASE_9B_8_4_PLAN.md`: Aligned evaluation scenario candidate lists with authoritative catalog fields.

#### Files Intentionally NOT Touched
- `backend/app/services/form_heuristics.py` (authoritative CV heuristics preserved)
- `backend/app/seeds/catalog/*.py` (all 10 catalog modules preserved)
- `backend/app/seeds/corrective_mappings.py` (Phase 9B.8.3 mappings preserved)
- `backend/app/services/exercise_relationship_service.py` (consumed as-is without duplication)
- `backend/app/services/llm_client.py` (zero Gemini/LLM calls)
- Phase 3 repositories and schemas (`exercise_repository.py`, etc.)
- All frontend UI source code (`src/**/*`)

---

### 3. Candidate-Generation Behavior by Intent

The recommendation engine strictly isolates candidate generation before any scoring occurs:

| Intent | Candidate Generation Source | Scope Isolation Enforcement |
|---|---|---|
| **`GENERAL`** | Entire 100-exercise catalog (`CATALOG_EXERCISES`) | Open library exploration across eligible catalog exercises. |
| **`PROGRESSION`** | `ExerciseRelationshipService.get_progressions(source_exercise_id)` | **Strict**: Regressions, substitutions, and complements are completely barred from entry. |
| **`REGRESSION`** | `ExerciseRelationshipService.get_regressions(source_exercise_id)` | **Strict**: Progressions, substitutions, and complements are completely barred from entry. |
| **`SUBSTITUTION`** | `ExerciseRelationshipService.get_substitutions(source_exercise_id)` | **Strict**: Only valid movement substitutions enter candidate pool. |
| **`COMPLEMENT`** | `ExerciseRelationshipService.get_complements(source_exercise_id)` | **Strict**: Only valid accessory/complementary exercises enter candidate pool. |
| **`CORRECTIVE`** | `ExerciseRelationshipService.get_corrective_exercises(source_exercise_id, corrective_issue_id)` | **Strict**: Source must be one of the canonical 5 CV exercises; issue must exist in Phase 9B.8.3 normalization mappings. Returns exclusively curated corrective drills. |

---

### 4. Hard Eligibility Gates (Binary Filters)

Hard constraints act as strict binary gates ($0$ or $1$). An exercise failing any active hard filter is immediately excluded:

1. **Non-Deprecated Catalog Membership**: Exercise must exist in `CATALOG_BY_ID` and not be marked `isDeprecated`.
2. **Explicit Exclusions**: `exercise.id not in request.excludedExerciseIds`.
3. **Available Equipment Gate**:
   $$\text{exercise.equipment} \subseteq \text{availableEquipment}$$
   If an exercise requires multiple items (e.g. `["barbell", "bench"]`) and the user provides only `["barbell"]`, the exercise is **ineligible**.
4. **Excluded Equipment Gate**:
   $$\text{exercise.equipment} \cap \text{excludedEquipment} = \emptyset$$
5. **Environment Compatibility Gate**:
   `request.environment in exercise.targetEnvironments or "anywhere" in exercise.targetEnvironments`.
6. **Canonical CV Gate (`form_analysis_supported_only = True`)**:
   Restricts candidates strictly to the canonical 5 CV exercises (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`). No inference from exercise similarity.

> [!IMPORTANT]
> **Zero Equipment Double-Counting**: Equipment compatibility is solely a hard eligibility gate. It is completely removed from all soft scoring profiles.

---

### 5. Exact Scoring Formulas & Weight Profiles

All individual signals are normalized to $[0.0, 1.0]$. The final candidate score is computed as:
$$\text{Score} = 100.0 \times \sum_{i} (w_i \times S_i) \quad \text{where } \sum w_i = 1.00 \text{ and } \text{Score} \in [0.0, 100.0]$$

#### Normalized Signal Definitions
- **Goal Alignment ($S_{\text{goal}} \in [0.0, 1.0]$)**: $1.0$ if `targetGoal in exercise.targetGoals` else $0.20$. Neutral ($1.0$) if unspecified.
- **Target Muscle Overlap ($S_{\text{muscle}} \in [0.0, 1.0]$)**:
  $$S_{\text{muscle}} = 0.75 \times \frac{|\text{targetMuscles} \cap \text{primaryMuscles}|}{\max(1, |\text{primaryMuscles}|)} + 0.25 \times \frac{|\text{targetMuscles} \cap \text{secondaryMuscles}|}{\max(1, |\text{secondaryMuscles}|)}$$
  Clamped to $[0.0, 1.0]$. If overlap is 0, soft baseline is $0.10$. Neutral ($1.0$) if unspecified. Muscle mismatch never hard-excludes.
- **Movement Pattern Match ($S_{\text{pattern}} \in [0.0, 1.0]$)**: $1.0$ if exact match else $0.0$. Neutral ($1.0$) if unspecified.
- **Difficulty Suitability ($S_{\text{diff}} \in [0.0, 1.0]$)**: Exact match $= 1.0$; 1 level away $= 0.50$; 2 levels away $= 0.0$. Neutral ($1.0$) if unspecified.
- **Category & Laterality Fit ($S_{\text{cat\_lat}} \in [0.0, 1.0]$)**: $0.60 S_{\text{cat}} + 0.40 S_{\text{lat}}$.
- **Relationship Edge Priority ($S_{\text{edge}} \in [0.0, 1.0]$)**: Priority 1 $\rightarrow 1.0$; Priority 2 $\rightarrow 0.50$; Priority 3+ $\rightarrow 1.0 / \text{priority}$.
- **Corrective Match Priority ($S_{\text{corr}} \in [0.0, 1.0]$)**: Priority 1 $\rightarrow 1.0$; Priority 2 $\rightarrow 0.70$.

#### Intent-Specific Scoring Profiles
- **Profile A: General Discovery (`intent = GENERAL`)**
  - Goal: $0.30$
  - Muscle: $0.30$
  - Movement Pattern: $0.20$
  - Difficulty: $0.10$
  - Category / Laterality: $0.10$
  - **Sum = 1.00**
- **Profile B: Relationship-Guided (`intent` $\in$ {`PROGRESSION`, `REGRESSION`, `SUBSTITUTION`, `COMPLEMENT`})**
  - Relationship Edge: $0.35$
  - Goal: $0.25$
  - Muscle: $0.25$
  - Difficulty: $0.15$
  - **Sum = 1.00**
- **Profile C: Corrective Guidance (`intent = CORRECTIVE`)**
  - Corrective Match: $0.50$
  - Movement Pattern: $0.25$
  - Difficulty: $0.15$
  - Muscle: $0.10$
  - **Sum = 1.00**

---

### 6. State A / B / C Handling

The engine eliminates all hidden assumptions and arbitrary bodyweight fallbacks:

- **State A (Valid Request)**:
  - Valid discovery or relationship query returns ranked candidates meeting eligibility criteria.
- **State B (Insufficient Data for Intent)**:
  - Missing `source_exercise_id` for relationship intents or missing `source_exercise_id`/`corrective_issue_id` for corrective intent.
  - Returns `total_eligible = 0`, `candidates = []`.
  - Diagnostics: Explicit message explaining the missing parameter (e.g. `"Intent 'progression' requires 'source_exercise_id'."`).
  - Zero fabricated bodyweight movements.
- **State C (Conflicting Hard Constraints)**:
  - Hard filters eliminate all candidates (e.g. `environment="outdoor"` + `availableEquipment=["barbell"]`).
  - Returns `total_eligible = 0`, `candidates = []`.
  - `conflicting_filters`: Detailed breakdown of which filters eliminated candidates (e.g. `"Equipment mismatch eliminated 12 candidate(s)..."`).

---

### 7. Intent-Aware Diversity & Stable Tie-Breaking

#### Diversity Policy
- **General Discovery**: Enabled by default (capped at max 2 candidates per movement pattern in top-N).
  - *Exception*: If a specific `movementPattern` was explicitly requested, capping for that pattern is disabled.
- **Relationship-Guided Intents**: Diversity post-processing is **disabled**. Graph edges are already semantically bounded and must never be pruned.
- **Corrective Guidance Intent**: Diversity post-processing is **disabled**. Curated drills must never be removed merely because they share a movement pattern.

#### Deterministic Tie-Breaking Sequence
1. **Tier 1**: `score` descending (rounded to 2 decimal places)
2. **Tier 2**: `priority` ascending (Priority 1 before Priority 2)
3. **Tier 3**: `exerciseType == "compound"` before `"isolation"`
4. **Tier 4**: Canonical `exerciseId` ascending alphabetical

Results are 100% stable and byte-for-byte identical across repeated invocations.

---

### 8. Deterministic Score Reasons

Reasons explain meaningful positive signals using concise deterministic string templates:
- Goal match: `"Matches selected fitness goal: {goal}"`
- Movement pattern match: `"Matches requested movement pattern: {pattern}"`
- Muscle overlap: `"Targets {count} requested muscle group(s): {muscles}"`
- Difficulty fit: `"Suitable for selected fitness level: {level}"`
- Relationship edge: `"{RelationshipType} from {source_exercise_name}"`
- Corrective issue: `"Corrective candidate for {issue_id}: {rationale}"`

All reasons are validated against `PROHIBITED_MEDICAL_PHRASES` at the schema layer. Zero LLM involvement; zero medical claims.

---

### 9. API Contract

- **Endpoint**: `POST /api/v1/exercises/recommendations`
- **Read-Only**: Zero database writes, zero query logging, zero PII persistence.
- **Mounted**: Mounted before `/exercises` router to avoid route shadowing.
- **Sample Request**:
  ```json
  {
    "intent": "corrective",
    "source_exercise_id": "ex_squat",
    "corrective_issue_id": "insufficient_depth"
  }
  ```
- **Sample Response**:
  ```json
  {
    "intent": "corrective",
    "total_evaluated": 3,
    "total_eligible": 3,
    "returned_count": 3,
    "candidates": [
      {
        "exercise_id": "ex_box_squat",
        "name": "Barbell Box Squat",
        "movement_pattern": "squat",
        "exercise_type": "compound",
        "difficulty": "beginner",
        "equipment": ["barbell", "box_platform"],
        "primary_muscles": ["quadriceps", "glutes"],
        "score": 95.0,
        "reasons": [
          "Corrective candidate for insufficient_depth: Provides a defined depth target and counterbalanced loading for practicing controlled depth.",
          "Matches requested movement pattern: squat",
          "Suitable for selected fitness level: beginner"
        ],
        "relationship_type": "corrective",
        "is_canonical_cv": false
      }
    ],
    "applied_filters": {
      "intent": "corrective",
      "source_exercise_id": "ex_squat",
      "corrective_issue_id": "insufficient_depth"
    },
    "diagnostics": [],
    "conflicting_filters": []
  }
  ```

---

### 10. Test & Regression Results

#### 1. Dedicated Recommendation Test Suite
Command: `py -m pytest backend/tests/test_exercise_recommendations.py -v`
- **Result**: **39 passed, 0 failed, 1 warning in 0.15s**
- Validated all 16 mandatory plan corrections:
  1. `test_1_progression_intent_cannot_return_regression_edges`: PASSED
  2. `test_2_regression_intent_cannot_return_progression_edges`: PASSED
  3. `test_3_substitution_intent_cannot_return_complement_edges`: PASSED
  4. `test_4_complement_intent_cannot_return_substitution_edges`: PASSED
  5. `test_5_invalid_corrective_source_or_issue_rejected`: PASSED
  6. `test_6_valid_corrective_returns_only_mapped_candidates`: PASSED
  7. `test_7_equipment_not_double_counted`: PASSED
  8. `test_8_diversity_does_not_remove_relationship_candidates`: PASSED
  9. `test_9_diversity_does_not_remove_corrective_candidates`: PASSED
  10. `test_10_muscle_mismatch_does_not_hard_exclude`: PASSED
  11. `test_11_insufficient_data_does_not_fabricate_bodyweight_fallback`: PASSED
  12. `test_12_scores_strictly_bounded_0_to_100`: PASSED
  13. `test_13_score_weights_sum_exactly_one`: PASSED
  14. `test_14_identical_requests_produce_identical_candidate_ordering`: PASSED
  15. `test_15_form_analysis_supported_only_returns_canonical_five`: PASSED
  16. `test_16_zero_external_network_or_gemini_dependency`: PASSED
- Validated all 15 concrete evaluation scenarios:
  1. General goal discovery: PASSED
  2. Gym barbell / dumbbell: PASSED
  3. Home dumbbells only: PASSED
  4. Home bodyweight only: PASSED
  5. Canonical squat progression: PASSED
  6. Canonical deadlift regression: PASSED
  7. Equipment substitution: PASSED
  8. Bench complement: PASSED
  9. Corrective squat depth: PASSED
  10. Corrective bench flare: PASSED
  11. Corrective deadlift lockout: PASSED
  12. Corrective curl drift: PASSED
  13. Corrective press lockout: PASSED
  14. Conflicting constraints: PASSED
  15. Insufficient request data: PASSED

#### 2. Combined Catalog, Relationship, and Recommendation Suite
Command: `py -m pytest backend/tests/test_exercise_relationships.py backend/tests/test_exercise_catalog.py backend/tests/test_exercise_knowledge_schema.py backend/tests/test_exercise_recommendations.py -v`
- **Result**: **107 passed, 0 failed, 1 warning in 0.28s**

#### 3. Full Backend Regression Suite
Command: `py -m pytest backend/tests -q`
- **Result**: **580 passed, 1 failed, 7 warnings in 25.67s**
- **Independent Quota Failure Detail**: The sole failure was the pre-existing external Google Cloud Firestore free-tier quota exhaustion (`google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded`) in `backend/tests/test_users.py::test_valid_authenticated_user_dependency`. Zero test regressions in any exercise, catalog, relationship, or recommendation components.

#### 4. Frontend Regression Suite
Command: `npm test -- --run`
- **Result**: **61 passed, 0 failed in 2.64s** (Phase 9B.6 binary encoder, WebSocket protocol, stream coordinator, and Phase 9B.7 session history tests all green).

#### 5. Frontend Production Build
Command: `npm run build`
- **Result**: **Build successful in 5.34s** with 0 errors.

---

### 11. Security, Privacy & Safety Audit

- **Zero Credentials / Secrets**: No API keys, service accounts, or tokens added.
- **Zero External Network Calls**: Recommendation engine operates 100% in-memory against pre-loaded catalog data structures.
- **Zero Gemini / LLM Dependencies**: Completely deterministic rule-based algorithms.
- **Zero Persistent Writes**: No recommendation logs, user write operations, or Firestore mutations created.
- **Zero PII**: No user identifiers stored or logged.
- **Strict Non-Medical Phrasing**: Automated validation ensures generated reasons make no claims to cure, prevent, or diagnose injuries.

---

Phase 9B.8.4 implementation complete — awaiting explicit approval for Phase 9B.8.5.

# PHASE 9B.8.4 IMPLEMENTATION PLAN
## Deterministic Personalized Exercise Recommendation Foundation (Final Corrected Plan)

**Status**: Plan Only — Awaiting Final Review & Approval Before Implementation  
**Date**: September 14, 2026  
**Scope Boundary**: Deterministic Candidate Generation & Ranking Decision Engine (Zero Gemini/LLM, Zero Vector DB, Zero ML)  

---

### 1. Objective & Architectural Principles

Phase 9B.8.4 establishes the deterministic recommendation engine connecting:
1. The **100-exercise knowledge catalog** (Phase 9B.8.2)
2. The **exercise relationship graph** (Phase 9B.8.3)
3. The **authoritative corrective guidance mappings** (Phase 9B.8.3)

with structured user constraints (goals, equipment, environment, fitness level, technique issues) to generate explainable, ranked exercise candidates.

#### Core Architectural Principle: Decision Engine vs. Presentation Layer
- **The Recommendation Engine is the Decision and Candidate Generation Layer**:
  - Enforces hard eligibility gates (equipment, environment, exclusions, CV support).
  - Drives intent-specific candidate generation (strict relationship and corrective isolation).
  - Scores soft alignment (goals, movement patterns, muscle groups, difficulty) using mathematically precise bounded weights summing to 1.00.
  - Generates deterministic, templated explanations explaining meaningful positive signals.
  - Guarantees 100% deterministic results with multi-tiered tie-breaking.
- **Gemini / LLM Separation**:
  - In a future phase (e.g. Phase 9C), Gemini may format or conversationally present already-selected candidates.
  - Gemini must **never** be the source of truth for exercise eligibility, equipment compatibility, movement-pattern matching, progression/regression selection, or corrective candidate retrieval.
- **No Scientific Validation Claims**:
  - This engine implements rule-based deterministic filtering and biomechanical heuristic ranking.
  - No claim of clinical efficacy, medical treatment, or empirical recommendation accuracy without a validated benchmark is made.

---

### 2. Current Architecture Dependencies & Authoritative Data Sources

The engine is grounded strictly in existing, verified data structures:

| Component | File Path | Authoritative Source & Role |
|---|---|---|
| **Taxonomies & Domain Models** | `backend/app/schemas/exercise.py` | `MovementPattern`, `ExerciseCategory`, `DifficultyLevel`, `EquipmentType`, `MuscleGroup`, `FitnessGoal`, `EnvironmentType`, `ExerciseKnowledgeSchema`, `CANONICAL_CV_EXERCISES` |
| **User Profile Models** | `backend/app/schemas/user.py` | `UserProfileSchema`, `FitnessGoal`, `EquipmentType`, `Environment`, `DifficultyLevel` |
| **100-Exercise Catalog** | `backend/app/seeds/catalog/__init__.py` | `CATALOG_BY_ID`, `CATALOG_EXERCISES`, `CATALOG_BY_MOVEMENT_PATTERN`, `CATALOG_BY_PRIMARY_MUSCLE` |
| **Relationship Graph Service** | `backend/app/services/exercise_relationship_service.py` | `ExerciseRelationshipService` (`get_progressions()`, `get_regressions()`, `get_substitutions()`, `get_complements()`, `get_corrective_exercises()`) |
| **Corrective Mappings** | `backend/app/seeds/corrective_mappings.py` | `RAW_CORRECTIVE_MAPPINGS`, `HEURISTIC_NAME_TO_ISSUE_ID`, `ISSUE_ID_TO_HEURISTIC_NAME` |
| **Form Heuristics Engine** | `backend/app/services/form_heuristics.py` | 25 observable heuristics across 5 CV exercises (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`) |
| **FastAPI Root Router** | `backend/app/api/v1/router.py` | API sub-router integration under `/exercises/recommendations` |

---

### 3. Strongly Typed Request & Response Schemas

```python
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from backend.app.schemas.exercise import (
    MovementPattern,
    ExerciseCategory,
    ExerciseType,
    Laterality,
    EnvironmentType,
    EquipmentType,
    MuscleGroup,
    DifficultyLevel,
    FitnessGoal,
    ExerciseRelationshipType,
)


class RecommendationIntent(str, Enum):
    GENERAL = "general"                 # Standard goal- and profile-based discovery
    PROGRESSION = "progression"         # Advance from source exercise
    REGRESSION = "regression"           # Regress from source exercise
    SUBSTITUTION = "substitution"       # Alternative for source exercise
    COMPLEMENT = "complement"           # Accessory work for source exercise
    CORRECTIVE = "corrective"           # Address an observed technique issue


class ExerciseRecommendationRequest(BaseModel):
    """Strongly typed recommendation query payload."""
    intent: RecommendationIntent = Field(default=RecommendationIntent.GENERAL)
    
    # User Profile / Contextual Inputs
    targetGoal: Optional[FitnessGoal] = Field(default=None, alias="target_goal")
    fitnessLevel: Optional[DifficultyLevel] = Field(default=None, alias="fitness_level")
    environment: Optional[EnvironmentType] = Field(default=None)
    availableEquipment: Optional[List[EquipmentType]] = Field(default=None, alias="available_equipment")
    
    # Movement & Muscle Preferences (Soft Ranking Signals)
    movementPattern: Optional[MovementPattern] = Field(default=None, alias="movement_pattern")
    targetMuscles: Optional[List[MuscleGroup]] = Field(default=None, alias="target_muscles")
    preferredCategory: Optional[ExerciseCategory] = Field(default=None, alias="preferred_category")
    preferredLaterality: Optional[Laterality] = Field(default=None, alias="preferred_laterality")
    
    # Hard Exclusions
    excludedEquipment: List[EquipmentType] = Field(default_factory=list, alias="excluded_equipment")
    excludedExerciseIds: List[str] = Field(default_factory=list, alias="excluded_exercise_ids")
    
    # Relationship & Corrective Targeting
    sourceExerciseId: Optional[str] = Field(default=None, alias="source_exercise_id")
    correctiveIssueId: Optional[str] = Field(default=None, alias="corrective_issue_id")
    formAnalysisSupportedOnly: bool = Field(default=False, alias="form_analysis_supported_only")
    
    # Pagination & Diversity Options
    limit: int = Field(default=10, ge=1, le=50)
    enableDiversity: bool = Field(default=True, alias="enable_diversity")

    model_config = {"extra": "ignore", "populate_by_name": True}


class ExerciseRecommendationNode(BaseModel):
    """Deterministic candidate recommendation with verified score and explainable reasons."""
    exerciseId: str = Field(..., alias="exercise_id")
    name: str
    movementPattern: MovementPattern = Field(..., alias="movement_pattern")
    exerciseType: ExerciseType = Field(..., alias="exercise_type")
    difficulty: DifficultyLevel
    equipment: List[EquipmentType]
    primaryMuscles: List[MuscleGroup] = Field(..., alias="primary_muscles")
    score: float = Field(..., ge=0.0, le=100.0)
    reasons: List[str]
    relationshipType: Optional[ExerciseRelationshipType] = Field(default=None, alias="relationship_type")
    isCanonicalCv: bool = Field(default=False, alias="is_canonical_cv")

    model_config = {"extra": "ignore", "populate_by_name": True}


class ExerciseRecommendationResponse(BaseModel):
    """Response payload containing ranked candidates or clear diagnostics."""
    intent: RecommendationIntent
    totalEvaluated: int = Field(..., alias="total_evaluated")
    totalEligible: int = Field(..., alias="total_eligible")
    returnedCount: int = Field(..., alias="returned_count")
    candidates: List[ExerciseRecommendationNode]
    appliedFilters: Dict[str, Any] = Field(default_factory=dict, alias="applied_filters")
    diagnostics: List[str] = Field(default_factory=list)
    conflictingFilters: List[str] = Field(default_factory=list, alias="conflicting_filters")

    model_config = {"extra": "ignore", "populate_by_name": True}
```

---

### 4. Hard Eligibility Filters (Binary Gates)

Hard constraints act as strict binary gates ($0$ or $1$). An exercise failing any active hard filter is immediately excluded:

| Filter | Logic | Rationale & Enforcement |
|---|---|---|
| **Catalog Membership** | `exercise.id in CATALOG_BY_ID` and not `exercise.isDeprecated` | Excludes non-existent, malformed, or deprecated records. |
| **Explicit Exclusion** | `exercise.id not in request.excludedExerciseIds` | User or caller explicitly excludes specific exercises. |
| **Equipment Availability** | If `availableEquipment` supplied: `all(eq in request.availableEquipment for eq in exercise.equipment)` | **Strict Hard Gate**: A user cannot perform an exercise requiring equipment they do not possess. |
| **Excluded Equipment** | `not any(eq in request.excludedEquipment for eq in exercise.equipment)` | Excludes exercises requiring forbidden equipment (e.g. no barbell). |
| **Environment Compatibility** | If `environment` supplied: `request.environment in exercise.targetEnvironments` or `"anywhere" in exercise.targetEnvironments` | Home workouts must not recommend gym-only equipment/machines (e.g. leg press). |
| **CV Support Gate** | If `formAnalysisSupportedOnly == True`: `exercise.id in CANONICAL_CV_EXERCISES` | **Strict Hard Gate**: Restricts candidate pool exclusively to the exactly 5 canonical CV exercises (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`). No inference from similarity. |

> [!IMPORTANT]
> **No Equipment Double-Counting**: Equipment compatibility is strictly an eligibility gate. It is completely removed from soft scoring to eliminate redundant point awards for merely surviving a filter.

---

### 5. Strict Intent-Driven Candidate Generation

The requested `intent` strictly dictates candidate generation. Candidates outside the requested relationship classification or corrective mapping **must not enter the candidate set**:

| Intent | Candidate Generation Source | Scope Isolation Enforcement |
|---|---|---|
| **`GENERAL`** | Entire 100-Exercise Catalog (`CATALOG_EXERCISES`) | Standard multi-dimensional ranking across the catalog. |
| **`PROGRESSION`** | `ExerciseRelationshipService.get_progressions(sourceExerciseId)` | **Strict**: Regressions, substitutions, and complements are completely barred from entry. |
| **`REGRESSION`** | `ExerciseRelationshipService.get_regressions(sourceExerciseId)` | **Strict**: Progressions, substitutions, and complements are completely barred from entry. |
| **`SUBSTITUTION`** | `ExerciseRelationshipService.get_substitutions(sourceExerciseId)` | **Strict**: Only valid movement substitutions enter candidate pool. |
| **`COMPLEMENT`** | `ExerciseRelationshipService.get_complements(sourceExerciseId)` | **Strict**: Only valid accessory/complementary exercises enter candidate pool. |
| **`CORRECTIVE`** | `ExerciseRelationshipService.get_corrective_exercises(sourceExerciseId, correctiveIssueId)` | **Strict**: Only curated candidates mapped to the specific observable technique issue enter candidate pool. |

---

### 6. Corrective Source & Issue Validation

For `intent == CORRECTIVE`:
1. **Source Exercise Validation**:
   - `sourceExerciseId` must be provided and must be one of the exactly 5 canonical CV exercises (`ex_squat`, `ex_bench_press`, `ex_deadlift`, `ex_bicep_curl`, `ex_shoulder_press`).
   - If missing: Returns zero candidates with diagnostic: `"Intent 'corrective' requires 'source_exercise_id'."`.
   - If non-CV: Returns zero candidates with diagnostic: `"Corrective recommendations require a canonical CV source exercise (ex_squat, ex_bench_press, ex_deadlift, ex_bicep_curl, ex_shoulder_press)."`.
2. **Corrective Issue Validation**:
   - `correctiveIssueId` must be provided.
   - The engine validates against the Phase 9B.8.3 normalization layer:
     `HEURISTIC_NAME_TO_ISSUE_ID` and `ISSUE_ID_TO_HEURISTIC_NAME` in `backend/app/seeds/corrective_mappings.py`.
   - If missing: Returns zero candidates with diagnostic: `"Intent 'corrective' requires 'corrective_issue_id'."`.
   - If invalid or unmapped for the source exercise: Returns zero candidates with diagnostic: `"Issue '{issue}' is not an authoritative Phase 9B.2 finding for exercise '{source}'."`.
   - Zero duplicated heuristic definitions; zero modifications to `form_heuristics.py`. Zero fabricated recommendations.

---

### 7. Soft Ranking Signals & Mathematical Scoring Model

For every scoring signal, its normalized range is strictly defined as $[0.0, 1.0]$. The final candidate score is computed as:
$$\text{Score} = 100.0 \times \sum_{i} (w_i \times S_i) \quad \text{where } \sum w_i = 1.00 \text{ and } \text{Score} \in [0.0, 100.0]$$

#### Why Each Signal Exists & Normalized Definitions:

1. **Goal Alignment ($S_{\text{goal}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Matches user fitness aspirations (e.g. strength vs. hypertrophy vs. endurance) against exercise target goals.
   - If `targetGoal` specified: $S_{\text{goal}} = 1.0$ if $\text{targetGoal} \in \text{exercise.targetGoals}$ else $0.20$.
   - If no `targetGoal` specified: $S_{\text{goal}} = 1.0$ (neutral).
2. **Target Muscle Overlap ($S_{\text{muscle}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Ranks exercises targeting the user's requested muscle groups without excluding non-matching exercises (soft signal).
   - Evaluates primary muscles ($0.75$ weight) and secondary muscles ($0.25$ weight):
     $$S_{\text{muscle}} = 0.75 \times \frac{|\text{targetMuscles} \cap \text{exercise.primaryMuscles}|}{\max(1, |\text{exercise.primaryMuscles}|)} + 0.25 \times \frac{|\text{targetMuscles} \cap \text{exercise.secondaryMuscles}|}{\max(1, |\text{exercise.secondaryMuscles}|)}$$
     clamped to $[0.0, 1.0]$. If overlap is zero: $S_{\text{muscle}} = 0.10$ (soft penalty, never hard-excluded).
   - If no `targetMuscles` specified: $S_{\text{muscle}} = 1.0$ (neutral).
3. **Movement Pattern Match ($S_{\text{pattern}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Prioritizes exercises matching the requested movement pattern (e.g. squat, hinge, push).
   - If `movementPattern` specified: $S_{\text{pattern}} = 1.0$ if $\text{exercise.movementPattern} == \text{request.movementPattern}$ else $0.0$.
   - If no `movementPattern` specified: $S_{\text{pattern}} = 1.0$ (neutral).
4. **Difficulty Suitability ($S_{\text{diff}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Aligns exercise complexity with user fitness level (beginner, intermediate, advanced).
   - If `fitnessLevel` specified: Exact match $= 1.0$; 1 step away $= 0.50$; 2 steps away $= 0.0$.
   - If no `fitnessLevel` specified: $S_{\text{diff}} = 1.0$ (neutral).
5. **Category & Laterality Preference ($S_{\text{cat\_lat}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Accommodates user preferences for exercise format (e.g. compound vs. isolation, bilateral vs. unilateral).
   - Category component ($0.60$): Match $= 1.0$; Mismatch $= 0.0$. If unspecified: $1.0$.
   - Laterality component ($0.40$): Match $= 1.0$; Mismatch $= 0.0$. If unspecified: $1.0$.
   - $S_{\text{cat\_lat}} = 0.60 S_{\text{cat}} + 0.40 S_{\text{lat}}$.
6. **Relationship Edge Priority ($S_{\text{edge}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Reflects curated biomechanical transition priority from the relationship graph.
   - $S_{\text{edge}} = \frac{1}{\text{node.priority}}$ (Priority 1 $\rightarrow 1.0$; Priority 2 $\rightarrow 0.50$; Priority 3 $\rightarrow 0.33$).
7. **Corrective Curated Priority ($S_{\text{corr}} \in [0.0, 1.0]$)**:
   - *Why it exists*: Prioritizes Tier-1 primary corrective drills over Tier-2 supporting drills.
   - Priority 1 $\rightarrow 1.0$; Priority 2 $\rightarrow 0.70$.

---

### 8. Intent-Specific Scoring Profiles

Weights are mathematically explicit, sum to exactly $1.00$, and contain **zero equipment points**:

#### Profile A: General Discovery (`intent = GENERAL`)
Evaluates open library exploration:
- $w_{\text{goal}} = 0.30$ (Goal Alignment)
- $w_{\text{muscle}} = 0.30$ (Target Muscle Overlap)
- $w_{\text{pattern}} = 0.20$ (Movement Pattern Match)
- $w_{\text{diff}} = 0.10$ (Difficulty Fit)
- $w_{\text{cat\_lat}} = 0.10$ (Category & Laterality)
$$\sum w_i = 0.30 + 0.30 + 0.20 + 0.10 + 0.10 = \mathbf{1.00}$$

#### Profile B: Relationship-Guided (`intent` $\in$ {`PROGRESSION`, `REGRESSION`, `SUBSTITUTION`, `COMPLEMENT`})
Ranks strictly within generated relationship edges:
- $w_{\text{edge}} = 0.35$ (Relationship Graph Edge Priority)
- $w_{\text{goal}} = 0.25$ (Goal Alignment)
- $w_{\text{muscle}} = 0.25$ (Target Muscle Preservation)
- $w_{\text{diff}} = 0.15$ (Difficulty Alignment)
$$\sum w_i = 0.35 + 0.25 + 0.25 + 0.15 = \mathbf{1.00}$$

#### Profile C: Corrective Guidance (`intent = CORRECTIVE`)
Ranks strictly within mapped corrective candidates:
- $w_{\text{corr}} = 0.50$ (Curated Corrective Mapping Priority)
- $w_{\text{pattern}} = 0.25$ (Movement Pattern Reinforcement)
- $w_{\text{diff}} = 0.15$ (Difficulty Accessibility)
- $w_{\text{muscle}} = 0.10$ (Anatomical Alignment)
$$\sum w_i = 0.50 + 0.25 + 0.15 + 0.10 = \mathbf{1.00}$$

---

### 9. Three Explicit Insufficient-Data / Diagnostic States

The engine completely removes all arbitrary "bodyweight fallback" assumptions and enforces three distinct states:

#### State A: Valid Unconstrained / General Discovery Request
- **Trigger**: Request has `intent = GENERAL` with minimal or unconstrained filters.
- **Behavior**: Deterministic general discovery ranking across eligible catalog exercises.
- **Result**: Returns ranked candidates matching eligible criteria.

#### State B: Insufficient Data for the Requested Intent
- **Trigger**: Request asks for an intent requiring specific inputs, but they are missing:
  - `intent` $\in$ {`PROGRESSION`, `REGRESSION`, `SUBSTITUTION`, `COMPLEMENT`} but `sourceExerciseId` is omitted or empty.
  - `intent = CORRECTIVE` but `sourceExerciseId` or `correctiveIssueId` is omitted or empty.
- **Behavior**: Returns `total_eligible = 0`, `candidates = []`.
- **Diagnostic**: Explicit explanation of what is missing (e.g. `"Intent 'progression' requires 'source_exercise_id'."`, `"Intent 'corrective' requires 'corrective_issue_id'."`).
- **No Arbitrary Fallback**: No generic bodyweight exercises are fabricated.

#### State C: Conflicting Hard Constraints
- **Trigger**: Hard filters eliminate all candidates (e.g. `environment="outdoor"` + `availableEquipment=["barbell"]`).
- **Behavior**: Returns `total_eligible = 0`, `candidates = []`.
- **Diagnostic**: Explicit list in `conflictingFilters` detailing why zero exercises matched (e.g. `"No catalog exercises match environment 'outdoor' with equipment ['barbell']."`).

---

### 10. Intent-Aware Diversity Strategy

Diversity post-processing prevents homogenization without overriding user intent:

- **General Discovery Mode**:
  - Diversity is **enabled by default** (can be disabled via `enableDiversity = False`).
  - Caps candidates to a maximum of **2 exercises per primary movement pattern** in the top-N returned candidates.
  - Exception: If the user explicitly requested a specific `movementPattern`, diversity capping for that pattern is disabled.
- **Relationship-Guided Modes (`PROGRESSION`, `REGRESSION`, `SUBSTITUTION`, `COMPLEMENT`)**:
  - **Diversity capping is DISABLED**.
  - Relationship candidates are already bounded (2 to 4 candidates per source exercise) and semantically focused. Diversity post-processing must **never** eliminate a valid relationship edge.
- **Corrective Guidance Mode (`CORRECTIVE`)**:
  - **Diversity capping is DISABLED**.
  - Corrective candidates are specifically curated (3 candidates per issue). Diversity must **never** remove an authoritative corrective candidate merely because it shares a movement pattern.

---

### 11. Deterministic Score Reasons & Tie Breaking

#### Explicit Score Reasons
The response exposes concise, deterministic reasons explaining meaningful positive signals:
- Goal match: `"Matches selected fitness goal: {goal}"`
- Movement pattern match: `"Matches requested movement pattern: {pattern}"`
- Muscle overlap: `"Targets {count} requested muscle group(s): {muscles}"`
- Difficulty suitability: `"Suitable for selected fitness level: {level}"`
- Relationship edge: `"{RelationshipType} from {source_exercise_name}"`
- Corrective issue: `"Corrective candidate for {issue_id}: {rationale}"`

> [!NOTE]
> Reasons are generated strictly via deterministic string templates. Zero LLM calls. No internal raw weights or implementation details are leaked.

#### Multi-Tiered Deterministic Tie Breaking
To guarantee byte-for-byte identical ordering across platforms and repeated runs:
```
┌────────────────────────────────────────────────────────┐
│ Tier 1: Score Descending (rounded to 2 decimal places) │
└───────────────────────────┬────────────────────────────┘
                            │ (if score is equal)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: Priority Ascending (Priority 1 before 2)       │
└───────────────────────────┬────────────────────────────┘
                            │ (if priority is equal)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: Compound Before Isolation                      │
│         (exerciseType == 'compound' before 'isolation')│
└───────────────────────────┬────────────────────────────┘
                            │ (if exerciseType is equal)
                            ▼
┌────────────────────────────────────────────────────────┐
│ Tier 4: Canonical Exercise ID Alphabetical Ascending   │
│         (e.g. 'ex_bench_press' before 'ex_push_up')    │
└────────────────────────────────────────────────────────┘
```

Never depends on dictionary iteration, set iteration, Firestore ordering, or runtime memory ordering.

---

### 12. Service Architecture & Layer Separation

```
                                Catalog (Phase 9B.8.2)
                                          │
                                          ▼
                      ExerciseRelationshipService (Phase 9B.8.3)
                                          │
                                          ▼
                     ExerciseRecommendationService (Phase 9B.8.4)
                                          │
                                          ▼
                      FastAPI Route: POST /exercises/recommendations
```

- **Clean Layer Separation**:
  - `ExerciseRelationshipService` provides graph facts and corrective mappings.
  - `ExerciseRecommendationService` consumes those facts, enforces user eligibility gates, scores candidates, and applies tie-breaking.
  - Zero duplication of graph traversal or heuristic normalization logic.

---

### 13. API Contract (`POST /api/v1/exercises/recommendations`)

- **Method & Path**: `POST /api/v1/exercises/recommendations`
- **Read-Only**: No persistence, no Firestore write, no logging of recommendation queries.
- **Sample Request (Corrective Intent)**:
  ```json
  {
    "intent": "corrective",
    "source_exercise_id": "ex_squat",
    "corrective_issue_id": "insufficient_depth",
    "available_equipment": ["barbell", "dumbbells"],
    "limit": 5
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
        "equipment": ["barbell"],
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

### 14. Testing Strategy (16 Mandatory Test Corrections)

Test file: `backend/tests/test_exercise_recommendations.py`  
Explicitly verifies all 16 mandatory plan corrections:

1. `test_progression_intent_cannot_return_regression_edges`: Confirms progression queries never return regression edges.
2. `test_regression_intent_cannot_return_progression_edges`: Confirms regression queries never return progression edges.
3. `test_substitution_intent_cannot_return_complement_edges`: Confirms substitution queries never return complement edges.
4. `test_complement_intent_cannot_return_substitution_edges`: Confirms complement queries never return substitution edges.
5. `test_invalid_corrective_source_or_issue_rejected`: Rejects non-CV source or unmapped issue with clean diagnostic.
6. `test_valid_corrective_returns_only_mapped_candidates`: Valid query returns exclusively authoritative mapped candidate exercises.
7. `test_equipment_not_double_counted`: Verifies soft scores do not award points for equipment survival.
8. `test_diversity_does_not_remove_relationship_candidates`: Progression/regression candidates are never pruned by diversity.
9. `test_diversity_does_not_remove_corrective_candidates`: Corrective candidates are never pruned by diversity.
10. `test_muscle_mismatch_does_not_hard_exclude`: Non-matching muscle exercises survive hard filter (soft ranking signal).
11. `test_insufficient_data_does_not_fabricate_bodyweight_fallback`: Empty relationship/corrective requests return zero candidates with diagnostic.
12. `test_scores_strictly_bounded_0_to_100`: Asserts $0.0 \le \text{score} \le 100.0$ across all profiles.
13. `test_score_weights_sum_exactly_one`: Verifies $\sum w_i == 1.00$ across all intent profiles.
14. `test_identical_requests_produce_identical_candidate_ordering`: Confirms byte-for-byte deterministic stability across repeated runs.
15. `test_form_analysis_supported_only_returns_canonical_five`: Restricts candidate pool strictly to the 5 canonical exercises when eligible.
16. `test_zero_external_network_or_gemini_dependency`: Confirms service executes 100% in-memory with zero network, Firestore, or LLM calls.

---

### 15. Evaluation Scenarios Dataset (15 Scenarios)

The evaluation suite tests actual catalog exercises across realistic fitness scenarios.  
*Note: Results reflect deterministic rule satisfaction; no empirical recommendation accuracy claim is made without a validated benchmark.*

| # | Scenario | Request Parameters | Expected Behavior & Candidates |
|---|---|---|---|
| **1** | General Goal Discovery | `intent="general"`, `goal="muscle_gain"`, `env="gym"` | Top candidates feature hypertrophy compound lifts (`ex_bench_press`, `ex_squat`, `ex_barbell_hip_thrust`). |
| **2** | Gym Barbell / Dumbbell | `intent="general"`, `goal="strength"`, `equipment=["barbell", "dumbbells", "bench"]` | Ranks heavy compound presses, squats, and deadlifts. |
| **3** | Home Dumbbells Only | `intent="general"`, `env="home"`, `equipment=["dumbbells"]` | Filters out barbell/cable exercises; ranks `ex_goblet_squat`, `ex_dumbbell_flat_press`, `ex_dumbbell_rdl`. |
| **4** | Home Bodyweight Only | `intent="general"`, `env="home"`, `equipment=["bodyweight"]` | Filters out all loaded lifts; ranks `ex_push_up`, `ex_bodyweight_squat`, `ex_front_plank`, `ex_reverse_lunge`. |
| **5** | Canonical Squat Progression | `intent="progression"`, `source="ex_squat"`, `equipment=["barbell"]` | Returns strictly `ex_front_squat` and `ex_overhead_squat`. Zero regressions. |
| **6** | Canonical Deadlift Regression | `intent="regression"`, `source="ex_deadlift"` | Returns strictly `ex_romanian_deadlift`, `ex_trap_bar_deadlift`. Zero progressions. |
| **7** | Equipment Substitution | `intent="substitution"`, `source="ex_bench_press"`, `equipment=["dumbbells", "bench"]` | Returns `ex_dumbbell_flat_press`, `ex_dumbbell_floor_press`. Zero barbells. |
| **8** | Bench Complement | `intent="complement"`, `source="ex_bench_press"` | Returns accessory movements (`ex_face_pull`, `ex_seated_cable_row`). |
| **9** | Corrective: Squat Depth | `intent="corrective"`, `source="ex_squat"`, `issue="insufficient_depth"` | Returns `ex_box_squat`, `ex_goblet_squat`, `ex_90_90_hip_flow`. |
| **10** | Corrective: Bench Flare | `intent="corrective"`, `source="ex_bench_press"`, `issue="excessive_elbow_flare"` | Returns `ex_close_grip_bench_press`, `ex_dumbbell_flat_press`, `ex_push_up`. |
| **11** | Corrective: Deadlift Lockout | `intent="corrective"`, `source="ex_deadlift"`, `issue="insufficient_lockout"` | Returns `ex_glute_bridge`, `ex_romanian_deadlift`, `ex_kettlebell_swing`. |
| **12** | Corrective: Curl Drift | `intent="corrective"`, `source="ex_bicep_curl"`, `issue="excessive_arm_movement"` | Returns `ex_concentration_curl`, `ex_incline_dumbbell_curl`, `ex_cable_bicep_curl`. |
| **13** | Corrective: Press Lockout | `intent="corrective"`, `source="ex_shoulder_press"`, `issue="insufficient_overhead_range"` | Returns `ex_landmine_press`, `ex_cat_cow`, `ex_thoracic_foam_roll`. |
| **14** | Conflicting Constraints | `env="outdoor"`, `equipment=["barbell"]` | Returns 0 candidates, diagnostic: `"No catalog exercises match environment 'outdoor' with equipment ['barbell']"`. |
| **15** | Insufficient Request Data | `intent="progression"` (no `source_exercise_id`) | Returns 0 candidates, diagnostic: `"Intent 'progression' requires 'source_exercise_id'"`. |

---

### 16. Security, Privacy & Safety Audit

- **Zero New Secrets**: No credentials, API keys, or service tokens added.
- **Zero External Network Calls**: 100% in-memory computation.
- **Zero Gemini / LLM Dependencies**: Completely deterministic rule-based algorithms.
- **Zero Persistent Writes**: No recommendation logs, user write operations, or Firestore mutations.
- **Zero PII**: No user identifiers stored or persisted.
- **Strict Non-Medical Phrasing**: Automated string matching ensures no reasons claim to cure, prevent, or diagnose injuries.

---

### 17. Files Likely to be Created / Modified

#### Created
1. `backend/app/services/exercise_recommendation_service.py`: Core recommendation decision engine.
2. `backend/app/api/v1/endpoints/exercise_recommendations.py`: Read-only recommendation endpoint (`POST /exercises/recommendations`).
3. `backend/tests/test_exercise_recommendations.py`: Dedicated test suite covering tests 1 through 16 and scenarios 1 through 15.
4. `PHASE_9B_8_4_IMPLEMENTATION_REPORT.md`: Final implementation report.

#### Modified
1. `backend/app/schemas/exercise.py`: Add `RecommendationIntent`, `ExerciseRecommendationRequest`, `ExerciseRecommendationNode`, `ExerciseRecommendationResponse`.
2. `backend/app/api/v1/router.py`: Register `exercise_recommendations_router` under prefix `/exercises/recommendations`.

---

### 18. Files Explicitly NOT to be Touched

- All frontend UI code (`src/**/*`)
- `backend/app/services/form_heuristics.py`
- `backend/app/seeds/catalog/*.py` (all 10 catalog modules)
- `backend/app/seeds/corrective_mappings.py`
- `backend/app/services/exercise_relationship_service.py` (consumed as-is)
- Phase 3 repositories and schemas (`exercise_repository.py`, etc.)
- `backend/app/services/llm_client.py`

---

### 19. Risks & Tradeoffs

| Risk / Tradeoff | Mitigation |
|---|---|
| **Risk**: Score ties leading to fluctuating recommendation order | **Mitigation**: Multi-tiered deterministic tie-breaking sequence ending with unique canonical `exerciseId`. |
| **Risk**: Over-filtering resulting in empty candidates | **Mitigation**: Explicit `conflictingFilters` diagnostic reporting so callers understand conflicting constraints. |
| **Risk**: Non-medical language compliance drift | **Mitigation**: Automated Pydantic model validator scanning generated reasons against `PROHIBITED_MEDICAL_PHRASES`. |
| **Tradeoff**: Strict relationship scoping prevents serendipitous cross-pattern discovery | **Mitigation**: Preserves strict relationship semantics for `PROGRESSION`/`REGRESSION`/`SUBSTITUTION`/`COMPLEMENT`; serendipitous discovery is explicitly the purpose of `intent=GENERAL`. |

---

### 20. Explicit Boundary for Phase 9B.8.5

Phase 9B.8.4 delivers the **deterministic candidate ranking and recommendation service**.

The following capabilities are strictly reserved for subsequent phases:
- **Phase 9B.8.5**: Multi-Day Workout Plan Generator & Split Architecture (Push/Pull/Legs, Upper/Lower, Full Body).
- **Phase 9B.8.6**: Adaptive Recommendation Tuning based on historical workout performance and fatigue.
- **Phase 9C**: Gemini-Powered Conversational Coach Presentation of Recommendations.

---

Phase 9B.8.4 plan complete — awaiting final review and approval before implementation.

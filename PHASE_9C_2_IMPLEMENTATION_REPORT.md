# Phase 9C.2 — Deterministic Progression & Adaptation Engine Implementation Report

**Status**: Verified & Accepted  
**Phase Completed**: Phase 9C.2 ONLY  
**Next Phase**: Phase 9C.3 (Pending Explicit User Approval)  
**Date**: September 17, 2026  

---

## 1. Objective

The primary objective of Phase 9C.2 was to construct the bounded, deterministic, evidence-based decision layer that consumes analytical signals established in Phase 9C.1 and evaluates whether future workout prescriptions should be adapted. 

Phase 9C.2 answers:
> *"What bounded adaptation, if any, is justified by the user's observed historical evidence?"*

Crucially, Phase 9C.2 is strictly a **decision and proposal engine**. It does **NOT** mutate active programs, alter database documents, mutate active workout sessions, inject corrective exercises into live workouts, or generate natural-language rationale via LLMs.

---

## 2. Core Architecture

The architecture maintains strict unidirectional data flow and modularity:

```
Authoritative Workout Data (Firestore Completed Sessions)
                ↓
Phase 9C.1 Adaptive Performance Signals (PersonalizationSignalService)
                ↓
Phase 9C.2 Deterministic Adaptation Engine (AdaptationEngineService)
                ↓
Structured Adaptation Proposals & Audit Objects (Read-Only API)
                ↓
Future Plan / Dynamic Prescription Consumer (Phase 9C.4)
```

Phase 9C.2 does **not** bypass Phase 9C.1 to recreate ad-hoc metrics or query raw sessions independently for analytics. It directly ingests `PersonalizationSignalsResponse` and inspects authoritative completed sessions from `WorkoutRepository` strictly for chronological streak verification.

---

## 3. Files Created & Modified

### Backend
1. **`backend/app/schemas/adaptation.py`** [NEW]: Strongly-typed Pydantic domain models:
   - `AdaptationType`
   - `DecisionStatus`
   - `PrescriptionDelta`
   - `AdaptationDecision`
   - `FutureSplitRecommendation`
   - `AdaptationEvaluationRequest`
   - `AdaptationEvaluationResponse`
   - `generate_decision_id`
2. **`backend/app/services/adaptation_engine_service.py`** [NEW]: Deterministic adaptation engine implementing double-progression, 21-day reset, hard 5% load ceiling, volume fatigue, adherence future split adaptation, form flaw proposals, and precedence resolution.
3. **`backend/app/api/v1/endpoints/personalization.py`** [MODIFIED]: Added read-only authenticated endpoints `GET /adaptations` and `POST /adaptations/evaluate`.
4. **`backend/tests/test_adaptation_engine.py`** [NEW]: 33 comprehensive unit, boundary, conflict, constraint, security, and idempotency tests.
5. **`backend/tests/test_personalization_signals.py`** [MODIFIED]: Isolated test user UIDs with UUIDs to ensure full test isolation across Firestore test runs.

### Frontend
6. **`src/types/adaptation.ts`** [NEW]: TypeScript domain contracts for adaptation types, decision statuses, prescription deltas, and API responses.
7. **`src/services/adaptationService.ts`** [NEW]: Authenticated API client consuming `GET /adaptations` and `POST /adaptations/evaluate`.
8. **`src/hooks/useAdaptationDecisions.ts`** [NEW]: TanStack Query hook `useAdaptationDecisions(windowDays)` for read-only consumption.
9. **`src/hooks/index.ts`** [MODIFIED]: Re-exported `useAdaptationDecisions`.

### Documentation
10. **`PHASE_9C_2_IMPLEMENTATION_REPORT.md`** [NEW]: This authoritative implementation and verification report.

---

## 4. Domain Models & Schemas

### Controlled Taxonomies
- **`AdaptationType`**:
  - `load_progression`: Bounded increase in working resistance (kg).
  - `rep_progression`: Bounded increase in target rep range (+1 rep).
  - `volume_reduction`: Bounded reduction in prescribed sets (-1 set).
  - `exercise_regression`: Proposes mechanically simpler catalog regression.
  - `exercise_substitution`: Proposes equivalent equipment/exercise substitution.
  - `split_adjustment`: Mesocycle-level training frequency adjustment.
  - `recurring_form_issue`: Notice of persistent biomechanical technique flaw.
  - `no_change`: Current prescription remains optimal.

- **`DecisionStatus`**:
  - `insufficient_data`: Fewer than required qualifying observations.
  - `no_change`: Evidence indicates current prescription is stable.
  - `progression_candidate`: Double-progression criteria met and approved.
  - `volume_reduction_candidate`: Volume fatigue criteria met.
  - `regression_candidate`: Catalog regression relationship recommended.
  - `substitution_candidate`: Catalog substitution relationship recommended.
  - `future_split_adjustment_candidate`: 4-week adherence frequency mismatch detected.
  - `form_issue_candidate`: Recurring CV form flaw detected.
  - `constrained_no_change`: Adaptation justified but blocked by safety ceiling or floor.

### Prescription Delta & Reversibility
`PrescriptionDelta` encapsulates exact parameters before and after adaptation:
- `exerciseId`, `exerciseName`
- `weightKg`, `setCount`
- `targetRepsMin`, `targetRepsMax`
- `targetRpe`, `restSeconds`
- Invariant validator: `targetRepsMin <= targetRepsMax`.

### Audit Object (`AdaptationDecision`)
- `decisionId`: Reproducible 16-character SHA-256 hash.
- `ruleCode`: Deterministic machine-readable rule identifier.
- `evidence`: Quantitative metrics evaluated (consecutive sessions, volume completion %, gap days).
- `previousPrescription`: Fully populated `PrescriptionDelta`.
- `proposedPrescription`: Fully populated `PrescriptionDelta`.
- `deltaMagnitude`: Numeric magnitude (+2.5 kg, -1 set, +1 rep).
- `isReversible`: Always `True`.
- `constraintsApplied`: List of safety limits enforced.

---

## 5. Adaptation Rules & Engineering Logic

### Double-Progression Rule
- **Eligibility**:
  - Requires **3 consecutive completed sessions** for the same exercise.
  - In each of the 3 sessions, **every prescribed set** must reach or exceed `targetRepsMax` (or `targetReps`).
  - A single session or 2 sessions produce `no_change` (`INSUFFICIENT_CONSECUTIVE_SESSIONS` or `PROGRESSION_EVIDENCE_EMERGING`).
  - Sequence interruption (pass $\rightarrow$ fail $\rightarrow$ pass) resets consecutive qualifying streak to 1.
- **21-Day Reset Rule**:
  - Gap between consecutive qualifying sessions must be $\le 21$ days.
  - A gap $> 21$ days (e.g. 22 days) resets the consecutive streak to 1.
  - Tested boundaries: exactly 21 days (eligible) vs 22 days (reset).
- **Load Increments**:
  - Upper-body compound movements: `+2.5 kg`.
  - Lower-body compound movements: `+5.0 kg`.
  - Weighted isolation movements: `+1.0 kg`.
  - Bodyweight & unweighted movements: Prefer bounded rep progression (`+1 rep` to min and max).

### Hard 5% Weekly Load Ceiling
- **Safety Invariant**: `proposedLoad <= baselineLoad * 1.05`.
- Standard equipment increments cannot violate the 5% ceiling.
- If proposed load exceeds the 5% ceiling and no standard representable load fits within the bound:
  - Return `constrained_no_change` with `LOAD_CEILING_5_PERCENT_EXCEEDED`.
  - Tested boundaries:
    - 50.0 kg baseline + 2.5 kg = 52.5 kg (exactly 5.0%) $\rightarrow$ APPROVED.
    - 40.0 kg baseline + 2.5 kg = 42.5 kg (6.25% > 5.0%) $\rightarrow$ CONSTRAINED (`constrained_no_change`).
    - 80.0 kg lower compound + 5.0 kg = 85.0 kg (6.25% > 5.0%) $\rightarrow$ CONSTRAINED.
    - 100.0 kg lower compound + 5.0 kg = 105.0 kg (exactly 5.0%) $\rightarrow$ APPROVED.

### Volume Fatigue Rule
- **Eligibility**: Requires **2 consecutive completed sessions** where set volume completion is $< 70\%$ (`completedSets / plannedSets < 0.70`).
- One incomplete session produces `no_change`.
- Two consecutive incomplete sessions produce `volume_reduction_candidate` with `deltaMagnitude = -1.0` set.
- **Set Bounds**:
  - Bounded between 1 and 5 sets (`MIN_NORMAL_SETS = 1`, `MAX_NORMAL_SETS = 5`).
  - If current set count is already 1: cannot reduce to 0; returns `constrained_no_change` with rule code `MINIMUM_SET_BOUND_REACHED`.

### Conflict Resolution Precedence
When conflicting signals exist for an exercise, conservative safety strictly overrides aggressive progression:
1. **Insufficient Evidence**: `< 2` sessions or invalid baseline $\rightarrow$ `insufficient_data`.
2. **Hard Safety Constraints**: Duration ceiling ($> 1.25\times$) or RPE ceiling ($> 9.0$) $\rightarrow$ `constrained_no_change`.
3. **Volume Fatigue**: 2 consecutive volume failures $\rightarrow$ `volume_reduction_candidate` **strictly overrides** load progression.
4. **Exercise Regression / Substitution**: Catalog relationship candidate $\rightarrow$ `regression_candidate`.
5. **Recurring Form Issue**: Recurring CV issue $\rightarrow$ `form_issue_candidate`.
6. **Adherence Future-Block Split**: Mesocycle frequency mismatch $\rightarrow$ `future_split_adjustment_candidate`.
7. **Double Progression**: 3 qualifying sessions $\rightarrow$ `progression_candidate`.
8. **No Change**: Prescriptions remain stable.

### Form Flaw Signal Handling
- Consumes Phase 9C.1 `formSignals`.
- If an observed issue has `isRecurring == True` ($\ge 50\%$ frequency across analyzed sessions):
  - Generates `form_issue_candidate` proposal with `RECURRING_FORM_ISSUE_DETECTED`.
  - Exposes issue details, recurrence rate, and occurrence count.
  - **Does NOT modify Slot 0** or inject corrective exercises (strictly deferred to Phase 9C.6).

### Adherence Future-Block Split Adaptation
- Evaluates 4-week window (28 days).
- If planned frequency is 5 days/week and observed frequency is $\approx 3$ days/week ($\le 3.6$ sessions/week with $\ge 4$ sessions completed):
  - Generates `futureSplitProposal` recommending a 3-day Full Body split for the **next mesocycle**.
  - Does **NOT** mutate the active week, active program, or today's workout.
  - If planned frequency was not configured: returns `None` without fabricating plan adherence.

### Duration & RPE Constraints
- **Duration Bound**: Estimated duration must satisfy $\le 1.25\times$ target duration. If exceeded, returns `constrained_no_change` with `DURATION_EXCEEDS_125_PCT`.
- **RPE Bound**: Prescribed RPE must never exceed 9.0 (`MAX_PERMITTED_RPE = 9.0`). Candidate RPE values $> 9.0$ are automatically clamped to 9.0 and logged in `constraintsApplied`.

---

## 6. API Endpoints

Both endpoints are strictly read-only, authenticated via Firebase Bearer tokens, and user-scoped to `current_user.uid`:

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/personalization/adaptations` | Returns evaluated adaptation decisions across all tracked exercises and adherence trends. | Yes (CurrentUser) |
| `POST` | `/api/v1/personalization/adaptations/evaluate` | Evaluates adaptation decisions against a specific candidate workout context (`candidateExercises`, `targetDurationMinutes`). | Yes (CurrentUser) |

- **Security**:
  - Token verification via `get_current_user`.
  - User identity comes strictly from verified claims, never from request bodies.
  - Unauthenticated requests rejected with HTTP 401.

---

## 7. Verification & Test Results

### Automated Backend Tests
- **Phase 9C.2 Test Suite**: `backend/tests/test_adaptation_engine.py`
  - **33 / 33 passed** (100%) in 5.18s
- **Full Backend Regression Suite**: `backend/tests`
  - **761 / 761 passed** (100%), 0 failures, 12 deprecation warnings in 39.38s

### Automated Frontend Tests
- **Frontend Test Suite**: `npm test`
  - **113 / 113 passed** (100%), 0 failures across 6 suites in 2.25s

### Production Build
- **Build Command**: `npm run build`
  - `tsc -b && vite build` succeeded in 972ms with 0 errors.

### Live API Verification
- Live daemon FastAPI server (`http://127.0.0.1:8000`):
  - `GET /api/v1/health` $\rightarrow$ `200 OK`
  - `GET /api/v1/personalization/adaptations` (no token) $\rightarrow$ `401 Unauthorized`
  - `POST /api/v1/personalization/adaptations/evaluate` (no token) $\rightarrow$ `401 Unauthorized`

---

## 8. Security Audit

- **Authentication Gate**: All personalization and adaptation endpoints require a verified Firebase Bearer token.
- **Authorization Scoping**: User identity is derived strictly from `current_user.uid`. Client-supplied UIDs in request bodies are ignored.
- **Cross-User Isolation**: Verified via `test_cross_user_isolation`. User A's session data never influences User B's evaluations.
- **Zero Database Writes**: Verified via `test_adaptation_zero_firestore_writes`. Evaluating adaptations performs zero mutations to Firestore.
- **Zero Secrets / Private Credentials**: Verified. No API keys, credentials, or service account JSON strings are exposed.
- **Zero LLM / Neural Calls**: No external network requests to Gemini or external APIs. Decisions are 100% deterministic and reproducible.

---

## 9. Explicitly Unimplemented Scope (Deferred to Future Phases)

The following capabilities were intentionally **not** implemented in Phase 9C.2:
- **Phase 9C.3**: Active Program & Mesocycle Lifecycle Persistence (`users/{uid}/programs`, `users/{uid}/adaptations` Firestore persistence).
- **Phase 9C.4**: Adaptive Workout Plan & Dynamic Prescription Integration (applying decisions to active workouts).
- **Phase 9C.5**: Frontend Program Tracking & Adaptive UI (adaptive dashboard cards, recommendation controls).
- **Phase 9C.6**: Form Analysis & Corrective Integration (injecting corrective exercises into Slot 0).
- **Phase 9C.7**: Comprehensive Multi-Week End-to-End Verification.

---

## 10. Conclusion & Stop Condition

Phase 9C.2 is **100% complete, tested, and verified**. Zero regressions exist across backend (761/761 passed) and frontend (113/113 passed). 

All work on Phase 9C.2 has stopped. We will await your explicit review and approval before proceeding to Phase 9C.3.

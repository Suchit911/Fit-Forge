# PHASE 9B.1 IMPLEMENTATION REPORT
## Deterministic Exercise Rep-Counting Engine

**Milestone:** Phase 9B.1 — Exercise FSM & Deterministic Rep Counting  
**Date:** 2026-09-13  
**Status:** COMPLETE & FULLY VERIFIED  
**Author:** AI Pair Programmer (DeepMind Antigravity)  

---

## 1. Implementation Status

Sub-Phase 9B.1 is **COMPLETE**.

The deterministic Finite State Machine (FSM) engine for exercise repetition counting has been implemented in [backend/app/services/exercise_fsm.py](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/exercise_fsm.py) and thoroughly verified with 32 unit test cases in [backend/tests/test_exercise_fsm.py](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/tests/test_exercise_fsm.py).

All 32 new tests pass 100% (in 0.16s). The full backend test suite of 293 tests passes 100% without any regressions. The frontend build (`npm run build`) builds cleanly with zero errors.

---

## 2. Files Created & Modified

### Created Files:
1. **[backend/app/services/exercise_fsm.py](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/app/services/exercise_fsm.py)**
   - Implements `ExerciseFSM`, `ExerciseFSMConfig`, `KinematicObservation`, `FSMUpdateResult`, and the factory `get_exercise_fsm`.
   - Supports 5 core exercises: Squat, Bench Press, Deadlift, Bicep Curl, Shoulder Press.
   - Enforces deterministic state transitions, $\pm 10^\circ$ hysteresis deadbands, minimum ROM thresholds, secondary 0.7s refractory cooldown, and strict 400 ms landmark occlusion buffering/invalidation.
2. **[backend/tests/test_exercise_fsm.py](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/tests/test_exercise_fsm.py)**
   - 32 deterministic unit tests covering Scenarios A through N across all 5 exercises using synthetic trajectories.
3. **[PHASE_9B_1_IMPLEMENTATION_REPORT.md](file:///c:/Users/Suchit/Downloads/Fitness%20App/PHASE_9B_1_IMPLEMENTATION_REPORT.md)**
   - Detailed milestone implementation and verification report.

### Modified Files:
- None. (Zero modifications were made to existing Phase 1–8 code or Phase 9A foundations).

---

## 3. FSM Architecture

The rep-counting engine is implemented as a pure, deterministic state machine driven exclusively by kinematic observations. It does not access cameras, files, network, or databases.

```
+-----------------------------------------------------------------------------------+
|                           KinematicObservation                                   |
|   - timestamp_ms: float                                                           |
|   - joint_angles: Dict[str, float] (e.g. {"left_knee": 92.0, "right_knee": 94.0}) |
|   - confidence: float (mean landmark tracking confidence)                         |
|   - landmarks_detected: bool                                                      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                ExerciseFSM                                        |
|   - Evaluates primary/secondary joint angles                                      |
|   - Enforces directional progression & deadband hysteresis                        |
|   - Tracks baseline starting angle & peak inflection angle                        |
|   - Buffers temporary landmark loss (<= 400 ms)                                   |
|   - Invalidates rep trajectory if landmark loss > 400 ms                          |
|   - Verifies minimum ROM & secondary refractory cooldown                          |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            FSMUpdateResult                                        |
|   - exercise_id: str                                                              |
|   - state: FSMState                                                               |
|   - rep_count: int                                                                |
|   - rep_completed: bool (True only on exact completion frame)                     |
|   - completed_rep_number: Optional[int]                                           |
|   - rom_degrees: Optional[float]                                                  |
|   - outcome: RepOutcome (VALID_REP, INCOMPLETE_REP, INVALIDATED_REP, NONE)        |
|   - invalidation_reason: Optional[str]                                            |
|   - tracking_status: TrackingStatus (TRACKING_ACTIVE, OCCLUDED_BUFFERING, LOST)   |
|   - duration_ms: Optional[float]                                                  |
+-----------------------------------------------------------------------------------+
```

---

## 4. State Transition Rules

The state machine implements the formal progression:

```
[IDLE]
  │ (Athlete detected in starting posture, confidence >= 0.50)
  ▼
[SETUP] ───(Baseline joint angle established)
  │ (Joint angle moves beyond initiation delta: > 12°)
  ▼
[IN_PROGRESS] ───(Extreme inflection reached <= threshold)
  │                                   │
  │ (Reverses before inflection)      ▼
  │ ──> [INCOMPLETE_RESET]       [INFLECTION]
  │                                   │ (Clears hysteresis deadband: >= 10°)
  │                                   ▼
  │                              [RETURNING]
  │                                   │ (Returns to start posture & ROM >= Min ROM)
  │                                   ▼
  │                              [COMPLETED] ──> rep_count += 1
  │                                   │ (Auto-transitions back to SETUP)
  │                                   ▼
  │                                [SETUP]
  │
  │ (Landmarks lost > 400 ms during movement)
  └───> [INVALIDATED_RESET] (rep_count unchanged, trajectory purged)
```

1. `IDLE` $\rightarrow$ `SETUP`: Primary joint is within start threshold range with confidence $\ge 0.50$.
2. `SETUP` $\rightarrow$ `IN_PROGRESS`: Primary joint angle diverges by $> 12.0^\circ$ from the established baseline angle.
3. `IN_PROGRESS` $\rightarrow$ `INFLECTION`: Primary joint crosses the inflection threshold (and secondary lockout criteria are satisfied, e.g. knees extended in Deadlift).
4. `IN_PROGRESS` $\rightarrow$ `INCOMPLETE_RESET`: Athlete reverses direction significantly before reaching the inflection threshold. Trajectory is reset without rep increment.
5. `INFLECTION` $\rightarrow$ `RETURNING`: Movement reverses direction and clears the hysteresis deadband ($10^\circ$).
6. `RETURNING` $\rightarrow$ `COMPLETED`: Joint angle returns to starting baseline posture AND observed range of motion $\ge \text{min\_rom\_degrees}$ AND cooldown elapsed.
7. `RETURNING` $\rightarrow$ `INCOMPLETE_RESET`: Joint angle returns to starting posture but observed $\text{ROM} < \text{min\_rom\_degrees}$ (partial twitch).

---

## 5. Exercise-Specific Kinematic Thresholds

| Exercise | Primary Joint(s) | Secondary Joint(s) | Movement Direction | Start Posture Threshold | Initiation Delta | Inflection / Depth Threshold | Return Threshold | Minimum ROM Threshold |
|---|---|---|---|---|---|---|---|---|
| **Squat** (`ex_squat`) | `left_knee`, `right_knee` | None | `FLEXION_FIRST` | $> 160^\circ$ | $12^\circ$ | $\le 95^\circ$ (parallel depth) | $> 160^\circ$ | $\ge 60^\circ$ |
| **Bench Press** (`ex_bench_press`) | `left_elbow`, `right_elbow` | None | `FLEXION_FIRST` | $> 155^\circ$ | $12^\circ$ | $\le 90^\circ$ (chest touch) | $> 155^\circ$ | $\ge 55^\circ$ |
| **Deadlift** (`ex_deadlift`) | `left_hip`, `right_hip` | `left_knee`, `right_knee` | `EXTENSION_FIRST` | $\le 90^\circ$ (floor setup) | $12^\circ$ | $\ge 165^\circ$ (lockout) | $\le 90^\circ$ | $\ge 65^\circ$ (with knee $\ge 165^\circ$) |
| **Bicep Curl** (`ex_bicep_curl`) | `left_elbow`, `right_elbow` | None | `FLEXION_FIRST` | $> 150^\circ$ (hang) | $12^\circ$ | $\le 55^\circ$ (peak contraction) | $> 150^\circ$ | $\ge 80^\circ$ |
| **Shoulder Press** (`ex_shoulder_press`) | `left_elbow`, `right_elbow` | None | `EXTENSION_FIRST` | $\le 85^\circ$ (chin rack) | $12^\circ$ | $\ge 165^\circ$ (overhead lockout) | $\le 85^\circ$ | $\ge 70^\circ$ |

---

## 6. Hysteresis Configuration & Rationale

- **Configured Deadband:** $10.0^\circ$ across all exercises.
- **Biomechanical Rationale:** At the inflection point (e.g. $92^\circ$ squat depth), landmark predictions fluctuate by $\pm 2^\circ\text{--}3^\circ$ due to micro-camera jitter and athlete breathing. Without hysteresis, this jitter causes high-frequency state toggling between `INFLECTION` and `RETURNING`.
- **Enforcement:**
  - In `FLEXION_FIRST`: After inflection $\theta_{\text{inflect}}$, the angle must rise to at least $\theta_{\text{inflect}} + 10^\circ$ before entering `RETURNING`.
  - In `EXTENSION_FIRST`: After inflection $\theta_{\text{inflect}}$, the angle must drop to at least $\theta_{\text{inflect}} - 10^\circ$ before entering `RETURNING`.
- **Verification:** Unit test `test_scenario_f_hysteresis_boundary_noise` verifies that 10 consecutive frames of alternating noise ($\pm 3^\circ$ around $95^\circ$) are completely absorbed without toggling state.

---

## 7. Minimum Range of Motion (ROM) Rules

- **Formula:** $\text{ROM}_{\text{observed}} = |\theta_{\text{baseline}} - \theta_{\text{inflection}}|$
- **Thresholds:**
  - Squat: $\ge 60^\circ$
  - Bench Press: $\ge 55^\circ$
  - Deadlift: $\ge 65^\circ$
  - Bicep Curl: $\ge 80^\circ$
  - Shoulder Press: $\ge 70^\circ$
- **Enforcement:** If an athlete descends and returns, but $\text{ROM}_{\text{observed}} < \text{min\_rom\_degrees}$, the FSM enters `INCOMPLETE_RESET`, sets `outcome = RepOutcome.INCOMPLETE_REP`, and leaves `rep_count` unchanged.
- **Verification:** Unit test `test_scenario_d_insufficient_rom_squat` verifies that a 40° squat dip leaves `rep_count` at 0.

---

## 8. Confidence Rules

- **Minimum Tracking Confidence:** $\ge 0.50$ (reusing Phase 9A's canonical tracking threshold `settings.CV_MIN_TRACKING_CONFIDENCE`).
- **Enforcement:** If `confidence < 0.50` or `landmarks_detected == False`, the frame is treated as missing data.
- **Guardrail:** Low confidence observations never trigger state advances and never create false rep counts.
- **Verification:** Unit test `test_scenario_k_low_confidence_rejected` verifies that an otherwise perfect trajectory with `confidence = 0.30` produces 0 counted reps.

---

## 9. 400 ms Landmark Occlusion Behavior

The FSM implements the strict 400 ms occlusion recovery window:
1. **Occlusion Initiation:** If tracking is lost (`confidence < 0.50` or missing landmarks) while in `IN_PROGRESS`, `INFLECTION`, or `RETURNING`:
   - The FSM records `occlusion_start_timestamp_ms`.
   - The FSM holds the active state without advancing or inventing movement.
   - Sets `tracking_status = TrackingStatus.OCCLUDED_BUFFERING`.
2. **Recovery ($\le 400\text{ ms}$):** If valid tracking resumes within 400 ms:
   - `occlusion_start_timestamp_ms` is cleared.
   - Movement continues seamlessly from the preserved state.
   - Verified by unit test `test_scenario_i_occlusion_under_400ms_recovery` (300 ms outage successfully recovers and counts the rep).
3. **Invalidation ($> 400\text{ ms}$):** If outage exceeds 400 ms:
   - The active rep trajectory is completely invalidated.
   - FSM transitions to `INVALIDATED_RESET`.
   - Sets `outcome = RepOutcome.INVALIDATED_REP` and `invalidation_reason = "landmarks_lost_exceeded_400ms"`.
   - `rep_count` is NOT incremented.
   - Verified by unit test `test_scenario_j_occlusion_over_400ms_invalidation` (500 ms outage invalidates rep; rep count remains 0).

---

## 10. 0.7-Second Refractory Cooldown Behavior

- **Designated Role:** The 0.7-second (700 ms) cooldown is **strictly a secondary debounce mechanism**, NOT the primary rep counting criterion.
- **Primary Criterion:** Directional state progression + inflection depth + return to start + minimum ROM satisfied.
- **Purpose:** Prevents duplicate `COMPLETED` events if an athlete hovers or oscillates at the lockout line.
- **Legitimate Fast Movements Permitted:** A rapid rep taking 0.8s to complete its full cycle will complete normally without being blocked. The cooldown only prevents a *second* rep from completing within 700 ms of the *first* completion event.
- **Verification:**
  - `test_scenario_g_rapid_valid_movement`: A fast 800 ms squat completes and counts.
  - `test_scenario_h_duplicate_completion_suppression`: Flutter at the completion threshold within 200 ms produces exactly 1 counted rep.

---

## 11. Test Coverage & Verification Results

### New Phase 9B.1 Tests:
All 32 tests in [backend/tests/test_exercise_fsm.py](file:///c:/Users/Suchit/Downloads/Fitness%20App/backend/tests/test_exercise_fsm.py) passed:
- `test_scenario_a_valid_complete_rep` (Squat, Bench, Deadlift, Curl, Shoulder Press) — **PASS** (5 tests)
- `test_scenario_b_two_valid_reps` (Squat, Bench, Deadlift, Curl, Shoulder Press) — **PASS** (5 tests)
- `test_scenario_c_partial_movement` (Squat, Bench, Deadlift, Curl, Shoulder Press) — **PASS** (5 tests)
- `test_scenario_d_insufficient_rom_squat` — **PASS**
- `test_scenario_e_reversed_movement_direction` — **PASS**
- `test_scenario_f_hysteresis_boundary_noise` — **PASS**
- `test_scenario_g_rapid_valid_movement` — **PASS**
- `test_scenario_h_duplicate_completion_suppression` — **PASS**
- `test_scenario_i_occlusion_under_400ms_recovery` — **PASS**
- `test_scenario_j_occlusion_over_400ms_invalidation` — **PASS**
- `test_scenario_k_low_confidence_rejected` — **PASS**
- `test_scenario_l_no_movement_elapsed_time` — **PASS**
- `test_scenario_m_determinism` (Squat, Bench, Deadlift, Curl, Shoulder Press) — **PASS** (5 tests)
- `test_scenario_n_cross_exercise_isolation` — **PASS**
- `test_factory_unsupported_exercise_raises_error` — **PASS**
- `test_deadlift_secondary_knee_lockout_required` — **PASS**

**Result:** **32 passed in 0.16s** (100% pass rate).

### Full Backend Regression Suite:
- Executed `py -m pytest backend/tests/ -v`.
- **293 passed in 29.49s** (100% pass rate).
- Zero regression across all Phase 1–8 and Phase 9A test suites.
- Note: External Firebase/Firestore passed without encountering any quota issues.

### Frontend Production Build:
- Executed `npm run build`.
- **Exit Code 0** (0 TypeScript errors, 0 Vite errors).

---

## 12. Architectural Limitations

1. **Single Representative Joint Angle:** The FSM currently uses the mean of visible bilateral joints (e.g. left and right knees). If asymmetric form analysis is needed (e.g. left knee flexes more than right), that belongs to the form heuristics layer (Phase 9B.2) rather than the rep counter.
2. **Secondary Joint Lockout for Deadlift:** The Deadlift FSM checks that knees reach lockout ($\ge 165^\circ$) along with hip extension. If the camera only captures the upper body, Deadlift lockout cannot be confirmed. Camera setup must capture full body.

---

## 13. Scope & Boundary Confirmations

### Phase 9B.2–9B.7 Deferred Confirmation:
- ❌ No `form_heuristics.py` implemented.
- ❌ No `form_scoring.py` implemented.
- ❌ No `form_session_manager.py` implemented.
- ❌ No WebSocket streaming endpoints created.
- ❌ No camera streaming or `getUserMedia` code added.
- ❌ No canvas skeleton overlay added.
- ❌ No frontend UI modifications made.

### Phase 9C Prohibited Features Confirmation:
- ❌ Zero Firestore persistence for form sessions.
- ❌ Zero video recording or uploads.
- ❌ Zero audio or voice coaching.
- ❌ Zero Gemini/LLM form analysis.
- ❌ Zero barbell detection models.
- ❌ Zero new external credentials or dependencies.

---

## 14. Conclusion

Phase 9B.1 is **COMPLETE**, fully tested, and ready for user review. Awaiting approval before proceeding to Phase 9B.2 (Form Heuristics).

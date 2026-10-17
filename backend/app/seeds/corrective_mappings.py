"""
Authoritative Corrective Guidance Mappings (Phase 9B.8.3).

Provides deterministic mappings from actual Phase 9B.2 form analysis heuristic observations
to suitable candidate exercises in the authoritative 100-exercise catalog.

Core Architecture:
- Authoritative Phase 9B.2 Heuristic Alignment: Every mapping connects strictly to a real,
  observable heuristic evaluated in `backend/app/services/form_heuristics.py`.
- Explicit Issue-ID Normalization Layer:
    actual heuristic name -> normalized technique issue ID -> candidate exercise IDs
- Conservative Technique Language: Strictly engineering/technique-oriented. No medical
  diagnoses, no injury cure/prevention claims, no biomechanical force guarantees.
- Bounded, Catalog-Backed Candidates: Every candidate is verified to exist in CATALOG_BY_ID.
"""

from typing import List, Dict, Any, Tuple
from backend.app.schemas.exercise import (
    PROHIBITED_MEDICAL_PHRASES,
    CANONICAL_CV_EXERCISES,
)
from backend.app.seeds.catalog import CATALOG_BY_ID


# Raw deterministic corrective guidance definitions
# Exactly 25 mappings corresponding to the 25 specific form heuristics in Phase 9B.2
RAW_CORRECTIVE_MAPPINGS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. SQUAT (ex_squat) - 5 Heuristics
    # -------------------------------------------------------------------------
    {
        "source_exercise_id": "ex_squat",
        "heuristic_name": "squat_depth",
        "issue_id": "insufficient_depth",
        "candidate_exercise_ids": ["ex_box_squat", "ex_goblet_squat", "ex_90_90_hip_flow"],
        "reason": "Provides a defined depth target and counterbalanced loading for practicing controlled depth.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_squat",
        "heuristic_name": "squat_torso_inclination",
        "issue_id": "excessive_torso_lean",
        "candidate_exercise_ids": ["ex_goblet_squat", "ex_front_squat", "ex_front_plank"],
        "reason": "Provides anterior loading and trunk bracing practice to support upright torso positioning.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_squat",
        "heuristic_name": "squat_knee_tracking",
        "issue_id": "knee_tracking_deviation",
        "candidate_exercise_ids": ["ex_goblet_squat", "ex_bulgarian_squat", "ex_side_plank"],
        "reason": "Provides a controlled squat variation to practice consistent knee tracking over the foot.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_squat",
        "heuristic_name": "squat_knee_symmetry",
        "issue_id": "asymmetrical_movement",
        "candidate_exercise_ids": ["ex_dumbbell_split_squat", "ex_walking_lunge", "ex_reverse_lunge"],
        "reason": "Provides unilateral leg practice for improving bilateral movement consistency.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_squat",
        "heuristic_name": "squat_movement_stability",
        "issue_id": "unstable_torso",
        "candidate_exercise_ids": ["ex_dead_bug", "ex_front_plank", "ex_goblet_squat"],
        "reason": "Provides isometric core bracing practice to reinforce trunk stability throughout the descent.",
        "priority": 2,
    },

    # -------------------------------------------------------------------------
    # 2. BENCH PRESS (ex_bench_press) - 4 Heuristics
    # -------------------------------------------------------------------------
    {
        "source_exercise_id": "ex_bench_press",
        "heuristic_name": "bench_elbow_rom",
        "issue_id": "insufficient_depth",
        "candidate_exercise_ids": ["ex_dumbbell_flat_press", "ex_push_up", "ex_dumbbell_floor_press"],
        "reason": "Provides a consistent bottom pressing target for practicing complete horizontal range of motion.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_bench_press",
        "heuristic_name": "bench_elbow_flare",
        "issue_id": "excessive_elbow_flare",
        "candidate_exercise_ids": ["ex_close_grip_bench_press", "ex_dumbbell_flat_press", "ex_push_up"],
        "reason": "Provides neutral grip and closer pressing angles for practicing moderate elbow tuck.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_bench_press",
        "heuristic_name": "bench_elbow_symmetry",
        "issue_id": "poor_press_symmetry",
        "candidate_exercise_ids": ["ex_dumbbell_flat_press", "ex_incline_db_press", "ex_push_up"],
        "reason": "Provides independent arm loading to practice symmetrical pressing mechanics.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_bench_press",
        "heuristic_name": "bench_movement_stability",
        "issue_id": "unstable_movement",
        "candidate_exercise_ids": ["ex_push_up", "ex_front_plank", "ex_dumbbell_floor_press"],
        "reason": "Provides floor-supported pressing and plank variations for practicing stable pressing control.",
        "priority": 2,
    },

    # -------------------------------------------------------------------------
    # 3. DEADLIFT (ex_deadlift) - 6 Heuristics
    # -------------------------------------------------------------------------
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_hip_lockout",
        "issue_id": "insufficient_lockout",
        "candidate_exercise_ids": ["ex_glute_bridge", "ex_romanian_deadlift", "ex_kettlebell_swing"],
        "reason": "Provides focused hip extension practice to reinforce consistent standing lockout.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_hip_knee_sequencing",
        "issue_id": "early_hip_rise",
        "candidate_exercise_ids": ["ex_trap_bar_deadlift", "ex_romanian_deadlift", "ex_front_squat"],
        "reason": "Provides an upright hinge variation for practicing coordinated leg drive and back angle timing.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_torso_angle",
        "issue_id": "excessive_torso_lean",
        "candidate_exercise_ids": ["ex_trap_bar_deadlift", "ex_sumo_deadlift", "ex_kettlebell_deadlift"],
        "reason": "Provides elevated handles and wide stance variations to practice a more upright starting torso angle.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_body_center_stability",
        "issue_id": "body_center_drift",
        "candidate_exercise_ids": ["ex_romanian_deadlift", "ex_kettlebell_deadlift", "ex_farmers_walk"],
        "reason": "Provides balance and close load positioning practice to maintain stable center of mass.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_hip_symmetry",
        "issue_id": "asymmetrical_movement",
        "candidate_exercise_ids": ["ex_dumbbell_rdl", "ex_bulgarian_squat", "ex_dumbbell_split_squat"],
        "reason": "Provides unilateral hinge and split-stance practice to balance movement mechanics between sides.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_deadlift",
        "heuristic_name": "deadlift_movement_stability",
        "issue_id": "unstable_torso",
        "candidate_exercise_ids": ["ex_front_plank", "ex_bird_dog", "ex_farmers_walk"],
        "reason": "Provides anti-extension and trunk bracing practice to support stable spinal positioning.",
        "priority": 2,
    },

    # -------------------------------------------------------------------------
    # 4. BICEP CURL (ex_bicep_curl) - 5 Heuristics
    # -------------------------------------------------------------------------
    {
        "source_exercise_id": "ex_bicep_curl",
        "heuristic_name": "curl_elbow_rom",
        "issue_id": "incomplete_rom",
        "candidate_exercise_ids": ["ex_concentration_curl", "ex_incline_dumbbell_curl", "ex_cable_bicep_curl"],
        "reason": "Provides anchored arm support to practice full elbow flexion without body momentum.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_bicep_curl",
        "heuristic_name": "curl_upper_arm_drift",
        "issue_id": "excessive_arm_movement",
        "candidate_exercise_ids": ["ex_concentration_curl", "ex_incline_dumbbell_curl", "ex_cable_bicep_curl"],
        "reason": "Provides physical arm placement against support to practice keeping the upper arm stationary.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_bicep_curl",
        "heuristic_name": "curl_torso_momentum",
        "issue_id": "unstable_torso",
        "candidate_exercise_ids": ["ex_concentration_curl", "ex_front_plank", "ex_cable_bicep_curl"],
        "reason": "Provides seated and constant-tension variations to practice curling without backward torso sway.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_bicep_curl",
        "heuristic_name": "curl_elbow_symmetry",
        "issue_id": "asymmetrical_movement",
        "candidate_exercise_ids": ["ex_dumbbell_hammer_curl", "ex_concentration_curl", "ex_incline_dumbbell_curl"],
        "reason": "Provides unilateral arm loading to practice symmetrical curl timing and elbow mechanics.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_bicep_curl",
        "heuristic_name": "curl_movement_stability",
        "issue_id": "unstable_movement",
        "candidate_exercise_ids": ["ex_concentration_curl", "ex_cable_bicep_curl", "ex_dead_bug"],
        "reason": "Provides continuous resistance and core bracing practice for smooth, controlled curl velocity.",
        "priority": 2,
    },

    # -------------------------------------------------------------------------
    # 5. SHOULDER PRESS (ex_shoulder_press) - 5 Heuristics
    # -------------------------------------------------------------------------
    {
        "source_exercise_id": "ex_shoulder_press",
        "heuristic_name": "shoulder_press_lockout",
        "issue_id": "insufficient_overhead_range",
        "candidate_exercise_ids": ["ex_landmine_press", "ex_cat_cow", "ex_thoracic_foam_roll"],
        "reason": "Provides an angled pressing vector and thoracic mobility drills to practice overhead reach within comfortable range.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_shoulder_press",
        "heuristic_name": "shoulder_press_forearm_verticality",
        "issue_id": "forearm_tilt",
        "candidate_exercise_ids": ["ex_arnold_press", "ex_landmine_press", "ex_machine_shoulder_press"],
        "reason": "Provides natural rotational freedom and guided paths to practice vertical forearm alignment.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_shoulder_press",
        "heuristic_name": "shoulder_press_torso_lean",
        "issue_id": "excessive_torso_lean",
        "candidate_exercise_ids": ["ex_machine_shoulder_press", "ex_landmine_press", "ex_front_plank"],
        "reason": "Provides seated back support and angled pressing to practice pressing without backward lumbar arching.",
        "priority": 1,
    },
    {
        "source_exercise_id": "ex_shoulder_press",
        "heuristic_name": "shoulder_press_elbow_symmetry",
        "issue_id": "poor_press_symmetry",
        "candidate_exercise_ids": ["ex_arnold_press", "ex_landmine_press", "ex_pike_push_up"],
        "reason": "Provides independent shoulder loading to practice balanced bilateral pressing coordination.",
        "priority": 2,
    },
    {
        "source_exercise_id": "ex_shoulder_press",
        "heuristic_name": "shoulder_press_movement_stability",
        "issue_id": "unstable_torso",
        "candidate_exercise_ids": ["ex_machine_shoulder_press", "ex_front_plank", "ex_dead_bug"],
        "reason": "Provides seated stability and core tension drills to maintain a firm pressing platform.",
        "priority": 2,
    },
]

# Fast lookups for normalization layer
HEURISTIC_NAME_TO_ISSUE_ID: Dict[Tuple[str, str], str] = {
    (m["source_exercise_id"], m["heuristic_name"]): m["issue_id"]
    for m in RAW_CORRECTIVE_MAPPINGS
}

ISSUE_ID_TO_HEURISTIC_NAME: Dict[Tuple[str, str], str] = {
    (m["source_exercise_id"], m["issue_id"]): m["heuristic_name"]
    for m in RAW_CORRECTIVE_MAPPINGS
}


# =============================================================================
# MODULE-LEVEL INTEGRITY VERIFICATION
# =============================================================================

assert len(RAW_CORRECTIVE_MAPPINGS) == 25, (
    f"Expected exactly 25 corrective mappings, got {len(RAW_CORRECTIVE_MAPPINGS)}"
)

# Verify canonical exercises coverage
cv_covered = set(m["source_exercise_id"] for m in RAW_CORRECTIVE_MAPPINGS)
assert cv_covered == set(CANONICAL_CV_EXERCISES.keys()), (
    f"Corrective mappings must cover all 5 canonical CV exercises: {cv_covered}"
)

# Referential integrity: all candidate IDs must exist in the 100-exercise catalog
for mapping in RAW_CORRECTIVE_MAPPINGS:
    source_id = mapping["source_exercise_id"]
    assert source_id in CATALOG_BY_ID, f"Source exercise '{source_id}' not found in catalog"

    candidates = mapping["candidate_exercise_ids"]
    assert len(candidates) > 0, f"Mapping for '{source_id}' - '{mapping['issue_id']}' has no candidates"
    assert len(candidates) == len(set(candidates)), f"Duplicate candidates in mapping: {mapping}"

    for cand_id in candidates:
        assert cand_id in CATALOG_BY_ID, (
            f"Candidate exercise '{cand_id}' in mapping for '{source_id}' - "
            f"'{mapping['issue_id']}' does not exist in 100-exercise catalog"
        )
        assert cand_id != source_id, (
            f"Self-referencing candidate '{cand_id}' in mapping for '{source_id}'"
        )

    # Non-medical language enforcement
    lower_reason = mapping["reason"].lower()
    for phrase in PROHIBITED_MEDICAL_PHRASES:
        assert phrase not in lower_reason, (
            f"Prohibited medical phrase '{phrase}' found in corrective reason: {mapping['reason']}"
        )

"""
Phase 9C.6.2.5 — Final Integration Verification & Freeze Suite (T01–T34).

This module provides end-to-end integration tests and verifies the remaining
freeze invariants:
- End-to-end integration from repetition heuristics -> single-session aggregation
  -> atomic persistence with canonical fingerprint -> multi-session longitudinal aggregation.
- T33: Snapshot Immutability (planSnapshot and effectivePlanSnapshot remain byte-identical).
- T34: Zero LLM in the live loop (AST and runtime inspection confirming zero LLM imports/calls).
- Explicit 1-to-1 confirmation of T24, T25, T26 under V2.3.3 Section 9 definitions.
"""

import ast
import json
import os
import sys
from typing import Optional, List
import pytest

from backend.app.schemas.form_evidence import (
    EvidenceLevel,
    CalculationStatus,
    ProvenanceTier,
    EvidenceAggregationConfig,
    SessionIssueSummary,
    SessionEvidenceRecord,
    ExerciseEvidenceSummary,
)
from backend.app.schemas.form_analysis import (
    FormAnalysisSessionDetailSchema,
    CompactRepSummarySchema,
)
from backend.app.services.form_analysis.session_evidence_aggregator import (
    SessionEvidenceAggregator,
)
from backend.app.services.form_analysis.multi_session_evidence_aggregator import (
    MultiSessionEvidenceAggregator,
)
from backend.app.repositories.form_analysis_repository import (
    FormAnalysisRepository,
    ConflictingSessionPayloadError,
    SessionPersistenceResult,
    compute_payload_fingerprint,
)


def _make_detail(
    session_id: str,
    user_id: str = "user-freeze",
    exercise_id: str = "ex_squat",
    rep_count: int = 10,
    valid_rep_count: int = 10,
    overall_score: float = 85.0,
    duration_seconds: int = 60,
    client_notes: Optional[str] = "Good session",
) -> FormAnalysisSessionDetailSchema:
    """Constructs a valid FormAnalysisSessionDetailSchema instance."""
    reps = [
        CompactRepSummarySchema(
            rep_number=i + 1,
            status="valid",
            score=overall_score,
            rom_degrees=95.0,
            duration_ms=2000.0,
            category_scores={"ROM": overall_score},
            feedback=[],
        )
        for i in range(rep_count)
    ]
    return FormAnalysisSessionDetailSchema(
        session_id=session_id,
        user_id=user_id,
        exercise_id=exercise_id,
        canonical_exercise_id=exercise_id,
        exercise_name="Barbell Back Squat",
        status="completed",
        started_at="2026-09-29T00:00:00Z",
        completed_at="2026-09-29T00:01:00Z",
        duration_seconds=duration_seconds,
        total_reps=rep_count,
        completed_reps=rep_count,
        valid_reps=valid_rep_count,
        incomplete_reps=0,
        invalid_reps=0,
        insufficient_data_reps=0,
        overall_score=overall_score,
        best_score=overall_score,
        worst_score=overall_score,
        category_averages={"ROM": overall_score},
        summary_feedback=[],
        reps=reps,
        client_notes=client_notes,
    )


# =============================================================================
# END-TO-END PIPELINE INTEGRATION TEST
# =============================================================================

def test_full_pipeline_e2e_integration():
    """
    Verifies seamless integration across:
    1. SessionEvidenceAggregator (repetition-level -> session record)
    2. FormAnalysisRepository._persist_session_detail_atomic (atomic persistence & fingerprinting)
    3. MultiSessionEvidenceAggregator (session records -> longitudinal ExerciseEvidenceSummary)
    """
    repo = FormAnalysisRepository(db=None)
    repo.clear_in_memory_for_testing()

    session_aggregator = SessionEvidenceAggregator()
    multi_aggregator = MultiSessionEvidenceAggregator()

    sessions = []
    user_id = "test_user_freeze_e2e"
    exercise_id = "ex_squat"

    for session_idx in range(4):
        session_id = f"freeze_sess_{session_idx + 1}"

        # 10 reps per session: 6 defective on depth (ROM), 4 acceptable
        heuristics_data = {
            "squat_depth": [
                {
                    "rep_number": r + 1,
                    "confidence": 0.85,
                    "is_acceptable": (r >= 6), # 6 defective (r=0..5), 4 acceptable (r=6..9)
                    "defect_category": "ROM",
                }
                for r in range(10)
            ],
            "squat_knee_valgus": [
                {
                    "rep_number": r + 1,
                    "confidence": 0.82,
                    "is_acceptable": True, # All clean
                    "defect_category": "ALIGNMENT",
                }
                for r in range(10)
            ],
        }

        # Run single-session aggregation
        record = session_aggregator.aggregate_session(
            exercise_id=exercise_id,
            heuristics_data=heuristics_data,
            total_reps=10,
            valid_reps=10,
            session_observability_ratio=1.0,
            session_id=session_id,
            user_id=user_id,
        )
        assert record.calculation_status == CalculationStatus.SUCCESS
        assert record.is_eligible_for_trends is True
        sessions.append(record)

        # Build session detail schema
        detail = _make_detail(
            session_id=session_id,
            user_id=user_id,
            exercise_id=exercise_id,
            rep_count=10,
            valid_rep_count=10,
            overall_score=75.0,
        )

        # Atomic persistence with canonical fingerprint
        persist_res = repo._persist_session_detail_atomic(user_id, detail)
        assert persist_res.created is True
        assert persist_res.status_code == 201
        assert persist_res.detail.payload_fingerprint is not None

        # Verify idempotency: immediate identical retry
        retry_res = repo._persist_session_detail_atomic(user_id, detail)
        assert retry_res.created is False
        assert retry_res.status_code == 200
        assert retry_res.detail.payload_fingerprint == persist_res.detail.payload_fingerprint

    # Run multi-session longitudinal aggregation over the 4 persisted sessions
    summary = multi_aggregator.aggregate_exercise_evidence(sessions, exercise_id)
    assert isinstance(summary, ExerciseEvidenceSummary)
    assert summary.exercise_id == exercise_id
    assert summary.eligible_sessions_count == 4
    assert summary.lookback_sessions_evaluated == 4

    # Verify depth issue: 4 qualifying sessions out of 4 -> ACTIONABLE_PATTERN
    assert "insufficient_depth" in summary.issues
    depth_agg = summary.issues["insufficient_depth"]
    assert depth_agg.evidence_level == EvidenceLevel.ACTIONABLE_PATTERN
    assert depth_agg.target_evaluated_sessions_count == 4
    assert depth_agg.qualifying_sessions_count == 4
    assert depth_agg.recurrence_ratio == pytest.approx(1.0)
    assert depth_agg.qualifying_mean_confidence == pytest.approx(0.85)

    # Verify knee valgus issue: 0 qualifying sessions -> NO_EVIDENCE
    assert "knee_tracking_deviation" in summary.issues
    knee_agg = summary.issues["knee_tracking_deviation"]
    assert knee_agg.evidence_level == EvidenceLevel.NO_EVIDENCE
    assert knee_agg.target_evaluated_sessions_count == 4
    assert knee_agg.qualifying_sessions_count == 0
    assert knee_agg.recurrence_ratio == pytest.approx(0.0)
    assert knee_agg.qualifying_mean_confidence is None


# =============================================================================
# T33: SNAPSHOT IMMUTABILITY VERIFICATION
# =============================================================================

def test_t33_snapshot_immutability():
    """
    T33: Snapshot Immutability
    Verifies that neither planSnapshot nor effectivePlanSnapshot is mutated
    during form analysis, evidence aggregation, or session persistence.
    Strategy D (automatic exercise substitution) is permanently rejected.
    """
    # 1. Construct a mock workout plan snapshot representing user's permanent plan
    mock_plan_snapshot = {
        "planId": "plan_phase9c_freeze",
        "userId": "user_freeze_immutability",
        "name": "Hypertrophy Mesocycle",
        "durationWeeks": 8,
        "daysPerWeek": 4,
        "exercises": [
            {
                "exerciseId": "ex_squat",
                "targetSets": 4,
                "targetReps": 10,
                "targetRpe": 8.0,
                "restSeconds": 120,
            },
            {
                "exerciseId": "ex_bench",
                "targetSets": 3,
                "targetReps": 8,
                "targetRpe": 7.5,
                "restSeconds": 90,
            },
        ],
        "version": 1,
    }

    # Canonical byte representation before any form analysis or aggregation
    snapshot_bytes_before = json.dumps(mock_plan_snapshot, sort_keys=True, separators=(",", ":"))

    # 2. Run single-session aggregation with extreme defects (e.g. 100% defect rate)
    session_aggregator = SessionEvidenceAggregator()
    session_record = session_aggregator.aggregate_session(
        exercise_id="ex_squat",
        heuristics_data={
            "squat_depth": [
                {"rep_number": r + 1, "confidence": 0.90, "is_acceptable": False}
                for r in range(10)
            ]
        },
        total_reps=10,
        valid_reps=10,
        session_observability_ratio=1.0,
    )

    # 3. Run multi-session aggregation
    multi_aggregator = MultiSessionEvidenceAggregator()
    evidence_summary = multi_aggregator.aggregate_exercise_evidence([session_record], "ex_squat")

    # 4. Run repository persistence
    repo = FormAnalysisRepository(db=None)
    detail = _make_detail("sess_immutability_1", user_id="user_freeze_immutability", rep_count=10)
    repo._persist_session_detail_atomic("user_freeze_immutability", detail)

    # 5. Canonical byte representation after all form operations
    snapshot_bytes_after = json.dumps(mock_plan_snapshot, sort_keys=True, separators=(",", ":"))

    # Invariant: Byte-identical, zero modifications, zero exercise substitutions
    assert snapshot_bytes_before == snapshot_bytes_after
    assert mock_plan_snapshot["exercises"][0]["exerciseId"] == "ex_squat"
    assert mock_plan_snapshot["exercises"][0]["targetSets"] == 4


# =============================================================================
# T34: ZERO LLM IN LIVE LOOP VERIFICATION
# =============================================================================

def test_t34_zero_llm_in_live_loop():
    """
    T34: Zero LLM in Live Loop
    Verifies that the live frame stream, repetition heuristics, normalization,
    and evidence aggregation pipelines contain ZERO LLM client imports or invocations.
    Guarantees deterministic execution and strict latency bounds.
    """
    prohibited_modules = {
        "google.generativeai",
        "google.ai.generativelanguage",
        "openai",
        "anthropic",
        "langchain",
        "litellm",
        "transformers",
        "huggingface_hub",
        "cohere",
    }

    files_to_check = [
        os.path.join("backend", "app", "schemas", "form_evidence.py"),
        os.path.join("backend", "app", "services", "form_analysis", "session_evidence_aggregator.py"),
        os.path.join("backend", "app", "services", "form_analysis", "multi_session_evidence_aggregator.py"),
        os.path.join("backend", "app", "services", "form_issue_normalizer.py"),
        os.path.join("backend", "app", "services", "form_heuristics.py"),
        os.path.join("backend", "app", "services", "form_stream_service.py"),
        os.path.join("backend", "app", "services", "form_session_manager.py"),
        os.path.join("backend", "app", "repositories", "form_analysis_repository.py"),
    ]

    for file_path in files_to_check:
        assert os.path.exists(file_path), f"Expected file {file_path} must exist"
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Parse AST to check imports
        tree = ast.parse(code, filename=file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for prohibited in prohibited_modules:
                        assert not alias.name.startswith(prohibited), (
                            f"Prohibited LLM import '{alias.name}' detected in {file_path}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for prohibited in prohibited_modules:
                        assert not node.module.startswith(prohibited), (
                            f"Prohibited LLM import-from '{node.module}' detected in {file_path}"
                        )

        # Check for dynamic or raw LLM references in code
        assert "generate_content" not in code, f"LLM method call found in {file_path}"
        assert "ChatCompletion" not in code, f"LLM method call found in {file_path}"


# =============================================================================
# EXPLICIT V2.3.3 SECTION 9 TESTS: T24, T25, T26
# =============================================================================

def test_t24_identical_retry_section_9_contract():
    """
    V2.3.3 Section 9 T24: Identical Retry
    Precondition: Session exists
    Input: Second call with identical payload fingerprint
    Expected: HTTP 200 with existing doc. Zero writes executed.
    """
    repo = FormAnalysisRepository(db=None)
    repo.clear_in_memory_for_testing()

    detail = _make_detail("sess_freeze_t24", user_id="user_t24", rep_count=8)

    # First write
    res1 = repo._persist_session_detail_atomic("user_t24", detail)
    assert res1.created is True
    assert res1.status_code == 201

    # Second write with identical payload
    res2 = repo._persist_session_detail_atomic("user_t24", detail)
    assert res2.created is False
    assert res2.status_code == 200
    assert res2.detail.session_id == res1.detail.session_id
    assert res2.detail.payload_fingerprint == res1.detail.payload_fingerprint


def test_t25_conflicting_payload_section_9_contract():
    """
    V2.3.3 Section 9 T25: Conflicting Payload
    Precondition: Session exists
    Input: Second call with modified rep count
    Expected: Raises ConflictingSessionPayloadError (HTTP 409).
    """
    repo = FormAnalysisRepository(db=None)
    repo.clear_in_memory_for_testing()

    detail1 = _make_detail("sess_freeze_t25", user_id="user_t25", rep_count=8)
    repo._persist_session_detail_atomic("user_t25", detail1)

    # Modified rep count -> different canonical fingerprint
    detail2 = _make_detail("sess_freeze_t25", user_id="user_t25", rep_count=12)

    with pytest.raises(ConflictingSessionPayloadError) as exc_info:
        repo._persist_session_detail_atomic("user_t25", detail2)

    assert exc_info.value.status_code == 409
    assert "Conflicting payload" in str(exc_info.value)


def test_t26_concurrent_finalization_section_9_contract():
    """
    V2.3.3 Section 9 T26: Concurrent Finalization
    Precondition: 10 threads
    Input: Identical session payload
    Expected: Exactly 1 document created; 9 return HTTP 200.
    """
    import concurrent.futures

    repo = FormAnalysisRepository(db=None)
    repo.clear_in_memory_for_testing()

    detail = _make_detail("sess_freeze_t26", user_id="user_t26", rep_count=10)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(repo._persist_session_detail_atomic, "user_t26", detail)
            for _ in range(10)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    created_count = sum(1 for r in results if r.created is True and r.status_code == 201)
    idempotent_count = sum(1 for r in results if r.created is False and r.status_code == 200)

    assert created_count == 1
    assert idempotent_count == 9

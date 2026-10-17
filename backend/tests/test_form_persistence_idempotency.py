"""
Focused Unit Tests for FormAnalysisRepository Persistence & Idempotency (Subphase 9C.6.2.4).

Covers:
- T24: First persistence succeeds (HTTP 201 equivalent, created=True, payload_fingerprint attached).
- T25: Identical retry is idempotent (HTTP 200 equivalent, created=False, zero duplicate writes).
- T26: Conflicting retry rejected (HTTP 409 equivalent ConflictingSessionPayloadError, original payload unchanged).
- Concurrent finalization safety (multi-threaded race condition safety).
- Deterministic SHA-256 canonical fingerprint generation:
    * Key ordering invariance (sort_keys=True)
    * Whitespace normalization
    * Semantic payload invariance
- Firestore transaction atomicity (read before write inside transaction context).
"""

import concurrent.futures
import hashlib
import json
from typing import Any, Dict, List, Optional
import pytest
from unittest.mock import MagicMock

from backend.app.schemas.form_analysis import (
    FormAnalysisSessionDetailSchema,
    CompactRepSummarySchema,
)
from backend.app.repositories.form_analysis_repository import (
    FormAnalysisRepository,
    ConflictingSessionPayloadError,
    SessionPersistenceResult,
    compute_payload_fingerprint,
    _to_canonical_serializable,
)


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

@pytest.fixture
def repo() -> FormAnalysisRepository:
    """Isolated FormAnalysisRepository using thread-safe in-memory store."""
    repository = FormAnalysisRepository(db=None)
    repository.clear_in_memory_for_testing()
    return repository


def make_test_detail(
    session_id: str = "sess-pers-1",
    user_id: str = "user-123",
    exercise_id: str = "ex_squat",
    rep_count: int = 5,
    duration_seconds: int = 45,
    client_notes: Optional[str] = "Good session",
) -> FormAnalysisSessionDetailSchema:
    """Constructs a valid FormAnalysisSessionDetailSchema instance."""
    reps = [
        CompactRepSummarySchema(
            rep_number=i + 1,
            status="valid",
            score=90.0,
            rom_degrees=95.0,
            duration_ms=2100.0,
            category_scores={"ROM": 95.0},
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
        started_at="2026-09-28T10:00:00Z",
        completed_at="2026-09-28T10:00:45Z",
        duration_seconds=duration_seconds,
        total_reps=rep_count,
        completed_reps=rep_count,
        valid_reps=rep_count,
        incomplete_reps=0,
        invalid_reps=0,
        insufficient_data_reps=0,
        overall_score=90.0,
        best_score=90.0,
        worst_score=90.0,
        category_averages={"ROM": 95.0},
        summary_feedback=[],
        reps=reps,
        created_at="2026-09-28T10:00:45Z",
        client_notes=client_notes,
    )


# =============================================================================
# DETERMINISTIC CANONICAL SHA-256 FINGERPRINT TESTS
# =============================================================================

def test_canonical_fingerprint_deterministic_and_reproducible():
    """Verifies that identical semantic inputs produce the exact same SHA-256 fingerprint."""
    reps = [{"rep_number": 1, "score": 90.0}]

    fp1 = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=reps,
        client_duration_seconds=60,
        client_notes="Note",
    )
    fp2 = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=reps,
        client_duration_seconds=60,
        client_notes="Note",
    )

    assert fp1 == fp2
    assert len(fp1) == 64
    assert int(fp1, 16) > 0  # Valid hex digest


def test_canonical_fingerprint_key_ordering_invariance():
    """Verifies that dict key ordering does not alter the canonical fingerprint."""
    dict_a = {"z_key": 1, "a_key": 2, "m_key": 3}
    dict_b = {"a_key": 2, "m_key": 3, "z_key": 1}

    fp_a = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=[dict_a],
    )
    fp_b = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=[dict_b],
    )

    assert fp_a == fp_b


def test_canonical_fingerprint_sensitivity_to_modifications():
    """Verifies that any modification to reps, duration, or exercise changes the fingerprint."""
    base_fp = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=[{"rep": 1}],
        client_duration_seconds=60,
    )

    # Different rep count/content
    diff_reps_fp = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=[{"rep": 1}, {"rep": 2}],
        client_duration_seconds=60,
    )
    assert base_fp != diff_reps_fp

    # Different duration
    diff_dur_fp = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_squat",
        reps=[{"rep": 1}],
        client_duration_seconds=90,
    )
    assert base_fp != diff_dur_fp

    # Different exercise
    diff_ex_fp = compute_payload_fingerprint(
        user_id="user_a",
        session_id="sess_1",
        canonical_exercise_id="ex_deadlift",
        reps=[{"rep": 1}],
        client_duration_seconds=60,
    )
    assert base_fp != diff_ex_fp


# =============================================================================
# T24: FIRST PERSISTENCE SUCCEEDS (HTTP 201 EQUIVALENT)
# =============================================================================

def test_t24_first_persistence_succeeds(repo: FormAnalysisRepository):
    """
    T24: First submission of a finalized session:
    - Successfully persisted.
    - Result status_code == 201, created == True.
    - SHA-256 fingerprint generated and attached to persisted record.
    """
    detail = make_test_detail(session_id="sess-t24", user_id="user-t24")
    result = repo._persist_session_detail_atomic(uid="user-t24", detail=detail)

    assert result.created is True
    assert result.status_code == 201
    assert result.detail.session_id == "sess-t24"
    assert result.detail.payload_fingerprint is not None
    assert len(result.detail.payload_fingerprint) == 64

    # Verify document is retrievable
    retrieved = repo.get_session_summary("user-t24", "sess-t24")
    assert retrieved is not None
    assert retrieved.payload_fingerprint == result.detail.payload_fingerprint


# =============================================================================
# T25: IDENTICAL RETRY IS IDEMPOTENT (HTTP 200 EQUIVALENT, ZERO WRITES)
# =============================================================================

def test_t25_identical_retry_is_idempotent(repo: FormAnalysisRepository):
    """
    T25: Identical retry with same session_id and identical payload:
    - Returns existing persisted document successfully.
    - Result status_code == 200, created == False.
    - Zero duplicate documents created.
    """
    detail = make_test_detail(session_id="sess-t25", user_id="user-t25")

    # 1. First submission
    res1 = repo._persist_session_detail_atomic(uid="user-t25", detail=detail)
    assert res1.created is True
    assert res1.status_code == 201

    # 2. Identical retry
    res2 = repo._persist_session_detail_atomic(uid="user-t25", detail=detail)
    assert res2.created is False
    assert res2.status_code == 200
    assert res2.detail.session_id == res1.detail.session_id
    assert res2.detail.payload_fingerprint == res1.detail.payload_fingerprint

    # 3. Verify exactly 1 session exists in history
    history = repo.list_user_history("user-t25")
    assert len(history) == 1
    assert history[0].session_id == "sess-t25"


# =============================================================================
# T26: CONFLICTING RETRY REJECTED (HTTP 409 CONFLICT EQUIVALENT)
# =============================================================================

def test_t26_conflicting_retry_raises_conflict_and_preserves_original(repo: FormAnalysisRepository):
    """
    T26: Conflicting retry with same session_id but modified payload (e.g. altered rep count):
    - Raises ConflictingSessionPayloadError (HTTP 409 Conflict equivalent).
    - Original persisted payload remains completely untouched and unchanged.
    """
    detail_original = make_test_detail(
        session_id="sess-t26",
        user_id="user-t26",
        rep_count=5,
        duration_seconds=45,
    )

    # 1. First submission succeeds
    res1 = repo._persist_session_detail_atomic(uid="user-t26", detail=detail_original)
    original_fp = res1.detail.payload_fingerprint
    assert res1.created is True

    # 2. Conflicting submission with different reps (e.g. 10 reps instead of 5)
    detail_conflicting = make_test_detail(
        session_id="sess-t26",
        user_id="user-t26",
        rep_count=10,  # MODIFIED!
        duration_seconds=45,
    )

    with pytest.raises(ConflictingSessionPayloadError) as exc_info:
        repo._persist_session_detail_atomic(uid="user-t26", detail=detail_conflicting)

    err = exc_info.value
    assert err.session_id == "sess-t26"
    assert err.status_code == 409
    assert err.existing_fingerprint == original_fp
    assert err.new_fingerprint != original_fp

    # 3. Invariant: Original document remains completely intact and uncorrupted
    retrieved = repo.get_session_summary("user-t26", "sess-t26")
    assert retrieved is not None
    assert retrieved.total_reps == 5  # Still 5, never 10
    assert retrieved.payload_fingerprint == original_fp


# =============================================================================
# CONCURRENT FINALIZATION & TRANSACTION ATOMICITY
# =============================================================================

def test_concurrent_finalization_creates_exactly_one_document(repo: FormAnalysisRepository):
    """
    Concurrency safety test: 10 concurrent threads finalize the identical session payload.
    Exactly 1 thread creates the document (created=True, 201);
    9 threads receive the existing document (created=False, 200).
    """
    detail = make_test_detail(session_id="sess-concurrency", user_id="user-conc")

    results: List[SessionPersistenceResult] = []

    def _worker():
        return repo._persist_session_detail_atomic(uid="user-conc", detail=detail)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_worker) for _ in range(10)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    created_count = sum(1 for r in results if r.created is True)
    retry_count = sum(1 for r in results if r.created is False)

    assert created_count == 1
    assert retry_count == 9

    # Verify exactly 1 history entry
    history = repo.list_user_history("user-conc")
    assert len(history) == 1


# =============================================================================
# FIRESTORE TRANSACTION ATOMICITY WITH MOCKED CLIENT
# =============================================================================

def test_firestore_transactional_execution_path():
    """
    Verifies that when Firestore db is configured, document lookup and write
    occur strictly inside the transaction context (transaction.set).
    """
    mock_db = MagicMock()
    mock_transaction = MagicMock()
    mock_db.transaction.return_value = mock_transaction

    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref

    # First call: document does not exist
    mock_snapshot_nonexistent = MagicMock()
    mock_snapshot_nonexistent.exists = False
    mock_doc_ref.get.return_value = mock_snapshot_nonexistent

    repo_mock = FormAnalysisRepository(db=mock_db)
    detail = make_test_detail(session_id="sess-txn-1", user_id="user-txn")

    # 1. First submission
    res1 = repo_mock._persist_session_detail_atomic(uid="user-txn", detail=detail)
    assert res1.created is True
    assert res1.status_code == 201

    # Verify doc_ref.get was called with transaction context
    mock_doc_ref.get.assert_called_with(transaction=mock_transaction)
    # Verify transaction.set was called to persist
    mock_transaction.set.assert_called_once()

    # 2. Second call: identical retry (snapshot exists with matching fingerprint)
    mock_snapshot_exists = MagicMock()
    mock_snapshot_exists.exists = True
    mock_snapshot_exists.to_dict.return_value = res1.detail.model_dump(mode="json")
    mock_doc_ref.get.return_value = mock_snapshot_exists

    mock_transaction.set.reset_mock()
    res2 = repo_mock._persist_session_detail_atomic(uid="user-txn", detail=detail)
    assert res2.created is False
    assert res2.status_code == 200

    # Verify transaction.set was NOT called on identical retry
    mock_transaction.set.assert_not_called()

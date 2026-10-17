"""
Comprehensive Verification Test Suite for Canonical Exercise Repository Integration (Stage 1).

Validates:
1. ExerciseRepository.list_exercises() returns all 100 canonical exercises.
2. All 100 canonical exercise IDs are unique and retrievable through get_by_id().
3. Every canonical catalog record converts into ExerciseKnowledgeSchema and ExerciseSchema without metadata loss.
4. Every exercise ID in the canonical catalog resolves to the correct exercise, never a different exercise.
5. GET /api/v1/exercises returns all 100 exercises using the real repository.
6. Detail endpoints return correct metadata for exercises previously missing:
   - ex_romanian_deadlift
   - ex_bulgarian_split_squat (resolves via canonical ID alias)
   - ex_incline_dumbbell_press (resolves via canonical ID alias)
7. Unknown exercise IDs return a proper 404 not-found response.
8. Filter querying (muscle, equipment, difficulty, category, search) across all 100 canonical records.
9. In-memory store and ensure_seeded idempotency.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.exercise_repository import (
    ExerciseRepository,
    get_exercise_repository,
    EXERCISE_ID_ALIASES,
)
from backend.app.schemas.exercise import ExerciseKnowledgeSchema
from backend.app.schemas.workout import ExerciseSchema
from backend.app.seeds.exercise_catalog import (
    RAW_CATALOG_DATA,
    EXERCISE_CATALOG,
    CATALOG_BY_ID,
)


@pytest.fixture
def repo() -> ExerciseRepository:
    """Isolated in-memory ExerciseRepository instance loaded with canonical catalog."""
    return ExerciseRepository(db=None)


# =============================================================================
# 1. EXACT CANONICAL COUNT & REPOSITORY LISTING
# =============================================================================

def test_repository_list_all_100_canonical_exercises(repo: ExerciseRepository):
    """1. Proves ExerciseRepository.list_exercises() returns all 100 canonical exercises."""
    exercises = repo.list_exercises()
    assert len(exercises) == 100, f"Expected 100 canonical exercises, found {len(exercises)}"
    
    # Ensure every returned item is an instance of ExerciseKnowledgeSchema and ExerciseSchema
    for ex in exercises:
        assert isinstance(ex, ExerciseKnowledgeSchema)
        assert isinstance(ex, ExerciseSchema)


# =============================================================================
# 2. ID UNIQUENESS & RETRIEVAL OF ALL 100 CANONICAL EXERCISES
# =============================================================================

def test_all_100_canonical_exercise_ids_unique_and_retrievable(repo: ExerciseRepository):
    """2. Proves all 100 canonical IDs are unique and retrievable via get_by_id()."""
    all_ids = [item["id"] for item in RAW_CATALOG_DATA]
    assert len(all_ids) == 100
    assert len(set(all_ids)) == 100, "Duplicate exercise IDs detected in catalog seeds"

    for ex_id in all_ids:
        ex = repo.get_by_id(ex_id)
        assert ex is not None, f"Failed to retrieve canonical exercise '{ex_id}' via get_by_id"
        assert ex.id == ex_id, f"ID mismatch: requested '{ex_id}', received '{ex.id}'"
        assert len(ex.name.strip()) > 0
        assert len(ex.primaryMuscles) > 0


# =============================================================================
# 3. SCHEMA CONVERSION & METADATA PRESERVATION
# =============================================================================

def test_canonical_catalog_records_convert_without_metadata_loss():
    """3. Proves every canonical catalog record converts into schemas without metadata loss."""
    assert len(RAW_CATALOG_DATA) == 100

    for raw in RAW_CATALOG_DATA:
        # Convert to ExerciseKnowledgeSchema
        schema_obj = ExerciseKnowledgeSchema(**raw)
        assert schema_obj.id == raw["id"]
        assert schema_obj.name == raw["name"]
        assert schema_obj.primaryMuscles == raw["primaryMuscles"]
        assert schema_obj.secondaryMuscles == raw.get("secondaryMuscles", [])
        assert schema_obj.equipment == raw.get("equipment", [])
        assert schema_obj.difficulty == raw.get("difficulty", "intermediate")
        assert schema_obj.category == raw.get("category", "strength")
        assert schema_obj.instructions == raw.get("instructions", [])
        assert schema_obj.safetyNotes == raw.get("safetyNotes", [])
        assert schema_obj.commonMistakes == raw.get("commonMistakes", [])
        assert schema_obj.movementPattern == raw["movementPattern"]
        assert schema_obj.exerciseType == raw["exerciseType"]
        assert schema_obj.laterality == raw["laterality"]
        assert schema_obj.targetEnvironments == raw["targetEnvironments"]
        assert schema_obj.progressions == raw.get("progressions", [])
        assert schema_obj.regressions == raw.get("regressions", [])
        assert schema_obj.substitutions == raw.get("substitutions", [])
        assert schema_obj.complementaryExercises == raw.get("complementaryExercises", [])

        # Backward compatibility with ExerciseSchema
        base_schema = ExerciseSchema(**raw)
        assert base_schema.id == raw["id"]
        assert base_schema.name == raw["name"]


# =============================================================================
# 4. EXACT RESOLUTION INTEGRITY (NEVER WRONG EXERCISE)
# =============================================================================

def test_every_catalog_id_resolves_to_correct_exercise(repo: ExerciseRepository):
    """4. Proves every ID in canonical catalog resolves to the correct exercise and never another."""
    for catalog_id, catalog_item in CATALOG_BY_ID.items():
        retrieved = repo.get_by_id(catalog_id)
        assert retrieved is not None
        assert retrieved.id == catalog_id
        assert retrieved.name == catalog_item.name
        assert retrieved.movementPattern == catalog_item.movementPattern
        assert retrieved.primaryMuscles == catalog_item.primaryMuscles


# =============================================================================
# 5. REAL API LIST ENDPOINT RETURNS ALL 100 CANONICAL EXERCISES
# =============================================================================

def test_api_list_exercises_returns_100_canonical(client: TestClient, repo: ExerciseRepository):
    """5. Proves GET /api/v1/exercises returns all 100 exercises using real repository."""
    app.dependency_overrides[get_exercise_repository] = lambda: repo
    try:
        response = client.get("/api/v1/exercises")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 100, f"Expected 100 exercises in API response, got {len(data)}"
        
        # Verify IDs in API response match canonical IDs exactly
        response_ids = {ex["id"] for ex in data}
        canonical_ids = set(CATALOG_BY_ID.keys())
        assert response_ids == canonical_ids
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 6. DETAIL ENDPOINT FOR PREVIOUSLY MISSING EXERCISES & ALIASES
# =============================================================================

def test_api_detail_previously_missing_exercises(client: TestClient, repo: ExerciseRepository):
    """
    6. Proves detail endpoints return correct metadata for exercises that were previously missing:
       - ex_romanian_deadlift (Barbell Romanian Deadlift)
       - ex_bulgarian_split_squat (Bulgarian Split Squat, resolved via alias)
       - ex_incline_dumbbell_press (Incline Dumbbell Press, resolved via alias)
    """
    app.dependency_overrides[get_exercise_repository] = lambda: repo
    try:
        # 1. Romanian Deadlift (canonical ID: ex_romanian_deadlift)
        res_rdl = client.get("/api/v1/exercises/ex_romanian_deadlift")
        assert res_rdl.status_code == 200
        data_rdl = res_rdl.json()
        assert data_rdl["id"] == "ex_romanian_deadlift"
        assert "Romanian Deadlift" in data_rdl["name"]
        assert "hamstrings" in data_rdl["primaryMuscles"]
        assert "glutes" in data_rdl["secondaryMuscles"] or "glutes" in data_rdl["primaryMuscles"]
        assert "barbell" in data_rdl["equipment"]
        assert len(data_rdl["instructions"]) > 0

        # 2. Bulgarian Split Squat (alias: ex_bulgarian_split_squat -> ex_bulgarian_squat)
        res_bss_alias = client.get("/api/v1/exercises/ex_bulgarian_split_squat")
        assert res_bss_alias.status_code == 200
        data_bss = res_bss_alias.json()
        assert data_bss["id"] == "ex_bulgarian_squat"
        assert "Bulgarian Split Squat" in data_bss["name"]
        assert "quadriceps" in data_bss["primaryMuscles"]
        assert len(data_bss["instructions"]) > 0

        # Also verify canonical ID works directly
        res_bss_canon = client.get("/api/v1/exercises/ex_bulgarian_squat")
        assert res_bss_canon.status_code == 200
        assert res_bss_canon.json()["id"] == "ex_bulgarian_squat"

        # 3. Incline Dumbbell Press (alias: ex_incline_dumbbell_press -> ex_incline_db_press)
        res_inc_alias = client.get("/api/v1/exercises/ex_incline_dumbbell_press")
        assert res_inc_alias.status_code == 200
        data_inc = res_inc_alias.json()
        assert data_inc["id"] == "ex_incline_db_press"
        assert "Incline Dumbbell Press" in data_inc["name"]
        assert "chest" in data_inc["primaryMuscles"]
        assert "dumbbells" in data_inc["equipment"]
        assert len(data_inc["instructions"]) > 0

        # Also verify canonical ID works directly
        res_inc_canon = client.get("/api/v1/exercises/ex_incline_db_press")
        assert res_inc_canon.status_code == 200
        assert res_inc_canon.json()["id"] == "ex_incline_db_press"
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 7. UNKNOWN EXERCISE ID HANDLING (404)
# =============================================================================

def test_api_unknown_exercise_id_returns_404(client: TestClient, repo: ExerciseRepository):
    """7. Proves unknown exercise IDs return HTTP 404 with proper error detail."""
    app.dependency_overrides[get_exercise_repository] = lambda: repo
    try:
        response = client.get("/api/v1/exercises/ex_completely_unknown_xyz")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # Non-ex_ prefix also returns 404
        res_bogus = client.get("/api/v1/exercises/non_existent_id_42")
        assert res_bogus.status_code == 404
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 8. QUERY FILTERING ACROSS CANONICAL 100 EXERCISES
# =============================================================================

def test_repository_filtering_across_canonical_catalog(repo: ExerciseRepository):
    """8. Proves multi-attribute filtering works reliably across all 100 canonical records."""
    # Filter by muscle
    chest_exercises = repo.list_exercises(muscle="chest")
    assert len(chest_exercises) >= 12
    for e in chest_exercises:
        assert "chest" in [m.lower() for m in e.primaryMuscles + e.secondaryMuscles]

    # Filter by equipment
    barbell_exercises = repo.list_exercises(equipment="barbell")
    assert len(barbell_exercises) >= 15
    for e in barbell_exercises:
        assert "barbell" in [eq.lower() for eq in e.equipment]

    # Filter by difficulty
    advanced_exercises = repo.list_exercises(difficulty="advanced")
    assert len(advanced_exercises) > 0
    for e in advanced_exercises:
        assert e.difficulty == "advanced"

    # Search query matching aliases
    rdl_search = repo.list_exercises(search="RDL")
    assert len(rdl_search) >= 2
    assert any("romanian" in e.name.lower() for e in rdl_search)


# =============================================================================
# 9. IN-MEMORY IMMUTABILITY & ENSURE_SEEDED IDEMPOTENCY
# =============================================================================

def test_ensure_seeded_and_store_isolation():
    """9. Proves ExerciseRepository initializes isolated in-memory stores with 100 items."""
    repo1 = ExerciseRepository(db=None)
    repo2 = ExerciseRepository(db=None)
    
    assert len(repo1._in_memory_store) == 100
    assert len(repo2._in_memory_store) == 100

    # Ensure no-op when db is None
    repo1.ensure_seeded()
    assert len(repo1._in_memory_store) == 100

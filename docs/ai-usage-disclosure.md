# AI Usage Disclosure

This document answers the assessment questions directly.

## 1. Did you use AI tools? If yes, where?

Yes. AI tools were used heavily during the coding phase after I simplified the problem into smaller backend modules and defined the overall structure, database relationships, route layout, and workflow boundaries.

AI support covered the implementation work, especially:

- aviation state machine implementation
- pytest coverage for edge cases and workflow enforcement
- Docker Compose wiring
- Alembic migration boilerplate
- documentation drafting and polishing

The overall architecture, API structure, database model, workflow boundaries, and business-rule design were defined by me, and AI was used as the coding accelerator under my direction.

## 2. What did AI generate?

AI generated the implementation code, helper ideas, draft snippets, and boilerplate for the backend after I had already simplified the problem and broken the system into smaller parts.

Examples of what AI helped draft:

- state-transition guard logic
- initial test-case skeletons
- Docker Compose and migration boilerplate
- documentation wording and section structure

AI did not design the backend on its own. It produced the coding work under my direction after the project direction was already fixed.

## 3. What did you manually review or change?

I manually reviewed and adjusted the AI-generated code before keeping it in the repository.

I changed:

- route wiring and function names to match the project conventions
- service-layer business rules so they matched the assessment workflow exactly
- database relationships and foreign-key usage
- seed data so the demo records matched the required aviation scenarios
- test assertions so they covered invalid actions, not just happy paths
- documentation tone so it reads like final submission documentation rather than a working draft

The final backend behavior reflects my review, correction, and guidance over the AI-generated implementation.

## 4. Which AI-generated suggestion did you reject and why?

AI suggested a lossy defect model that would have collapsed too much information into aircraft status and a minimal fault flag.

I rejected that suggestion because it would have removed important aviation traceability:

- defects need their own table
- defects need severity and status history
- defects need audit logs
- defects need to be visible independently from the aircraft record

I reformulated the model so defects remain first-class records tied to aircraft and sorties, which better matches the assessment and real aviation operations.

## 5. Which part of the project did you personally design?

I personally designed the most important structural parts of the project:

- the relational database schema
- the route structure and API grouping
- the role and permission model
- the workflow boundaries between sorties, training progress, defects, and aircraft readiness
- the seed-data relationships
- the documentation structure

The backend organization was planned by me first, and AI was then used to implement the coding work under that structure.

## 6. Which part are you least confident about?

The most delicate part of the backend is the recovery flow after severe defects, especially the interaction between:

- aircraft readiness
- sortie closure
- `AIRCRAFT_GROUNDED`
- `RECOVERY_REQUIRED`
- defect resolution

That area is the hardest because it combines safety logic, workflow state, and auditability in one sequence.

## 7. Pick one backend route and explain it line by line.

I am using `PATCH /sorties/{sortie_id}/release` from [app/api/routes/sorties.py](/C:/Users/Sohan%20Sarkar/Documents/Airman/app/api/routes/sorties.py) as the example.

```python
@router.patch("/{sortie_id}/release", response_model=SortieResponse)
def patch_release_sortie(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(release_sortie(db, current_user, sortie_id))
```

Line by line:

- `@router.patch("/{sortie_id}/release", response_model=SortieResponse)`
  - registers the route as a `PATCH` endpoint
  - uses the sortie id in the path
  - tells FastAPI to serialize the response as `SortieResponse`
- `def patch_release_sortie(`
  - defines the endpoint handler
  - the route itself stays thin and delegates business logic to the service layer
- `sortie_id: int,`
  - receives the sortie identifier from the URL path
- `db: Session = Depends(get_db),`
  - injects a database session for the request
  - the route does not create its own session manually
- `current_user: User = Depends(get_current_user),`
  - loads the authenticated caller from the bearer token
  - the permission model is enforced against the real user object
- `) -> SortieResponse:`
  - documents the endpoint return type for readability and OpenAPI
- `return SortieResponse.model_validate(release_sortie(db, current_user, sortie_id))`
  - calls the service function that contains the actual workflow rules
  - validates the returned ORM object against the response schema
  - returns a clean API payload rather than exposing raw database objects

This route matters because it keeps HTTP handling separate from aviation workflow enforcement.

## 8. Pick one business rule and explain how your code enforces it.

I am using the rule "a sortie cannot close before training approval" from [app/services/sortie_service.py](/C:/Users/Sohan%20Sarkar/Documents/Airman/app/services/sortie_service.py).

```python
def close_sortie(session: Session, actor: User, sortie_id: int) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if sortie.status not in {SortieStatus.TRAINING_APPROVED, SortieStatus.RECOVERY_REQUIRED}:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to CLOSED")
    progress = sortie.training_progress
    if progress is None or progress.status != TrainingStatus.APPROVED:
        raise invalid_state("Sortie cannot close before training approval")
    open_severe_defects = [
        defect
        for defect in sortie.aircraft.defects
        if defect.status == DefectStatus.OPEN and defect.severity in {DefectSeverity.HIGH, DefectSeverity.CRITICAL}
    ]
    if open_severe_defects:
        raise conflict("Sortie cannot close until defect recovery is completed")
    sortie.aircraft.status = AircraftStatus.READY
    _transition_sortie(
        session,
        actor=actor,
        sortie=sortie,
        allowed_from={SortieStatus.TRAINING_APPROVED, SortieStatus.RECOVERY_REQUIRED},
        next_status=SortieStatus.CLOSED,
        action="SORTIE_CLOSED",
    )
    session.commit()
    session.refresh(sortie)
    return sortie
```

How the rule is enforced:

- `require_role(actor, [RoleEnum.DISPATCHER])`
  - only dispatchers or admins can close a sortie
- `sortie = get_sortie(session, actor, sortie_id)`
  - loads the sortie and applies the visibility rules
- `if sortie.status not in {SortieStatus.TRAINING_APPROVED, SortieStatus.RECOVERY_REQUIRED}:`
  - blocks closure from any invalid state
- `raise invalid_state(...)`
  - returns a structured workflow error instead of silently accepting the action
- `progress = sortie.training_progress`
  - checks whether the sortie has a linked training record
- `if progress is None or progress.status != TrainingStatus.APPROVED:`
  - blocks closure if the training has not been approved by a CFI
- `open_severe_defects = [...]`
  - scans the aircraft for open high or critical defects
- `if open_severe_defects:`
  - prevents closure if the safety issue has not been cleared
- `sortie.aircraft.status = AircraftStatus.READY`
  - restores aircraft readiness only after the workflow is safe
- `_transition_sortie(...)`
  - performs the final state transition to `CLOSED`
  - writes the audit log entry
- `session.commit()`
  - persists the transition as one transaction
- `session.refresh(sortie)`
  - reloads the updated ORM object before returning it

This rule matters because it prevents the backend from marking a sortie complete before training and safety requirements are satisfied.

## 9. Pick one test and explain why it matters.

I am using `test_cannot_mark_scheduled_sortie_airborne_directly` from [tests/test_sorties.py](/C:/Users/Sohan%20Sarkar/Documents/Airman/tests/test_sorties.py).

```python
def test_cannot_mark_scheduled_sortie_airborne_directly(client, dispatcher_headers):
    response = client.patch("/sorties/1/airborne", headers=dispatcher_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "INVALID_STATE_TRANSITION"
```

Why each line matters:

- `def test_cannot_mark_scheduled_sortie_airborne_directly(...):`
  - declares an invalid-workflow test, not a happy-path test
- `response = client.patch("/sorties/1/airborne", headers=dispatcher_headers)`
  - simulates a dispatcher calling the route directly
  - this is the exact kind of real API misuse the backend must reject
- `assert response.status_code == 409`
  - confirms the API rejects the invalid state change with a conflict-style workflow error
- `assert response.json()["error"] == "INVALID_STATE_TRANSITION"`
  - confirms the rejection is structured and specific
  - the frontend or reviewer can distinguish workflow rejection from validation or permission failure

This test matters because aviation workflow bugs are often invalid transitions that appear harmless until they are exercised directly.

## 10. What would break first if this backend had 10 flight schools using it?

The first pressure point would be multi-tenant scale and data isolation, not the route definitions themselves.

The main things that would need to improve first are:

- stronger tenant boundaries than base-scoped checks alone
- more explicit query pagination envelopes for large datasets
- database indexing tuned for multi-school filtering
- structured request tracing for debugging across many operators
- a real authentication system instead of mock login
- production PostgreSQL settings and connection pooling

In practice, the first visible weakness would be read-heavy list endpoints and tenant isolation rules under higher concurrency. The workflow logic is sound for the assessment scope, but a real multi-school rollout would need production-grade tenancy and operations hardening.

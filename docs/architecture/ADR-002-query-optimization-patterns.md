# ADR-002: Query Optimization Patterns and N+1 Prevention

**Date**: 2026-04-24  
**Status**: ACCEPTED  
**Author**: Architecture Review  

## Context

The codebase previously had several endpoints that risked N+1 query patterns:
- Fetching job lists with related data
- Retrieving chapters for display
- Batch operations over multiple jobs

N+1 queries occur when a query fetches parent records, then a separate query fetches child records for each parent in a loop. Example:

```python
# BAD: N+1 pattern
jobs = fetch_all_jobs()  # 1 query
for job in jobs:
    chapters = fetch_chapters(job.id)  # N queries
```

Additionally, some endpoints were fetching all columns when only a subset was needed (overfetching).

## Decision

Establish and document **standard query optimization patterns** as best practices:

1. **Batch Queries**: Use `batch_*` functions for fetching related data
2. **Field Selection**: Explicitly select only needed columns
3. **Predefined Selections**: Common field sets stored as constants
4. **Code Review**: Query optimization reviewed during code review

Implement in `app/services/query_optimization.py` with:
- `batch_jobs_by_id()` - Fetch multiple jobs in one query
- `batch_chapters_by_job_id()` - Fetch all chapters for a job
- `select_minimal_fields()` - Build efficient column selections
- Predefined field constants for common use cases

## Rationale

### Why Patterns vs Framework?
- **Simplicity**: No ORM overhead, explicit control
- **Clarity**: Pattern names indicate intent (batch, minimal fields)
- **Flexibility**: Easy to extend for new query patterns
- **Learning**: Developers understand query behavior at SQL level

### Why Predefined Constants?
- **Reusability**: `LISTING_JOB_FIELDS` used across endpoints
- **Consistency**: Same columns selected everywhere for job lists
- **Maintenance**: Change definition once, affects all uses
- **Documentation**: Constant names indicate purpose (MINIMAL vs FULL)

### Performance Targets
- **Single Job Lookup**: ~10-50ms (no change, already optimized)
- **Batch 100 Jobs**: ~50-100ms (1 query vs 100)
- **Chapter Listing**: ~20-30ms (1 query vs N)
- **Database Bytes**: Reduce by 60% via field selection

## Consequences

### Positive
- **Query Count**: Reduce N+1 from worst case to 1-2 queries per request
- **Latency**: Batch operations 10-100x faster
- **Bandwidth**: Field selection reduces data transfer by 60%
- **Scalability**: Can handle batch operations on thousands of records
- **Developer Experience**: Clear patterns to follow (less thinking)

### Negative
- **Boilerplate**: Some endpoints need `select_minimal_fields()` call
- **Maintenance**: New patterns require additions to query_optimization.py
- **Testing**: Batch functions need tests for correctness

### Mitigation
- **Templates**: Copy-paste examples in docstrings
- **Code Review**: Catch N+1 patterns before merge
- **Monitoring**: Query count metrics alert on regressions

## Implementation Details

### Core Functions

```python
# Batch fetch (prevents N+1)
jobs = batch_jobs_by_id(supabase, ["id-1", "id-2", "id-3"])

# Efficient field selection
fields = select_minimal_fields(["id", "status", "created_at"])
query.select(fields)

# Predefined selections
query.select(LISTING_JOB_FIELDS)  # Consistent across endpoints
```

### Field Sets

| Set | Fields | Use Case |
|-----|--------|----------|
| MINIMAL | id, status, created_at, updated_at | Status checks, existence verification |
| LISTING | + config | Job list endpoints |
| COVER | Subset for cover operations | Cover approval flow |
| FULL | * | Detailed job view, rare cases |

### Application Pattern

```python
# Endpoint: GET /v1/jobs (list with pagination)
@router.get("/jobs")
async def list_jobs(supabase: Client):
    result = (
        supabase
        .table("jobs")
        .select(LISTING_JOB_FIELDS)  # Explicit, minimal selection
        .order("created_at", desc=True)
        .range(0, 19)
        .execute()
    )
    return result.data

# Endpoint: POST /batch/approve (approve multiple covers)
@router.post("/batch/approve")
async def batch_approve(body: BatchApproveRequest, supabase: Client):
    jobs = batch_jobs_by_id(  # 1 query instead of N
        supabase,
        body.job_ids,
        fields=COVER_JOB_FIELDS
    )
    # ... process jobs
```

## Testing Strategy

1. **Unit Tests**: Verify batch functions return correct data
2. **Query Count Tests**: Assert single query for batch operations
3. **Field Selection Tests**: Verify only requested columns returned
4. **Regression Tests**: Monitor query count in integration tests

## Monitoring

### Metrics
- Query count per request (detect N+1)
- Database bytes per request (validate field selection)
- Batch operation latency (track improvement)

### Alerts
- Query count > 5 per single endpoint request
- Unexpected increase in bytes/request (field creep)

## Migration Strategy

### Phase 1 (Immediate)
- New endpoints use batch functions and field selection
- Document patterns in code review template

### Phase 2 (This Sprint)
- Audit existing endpoints for N+1 patterns
- Convert high-traffic endpoints (job list, chapter list)

### Phase 3 (Next Sprint)
- Convert remaining endpoints
- Remove deprecated query patterns

## Alternatives Considered

### A. Use ORM (SQLAlchemy, Tortoise)
- **Pros**: Relationships automatic, eager loading easy
- **Cons**: Added dependency, learning curve, abstraction overhead

### B. GraphQL
- **Pros**: Clients request exact fields, no overfetching
- **Cons**: Complete rewrite, added server complexity

### C. Manual SQL with Indexes
- **Pros**: Full control, optimal queries
- **Cons**: Raw SQL queries error-prone, no type safety

**Selected**: Option A (Patterns) for balance of simplicity and performance

## References

- `app/services/query_optimization.py` - Pattern implementations
- `app/api/jobs.py` - Example usage: list_jobs endpoint
- `app/api/chapters.py` - Example usage: batch chapter operations
- Performance testing results (to be added post-implementation)

## Review & Sunset

Review this ADR in **Q3 2026** to validate:
- Are N+1 patterns eliminated? (Target: 0 detected)
- Query count trends (Target: stay ≤ 2 per request)
- Developer adoption of batch functions (Target: 100% new code)
- If new ORM adopted, revisit this approach

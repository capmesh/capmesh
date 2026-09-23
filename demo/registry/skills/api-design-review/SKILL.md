# API Design Review Skill

## Purpose
Review REST/GraphQL/gRPC API definitions for consistency,
completeness, and adherence to design standards.

## Procedure

### Step 1 — Load API Specs
Use `repository.read/v1` to load:
- OpenAPI/Swagger specifications
- GraphQL schema files
- gRPC .proto definitions
- Postman/Insomnia collections
- API changelog

### Step 2 — Consistency Check
Use `code.quality/v1` to validate:
- Naming conventions (camelCase vs snake_case, plural resources)
- HTTP method semantics (GET never mutates, etc.)
- Status code correctness
- Pagination patterns (cursor vs offset)
- Error response format standardisation

### Step 3 — Completeness Review
Verify:
- All endpoints documented with request/response schemas
- Authentication documented per endpoint
- Rate limiting documented
- Deprecation notices present where applicable

### Step 4 — Report
Produce an APIDesignReport with:
- Violations table (endpoint, issue, severity, recommendation)
- Consistency score (0-100)
- Breaking change analysis vs. previous version
- Overall: APPROVED / REVISE

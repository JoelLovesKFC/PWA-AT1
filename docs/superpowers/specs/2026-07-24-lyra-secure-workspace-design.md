# LYRA Secure Workspace Refurbishment Design

**Date:** 24 July 2026  
**Repository:** `JoelLovesKFC/PWA-AT1`  
**Target branch:** `refactor/lyra-band6`  
**Status:** Approved design for implementation planning

## 1. Purpose

The existing Nobu productivity PWA will be refurbished and rebranded as **LYRA**, a secure document, task and notes workspace designed to satisfy the highest performance band of the Year 12 Software Engineering Assessment Task 3.

The refurbishment will retain the current working Flask, SQLite, Bootstrap and JavaScript functionality while adding secure document management, role-based approval workflows, audit logging, automated validation and cleanup, stronger security, automated tests and complete project evidence.

The goal is not to discard the current project. The goal is to preserve its working features, improve its engineering quality and align the final submission closely with the supplied secure document management project option and marking rubric.

## 2. Confirmed Decisions

- The product will be renamed from **Nobu** to **LYRA**.
- The current clean productivity visual style will be retained.
- Existing task, notes, profile and trash features will remain.
- Secure document upload, review and approval features will be added.
- The backend will be reorganised into modular Flask blueprints and services.
- The system will support Standard User, Reviewer and Admin roles.
- New registrations will default to Standard User.
- Three demo roles will be available through a local seeding command for assessment marking.
- Allowed uploads will be PDF, DOCX and TXT files up to 10 MB.
- Files will be stored outside the public static directory.
- The application will remain locally runnable on the teacher's laptop.

## 3. Scope

### 3.1 In scope

- LYRA rebranding across templates, metadata, PWA files and documentation
- modular Flask application factory and blueprints
- secure login, registration and session handling
- user role and account-status management
- secure document upload and protected download
- document submission, approval, rejection and resubmission
- document metadata and review history
- audit logging
- simulated dashboard notifications
- automated file validation
- automated rejected-file cleanup command
- preservation of task, note, profile and trash features
- unit and integration tests
- GitHub Actions test automation
- complete README and local setup instructions
- folio evidence and technical diagrams under `docs/`

### 3.2 Out of scope

- cloud deployment as a requirement for marking
- real email delivery
- external antivirus services
- real-time multi-user collaboration
- native mobile applications
- replacing SQLite with a hosted database
- replacing Bootstrap with a full React rebuild
- production-grade enterprise identity providers

These exclusions keep the project achievable, testable and aligned with the assessment without adding unnecessary implementation risk.

## 4. Proposed Architecture

```text
PWA-AT1/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── audit_log.py
│   │   ├── notification.py
│   │   ├── task.py
│   │   ├── note.py
│   │   └── workspace.py
│   ├── auth/
│   │   ├── routes.py
│   │   └── validators.py
│   ├── documents/
│   │   ├── routes.py
│   │   ├── permissions.py
│   │   └── transitions.py
│   ├── admin/
│   │   └── routes.py
│   ├── tasks/
│   │   └── routes.py
│   ├── notes/
│   │   └── routes.py
│   ├── profile/
│   │   └── routes.py
│   ├── services/
│   │   ├── file_storage.py
│   │   ├── file_validation.py
│   │   ├── audit_service.py
│   │   ├── notification_service.py
│   │   └── cleanup_service.py
│   ├── templates/
│   └── static/
├── instance/
│   └── site.db
├── uploads/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── docs/
├── .github/workflows/tests.yml
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

### 4.1 Architectural principles

- **Separation of concerns:** page routes, APIs, models, validation and storage logic will not remain mixed in one large file.
- **Application factory:** tests and local runtime can create the app with different configuration values.
- **Blueprint isolation:** authentication, documents, administration, tasks, notes and profile functionality remain independently understandable.
- **Service isolation:** file handling, auditing, notifications and cleanup are reusable services rather than route-specific code.
- **Least privilege:** every protected operation checks the authenticated user's role and ownership.
- **Backward preservation:** current task and notes behaviour is migrated rather than removed.

## 5. User Roles

### 5.1 Standard User

A Standard User can:

- register and log in
- upload PDF, DOCX and TXT documents up to 10 MB
- view and download their own documents
- edit document metadata while a document is in Draft or Rejected state
- submit a document for review
- view status, review feedback and notifications
- revise and resubmit rejected documents
- use tasks, notes, profile and trash features

A Standard User cannot:

- view another user's private documents
- review or approve documents
- change account roles
- access the complete audit log
- edit a document while it is pending review

### 5.2 Reviewer

A Reviewer can:

- access documents currently awaiting review
- download submitted documents
- approve a pending document
- reject a pending document with required feedback
- view their review history
- use ordinary productivity features

A Reviewer cannot:

- approve their own document
- change user roles
- alter a completed review decision without an authorised administrative override
- access unrelated private drafts

### 5.3 Admin

An Admin can:

- view all users and documents
- assign Standard User, Reviewer and Admin roles
- disable and reactivate accounts
- view the complete audit log
- review maintenance results
- run cleanup and reporting commands
- archive approved documents
- override a document decision only when a reason is recorded

### 5.4 Registration and demo accounts

- Every public registration creates a Standard User account.
- A Flask CLI command will create local demonstration users for the three roles.
- Demo credentials will be generated or explicitly supplied when running the command rather than silently embedded in production code.
- The README will explain the exact command needed for the teacher to create the accounts.

## 6. Document Workflow

### 6.1 State machine

```text
Draft
  ↓ submit
Pending Review
  ├── approve ──> Approved ──> Archived
  └── reject ───> Rejected ──> Draft ──> Pending Review
```

### 6.2 Permitted transitions

| Current state | Actor | Action | New state | Conditions |
|---|---|---|---|---|
| Draft | Owner | Submit | Pending Review | File exists and metadata is valid |
| Pending Review | Reviewer | Approve | Approved | Reviewer is not owner |
| Pending Review | Reviewer | Reject | Rejected | Non-empty feedback required |
| Rejected | Owner | Revise | Draft | Owner uploads a replacement or edits metadata |
| Approved | Admin | Archive | Archived | Administrative action is audited |
| Any applicable state | Admin | Override | Approved or Rejected | Reason is mandatory and logged |

The backend will reject every invalid transition even if a request is manually constructed outside the interface.

### 6.3 Document list metadata

Each document record shown in the interface will include:

- original filename
- type and file size
- owner
- status
- upload date
- submission date
- reviewer
- decision date
- latest feedback
- current version
- available actions based on the active user's permissions

### 6.4 Review history

Review decisions will be stored in a separate `DocumentReview` table. A new decision will not overwrite the previous decision history. This provides stronger auditability and allows rejected documents to be revised and resubmitted while preserving earlier feedback.

## 7. Data Model

### 7.1 User

```text
User
- id: Integer, primary key
- name: String(100), required
- username: String(80), unique, required
- email: String(120), unique, required
- password_hash: String, required
- role: Enum-like string [user, reviewer, admin]
- is_active: Boolean, default true
- created_at: DateTime
```

### 7.2 Document

```text
Document
- id: Integer, primary key
- original_filename: String, required
- storage_filename: String, unique, required
- mime_type: String, required
- file_size: Integer, required
- status: Enum-like string [draft, pending_review, approved, rejected, archived]
- owner_id: Foreign key -> User.id
- current_version: Integer, default 1
- created_at: DateTime
- updated_at: DateTime
- submitted_at: DateTime, nullable
- archived_at: DateTime, nullable
```

### 7.3 DocumentReview

```text
DocumentReview
- id: Integer, primary key
- document_id: Foreign key -> Document.id
- reviewer_id: Foreign key -> User.id
- decision: Enum-like string [approved, rejected, override_approved, override_rejected]
- feedback: Text
- decided_at: DateTime
```

### 7.4 AuditLog

```text
AuditLog
- id: Integer, primary key
- actor_id: Foreign key -> User.id, nullable for anonymous login failures
- action: String, required
- target_type: String
- target_id: Integer, nullable
- result: String [success, failure]
- details: JSON/Text
- ip_address: String
- created_at: DateTime
```

### 7.5 Notification

```text
Notification
- id: Integer, primary key
- user_id: Foreign key -> User.id
- message: String, required
- is_read: Boolean, default false
- related_document_id: Foreign key -> Document.id, nullable
- created_at: DateTime
```

### 7.6 Existing models

Existing `Task`, `Note` and `Workspace` records remain associated with their owning user. Their routes and models will be migrated into modular files while preserving their existing data and public behaviour.

## 8. Secure File Handling

### 8.1 Accepted files

- `.pdf`
- `.docx`
- `.txt`
- maximum size: 10 MB

### 8.2 Upload process

```text
Authenticated request
  ↓
Role and CSRF checks
  ↓
Presence and size validation
  ↓
Extension and MIME validation
  ↓
Original filename sanitisation
  ↓
Random server-side storage name
  ↓
Write to protected uploads directory
  ↓
Create database record
  ↓
Create audit record
  ↓
Return safe response
```

### 8.3 Storage rules

- Uploaded files are never stored under `/static`.
- The original filename is metadata only.
- The physical filename is a random identifier with a validated extension.
- Files are accessed only through an authenticated Flask download route.
- The download route rechecks ownership or role permission.
- Paths are built from server-controlled values, not raw user input.
- Missing or altered storage files produce a safe error and audit event.
- Uploaded content is never executed by the server.

### 8.4 Failure handling

When database creation fails after a file has been written, the file will be removed to avoid orphaned data. When file writing fails, no database record will be committed.

## 9. Security Design

### 9.1 Authentication

- Bcrypt password hashing remains in use.
- Password rules will be strengthened and centralised.
- Login remains rate-limited.
- Disabled accounts cannot authenticate.
- Successful and failed login attempts are audited.
- Session data is cleared during logout.

### 9.2 Configuration

- The fallback secret key is removed from runtime code.
- `SECRET_KEY` is loaded from environment configuration.
- `.env.example` documents required values without containing real secrets.
- Development, testing and production-like settings are separated.
- Debug mode is not forced on in `run.py`.
- Secure cookie flags are configurable and enabled where appropriate.

### 9.3 Authorisation

- Page visibility and backend permission checks are separate controls.
- Decorators or permission helpers enforce authentication and roles.
- Ownership is checked for every user-specific document, task and note action.
- Reviewers cannot approve their own documents.
- Admin actions require explicit role checks and generate audit records.

### 9.4 CSRF and validation

- Broad `@csrf.exempt` usage will be removed from state-changing browser APIs.
- JavaScript requests will submit the CSRF token in a consistent header.
- Required fields, lengths, identifiers, role values, statuses and dates are validated centrally.
- Invalid JSON and malformed requests return consistent 400 responses.
- Database exceptions are logged without exposing stack traces to users.

### 9.5 Output safety

- Dynamic user text is escaped before insertion into HTML.
- Document feedback and names are displayed through safe templates or text-node operations.
- Error responses do not reveal local paths, SQL statements or internal exceptions.

## 10. Interface Design

The existing clean Bootstrap-based design will be preserved and rebranded as LYRA. This reduces implementation risk and keeps evidence of the original development work.

### 10.1 Standard User navigation

```text
Dashboard
Documents
Tasks & Notes
Notifications
Profile
Trash
```

### 10.2 Reviewer additions

```text
Review Queue
Review History
```

### 10.3 Admin additions

```text
User Management
All Documents
Audit Log
Maintenance
```

### 10.4 Interface rules

- Navigation items appear according to role.
- Backend authorisation remains mandatory even when an action is hidden.
- Validation failures appear beside the related field or in an accessible alert.
- Approval, rejection, permanent deletion and administrative override require confirmation.
- Rejection requires written feedback.
- Status is communicated through text and badges, not colour alone.
- Tables remain usable on smaller screens through responsive layouts.
- Forms have visible labels and keyboard-accessible controls.

## 11. API and Error Response Conventions

State-changing endpoints will return a consistent JSON format.

### 11.1 Success

```json
{
  "status": "success",
  "message": "Document submitted for review.",
  "data": {}
}
```

### 11.2 Validation failure

```json
{
  "status": "error",
  "code": "INVALID_FILE_TYPE",
  "message": "Only PDF, DOCX and TXT files are accepted.",
  "field": "document"
}
```

### 11.3 Error handlers

Custom handlers will cover:

- 400 invalid request
- 401 unauthenticated
- 403 forbidden
- 404 missing record
- 413 oversized upload
- database failures
- unexpected 500 errors

Application logs retain diagnostic detail. Browser responses remain safe and understandable.

## 12. Automation

### 12.1 Upload validation automation

Every uploaded document is automatically checked for:

- presence
- size
- approved extension
- expected MIME type
- filename safety
- storage collision avoidance

### 12.2 Cleanup automation

A Flask CLI command will inspect rejected documents older than a configured retention period.

```bash
flask cleanup-documents --dry-run
flask cleanup-documents
```

The dry-run mode lists planned actions without deleting files. The real mode removes eligible files or archives records according to the final implementation rule, records the result and produces a summary.

### 12.3 Notifications

LYRA creates dashboard notifications when:

- a document is submitted
- a document is approved
- a document is rejected
- an Admin changes a user's role
- a maintenance process affects one of the user's documents

Email delivery is intentionally simulated because real external email infrastructure is outside the assessment scope.

## 13. Testing Strategy

### 13.1 Test environment

- Pytest will be used.
- Tests will create the Flask application through the application factory.
- Each test run uses an isolated temporary SQLite database.
- File tests use a temporary upload directory.
- Test data will never modify the submitted local database.
- CSRF behaviour will be deliberately tested rather than globally disabled without evidence.

### 13.2 Unit tests

- password validation
- role validation
- canonical status handling
- allowed document transitions
- prevention of invalid transitions
- extension validation
- MIME validation
- 10 MB size boundary
- secure random storage naming
- retention-date calculation
- notification creation
- audit-event creation

### 13.3 Integration tests

- registration creates a Standard User
- valid login succeeds
- invalid login is rejected
- disabled account login is rejected
- Standard User uploads a valid document
- invalid extension is rejected
- oversized file is rejected
- unauthenticated upload is rejected
- user cannot access another user's private document
- owner submits a Draft document
- Reviewer approves a pending document
- Reviewer rejects with feedback
- rejection without feedback fails
- Reviewer cannot approve their own document
- owner revises and resubmits a rejected document
- Admin changes a role
- non-Admin role change fails
- every important action creates an audit record
- cleanup dry-run does not delete data
- cleanup removes or archives eligible test records
- task CRUD regression tests
- note CRUD regression tests
- protected download tests

### 13.4 Automated commands

```bash
pytest
pytest --cov=app --cov-report=term-missing
flask seed-demo
flask cleanup-documents --dry-run
```

### 13.5 Continuous integration

`.github/workflows/tests.yml` will install dependencies and run the automated test suite on pushes and pull requests. This provides repeatable evidence of automated testing.

## 14. Documentation and Folio Evidence

The `docs/` folder will contain evidence aligned with the supplied folio template and checklist.

```text
docs/
├── 01-problem-definition.md
├── 02-functional-requirements.md
├── 03-non-functional-requirements.md
├── 04-storyboard.md
├── 05-financial-feasibility.md
├── 06-data-flow-diagram.md
├── 07-data-dictionary.md
├── 08-uml-class-diagram.md
├── 09-er-diagram.md
├── 10-development-approach.md
├── 11-gantt-chart.md
├── 12-project-diary.md
├── 13-algorithm-pseudocode.md
├── 14-version-sequence.md
├── 15-prototyping-evidence.md
├── 16-test-plan-and-results.md
├── 17-optimisation.md
└── 18-final-evaluation.md
```

The documentation will distinguish between:

- planned behaviour
- implemented behaviour
- automated test evidence
- manual testing evidence
- optimisation changes
- remaining limitations

No test result, performance result, screenshot or user feedback will be claimed until it has actually been produced.

## 15. Migration Strategy

The refurbishment must preserve the current application while allowing the architecture to improve safely.

### 15.1 Sequence

1. Add configuration, extensions and application factory.
2. Move existing database models without changing their table names.
3. Register existing routes through blueprints.
4. Run regression tests for current task and note behaviour.
5. Add role and account fields using an idempotent local migration strategy.
6. Add document, review, audit and notification tables.
7. Add secure document services and routes.
8. Add Reviewer and Admin pages.
9. Rebrand user-visible Nobu references to LYRA.
10. Complete automated tests and documentation evidence.

### 15.2 Data preservation

- Existing table names and key fields will remain compatible where practical.
- Existing users default to Standard User unless assigned another role.
- Existing users default to active.
- Existing tasks, notes and workspaces remain intact.
- Database backups will be documented before schema changes.

## 16. Acceptance Criteria

The refurbishment is ready for submission only when all of the following are true:

1. The application starts locally from documented instructions.
2. `requirements.txt` installs all required Python dependencies.
3. LYRA branding replaces user-visible Nobu branding.
4. New users register as Standard Users.
5. Demo accounts can be created through a documented command.
6. PDF, DOCX and TXT uploads up to 10 MB work.
7. Disallowed and oversized files are rejected safely.
8. Uploaded files are stored outside the static directory.
9. Users cannot access another user's private files.
10. Users can submit documents for review.
11. Reviewers can approve or reject pending documents.
12. Rejection requires feedback.
13. Reviewers cannot review their own documents.
14. Admins can manage roles and account status.
15. Important actions create audit-log records.
16. Notifications appear for workflow changes.
17. Cleanup dry-run and execution commands work.
18. Existing task and note functionality still works.
19. Unit and integration tests pass locally.
20. GitHub Actions runs the tests automatically.
21. README setup and demonstration instructions are complete.
22. Folio documentation covers every required checklist area.
23. No default production secret or forced debug mode remains.
24. Error messages do not expose sensitive internal details.

## 17. Main Risks and Controls

| Risk | Control |
|---|---|
| Refactor breaks current functionality | Migrate incrementally and add regression tests before feature expansion |
| Scope becomes too large | Preserve existing Bootstrap UI and avoid React rebuild |
| Existing database becomes incompatible | Preserve table names, use additive migrations and document backups |
| File upload introduces security issues | Protected storage, allow-list validation, random names and permission-checked downloads |
| Role checks exist only in interface | Enforce every permission in backend helpers and integration tests |
| Testing is left until the end | Implement tests alongside each module and require CI execution |
| Documentation makes unsupported claims | Record only verified test outputs, screenshots and measured results |
| Teacher cannot run the application | Provide exact setup commands, `.env.example`, requirements and seed command |

## 18. Implementation Principle

The implementation should favour a smaller, fully working and thoroughly tested solution over unfinished extra features. A feature is not complete until its permissions, validation, error handling, tests and documentation are also complete.

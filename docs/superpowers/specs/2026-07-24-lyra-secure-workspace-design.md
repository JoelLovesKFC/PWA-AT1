# LYRA Secure Workspace Refurbishment Design

**Date:** 24 July 2026  
**Repository:** `JoelLovesKFC/PWA-AT1`  
**Branch:** `refactor/lyra-band6`  
**Status:** Approved design, ready for implementation planning

## 1. Purpose

The existing Nobu productivity PWA will be refurbished and rebranded as **LYRA**, a secure document, task and notes workspace. The project will retain its working Flask, SQLite, Bootstrap and JavaScript foundation while adding secure document management, role-based approval, audit logging, automation, stronger validation, automated tests and complete assessment evidence.

The aim is to improve and extend the existing work rather than replace it. The final system must remain easy for the teacher to install and run locally.

## 2. Confirmed decisions

- Rename the product from **Nobu** to **LYRA**.
- Keep the existing clean productivity interface rather than rebuilding it in React.
- Preserve tasks, notes, profile and trash features.
- Add secure PDF, DOCX and TXT uploads up to 10 MB.
- Add Standard User, Reviewer and Admin roles.
- New registrations always receive the Standard User role.
- Provide a local command that seeds one demonstration account for each role.
- Store files outside the public static directory.
- Refactor the backend into modular Flask blueprints and services.
- Add unit tests, integration tests and GitHub Actions automation.
- Add documentation matching every supplied folio and checklist section.

## 3. Scope

### Included

- LYRA branding across templates, PWA metadata, icons/text references and documentation
- Flask application factory and modular blueprints
- secure registration, login, logout and session handling
- account roles and active/disabled status
- protected document upload and download
- document submission, review, rejection, revision and approval
- review history, audit records and dashboard notifications
- automatic file validation
- scheduled cleanup of old rejected documents
- Admin user management
- preservation and regression testing of current productivity features
- local setup instructions, `requirements.txt` and `.env.example`
- GitHub Actions test workflow
- folio planning, design, test and evaluation evidence

### Excluded

- cloud deployment as a marking requirement
- real email delivery
- external antivirus subscriptions
- real-time multi-user editing
- native mobile applications
- hosted database infrastructure
- enterprise single sign-on
- complete frontend framework rewrite

These exclusions keep the project achievable and reduce the risk of submitting unfinished features.

## 4. Architecture

```text
PWA-AT1/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── review.py
│   │   ├── audit_log.py
│   │   ├── notification.py
│   │   ├── task.py
│   │   ├── note.py
│   │   └── workspace.py
│   ├── auth/
│   ├── documents/
│   ├── admin/
│   ├── tasks/
│   ├── notes/
│   ├── profile/
│   ├── services/
│   │   ├── file_validation.py
│   │   ├── file_storage.py
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

### Architectural rules

- Routes, models, validation, permissions and storage must not remain mixed in one large file.
- The application factory must support development and isolated testing configurations.
- Blueprints isolate authentication, documents, administration, tasks, notes and profile functions.
- Services isolate file handling, auditing, notifications and cleanup.
- Every protected action checks authentication, role and ownership in the backend.
- Existing database table names are retained where practical to preserve current data.

## 5. Roles and permissions

The database stores roles as `user`, `reviewer` and `admin`. The interface displays `user` as **Standard User**.

### Standard User

Can:

- register and log in
- upload valid documents
- view and download their own documents
- edit metadata in Draft state
- submit a Draft for review
- view status, feedback and notifications
- revise a Rejected document and resubmit it
- use tasks, notes, profile and trash

Cannot:

- view another user's private files
- review documents
- change roles
- view the complete audit log
- modify a Pending Review or Approved document

### Reviewer

Can:

- access Pending Review documents they do not own
- download submitted files
- approve a Pending Review document
- reject a Pending Review document with written feedback
- view their previous review decisions
- use normal productivity features

Cannot:

- review or approve their own document
- view unrelated private Draft documents
- change user roles
- rewrite completed review history

### Admin

Can:

- view all users and document metadata
- change roles
- disable or reactivate accounts
- view all audit records
- view maintenance reports
- trigger a non-destructive cleanup dry run from the Maintenance page
- archive Approved documents
- override an existing decision when a reason is recorded

The destructive cleanup action remains a local CLI command to reduce accidental deletion. An Admin cannot approve their own document, including through override.

### Demo accounts

The command below creates or resets the three assessment accounts:

```bash
flask seed-demo --password "TeacherChosenPassword"
```

It creates:

- `demo_user`
- `demo_reviewer`
- `demo_admin`

The password is supplied by the person running the command and is not hardcoded in production code. The command is idempotent so it can be safely rerun for marking.

## 6. Document workflow

### States

- `draft`
- `pending_review`
- `approved`
- `rejected`
- `archived`
- `expired`

### State machine

```text
Draft
  ↓ submit
Pending Review
  ├── approve ──> Approved ──> Archived
  └── reject ───> Rejected ──> Draft ──> Pending Review
                         └──── cleanup after retention ──> Expired
```

### Permitted transitions

| Current state | Actor | Action | New state | Conditions |
|---|---|---|---|---|
| Draft | Owner | Submit | Pending Review | Stored file exists and metadata is valid |
| Pending Review | Reviewer/Admin | Approve | Approved | Actor is not the owner |
| Pending Review | Reviewer/Admin | Reject | Rejected | Actor is not owner; feedback is required |
| Rejected | Owner | Revise | Draft | Replacement file or metadata revision is saved |
| Approved | Admin | Archive | Archived | Reason is recorded in audit details |
| Rejected | Cleanup service | Expire | Expired | Rejected for at least the configured retention period |
| Pending Review, Approved or Rejected | Admin | Override decision | Approved or Rejected | Actor is not owner; reason is required |

All invalid transitions return a safe 400 or 403 response. Interface controls do not replace backend enforcement.

### Review history

Each decision creates a new `DocumentReview` record. Earlier approvals, rejections and feedback are never overwritten. This lets the folio demonstrate a clear approval state machine and complete decision history.

### Document list

Each row displays:

- original filename
- file type and size
- owner
- current status
- version
- upload and submission dates
- latest reviewer and decision date
- latest feedback
- role-appropriate actions

## 7. Data model

### User

```text
id                 Integer, primary key
name               String(100), required
username           String(80), unique, required
email              String(120), unique, required
password_hash      String, required
role               String [user, reviewer, admin], required
is_active          Boolean, default true
created_at         DateTime, required
```

### Document

```text
id                 Integer, primary key
original_filename  String, required
storage_filename   String, unique, nullable after expiry
mime_type          String, required
file_size          Integer, required
status             String [draft, pending_review, approved, rejected, archived, expired]
owner_id           Foreign key -> User.id, required
current_version    Integer, default 1
created_at         DateTime, required
updated_at         DateTime, required
submitted_at       DateTime, nullable
archived_at        DateTime, nullable
file_removed_at    DateTime, nullable
```

### DocumentReview

```text
id                 Integer, primary key
document_id        Foreign key -> Document.id, required
reviewer_id        Foreign key -> User.id, required
decision           String [approved, rejected, override_approved, override_rejected]
feedback           Text
decided_at         DateTime, required
```

### AuditLog

```text
id                 Integer, primary key
actor_id           Foreign key -> User.id, nullable for anonymous failures
action             String, required
target_type        String
target_id          Integer, nullable
result             String [success, failure]
details            JSON/Text
ip_address         String
created_at         DateTime, required
```

### Notification

```text
id                   Integer, primary key
user_id              Foreign key -> User.id, required
message              String, required
is_read              Boolean, default false
related_document_id  Foreign key -> Document.id, nullable
created_at           DateTime, required
```

Existing Task, Note and Workspace entities remain linked to their owner. Their current records must survive the migration.

## 8. Secure file handling

### File rules

- accepted extensions: `.pdf`, `.docx`, `.txt`
- maximum request size: 10 MB
- original filename retained only as metadata
- physical storage filename generated with a random UUID
- files stored under the configured protected upload directory, never `/static`
- downloads served only by a permission-checked Flask route

### Content validation

LYRA does not trust the browser-provided MIME value alone.

- PDF files must begin with a valid PDF signature.
- DOCX files must be valid ZIP containers containing the expected Office document entries.
- TXT files must decode as text and must not contain binary null bytes.
- The extension, detected content type and submitted MIME type must be compatible.

This pure-Python validation avoids platform-specific native dependencies that could prevent the teacher running the project on Windows.

### Transaction behaviour

1. Validate request and permission.
2. Validate file size, extension and content signature.
3. Generate the server-controlled storage name.
4. Write the file to protected storage.
5. Create the database record and audit event in one database transaction.
6. If the database transaction fails, remove the newly written file.
7. If file writing fails, do not create the database record.

### Downloads

The route verifies:

- an authenticated session
- document existence
- file availability
- owner, assigned reviewer or Admin permission
- a safe server-controlled path

Every successful and denied download attempt creates an audit record.

## 9. Authentication and security

### Passwords

- Bcrypt hashing remains in use.
- Passwords must be 10 to 128 characters.
- Passwords must contain at least one uppercase letter, lowercase letter and number.
- Validation is centralised and covered by boundary tests.

### Sessions

- login remains rate-limited
- disabled users cannot authenticate
- successful login makes the session permanent for a configurable two-hour lifetime
- cookies use `HttpOnly` and `SameSite=Lax`
- `Secure` is enabled when HTTPS is used
- logout clears the session
- login success and failure are audited

### Configuration

- no fallback production secret key
- `SECRET_KEY` loaded from environment variables
- `.env.example` documents required local values
- separate development and testing configuration classes
- debug mode is not forced on by `run.py`
- upload directory, database URI, retention period and maximum file size are configurable

### CSRF and validation

- state-changing browser requests require Flask-WTF CSRF protection
- JavaScript sends the token in `X-CSRFToken`
- broad `@csrf.exempt` use is removed
- JSON CSRF failures return a consistent safe error
- identifiers, roles, statuses, lengths, dates and ownership are validated server-side

### Output safety

- user-controlled text is escaped before insertion into HTML
- JavaScript uses text nodes or explicit escaping for dynamic content
- errors never reveal SQL, local paths, secret values or stack traces
- full diagnostic details go only to application logs

## 10. Interface

The existing responsive Bootstrap layout remains the visual foundation.

### Standard User navigation

```text
Dashboard
Documents
Tasks & Notes
Notifications
Profile
Trash
```

### Reviewer additions

```text
Review Queue
Review History
```

### Admin additions

```text
User Management
All Documents
Audit Log
Maintenance
```

### Interface rules

- actions are hidden when irrelevant but still protected in the backend
- forms use visible labels and keyboard-accessible controls
- errors appear beside the related field or in an accessible alert
- status uses text and icons as well as colour
- document tables remain usable on smaller screens
- rejection requires feedback before submission
- approval, rejection, permanent deletion and override use confirmation dialogs

## 11. API response convention

### Success

```json
{
  "status": "success",
  "message": "Document submitted for review.",
  "data": {}
}
```

### Validation failure

```json
{
  "status": "error",
  "code": "INVALID_FILE_TYPE",
  "message": "Only PDF, DOCX and TXT files are accepted.",
  "field": "document"
}
```

Custom handlers cover invalid requests, unauthenticated access, forbidden actions, missing records, oversized requests, database errors and unexpected server errors.

## 12. Automation

### Upload validation

Every upload automatically checks presence, size, extension, content signature, filename safety and collision avoidance.

### Rejected-document cleanup

The default retention period is 30 days and can be changed through configuration.

```bash
flask cleanup-documents --dry-run
flask cleanup-documents
```

Dry run:

- lists eligible rejected documents
- reports files that would be removed
- changes no files or database records

Execution:

- selects documents that have remained Rejected for at least the retention period
- deletes the protected binary file
- changes the document state to Expired
- clears `storage_filename`
- records `file_removed_at`
- preserves metadata, review history and audit history
- creates a user notification and cleanup audit record
- prints a summary of processed, skipped and failed records

### Notifications

Notifications are created when:

- a document is submitted
- a document is approved or rejected
- a rejected document is revised
- a role or account status changes
- cleanup expires a document

Real email delivery is simulated through the dashboard because external email infrastructure is outside scope.

## 13. Testing

### Test environment

- Pytest and pytest-cov
- application factory with test configuration
- temporary SQLite database for every test session
- temporary protected upload directory
- no changes to the submitted database or real upload folder
- CSRF behaviour tested explicitly

### Unit coverage

- password boundaries and complexity
- role and account-status validation
- document transition matrix
- self-review prevention
- extension and content-signature validation
- exact 10 MB size boundary
- random storage naming and safe path building
- retention-date calculations
- audit and notification creation
- cleanup selection and state changes

### Integration coverage

- registration defaults to Standard User
- login success, failure and rate-limit behaviour
- disabled-account rejection
- valid PDF, DOCX and TXT uploads
- invalid, disguised and oversized upload rejection
- unauthenticated and cross-user access rejection
- protected downloads
- Draft submission
- Reviewer approval
- rejection with required feedback
- rejection without feedback failure
- self-approval failure for Reviewer and Admin
- rejected-document revision and resubmission
- Admin role and account-status changes
- non-Admin management failure
- audit records for critical actions
- notification lifecycle
- cleanup dry run and execution
- existing task CRUD regression
- existing note CRUD regression
- trash restore and permanent-delete regression

### Coverage targets

- every route must have at least one success and one relevant failure test
- all document transition, permission and file-validation branches must be covered
- target at least 85% total line coverage
- target 100% line coverage for transition and permission modules

Commands:

```bash
pytest
pytest --cov=app --cov-report=term-missing
flask seed-demo --password "TeacherChosenPassword"
flask cleanup-documents --dry-run
```

GitHub Actions runs tests on pushes and pull requests. Test outputs are documented only after they have actually run.

## 14. Documentation package

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

Documentation clearly separates planned behaviour, implemented behaviour, automated evidence, manual evidence, measured optimisation and remaining limitations. No screenshots, performance results, test results or user feedback are claimed before evidence exists.

## 15. Migration sequence

1. Add configuration, extensions and application factory.
2. Move current models without changing existing table names.
3. Move existing routes into blueprints.
4. Add regression tests for tasks, notes, profile and trash.
5. Add `role`, `is_active` and `created_at` fields with safe defaults.
6. Add Document, DocumentReview, AuditLog and Notification tables.
7. Add secure validation and storage services.
8. Add document workflow routes and pages.
9. Add Reviewer and Admin functions.
10. Rebrand all user-visible Nobu references to LYRA.
11. Add CLI automation, CI and complete documentation.
12. Run full tests and record only verified results.

Before schema changes, the README and folio will instruct the user to copy `instance/site.db` as a backup. Existing users default to Standard User and active. Existing tasks, notes and workspaces remain intact.

## 16. Acceptance criteria

The refurbishment is ready for submission only when:

1. The teacher can install and start LYRA from the README.
2. `requirements.txt` contains every Python dependency.
3. LYRA branding replaces all user-visible Nobu branding.
4. New registrations receive the Standard User role.
5. The demo seed command creates all three roles.
6. Valid PDF, DOCX and TXT files up to 10 MB upload successfully.
7. Disguised, invalid and oversized files are rejected safely.
8. Uploaded files remain outside `/static`.
9. Cross-user private-file access is prevented.
10. Owners can submit Draft documents.
11. Reviewers can approve or reject eligible Pending Review documents.
12. Rejection requires feedback.
13. No role can approve its own document.
14. Rejected documents can be revised and resubmitted.
15. Admins can manage roles and account status.
16. Critical actions create audit records.
17. Workflow changes create dashboard notifications.
18. Cleanup dry run makes no changes.
19. Cleanup execution expires eligible rejected documents while preserving metadata and history.
20. Existing task, note, profile and trash behaviour still works.
21. Unit and integration tests pass locally.
22. GitHub Actions runs the same test suite automatically.
23. Coverage targets are measured and documented.
24. The README contains setup, demo and troubleshooting instructions.
25. Every supplied folio/checklist area has corresponding evidence.
26. No fallback secret or forced debug mode remains.
27. Error messages do not expose sensitive internal details.

## 17. Risks and controls

| Risk | Control |
|---|---|
| Refactor breaks current features | Move incrementally and establish regression tests first |
| Scope becomes too large | Preserve Bootstrap UI and exclude React/cloud/email rebuilds |
| Existing database becomes incompatible | Additive schema changes, safe defaults and documented backup |
| File upload creates vulnerabilities | Protected storage, content validation, random names and permission-checked download |
| Role security exists only in the UI | Backend permission helpers and negative integration tests |
| Destructive cleanup is triggered accidentally | UI provides dry run only; destructive action requires CLI command |
| Testing is delayed | Write tests beside each module and require CI |
| Documentation exaggerates results | Record only reproduced evidence and state remaining limits |
| Teacher cannot run the project | Pure-Python dependencies, exact commands, `.env.example` and seed command |

## 18. Completion principle

Prefer a smaller fully working and thoroughly tested solution over unfinished extra features. A feature is complete only when its permissions, validation, error handling, tests and documentation are also complete.

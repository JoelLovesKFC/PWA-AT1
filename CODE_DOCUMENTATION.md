# Code Documentation & Cleanup Summary
====================================

## Overview
This document outlines the code structure and organization of the Nobu Task Manager PWA application.

## Project Structure

```
PWA-AT1/
├── main.py                 # Flask backend application (routes, API,  models)
├── instance/
│   └── site.db            # SQLite database
├── static/
│   ├── js/
│   │   ├── login.js       # Login form handling
│   │   ├── register.js    # Registration form handling
│   │   ├── tasks.js       # Task CRUD operations
│   │   ├── profile_basic.js # Profile editing
│   │   ├── workspaces.js  # Workspace management
│   │   └── workspace_notes.js # Notes within workspaces
│   ├── icon-192.png       # PWA icon 192x192
│   ├── icon-512.png       # PWA icon 512x512
│   ├── manifest.json      # PWA manifest file
│   ├── sw.js              # Service Worker for offline support
│   └── style-*.css        # Page-specific stylesheets
└── templates/
    ├── base.html          # Base template (navbar, sidebar, PWA setup)
    ├── home.html          # Landing page
    ├── login.html         # Login page
    ├── register.html      # Registration page
    ├── task.html          # Tasks management page
    ├── profile.html       # User profile page
    └── *.html             # Other pages

```

## Key Components

### 1. Backend (main.py)

**Database Models:**
- `User`: Stores user accounts (username, email, hashed password)
- `Task`: To-do items with status, due dates, and soft delete functionality
- `Note`: User notes/documents, can be standalone or in workspaces
- `Workspace`: Collections for organizing notes

**API Endpoints:**
- `/api/register` - User registration
- `/api/tasks` - CRUD operations for tasks
- `/api/tasks/reorder` - Drag-and-drop sorting
- `/api/standalone_notes` - CRUD for standalone notes
- `/api/trash` - View/restore/permanently delete trashed items
- `/api/profile/basic` - Update user profile
- `/api/change_password` - Change user password

**Authentication:**
- Session-based (stored in Flask session)
- Bcrypt password hashing
- Rate limiting on login (5 attempts per minute)
- CSRF protection on forms

**Soft Delete System:**
- Items marked as `is_trashed=True` instead of being deleted
- Can be restored from trash
- Permanent delete option available

### 2. Frontend JavaScript

**tasks.js** - Task Management:
- State management for tasks list
- Sorting (manual, newest, alphabetical, by due date)
- Filtering (all, todo, in_progress, done)
- Bulk selection and deletion
- Drag-and-drop reordering with SortableJS
- Inline editing with modal

**login.js** - Authentication:
- Form validation
- Password visibility toggle
- AJAX login request
- Error handling and display

**register.js** - User Registration:
- Form validation (all fields, password match, length)
- Field-specific error messages
- AJAX registration request

**profile_basic.js** - Profile Editing:
- Update user name, username, email
- Username uniqueness validation
- Success/error feedback

### 3. Progressive Web App (PWA)

**manifest.json:**
- App name: "Nobu - Task Manager"
- Start URL: /tasks
- Display: standalone (no browser UI)
- Theme color: #212529 (dark)
- Icons: 192x192 and 512x512 PNG

**sw.js** (Service Worker):
- Caches essential assets for offline use
- Network-first strategy for API calls
- Cache-first for static assets
- Automatic cache versioning

**base.html PWA Setup:**
- Manifest link
- Theme color meta tags
- Apple-specific meta tags for iOS
- Service worker registration script

### 4. Styling

**Consistent Design System:**
- Dark sidebar (#212529)
- Bootstrap 5.3 framework
- Inter font family
- Responsive breakpoints
- Task status colors:
  - Todo: Gray
  - In Progress: Yellow/Warning
  - Done: Green

### 5. Security Features

- CSRF Protection (Flask-WTF)
- Rate Limiting (Flask-Limiter)
- Password Hashing (Bcrypt)
- Session-based authentication
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (escaped HTML in templates)

## Code Patterns

### API Response Format
```javascript
// Success
{ "status": "success", "message": "..." }

// Error
{ "status": "error", "message": "..." }

// Validation Error
{ "status": "error", "field": "username", "message": "..." }
```

### Database Queries
```python
# Always filter by user_id for security
Task.query.filter_by(user_id=session['user_id'], is_trashed=False)

# Soft delete instead of db.session.delete()
item.is_trashed = True
db.session.commit()
```

### Frontend AJAX Pattern
```javascript
const res = await fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
});
if (res.ok) {
    // Success handling
} else {
    // Error handling
}
```

## Future Improvements

1. **Add More Comments**: In-line comments explaining complex logic
2. **TypeScript**: Convert JS to TypeScript for type safety
3. **API Documentation**: Use Swagger/OpenAPI
4. **Unit Tests**: Add pytest for backend, Jest for frontend
5. **Error Logging**: Implement proper logging system
6. **Database Migrations**: Use Alembic instead of manual ALTER TABLE
7. **Environment Config**: Separate dev/prod configurations
8. **Docker**: Containerize the application
9. **CI/CD**: Automated testing and deployment

## Contributing Guidelines

When adding new features:
1. Add docstrings to all functions
2. Comment complex logic
3. Follow existing naming conventions
4. Test on multiple browsers
5. Ensure PWA functionality still works
6. Update this documentation

## Notes

- The app uses SQLite for development (switch to PostgreSQL for production)
- Debug mode is enabled (disable in production)
- SECRET_KEY should be set via environment variable in production
- Service worker requires HTTPS in production (works on localhost without)

---

Created: 2025-11-21
Last Updated: 2025-11-21

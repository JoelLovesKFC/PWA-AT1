document.addEventListener("DOMContentLoaded", function () {
    const notesContainer = document.getElementById('notes-container');
    const noteForm = document.getElementById('noteForm');
    const noteModalEl = document.getElementById('noteModal');
    const noteModal = new bootstrap.Modal(noteModalEl);

    // --- READ: Fetch and display all notes when the page loads ---
    async function fetchAndDisplayNotes() {
        try {
            const response = await fetch('/api/notes');
            if (!response.ok) throw new Error('Failed to fetch notes.');
            const notes = await response.json();

            notesContainer.innerHTML = ''; // Clear existing notes
            if (notes.length === 0) {
                notesContainer.innerHTML = '<p class="text-muted">You have no notes yet. Click "Add New Note" to get started!</p>';
            }

            notes.forEach(note => {
                const noteCard = `
                    <div class="col-md-6 col-lg-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">${escapeHTML(note.title)}</h5>
                                <p class="card-text">${escapeHTML(note.content)}</p>
                                <p class="card-text"><small class="text-muted">Created: ${new Date(note.date_created).toLocaleString()}</small></p>
                                <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${note.id}" data-title="${escapeHTML(note.title)}" data-content="${escapeHTML(note.content)}">Edit</button>
                                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${note.id}">Delete</button>
                            </div>
                        </div>
                    </div>
                `;
                notesContainer.insertAdjacentHTML('beforeend', noteCard);
            });
        } catch (error) {
            console.error('Error fetching notes:', error);
            notesContainer.innerHTML = '<p class="text-danger">Could not load notes.</p>';
        }
    }

    // --- CREATE / UPDATE: Handle the form submission ---
    noteForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const noteId = document.getElementById('note-id').value;
        const title = document.getElementById('note-title').value;
        const content = document.getElementById('note-content').value;
        const csrfToken = 'dummy-token'; // This will be replaced if you add CSRF to the API

        const method = noteId ? 'PUT' : 'POST';
        const url = noteId ? `/api/notes/${noteId}` : '/api/notes';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content })
            });
            if (!response.ok) throw new Error('Failed to save note.');

            noteModal.hide(); // Hide the pop-up form
            fetchAndDisplayNotes(); // Refresh the list of notes
        } catch (error) {
            console.error('Error saving note:', error);
            alert('Could not save the note. Please try again.');
        }
    });

    // --- Event Delegation for EDIT and DELETE buttons ---
    notesContainer.addEventListener('click', async function (event) {
        const target = event.target;

        // --- UPDATE (Part 1): Handle click on "Edit" button ---
        if (target.classList.contains('edit-btn')) {
            const noteId = target.dataset.id;
            const noteTitle = target.dataset.title;
            const noteContent = target.dataset.content;

            // Populate the modal form with the note's data
            document.getElementById('note-id').value = noteId;
            document.getElementById('note-title').value = noteTitle;
            document.getElementById('note-content').value = noteContent;
            document.getElementById('noteModalLabel').textContent = 'Edit Note';
            noteModal.show();
        }

        // --- DELETE: Handle click on "Delete" button ---
        if (target.classList.contains('delete-btn')) {
            const noteId = target.dataset.id;
            if (confirm('Are you sure you want to delete this note?')) {
                try {
                    const response = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
                    if (!response.ok) throw new Error('Failed to delete note.');
                    fetchAndDisplayNotes(); // Refresh the list
                } catch (error) {
                    console.error('Error deleting note:', error);
                    alert('Could not delete the note.');
                }
            }
        }
    });

    // A simple helper function to prevent XSS attacks when displaying user content
    function escapeHTML(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }
    
    // Initial load of notes
    fetchAndDisplayNotes();
});
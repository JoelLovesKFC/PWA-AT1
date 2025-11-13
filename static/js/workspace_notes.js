(() => {
    const root = document.getElementById('wsRoot');
    if (!root) return;

    const WS_ID = Number(root.dataset.wsId);
    const CSRF = root.dataset.csrf;

    const listEl = document.getElementById('notesList');
    const newBtn = document.getElementById('newNoteBtn');
    const delBtn = document.getElementById('deleteNoteBtn');
    const titleEl = document.getElementById('noteTitle');
    const bodyEl = document.getElementById('noteBody');
    const stateEl = document.getElementById('saveState');

    let notes = [];
    let currentId = null;
    let dirty = false;
    let autosaveTimer = null;
    let debounceTimer = null;

    function setState(text, colorClass = 'text-secondary') {
        stateEl.className = 'ms-auto small ' + colorClass;
        stateEl.innerHTML = `<span class="status-dot">●</span> ${text}`;
    }

    function escapeHtml(s) {
        return (s || '').replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;'
        }[m]));
    }

    function renderList() {
        if (!notes.length) {
            listEl.innerHTML = `<div class="p-3 text-secondary small">No notes yet.</div>`;
            return;
        }
        listEl.innerHTML = notes.map(n => `
      <div class="note-item ${n.id === currentId ? 'active' : ''}" data-id="${n.id}">
        <h6>${escapeHtml(n.title || 'Untitled')}</h6>
        <small>${n.updated_at ? new Date(n.updated_at).toLocaleString() : ''}</small>
      </div>
    `).join('');

        listEl.querySelectorAll('.note-item').forEach(el => {
            el.addEventListener('click', () => openNote(Number(el.dataset.id)));
        });
    }

    function openNote(id) {
        const n = notes.find(x => x.id === id);
        if (!n) return;
        currentId = id;
        titleEl.value = n.title || '';
        bodyEl.value = n.content || '';
        dirty = false;
        delBtn.classList.remove('d-none');
        renderList();
        setState('Loaded');
    }

    async function loadNotes() {
        const res = await fetch(`/api/workspaces/${WS_ID}/notes`);
        notes = await res.json();
        renderList();
        if (notes.length && currentId === null) openNote(notes[0].id);
    }

    async function createNote() {
        if (dirty) await saveNow();
        const res = await fetch(`/api/workspaces/${WS_ID}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ title: 'Untitled', content: '' })
        });
        const n = await res.json();
        notes.unshift(n);
        openNote(n.id);
    }

    async function deleteNote() {
        if (!currentId) return;
        if (!confirm('Delete this note?')) return;
        await fetch(`/api/workspaces/${WS_ID}/notes/${currentId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': CSRF }
        });
        notes = notes.filter(n => n.id !== currentId);
        currentId = null;
        titleEl.value = '';
        bodyEl.value = '';
        dirty = false;
        delBtn.classList.add('d-none');
        renderList();
        if (notes.length) openNote(notes[0].id);
    }

    async function saveNow() {
        if (!currentId || !dirty) return;
        setState('Saving…', 'text-warning');
        const payload = { title: (titleEl.value || '').trim() || 'Untitled', content: bodyEl.value || '' };
        const res = await fetch(`/api/workspaces/${WS_ID}/notes/${currentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const n = notes.find(x => x.id === currentId);
            if (n) {
                n.title = payload.title;
                n.content = payload.content;
                n.updated_at = new Date().toISOString();
            }
            renderList();
            dirty = false;
            setState('Saved', 'text-success');
        } else {
            setState('Save failed', 'text-danger');
        }
    }

    function markDirty() {
        dirty = true;
        setState('Unsaved changes', 'text-warning');
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(saveNow, 1500);
    }

    function startAutosave() {
        clearInterval(autosaveTimer);
        autosaveTimer = setInterval(saveNow, 60 * 1000);
    }

    // wire up
    newBtn.addEventListener('click', createNote);
    delBtn.addEventListener('click', deleteNote);
    titleEl.addEventListener('input', markDirty);
    bodyEl.addEventListener('input', markDirty);

    // best effort save on unload
    window.addEventListener('beforeunload', () => {
        if (!currentId || !dirty || !navigator.sendBeacon) return;
        const payload = JSON.stringify({
            title: (titleEl.value || '').trim() || 'Untitled',
            content: bodyEl.value || ''
        });
        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(`/api/workspaces/${WS_ID}/notes/${currentId}`, blob);
    });

    loadNotes();
    startAutosave();
})();

(() => {
    const listEl = document.getElementById('taskList');
    const newBtn = document.getElementById('newTaskBtn');
    const delBtn = document.getElementById('bulkDeleteBtn');

    // modal bits
    const modalEl = document.getElementById('taskModal');
    const bsModal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('taskForm');
    const fldId = document.getElementById('taskId');
    const fldTitle = document.getElementById('taskTitle');
    const fldDesc = document.getElementById('taskDesc');
    const fldDue = document.getElementById('taskDue');
    const fldStatus = document.getElementById('taskStatus');

    // filter buttons
    const fltBtns = {
        all: document.getElementById('flt-all'),
        todo: document.getElementById('flt-todo'),
        in_progress: document.getElementById('flt-progress'),
        done: document.getElementById('flt-done'),
    };

    let currentFilter = 'all';     // keep track to re-load correctly
    let selected = new Set();      // selected task IDs
    let lastItems = [];            // cache current tasks for edit modal

    function badge(status) {
        switch (status) {
            case 'done': return `<span class="badge rounded-pill badge-done">Done</span>`;
            case 'in_progress': return `<span class="badge rounded-pill badge-progress">In&nbsp;Progress</span>`;
            default: return `<span class="badge rounded-pill badge-todo">To&nbsp;Do</span>`;
        }
    }

    function rowTemplate(t) {
        const status = t.status || (t.completed ? 'done' : 'todo');
        const due = t.due_date ? ` <span class="task-meta ms-2">Due ${t.due_date}</span>` : '';
        const checked = selected.has(t.id) ? 'checked' : '';
        return `
      <div class="task-row" data-id="${t.id}" data-status="${status}">
        <input type="checkbox" class="form-check-input task-check" ${checked} />
        <div class="flex-grow-1">
          <div class="d-flex align-items-center gap-2">
            <span class="task-title">${escapeHtml(t.title)}</span>
            ${badge(status)} ${due}
          </div>
          ${t.description ? `<div class="task-meta mt-1">${escapeHtml(t.description)}</div>` : ''}
        </div>
        <div class="d-flex align-items-start gap-2">
          <button class="btn btn-sm btn-outline-secondary btn-edit" title="Edit"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-sm btn-outline-danger btn-del" title="Delete"><i class="bi bi-trash"></i></button>
        </div>
      </div>`;
    }

    function escapeHtml(s) {
        return (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
    }

    function setFilter(newFilter) {
        currentFilter = newFilter;
        Object.entries(fltBtns).forEach(([k, btn]) => {
            if (k === newFilter) {
                btn.classList.remove('btn-outline-secondary');
                btn.classList.add('btn-secondary');
            } else {
                btn.classList.add('btn-outline-secondary');
                btn.classList.remove('btn-secondary');
            }
        });
        applyFilter();
    }

    function applyFilter() {
        [...listEl.querySelectorAll('.task-row')].forEach(row => {
            const st = row.dataset.status;
            row.style.display = (currentFilter === 'all' || st === currentFilter) ? '' : 'none';
        });
    }

    async function loadTasks() {
        const res = await fetch('/api/tasks?ts=' + Date.now());
        const items = await res.json();
        lastItems = items; // cache for edit lookups
        listEl.innerHTML = items.map(rowTemplate).join('');
        applyFilter();
    }

    function toggleSelected(id, state) {
        if (state) selected.add(id);
        else selected.delete(id);
        updateBulkButton();
    }

    function updateBulkButton() {
        delBtn.disabled = selected.size === 0;
        delBtn.innerHTML = `<i class="bi bi-trash me-1"></i>Delete${selected.size ? ` (${selected.size})` : ''}`;
    }

    // --- modal handling
    function openModalForCreate() {
        form.reset();
        fldId.value = '';
        document.getElementById('taskModalLabel').textContent = 'New Task';
        bsModal.show();
    }

    function openModalForEdit(t) {
        if (!t) return;
        form.reset();
        fldId.value = t.id;
        fldTitle.value = t.title || '';
        fldDesc.value = t.description || '';
        fldDue.value = t.due_date || '';
        fldStatus.value = t.status || (t.completed ? 'done' : 'todo');
        document.getElementById('taskModalLabel').textContent = 'Edit Task';
        bsModal.show();
    }

    async function saveFromModal() {
        const payload = {
            title: fldTitle.value.trim(),
            description: fldDesc.value.trim(),
            due_date: fldDue.value || null,
            status: fldStatus.value,
            completed: fldStatus.value === 'done'
        };
        if (!payload.title) return;

        const id = fldId.value;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/tasks/${id}` : '/api/tasks';

        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) { alert('Could not save task'); return; }
        bsModal.hide();

        await loadTasks();  // stays on current filter
    }

    // --- bulk delete
    async function bulkDelete() {
        if (selected.size === 0) return;
        if (!confirm(`Delete ${selected.size} selected task(s)?`)) return;

        const ids = [...selected];
        const res = await fetch('/api/tasks/bulk_delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        });
        if (!res.ok) { alert('Bulk delete failed.'); return; }
        selected.clear();
        updateBulkButton();
        await loadTasks();
    }

    // === delegated interactions on the task list (edit / delete / checkbox / row click) ===
    listEl.addEventListener('click', async (e) => {
        const row = e.target.closest('.task-row');
        if (!row) return;
        const id = Number(row.dataset.id);

        // delete button
        if (e.target.closest('.btn-del')) {
            e.preventDefault(); e.stopPropagation();
            if (!confirm('Delete this task?')) return;
            const resp = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            if (!resp.ok) { alert('Could not delete task.'); return; }
            selected.delete(id);
            updateBulkButton();
            await loadTasks();
            return;
        }

        // edit button
        if (e.target.closest('.btn-edit')) {
            e.preventDefault(); e.stopPropagation();
            const t = lastItems.find(x => x.id === id);
            openModalForEdit(t);
            return;
        }

        // checkbox
        if (e.target.classList.contains('task-check')) {
            e.stopPropagation();
            toggleSelected(id, e.target.checked);
            return;
        }

        // click anywhere on the row toggles the checkbox
        const cb = row.querySelector('.task-check');
        if (cb) {
            cb.checked = !cb.checked;
            toggleSelected(id, cb.checked);
        }
    });

    // wire up UI
    newBtn.addEventListener('click', openModalForCreate);
    document.getElementById('saveTaskBtn').addEventListener('click', saveFromModal);
    delBtn.addEventListener('click', bulkDelete);
    Object.values(fltBtns).forEach(btn => {
        btn.addEventListener('click', () => setFilter(btn.dataset.filter));
    });

    // initialise
    setFilter('all');  // default highlight
    loadTasks();
})();


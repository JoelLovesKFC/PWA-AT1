(() => {
    const listEl = document.getElementById('taskList');
    const defaultHeader = document.getElementById('defaultHeader');
    const selectionHeader = document.getElementById('selectionHeader');
    const newBtn = document.getElementById('newTaskBtn');
    const delBtn = document.getElementById('bulkDeleteBtn');
    const clearSelBtn = document.getElementById('clearSelectionBtn');
    const selectedCountSpan = document.getElementById('selectedCount');
    const filterLabel = document.getElementById('filterLabel');

    const modalEl = document.getElementById('taskModal');
    const bsModal = new bootstrap.Modal(modalEl);
    const form = document.getElementById('taskForm');
    const fldId = document.getElementById('taskId');
    const fldTitle = document.getElementById('taskTitle');
    const fldDesc = document.getElementById('taskDesc');
    const fldDue = document.getElementById('taskDue');
    const fldStatus = document.getElementById('taskStatus');

    let currentFilter = 'all';
    let selected = new Set();
    let sortableInstance = null;

    // --- SORTABLE INIT (Always active unless filtered) ---
    function initSortable() {
        if (sortableInstance) sortableInstance.destroy();

        if (currentFilter === 'all') {
            sortableInstance = new Sortable(listEl, {
                animation: 150,
                handle: '.task-row',
                onEnd: function (evt) {
                    saveOrder();
                }
            });
            listEl.classList.remove('sort-disabled');
        } else {
            listEl.classList.add('sort-disabled');
        }
    }

    async function saveOrder() {
        const rows = Array.from(listEl.querySelectorAll('.task-row'));
        const orderedIds = rows.map(row => parseInt(row.dataset.id));
        try {
            await fetch('/api/tasks/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: orderedIds })
            });
        } catch (e) { console.error("Failed to save order", e); }
    }

    function getStatusMeta(status) {
        switch (status) {
            case 'done': return { label: 'Done', badgeClass: 'bg-success', rowClass: 'status-done' };
            case 'in_progress': return { label: 'In Progress', badgeClass: 'bg-warning text-dark', rowClass: 'status-inprogress' };
            default: return { label: 'To Do', badgeClass: 'bg-secondary', rowClass: 'status-todo' };
        }
    }

    function rowTemplate(t) {
        const rawStatus = t.status || (t.completed ? 'done' : 'todo');
        const meta = getStatusMeta(rawStatus);
        const due = t.due_date ? `<span class="ms-2 text-muted"><i class="bi bi-calendar-event me-1"></i>${t.due_date}</span>` : '';
        const isSelected = selected.has(t.id);
        const checkedAttr = isSelected ? 'checked' : '';
        const selectionClass = isSelected ? 'selected-row' : '';
        const cursorStyle = (currentFilter === 'all') ? 'cursor: grab;' : 'cursor: default;';

        return `
      <div class="task-row ${meta.rowClass} ${selectionClass}" data-id="${t.id}" data-status="${rawStatus}" style="${cursorStyle}">
        <input type="checkbox" class="form-check-input task-check mt-1" ${checkedAttr} />
        <div class="flex-grow-1 ms-2">
          <div class="d-flex align-items-center flex-wrap gap-2 mb-1">
            <span class="task-title">${escapeHtml(t.title)}</span>
            <span class="badge ${meta.badgeClass} badge-status rounded-pill">${meta.label}</span>
          </div>
          <div class="task-meta">
            ${t.description ? `<span class="me-2">${escapeHtml(t.description)}</span>` : ''}
            ${due}
          </div>
        </div>
        <div class="d-flex align-items-center gap-1">
          <button class="btn btn-sm btn-light text-secondary btn-edit" title="Edit"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-sm btn-light text-danger btn-del" title="Delete"><i class="bi bi-trash"></i></button>
        </div>
      </div>`;
    }

    function escapeHtml(s) { return (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])); }

    function setFilter(newFilter, labelText) {
        currentFilter = newFilter;
        filterLabel.textContent = "Filter: " + labelText;
        applyFilter();
        initSortable();
    }

    function applyFilter() {
        let visibleCount = 0;
        [...listEl.querySelectorAll('.task-row')].forEach(row => {
            const st = row.dataset.status;
            const show = (currentFilter === 'all' || st === currentFilter);
            row.style.display = show ? 'flex' : 'none';
            if (show) visibleCount++;
        });
    }

    function calculateStats(items) {
        const todayStr = new Date().toISOString().split('T')[0];
        let overdueCount = 0, todayCount = 0, completedCount = 0, pendingTotal = 0;
        items.forEach(t => {
            const isDone = (t.status === 'done' || t.completed);
            if (isDone) { completedCount++; } else {
                pendingTotal++;
                if (t.due_date === todayStr) todayCount++;
                if (t.due_date && t.due_date < todayStr) overdueCount++;
            }
        });
        const elToday = document.getElementById('stat-today');
        const elOverdue = document.getElementById('stat-overdue');
        const elCompleted = document.getElementById('stat-completed');
        const elTotal = document.getElementById('stat-total');
        if (elToday) elToday.textContent = todayCount;
        if (elOverdue) elOverdue.textContent = overdueCount;
        if (elCompleted) elCompleted.textContent = completedCount;
        if (elTotal) elTotal.textContent = pendingTotal;
    }

    async function loadTasks() {
        try {
            const res = await fetch('/api/tasks?ts=' + Date.now());
            const items = await res.json();

            if (items.length === 0) {
                listEl.innerHTML = `<div class="text-center py-5 text-muted"><i class="bi bi-clipboard-check display-4"></i><p class="mt-2">No tasks found. Create one!</p></div>`;
            } else {
                listEl.innerHTML = items.map(rowTemplate).join('');
            }
            applyFilter();
            selected.clear(); updateBulkUI();
            calculateStats(items);
            initSortable();
        } catch (e) { console.error(e); }
    }

    function toggleSelected(id, state) {
        if (state) selected.add(id); else selected.delete(id);
        updateBulkUI();
    }

    function updateBulkUI() {
        if (selected.size > 0) {
            defaultHeader.classList.remove('d-flex'); defaultHeader.classList.add('d-none');
            selectionHeader.classList.remove('d-none'); selectionHeader.classList.add('d-flex');
            selectedCountSpan.textContent = selected.size;
        } else {
            selectionHeader.classList.remove('d-flex'); selectionHeader.classList.add('d-none');
            defaultHeader.classList.remove('d-none'); defaultHeader.classList.add('d-flex');
        }
    }

    function clearSelection() {
        selected.clear();
        document.querySelectorAll('.task-check').forEach(cb => cb.checked = false);
        document.querySelectorAll('.task-row').forEach(r => r.classList.remove('selected-row'));
        updateBulkUI();
    }

    listEl.addEventListener('click', (e) => {
        const row = e.target.closest('.task-row');
        if (!row) return;
        const id = Number(row.dataset.id);
        const checkbox = row.querySelector('.task-check');

        if (e.target.closest('.btn-del')) {
            e.preventDefault(); e.stopPropagation(); openDeleteModalForSingle(id); return;
        }
        if (e.target.closest('.btn-edit')) {
            e.preventDefault(); e.stopPropagation();
            fetch(`/api/tasks`).then(r => r.json()).then(all => { const task = all.find(x => x.id === id); openModalForEdit(task); });
            return;
        }

        const newState = !checkbox.checked;
        if (!e.target.classList.contains('task-check')) checkbox.checked = newState;
        toggleSelected(id, checkbox.checked);
        if (checkbox.checked) row.classList.add('selected-row');
        else row.classList.remove('selected-row');
    });

    function openModalForCreate() {
        form.reset(); fldId.value = '';
        fldStatus.value = ['todo', 'in_progress', 'done'].includes(currentFilter) ? currentFilter : 'todo';
        document.getElementById('taskModalLabel').textContent = 'New Task'; bsModal.show();
    }
    function openModalForEdit(t) {
        form.reset(); fldId.value = t.id; fldTitle.value = t.title || ''; fldDesc.value = t.description || '';
        fldDue.value = t.due_date || ''; fldStatus.value = t.status || 'todo';
        document.getElementById('taskModalLabel').textContent = 'Edit Task'; bsModal.show();
    }
    async function saveFromModal() {
        const payload = { title: fldTitle.value.trim(), description: fldDesc.value.trim(), due_date: fldDue.value || null, status: fldStatus.value || 'todo' };
        if (!payload.title) return;
        const id = fldId.value; const method = id ? 'PUT' : 'POST'; const url = id ? `/api/tasks/${id}` : '/api/tasks';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        if (res.ok) { bsModal.hide(); if (currentFilter !== 'all' && payload.status !== currentFilter) setFilter('all', 'All Tasks'); await loadTasks(); }
    }

    const deleteModal = new bootstrap.Modal(document.getElementById('deleteTaskModal'));
    const deleteModalBody = document.getElementById('deleteModalBody');
    const deleteTaskIdFld = document.getElementById('deleteTaskId');
    const deleteIsBulkFld = document.getElementById('deleteIsBulk');

    function openDeleteModalForSingle(id) {
        deleteModalBody.textContent = 'Delete this task?'; deleteTaskIdFld.value = id; deleteIsBulkFld.value = 'false'; deleteModal.show();
    }
    delBtn.addEventListener('click', () => {
        if (selected.size === 0) return;
        deleteModalBody.textContent = `Move ${selected.size} tasks to bin?`; deleteIsBulkFld.value = 'true'; deleteModal.show();
    });
    clearSelBtn.addEventListener('click', clearSelection);

    document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
        const isBulk = deleteIsBulkFld.value === 'true';
        if (isBulk) {
            await fetch('/api/tasks/bulk_delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: [...selected] }) });
            selected.clear(); updateBulkUI();
        } else {
            const id = deleteTaskIdFld.value; await fetch(`/api/tasks/${id}`, { method: 'DELETE' }); selected.delete(Number(id));
        }
        deleteModal.hide(); await loadTasks();
    });

    newBtn.addEventListener('click', openModalForCreate);
    document.getElementById('saveTaskBtn').addEventListener('click', saveFromModal);

    document.querySelectorAll('.dropdown-item[data-filter]').forEach(l => {
        l.addEventListener('click', (e) => { e.preventDefault(); setFilter(e.target.dataset.filter, e.target.textContent); });
    });

    loadTasks();
})();
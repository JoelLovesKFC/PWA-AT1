document.addEventListener('DOMContentLoaded', () => {
    // State
    let tasksData = [];
    let currentSort = 'manual';
    let currentFilter = 'all';
    let selectedTaskIds = new Set();

    // DOM Elements
    const taskListEl = document.getElementById('taskList');
    const taskModalEl = document.getElementById('taskModal');
    const taskModal = new bootstrap.Modal(taskModalEl);
    const deleteTaskModal = new bootstrap.Modal(document.getElementById('deleteTaskModal'));

    // Buttons & Inputs
    const newTaskBtn = document.getElementById('newTaskBtn');
    const saveTaskBtn = document.getElementById('saveTaskBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const clearSelectionBtn = document.getElementById('clearSelectionBtn');

    // Headers
    const defaultHeader = document.getElementById('defaultHeader');
    const selectionHeader = document.getElementById('selectionHeader');
    const selectedCountEl = document.getElementById('selectedCount');

    // Inputs
    const inpId = document.getElementById('taskId');
    const inpTitle = document.getElementById('taskTitle');
    const inpDesc = document.getElementById('taskDesc');
    const inpDue = document.getElementById('taskDue');
    const inpStatus = document.getElementById('taskStatus');

    // CSRF
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // --- Initialization ---
    loadTasks();

    // --- Event Listeners ---

    // 1. New Task
    newTaskBtn.addEventListener('click', () => {
        resetForm();
        taskModal.show();
    });

    // 2. Save Task (Create or Update)
    saveTaskBtn.addEventListener('click', async () => {
        const id = inpId.value;
        const title = inpTitle.value.trim();
        const description = inpDesc.value.trim();
        const due_date = inpDue.value;
        const status = inpStatus.value;

        // VALIDATION: Check if title is empty
        if (!title) {
            // Uses the global showToast function from base.html
            showToast("Title is required", "warning");
            // Shake the input to give visual feedback
            inpTitle.classList.add('is-invalid');
            setTimeout(() => inpTitle.classList.remove('is-invalid'), 2000);
            return;
        }

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/tasks/${id}` : '/api/tasks';

        try {
            const res = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ title, description, due_date, status })
            });

            if (res.ok) {
                taskModal.hide();
                loadTasks();
                showToast(id ? "Task updated" : "Task created", "success");
            } else {
                showToast("Failed to save task", "danger");
            }
        } catch (err) {
            console.error(err);
            showToast("Network error", "danger");
        }
    });

    // 3. Sorting
    document.querySelectorAll('[data-sort]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            currentSort = e.target.dataset.sort;
            document.getElementById('sortLabel').innerText = e.target.innerText;
            renderTasks(); // Re-render with new sort
        });
    });

    // 4. Filtering
    document.querySelectorAll('[data-filter]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            currentFilter = e.target.dataset.filter;
            document.getElementById('filterLabel').innerText = `Filter: ${e.target.innerText}`;
            loadTasks(); // Reload from server (or re-render if caching)
        });
    });

    // 5. Bulk Actions
    clearSelectionBtn.addEventListener('click', () => {
        selectedTaskIds.clear();
        updateSelectionUI();
        renderTasks();
    });

    bulkDeleteBtn.addEventListener('click', () => {
        if (selectedTaskIds.size === 0) return;
        document.getElementById('deleteModalBody').innerText = `Are you sure you want to delete ${selectedTaskIds.size} tasks?`;
        document.getElementById('deleteIsBulk').value = 'true';
        deleteTaskModal.show();
    });

    confirmDeleteBtn.addEventListener('click', async () => {
        const isBulk = document.getElementById('deleteIsBulk').value === 'true';

        if (isBulk) {
            const ids = Array.from(selectedTaskIds);
            try {
                const res = await fetch('/api/tasks/bulk_delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({ ids })
                });
                if (res.ok) {
                    selectedTaskIds.clear();
                    updateSelectionUI();
                    loadTasks();
                    deleteTaskModal.hide();
                    showToast("Tasks moved to trash", "success");
                }
            } catch (e) { console.error(e); }
        } else {
            const id = document.getElementById('deleteTaskId').value;
            try {
                const res = await fetch(`/api/tasks/${id}`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrfToken }
                });
                if (res.ok) {
                    loadTasks();
                    deleteTaskModal.hide();
                    showToast("Task moved to trash", "success");
                }
            } catch (e) { console.error(e); }
        }
    });


    // --- Functions ---

    async function loadTasks() {
        taskListEl.innerHTML = '<div class="text-center text-muted py-4">Loading...</div>';
        try {
            // Fetch with status filter if needed, otherwise filter client side
            let url = '/api/tasks';
            if (currentFilter !== 'all') url += `?status=${currentFilter}`;

            const res = await fetch(url);
            tasksData = await res.json();
            renderTasks();
        } catch (err) {
            console.error(err);
            taskListEl.innerHTML = '<div class="text-center text-danger py-4">Error loading tasks.</div>';
        }
    }

    function renderTasks() {
        // 1. Sort Data
        let displayData = [...tasksData];
        if (currentSort === 'due_asc') {
            displayData.sort((a, b) => {
                if (!a.due_date) return 1;
                if (!b.due_date) return -1;
                return new Date(a.due_date) - new Date(b.due_date);
            });
        } else if (currentSort === 'newest') {
            displayData.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        } else if (currentSort === 'alpha') {
            displayData.sort((a, b) => a.title.localeCompare(b.title));
        } else {
            // Manual: sort by position
            displayData.sort((a, b) => a.position - b.position);
        }

        if (displayData.length === 0) {
            taskListEl.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-clipboard-check display-4 mb-3 d-block opacity-50"></i>
                    <p>No tasks found. Create one!</p>
                </div>
            `;
            return;
        }

        taskListEl.innerHTML = displayData.map(t => createTaskHTML(t)).join('');

        // Re-init Sortable only if sort is manual
        if (currentSort === 'manual') {
            initSortable();
        }
    }

    function createTaskHTML(t) {
        const isSelected = selectedTaskIds.has(t.id);
        const statusClass = t.status === 'todo' ? 'status-todo' : (t.status === 'in_progress' ? 'status-inprogress' : 'status-done');
        const badgeClass = t.status === 'todo' ? 'bg-secondary' : (t.status === 'in_progress' ? 'bg-warning text-dark' : 'bg-success');
        const statusLabel = t.status === 'todo' ? 'To Do' : (t.status === 'in_progress' ? 'In Progress' : 'Done');
        const checkIcon = isSelected ? 'bi-check-circle-fill text-primary' : 'bi-circle text-muted';

        // Due date formatting
        let dueHtml = '';
        if (t.due_date) {
            const d = new Date(t.due_date);
            const now = new Date();
            now.setHours(0, 0, 0, 0);
            const isOverdue = d < now && t.status !== 'done';
            dueHtml = `<small class="me-3 ${isOverdue ? 'text-danger fw-bold' : ''}"><i class="bi bi-calendar-event me-1"></i>${d.toLocaleDateString()}</small>`;
        }

        return `
        <div class="task-row ${statusClass} ${isSelected ? 'selected-row' : ''}" data-id="${t.id}">
            <div class="pt-1">
                <i class="bi ${checkIcon} task-check" onclick="toggleSelection(${t.id}, event)"></i>
            </div>
            <div class="flex-grow-1" onclick="editTask(${t.id})">
                <div class="d-flex align-items-start justify-content-between">
                    <div class="task-title mb-1">${escapeHtml(t.title)}</div>
                    <span class="badge ${badgeClass} badge-status ms-2">${statusLabel}</span>
                </div>
                <div class="task-meta">
                    ${dueHtml}
                    <span class="text-truncate d-inline-block" style="max-width: 300px; vertical-align: bottom;">${escapeHtml(t.description)}</span>
                </div>
            </div>
            <div class="dropdown">
                <button class="btn btn-link text-muted p-0" data-bs-toggle="dropdown"><i class="bi bi-three-dots-vertical"></i></button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><button class="dropdown-item" onclick="editTask(${t.id})"><i class="bi bi-pencil me-2"></i>Edit</button></li>
                    <li><button class="dropdown-item text-danger" onclick="promptDelete(${t.id})"><i class="bi bi-trash me-2"></i>Delete</button></li>
                </ul>
            </div>
        </div>
        `;
    }

    function initSortable() {
        new Sortable(taskListEl, {
            animation: 150,
            ghostClass: 'bg-light',
            onEnd: async function () {
                // Get new order
                const ids = Array.from(taskListEl.children).map(row => row.dataset.id);
                await fetch('/api/tasks/reorder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({ ids })
                });
            }
        });
    }

    function resetForm() {
        inpId.value = '';
        inpTitle.value = '';
        inpDesc.value = '';
        inpDue.value = '';
        inpStatus.value = 'todo';
        inpTitle.classList.remove('is-invalid');
    }

    // Expose functions to global scope for onclick handlers in HTML
    window.editTask = (id) => {
        const t = tasksData.find(x => x.id == id);
        if (!t) return;
        inpId.value = t.id;
        inpTitle.value = t.title;
        inpDesc.value = t.description;
        inpDue.value = t.due_date ? t.due_date : '';
        inpStatus.value = t.status;
        taskModal.show();
    };

    window.promptDelete = (id) => {
        document.getElementById('deleteModalBody').innerText = "Are you sure you want to delete this task?";
        document.getElementById('deleteTaskId').value = id;
        document.getElementById('deleteIsBulk').value = 'false';
        deleteTaskModal.show();
    };

    window.toggleSelection = (id, e) => {
        e.stopPropagation();
        if (selectedTaskIds.has(id)) selectedTaskIds.delete(id);
        else selectedTaskIds.add(id);
        updateSelectionUI();
        renderTasks();
    };

    function updateSelectionUI() {
        const count = selectedTaskIds.size;
        if (count > 0) {
            defaultHeader.classList.remove('d-flex');
            defaultHeader.classList.add('d-none');
            selectionHeader.classList.remove('d-none');
            selectionHeader.classList.add('d-flex');
            selectedCountEl.innerText = count;
        } else {
            defaultHeader.classList.remove('d-none');
            defaultHeader.classList.add('d-flex');
            selectionHeader.classList.remove('d-flex');
            selectionHeader.classList.add('d-none');
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }
});
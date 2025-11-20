(() => {
  // 1. HTML for Modals
  function ensureModals() {
    if (document.getElementById('renameWorkspaceModal')) return;
    const html = `
      <div class="modal fade" id="renameWorkspaceModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered"><div class="modal-content bg-dark text-light">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">Rename Workspace</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <form id="renameWorkspaceForm">
            <div class="modal-body">
              <label class="form-label small">New name</label>
              <input id="renameWorkspaceName" class="form-control form-control-sm" type="text" required>
            </div>
            <div class="modal-footer border-secondary">
              <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
              <button type="submit" class="btn btn-primary btn-sm">Save</button>
            </div>
          </form>
        </div></div>
      </div>
      <!-- DELETE CONFIRMATION MODAL -->
      <div class="modal fade" id="deleteWorkspaceModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered"><div class="modal-content bg-dark text-light">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">Delete Workspace</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            Are you sure you want to move <strong id="deleteWorkspaceName"></strong> to trash?
          </div>
          <div class="modal-footer border-secondary">
            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
            <button id="confirmDeleteWsBtn" type="button" class="btn btn-danger btn-sm">Move to Trash</button>
          </div>
        </div></div>
      </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
  }

  // 2. API Helper
  async function api(url, method = 'GET', body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || 'Request failed');
    return data;
  }

  // 3. Render Sidebar List
  async function renderList() {
    const list = document.getElementById('workspaceList');
    if (!list) return;

    const pathParts = window.location.pathname.split('/');
    const currentWsId = (pathParts[1] === 'workspaces' && pathParts[2]) ? parseInt(pathParts[2]) : null;

    list.innerHTML = '<li class="nav-item"><span class="nav-link disabled text-secondary small">Loading…</span></li>';

    try {
      const items = await api('/api/workspaces');

      if (items.length === 0) {
        list.innerHTML = `<li class="nav-item text-center mt-2"><span class="text-muted small">No workspaces yet.<br>Click '+' to add.</span></li>`;
        return;
      }

      list.innerHTML = '';
      items.forEach(ws => {
        const li = document.createElement('li');
        li.className = 'nav-item position-relative';
        li.dataset.id = ws.id;

        const isActive = currentWsId === ws.id ? 'active' : '';

        li.innerHTML = `
          <a href="/workspaces/${ws.id}" class="nav-link d-flex align-items-center justify-content-between pe-1 ${isActive}" data-ws-id="${ws.id}">
            <span class="d-flex align-items-center text-truncate">
                <i class="bi bi-journal-text me-2 opacity-75"></i>
                <span class="text-truncate">${escapeHtml(ws.name)}</span>
            </span>
            <div class="dropdown">
                <button class="ws-actions-btn" data-bs-toggle="dropdown" aria-expanded="false" onclick="event.preventDefault()">
                    <i class="bi bi-three-dots"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-sm">
                    <li><button class="dropdown-item small" data-action="rename" data-id="${ws.id}"><i class="bi bi-pencil me-2"></i>Rename</button></li>
                    <li><hr class="dropdown-divider border-secondary"></li>
                    <li><button class="dropdown-item small text-danger" data-action="delete" data-id="${ws.id}"><i class="bi bi-trash me-2"></i>Delete</button></li>
                </ul>
            </div>
          </a>
        `;
        list.appendChild(li);
      });

      if (window.Sortable) {
        new Sortable(list, {
          animation: 150,
          onEnd: function () { saveWorkspaceOrder(); }
        });
      }

    } catch (err) {
      list.innerHTML = `<li class="nav-item"><span class="nav-link disabled text-danger">Failed to load</span></li>`;
      console.error(err);
    }
  }

  // 4. Save Drag Order
  async function saveWorkspaceOrder() {
    const list = document.getElementById('workspaceList');
    const orderedIds = Array.from(list.querySelectorAll('li.nav-item')).map(li => parseInt(li.dataset.id));
    if (orderedIds.length > 0) {
      try { await api('/api/workspaces/reorder', 'POST', { ids: orderedIds }); } catch (e) { }
    }
  }

  // 5. Wire up Forms (Rename & Delete)
  function wireForms() {
    const renameForm = document.getElementById('renameWorkspaceForm');
    if (renameForm && !renameForm._wired) {
      renameForm._wired = true;
      renameForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const newName = document.getElementById('renameWorkspaceName').value.trim();
        const id = renameForm.dataset.id;
        if (!newName || !id) return;
        await api(`/api/workspaces/${id}`, 'PUT', { name: newName });
        bootstrap.Modal.getInstance(document.getElementById('renameWorkspaceModal')).hide();
        renderList();
        if (window.location.pathname.includes(`/workspaces/${id}`)) window.location.reload();
      });
    }

    const delBtn = document.getElementById('confirmDeleteWsBtn');
    if (delBtn && !delBtn._wired) {
      delBtn._wired = true;
      delBtn.addEventListener('click', async () => {
        const id = delBtn.dataset.id;
        if (!id) return;

        try {
          // Perform Soft Delete
          await api(`/api/workspaces/${id}`, 'DELETE');

          // Close Modal
          bootstrap.Modal.getInstance(document.getElementById('deleteWorkspaceModal')).hide();

          // Redirect if we were inside that workspace, else just refresh list
          if (window.location.pathname.includes(`/workspaces/${id}`)) {
            window.location.href = '/tasks';
          } else {
            renderList();
          }
        } catch (e) {
          console.error("Delete failed", e);
          alert("Could not delete workspace.");
        }
      });
    }
  }

  // 6. Trash Logic
  let wsTrashModal;
  async function openWsTrash() {
    const el = document.getElementById('workspaceTrashModal');
    if (!el) return;
    if (!wsTrashModal) wsTrashModal = new bootstrap.Modal(el);

    wsTrashModal.show();
    const container = document.getElementById('wsTrashList');
    container.innerHTML = '<div class="spinner-border spinner-border-sm text-secondary"></div>';

    try {
      const items = await api('/api/trash/workspaces');
      if (items.length === 0) {
        container.innerHTML = '<p class="text-muted">Trash is empty.</p>';
        return;
      }

      container.innerHTML = items.map(ws => `
            <div class="trash-item">
                <span class="fw-bold text-dark">${escapeHtml(ws.name)}</span>
                <div class="trash-actions d-flex gap-2">
                    <button class="btn btn-sm btn-outline-primary restore-ws-btn" data-id="${ws.id}">Restore</button>
                    <button class="btn btn-sm btn-outline-danger delete-ws-btn" data-id="${ws.id}">Delete Forever</button>
                </div>
            </div>
          `).join('');

      container.querySelectorAll('.restore-ws-btn').forEach(b => b.addEventListener('click', () => restoreWorkspace(b.dataset.id)));
      container.querySelectorAll('.delete-ws-btn').forEach(b => b.addEventListener('click', () => hardDeleteWorkspace(b.dataset.id)));

    } catch (e) {
      container.innerHTML = '<p class="text-danger">Failed to load.</p>';
    }
  }

  async function restoreWorkspace(id) {
    await api(`/api/workspaces/${id}/restore`, 'POST');
    openWsTrash();
    renderList();
  }

  async function hardDeleteWorkspace(id) {
    if (!confirm("Delete permanently? This cannot be undone.")) return;
    await api(`/api/workspaces/${id}/permanent`, 'DELETE');
    openWsTrash();
  }

  // 7. Global Event Listener
  document.addEventListener('click', async (e) => {

    // Trash Button
    if (e.target.closest('#openWsTrashBtn')) {
      e.preventDefault();
      openWsTrash();
      return;
    }

    // Create Workspace Button
    const createBtn = e.target.closest('[data-action="open-create-workspace"]');
    if (createBtn) {
      e.preventDefault();
      try {
        await api('/api/workspaces', 'POST', {});
        await renderList();
      } catch (err) { console.error(err); alert("Failed to create workspace"); }
      return;
    }

    // Rename Button
    const renameBtn = e.target.closest('[data-action="rename"]');
    if (renameBtn) {
      e.preventDefault(); e.stopPropagation();
      ensureModals(); wireForms();
      const id = renameBtn.dataset.id;
      document.getElementById('renameWorkspaceForm').dataset.id = id;
      document.getElementById('renameWorkspaceName').value = '';
      new bootstrap.Modal(document.getElementById('renameWorkspaceModal')).show();
      return;
    }

    // Delete Button (Opens Confirm Modal)
    const deleteBtn = e.target.closest('[data-action="delete"]');
    if (deleteBtn) {
      e.preventDefault(); e.stopPropagation();
      ensureModals(); wireForms();
      const id = deleteBtn.dataset.id;
      // IMPORTANT: Pass the ID to the confirm button inside the modal
      document.getElementById('confirmDeleteWsBtn').dataset.id = id;
      document.getElementById('deleteWorkspaceName').textContent = 'this workspace';
      new bootstrap.Modal(document.getElementById('deleteWorkspaceModal')).show();
      return;
    }
  });

  function escapeHtml(s) { return (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])) }

  // Init
  ensureModals();
  wireForms();
  renderList();
})();
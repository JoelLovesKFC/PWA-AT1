(() => {
  function ensureModals() {
    if (document.getElementById('createWorkspaceModal')) return;
    const html = `
      <div class="modal fade" id="createWorkspaceModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered"><div class="modal-content bg-dark text-light">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">Create Workspace</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <form id="createWorkspaceForm">
            <div class="modal-body">
              <label class="form-label small">Name</label>
              <input id="createWorkspaceName" class="form-control form-control-sm" type="text" placeholder="e.g., Design Team" required>
            </div>
            <div class="modal-footer border-secondary">
              <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
              <button type="submit" class="btn btn-primary btn-sm">Create</button>
            </div>
          </form>
        </div></div>
      </div>
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
      <div class="modal fade" id="deleteWorkspaceModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered"><div class="modal-content bg-dark text-light">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">Delete Workspace</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            Are you sure you want to delete <strong id="deleteWorkspaceName"></strong>?
          </div>
          <div class="modal-footer border-secondary">
            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
            <button id="confirmDeleteBtn" type="button" class="btn btn-danger btn-sm">Delete</button>
          </div>
        </div></div>
      </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
  }

  async function api(url, method = 'GET', body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || 'Request failed');
    return data;
  }

  async function renderList() {
    const list = document.getElementById('workspaceList');
    if (!list) return;
    list.innerHTML = '<li class="nav-item"><span class="nav-link disabled">Loading…</span></li>';
    try {
      const items = await api('/api/workspaces');
      list.innerHTML = items.length ? '' : '<li class="nav-item"><span class="nav-link disabled">No workspaces</span></li>';
      items.forEach(ws => {
        const li = document.createElement('li');
        li.className = 'nav-item d-flex align-items-center';
        li.innerHTML = `
          <a href="#" class="nav-link flex-grow-1 d-flex align-items-center" data-ws-id="${ws.id}">
            <i class="bi bi-kanban"></i><span class="ms-1 text-truncate">${ws.name}</span>
          </a>
          <div class="dropend ms-1">
            <button class="btn btn-sm btn-dark" data-bs-toggle="dropdown" aria-expanded="false">
              <i class="bi bi-three-dots-vertical"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-dark">
              <li><button class="dropdown-item" data-action="rename" data-id="${ws.id}"><i class="bi bi-pencil me-2"></i>Rename</button></li>
              <li><button class="dropdown-item text-danger" data-action="delete" data-id="${ws.id}"><i class="bi bi-trash me-2"></i>Delete</button></li>
            </ul>
          </div>`;
        list.appendChild(li);
      });
    } catch (err) {
      list.innerHTML = `<li class="nav-item"><span class="nav-link disabled">Failed to load</span></li>`;
      console.error(err);
    }
  }

  function wireForms() {
    const createForm = document.getElementById('createWorkspaceForm');
    if (createForm && !createForm._wired) {
      createForm._wired = true;
      createForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('createWorkspaceName').value.trim();
        if (!name) return;
        await api('/api/workspaces', 'POST', { name });
        document.getElementById('createWorkspaceName').value = '';
        bootstrap.Modal.getInstance(document.getElementById('createWorkspaceModal')).hide();
        renderList();
      });
    }

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
      });
    }

    const delBtn = document.getElementById('confirmDeleteBtn');
    if (delBtn && !delBtn._wired) {
      delBtn._wired = true;
      delBtn.addEventListener('click', async () => {
        const id = delBtn.dataset.id;
        if (!id) return;
        await api(`/api/workspaces/${id}`, 'DELETE');
        bootstrap.Modal.getInstance(document.getElementById('deleteWorkspaceModal')).hide();
        renderList();
      });
    }
  }

  document.addEventListener('click', (e) => {
    const createBtn = e.target.closest('[data-bs-target="#createWorkspaceModal"], [data-action="open-create-workspace"]');
    if (createBtn) {
      ensureModals(); wireForms();
      new bootstrap.Modal(document.getElementById('createWorkspaceModal')).show();
      return;
    }

    const renameBtn = e.target.closest('[data-action="rename"]');
    if (renameBtn) {
      ensureModals(); wireForms();
      const id = renameBtn.dataset.id;
      document.getElementById('renameWorkspaceForm').dataset.id = id;
      document.getElementById('renameWorkspaceName').value = '';
      new bootstrap.Modal(document.getElementById('renameWorkspaceModal')).show();
      return;
    }

    const deleteBtn = e.target.closest('[data-action="delete"]');
    if (deleteBtn) {
      ensureModals(); wireForms();
      const id = deleteBtn.dataset.id;
      document.getElementById('confirmDeleteBtn').dataset.id = id;
      document.getElementById('deleteWorkspaceName').textContent = 'this workspace';
      new bootstrap.Modal(document.getElementById('deleteWorkspaceModal')).show();
      return;
    }
  });

  ensureModals();
  wireForms();
  renderList();
})();

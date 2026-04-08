/* global API, routeTitle, routeContent */
"use strict";

window.ConfigModule = (function () {
  const roleLabels = {
    administracion: "Administración",
    recepcionista: "Recepción",
    profesional: "Profesional",
    contador: "Contador",
  };

  const state = {
    users: [],
    roles: [],
    permissions: [],
    modules: [],
  };

  const selectors = {};

  async function loadUsers() {
    const res = await API.request("/api/config/users");
    state.users = res.data || [];
    state.roles = res.roles || Object.keys(roleLabels);
    renderUsers();
  }

  async function loadPermissions() {
    const res = await API.request("/api/config/permissions");
    state.permissions = res.data || [];
    state.modules = res.modules || [];
    if (!state.roles.length && res.roles) {
      state.roles = res.roles;
    }
    renderPermissions();
  }

  async function refreshAll() {
    try {
      await Promise.all([loadUsers(), loadPermissions()]);
    } catch (err) {
      alert(err.message || err);
    }
  }

  function renderUsers() {
    const tbody = selectors.usersBody;
    if (!tbody) return;
    if (!state.users.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="table__empty muted">Sin usuarios registrados</td></tr>`;
    } else {
      tbody.innerHTML = state.users
        .map((user) => {
          const roleOptions = state.roles
            .map(
              (role) =>
                `<option value="${role}" ${role === user.rol ? "selected" : ""}>${roleLabels[role] || role}</option>`
            )
            .join("");
          const checked = user.activo ? "checked" : "";
          return `
            <tr data-id="${user.id}">
              <td>
                <div class="table-main">${user.nombre}</div>
                <div class="table-sub muted">${user.email}</div>
              </td>
              <td class="table-center">
                <select class="input input--select cfg-user-role" data-id="${user.id}">
                  ${roleOptions}
                </select>
              </td>
              <td class="table-center">
                <label class="switch">
                  <input type="checkbox" class="cfg-user-active" data-id="${user.id}" ${checked}>
                  <span class="switch__slider"></span>
                </label>
              </td>
              <td class="table-actions">
                <button class="button button--ghost cfg-reset-pass" data-id="${user.id}">Reiniciar clave</button>
              </td>
            </tr>
          `;
        })
        .join("");
    }

    tbody.querySelectorAll(".cfg-user-role").forEach((sel) => {
      sel.addEventListener("change", async (e) => {
        const id = Number(e.target.dataset.id);
        const rol = e.target.value;
        try {
          await API.request(`/api/config/users/${id}`, {
            method: "PUT",
            body: JSON.stringify({ rol }),
          });
        } catch (err) {
          alert(err.message || err);
          await loadUsers();
        }
      });
    });

    tbody.querySelectorAll(".cfg-user-active").forEach((chk) => {
      chk.addEventListener("change", async (e) => {
        const id = Number(e.target.dataset.id);
        const value = e.target.checked;
        try {
          await API.request(`/api/config/users/${id}`, {
            method: "PUT",
            body: JSON.stringify({ activo: value }),
          });
        } catch (err) {
          alert(err.message || err);
          e.target.checked = !value;
        }
      });
    });

    tbody.querySelectorAll(".cfg-reset-pass").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = Number(e.target.dataset.id);
        const nueva = prompt("Nueva contraseña");
        if (!nueva) return;
        try {
          await API.request(`/api/config/users/${id}`, {
            method: "PUT",
            body: JSON.stringify({ password: nueva }),
          });
          alert("Contraseña actualizada");
        } catch (err) {
          alert(err.message || err);
        }
      });
    });
  }

  function renderPermissions() {
    const wrapper = selectors.permsWrapper;
    if (!wrapper) return;
    if (!state.permissions.length) {
      wrapper.innerHTML = `<div class="muted">Sin información de permisos.</div>`;
      return;
    }
    const moduleMap = Object.fromEntries((state.modules || []).map((m) => [m.key, m.label]));
    const grouped = {};
    state.permissions.forEach((perm) => {
      if (!grouped[perm.role]) grouped[perm.role] = [];
      grouped[perm.role].push(perm);
    });
    Object.keys(grouped).forEach((role) => {
      grouped[role].sort(
        (a, b) => (moduleMap[a.module] || a.module).localeCompare(moduleMap[b.module] || b.module)
      );
    });

    wrapper.innerHTML = state.roles
      .map((role) => {
        const perms = grouped[role] || [];
        const rows = perms
          .map((perm) => {
            const readChecked = perm.can_read ? "checked" : "";
            const writeChecked = perm.can_write ? "checked" : "";
            return `
              <tr data-id="${perm.id}">
                <td>${moduleMap[perm.module] || perm.module}</td>
                <td class="table-center">
                  <label class="switch">
                    <input type="checkbox" class="perm-toggle" data-field="can_read" data-id="${perm.id}" ${readChecked}>
                    <span class="switch__slider"></span>
                  </label>
                </td>
                <td class="table-center">
                  <label class="switch">
                    <input type="checkbox" class="perm-toggle" data-field="can_write" data-id="${perm.id}" ${writeChecked}>
                    <span class="switch__slider"></span>
                  </label>
                </td>
              </tr>
            `;
          })
          .join("");
        return `
          <article class="card config-card" style="margin-bottom: 0;">
            <header class="card__header" style="background: var(--color-surface-soft); padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--color-border); border-radius: 6px 6px 0 0;">
              <h3 class="card__title" style="font-size: 1rem;">Rol: ${roleLabels[role] || role}</h3>
            </header>
            <div class="card__body" style="padding: 0;">
              <table class="table table--compact" style="margin: 0; font-size: 0.85rem; border: none;">
                <thead>
                  <tr><th>Módulo</th><th class="table-center">Lectura</th><th class="table-center">Edición</th></tr>
                </thead>
                <tbody>
                  ${rows || `<tr><td colspan="3" class="table__empty muted">Sin módulos configurados.</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
        `;
      })
      .join("");

    wrapper.querySelectorAll(".perm-toggle").forEach((chk) => {
      chk.addEventListener("change", async (e) => {
        const checkbox = e.target;
        const id = Number(checkbox.dataset.id);
        const field = checkbox.dataset.field;
        const value = checkbox.checked;
        const payload = { [field]: value };

        if (field === "can_write" && value) {
          payload.can_read = true;
          const row = checkbox.closest("tr");
          const readToggle = row?.querySelector('.perm-toggle[data-field="can_read"]');
          if (readToggle && !readToggle.checked) {
            readToggle.checked = true;
          }
        }

        try {
          await API.request(`/api/config/permissions/${id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
        } catch (err) {
          alert(err.message || err);
          checkbox.checked = !value;
        }
      });
    });
  }

  async function handleUserCreate(ev) {
    ev.preventDefault();
    const form = ev.target;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    try {
      await API.request("/api/config/users", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      form.reset();
      await loadUsers();
    } catch (err) {
      alert(err.message || err);
    }
  }

  function render() {
    routeTitle.textContent = "Configuración";
    routeContent.innerHTML = `
      <div class="page-shell config-page split-layout">
        <aside class="split-layout__sidebar" style="display: flex; flex-direction: column; gap: var(--space-5);">
          <article class="card form-card">
            <header class="card__header">
              <h2 class="card__title">Nuevo Usuario</h2>
              <p class="card__subtitle">Cree cuentas y asigne roles.</p>
            </header>
            <div class="card__body config-users">
              <form id="cfg-user-form" class="form config-user-form">
                <div class="form-grid config-user-grid" style="grid-template-columns: 1fr; gap: var(--space-3);">
                  <div class="form-field">
                    <label class="form-field__label">Nombre</label>
                    <input name="nombre" class="input" required placeholder="Nombre completo">
                  </div>
                  <div class="form-field">
                    <label class="form-field__label">Email</label>
                    <input name="email" type="email" class="input" required placeholder="usuario@dominio.com">
                  </div>
                  <div class="form-grid form-grid--two">
                      <div class="form-field">
                        <label class="form-field__label">Rol</label>
                        <select name="rol" class="input input--select" required>
                          ${Object.entries(roleLabels).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
                        </select>
                      </div>
                      <div class="form-field">
                        <label class="form-field__label">Contraseña</label>
                        <input name="password" type="password" class="input" required placeholder="Inicial">
                      </div>
                  </div>
                </div>
                <div class="form-actions" style="margin-top: var(--space-4);">
                  <button type="submit" class="button button--primary" style="width: 100%;">Crear usuario</button>
                </div>
              </form>
            </div>
          </article>
        </aside>

        <main class="split-layout__main" style="display: flex; flex-direction: column; gap: var(--space-5);">
          
          <article class="card list-card">
            <header class="card__header">
              <h2 class="card__title">Directorio de Usuarios</h2>
            </header>
            <div class="card__body">
              <div class="table-shell" style="max-height: 250px;">
                <table class="table table--compact">
                  <thead>
                    <tr>
                      <th>Usuario</th>
                      <th class="table-center">Rol</th>
                      <th class="table-center">Activo</th>
                      <th class="table-center">Acciones</th>
                    </tr>
                  </thead>
                  <tbody id="cfg-users-body"></tbody>
                </table>
              </div>
            </div>
          </article>

          <article class="card list-card">
            <header class="card__header">
              <h2 class="card__title">Accesos por módulos</h2>
              <p class="card__subtitle" style="margin-top: 4px;">Controle qué puede ver o editar cada rol dentro del sistema.</p>
            </header>
            <div class="card__body">
              <div id="cfg-perms-wrapper" class="config-perms-wrapper" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-4); background: var(--color-surface-soft); padding: 16px; border-radius: 8px;">
                <div class="muted">Cargando permisos...</div>
              </div>
            </div>
          </article>

        </main>
      </div>
    `;

    selectors.usersBody = document.getElementById("cfg-users-body");
    selectors.permsWrapper = document.getElementById("cfg-perms-wrapper");

    const form = document.getElementById("cfg-user-form");
    if (form) form.addEventListener("submit", handleUserCreate);

    refreshAll();
  }

  return { render };
})();

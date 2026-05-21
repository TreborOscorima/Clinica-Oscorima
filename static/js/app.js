window.loginView = document.getElementById("login-view");
window.routerView = document.getElementById("router-view");
window.routeTitle = document.getElementById("route-title");
window.routeContent = document.getElementById("route-content");
window.bodyEl = document.body;
window.sidebarEl = document.getElementById("sidebar");
window.navToggleBtn = document.getElementById("nav-toggle");

const routeLoader = document.getElementById("route-loader");

function _updateTopbarUser(name) {
  const nameEl = document.getElementById("user-display-name");
  const avatarEl = document.getElementById("user-avatar");
  if (nameEl) nameEl.textContent = name;
  if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase();
}

// Setup FAB for Mobile Bottom-sheets
window.setupMobileFab = function() {
  const fab = document.getElementById("fab-mobile");
  const overlay = document.getElementById("bottom-sheet-overlay");
  const sidebar = document.querySelector(".split-layout__sidebar");
  
  if (!fab || !overlay) return;
  
  fab.replaceWith(fab.cloneNode(true));
  overlay.replaceWith(overlay.cloneNode(true));
  
  const newFab = document.getElementById("fab-mobile");
  const newOverlay = document.getElementById("bottom-sheet-overlay");
  
  if (sidebar) {
    newFab.classList.add("is-visible");
    newFab.addEventListener("click", () => {
      sidebar.classList.add("is-open");
      newOverlay.classList.add("is-active");
    });
    newOverlay.addEventListener("click", () => {
      sidebar.classList.remove("is-open");
      newOverlay.classList.remove("is-active");
    });
  } else {
    newFab.classList.remove("is-visible");
  }
};
const footerYear = document.querySelector('.sidebar__footer small');
if (footerYear) {
  footerYear.textContent = '© ' + new Date().getFullYear() + ' Clínica Estética WAYKI SAC';
}



const routes = {
  dashboard: () => {
    window.routeTitle.textContent = "Inicio";
    const userName = localStorage.getItem("wayki_user_name") || "Administrador";
    const tiles = [
      { route: "turnos",        label: "Turnos",        icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>' },
      { route: "caja",          label: "Caja",          icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/><path d="M7 15h4m4 0h2"/></svg>' },
      { route: "pacientes",     label: "Pacientes",     icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' },
      { route: "profesionales", label: "Profesionales", icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4"/><circle cx="20" cy="10" r="2"/></svg>' },
      { route: "inventario",    label: "Inventario",    icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>' },
      { route: "compras",       label: "Compras",       icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>' },
      { route: "servicios",     label: "Servicios",     icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>' },
      { route: "reportes",      label: "Reportes",      icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>' },
      { route: "configuracion", label: "Ajustes",       icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' },
    ];

    const now = new Date();
    const hora = now.getHours();
    const saludo = hora < 12 ? "¡Buenos días" : hora < 19 ? "¡Buenas tardes" : "¡Buenas noches";
    const fechaStr = now.toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });
    const fechaCap = fechaStr.charAt(0).toUpperCase() + fechaStr.slice(1);

    window.routeContent.innerHTML = `
      <div class="page-shell animate-in">
        <div class="dash-layout">

          <div class="dash-layout__main">
            <div class="dash-greeting">
              <h1 class="dash-greeting__hello">${saludo}, ${userName}!</h1>
              <p class="dash-greeting__sub">Gestioná turnos, caja, inventario y reportes desde una sola plataforma.</p>
            </div>

            <p class="dash-section-label">¿Qué necesitás hoy?</p>
            <div class="feature-tiles">
              ${tiles.map((t, i) => `
                <button class="feature-tile animate-in stagger-${i + 1}" data-route="${t.route}" aria-label="Ir a ${t.label}">
                  <div class="feature-tile__icon">${t.icon}</div>
                  <span class="feature-tile__label">${t.label}</span>
                </button>
              `).join("")}
            </div>
          </div>

          <aside class="dash-side">
            <div class="dash-info-card dash-info-card--blue animate-in stagger-2">
              <div class="dash-info-card__header">
                <div class="dash-info-card__icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                </div>
                <span class="dash-info-card__eyebrow">Hoy</span>
              </div>
              <div>
                <p class="dash-info-card__title">Agenda del día</p>
                <p class="dash-info-card__body">${fechaCap}</p>
              </div>
              <button class="dash-info-card__action" data-route="turnos">
                Ver turnos
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </button>
            </div>

            <div class="dash-info-card dash-info-card--teal animate-in stagger-3">
              <div class="dash-info-card__header">
                <div class="dash-info-card__icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                </div>
                <span class="dash-info-card__eyebrow">Caja</span>
              </div>
              <div>
                <p class="dash-info-card__title">Movimientos</p>
                <p class="dash-info-card__body">Registrá ingresos y egresos del día.</p>
              </div>
              <button class="dash-info-card__action" data-route="caja">
                Ir a caja
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </button>
            </div>

            <div class="dash-info-card dash-info-card--rose animate-in stagger-4">
              <div class="dash-info-card__header">
                <div class="dash-info-card__icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
                </div>
                <span class="dash-info-card__eyebrow">Inventario</span>
              </div>
              <div>
                <p class="dash-info-card__title">Control de stock</p>
                <p class="dash-info-card__body">Revisá productos con stock bajo.</p>
              </div>
              <button class="dash-info-card__action" data-route="inventario">
                Ver stock
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
              </button>
            </div>
          </aside>

        </div>
      </div>
    `;

    window.routeContent.querySelectorAll(".feature-tile, .dash-info-card__action").forEach((el) => {
      el.addEventListener("click", () => navigate(el.dataset.route));
      el.addEventListener("keypress", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); navigate(el.dataset.route); }
      });
    });
  },
  pacientes: window.PacientesModule.render,
  turnos: window.TurnosModule.render,
  servicios: window.ServiciosModule.render,
  profesionales: window.ProfesionalesModule.render,
  caja: window.CajaModule.render,
  inventario: window.InventarioModule.render,
  compras: window.ComprasModule.render,
  reportes: window.ReportesModule.render,
  configuracion: window.ConfigModule.render,
};

function setActiveNav(route) {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('is-active', link.dataset.route === route);
  });
}

function closeSidebar() {
  if (!sidebarEl) return;
  sidebarEl.classList.remove('sidebar--open');
  bodyEl.classList.remove('sidebar-open');
}



// --- navegación centralizada ---
function navigate(route) {
  const fn = routes[route];
  if (location.hash !== `#/${route}` && !location.hash.startsWith(`#/${route}?`)) {
    location.hash = `#/${route}`;
  }
  
  if (window.routeTitle) window.routeTitle.textContent = route.charAt(0).toUpperCase() + route.slice(1);
  setActiveNav(route);
  closeSidebar();
  
  // Transición elegante y setup de FAB
  if (routeLoader) routeLoader.style.display = "block";
  if (window.routeContent) window.routeContent.classList.add("is-loading");
  
  setTimeout(() => {
    if (typeof fn === "function") {
      fn();
    } else {
      if (window.routeContent) window.routeContent.innerHTML = "<div class='card'>Ruta no encontrada</div>";
    }
    
    if (window.routeContent) window.routeContent.classList.remove("is-loading");
    if (routeLoader) routeLoader.style.display = "none";
    window.setupMobileFab();
  }, 150);
}

// abre la ruta del hash si existe (ej: #/caja?turno=5)
function openFromHash() {
  if (!API.hasSession()) return; // si no hay token valido, no navegar
  if (location.hash.startsWith("#/")) {
    const route = location.hash.slice(2).split("?")[0];
    if (routes[route]) return navigate(route);
  }
  // por defecto
  navigate("dashboard");
}

// --- auth guard ---
async function checkAuth() {
  let has = API.hasSession();
  if (has) {
    try {
      await API.ensureAccessToken();
      has = API.hasSession();
    } catch (err) {
      has = false;
    }
  }
  window.loginView.style.display = has ? "none" : "block";
  window.routerView.style.display = has ? "block" : "none";
  document.body.classList.toggle('is-authenticated', has);
  if (!has) {
    closeSidebar();
  } else {
    openFromHash();
  }
}

// --- login wiring (click + submit + errores) ---
const loginForm = document.getElementById("login-form");
const btnLogin  = document.getElementById("btn-login");
const emailEl   = document.getElementById("login-email");
const passEl    = document.getElementById("login-pass");
const loginMsg  = document.getElementById("login-msg");

async function doLogin(ev) {
  ev.preventDefault();
  loginMsg.textContent = "";
  const email = (emailEl.value || "").trim();
  const password = passEl.value || "";
  if (!email || !password) {
    loginMsg.textContent = "Completa email y contrasena.";
    return;
  }
  try {
    const res = await API.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: "none",
    });
    const { access_token, refresh_token, expires_at, refresh_expires_at } = res || {};
    if (!access_token || !refresh_token) {
      throw new Error("La respuesta no incluyo tokens de sesion.");
    }
    API.setTokens({
      accessToken: access_token,
      refreshToken: refresh_token,
      expiresAt: expires_at,
      refreshExpiresAt: refresh_expires_at,
    });
    const emailVal = (emailEl.value || "").trim();
    const displayName = (res && res.nombre) ? res.nombre : emailVal.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    localStorage.setItem("wayki_user_name", displayName);
    _updateTopbarUser(displayName);
    loginMsg.textContent = "Bienvenido!";
    await checkAuth();
  } catch (e) {
    API.clearTokens();
    loginMsg.textContent = (e && e.message) || "Credenciales invalidas o servidor no disponible.";
  }
}

if (loginForm) loginForm.addEventListener("submit", doLogin);
if (btnLogin)  btnLogin.addEventListener("click", doLogin);

// --- links del sidebar (bloquea si no hay token) ---
document.querySelectorAll("nav a[data-route]").forEach(a => {
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (!API.hasSession()) { checkAuth(); return; }
    const route = a.dataset.route;
    navigate(route);
    closeSidebar();
  });
});

if (navToggleBtn && sidebarEl) {
  navToggleBtn.addEventListener('click', () => {
    const willOpen = !sidebarEl.classList.contains('sidebar--open');
    sidebarEl.classList.toggle('sidebar--open', willOpen);
    bodyEl.classList.toggle('sidebar-open', willOpen);
  });
}



if (sidebarEl) {
  document.addEventListener("click", (ev) => {
    if (!bodyEl.classList.contains('sidebar-open')) return;
    if (sidebarEl.contains(ev.target)) return;
    if (navToggleBtn && navToggleBtn.contains(ev.target)) return;
    closeSidebar();
  });
}

window.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && bodyEl.classList.contains('sidebar-open')) {
    closeSidebar();
  }
});

window.addEventListener("resize", () => {
  if (window.innerWidth >= 960) {
    closeSidebar();
  }
});

window.addEventListener("api:session-ended", () => {
  checkAuth();
});

// --- logout ---
document.getElementById("logout").addEventListener("click", async (e) => {
  e.preventDefault();
  API.clearTokens();
  localStorage.removeItem("wayki_user_name");
  _updateTopbarUser("Admin");
  location.hash = "";
  closeSidebar();
  await checkAuth();
});

// --- cambiar de ruta si cambia el hash (ej: desde Turnos -> Caja con ?turno=ID) ---
window.addEventListener("hashchange", () => {
  if (!API.hasSession()) return;
  openFromHash();
});

// boot
const _savedName = localStorage.getItem("wayki_user_name");
if (_savedName) _updateTopbarUser(_savedName);
checkAuth();

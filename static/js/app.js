window.loginView = document.getElementById("login-view");
window.routerView = document.getElementById("router-view");
window.routeTitle = document.getElementById("route-title");
window.routeContent = document.getElementById("route-content");
window.bodyEl = document.body;
window.sidebarEl = document.getElementById("sidebar");
window.navToggleBtn = document.getElementById("nav-toggle");

const routeLoader = document.getElementById("route-loader");

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
    window.routeTitle.textContent = "Centro de Control";
    const shortcuts = [
      { route: "turnos", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>', title: "Turnos", description: "Gestione la agenda de los profesionales." },
      { route: "caja", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>', title: "Caja", description: "Movimientos, cobros y facturación." },
      { route: "pacientes", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>', title: "Pacientes", description: "Fichas, altas rápidas e historiales." },
      { route: "profesionales", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6 6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6 6 6 0 0 0 6-6v-4"/><circle cx="20" cy="10" r="2"/></svg>', title: "Profesionales", description: "Directorio del equipo y especialidades." },
      { route: "inventario", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>', title: "Inventario", description: "Control de stock e insumos médicos." },
      { route: "servicios", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>', title: "Servicios", description: "Precios y catálogo de tratamientos." },
      { route: "reportes", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>', title: "Reportes", description: "Análisis y exportación de datos." },
      { route: "configuracion", icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>', title: "Ajustes", description: "Permisos, roles y usuarios del sistema." },
    ];

    window.routeContent.innerHTML = `
      <div class="page-shell">
        <header class="dash-header">
          <div class="dash-header__text">
            <span class="eyebrow">Panel principal</span>
            <h1 style="font-family:var(--font-display);font-size:var(--fs-2xl);font-weight:700;margin:0;">Acceso Rápido</h1>
            <p style="color:var(--text-muted);margin-top:var(--s2);">Módulos del ecosistema WaykiSAC.</p>
          </div>
        </header>
        <div class="dashboard-shortcuts">
          ${shortcuts.map((item, i) => `
            <article class="card card--shortcut animate-in stagger-${i + 1}" data-route="${item.route}" tabindex="0" role="button" aria-label="Ir a ${item.title}">
              <div class="shortcut-icon">${item.icon}</div>
              <div class="shortcut-body">
                <h3 class="card__title">${item.title}</h3>
                <p class="card__subtitle">${item.description}</p>
              </div>
            </article>
          `).join("")}
        </div>
      </div>
    `;

    window.routeContent.querySelectorAll(".card--shortcut").forEach((card) => {
      card.addEventListener("click", () => navigate(card.dataset.route));
      card.addEventListener("keypress", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          navigate(card.dataset.route);
        }
      });
    });
  },
  pacientes: window.PacientesModule.render,
  turnos: window.TurnosModule.render,
  servicios: window.ServiciosModule.render,
  profesionales: window.ProfesionalesModule.render,
  caja: window.CajaModule.render,
  inventario: window.InventarioModule.render,
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
checkAuth();

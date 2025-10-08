const loginView = document.getElementById("login-view");
const routerView = document.getElementById("router-view");
const routeTitle = document.getElementById("route-title");
const routeContent = document.getElementById("route-content");
const bodyEl = document.body;
const sidebarEl = document.getElementById("sidebar");
const navToggleBtn = document.getElementById("nav-toggle");
const footerYear = document.querySelector('.sidebar__footer small');
if (footerYear) {
  footerYear.textContent = '© ' + new Date().getFullYear() + ' Clínica Estética WAYKI SAC';
}



const routes = {
  dashboard: () => {
    routeTitle.textContent = "Dashboard";
    const shortcuts = [
      { route: "turnos", title: "Turnos", description: "Gestione turnos del día, semana o mes." },
      { route: "pacientes", title: "Pacientes", description: "Altas rápidas y búsquedas." },
      { route: "servicios", title: "Servicios", description: "Catálogo y protocolos." },
      { route: "profesionales", title: "Profesionales", description: "Equipo y especialidades." },
      { route: "caja", title: "Caja", description: "Movimientos, cobros y cierres diarios." },
      { route: "inventario", title: "Inventario", description: "Control de insumos, stock y movimientos." },
      { route: "reportes", title: "Reportes", description: "Análisis de facturación, pacientes e inventario." },
    ];

    routeContent.innerHTML = `
      <div class="dashboard-shortcuts">
        ${shortcuts
          .map(
            (item) => `
              <article class="card card--shortcut" data-route="${item.route}" tabindex="0" role="button" aria-label="Ir a ${item.title}">
                <div class="card__header">
                  <h3 class="card__title">${item.title}</h3>
                  <p class="card__subtitle">${item.description}</p>
                </div>
              </article>
            `
          )
          .join("")}
      </div>
    `;

    routeContent.querySelectorAll(".card--shortcut").forEach((card) => {
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
  routeTitle.textContent = route.charAt(0).toUpperCase() + route.slice(1);
  setActiveNav(route);
  closeSidebar();
  if (typeof fn === "function") {
    fn();
  } else {
    routeContent.innerHTML = "<div class='card'>Ruta no encontrada</div>";
  }
}

// abre la ruta del hash si existe (ej: #/caja?turno=5)
function openFromHash() {
  if (!API.token()) return; // si no hay token, no navegar
  if (location.hash.startsWith("#/")) {
    const route = location.hash.slice(2).split("?")[0];
    if (routes[route]) return navigate(route);
  }
  // por defecto
  navigate("dashboard");
}

// --- auth guard ---
function checkAuth() {
  const has = !!API.token();
  loginView.style.display = has ? "none" : "block";
  routerView.style.display = has ? "block" : "none";
  document.body.classList.toggle('is-authenticated', has);
  if (!has) {
    closeSidebar();
  }
  if (has) openFromHash();
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
    loginMsg.textContent = "Completá email y contraseña.";
    return;
  }
  try {
    const res = await API.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const token = res.access_token || res.token;
    if (!token) throw new Error("La respuesta no trajo token.");
    API.setToken(token);
    loginMsg.textContent = "¡Bienvenido!";
    checkAuth();
  } catch (e) {
    loginMsg.textContent = e.message || "Credenciales inválidas o servidor no disponible.";
  }
}

if (loginForm) loginForm.addEventListener("submit", doLogin);
if (btnLogin)  btnLogin.addEventListener("click", doLogin);

// --- links del sidebar (bloquea si no hay token) ---
document.querySelectorAll("nav a[data-route]").forEach(a => {
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (!API.token()) { checkAuth(); return; }
    const route = a.dataset.route;
    navigate(route);
  });
});

if (navToggleBtn && sidebarEl) {
  navToggleBtn.addEventListener('click', () => {
    const willOpen = !sidebarEl.classList.contains('sidebar--open');
    sidebarEl.classList.toggle('sidebar--open', willOpen);
    bodyEl.classList.toggle('sidebar-open', willOpen);
  });
}


// --- logout ---
document.getElementById("logout").addEventListener("click", (e) => {
  e.preventDefault();
  localStorage.removeItem("token");
  location.hash = "";
  closeSidebar();
  checkAuth();
});

// --- cambiar de ruta si cambia el hash (ej: desde Turnos -> Caja con ?turno=ID) ---
window.addEventListener("hashchange", () => {
  if (!API.token()) return;
  openFromHash();
});

// boot
checkAuth();

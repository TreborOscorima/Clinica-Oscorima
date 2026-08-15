/**
 * AnatomicalViewer — motor de render 3D genérico para TUWAYKILIFE.
 *
 * E1: puente JS↔Reflex validado. E2: motor genérico dental (dientes procedurales
 * por tipo, dos arcadas). E3: odontograma 3D sobre datos reales. E6: escena
 * FACIAL — rostro procedural con marcadores de zona clicables para el mapa
 * estético (evaluaciones + puntos de aplicación).
 *
 * Sin CDN en runtime: Three.js vive vendorizado en ./vendor/. El renderer NUNCA
 * toca la BD: solo emite `anatomy_id` (+ coordenada de click) por el puente y
 * pinta lo que Python le pasa ya calculado (setData). El 2D / los listados siguen
 * siendo la fuente de verdad y el fallback. Geometría procedural (reconocible);
 * E10 la sustituye por GLB realista SIN tocar la lógica clínica.
 */
import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';
// Se importa para validar la cadena del loader (se usará al cargar GLB en E10).
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Numeración FDI (espejo de services/odontograma.ARCADA_*). Orden izq→der en pantalla.
const ARCADA_SUPERIOR = ["18","17","16","15","14","13","12","11",
                         "21","22","23","24","25","26","27","28"];
const ARCADA_INFERIOR = ["48","47","46","45","44","43","42","41",
                         "31","32","33","34","35","36","37","38"];

const COLOR_DEFAULT  = 0xe5e7eb; // gray-200 (pieza sana / sin estado)
const COLOR_SELECTED = 0x0284c7; // sky-600 (selección)
const COLOR_HOVER    = 0x7dd3fc; // sky-300
const COLOR_ROOT     = 0xeceadf; // marfil (raíz)
const COLOR_ZONA     = 0x64748b; // slate-500 (marcador de zona sin actividad)
const COLOR_SKIN     = 0xf0cfb8; // piel estilizada (rostro)

const CAMERAS_DENTAL = {
  frontal:  { pos: [0, 0.2, 9],   target: [0, 0, 0] },
  superior: { pos: [0, 8.5, 0.01], target: [0, 0.6, 0] },  // oclusal maxilar
  inferior: { pos: [0, -8.5, 0.01], target: [0, -0.6, 0] }, // oclusal mandíbula
  lateral:  { pos: [8.5, 0.5, 3.5], target: [0, 0, 0] },
};

const CAMERAS_FACIAL = {
  frontal:   { pos: [0, 0.2, 7.6],  target: [0, 0.05, 0] },
  perfil_izq:{ pos: [-6.8, 0.3, 3], target: [0, 0.05, 0] },
  perfil_der:{ pos: [6.8, 0.3, 3],  target: [0, 0.05, 0] },
  superior:  { pos: [0, 6.5, 4.5],  target: [0, 0.1, 0] },
};

// Tipo de pieza a partir del último dígito FDI (1,2 incisivo · 3 canino · 4,5 premolar · 6-8 molar)
function _tipo(fdi) {
  const d = fdi.charCodeAt(1) - 48;
  if (d <= 2) return "incisivo";
  if (d === 3) return "canino";
  if (d <= 5) return "premolar";
  return "molar";
}

// Dimensiones aproximadas de corona por tipo [ancho, alto, profundidad].
const _DIM = {
  incisivo: [0.42, 0.85, 0.26],
  canino:   [0.44, 0.98, 0.40],
  premolar: [0.55, 0.80, 0.52],
  molar:    [0.76, 0.78, 0.72],
};

// ── Zonas faciales (espejo de services/anatomia._FACIAL). ─────────────────────
// u: -1..1 (izq→der en pantalla), v: -1..1 (mentón→frente). Bilaterales = 2 pts.
const FACE_ZONES = [
  { id: "frente",            pts: [[0, 0.86]] },
  { id: "entrecejo",         pts: [[0, 0.52]] },
  { id: "cola_ceja",         pts: [[-0.6, 0.56], [0.6, 0.56]] },
  { id: "patas_gallo",       pts: [[-0.86, 0.42], [0.86, 0.42]] },
  { id: "surco_lagrimal",    pts: [[-0.38, 0.28], [0.38, 0.28]] },
  { id: "dorso_nasal",       pts: [[0, 0.16]] },
  { id: "pomulo",            pts: [[-0.66, 0.02], [0.66, 0.02]] },
  { id: "surco_nasogeniano", pts: [[-0.4, -0.24], [0.4, -0.24]] },
  { id: "codigo_barras",     pts: [[0, -0.34]] },
  { id: "labios",            pts: [[0, -0.5]] },
  { id: "comisuras",         pts: [[-0.32, -0.5], [0.32, -0.5]] },
  { id: "menton",            pts: [[0, -0.86]] },
  { id: "linea_mandibular",  pts: [[-0.74, -0.62], [0.74, -0.62]] },
  { id: "cuello",            pts: [[0, -1.4]] },  // manual: sobre el cuello
];

const AnatomyViewer = (() => {
  let renderer, scene, camera, controls, raycaster, pointer;
  let container, bridge, nodes = [], decor = [], hovered = null;
  let rafId = null, colores = {}, seleccionado = "";
  let inited = false, sceneType = "dental";
  let cameras = CAMERAS_DENTAL, defaultColor = COLOR_DEFAULT;

  function _webglOK() {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
                (c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch (e) { return false; }
  }

  // ── Construcción dental ─────────────────────────────────────────────────────
  function _crown(tipo, mat) {
    const [w, h, d] = _DIM[tipo];
    let geo;
    if (tipo === "premolar" || tipo === "molar") {
      geo = new THREE.CylinderGeometry(w * 0.52, w * 0.46, h, 10);
    } else {
      geo = new THREE.BoxGeometry(w, h, d);
    }
    return new THREE.Mesh(geo, mat);
  }

  function _root(tipo) {
    const [w, h] = _DIM[tipo];
    const rootLen = h * (tipo === "incisivo" ? 1.05 : 0.9);
    const geo = new THREE.ConeGeometry(w * 0.34, rootLen, 6);
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_ROOT, roughness: 0.7 });
    const m = new THREE.Mesh(geo, mat);
    m.position.y = h / 2 + rootLen / 2 - 0.05;
    return m;
  }

  function _tooth(fdi, arcada) {
    const tipo = _tipo(fdi);
    const mat = new THREE.MeshStandardMaterial({ color: defaultColor, roughness: 0.55, metalness: 0.04 });
    const crown = _crown(tipo, mat);
    const g = new THREE.Group();
    g.add(crown);
    g.add(_root(tipo));
    if (arcada === "inferior") g.rotation.z = Math.PI;
    g.userData = { anatomy_type: "tooth", anatomy_id: fdi, arcada, paint: crown };
    return g;
  }

  function _colocarArcada(fdis, arcada) {
    const n = fdis.length;
    const radiusX = 3.5, radiusZ = 2.7;
    const yArco = arcada === "superior" ? 1.15 : -1.15;
    fdis.forEach((fdi, i) => {
      const t = i / (n - 1);
      const ang = (t - 0.5) * Math.PI * 1.12;
      const g = _tooth(fdi, arcada);
      g.position.set(Math.sin(ang) * radiusX, yArco, Math.cos(ang) * radiusZ);
      g.rotateY(ang);
      nodes.push(g);
      scene.add(g);
    });
  }

  function _buildDental() {
    _colocarArcada(ARCADA_SUPERIOR, "superior");
    _colocarArcada(ARCADA_INFERIOR, "inferior");
  }

  // ── Construcción facial ─────────────────────────────────────────────────────
  // Semiejes del elipsoide del rostro (mesh escalado), centro en cy.
  const _FA = 1.35, _FB = 1.7, _FC = 1.4, _FCY = 0.2;

  function _facePos(u, v) {
    const x = u * _FA * 0.72;
    const y = _FCY + v * _FB * 0.72;
    const rad = 1 - (x / _FA) ** 2 - ((y - _FCY) / _FB) ** 2;
    let z;
    if (rad > 0.05) z = _FC * Math.sqrt(rad) * 1.02 + 0.05;
    else z = 0.62;  // fuera del rostro (cuello) → frente del cilindro
    return [x, y, z];
  }

  function _faceDecor() {
    const skin = new THREE.MeshStandardMaterial({ color: COLOR_SKIN, roughness: 0.9, metalness: 0.0 });
    // Cabeza (elipsoide).
    const head = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 48), skin);
    head.scale.set(_FA, _FB, _FC);
    head.position.y = _FCY;
    scene.add(head); decor.push(head);
    // Cuello.
    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.58, 0.72, 1.2, 24),
      new THREE.MeshStandardMaterial({ color: 0xe4bda6, roughness: 0.9 }),
    );
    neck.position.set(0, _FCY - _FB * 0.86, 0.06);
    scene.add(neck); decor.push(neck);
    // Hombros (sugeridos).
    const shoulders = new THREE.Mesh(
      new THREE.CylinderGeometry(1.9, 2.2, 0.7, 28),
      new THREE.MeshStandardMaterial({ color: 0xdfe3ea, roughness: 0.95 }),
    );
    shoulders.position.set(0, _FCY - _FB * 1.5, 0.0);
    scene.add(shoulders); decor.push(shoulders);
  }

  function _zoneMarker(id, u, v) {
    const [x, y, z] = _facePos(u, v);
    const mat = new THREE.MeshStandardMaterial({
      color: defaultColor, roughness: 0.4, metalness: 0.1,
      emissive: 0x000000,
    });
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.13, 18, 18), mat);
    m.position.set(x, y, z);
    const g = new THREE.Group();
    g.add(m);
    g.userData = { anatomy_type: "zone", anatomy_id: id, paint: m };
    return g;
  }

  function _buildFacial() {
    _faceDecor();
    for (const z of FACE_ZONES) {
      for (const [u, v] of z.pts) {
        const g = _zoneMarker(z.id, u, v);
        nodes.push(g);
        scene.add(g);
      }
    }
  }

  // ── Pintado / selección (común) ─────────────────────────────────────────────
  function _baseColor(id) {
    if (id === seleccionado) return COLOR_SELECTED;
    if (colores[id] != null) return new THREE.Color(colores[id]).getHex();
    return defaultColor;
  }

  function _repaint() {
    for (const g of nodes) {
      const id = g.userData.anatomy_id;
      const hex = g === hovered ? COLOR_HOVER : _baseColor(id);
      g.userData.paint.material.color.setHex(hex);
    }
  }

  function _nodeFromHit(obj) {
    let o = obj;
    while (o && !(o.userData && o.userData.anatomy_id)) o = o.parent;
    return o;
  }

  function _pick(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(nodes, true)[0];
    return hit ? _nodeFromHit(hit.object) : null;
  }

  function _onPointerMove(ev) {
    const next = _pick(ev);
    if (next !== hovered) {
      hovered = next;
      renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
      _repaint();
    }
  }

  function _onClick(ev) {
    const g = _pick(ev);
    if (!g || !bridge) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const cx = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    const cy = Math.max(0, Math.min(1, (ev.clientY - rect.top) / rect.height));
    const payload = JSON.stringify({
      anatomy_id: g.userData.anatomy_id,
      coord_x: Math.round(cx * 1e4) / 1e4,
      coord_y: Math.round(cy * 1e4) / 1e4,
    });
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value").set;
    setter.call(bridge, payload);
    bridge.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function _animate() {
    rafId = requestAnimationFrame(_animate);
    controls.update();
    renderer.render(scene, camera);
  }

  function _resize() {
    if (!container || !renderer) return;
    const w = container.clientWidth || 600, h = container.clientHeight || 440;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function setCamera(name) {
    const c = cameras[name] || cameras.frontal;
    if (!camera || !controls) return;
    camera.position.set(c.pos[0], c.pos[1], c.pos[2]);
    controls.target.set(c.target[0], c.target[1], c.target[2]);
    controls.update();
  }

  function init(canvasId, bridgeId, type) {
    container = document.getElementById(canvasId);
    bridge = document.getElementById(bridgeId);
    if (!container) return false;
    const nextType = type || "dental";
    if (inited && renderer && container.contains(renderer.domElement) && nextType === sceneType) return true;
    dispose();
    sceneType = nextType;
    cameras = sceneType === "facial" ? CAMERAS_FACIAL : CAMERAS_DENTAL;
    defaultColor = sceneType === "facial" ? COLOR_ZONA : COLOR_DEFAULT;

    if (!_webglOK()) {
      container.innerHTML =
        '<div style="padding:1rem;color:#6b7280;font-size:.875rem">' +
        'Tu navegador no soporta WebGL; usá la vista de listado.</div>';
      return false;
    }

    const w = container.clientWidth || 600, h = container.clientHeight || 440;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf9fafb);

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h, false);
    container.appendChild(renderer.domElement);
    renderer.domElement.style.cursor = "grab";
    renderer.domElement.style.display = "block";

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(3, 6, 5); scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.35);
    fill.position.set(-4, -3, 4); scene.add(fill);

    nodes = []; decor = [];
    if (sceneType === "facial") _buildFacial();
    else _buildDental();

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 4;
    controls.maxDistance = 20;
    setCamera("frontal");

    raycaster = new THREE.Raycaster();
    pointer = new THREE.Vector2();

    renderer.domElement.addEventListener("pointermove", _onPointerMove);
    renderer.domElement.addEventListener("click", _onClick);
    window.addEventListener("resize", _resize);

    inited = true;
    _repaint();
    _animate();
    return true;
  }

  /**
   * setData({colores: {"16":"#ef4444", ...}, seleccionado: "16"})
   * colores: hex por anatomy_id (estado clínico ya calculado en Python).
   */
  function setData(payload) {
    if (typeof payload === "string") {
      try { payload = JSON.parse(payload); } catch (e) { return; }
    }
    payload = payload || {};
    colores = payload.colores || {};
    seleccionado = payload.seleccionado || "";
    if (inited) _repaint();
  }

  // Introspección para tests/E2E: color hex actual (base, sin hover) por anatomy_id.
  function getColors() {
    const out = {};
    for (const g of nodes) {
      out[g.userData.anatomy_id] = "#" + _baseColor(g.userData.anatomy_id)
        .toString(16).padStart(6, "0");
    }
    return out;
  }

  function dispose() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    if (renderer) {
      renderer.domElement.removeEventListener("pointermove", _onPointerMove);
      renderer.domElement.removeEventListener("click", _onClick);
      window.removeEventListener("resize", _resize);
      renderer.dispose();
      if (renderer.domElement.parentNode)
        renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
    for (const g of nodes) {
      g.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });
    }
    for (const d of decor) {
      d.geometry?.dispose(); d.material?.dispose();
    }
    nodes = []; decor = []; hovered = null; inited = false;
    renderer = scene = camera = controls = null;
  }

  return { init, setData, setCamera, getColors, dispose, _webglOK };
})();

window.AnatomyViewer = AnatomyViewer;

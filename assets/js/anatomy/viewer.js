/**
 * AnatomicalViewer — motor de render 3D genérico para TUWAYKILIFE.
 *
 * E1: puente JS↔Reflex validado. E2: motor genérico — dientes procedurales por
 * tipo (incisivo/canino/premolar/molar), dos arcadas en herradura, cámaras
 * predefinidas (frontal/oclusal/lateral), hover+highlight, raycast de selección.
 *
 * Sin CDN en runtime: Three.js vive vendorizado en ./vendor/. El renderer NUNCA
 * toca la BD: solo emite `anatomy_id` (por el puente) y pinta lo que Python le
 * pasa ya calculado (setData). El 2D sigue siendo la fuente de verdad y el
 * fallback. La geometría es procedural (reconocible); E10 la sustituye por GLB
 * realista SIN tocar la lógica clínica (misma API + userData por anatomy_id).
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

const CAMERAS = {
  frontal:  { pos: [0, 0.2, 9],   target: [0, 0, 0] },
  superior: { pos: [0, 8.5, 0.01], target: [0, 0.6, 0] },  // oclusal maxilar
  inferior: { pos: [0, -8.5, 0.01], target: [0, -0.6, 0] }, // oclusal mandíbula
  lateral:  { pos: [8.5, 0.5, 3.5], target: [0, 0, 0] },
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

const AnatomyViewer = (() => {
  let renderer, scene, camera, controls, raycaster, pointer;
  let container, bridge, teeth = [], hovered = null;
  let rafId = null, colores = {}, seleccionado = "";
  let inited = false;

  function _webglOK() {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
                (c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch (e) { return false; }
  }

  function _crown(tipo, mat) {
    const [w, h, d] = _DIM[tipo];
    let geo;
    if (tipo === "premolar" || tipo === "molar") {
      // Corona redondeada (cilindro ligeramente cónico) → lee como muela.
      geo = new THREE.CylinderGeometry(w * 0.52, w * 0.46, h, 10);
    } else {
      geo = new THREE.BoxGeometry(w, h, d);
    }
    const m = new THREE.Mesh(geo, mat);
    return m;
  }

  function _root(tipo) {
    const [w, h] = _DIM[tipo];
    const rootLen = h * (tipo === "incisivo" ? 1.05 : 0.9);
    const geo = new THREE.ConeGeometry(w * 0.34, rootLen, 6);
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_ROOT, roughness: 0.7 });
    const m = new THREE.Mesh(geo, mat);
    m.position.y = h / 2 + rootLen / 2 - 0.05;   // raíz apoyada sobre la corona, apex hacia +y
    return m;
  }

  function _tooth(fdi, arcada) {
    const tipo = _tipo(fdi);
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_DEFAULT, roughness: 0.55, metalness: 0.04 });
    const crown = _crown(tipo, mat);
    const g = new THREE.Group();
    g.add(crown);
    g.add(_root(tipo));
    // En local: corona centrada, raíz hacia +y. Para la mandíbula, invertimos.
    if (arcada === "inferior") g.rotation.z = Math.PI;
    g.userData = { anatomy_type: "tooth", anatomy_id: fdi, arcada, crown };
    return g;
  }

  function _colocarArcada(fdis, arcada) {
    const n = fdis.length;
    const radiusX = 3.5, radiusZ = 2.7;
    const yArco = arcada === "superior" ? 1.15 : -1.15;
    fdis.forEach((fdi, i) => {
      const t = i / (n - 1);                 // 0..1 izq→der
      const ang = (t - 0.5) * Math.PI * 1.12; // herradura
      const g = _tooth(fdi, arcada);
      g.position.set(Math.sin(ang) * radiusX, yArco, Math.cos(ang) * radiusZ);
      g.rotateY(ang);                          // orienta la pieza radialmente
      teeth.push(g);
      scene.add(g);
    });
  }

  function _baseColor(id) {
    if (id === seleccionado) return COLOR_SELECTED;
    if (colores[id] != null) return new THREE.Color(colores[id]).getHex();
    return COLOR_DEFAULT;
  }

  function _repaint() {
    for (const g of teeth) {
      const id = g.userData.anatomy_id;
      const hex = g === hovered ? COLOR_HOVER : _baseColor(id);
      g.userData.crown.material.color.setHex(hex);
    }
  }

  function _toothFromHit(obj) {
    let o = obj;
    while (o && !(o.userData && o.userData.anatomy_id)) o = o.parent;
    return o;
  }

  function _pick(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(teeth, true)[0];
    return hit ? _toothFromHit(hit.object) : null;
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
    const payload = JSON.stringify({ anatomy_id: g.userData.anatomy_id });
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
    const c = CAMERAS[name] || CAMERAS.frontal;
    if (!camera || !controls) return;
    camera.position.set(c.pos[0], c.pos[1], c.pos[2]);
    controls.target.set(c.target[0], c.target[1], c.target[2]);
    controls.update();
  }

  function init(canvasId, bridgeId) {
    container = document.getElementById(canvasId);
    bridge = document.getElementById(bridgeId);
    if (!container) return false;
    if (inited && renderer && container.contains(renderer.domElement)) return true;
    dispose();

    if (!_webglOK()) {
      container.innerHTML =
        '<div style="padding:1rem;color:#6b7280;font-size:.875rem">' +
        'Tu navegador no soporta WebGL; usá la vista 2D.</div>';
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

    teeth = [];
    _colocarArcada(ARCADA_SUPERIOR, "superior");
    _colocarArcada(ARCADA_INFERIOR, "inferior");

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
    for (const g of teeth) {
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
    for (const g of teeth) {
      g.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });
    }
    teeth = []; hovered = null; inited = false;
    renderer = scene = camera = controls = null;
  }

  return { init, setData, setCamera, getColors, dispose, _webglOK };
})();

window.AnatomyViewer = AnatomyViewer;

/**
 * AnatomicalViewer — motor de render 3D genérico para TUWAYKILIFE.
 *
 * Etapa E1 (prototipo del puente JS↔Reflex): escena procedural (dientes = cajas)
 * con OrbitControls (rotar/zoom/pan) y raycast de selección. Al hacer click sobre
 * una malla, escribe la selección en un <input> oculto ("puente") y dispara su
 * evento `input`, que Reflex captura como on_change → handler de Python. Python
 * responde con AnatomyViewer.setData(...) para repintar colores/estado.
 *
 * Sin CDN en runtime: Three.js vive vendorizado en ./vendor/. El renderer NUNCA
 * toca la BD; solo emite `anatomy_id` y pinta lo que recibe ya calculado.
 */
import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';
// Se importa para validar que el loader resuelve (se usará en etapas con GLB).
import { GLTFLoader } from './vendor/GLTFLoader.js';

const COLOR_DEFAULT   = 0xe5e7eb; // gray-200 (pieza sin estado)
const COLOR_SELECTED  = 0x0284c7; // sky-600 (selección)
const COLOR_HOVER     = 0x7dd3fc; // sky-300

// Piezas de demo para E1: cuadrante superior derecho + izquierdo (FDI), como el
// odontograma 2D. En E3 esto se sustituye por datos reales / GLB con userData.
const DEMO_PIEZAS = ["18","17","16","15","14","13","12","11",
                     "21","22","23","24","25","26","27","28"];

const AnatomyViewer = (() => {
  let renderer, scene, camera, controls, raycaster, pointer;
  let container, bridge, meshes = [], hovered = null;
  let rafId = null, colores = {}, seleccionado = "";
  let inited = false;

  function _webglOK() {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
                (c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch (e) { return false; }
  }

  function _tooth(anatomyId, index, total) {
    // Caja simple; arco leve para que parezca arcada.
    const geo = new THREE.BoxGeometry(0.6, 0.9, 0.5);
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_DEFAULT, roughness: 0.6, metalness: 0.05 });
    const mesh = new THREE.Mesh(geo, mat);
    const spread = total - 1;
    const t = index / spread;               // 0..1
    mesh.position.x = (t - 0.5) * spread * 0.75;
    mesh.position.z = -Math.sin(t * Math.PI) * 1.6; // arco
    mesh.userData = { anatomy_type: "tooth", anatomy_id: anatomyId };
    return mesh;
  }

  function _baseColor(id) {
    if (id === seleccionado) return COLOR_SELECTED;
    if (colores[id] != null) return new THREE.Color(colores[id]).getHex();
    return COLOR_DEFAULT;
  }

  function _repaint() {
    for (const m of meshes) {
      const id = m.userData.anatomy_id;
      m.material.color.setHex(m === hovered ? COLOR_HOVER : _baseColor(id));
    }
  }

  function _onPointerMove(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    const next = hit ? hit.object : null;
    if (next !== hovered) {
      hovered = next;
      renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
      _repaint();
    }
  }

  function _onClick(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    if (!hit || !bridge) return;
    const payload = JSON.stringify({ anatomy_id: hit.object.userData.anatomy_id });
    // Puente JS→Reflex: setter nativo + evento input (Reflex lo capta como on_change).
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
    const w = container.clientWidth || 600, h = container.clientHeight || 420;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function init(canvasId, bridgeId) {
    container = document.getElementById(canvasId);
    bridge = document.getElementById(bridgeId);
    if (!container) return false;
    if (inited && renderer && container.contains(renderer.domElement)) return true;
    dispose(); // limpieza si se re-montó

    if (!_webglOK()) {
      container.innerHTML =
        '<div style="padding:1rem;color:#6b7280;font-size:.875rem">' +
        'Tu navegador no soporta WebGL; usá la vista 2D.</div>';
      return false;
    }

    const w = container.clientWidth || 600, h = container.clientHeight || 420;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf9fafb); // fondo del producto

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    camera.position.set(0, 1.5, 9);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h, false);
    container.appendChild(renderer.domElement);
    renderer.domElement.style.cursor = "grab";
    renderer.domElement.style.display = "block";
    renderer.domElement.style.borderRadius = "0.75rem";

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(3, 5, 4);
    scene.add(key);

    meshes = DEMO_PIEZAS.map((id, i) => _tooth(id, i, DEMO_PIEZAS.length));
    meshes.forEach((m) => scene.add(m));

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 0);

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
   * setData({colores: {"16":"#dc2626", ...}, seleccionado: "16"})
   * colores: hex por anatomy_id (estado clínico ya calculado en Python).
   */
  function setData(payload) {
    if (typeof payload === "string") {
      try { payload = JSON.parse(payload); } catch (e) { return; }
    }
    payload = payload || {};
    colores = payload.colores || {};
    seleccionado = payload.seleccionado || "";
    _repaint();
  }

  // Introspección para tests/E2E: color hex actual (base, sin hover) por anatomy_id.
  function getColors() {
    const out = {};
    for (const m of meshes) {
      out[m.userData.anatomy_id] = "#" + _baseColor(m.userData.anatomy_id)
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
    for (const m of meshes) {
      m.geometry?.dispose();
      m.material?.dispose();
    }
    meshes = []; hovered = null; inited = false;
    renderer = scene = camera = controls = null;
  }

  return { init, setData, dispose, getColors, _webglOK };
})();

window.AnatomyViewer = AnatomyViewer;

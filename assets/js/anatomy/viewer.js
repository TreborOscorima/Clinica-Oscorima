/**
 * AnatomicalViewer — motor de render 3D dental para TUWAYKILIFE (odontograma).
 *
 * E1: puente JS↔Reflex validado. E2: motor dental (dientes procedurales por tipo,
 * dos arcadas). E3: odontograma 3D sobre datos reales, con GLB realista de las
 * arcadas y marcadores FDI clicables sobre la superficie.
 *
 * Sin CDN en runtime: Three.js vive vendorizado en ./vendor/. El renderer NUNCA
 * toca la BD: solo emite `anatomy_id` (+ coordenada de click) por el puente y
 * pinta lo que Python le pasa ya calculado (setData). El 2D / los listados siguen
 * siendo la fuente de verdad y el fallback.
 */
import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';
import { mergeGeometries } from './vendor/BufferGeometryUtils.js';
// Carga los GLB realistas de las arcadas (arcada_superior/arcada_inferior).
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Numeración FDI (espejo de services/odontograma.ARCADA_*). Orden izq→der en pantalla.
const ARCADA_SUPERIOR = ["18","17","16","15","14","13","12","11",
                         "21","22","23","24","25","26","27","28"];
const ARCADA_INFERIOR = ["48","47","46","45","44","43","42","41",
                         "31","32","33","34","35","36","37","38"];

const COLOR_DEFAULT  = 0xf3f1ea; // esmalte (pieza sana / sin estado)
const COLOR_SELECTED = 0x0284c7; // sky-600 (selección)
const COLOR_HOVER    = 0x7dd3fc; // sky-300
const COLOR_ROOT     = 0xe7e2d2; // marfil (raíz)
const COLOR_GUM      = 0xd08a86; // encía (gingiva)
const COLOR_ZONA     = 0x64748b; // slate-500 (marcador dental sin actividad)

const CAMERAS_DENTAL = {
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
  let container, bridge, nodes = [], decor = [], hovered = null;
  let rafId = null, colores = {}, seleccionado = "";
  let inited = false, sceneType = "dental";
  let cameras = CAMERAS_DENTAL, defaultColor = COLOR_DEFAULT;
  let gltfLoader = null, modelRoot = null, modelUrl = "";
  let needsRender = true, resizeObs = null;

  function _webglOK() {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
                (c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch (e) { return false; }
  }

  // ── Construcción dental ─────────────────────────────────────────────────────
  const _ARCO = { radiusX: 3.5, radiusZ: 2.7, ySup: 1.15, yInf: -1.15, span: Math.PI * 1.12 };

  // Corona bulbosa (elipsoide) + cúspides, fusionada en UNA geometría para que
  // siga siendo un solo mesh pintable por estado clínico.
  function _crownGeo(tipo) {
    const [w, h, d] = _DIM[tipo];
    const parts = [];
    const body = new THREE.SphereGeometry(0.5, 18, 16);
    body.scale(w, h, d);
    parts.push(body);
    const topY = h * 0.42;
    if (tipo === "canino") {
      // Cúspide puntiaguda en el borde incisal (abajo).
      const tip = new THREE.ConeGeometry(w * 0.34, h * 0.5, 12);
      tip.rotateX(Math.PI);
      tip.translate(0, -h * 0.4, d * 0.06);
      parts.push(tip);
    } else if (tipo === "premolar" || tipo === "molar") {
      const cusps = tipo === "premolar"
        ? [[-w * 0.24, 0], [w * 0.24, 0]]
        : [[-w * 0.26, -d * 0.24], [w * 0.26, -d * 0.24],
           [-w * 0.26, d * 0.24], [w * 0.26, d * 0.24]];
      for (const [cx, cz] of cusps) {
        const cusp = new THREE.SphereGeometry(w * 0.2, 10, 8);
        cusp.scale(1, 0.72, 1);
        cusp.translate(cx, topY * 0.9, cz);
        parts.push(cusp);
      }
    }
    const geo = mergeGeometries(parts, false);
    parts.forEach((p) => p.dispose());
    geo.computeVertexNormals();
    return geo;
  }

  function _root(tipo) {
    const [w, h] = _DIM[tipo];
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_ROOT, roughness: 0.85 });
    const g = new THREE.Group();
    const rootLen = h * (tipo === "incisivo" ? 1.15 : tipo === "molar" ? 0.85 : 1.0);
    const mk = (r, offx) => {
      const m = new THREE.Mesh(new THREE.ConeGeometry(r, rootLen, 8), mat);
      m.position.set(offx, h / 2 + rootLen / 2 - 0.1, 0);
      return m;
    };
    if (tipo === "molar") {          // dos raíces
      g.add(mk(w * 0.19, -w * 0.24));
      g.add(mk(w * 0.19, w * 0.24));
    } else {                          // raíz única cónica
      g.add(mk(w * 0.32, 0));
    }
    return g;
  }

  function _tooth(fdi, arcada) {
    const tipo = _tipo(fdi);
    const mat = new THREE.MeshStandardMaterial({ color: defaultColor, roughness: 0.32, metalness: 0.02 });
    const crown = new THREE.Mesh(_crownGeo(tipo), mat);
    const g = new THREE.Group();
    g.add(crown);
    g.add(_root(tipo));
    if (arcada === "inferior") g.rotation.z = Math.PI;
    g.userData = { anatomy_type: "tooth", anatomy_id: fdi, arcada, paint: crown };
    return g;
  }

  function _colocarArcada(fdis, arcada) {
    const n = fdis.length;
    const { radiusX, radiusZ, span } = _ARCO;
    const yArco = arcada === "superior" ? _ARCO.ySup : _ARCO.yInf;
    fdis.forEach((fdi, i) => {
      const t = i / (n - 1);
      const ang = (t - 0.5) * span;
      const g = _tooth(fdi, arcada);
      g.position.set(Math.sin(ang) * radiusX, yArco, Math.cos(ang) * radiusZ);
      g.rotateY(ang);
      nodes.push(g);
      scene.add(g);
    });
  }

  // Encía: tubo rosado siguiendo la curva de la arcada, sobre la línea gingival.
  function _gumArc(arcada) {
    const { radiusX, radiusZ, span } = _ARCO;
    const yArco = arcada === "superior" ? _ARCO.ySup : _ARCO.yInf;
    const pts = [];
    for (let i = 0; i <= 24; i++) {
      const ang = (i / 24 - 0.5) * span;
      pts.push(new THREE.Vector3(Math.sin(ang) * radiusX, yArco, Math.cos(ang) * radiusZ));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 48, 0.34, 14, false);
    const mat = new THREE.MeshStandardMaterial({ color: COLOR_GUM, roughness: 0.85 });
    const m = new THREE.Mesh(geo, mat);
    m.position.y = arcada === "superior" ? 0.47 : -0.47; // sube/baja a la línea gingival
    return m;
  }

  // Entorno equirectangular procedural (studio) → PMREM para reflejos del esmalte.
  function _studioEnv() {
    const c = document.createElement("canvas"); c.width = 512; c.height = 256;
    const g = c.getContext("2d");
    const grd = g.createLinearGradient(0, 0, 0, 256);
    grd.addColorStop(0.00, "#ffffff");
    grd.addColorStop(0.45, "#e6ebf3");
    grd.addColorStop(0.55, "#cfd6e0");
    grd.addColorStop(1.00, "#9aa2ad");
    g.fillStyle = grd; g.fillRect(0, 0, 512, 256);
    for (const xr of [[150, 60], [380, 50]]) {
      const rg = g.createRadialGradient(xr[0], 70, 4, xr[0], 70, xr[1]);
      rg.addColorStop(0, "rgba(255,255,255,0.95)");
      rg.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = rg; g.fillRect(0, 0, 512, 256);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.mapping = THREE.EquirectangularReflectionMapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    const pmrem = new THREE.PMREMGenerator(renderer);
    pmrem.compileEquirectangularShader();
    const rt = pmrem.fromEquirectangular(tex);
    tex.dispose(); pmrem.dispose();
    return rt.texture;
  }

  // Tinte natural por vértices: incisal (arriba) más blanco, cervical (abajo) más cálido.
  function _tintGeo(geo) {
    const pos = geo.attributes.position; const N = pos.count;
    let ymn = Infinity, ymx = -Infinity;
    for (let i = 0; i < N; i++) { const y = pos.getY(i); if (y < ymn) ymn = y; if (y > ymx) ymx = y; }
    const top = new THREE.Color(0xfdfbf4), bot = new THREE.Color(0xe6d3a8), col = new THREE.Color();
    const arr = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const t = (pos.getY(i) - ymn) / ((ymx - ymn) || 1);
      col.copy(bot).lerp(top, Math.pow(t, 0.7));
      arr[i * 3] = col.r; arr[i * 3 + 1] = col.g; arr[i * 3 + 2] = col.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(arr, 3));
  }

  function _buildDentalProcedural() {
    _colocarArcada(ARCADA_SUPERIOR, "superior");
    _colocarArcada(ARCADA_INFERIOR, "inferior");
    for (const arc of ["superior", "inferior"]) {
      const gum = _gumArc(arc);
      scene.add(gum); decor.push(gum);
    }
    _repaint();
  }

  function _buildDental() {
    let spec = null;
    if (modelUrl) { try { spec = JSON.parse(modelUrl); } catch (e) { spec = null; } }
    if (spec && spec.inferior && spec.superior) _loadDentalModels(spec);
    else _buildDentalProcedural();
  }

  // ── Pipeline GLB dental: ensambla arcada inferior + superior como una boca ────
  // Cada GLB ya viene canónico (dientes +Y, incisivos +Z, centrado). La inferior
  // queda con coronas hacia arriba; la superior se rota 180° para morder hacia
  // abajo. Material de esmalte uniforme (estilo modelo de estudio dental).
  function _loadDentalModels(spec) {
    if (!gltfLoader) gltfLoader = new GLTFLoader();
    modelRoot = new THREE.Group();
    scene.add(modelRoot);
    const arches = {};
    let pending = 2;
    const GAP = 0.5;  // separación de mordida (unidades del modelo, antes de escalar)

    function assemble() {
      const L = arches.inferior, U = arches.superior;
      if (L) {
        L.updateMatrixWorld(true);
        const bL = new THREE.Box3().setFromObject(L);
        L.position.y -= bL.max.y + GAP * 0.5;   // coronas justo bajo el plano oclusal
        modelRoot.add(L);
      }
      if (U) {
        U.rotation.z = Math.PI;                  // muerde hacia abajo
        U.updateMatrixWorld(true);
        const bU = new THREE.Box3().setFromObject(U);
        U.position.y -= bU.min.y - GAP * 0.5;    // coronas justo sobre el plano oclusal
        modelRoot.add(U);
      }
      _fitModel(modelRoot, 4.8, 0);              // encuadra la boca completa
      _placeDentalMarkers(L, U);                 // overlay clicable 32 FDI (raycast)
    }

    function loadOne(url, key) {
      gltfLoader.load(
        url,
        (gltf) => {
          const root = gltf.scene;
          // Esmalte PBR: baja rugosidad + clearcoat = brillo húmedo; tinte por vértices.
          const enamel = new THREE.MeshPhysicalMaterial({
            color: 0xffffff, vertexColors: true,
            roughness: 0.30, metalness: 0.0,
            clearcoat: 0.65, clearcoatRoughness: 0.28,
            sheen: 0.25, sheenColor: new THREE.Color(0xfff4e0),
            envMapIntensity: 1.0,
          });
          root.traverse((o) => {
            if (o.isMesh) {
              o.geometry.computeVertexNormals();
              _tintGeo(o.geometry);
              o.material = enamel;
            }
          });
          arches[key] = root;
          if (--pending === 0) assemble();
        },
        undefined,
        () => { if (--pending === 0) assemble(); },
      );
    }
    loadOne(spec.inferior, "inferior");
    loadOne(spec.superior, "superior");
  }

  // Escala un GLB a la altura objetivo y lo centra (usado por el ensamblado dental).
  function _fitModel(obj, targetHeight, centerY) {
    let box = new THREE.Box3().setFromObject(obj);
    const size = box.getSize(new THREE.Vector3());
    obj.scale.setScalar(targetHeight / (size.y || 1));
    box = new THREE.Box3().setFromObject(obj);
    const c = box.getCenter(new THREE.Vector3());
    obj.position.sub(c);
    obj.position.y += centerY;
    return new THREE.Box3().setFromObject(obj);
  }

  // Marcador dental clicable (esfera pequeña que se apoya sobre la corona).
  function _toothMarkerAt(id, pos, radius) {
    const mat = new THREE.MeshStandardMaterial({
      color: COLOR_ZONA, roughness: 0.35, metalness: 0.1, emissive: 0x0b0b0b,
    });
    const m = new THREE.Mesh(new THREE.SphereGeometry(radius, 16, 12), mat);
    m.position.copy(pos);
    const g = new THREE.Group();
    g.add(m);
    g.userData = { anatomy_type: "tooth", anatomy_id: id, paint: m, baseHex: COLOR_ZONA, isMarker: true };
    return g;
  }

  // Puntos (world) de la cresta oclusal/incisal de una arcada (banda de coronas).
  function _archRidgePoints(archGroup, isLower) {
    archGroup.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(archGroup);
    const size = box.getSize(new THREE.Vector3());
    const yThresh = isLower ? box.max.y - size.y * 0.28 : box.min.y + size.y * 0.28;
    const pts = [];
    const v = new THREE.Vector3();
    archGroup.traverse((o) => {
      if (!o.isMesh || !o.geometry || !o.geometry.attributes.position) return;
      const pos = o.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        v.set(pos.getX(i), pos.getY(i), pos.getZ(i)).applyMatrix4(o.matrixWorld);
        if (isLower ? v.y >= yThresh : v.y <= yThresh) pts.push(v.clone());
      }
    });
    return { pts, box, size };
  }

  // Coloca N marcadores FDI sobre una arcada: reparte por el arco (evita la
  // abertura posterior), ajusta Y por raycast a la corona, y asigna FDI por X
  // (izq→der en pantalla, igual que el array).
  function _placeArchMarkers(archGroup, fdiArr, isLower) {
    const { pts, box, size } = _archRidgePoints(archGroup, isLower);
    if (pts.length < fdiArr.length) return;
    let cx = 0, cz = 0, meanR = 0;
    for (const p of pts) { cx += p.x; cz += p.z; }
    cx /= pts.length; cz /= pts.length;
    const ang = new Array(pts.length);
    for (let i = 0; i < pts.length; i++) {
      ang[i] = Math.atan2(pts[i].z - cz, pts[i].x - cx);
      meanR += Math.hypot(pts[i].x - cx, pts[i].z - cz);
    }
    meanR /= pts.length;
    // Hueco angular mayor = abertura posterior de la herradura.
    const sorted = ang.slice().sort((a, b) => a - b);
    let gap = (sorted[0] + 2 * Math.PI) - sorted[sorted.length - 1];
    let a0 = sorted[0];
    for (let i = 1; i < sorted.length; i++) {
      const d = sorted[i] - sorted[i - 1];
      if (d > gap) { gap = d; a0 = sorted[i]; }
    }
    const span = 2 * Math.PI - gap;                 // arco ocupado por los dientes
    const N = fdiArr.length;
    const rc = new THREE.Raycaster();
    const radius = Math.max(size.x, size.z) * 0.026;
    // Y a media corona (banda cerca del borde de mordida, no la encía).
    const crownMidY = isLower ? box.max.y - size.y * 0.30 : box.min.y + size.y * 0.30;
    const found = [];
    for (let k = 0; k < N; k++) {
      const target = a0 + span * (k + 0.5) / N;
      const ct = Math.cos(target), st = Math.sin(target);
      // Raycast radial: desde fuera de la arcada hacia el centro → cara vestibular.
      rc.set(new THREE.Vector3(cx + meanR * 2.4 * ct, crownMidY, cz + meanR * 2.4 * st),
             new THREE.Vector3(-ct, 0, -st).normalize());
      const hit = rc.intersectObject(archGroup, true)[0];
      let p;
      if (hit) { p = hit.point.clone(); p.x += ct * radius * 0.8; p.z += st * radius * 0.8; }
      else { p = new THREE.Vector3(cx + meanR * ct, crownMidY, cz + meanR * st); }
      found.push(p);
    }
    found.sort((a, b) => a.x - b.x);               // izq→der en pantalla
    for (let i = 0; i < found.length && i < N; i++) {
      const g = _toothMarkerAt(fdiArr[i], found[i], radius);
      nodes.push(g);
      scene.add(g);
    }
  }

  function _placeDentalMarkers(L, U) {
    if (modelRoot) modelRoot.updateMatrixWorld(true);
    if (L) _placeArchMarkers(L, ARCADA_INFERIOR, true);
    if (U) _placeArchMarkers(U, ARCADA_SUPERIOR, false);
    _repaint();
  }

  // ── Pintado / selección (común) ─────────────────────────────────────────────
  function _nodeBaseHex(g) {
    const id = g.userData.anatomy_id;
    if (id === seleccionado) return COLOR_SELECTED;
    if (colores[id] != null) return new THREE.Color(colores[id]).getHex();
    // baseHex: color visible propio del nodo (marcadores dentales) cuando no hay
    // estado; si no lo define, usa el defaultColor de la escena (zonas faciales).
    return g.userData.baseHex != null ? g.userData.baseHex : defaultColor;
  }

  function _repaint() {
    for (const g of nodes) {
      if (g.userData.isMarker) {
        // Marcador de zona: oculto para dejar el modelo LIMPIO; se muestra solo
        // si la zona tiene estado (histórico), está seleccionada, o el cursor
        // está encima (feedback de "vas a tocar acá").
        const id = g.userData.anatomy_id;
        g.visible = colores[id] != null || id === seleccionado || g === hovered;
        if (g.visible) {
          const hex = g === hovered ? COLOR_HOVER : _nodeBaseHex(g);
          g.userData.paint.material.color.setHex(hex);
        }
      } else {
        // Superficie (diente procedural): siempre visible, coloreada por estado.
        g.userData.paint.material.color.setHex(g === hovered ? COLOR_HOVER : _nodeBaseHex(g));
      }
    }
    needsRender = true;
  }

  function _nodeFromHit(obj) {
    let o = obj;
    while (o && !(o.userData && o.userData.anatomy_id)) o = o.parent;
    return o;
  }

  // Objetos "superficie" contra los que se hace click: el modelo GLB real (las
  // arcadas) y los nodos que SON superficie (dientes procedurales). Los
  // marcadores (isMarker) no se clickean directo: son anclas.
  function _surfaceTargets() {
    const t = [];
    if (modelRoot) t.push(modelRoot);
    for (const d of decor) t.push(d);
    for (const g of nodes) if (!g.userData.isMarker) t.push(g);
    return t;
  }

  const _wp = new THREE.Vector3();
  function _anchorWorld(g) { return g.userData.paint.getWorldPosition(_wp); }

  // Click sobre la SUPERFICIE (no sobre bolitas): raycast al modelo y se resuelve
  // a la pieza cuyo ancla queda más cerca del punto tocado. Así el modelo se ve
  // limpio (sin marcadores flotantes) y al tocar un diente se selecciona su pieza.
  function _pick(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(_surfaceTargets(), true)[0];
    if (!hit) return null;
    // Diente procedural: el hit YA es el nodo-superficie.
    const direct = _nodeFromHit(hit.object);
    if (direct && !direct.userData.isMarker) return direct;
    // GLB: el marcador de zona cuyo ancla está más cerca del punto tocado.
    let best = null, bestD = Infinity;
    for (const g of nodes) {
      const d = _anchorWorld(g).distanceToSquared(hit.point);
      if (d < bestD) { bestD = d; best = g; }
    }
    return best;
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

  // Render bajo demanda: el RAF sigue vivo (controls.update() es barato) pero solo
  // repintamos la GPU cuando algo cambió — la cámara se movió (update() reporta true
  // durante el arrastre y todo el settle del damping) o marcamos needsRender (hover,
  // datos, resize, cambio de cámara). Con el cuerpo de cientos de miles de triángulos
  // esto lleva el consumo de GPU a ~0 mientras la escena está quieta.
  function _animate() {
    rafId = requestAnimationFrame(_animate);
    const moved = controls.update();
    if (needsRender || moved) {
      renderer.render(scene, camera);
      needsRender = false;
    }
  }

  function _resize() {
    if (!container || !renderer) return;
    const w = container.clientWidth || 600, h = container.clientHeight || 440;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    needsRender = true;
  }

  // Pausa total del loop cuando la pestaña no está visible (ahorra GPU/batería en
  // tablets y laptops); al volver a foco, reanuda si la escena sigue montada.
  function _onVisibility() {
    if (document.hidden) {
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    } else if (inited && !rafId) {
      needsRender = true;
      _animate();
    }
  }

  function setCamera(name) {
    const c = cameras[name] || cameras.frontal;
    if (!camera || !controls) return;
    camera.position.set(c.pos[0], c.pos[1], c.pos[2]);
    controls.target.set(c.target[0], c.target[1], c.target[2]);
    controls.update();
    needsRender = true;
  }

  function init(canvasId, bridgeId, type, modelUrlArg) {
    container = document.getElementById(canvasId);
    bridge = document.getElementById(bridgeId);
    if (!container) return false;
    const nextType = type || "dental";
    const nextModel = modelUrlArg || "";
    if (inited && renderer && container.contains(renderer.domElement)
        && nextType === sceneType && nextModel === modelUrl) return true;
    dispose();
    sceneType = nextType;
    modelUrl = nextModel;
    cameras = CAMERAS_DENTAL;
    defaultColor = COLOR_DEFAULT;

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

    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    // En punteros gruesos (tablet) limitamos el DPR a 1.5: la nitidez extra no se
    // percibe y el relleno de píxeles cae ~40% en pantallas retina.
    const _coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, _coarse ? 1.5 : 2));
    renderer.setSize(w, h, false);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);
    renderer.domElement.style.cursor = "grab";
    renderer.domElement.style.display = "block";
    // El canvas llena su contenedor por CSS (el buffer se ajusta con setSize en
    // _resize): así escala bien al agrandar/pantalla completa sin recortarse.
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";

    // Entorno de reflejos (studio suave, sin archivo externo) para brillo húmedo del esmalte.
    scene.environment = _studioEnv();

    scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    const key = new THREE.DirectionalLight(0xffffff, 0.7);
    key.position.set(3, 6, 5); scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.3);
    fill.position.set(-4, -3, 4); scene.add(fill);

    nodes = []; decor = []; needsRender = true;
    _buildDental();

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
    document.addEventListener("visibilitychange", _onVisibility);
    if (window.ResizeObserver) {
      // El contenedor puede cambiar de tamaño sin que cambie la ventana (paneles que
      // se abren/colapsan). ResizeObserver cubre laptop/tablet/pantalla grande.
      resizeObs = new ResizeObserver(_resize);
      resizeObs.observe(container);
    }

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
      out[g.userData.anatomy_id] = "#" + _nodeBaseHex(g)
        .toString(16).padStart(6, "0");
    }
    return out;
  }

  function dispose() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    document.removeEventListener("visibilitychange", _onVisibility);
    if (resizeObs) { resizeObs.disconnect(); resizeObs = null; }
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
    if (modelRoot) {
      modelRoot.traverse((o) => {
        o.geometry?.dispose();
        if (Array.isArray(o.material)) o.material.forEach((m) => m.dispose());
        else o.material?.dispose();
      });
      modelRoot = null;
    }
    nodes = []; decor = []; hovered = null; inited = false;
    renderer = scene = camera = controls = null;
  }

  return { init, setData, setCamera, getColors, dispose, _webglOK };
})();

window.AnatomyViewer = AnatomyViewer;

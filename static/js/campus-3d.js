/**
 * RCERT Smart Campus Digital Twin 2.0 — Authentic 3D Architectural Campus Model
 * Rajiv Gandhi College of Engineering, Research & Technology (RCERT), Chandrapur
 * Modeled from verified reference photographs, drone video frames, and site layout.
 */

// Architectural coordinates for all 18 verified zones
const ZONE_ANCHORS = {
  main_gate:          { pos: [0, 0, 11.5],   type: "Entrance" },
  main_building:      { pos: [0, 0, 0.2],    type: "Administration" },
  computer_science:   { pos: [5.8, 0, -1.0],  type: "Academic" },
  data_science:       { pos: [5.8, 0, 3.4],   type: "Academic" },
  mechanical:         { pos: [-5.8, 0, -1.0], type: "Academic" },
  electrical:         { pos: [-3.4, 0, 2.2],  type: "Academic" },
  mining:             { pos: [-6.2, 0, 3.4],  type: "Academic" },
  civil:              { pos: [8.6, 0, -4.8],  type: "Academic" },
  mba:                { pos: [-3.4, 0, -6.5], type: "Academic" },
  polytechnic:        { pos: [-7.2, 0, -5.5], type: "Academic" },
  electrical_workshop:{ pos: [-8.4, 0, 5.4],  type: "Workshop" },
  auditorium:         { pos: [-9.0, 0, 9.0],  type: "Facility" },
  canteen:            { pos: [2.2, 0, -7.2],  type: "Facility" },
  gym:                { pos: [8.6, 0, 6.2],   type: "Facility" },
  boys_hostel:        { pos: [-9.4, 0, -8.6], type: "Hostel" },
  girls_hostel:       { pos: [9.6, 0, 0.6],   type: "Hostel" },
  boys_parking:       { pos: [-7.0, 0, 12.0], type: "Parking" },
  girls_parking:      { pos: [7.0, 0, 12.0],  type: "Parking" }
};

const CATEGORY_COLORS = {
  Academic:       0x8a72e8,
  Administration: 0xa98af6,
  Facility:       0xde9b59,
  Workshop:       0x48a8b8,
  Hostel:         0x3fa99f,
  Parking:        0x6a788e,
  Entrance:       0x5cc68e
};

export async function startCampusTwin(container, zones, onSelect) {
  if (!container || !zones?.length) return null;

  let THREE;
  try {
    THREE = await import("https://esm.sh/three@0.160.0");
  } catch (error) {
    console.warn("Three.js ESM import failed; activating fallback", error);
    return null;
  }

  if (!THREE.WebGLRenderer) return null;

  // Scene setup
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0e16);
  scene.fog = new THREE.FogExp2(0x0a0e16, 0.016);

  // Camera & Orbit state
  const camera = new THREE.PerspectiveCamera(38, 1, 0.2, 160);
  let radius = 32, azimuth = Math.PI * 0.24, elevation = 0.68;
  const target = new THREE.Vector3(0, 0.5, 1.2);

  function updateCamera() {
    const h = radius * Math.cos(elevation);
    camera.position.set(
      target.x + h * Math.sin(azimuth),
      target.y + radius * Math.sin(elevation),
      target.z + h * Math.cos(azimuth)
    );
    camera.lookAt(target);
  }
  updateCamera();

  // Renderer with high quality color space and tone mapping
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.replaceChildren(renderer.domElement);

  // Daylighting setup matching Chandrapur solar ambiance
  const hemiLight = new THREE.HemisphereLight(0xdce8ff, 0x1f2722, 1.8);
  scene.add(hemiLight);

  const sun = new THREE.DirectionalLight(0xfff3db, 2.8);
  sun.position.set(-14, 26, 16);
  sun.castShadow = true;
  sun.shadow.mapSize.width = 2048;
  sun.shadow.mapSize.height = 2048;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 70;
  sun.shadow.camera.left = -22;
  sun.shadow.camera.right = 22;
  sun.shadow.camera.top = 22;
  sun.shadow.camera.bottom = -22;
  sun.shadow.bias = -0.0004;
  scene.add(sun);

  const fillLight = new THREE.DirectionalLight(0x8faee0, 0.9);
  fillLight.position.set(16, 14, -14);
  scene.add(fillLight);

  // Reusable Architectural Materials
  const matWallCream = new THREE.MeshStandardMaterial({ color: 0xded9cf, roughness: 0.78, metalness: 0.04 });
  const matWallTerracotta = new THREE.MeshStandardMaterial({ color: 0xa24830, roughness: 0.72, metalness: 0.05 });
  const matGlass = new THREE.MeshStandardMaterial({ color: 0x182a3a, roughness: 0.15, metalness: 0.85 });
  const matRoof = new THREE.MeshStandardMaterial({ color: 0x363e48, roughness: 0.85, metalness: 0.1 });
  const matWorkshopRoof = new THREE.MeshStandardMaterial({ color: 0x2e4e6d, roughness: 0.55, metalness: 0.25 });
  const matPortico = new THREE.MeshStandardMaterial({ color: 0xd0cbbd, roughness: 0.65, metalness: 0.05 });
  const matRoad = new THREE.MeshStandardMaterial({ color: 0x1f252c, roughness: 0.88 });
  const matPaving = new THREE.MeshStandardMaterial({ color: 0x2d353f, roughness: 0.92 });
  const matLawn = new THREE.MeshStandardMaterial({ color: 0x213a27, roughness: 0.96 });
  const matLawnBright = new THREE.MeshStandardMaterial({ color: 0x2c4e33, roughness: 0.95 });
  const matTrunk = new THREE.MeshStandardMaterial({ color: 0x4a3a2b, roughness: 0.9 });
  const matFronds = new THREE.MeshStandardMaterial({ color: 0x285933, roughness: 0.75 });
  const matTree = new THREE.MeshStandardMaterial({ color: 0x2d5537, roughness: 0.85 });
  const matCurb = new THREE.MeshStandardMaterial({ color: 0x5a6370, roughness: 0.7 });
  const matWhiteStripe = new THREE.MeshBasicMaterial({ color: 0xd8dde5 });
  const matSteel = new THREE.MeshStandardMaterial({ color: 0xc8d2de, roughness: 0.25, metalness: 0.8 });

  // 1. Campus Ground Terrain
  // Regional Terrain (Chandrapur & Tadoba forest fringe)
  const regionalGround = new THREE.Mesh(new THREE.PlaneGeometry(68, 68), new THREE.MeshStandardMaterial({ color: 0x132217, roughness: 0.98 }));
  regionalGround.rotation.x = -Math.PI / 2;
  regionalGround.position.y = -0.07;
  regionalGround.receiveShadow = true;
  scene.add(regionalGround);

  const campusGround = new THREE.Mesh(new THREE.PlaneGeometry(36, 36), matLawn);
  campusGround.rotation.x = -Math.PI / 2;
  campusGround.position.y = -0.06;
  campusGround.receiveShadow = true;
  scene.add(campusGround);

  // Perimeter Boundary Wall
  const boundNorth = new THREE.Mesh(new THREE.BoxGeometry(35, 0.4, 0.2), matWallCream);
  boundNorth.position.set(0, 0.2, -17.5);
  scene.add(boundNorth);
  const boundWest = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.4, 35), matWallCream);
  boundWest.position.set(-17.5, 0.2, 0);
  scene.add(boundWest);
  const boundEast = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.4, 35), matWallCream);
  boundEast.position.set(17.5, 0.2, 0);
  scene.add(boundEast);

  // 2. Road Network and Boulevard
  function addRoad(x, z, w, d) {
    const r = new THREE.Mesh(new THREE.BoxGeometry(w, 0.02, d), matRoad);
    r.position.set(x, -0.04, z);
    r.receiveShadow = true;
    scene.add(r);
  }
  // Ballarpur Road / Highway frontage outside South boundary
  addRoad(0, 15.2, 48, 3.8);
  // Approach Driveway from Highway into Grand Entrance Gate
  addRoad(0, 12.8, 4.4, 2.6);
  // Highway yellow dashed divider markings
  for (let sx = -22; sx <= 22; sx += 3.5) {
    const hwStripe = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.025, 0.12), new THREE.MeshBasicMaterial({ color: 0xe0a030 }));
    hwStripe.position.set(sx, -0.03, 15.2);
    scene.add(hwStripe);
  }

  // Representative Entrance Bank / ATM Kiosk (State Bank / Canara Bank Campus ATM)
  const kioskGroup = new THREE.Group();
  kioskGroup.position.set(5.2, 0, 11.2);
  const kioskCore = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.4, 1.6), matWallCream);
  kioskCore.position.y = 0.7;
  kioskGroup.add(kioskCore);
  const kioskCanopy = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.1, 1.8), new THREE.MeshStandardMaterial({ color: 0x1b4f8c }));
  kioskCanopy.position.set(0, 1.45, 0);
  kioskGroup.add(kioskCanopy);
  const atmGlass = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.0, 0.04), matGlass);
  atmGlass.position.set(0, 0.6, 0.81);
  kioskGroup.add(atmGlass);
  const atmSign = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.22, 0.06), new THREE.MeshBasicMaterial({ color: 0x0a66c2 }));
  atmSign.position.set(0, 1.25, 0.83);
  kioskGroup.add(atmSign);
  scene.add(kioskGroup);

  // Main Boulevard (Gate to Quad)
  addRoad(0, 7.5, 3.2, 8.5);
  // Transverse Campus Avenue
  addRoad(0, 3.4, 28, 2.2);
  // Northern Quad Loop
  addRoad(0, -3.8, 24, 1.8);
  // Side connectors
  addRoad(-6.5, 1.5, 1.6, 9.0);
  addRoad(6.5, 1.5, 1.6, 9.0);
  addRoad(-6.5, -4.5, 1.4, 6.0);
  addRoad(6.5, -4.5, 1.4, 6.0);
  // Workshop access
  addRoad(-11.5, 5.4, 4.0, 1.4);

  // Center divider stripe on Boulevard
  const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.025, 7.8), matWhiteStripe);
  stripe.position.set(0, -0.03, 7.5);
  scene.add(stripe);

  // 3. Central Circular Roundabout Island (Verified from Frame 060 & 240)
  const roundaboutRing = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.025, 32), matPaving);
  roundaboutRing.position.set(0, -0.035, 3.4);
  scene.add(roundaboutRing);

  const roundaboutIsland = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.68, 0.12, 32), matLawnBright);
  roundaboutIsland.position.set(0, 0.02, 3.4);
  roundaboutIsland.receiveShadow = true;
  scene.add(roundaboutIsland);

  // Roundabout Curb
  const roundaboutCurb = new THREE.Mesh(new THREE.CylinderGeometry(1.72, 1.72, 0.14, 32, 1, true), matCurb);
  roundaboutCurb.position.set(0, 0.03, 3.4);
  scene.add(roundaboutCurb);

  // Center Flagpole with Tricolor
  const flagpole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 3.2, 12), matSteel);
  flagpole.position.set(0, 1.6, 3.4);
  flagpole.castShadow = true;
  scene.add(flagpole);

  const flag = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.02), new THREE.MeshBasicMaterial({ color: 0xff8f3d }));
  flag.position.set(0.38, 2.9, 3.4);
  scene.add(flag);

  // 4. Royal Palm Trees lining the Boulevard (Verified from Drone Frames)
  function addPalmTree(x, z) {
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.12, 1.8, 8), matTrunk);
    trunk.position.set(x, 0.9, z);
    trunk.castShadow = true;
    scene.add(trunk);

    const frondGroup = new THREE.Group();
    frondGroup.position.set(x, 1.8, z);
    for (let a = 0; a < 7; a++) {
      const angle = (a / 7) * Math.PI * 2;
      const frond = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.04, 0.22), matFronds);
      frond.position.set(Math.cos(angle) * 0.45, 0.1, Math.sin(angle) * 0.45);
      frond.rotation.y = angle;
      frond.rotation.z = 0.28;
      frondGroup.add(frond);
    }
    scene.add(frondGroup);
  }
  for (let z = 4.8; z <= 10.5; z += 1.8) {
    addPalmTree(-2.0, z);
    addPalmTree(2.0, z);
  }

  // 5. Landscaping Trees in Campus Quads
  function addShadeTree(x, z, s = 1.0) {
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.09 * s, 0.14 * s, 0.8 * s, 8), matTrunk);
    trunk.position.set(x, 0.4 * s, z);
    trunk.castShadow = true;
    scene.add(trunk);

    const foliage = new THREE.Mesh(new THREE.IcosahedronGeometry(0.55 * s, 1), matTree);
    foliage.position.set(x, 0.95 * s, z);
    foliage.castShadow = true;
    scene.add(foliage);
  }
  const shadeCoords = [
    [-3.2, 5.8], [3.2, 5.8], [-4.5, 0], [4.5, 0], [-2.0, -2.4], [2.0, -2.4],
    [-8.5, -2.5], [8.5, -2.5], [-11.0, 1.0], [11.0, 3.5], [-11.0, 8.0], [11.0, 8.0],
    [-1.0, -8.5], [1.0, -8.5], [-6.0, 8.5], [6.0, 8.5]
  ];
  for (const [tx, tz] of shadeCoords) {
    addShadeTree(tx, tz, 0.9 + Math.random() * 0.25);
  }

  // 5b. Dense Forest Fringe around Campus Perimeter (Chandrapur & Tadoba Forest Belt)
  const forestMats = [
    new THREE.MeshStandardMaterial({ color: 0x1c3a22, roughness: 0.88 }),
    new THREE.MeshStandardMaterial({ color: 0x24472c, roughness: 0.88 }),
    new THREE.MeshStandardMaterial({ color: 0x19321e, roughness: 0.90 }),
    new THREE.MeshStandardMaterial({ color: 0x2d5537, roughness: 0.85 })
  ];

  function addForestTree(x, z, s = 1.0) {
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * s, 0.16 * s, 1.0 * s, 6), matTrunk);
    trunk.position.set(x, 0.5 * s, z);
    trunk.castShadow = true;
    scene.add(trunk);

    const fMat = forestMats[Math.floor(Math.random() * forestMats.length)];
    const isCone = Math.random() > 0.45;
    const foliage = isCone
      ? new THREE.Mesh(new THREE.ConeGeometry(0.75 * s, 1.8 * s, 6), fMat)
      : new THREE.Mesh(new THREE.IcosahedronGeometry(0.7 * s, 1), fMat);
    foliage.position.set(x, (isCone ? 1.5 : 1.3) * s, z);
    foliage.castShadow = true;
    scene.add(foliage);
  }

  // North perimeter forest (behind campus departments)
  for (let x = -22; x <= 22; x += 2.0) {
    addForestTree(x + (Math.random() - 0.5) * 0.8, -19.5 + (Math.random() - 0.5) * 1.4, 1.0 + Math.random() * 0.5);
    addForestTree(x + (Math.random() - 0.5) * 0.8, -21.8 + (Math.random() - 0.5) * 1.6, 1.2 + Math.random() * 0.6);
  }
  // East and West perimeter forest
  for (let z = -19; z <= 13; z += 2.0) {
    addForestTree(-19.5 + (Math.random() - 0.5) * 1.2, z + (Math.random() - 0.5) * 0.8, 1.0 + Math.random() * 0.5);
    addForestTree(-21.8 + (Math.random() - 0.5) * 1.4, z + (Math.random() - 0.5) * 0.8, 1.2 + Math.random() * 0.6);
    addForestTree(19.5 + (Math.random() - 0.5) * 1.2, z + (Math.random() - 0.5) * 0.8, 1.0 + Math.random() * 0.5);
    addForestTree(21.8 + (Math.random() - 0.5) * 1.4, z + (Math.random() - 0.5) * 0.8, 1.2 + Math.random() * 0.6);
  }
  // Highway roadside trees along Ballarpur Road (clear of gate center)
  for (let x = -24; x <= 24; x += 3.2) {
    if (Math.abs(x) > 3.6) {
      addForestTree(x, 17.6 + (Math.random() - 0.5) * 0.8, 1.0 + Math.random() * 0.4);
    }
  }

  // Pickables tracking
  const pickables = [];
  const zoneGroups = new Map();
  const labelSprites = new Map();
  const coreLabels = new Set(["main_building", "main_gate", "computer_science", "mechanical", "electrical_workshop", "boys_hostel", "girls_hostel", "auditorium"]);

  // Label Sprite Generator
  function createZoneLabel(text, colorHex) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 112;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgba(10, 15, 24, 0.92)";
    ctx.beginPath();
    ctx.roundRect(8, 10, 496, 92, 18);
    ctx.fill();
    ctx.strokeStyle = `#${colorHex.toString(16).padStart(6, "0")}`;
    ctx.lineWidth = 4;
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 34px 'Segoe UI', system-ui, Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text.length > 24 ? text.slice(0, 22) + "…" : text, 256, 56);

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(3.8, 0.85, 1);
    sprite.renderOrder = 8;
    return sprite;
  }

  // Builder Helper: Add Window Grid
  function addWindowGrid(group, w, h, rows, cols, zOffset, isBack = false) {
    const spacingX = w / (cols + 1);
    const spacingY = h / (rows + 1);
    const winW = spacingX * 0.65;
    const winH = spacingY * 0.58;

    for (let r = 1; r <= rows; r++) {
      for (let c = 1; c <= cols; c++) {
        const win = new THREE.Mesh(new THREE.BoxGeometry(winW, winH, 0.04), matGlass);
        const wx = -w / 2 + c * spacingX;
        const wy = r * spacingY;
        const wz = isBack ? -zOffset - 0.02 : zOffset + 0.02;
        win.position.set(wx, wy, wz);
        group.add(win);
      }
    }
  }

  // 6. BUILD EACH AUTHENTIC RCERT ARCHITECTURAL ZONE
  for (const zone of zones) {
    const anchor = ZONE_ANCHORS[zone.id] || { pos: [0, 0, 0], type: "Academic" };
    const [px, py, pz] = anchor.pos;
    const cat = zone.type || anchor.type || "Academic";
    const colorHex = CATEGORY_COLORS[cat] || 0x8a72e8;

    const group = new THREE.Group();
    group.position.set(px, py, pz);
    group.userData.zone = zone;
    group.userData.meshes = [];

    // Detailed architectural construction by Zone ID
    if (zone.id === "main_building") {
      // === RCERT MAIN ADMINISTRATION & ACADEMIC COMPLEX ===
      // Verified from Video Frames 060, 120, 240
      const bw = 9.4, bh = 2.8, bd = 3.2;

      // Central Stucco Main Core
      const core = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), matWallCream);
      core.position.y = bh / 2;
      core.castShadow = true;
      core.receiveShadow = true;
      group.add(core);
      group.userData.meshes.push(core);

      // Terracotta Flanking Accent Piers (Frame 120 & 180)
      const pierLeft = new THREE.Mesh(new THREE.BoxGeometry(0.6, bh + 0.1, bd + 0.1), matWallTerracotta);
      pierLeft.position.set(-bw / 2 + 0.3, bh / 2, 0);
      group.add(pierLeft);
      group.userData.meshes.push(pierLeft);

      const pierRight = new THREE.Mesh(new THREE.BoxGeometry(0.6, bh + 0.1, bd + 0.1), matWallTerracotta);
      pierRight.position.set(bw / 2 - 0.3, bh / 2, 0);
      group.add(pierRight);
      group.userData.meshes.push(pierRight);

      // Floor Cornice / Slab Bands (3 stories)
      for (let f = 1; f <= 3; f++) {
        const band = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.15, 0.08, bd + 0.15), matPortico);
        band.position.set(0, (bh / 3) * f, 0);
        group.add(band);
      }

      // Front Central Glass Curtain Wall Atrium
      const atrium = new THREE.Mesh(new THREE.BoxGeometry(3.4, bh * 0.9, 0.5), matGlass);
      atrium.position.set(0, (bh * 0.9) / 2 + 0.1, bd / 2 + 0.22);
      group.add(atrium);
      group.userData.meshes.push(atrium);

      // Drive-Under Entrance Portico Canopy (Frame 060 & 240)
      const porticoCanopy = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.14, 2.0), matPortico);
      porticoCanopy.position.set(0, 1.35, bd / 2 + 1.25);
      porticoCanopy.castShadow = true;
      group.add(porticoCanopy);

      const colCoords = [[-1.6, 2.0], [1.6, 2.0], [-1.6, 0.6], [1.6, 0.6]];
      for (const [cx, cz] of colCoords) {
        const col = new THREE.Mesh(new THREE.BoxGeometry(0.18, 1.35, 0.18), matPortico);
        col.position.set(cx, 1.35 / 2, bd / 2 + cz);
        group.add(col);
      }

      // Windows on front facade wings
      addWindowGrid(group, 2.6, bh, 3, 2, bd / 2); // left wing
      // right wing windows
      const rWin1 = new THREE.Mesh(new THREE.BoxGeometry(2.4, bh * 0.75, 0.04), matGlass);
      rWin1.position.set(3.0, bh / 2, bd / 2 + 0.02);
      group.add(rWin1);

      const lWin1 = new THREE.Mesh(new THREE.BoxGeometry(2.4, bh * 0.75, 0.04), matGlass);
      lWin1.position.set(-3.0, bh / 2, bd / 2 + 0.02);
      group.add(lWin1);

      // Roof Terrace Parapet
      const parapet = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.1, 0.35, bd + 0.1), matWallCream);
      parapet.position.set(0, bh + 0.17, 0);
      group.add(parapet);

      // Distinctive Rooftop Triangular Gazebo Pavilion (Verified from Frame 120!)
      const gazeboCanopy = new THREE.Mesh(new THREE.ConeGeometry(1.6, 1.0, 4), matGlass);
      gazeboCanopy.rotation.y = Math.PI / 4;
      gazeboCanopy.position.set(0, bh + 1.25, 0);
      group.add(gazeboCanopy);

      const gazPillars = [[-0.8, -0.8], [0.8, -0.8], [-0.8, 0.8], [0.8, 0.8]];
      for (const [gx, gz] of gazPillars) {
        const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.75, 8), matSteel);
        p.position.set(gx, bh + 0.65, gz);
        group.add(p);
      }

      // Institutional Signboard Banner
      const signMesh = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.35, 0.08), new THREE.MeshBasicMaterial({ color: 0x1b3c66 }));
      signMesh.position.set(0, bh + 0.05, bd / 2 + 0.15);
      group.add(signMesh);

    } else if (zone.id === "main_gate") {
      // === RCERT GRAND MAIN ENTRANCE GATE (Frame 060) ===
      // Pylons on left and right
      const pylonL = new THREE.Mesh(new THREE.BoxGeometry(0.7, 2.6, 0.7), matWallTerracotta);
      pylonL.position.set(-2.8, 1.3, 0);
      pylonL.castShadow = true;
      group.add(pylonL);
      group.userData.meshes.push(pylonL);

      const pylonR = new THREE.Mesh(new THREE.BoxGeometry(0.7, 2.6, 0.7), matWallTerracotta);
      pylonR.position.set(2.8, 1.3, 0);
      pylonR.castShadow = true;
      group.add(pylonR);
      group.userData.meshes.push(pylonR);

      // Central Lintels / Arched Beam with RCERT Signage
      const lintel = new THREE.Mesh(new THREE.BoxGeometry(6.6, 0.45, 0.6), matWallCream);
      lintel.position.set(0, 2.5, 0);
      group.add(lintel);
      group.userData.meshes.push(lintel);

      const signBoard = new THREE.Mesh(new THREE.BoxGeometry(5.8, 0.28, 0.66), new THREE.MeshBasicMaterial({ color: 0x18345c }));
      signBoard.position.set(0, 2.5, 0);
      group.add(signBoard);

      // Left & Right Security Guard Cabins
      const cabinL = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.6, 1.4), matWallCream);
      cabinL.position.set(-4.2, 0.8, 0);
      group.add(cabinL);
      group.userData.meshes.push(cabinL);

      const cabinR = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.6, 1.4), matWallCream);
      cabinR.position.set(4.2, 0.8, 0);
      group.add(cabinR);
      group.userData.meshes.push(cabinR);

      // Barrier Boom Gate
      const barrier = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.08, 0.08), new THREE.MeshBasicMaterial({ color: 0xf28686 }));
      barrier.position.set(0, 0.5, 0);
      group.add(barrier);

    } else if (zone.id === "electrical_workshop") {
      // === CENTRAL & ELECTRICAL WORKSHOPS (Industrial Gabled Roof) ===
      const ww = 5.2, wh = 1.6, wd = 3.2;
      const wsCore = new THREE.Mesh(new THREE.BoxGeometry(ww, wh, wd), matWallCream);
      wsCore.position.y = wh / 2;
      wsCore.castShadow = true;
      group.add(wsCore);
      group.userData.meshes.push(wsCore);

      // Dual Gabled Roofs (Verified Indian Engineering Workshop Architecture)
      const roofGeom = new THREE.ConeGeometry(2.2, 0.75, 4);
      roofGeom.rotateY(Math.PI / 4);
      roofGeom.scale(1.2, 1, 0.75);

      const gabledRoof1 = new THREE.Mesh(roofGeom, matWorkshopRoof);
      gabledRoof1.position.set(-1.3, wh + 0.35, 0);
      group.add(gabledRoof1);

      const gabledRoof2 = new THREE.Mesh(roofGeom, matWorkshopRoof);
      gabledRoof2.position.set(1.3, wh + 0.35, 0);
      group.add(gabledRoof2);

      // High clerestory window strip
      const clerestory = new THREE.Mesh(new THREE.BoxGeometry(ww * 0.85, 0.28, wd + 0.04), matGlass);
      clerestory.position.set(0, wh * 0.72, 0);
      group.add(clerestory);

    } else if (zone.id === "auditorium") {
      // === AUDITORIUM & CONVOCATION HALL ===
      const aw = 4.6, ah = 2.4, ad = 3.6;
      const audCore = new THREE.Mesh(new THREE.BoxGeometry(aw, ah, ad), matWallCream);
      audCore.position.y = ah / 2;
      audCore.castShadow = true;
      group.add(audCore);
      group.userData.meshes.push(audCore);

      // Stepped tiered roof
      const audRoof = new THREE.Mesh(new THREE.BoxGeometry(aw * 0.85, 0.35, ad * 0.85), matRoof);
      audRoof.position.set(0, ah + 0.17, 0);
      group.add(audRoof);

      // Entrance Portico with columns
      const audPortico = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.12, 1.2), matWallTerracotta);
      audPortico.position.set(0, 1.4, ad / 2 + 0.6);
      group.add(audPortico);

      const colL = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.4, 0.16), matPortico);
      colL.position.set(-1.0, 0.7, ad / 2 + 1.0);
      group.add(colL);

      const colR = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.4, 0.16), matPortico);
      colR.position.set(1.0, 0.7, ad / 2 + 1.0);
      group.add(colR);

    } else if (zone.id === "boys_hostel" || zone.id === "girls_hostel") {
      // === STUDENT HOSTEL BLOCKS (3 Stories with Balcony Grids) ===
      const hw = 5.6, hh = 2.4, hd = 3.0;
      const hostCore = new THREE.Mesh(new THREE.BoxGeometry(hw, hh, hd), matWallCream);
      hostCore.position.y = hh / 2;
      hostCore.castShadow = true;
      group.add(hostCore);
      group.userData.meshes.push(hostCore);

      // Balcony grid cutouts
      addWindowGrid(group, hw * 0.88, hh, 3, 4, hd / 2);
      addWindowGrid(group, hw * 0.88, hh, 3, 4, hd / 2, true);

      // Roof Parapet and water tank tower
      const hostParapet = new THREE.Mesh(new THREE.BoxGeometry(hw + 0.1, 0.3, hd + 0.1), matWallTerracotta);
      hostParapet.position.set(0, hh + 0.15, 0);
      group.add(hostParapet);

      const tankTower = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.7, 1.2), matWallCream);
      tankTower.position.set(-hw * 0.3, hh + 0.5, 0);
      group.add(tankTower);

    } else if (zone.id === "canteen") {
      // === KAKA CANTEEN (Open Pavilion with Pergola Canopy) ===
      const cw = 3.2, ch = 1.3, cd = 2.4;
      const canCore = new THREE.Mesh(new THREE.BoxGeometry(cw, ch, cd), matWallCream);
      canCore.position.y = ch / 2;
      group.add(canCore);
      group.userData.meshes.push(canCore);

      const canRoof = new THREE.Mesh(new THREE.BoxGeometry(cw + 0.4, 0.12, cd + 0.4), matWallTerracotta);
      canRoof.position.set(0, ch + 0.06, 0);
      group.add(canRoof);

      // Outdoor dining tables
      const table1 = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.05, 12), matPaving);
      table1.position.set(cw / 2 + 0.8, 0.3, 0);
      group.add(table1);

    } else if (zone.id === "boys_parking" || zone.id === "girls_parking") {
      // === PARKING LOTS WITH SOLAR SHADE AWNINGS ===
      const pw = 4.2, ph = 0.04, pd = 2.4;
      const lot = new THREE.Mesh(new THREE.BoxGeometry(pw, ph, pd), matRoad);
      lot.position.set(0, 0.02, 0);
      group.add(lot);
      group.userData.meshes.push(lot);

      // Parking bay stripes
      for (let s = -pw * 0.4; s <= pw * 0.4; s += 0.7) {
        const mark = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.015, pd * 0.75), matWhiteStripe);
        mark.position.set(s, 0.045, 0);
        group.add(mark);
      }

      // Shade canopy
      const canopy = new THREE.Mesh(new THREE.BoxGeometry(pw * 0.9, 0.06, pd * 0.8), matWorkshopRoof);
      canopy.position.set(0, 1.1, 0);
      group.add(canopy);

      const pCol1 = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.1, 8), matSteel);
      pCol1.position.set(-pw * 0.4, 0.55, 0);
      group.add(pCol1);
      const pCol2 = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.1, 8), matSteel);
      pCol2.position.set(pw * 0.4, 0.55, 0);
      group.add(pCol2);

    } else {
      // === STANDARD ACADEMIC DEPARTMENTS & WINGS (CSE, IT, Mech, Mining, Civil, MBA, etc.) ===
      // Verified from Courtyard Frame 180 & Complex Frame 240
      const aw = cat === "Academic" ? 4.6 : 3.6;
      const ah = cat === "Academic" ? 2.4 : 1.8;
      const ad = cat === "Academic" ? 2.8 : 2.2;

      // Main structural block
      const acadCore = new THREE.Mesh(new THREE.BoxGeometry(aw, ah, ad), matWallCream);
      acadCore.position.y = ah / 2;
      acadCore.castShadow = true;
      acadCore.receiveShadow = true;
      group.add(acadCore);
      group.userData.meshes.push(acadCore);

      // Terracotta framing pylons
      const pierL = new THREE.Mesh(new THREE.BoxGeometry(0.45, ah + 0.05, ad + 0.08), matWallTerracotta);
      pierL.position.set(-aw / 2 + 0.22, ah / 2, 0);
      group.add(pierL);
      group.userData.meshes.push(pierL);

      const pierR = new THREE.Mesh(new THREE.BoxGeometry(0.45, ah + 0.05, ad + 0.08), matWallTerracotta);
      pierR.position.set(aw / 2 - 0.22, ah / 2, 0);
      group.add(pierR);
      group.userData.meshes.push(pierR);

      // Roof with parapet
      const parapet = new THREE.Mesh(new THREE.BoxGeometry(aw + 0.08, 0.25, ad + 0.08), matRoof);
      parapet.position.set(0, ah + 0.12, 0);
      group.add(parapet);

      // Horizontal Floor Bands
      const band = new THREE.Mesh(new THREE.BoxGeometry(aw + 0.12, 0.06, ad + 0.12), matPortico);
      band.position.set(0, ah * 0.5, 0);
      group.add(band);

      // Recessed Windows
      addWindowGrid(group, aw * 0.75, ah, 2, 3, ad / 2);
    }

    // Add all meshes in this group to raycasting pickables
    for (const m of group.userData.meshes) {
      m.userData.zone = zone;
      m.userData.parentGroup = group;
      pickables.push(m);
    }

    scene.add(group);
    zoneGroups.set(zone.id, group);

    // Floating Label Sprite
    const labelHeight = (group.userData.meshes[0]?.geometry?.parameters?.height || 2.2) + 1.1;
    const sprite = createZoneLabel(zone.name, colorHex);
    sprite.position.set(px, py + labelHeight, pz);
    sprite.userData.zone = zone;
    scene.add(sprite);
    pickables.push(sprite);
    labelSprites.set(zone.id, sprite);
  }

  // Zone Selection & Highlighting
  let selectedId = null;

  function select(id, notify = false) {
    if (selectedId === id && !notify) return;
    selectedId = id;
    for (const [zoneId, grp] of zoneGroups) {
      const active = zoneId === id;
      for (const m of grp.userData.meshes) {
        if (m.material) {
          if (!m.userData.origEmissive) {
            m.userData.origEmissive = m.material.emissive ? m.material.emissive.clone() : new THREE.Color(0);
          }
          if (active) {
            m.material.emissive = new THREE.Color(0x9b7cff);
            m.material.emissiveIntensity = 0.55;
          } else {
            m.material.emissive = m.userData.origEmissive;
            m.material.emissiveIntensity = 0.0;
          }
        }
      }
      grp.scale.setScalar(active ? 1.05 : 1.0);
    }

    for (const [zoneId, sprite] of labelSprites) {
      sprite.visible = coreLabels.has(zoneId) || zoneId === id;
    }

    if (notify) {
      const matchedZone = zones.find(z => z.id === id);
      if (matchedZone) onSelect?.(matchedZone);
    }
  }

  function filterByType(category) {
    for (const [zoneId, grp] of zoneGroups) {
      const zone = grp.userData.zone;
      const matches = category === "all" || zone.type === category;
      grp.visible = matches;
      const sprite = labelSprites.get(zoneId);
      if (sprite) {
        sprite.visible = matches && (coreLabels.has(zoneId) || zoneId === selectedId);
      }
    }
  }

  // Pointer & Orbit Controls
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let drag = null, isMoved = false;

  function resize() {
    const w = Math.max(1, container.clientWidth);
    const h = Math.max(1, container.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  resize();

  function onPointerDown(e) {
    drag = { x: e.clientX, y: e.clientY, azimuth, elevation, btn: e.button };
    isMoved = false;
    renderer.domElement.setPointerCapture?.(e.pointerId);
  }

  function onPointerMove(e) {
    if (!drag) {
      // Hover highlight cursor check
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(pickables, false)[0];
      renderer.domElement.style.cursor = hit ? "pointer" : "default";
      return;
    }

    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) isMoved = true;

    if (drag.btn === 2 || e.shiftKey) {
      // Pan controls
      const panSpeed = 0.025;
      const forward = new THREE.Vector3();
      camera.getWorldDirection(forward);
      forward.y = 0;
      forward.normalize();
      const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();
      target.addScaledVector(right, -dx * panSpeed);
      target.addScaledVector(forward, dy * panSpeed);
    } else {
      // Orbit rotation
      azimuth = drag.azimuth - dx * 0.0055;
      elevation = Math.max(0.18, Math.min(1.38, drag.elevation + dy * 0.004));
    }
    updateCamera();
  }

  function onPointerUp(e) {
    if (!drag) return;
    const wasMoved = isMoved;
    drag = null;
    if (wasMoved) return;

    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);

    const hit = raycaster.intersectObjects(pickables, false)[0];
    if (hit?.object?.userData?.zone) {
      select(hit.object.userData.zone.id, true);
    }
  }

  function onWheel(e) {
    e.preventDefault();
    radius = Math.max(12, Math.min(48, radius + Math.sign(e.deltaY) * 1.5));
    updateCamera();
  }

  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointermove", onPointerMove);
  renderer.domElement.addEventListener("pointerup", onPointerUp);
  renderer.domElement.addEventListener("wheel", onWheel, { passive: false });
  renderer.domElement.addEventListener("contextmenu", e => e.preventDefault());

  // Render loop
  let rafId = 0, isRunning = true;
  function animate() {
    if (!isRunning) return;
    rafId = requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }
  animate();

  const handleVisibility = () => {
    isRunning = !document.hidden;
    if (isRunning && !rafId) animate();
  };
  document.addEventListener("visibilitychange", handleVisibility);

  return {
    select,
    filterByType,
    reset() {
      azimuth = Math.PI * 0.24;
      elevation = 0.68;
      radius = 32;
      target.set(0, 0.5, 1.2);
      updateCamera();
    },
    destroy() {
      isRunning = false;
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", handleVisibility);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("wheel", onWheel);
      renderer.dispose();
      container.replaceChildren();
    }
  };
}

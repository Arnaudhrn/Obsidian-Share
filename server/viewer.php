<?php
// viewer.php - Visualisateur 3D pour fichiers STL

session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax', 'secure' => true]);
session_start();

$folder = $_GET['folder'] ?? '';
$file   = basename($_GET['file'] ?? '');  // basename empêche la traversée de répertoire

// Sanitize folder: pas de / ni de .. (le nom du dossier peut contenir espaces et tirets)
$folder = str_replace(['..', '/', '\\'], '', $folder);

// Validation basique
if (empty($folder) || empty($file)) {
    http_response_code(400);
    die('Paramètres manquants.');
}

// Vérification de l'authentification (même système que index.php)
if (!isset($_SESSION['folders'][$folder]) || !$_SESSION['folders'][$folder]) {
    http_response_code(403);
    die('Accès non autorisé. Retournez sur le site et authentifiez-vous.');
}

// Vérification de l'extension
if (!preg_match('/\.stl$/i', $file)) {
    http_response_code(400);
    die('Format non supporté.');
}

// Construire et valider le chemin réel (anti path-traversal)
$stl_path = realpath(__DIR__ . '/' . $folder . '/.stl/' . $file);
$base_dir = realpath(__DIR__);

if ($stl_path === false || strpos($stl_path, $base_dir . DIRECTORY_SEPARATOR) !== 0 || !file_exists($stl_path)) {
    http_response_code(404);
    die('Fichier STL introuvable.');
}

// URL relative du fichier STL (pour Three.js côté client)
$stl_url = rawurlencode($folder) . '/.stl/' . rawurlencode($file);

// Nom affiché (sans extension)
$display_name = pathinfo($file, PATHINFO_FILENAME);

// Mode intégré (iframe dans le site) vs standalone (nouvel onglet navigateur)
$is_embedded = ($_GET['embed'] ?? '') === '1';
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($display_name) ?> — Viewer 3D</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: #1e1e1e;
            color: #e3e3e3;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Barre du haut — masquée quand intégré en iframe */
        #toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 16px;
            background: #242424;
            border-bottom: 1px solid rgba(100, 95, 135, 0.2);
            flex-shrink: 0;
            z-index: 10;
        }

        #toolbar-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        #file-icon {
            width: 20px;
            height: 20px;
            opacity: 0.7;
        }

        #file-name {
            font-size: 14px;
            font-weight: 500;
            color: #e3e3e3;
            letter-spacing: 0.01em;
        }

        #close-btn {
            background: rgba(100, 95, 135, 0.12);
            border: 1px solid rgba(100, 95, 135, 0.2);
            color: #a0a0a0;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s;
            font-family: inherit;
        }

        #close-btn:hover {
            background: rgba(100, 95, 135, 0.22);
            color: #e3e3e3;
        }

        /* Canvas WebGL */
        #canvas-container {
            flex: 1;
            position: relative;
        }

        canvas {
            display: block;
            width: 100% !important;
            height: 100% !important;
        }

        /* Spinner de chargement */
        #loader {
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: #1e1e1e;
            gap: 14px;
            z-index: 5;
        }

        #loader-spinner {
            width: 36px;
            height: 36px;
            border: 3px solid rgba(100, 95, 135, 0.2);
            border-top-color: #7c3aed;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        #loader-text {
            font-size: 13px;
            color: #a0a0a0;
        }

        /* Aide contrôles */
        #controls-hint {
            position: absolute;
            bottom: 14px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 11px;
            color: rgba(160, 160, 160, 0.5);
            pointer-events: none;
            white-space: nowrap;
            letter-spacing: 0.02em;
        }

        /* Message d'erreur */
        #error-msg {
            display: none;
            position: absolute;
            inset: 0;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 10px;
            color: #a0a0a0;
            font-size: 14px;
        }

        #error-msg.visible { display: flex; }
    </style>

    <!-- Import map Three.js (CDN) -->
    <script type="importmap">
    {
        "imports": {
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
        }
    }
    </script>
</head>
<body>

<!-- Barre du haut (masquée si iframe dans le site) -->
<div id="toolbar" <?= $is_embedded ? 'style="display:none"' : '' ?>>
    <div id="toolbar-left">
        <svg id="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
                d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9"/>
        </svg>
        <span id="file-name"><?= htmlspecialchars($display_name) ?></span>
    </div>
    <button id="close-btn" onclick="window.close()">✕ Fermer</button>
</div>

<!-- Zone 3D -->
<div id="canvas-container">
    <div id="loader">
        <div id="loader-spinner"></div>
        <div id="loader-text">Chargement du modèle…</div>
    </div>
    <div id="error-msg">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
        </svg>
        <span>Impossible de charger le fichier STL.</span>
    </div>
    <div id="controls-hint">Clic gauche : rotation &nbsp;·&nbsp; Clic droit : déplacer &nbsp;·&nbsp; Molette : zoom</div>
</div>

<script type="module">
import * as THREE from 'three';
import { STLLoader }     from 'three/addons/loaders/STLLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const STL_URL = <?= json_encode($stl_url) ?>;

// ── Scène ────────────────────────────────────────────────────────────────────
const container = document.getElementById('canvas-container');
const scene     = new THREE.Scene();
// Fond géré par CSS — évite l'altération de couleur par le tone mapping
scene.background = null;

// ── Caméra ───────────────────────────────────────────────────────────────────
const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.01,
    10000
);
camera.position.set(0, 0, 5);

// ── Renderer ─────────────────────────────────────────────────────────────────
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.outputColorSpace   = THREE.SRGBColorSpace;
renderer.toneMapping        = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
container.appendChild(renderer.domElement);

// ── Lumières (3 points, style macOS Preview) ─────────────────────────────────
// Lumière ambiante douce
const ambient = new THREE.AmbientLight(0xffffff, 0.45);
scene.add(ambient);

// Lumière clé (key light) — haut droit avant
const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
keyLight.position.set(5, 8, 6);
scene.add(keyLight);

// Lumière de remplissage (fill light) — bas gauche
const fillLight = new THREE.DirectionalLight(0xd0e8ff, 0.4);
fillLight.position.set(-6, -3, 4);
scene.add(fillLight);

// Lumière de contour (rim light) — arrière
const rimLight = new THREE.DirectionalLight(0xb0c8ff, 0.25);
rimLight.position.set(0, 4, -8);
scene.add(rimLight);


// ── Contrôles ────────────────────────────────────────────────────────────────
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping    = true;
controls.dampingFactor    = 0.06;
controls.screenSpacePanning = true;
controls.minDistance      = 0.1;
controls.maxDistance      = 500;
controls.autoRotateSpeed  = 0;

// ── Chargement STL ───────────────────────────────────────────────────────────
const loader = new STLLoader();
loader.load(
    STL_URL,
    function (geometry) {
        // Centrer et normaliser la géométrie
        geometry.computeBoundingBox();
        const box    = geometry.boundingBox;
        const center = new THREE.Vector3();
        box.getCenter(center);
        geometry.translate(-center.x, -center.y, -center.z);

        const size   = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale  = 3.5 / maxDim;   // Remplit ~80% du viewport

        // Matériau style macOS Preview (blanc mat légèrement brillant)
        const material = new THREE.MeshStandardMaterial({
            color:     0xe8e8e8,
            roughness: 0.65,
            metalness: 0.08,
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.scale.setScalar(scale);
        scene.add(mesh);

        // Ajuster la caméra pour cadrer la pièce
        const dist = maxDim * scale * 1.8;
        camera.position.set(dist * 0.7, dist * 0.5, dist);
        camera.near = dist * 0.001;
        camera.far  = dist * 20;
        camera.updateProjectionMatrix();
        controls.target.set(0, mesh.position.y, 0);
        controls.update();

        // Masquer le loader
        document.getElementById('loader').style.display = 'none';
    },
    function (xhr) {
        if (xhr.total > 0) {
            const pct = Math.round(xhr.loaded / xhr.total * 100);
            document.getElementById('loader-text').textContent =
                'Chargement… ' + pct + '%';
        }
    },
    function (error) {
        console.error('STL load error:', error);
        document.getElementById('loader').style.display = 'none';
        document.getElementById('error-msg').classList.add('visible');
    }
);

// ── Boucle de rendu ──────────────────────────────────────────────────────────
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}
animate();

// ── Redimensionnement ────────────────────────────────────────────────────────
window.addEventListener('resize', () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
});
</script>

</body>
</html>

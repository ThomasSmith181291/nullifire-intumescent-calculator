/**
 * Three.js 3D structural grid preview.
 * Phase 1: Wireframe lines for grid, levels, and members.
 * Members colored by verification status (green/amber/red).
 */

const STATUS_COLORS = {
    ok: 0x22c55e,
    warning: 0xf59e0b,
    exceeds: 0xef4444,
    pending: 0x9ca3af,
};

let scene, camera, renderer, controls;
let gridGroup, levelGroup, memberGroup;
let container = null;
let animFrameId = null;

export function init3D(containerId) {
    container = document.getElementById(containerId);
    if (!container || typeof THREE === 'undefined') return false;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(30, 20, 30);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Orbit controls
    if (THREE.OrbitControls) {
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
    }

    // Groups
    gridGroup = new THREE.Group();
    levelGroup = new THREE.Group();
    memberGroup = new THREE.Group();
    scene.add(gridGroup, levelGroup, memberGroup);

    // Ambient light
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    scene.add(new THREE.DirectionalLight(0xffffff, 0.5));

    // Ground plane
    const groundGeo = new THREE.PlaneGeometry(100, 100);
    const groundMat = new THREE.MeshBasicMaterial({ color: 0xe8e8e8, side: THREE.DoubleSide });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    scene.add(ground);

    // Axes helper
    scene.add(new THREE.AxesHelper(5));

    // Resize handler
    window.addEventListener('resize', onResize);

    animate();
    return true;
}

function onResize() {
    if (!container || !camera || !renderer) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
    animFrameId = requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
}

export function updateScene(sceneData) {
    if (!scene) return;

    // Clear existing
    clearGroup(gridGroup);
    clearGroup(levelGroup);
    clearGroup(memberGroup);

    if (!sceneData) return;

    const { gridlines, levels, members, intersections } = sceneData;

    // Draw gridlines
    drawGridlines(gridlines);

    // Draw levels as horizontal planes
    drawLevels(levels, gridlines);

    // Draw members as colored lines
    drawMembers(members, intersections, levels);

    // Auto-fit camera
    fitCamera(gridlines, levels);
}

function clearGroup(group) {
    while (group.children.length > 0) {
        const child = group.children[0];
        group.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
    }
}

function drawGridlines(gridlines) {
    const xLines = gridlines.filter(g => g.direction === 'x');
    const yLines = gridlines.filter(g => g.direction === 'y');
    const maxX = Math.max(...xLines.map(l => l.position), 10);
    const maxY = Math.max(...yLines.map(l => l.position), 10);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x999999, linewidth: 1 });
    const labelMat = new THREE.LineBasicMaterial({ color: 0xE31937, linewidth: 2 });

    for (const gl of xLines) {
        const geo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(gl.position, 0, 0),
            new THREE.Vector3(gl.position, 0, maxY + 2),
        ]);
        gridGroup.add(new THREE.Line(geo, lineMat));

        // Label
        addTextLabel(gl.name, gl.position, 0.5, -1, gridGroup);
    }

    for (const gl of yLines) {
        const geo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, gl.position),
            new THREE.Vector3(maxX + 2, 0, gl.position),
        ]);
        gridGroup.add(new THREE.Line(geo, lineMat));
        addTextLabel(gl.name, -1, 0.5, gl.position, gridGroup);
    }
}

function drawLevels(levels, gridlines) {
    if (!levels.length) return;
    const xLines = gridlines.filter(g => g.direction === 'x');
    const yLines = gridlines.filter(g => g.direction === 'y');
    const maxX = Math.max(...xLines.map(l => l.position), 10);
    const maxY = Math.max(...yLines.map(l => l.position), 10);

    for (const level of levels) {
        const h = level.height;
        // Draw a faint rectangle at this height
        const points = [
            new THREE.Vector3(0, h, 0),
            new THREE.Vector3(maxX, h, 0),
            new THREE.Vector3(maxX, h, maxY),
            new THREE.Vector3(0, h, maxY),
            new THREE.Vector3(0, h, 0),
        ];
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        const mat = new THREE.LineBasicMaterial({ color: 0x4488ff, linewidth: 1, transparent: true, opacity: 0.4 });
        levelGroup.add(new THREE.Line(geo, mat));

        addTextLabel(level.name, -2, h, 0, levelGroup);
    }
}

function drawMembers(members, intersections, levels) {
    const levelMap = {};
    for (const l of levels) levelMap[l.name] = l.height;

    for (const member of members) {
        const from = member.grid_from;
        const to = member.grid_to;
        const levelName = member.grid_level || member.level;

        if (!from || !to || !intersections[from] || !intersections[to]) continue;

        const h = levelMap[levelName] || 0;
        const p1 = intersections[from];
        const p2 = intersections[to];

        const color = STATUS_COLORS[member.status] || STATUS_COLORS.pending;
        const geo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(p1.x, h, p1.y),
            new THREE.Vector3(p2.x, h, p2.y),
        ]);
        const mat = new THREE.LineBasicMaterial({ color, linewidth: 3 });
        const line = new THREE.Line(geo, mat);
        line.userData = { memberId: member.id };
        memberGroup.add(line);
    }
}

function addTextLabel(text, x, y, z, group) {
    // Simple sprite-based text labels
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#333';
    ctx.font = 'bold 24px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(text, 64, 40);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(x, y, z);
    sprite.scale.set(2, 1, 1);
    group.add(sprite);
}

function fitCamera(gridlines, levels) {
    const xLines = gridlines.filter(g => g.direction === 'x');
    const yLines = gridlines.filter(g => g.direction === 'y');
    const maxX = Math.max(...xLines.map(l => l.position), 10);
    const maxY = Math.max(...yLines.map(l => l.position), 10);
    const maxH = Math.max(...levels.map(l => l.height), 5);

    const dist = Math.max(maxX, maxY, maxH) * 1.5;
    camera.position.set(dist, dist * 0.7, dist);
    camera.lookAt(maxX / 2, maxH / 2, maxY / 2);
    if (controls) controls.target.set(maxX / 2, maxH / 2, maxY / 2);
}

export function destroy3D() {
    if (animFrameId) cancelAnimationFrame(animFrameId);
    if (renderer && container) {
        container.removeChild(renderer.domElement);
        renderer.dispose();
    }
    window.removeEventListener('resize', onResize);
    scene = camera = renderer = controls = null;
}

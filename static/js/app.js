import { api } from './api.js';

// ── State ──
let project = null;
let memberGridApi = null;
let xGridApi = null, yGridApi = null, levelGridApi = null;
let products = [], fireRatings = [], failureTemps = [], origins = [], steelTypes = [];
let threeScene = null;

// ── Helpers ──
const $ = id => document.getElementById(id);
function fillSelect(id, opts, sel) {
    $(id).innerHTML = opts.map(o => `<option value="${o.v}"${String(o.v)===String(sel)?' selected':''}>${o.t}</option>`).join('');
}
function toast(msg, type='success') {
    const t = document.createElement('div'); t.className = `toast ${type}`; t.textContent = msg;
    document.body.appendChild(t); setTimeout(() => t.remove(), 3000);
}
function modal(html) {
    const o = document.createElement('div'); o.className = 'modal-overlay';
    o.innerHTML = `<div class="modal">${html}</div>`;
    document.body.appendChild(o);
    o.addEventListener('click', e => { if (e.target === o) o.remove(); });
    return o;
}

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
    [products, origins, steelTypes] = await Promise.all([
        api.getProducts(), api.getOrigins(), api.getSteelTypes()
    ]);
    fillSelect('sel-origin', origins.map(o => ({ v: o.id, t: `${o.code} - ${o.description}` })));

    // Buttons
    for (const [id, fn] of Object.entries({
        'btn-new-project': showNewProject, 'btn-load-project': showLoadProject,
        'btn-welcome-new': showNewProject, 'btn-welcome-load': showLoadProject,
        'btn-add-member': showAddMember, 'btn-import': showImport,
        'btn-delete-selected': deleteSelected, 'btn-close-panel': () => $('product-panel').style.display='none',
        'btn-export-excel': () => project && window.open(api.exportExcelUrl(project.id)),
        'btn-export-pdf': () => project && window.open(api.exportPdfUrl(project.id)),
    })) { const el = $(id); if (el) el.onclick = fn; }

    // Sidebar changes
    $('sel-fire-rating').onchange = async () => { await cascadeTemps(); await saveDefaults(); };
    $('sel-failure-temp').onchange = saveDefaults;
    $('sel-origin').onchange = saveDefaults;

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            $(btn.dataset.tab).classList.add('active');
            if (btn.dataset.tab === 'grid-tab') refreshThreeScene();
        };
    });

    // Grid setup buttons
    $('btn-add-x-row').onclick = () => xGridApi?.applyTransaction({ add: [{ name: '', position: 0 }] });
    $('btn-add-y-row').onclick = () => yGridApi?.applyTransaction({ add: [{ name: '', position: 0 }] });
    $('btn-add-level-row').onclick = () => levelGridApi?.applyTransaction({ add: [{ name: '', height: 0 }] });
    $('btn-save-x').onclick = () => saveGridlines('x');
    $('btn-save-y').onclick = () => saveGridlines('y');
    $('btn-save-levels').onclick = saveLevels;
});

// ── Project ──
async function showNewProject() {
    const frs = products.length ? await api.getProductFireRatings(products[0].id) : [];
    const fts = frs.length ? await api.getProductFailureTemps(products[0].id, frs[1]?.id || frs[0]?.id) : [];
    const m = modal(`
        <h2>New Project</h2>
        <div class="form-group"><label>Project Name *</label><input type="text" id="dlg-name" autofocus></div>
        <div class="form-group"><label>Client</label><input type="text" id="dlg-client"></div>
        <div class="form-group"><label>Fire Rating</label><select id="dlg-fr">${frs.map(f=>`<option value="${f.id}"${f.id===3?' selected':''}>${f.description}</option>`).join('')}</select></div>
        <div class="form-group"><label>Failure Temp</label><select id="dlg-ft">${fts.map(f=>`<option value="${f.id}"${f.id===7?' selected':''}>${f.description}</option>`).join('')}</select></div>
        <div class="btn-row"><button class="btn btn-secondary" id="dlg-cancel">Cancel</button><button class="btn btn-primary" id="dlg-ok">Create</button></div>
    `);
    $('dlg-fr').onchange = async () => {
        const fts2 = await api.getProductFailureTemps(products[0].id, $('dlg-fr').value);
        $('dlg-ft').innerHTML = fts2.map(f => `<option value="${f.id}">${f.description}</option>`).join('');
    };
    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-ok').onclick = async () => {
        const name = $('dlg-name').value.trim(); if (!name) return;
        const p = await api.createProject({ name, client: $('dlg-client').value.trim(),
            product_id: products[0]?.id||284, fire_rating_id: +$('dlg-fr').value||3,
            failure_temp_id: +$('dlg-ft').value||7, origin_id: 1 });
        m.remove(); await loadProject(p.id); toast('Project created');
    };
    $('dlg-name').onkeydown = e => { if (e.key === 'Enter') $('dlg-ok').click(); };
}

async function showLoadProject() {
    const list = await api.listProjects();
    if (!list.length) { toast('No projects', 'error'); return; }
    const m = modal(`<h2>Load Project</h2>
        <div style="max-height:300px;overflow-y:auto">${list.map(p => `<div class="load-item" data-id="${p.id}" style="padding:10px;cursor:pointer;border-bottom:1px solid #eee"><strong>${p.name}</strong>${p.client?' - '+p.client:''}</div>`).join('')}</div>
        <div class="btn-row"><button class="btn btn-secondary" id="dlg-cancel">Cancel</button></div>`);
    $('dlg-cancel').onclick = () => m.remove();
    m.querySelectorAll('.load-item').forEach(el => {
        el.onmouseenter = () => el.style.background = '#f5f5f5';
        el.onmouseleave = () => el.style.background = '';
        el.onclick = async () => { m.remove(); await loadProject(el.dataset.id); };
    });
}

async function loadProject(pid) {
    project = await api.getProject(pid);
    if (!project) return;

    $('welcome-screen').style.display = 'none';
    $('work-area').style.display = 'flex';
    $('project-settings').style.display = 'block';
    $('header-actions').style.display = 'flex';
    $('header-project-name').textContent = project.name;
    $('inp-project-name').value = project.name;
    $('inp-project-client').value = project.client || '';

    fireRatings = await api.getProductFireRatings(products[0]?.id || project.product_id);
    fillSelect('sel-fire-rating', fireRatings.map(f => ({ v: f.id, t: f.description })), project.fire_rating_id);
    await cascadeTemps();
    fillSelect('sel-origin', origins.map(o => ({ v: o.id, t: `${o.code} - ${o.description}` })), project.origin_id);

    initGridSetupTables();
    initMemberGrid();
    updateSummary();
}

async function cascadeTemps() {
    const frId = $('sel-fire-rating').value;
    const pid = products[0]?.id || project?.product_id;
    if (!frId || !pid) return;
    failureTemps = await api.getProductFailureTemps(pid, frId);
    fillSelect('sel-failure-temp', failureTemps.map(f => ({ v: f.id, t: f.description })), project?.failure_temp_id);
}

async function saveDefaults() {
    if (!project) return;
    const d = { fire_rating_id: +$('sel-fire-rating').value, failure_temp_id: +$('sel-failure-temp').value, origin_id: +$('sel-origin').value };
    if (isNaN(d.fire_rating_id) || isNaN(d.failure_temp_id)) return;
    project = await api.updateProject(project.id, d);
    if (memberGridApi && project.members) { memberGridApi.setGridOption('rowData', project.members); updateSummary(); }
}

// ── Grid Setup Tab ──
function initGridSetupTables() {
    const gridlineCols = [
        { field: 'name', headerName: 'Name', editable: true, width: 80, cellEditor: 'agTextCellEditor' },
        { field: 'position', headerName: 'Position (m)', editable: true, width: 120, cellEditor: 'agNumberCellEditor',
          valueParser: p => parseFloat(p.newValue) || 0 },
        { headerName: '', width: 40, cellRenderer: p => '<span style="cursor:pointer;color:#ccc" title="Delete">✕</span>',
          onCellClicked: p => p.api.applyTransaction({ remove: [p.data] }) },
    ];
    const levelCols = [
        { field: 'name', headerName: 'Name', editable: true, width: 100, cellEditor: 'agTextCellEditor' },
        { field: 'height', headerName: 'Height (m)', editable: true, width: 100, cellEditor: 'agNumberCellEditor',
          valueParser: p => parseFloat(p.newValue) || 0 },
        { headerName: '', width: 40, cellRenderer: () => '<span style="cursor:pointer;color:#ccc" title="Delete">✕</span>',
          onCellClicked: p => p.api.applyTransaction({ remove: [p.data] }) },
    ];
    const defaults = { defaultColDef: { resizable: true, sortable: false }, animateRows: false, singleClickEdit: true };

    // Load existing data
    loadGridData().then(({ xLines, yLines, levels }) => {
        if (xGridApi) xGridApi.destroy();
        xGridApi = agGrid.createGrid($('x-grid-table'), { ...defaults, columnDefs: gridlineCols,
            rowData: xLines.length ? xLines.map(g => ({ name: g.name, position: g.position }))
                : [{ name: 'A', position: 0 }, { name: 'B', position: 6 }, { name: 'C', position: 12 }] });

        if (yGridApi) yGridApi.destroy();
        yGridApi = agGrid.createGrid($('y-grid-table'), { ...defaults, columnDefs: gridlineCols,
            rowData: yLines.length ? yLines.map(g => ({ name: g.name, position: g.position }))
                : [{ name: '1', position: 0 }, { name: '2', position: 8 }] });

        if (levelGridApi) levelGridApi.destroy();
        levelGridApi = agGrid.createGrid($('levels-table'), { ...defaults, columnDefs: levelCols,
            rowData: levels.length ? levels.map(l => ({ name: l.name, height: l.height }))
                : [{ name: 'Ground', height: 0 }, { name: 'First Floor', height: 3.5 }, { name: 'Roof', height: 7.2 }] });
    });
}

async function loadGridData() {
    if (!project) return { xLines: [], yLines: [], levels: [] };
    const [gridlines, levels] = await Promise.all([api.getGridlines(project.id), api.getLevels(project.id)]);
    return { xLines: gridlines.filter(g => g.direction === 'x'), yLines: gridlines.filter(g => g.direction === 'y'), levels };
}

function getGridRows(gridApi) {
    const rows = [];
    gridApi.forEachNode(n => { if (n.data.name) rows.push(n.data); });
    return rows;
}

async function saveGridlines(direction) {
    if (!project) return;
    const ga = direction === 'x' ? xGridApi : yGridApi;
    const rows = getGridRows(ga).map(r => ({ direction, name: r.name, position: parseFloat(r.position) || 0 }));
    // Clear existing gridlines of this direction then batch add
    const existing = await api.getGridlines(project.id);
    for (const g of existing.filter(g => g.direction === direction)) {
        await api.deleteGridline(project.id, g.id);
    }
    if (rows.length) await api.batchAddGridlines(project.id, rows);
    toast(`${direction.toUpperCase()} gridlines saved`);
    refreshThreeScene();
}

async function saveLevels() {
    if (!project) return;
    const rows = getGridRows(levelGridApi).map(r => ({ name: r.name, height: parseFloat(r.height) || 0 }));
    // Clear and re-add
    const existing = await api.getLevels(project.id);
    for (const l of existing) await api.deleteLevel(project.id, l.id);
    if (rows.length) await api.batchAddLevels(project.id, rows);
    toast('Levels saved');
    refreshThreeScene();
}

// ── 3D Scene ──
function refreshThreeScene() {
    if (!project) return;
    api.getSceneData(project.id).then(data => {
        if (!data) return;
        render3D(data);
    });
}

function render3D(sceneData) {
    const container = $('three-container');
    if (!container || typeof THREE === 'undefined') return;

    // Dispose previous
    if (threeScene?.renderer) {
        container.innerHTML = '';
        threeScene.renderer.dispose();
    }

    const W = container.clientWidth, H = container.clientHeight;
    if (W < 10 || H < 10) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dir = new THREE.DirectionalLight(0xffffff, 0.4);
    dir.position.set(10, 20, 10);
    scene.add(dir);

    // Ground
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshBasicMaterial({ color: 0xe8e8e8, side: THREE.DoubleSide }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02; scene.add(ground);

    const { gridlines, levels, members, intersections } = sceneData;
    const xLines = gridlines.filter(g => g.direction === 'x');
    const yLines = gridlines.filter(g => g.direction === 'y');
    const maxX = Math.max(...xLines.map(l => l.position), 1);
    const maxY = Math.max(...yLines.map(l => l.position), 1);
    const maxH = Math.max(...levels.map(l => l.height), 1);
    const gridMat = new THREE.LineBasicMaterial({ color: 0xbbbbbb });
    const levelMat = new THREE.LineBasicMaterial({ color: 0x4488ff, transparent: true, opacity: 0.3 });

    // Draw gridlines
    for (const g of xLines) {
        const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(g.position, 0, -1), new THREE.Vector3(g.position, 0, maxY + 1)]);
        scene.add(new THREE.Line(geo, gridMat));
        addLabel(scene, g.name, g.position, 0.3, -1.5);
    }
    for (const g of yLines) {
        const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-1, 0, g.position), new THREE.Vector3(maxX + 1, 0, g.position)]);
        scene.add(new THREE.Line(geo, gridMat));
        addLabel(scene, g.name, -1.5, 0.3, g.position);
    }

    // Draw levels
    for (const lv of levels) {
        const pts = [new THREE.Vector3(-0.5, lv.height, -0.5), new THREE.Vector3(maxX+0.5, lv.height, -0.5),
                     new THREE.Vector3(maxX+0.5, lv.height, maxY+0.5), new THREE.Vector3(-0.5, lv.height, maxY+0.5),
                     new THREE.Vector3(-0.5, lv.height, -0.5)];
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), levelMat));
        addLabel(scene, lv.name, -2, lv.height + 0.2, 0);
    }

    // Draw vertical columns at intersections (faint)
    const colMat = new THREE.LineBasicMaterial({ color: 0xdddddd });
    for (const key of Object.keys(intersections)) {
        const p = intersections[key];
        for (let i = 0; i < levels.length - 1; i++) {
            const geo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(p.x, levels[i].height, p.y),
                new THREE.Vector3(p.x, levels[i + 1].height, p.y)
            ]);
            scene.add(new THREE.Line(geo, colMat));
        }
    }

    // Draw members
    const STATUS_COLORS = { ok: 0x22c55e, warning: 0xf59e0b, exceeds: 0xef4444, pending: 0x9ca3af };
    const levelMap = {};
    for (const l of levels) levelMap[l.name] = l.height;

    for (const m of members) {
        if (!m.grid_from || !m.grid_to) continue;
        const p1 = intersections[m.grid_from], p2 = intersections[m.grid_to];
        if (!p1 || !p2) continue;
        const h1 = levelMap[m.grid_level_from] || 0;
        const h2 = levelMap[m.grid_level_to] || h1;
        const color = STATUS_COLORS[m.status] || 0x9ca3af;
        const mat = new THREE.LineBasicMaterial({ color, linewidth: 2 });
        const geo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(p1.x, h1, p1.y), new THREE.Vector3(p2.x, h2, p2.y)
        ]);
        scene.add(new THREE.Line(geo, mat));
    }

    // Camera
    const dist = Math.max(maxX, maxY, maxH) * 1.8;
    camera.position.set(dist * 0.8, dist * 0.6, dist * 0.8);
    controls.target.set(maxX / 2, maxH / 2, maxY / 2);

    threeScene = { scene, camera, renderer, controls };
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    // Resize
    const ro = new ResizeObserver(() => {
        const w = container.clientWidth, h = container.clientHeight;
        if (w > 0 && h > 0) { camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h); }
    });
    ro.observe(container);
}

function addLabel(scene, text, x, y, z) {
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 48;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#555'; ctx.font = 'bold 22px Arial'; ctx.textAlign = 'center';
    ctx.fillText(text, 64, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
    sprite.position.set(x, y, z); sprite.scale.set(1.5, 0.6, 1);
    scene.add(sprite);
}

// ── Member Grid ──
function initMemberGrid() {
    const frOpts = fireRatings.map(f => f.id);
    const frMap = Object.fromEntries(fireRatings.map(f => [f.id, f.description]));
    const ftOpts = failureTemps.map(f => f.id);
    const ftMap = Object.fromEntries(failureTemps.map(f => [f.id, f.description]));
    const STATUS_COLORS = { ok: '#22c55e', warning: '#f59e0b', exceeds: '#ef4444', pending: '#9ca3af' };

    const cols = [
        { headerName: '', checkboxSelection: true, headerCheckboxSelection: true, width: 36, pinned: 'left', suppressMenu: true },
        { field: 'member_type', headerName: 'Type', width: 60, editable: true,
          cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['beam', 'column', 'bracing'] } },
        { field: 'section_name', headerName: 'Section', width: 130 },
        { field: 'steel_type', headerName: 'Steel', width: 45 },
        { field: 'hp_profile_name', headerName: 'Exp.', width: 55 },
        { field: 'hp_over_a', headerName: 'Hp/A', width: 55, valueFormatter: p => p.value != null ? Math.round(p.value) : '' },
        { field: 'fire_rating_id', headerName: 'Fire Rating', width: 95, editable: true,
          cellEditor: 'agSelectCellEditor', cellEditorParams: { values: frOpts },
          valueFormatter: p => p.value != null ? (frMap[p.value] || '(default)') : '(default)' },
        { field: 'failure_temp_id', headerName: 'Temp', width: 65, editable: true,
          cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ftOpts },
          valueFormatter: p => p.value != null ? (ftMap[p.value] || '(default)') : '(default)' },
        { field: 'product_id', headerName: 'Product', width: 120, editable: false,
          valueFormatter: p => { if (!p.value) return '(default)'; const pr = products.find(x => x.id === p.value); return pr ? pr.name.replace('Nullifire ', '') : '(default)'; } },
        { field: 'dft_mm', headerName: 'DFT', width: 105,
          valueFormatter: p => p.value != null ? `${p.value.toFixed(3)} (${Math.round(p.value*1000)}um)` : '-' },
        { field: 'quantity', headerName: 'Qty', width: 50, editable: true, cellEditor: 'agNumberCellEditor' },
        { field: 'length_m', headerName: 'Len(m)', width: 65, editable: true, cellEditor: 'agNumberCellEditor',
          valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'surface_area_m2', headerName: 'Area(m2)', width: 70, valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'volume_litres', headerName: 'Litres', width: 60, valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'zone', headerName: 'Zone', width: 70, editable: true },
        { field: 'level', headerName: 'Level', width: 60, editable: true },
        { field: 'status', headerName: '', width: 35, suppressMenu: true,
          cellRenderer: p => `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${STATUS_COLORS[p.value]||STATUS_COLORS.pending}" title="${p.value||''}"></span>` },
        { headerName: '', width: 55, suppressMenu: true,
          cellRenderer: () => `<button class="btn btn-sm btn-secondary" style="padding:2px 5px;font-size:10px" data-action="compare">Compare</button>`,
          onCellClicked: e => { if (e.event.target.dataset.action === 'compare') showCompare(e.data); } },
    ];

    if (memberGridApi) memberGridApi.destroy();
    memberGridApi = agGrid.createGrid($('member-grid'), {
        columnDefs: cols, rowData: project?.members || [], rowSelection: 'multiple',
        enableCellChangeFlash: true, animateRows: true, singleClickEdit: true,
        defaultColDef: { resizable: true, sortable: true, filter: true },
        getRowId: p => p.data.id,
        onCellValueChanged: onMemberEdit,
        onSelectionChanged: () => {
            const n = memberGridApi.getSelectedRows().length;
            $('btn-delete-selected').disabled = n === 0;
            $('btn-delete-selected').textContent = n ? `Delete (${n})` : 'Delete Selected';
        },
    });
}

async function onMemberEdit(ev) {
    const { data, colDef, newValue, oldValue } = ev;
    if (!data.id || !project || newValue === oldValue) return;
    try {
        const updated = await api.updateMember(project.id, data.id, { [colDef.field]: newValue });
        if (updated?.id) { ev.api.applyTransaction({ update: [updated] }); updateSummary(); }
    } catch (e) { toast(`Update failed: ${e.message}`, 'error'); }
}

async function deleteSelected() {
    if (!memberGridApi || !project) return;
    const sel = memberGridApi.getSelectedRows(); if (!sel.length) return;
    await api.batchDeleteMembers(project.id, sel.map(r => r.id));
    memberGridApi.applyTransaction({ remove: sel });
    updateSummary(); toast(`Deleted ${sel.length} member(s)`);
}

function updateSummary() {
    let L = 0, K = 0, A = 0, N = 0, ok = 0, w = 0, x = 0;
    if (memberGridApi) memberGridApi.forEachNode(n => {
        const d = n.data; L += d.volume_litres||0; K += d.weight_kg||0; A += d.surface_area_m2||0; N++;
        if (d.status === 'ok') ok++; else if (d.status === 'warning') w++; else if (d.status === 'exceeds') x++;
    });
    $('ss-count').textContent = N; $('ss-area').textContent = `${A.toFixed(1)} m\u00B2`;
    $('ss-litres').textContent = `${L.toFixed(1)} L`; $('ss-weight').textContent = `${K.toFixed(1)} kg`;
    $('ss-ok').textContent = ok; $('ss-warn').textContent = w; $('ss-exc').textContent = x;
    $('member-count').textContent = `${N} member${N!==1?'s':''}`;
}

// ── Add Member Dialog ──
async function showAddMember() {
    if (!project) return;
    const cats = steelTypes.map(st => `<button class="section-cat-btn" data-tid="${st.id}">${st.abbrev} (${st.section_count})</button>`).join('');
    const m = modal(`
        <h2>Add Steel Member</h2>
        <div class="form-group"><label>Search or browse</label><input type="text" id="dlg-search" placeholder="Type section e.g. 254x102" autofocus style="width:100%"></div>
        <div class="section-categories">${cats}</div>
        <div id="dlg-results" style="max-height:180px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;margin-bottom:10px"></div>
        <div id="dlg-sel" style="display:none;padding:8px 10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;margin-bottom:10px">
            <strong id="dlg-sel-name"></strong> <span id="dlg-sel-type" style="color:#666"></span></div>
        <div class="form-group"><label>Exposure</label><select id="dlg-exp" disabled style="width:100%"><option>Select section first</option></select></div>
        <div class="form-group"><label>Member Type</label><select id="dlg-mtype" style="width:100%"><option value="beam">Beam</option><option value="column">Column</option><option value="bracing">Bracing</option></select></div>
        <div style="display:flex;gap:10px">
            <div class="form-group" style="flex:1"><label>Qty</label><input type="number" id="dlg-qty" value="1" min="1"></div>
            <div class="form-group" style="flex:1"><label>Length (m)</label><input type="number" id="dlg-len" value="0" step="0.1"></div>
        </div>
        <div style="display:flex;gap:10px">
            <div class="form-group" style="flex:1"><label>Zone</label><input type="text" id="dlg-zone"></div>
            <div class="form-group" style="flex:1"><label>Level</label><input type="text" id="dlg-level"></div>
        </div>
        <div class="btn-row"><button class="btn btn-secondary" id="dlg-cancel">Cancel</button><button class="btn btn-primary" id="dlg-add" disabled>Add Member</button></div>
    `);

    let selSection = null, searchTo = null;

    // Category browse
    m.querySelectorAll('.section-cat-btn').forEach(btn => {
        btn.onclick = async () => {
            m.querySelectorAll('.section-cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active'); $('dlg-search').value = '';
            const secs = await api.getSectionsByType(btn.dataset.tid, project.origin_id);
            renderResults(secs);
        };
    });

    // Search
    $('dlg-search').oninput = () => {
        clearTimeout(searchTo); m.querySelectorAll('.section-cat-btn').forEach(b => b.classList.remove('active'));
        const q = $('dlg-search').value.trim(); if (q.length < 2) { $('dlg-results').innerHTML = ''; return; }
        searchTo = setTimeout(async () => renderResults(await api.searchSections(q, project.origin_id)), 150);
    };

    function renderResults(secs) {
        $('dlg-results').innerHTML = secs.length ? secs.map(s => `<div class="sr" data-id="${s.id}" style="padding:5px 8px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:12px;display:flex;justify-content:space-between">
            <span><strong>${s.serial_size}</strong> <span style="color:#666">${s.steel_type_abbrev}</span></span>
            <span style="color:#999">${s.weight?s.weight+'kg/m':''}</span></div>`).join('')
            : '<div style="padding:10px;color:#999;text-align:center">No results</div>';

        $('dlg-results').querySelectorAll('.sr').forEach(el => {
            const sec = secs.find(s => String(s.id) === el.dataset.id);
            el.onmouseenter = () => el.style.background = '#f5f5f5';
            el.onmouseleave = () => el.style.background = '';
            el.onclick = async () => {
                selSection = sec; $('dlg-sel-name').textContent = sec.serial_size;
                $('dlg-sel-type').textContent = `${sec.steel_type_name} (${sec.steel_type_abbrev})`;
                $('dlg-sel').style.display = 'block'; $('dlg-results').innerHTML = '';
                const profs = await api.getSectionProfiles(sec.id, project.product_id);
                $('dlg-exp').disabled = false;
                $('dlg-exp').innerHTML = profs.map(p => `<option value="${p.name}">${p.description}</option>`).join('');
                const defs = { 7: 'U1', 8: 'U4', 3: 'C1', 4: 'R1', 5: 'S1', 1: 'A5', 2: 'F1', 6: 'T1' };
                const d = defs[sec.steel_type_id];
                if (d && profs.some(p => p.name === d)) $('dlg-exp').value = d;
                $('dlg-add').disabled = false; $('dlg-qty').focus();
            };
        });
    }

    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-add').onclick = async () => {
        if (!selSection) return;
        try {
            const member = await api.addMember(project.id, {
                section_id: selSection.id, hp_profile_name: $('dlg-exp').value,
                member_type: $('dlg-mtype').value,
                quantity: +$('dlg-qty').value || 1, length_m: +$('dlg-len').value || 0,
                zone: $('dlg-zone').value.trim(), level: $('dlg-level').value.trim(),
            });
            if (member && memberGridApi) {
                memberGridApi.applyTransaction({ add: [member] }); updateSummary();
                toast(`Added ${selSection.serial_size} - DFT: ${member.dft_mm ? (member.dft_mm*1000).toFixed(0)+'um' : 'N/A'}`);
            }
            m.remove();
        } catch (e) { toast(e.message, 'error'); }
    };
    $('dlg-level').onkeydown = e => { if (e.key === 'Enter') $('dlg-add').click(); };
}

// ── Product Compare Panel ──
async function showCompare(memberData) {
    if (!project || !memberData.section_id) return;
    $('product-panel').style.display = 'flex';
    $('product-panel-content').innerHTML = '<p style="color:#999;font-size:12px">Loading...</p>';

    try {
        const frId = memberData.fire_rating_id || project.fire_rating_id;
        const ftId = memberData.failure_temp_id || project.failure_temp_id;
        const r = await fetch('/api/dft/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ section_id: memberData.section_id, hp_profile_name: memberData.hp_profile_name,
                fire_rating_id: frId, failure_temp_id: ftId }) }).then(r => r.json());

        const frName = fireRatings.find(f => f.id === frId)?.description || '';
        const ftName = failureTemps.find(f => f.id === ftId)?.description || '';

        let html = `<div style="margin-bottom:10px;font-size:12px;color:#666;line-height:1.5">
            <strong>${memberData.section_name}</strong> - ${memberData.hp_profile_name}<br>
            Hp/A: ${memberData.hp_over_a ? Math.round(memberData.hp_over_a) : 'N/A'} | ${frName} | ${ftName}<br>
            <strong>${r.products_with_coverage}/${r.total_products}</strong> products available</div>`;

        r.all_results.forEach((p, i) => {
            const ok = p.status === 'ok';
            const isBest = ok && i === 0;
            html += `<div class="product-card ${isBest ? 'best' : ''} ${ok ? '' : 'no-coverage'}">
                <div class="pc-top">
                    <span class="pc-name">${p.product_name.replace('Nullifire ', '')}${isBest ? ' ★' : ''}</span>
                    <span class="pc-badge ${ok ? 'ok' : 'no-data'}">${ok ? 'Available' : p.status.replace(/_/g, ' ')}</span>
                </div>
                ${ok ? `<div class="pc-dft">${p.dft_mm.toFixed(3)} mm <span class="pc-dft-um">(${Math.round(p.dft_mm*1000)} um)</span></div>
                    <button class="btn btn-sm ${isBest ? 'btn-primary' : 'btn-secondary'} btn-assign" data-pid="${p.product_id}" data-mid="${memberData.id}">
                        ${isBest ? 'Assign (Best)' : 'Assign'}</button>` : ''}
                ${!ok && p.error ? `<div style="font-size:10px;color:#999;margin-top:4px">${p.error}</div>` : ''}
            </div>`;
        });

        $('product-panel-content').innerHTML = html;

        // Assign buttons
        $('product-panel-content').querySelectorAll('.btn-assign').forEach(btn => {
            btn.onclick = async () => {
                const updated = await api.updateMember(project.id, btn.dataset.mid, { product_id: +btn.dataset.pid });
                if (updated && memberGridApi) {
                    memberGridApi.applyTransaction({ update: [updated] }); updateSummary();
                    toast(`Assigned ${products.find(p => p.id === +btn.dataset.pid)?.name || 'product'}`);
                    $('product-panel').style.display = 'none';
                }
            };
        });
    } catch (e) { $('product-panel-content').innerHTML = `<p style="color:var(--status-red)">${e.message}</p>`; }
}

// ── Import ──
async function showImport() {
    if (!project) return;
    const m = modal(`
        <h2>Import Steel Schedule</h2>
        <div class="form-group"><label>Upload CSV or Excel</label><input type="file" id="dlg-file" accept=".csv,.xlsx,.xls"></div>
        <div id="dlg-preview" style="display:none">
            <div id="dlg-info" style="margin-bottom:6px;font-size:11px;color:#666"></div>
            <div id="dlg-map" style="margin-bottom:8px"></div>
            <div id="dlg-sample" style="max-height:120px;overflow:auto;font-size:10px;border:1px solid #ddd;border-radius:4px"></div>
        </div>
        <div class="btn-row"><button class="btn btn-secondary" id="dlg-cancel">Cancel</button><button class="btn btn-primary" id="dlg-go" disabled>Import</button></div>
    `);
    let parsed = null;

    $('dlg-file').onchange = async e => {
        const file = e.target.files[0]; if (!file) return;
        const fd = new FormData(); fd.append('file', file);
        const resp = await fetch('/api/import/parse', { method: 'POST', body: fd });
        parsed = await resp.json(); if (parsed.error) { toast(parsed.error, 'error'); return; }
        $('dlg-preview').style.display = 'block';
        $('dlg-info').textContent = `${parsed.total_rows} rows, ${parsed.headers.length} columns`;
        const fields = ['section', 'quantity', 'length', 'zone', 'level'];
        $('dlg-map').innerHTML = '<label style="font-size:11px;font-weight:600">Column Mapping</label>' +
            fields.map(f => `<div style="display:flex;gap:6px;align-items:center;margin:3px 0">
                <span style="width:55px;font-size:11px">${f}</span>
                <select data-f="${f}" style="flex:1;font-size:11px;padding:2px 4px">
                    <option value="">Skip</option>${parsed.headers.map((h,i) => `<option value="${i}"${parsed.suggested_mapping[f]===i?' selected':''}>${h}</option>`).join('')}
                </select></div>`).join('');
        $('dlg-sample').innerHTML = `<table style="width:100%;border-collapse:collapse"><tr>${parsed.headers.map(h => `<th style="padding:2px 4px;border-bottom:1px solid #ddd;font-size:10px">${h}</th>`).join('')}</tr>${parsed.sample_rows.slice(0,3).map(r => `<tr>${r.map(c => `<td style="padding:2px 4px;font-size:10px">${c}</td>`).join('')}</tr>`).join('')}</table>`;
        $('dlg-go').disabled = false;
    };

    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-go').onclick = async () => {
        if (!parsed) return;
        const map = {};
        m.querySelectorAll('[data-f]').forEach(s => { if (s.value !== '') map[s.dataset.f] = +s.value; });
        if (map.section === undefined) { toast('Map Section column', 'error'); return; }

        const members = [];
        for (const row of parsed.all_rows) {
            const q = row[map.section]; if (!q) continue;
            const results = await api.searchSections(q, project.origin_id);
            if (!results.length) continue;
            members.push({ section_id: results[0].id,
                quantity: map.quantity !== undefined ? +row[map.quantity] || 1 : 1,
                length_m: map.length !== undefined ? +row[map.length] || 0 : 0,
                zone: map.zone !== undefined ? row[map.zone] || '' : '',
                level: map.level !== undefined ? row[map.level] || '' : '' });
        }
        if (!members.length) { toast('No valid members', 'error'); return; }
        const result = await api.importMembers(project.id, members);
        m.remove();
        project = await api.getProject(project.id);
        memberGridApi.setGridOption('rowData', project.members);
        updateSummary(); toast(`Imported ${result.added_count} members`);
    };
}

import { api } from './api.js';

// ── State ──────────────────────────────────────────
let project = null;
let gridApi = null;
let products = [];
let fireRatings = [];
let failureTemps = [];
let origins = [];
let steelTypes = [];

// ── Init ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    // Load reference data
    products = await api.getProducts();
    origins = await api.getOrigins();
    steelTypes = await api.getSteelTypes();

    // Populate sidebar dropdowns
    fillSelect('sel-fire-rating', []);
    fillSelect('sel-failure-temp', []);
    fillSelect('sel-origin', origins.map(o => ({ v: o.id, t: `${o.code} — ${o.description}` })));

    // Button handlers
    $('btn-new-project').onclick = showNewProjectDialog;
    $('btn-load-project').onclick = showLoadDialog;
    $('btn-welcome-new').onclick = showNewProjectDialog;
    $('btn-welcome-load').onclick = showLoadDialog;
    $('btn-add-member').onclick = showAddMemberDialog;
    $('btn-import').onclick = showImportDialog;
    $('btn-delete-selected').onclick = deleteSelected;
    $('btn-export-excel').onclick = () => { if (project) window.open(api.exportExcelUrl(project.id)); };
    $('btn-export-pdf').onclick = () => { if (project) window.open(api.exportPdfUrl(project.id)); };
    $('btn-add-gridline').onclick = showAddGridlineDialog;
    $('btn-add-level').onclick = showAddLevelDialog;
    $('btn-close-product-panel').onclick = () => $('product-panel').style.display = 'none';

    // Sidebar change handlers
    $('sel-fire-rating').onchange = async () => {
        await cascadeFailureTemps();
        await saveProjectDefaults();
    };
    $('sel-failure-temp').onchange = saveProjectDefaults;
    $('sel-origin').onchange = saveProjectDefaults;
});

// ── Helpers ────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function fillSelect(id, opts, selectedVal) {
    const sel = $(id);
    sel.innerHTML = opts.map(o =>
        `<option value="${o.v}" ${String(o.v) === String(selectedVal) ? 'selected' : ''}>${o.t}</option>`
    ).join('');
}

function showToast(msg, type = 'success') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

function modal(html) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="modal">${html}</div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    return overlay;
}

// ── Project Management ─────────────────────────────
async function showNewProjectDialog() {
    const m = modal(`
        <h2>New Project</h2>
        <div class="form-group"><label>Project Name *</label><input type="text" id="dlg-name" autofocus></div>
        <div class="form-group"><label>Client</label><input type="text" id="dlg-client"></div>
        <div class="form-group"><label>Reference</label><input type="text" id="dlg-ref"></div>
        <div class="form-group"><label>Default Fire Rating</label>
            <select id="dlg-fr">${products.length ? '' : '<option>Loading...</option>'}</select></div>
        <div class="form-group"><label>Default Failure Temp</label>
            <select id="dlg-ft"></select></div>
        <div class="btn-row">
            <button class="btn btn-secondary" id="dlg-cancel">Cancel</button>
            <button class="btn btn-primary" id="dlg-create">Create Project</button>
        </div>
    `);

    // Use first product to populate fire ratings
    if (products.length) {
        const frs = await api.getProductFireRatings(products[0].id);
        fillSelect('dlg-fr', frs.map(f => ({ v: f.id, t: f.description })), 3);
        const fts = await api.getProductFailureTemps(products[0].id, 3);
        fillSelect('dlg-ft', fts.map(f => ({ v: f.id, t: f.description })), 7);
        $('dlg-fr').onchange = async () => {
            const fts2 = await api.getProductFailureTemps(products[0].id, $('dlg-fr').value);
            fillSelect('dlg-ft', fts2.map(f => ({ v: f.id, t: f.description })));
        };
    }

    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-create').onclick = async () => {
        const name = $('dlg-name').value.trim();
        if (!name) { $('dlg-name').focus(); return; }
        const p = await api.createProject({
            name,
            client: $('dlg-client').value.trim(),
            reference: $('dlg-ref').value.trim(),
            product_id: products[0]?.id || 284,
            fire_rating_id: parseInt($('dlg-fr').value) || 3,
            failure_temp_id: parseInt($('dlg-ft').value) || 7,
            origin_id: 1,
        });
        m.remove();
        await loadProject(p.id);
        showToast('Project created');
    };
    $('dlg-name').onkeydown = (e) => { if (e.key === 'Enter') $('dlg-create').click(); };
}

async function showLoadDialog() {
    const list = await api.listProjects();
    if (!list.length) { showToast('No saved projects', 'error'); return; }
    const m = modal(`
        <h2>Load Project</h2>
        <div style="max-height:300px;overflow-y:auto">
            ${list.map(p => `<div class="project-list-item" data-id="${p.id}">
                <strong>${p.name}</strong>${p.client ? ` — ${p.client}` : ''}
                <span style="float:right;font-size:11px;color:#999">${(p.updated_at || '').substring(0, 10)}</span>
            </div>`).join('')}
        </div>
        <div class="btn-row"><button class="btn btn-secondary" id="dlg-cancel">Cancel</button></div>
    `);
    $('dlg-cancel').onclick = () => m.remove();
    m.querySelectorAll('.project-list-item').forEach(el => {
        el.style.cssText = 'padding:10px 12px;cursor:pointer;border-bottom:1px solid #eee';
        el.onmouseenter = () => el.style.background = '#f5f5f5';
        el.onmouseleave = () => el.style.background = '';
        el.onclick = async () => { m.remove(); await loadProject(el.dataset.id); };
    });
}

async function loadProject(projectId) {
    project = await api.getProject(projectId);
    if (!project) return;

    // Show work area, hide welcome
    $('welcome-screen').style.display = 'none';
    $('work-area').style.display = 'flex';
    $('project-settings').style.display = 'block';
    $('btn-delete-selected').disabled = false;

    // Update header
    $('header-project-name').textContent = project.name;
    $('inp-project-name').value = project.name;
    $('inp-project-client').value = project.client || '';

    // Populate fire rating and temp dropdowns
    // Use first product for available ratings (all products share similar ratings)
    fireRatings = await api.getProductFireRatings(products[0]?.id || project.product_id);
    fillSelect('sel-fire-rating', fireRatings.map(f => ({ v: f.id, t: f.description })), project.fire_rating_id);

    await cascadeFailureTemps();
    fillSelect('sel-origin', origins.map(o => ({ v: o.id, t: `${o.code} — ${o.description}` })), project.origin_id);

    // Load grid & levels
    await refreshGridlines();
    await refreshLevels();

    // Init AG Grid
    initMemberGrid();

    // Load summary
    updateSummary();
}

async function cascadeFailureTemps() {
    const frId = $('sel-fire-rating').value;
    const pid = products[0]?.id || project?.product_id;
    if (!frId || !pid) return;
    failureTemps = await api.getProductFailureTemps(pid, frId);
    fillSelect('sel-failure-temp', failureTemps.map(f => ({ v: f.id, t: f.description })),
        project?.failure_temp_id);
}

async function saveProjectDefaults() {
    if (!project) return;
    const data = {
        fire_rating_id: parseInt($('sel-fire-rating').value),
        failure_temp_id: parseInt($('sel-failure-temp').value),
        origin_id: parseInt($('sel-origin').value),
    };
    if (isNaN(data.fire_rating_id) || isNaN(data.failure_temp_id)) return;
    project = await api.updateProject(project.id, data);
    // Refresh grid with recalculated members
    if (gridApi && project.members) {
        gridApi.setGridOption('rowData', project.members);
        updateSummary();
    }
}

// ── AG Grid ────────────────────────────────────────
const STATUS_COLORS = {
    ok: '#22c55e', warning: '#f59e0b', exceeds: '#ef4444', pending: '#9ca3af',
};

function initMemberGrid() {
    const gridDiv = $('member-grid');

    const colDefs = [
        { headerName: '', checkboxSelection: true, headerCheckboxSelection: true, width: 40, pinned: 'left', suppressMenu: true },
        { field: 'section_name', headerName: 'Section', width: 150 },
        { field: 'steel_type', headerName: 'Type', width: 55 },
        { field: 'hp_profile_name', headerName: 'Exposure', width: 80 },
        { field: 'hp_over_a', headerName: 'Hp/A', width: 65, valueFormatter: p => p.value != null ? Math.round(p.value) : '' },
        { field: 'dft_mm', headerName: 'DFT (mm)', width: 120,
            valueFormatter: p => p.value != null ? `${p.value.toFixed(3)} (${Math.round(p.value * 1000)}µm)` : '—' },
        { field: 'quantity', headerName: 'Qty', width: 55, editable: true, cellEditor: 'agNumberCellEditor' },
        { field: 'length_m', headerName: 'Length (m)', width: 85, editable: true, cellEditor: 'agNumberCellEditor',
            valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'surface_area_m2', headerName: 'Area (m²)', width: 85,
            valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'volume_litres', headerName: 'Litres', width: 75,
            valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
        { field: 'weight_kg', headerName: 'Kg', width: 65,
            valueFormatter: p => p.value != null ? p.value.toFixed(1) : '' },
        { field: 'zone', headerName: 'Zone', width: 90, editable: true },
        { field: 'level', headerName: 'Level', width: 75, editable: true },
        { field: 'status', headerName: '', width: 40, suppressMenu: true,
            cellRenderer: p => {
                const c = STATUS_COLORS[p.value] || STATUS_COLORS.pending;
                return `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${c}" title="${p.value || ''}"></span>`;
            }
        },
        { headerName: '', width: 70, suppressMenu: true,
            cellRenderer: p => `<button class="btn btn-sm btn-secondary" style="padding:2px 6px;font-size:11px" data-action="compare">Compare</button>`,
            onCellClicked: (e) => {
                if (e.event.target.dataset.action === 'compare') showProductComparison(e.data);
            }
        },
    ];

    const gridOptions = {
        columnDefs: colDefs,
        rowData: project?.members || [],
        rowSelection: 'multiple',
        enableCellChangeFlash: true,
        animateRows: true,
        defaultColDef: { resizable: true, sortable: true, filter: true },
        getRowId: p => p.data.id,
        onCellValueChanged: onCellEdit,
        onSelectionChanged: () => {
            const count = gridApi.getSelectedRows().length;
            $('btn-delete-selected').disabled = count === 0;
            $('btn-delete-selected').textContent = count > 0 ? `Delete Selected (${count})` : 'Delete Selected';
        },
    };

    if (gridApi) gridApi.destroy();
    gridApi = agGrid.createGrid(gridDiv, gridOptions);
}

async function onCellEdit(event) {
    const { data, colDef, newValue, oldValue } = event;
    if (!data.id || !project || newValue === oldValue) return;
    try {
        const updated = await api.updateMember(project.id, data.id, { [colDef.field]: newValue });
        if (updated?.id) {
            event.api.applyTransaction({ update: [updated] });
            updateSummary();
        }
    } catch (e) {
        showToast(`Update failed: ${e.message}`, 'error');
    }
}

async function deleteSelected() {
    if (!gridApi || !project) return;
    const selected = gridApi.getSelectedRows();
    if (!selected.length) return;
    await api.batchDeleteMembers(project.id, selected.map(r => r.id));
    gridApi.applyTransaction({ remove: selected });
    updateSummary();
    showToast(`Deleted ${selected.length} member(s)`);
}

function updateSummary() {
    let litres = 0, kg = 0, area = 0, count = 0, ok = 0, warn = 0, exc = 0;
    if (gridApi) {
        gridApi.forEachNode(n => {
            const d = n.data;
            litres += d.volume_litres || 0;
            kg += d.weight_kg || 0;
            area += d.surface_area_m2 || 0;
            count++;
            if (d.status === 'ok') ok++;
            else if (d.status === 'warning') warn++;
            else if (d.status === 'exceeds') exc++;
        });
    }
    $('sum-count').textContent = count;
    $('sum-area').textContent = `${area.toFixed(1)} m²`;
    $('sum-litres').textContent = `${litres.toFixed(1)} L`;
    $('sum-weight').textContent = `${kg.toFixed(1)} kg`;
    $('sum-ok').textContent = ok;
    $('sum-warning').textContent = warn;
    $('sum-exceeds').textContent = exc;
    $('member-count').textContent = `${count} member${count !== 1 ? 's' : ''}`;
}

// ── Add Member Dialog ──────────────────────────────
async function showAddMemberDialog() {
    if (!project) return;

    const catButtons = steelTypes.map(st =>
        `<button class="section-cat-btn" data-type-id="${st.id}">${st.abbrev} (${st.section_count})</button>`
    ).join('');

    const m = modal(`
        <h2>Add Steel Member</h2>
        <div class="form-group">
            <label>Search or browse sections</label>
            <input type="text" id="dlg-search" placeholder="Type section size e.g. 254x102 or UB 305" autofocus style="width:100%">
        </div>
        <div class="section-categories" id="dlg-categories">${catButtons}</div>
        <div id="dlg-results" style="max-height:200px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;margin-bottom:12px"></div>
        <div id="dlg-selected-info" style="display:none;padding:8px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;margin-bottom:12px">
            <strong id="dlg-sel-name"></strong> <span id="dlg-sel-type" style="color:#666"></span>
        </div>
        <div class="form-group">
            <label>Exposure</label>
            <select id="dlg-exposure" style="width:100%" disabled><option>Select section first</option></select>
        </div>
        <div style="display:flex;gap:12px">
            <div class="form-group" style="flex:1"><label>Quantity</label><input type="number" id="dlg-qty" value="1" min="1"></div>
            <div class="form-group" style="flex:1"><label>Length (m)</label><input type="number" id="dlg-length" value="0" step="0.1" min="0"></div>
        </div>
        <div style="display:flex;gap:12px">
            <div class="form-group" style="flex:1"><label>Zone</label><input type="text" id="dlg-zone" placeholder="Optional"></div>
            <div class="form-group" style="flex:1"><label>Level</label><input type="text" id="dlg-level" placeholder="Optional"></div>
        </div>
        <div class="btn-row">
            <button class="btn btn-secondary" id="dlg-cancel">Cancel</button>
            <button class="btn btn-primary" id="dlg-add" disabled>Add Member</button>
        </div>
    `);

    let selectedSection = null;
    let searchTimeout = null;

    // Category buttons
    m.querySelectorAll('.section-cat-btn').forEach(btn => {
        btn.onclick = async () => {
            m.querySelectorAll('.section-cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            $('dlg-search').value = '';
            const sections = await api.getSectionsByType(btn.dataset.typeId, project.origin_id);
            renderSectionResults(sections, m);
        };
    });

    // Search
    $('dlg-search').oninput = () => {
        clearTimeout(searchTimeout);
        m.querySelectorAll('.section-cat-btn').forEach(b => b.classList.remove('active'));
        const q = $('dlg-search').value.trim();
        if (q.length < 2) { $('dlg-results').innerHTML = ''; return; }
        searchTimeout = setTimeout(async () => {
            const results = await api.searchSections(q, project.origin_id);
            renderSectionResults(results, m);
        }, 150);
    };

    function renderSectionResults(sections, modal) {
        $('dlg-results').innerHTML = sections.length
            ? sections.map(s => `<div class="search-result" data-id="${s.id}" style="padding:6px 10px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px;display:flex;justify-content:space-between">
                <span><strong>${s.serial_size}</strong> <span style="color:#666">${s.steel_type_abbrev}</span></span>
                <span style="color:#999">${s.weight ? s.weight + 'kg/m' : ''} ${s.depth ? s.depth + 'mm' : ''}</span>
            </div>`).join('')
            : '<div style="padding:12px;color:#999;text-align:center">No sections found</div>';

        $('dlg-results').querySelectorAll('.search-result').forEach(el => {
            const section = sections.find(s => String(s.id) === el.dataset.id);
            el.onmouseenter = () => el.style.background = '#f5f5f5';
            el.onmouseleave = () => el.style.background = '';
            el.onclick = async () => {
                selectedSection = section;
                $('dlg-sel-name').textContent = section.serial_size;
                $('dlg-sel-type').textContent = `${section.steel_type_name} (${section.steel_type_abbrev})`;
                $('dlg-selected-info').style.display = 'block';
                $('dlg-results').innerHTML = '';

                // Load profiles
                const profiles = await api.getSectionProfiles(section.id, project.product_id);
                $('dlg-exposure').disabled = false;
                $('dlg-exposure').innerHTML = profiles.map(p =>
                    `<option value="${p.name}">${p.description} (${p.abbreviation})</option>`
                ).join('');

                // Auto-default: UB→U1 (3-sided), UC→U4 (4-sided)
                const defaults = { 7: 'U1', 8: 'U4', 3: 'C1', 4: 'R1', 5: 'S1' };
                const def = defaults[section.steel_type_id];
                if (def && profiles.some(p => p.name === def)) $('dlg-exposure').value = def;

                $('dlg-add').disabled = false;
                $('dlg-qty').focus();
            };
        });
    }

    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-add').onclick = async () => {
        if (!selectedSection) return;
        const profile = $('dlg-exposure').value;
        if (!profile) return;

        try {
            const member = await api.addMember(project.id, {
                section_id: selectedSection.id,
                hp_profile_name: profile,
                quantity: parseInt($('dlg-qty').value) || 1,
                length_m: parseFloat($('dlg-length').value) || 0,
                zone: $('dlg-zone').value.trim(),
                level: $('dlg-level').value.trim(),
            });
            if (member && gridApi) {
                gridApi.applyTransaction({ add: [member] });
                updateSummary();
                showToast(`Added ${selectedSection.serial_size} — DFT: ${member.dft_mm ? (member.dft_mm * 1000).toFixed(0) + 'µm' : 'N/A'}`);
            }
            m.remove();
        } catch (e) {
            showToast(`Failed: ${e.message}`, 'error');
        }
    };

    // Enter on level field triggers add
    $('dlg-level').onkeydown = (e) => { if (e.key === 'Enter') $('dlg-add').click(); };
    $('dlg-qty').onkeydown = (e) => { if (e.key === 'Enter') $('dlg-length').focus(); };
}

// ── Product Comparison Panel ───────────────────────
async function showProductComparison(memberData) {
    if (!project || !memberData.section_id || !memberData.hp_profile_name) return;

    $('product-panel').style.display = 'flex';
    $('product-panel-content').innerHTML = '<p style="color:#999">Loading...</p>';

    try {
        const result = await api.health(); // verify API first
        const comparison = await fetch('/api/dft/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: memberData.section_id,
                hp_profile_name: memberData.hp_profile_name,
                fire_rating_id: project.fire_rating_id,
                failure_temp_id: project.failure_temp_id,
            }),
        }).then(r => r.json());

        let html = `<div style="margin-bottom:12px;font-size:12px;color:#666">
            <strong>${memberData.section_name}</strong> — ${memberData.hp_profile_name}<br>
            Hp/A: ${memberData.hp_over_a ? Math.round(memberData.hp_over_a) + ' m⁻¹' : 'N/A'}<br>
            ${comparison.products_with_coverage}/${comparison.total_products} products can cover this member
        </div>`;

        for (const p of comparison.all_results) {
            const ok = p.status === 'ok';
            html += `<div class="product-card ${ok ? '' : 'no-coverage'}">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span class="product-name">${p.product_name}</span>
                    <span class="product-status ${ok ? 'ok' : 'no-data'}">${ok ? 'Available' : p.status}</span>
                </div>
                ${ok ? `<div class="product-dft">${p.dft_mm.toFixed(3)} mm <span class="product-dft-um">(${Math.round(p.dft_mm * 1000)} µm)</span></div>` : ''}
                ${!ok && p.error ? `<div style="font-size:11px;color:#999;margin-top:4px">${p.error}</div>` : ''}
            </div>`;
        }

        $('product-panel-content').innerHTML = html;
    } catch (e) {
        $('product-panel-content').innerHTML = `<p style="color:var(--status-red)">Error: ${e.message}</p>`;
    }
}

// ── Grid & Levels ──────────────────────────────────
async function refreshGridlines() {
    if (!project) return;
    const gridlines = await api.getGridlines(project.id);
    const list = $('gridline-list');
    list.innerHTML = gridlines.length
        ? gridlines.map(g => `<div class="item-list-item">
            <span><span class="item-name">${g.name}</span> <span class="item-detail">${g.direction === 'x' ? '→' : '↑'} ${g.position}m</span></span>
            <button class="btn-delete-item" data-id="${g.id}">×</button>
        </div>`).join('')
        : '<div style="padding:4px;color:#999;font-size:11px">No gridlines defined</div>';

    list.querySelectorAll('.btn-delete-item').forEach(btn => {
        btn.onclick = async () => {
            await api.deleteGridline(project.id, btn.dataset.id);
            await refreshGridlines();
        };
    });
}

async function refreshLevels() {
    if (!project) return;
    const levels = await api.getLevels(project.id);
    const list = $('level-list');
    list.innerHTML = levels.length
        ? levels.map(l => `<div class="item-list-item">
            <span><span class="item-name">${l.name}</span> <span class="item-detail">+${l.height}m</span></span>
            <button class="btn-delete-item" data-id="${l.id}">×</button>
        </div>`).join('')
        : '<div style="padding:4px;color:#999;font-size:11px">No levels defined</div>';

    list.querySelectorAll('.btn-delete-item').forEach(btn => {
        btn.onclick = async () => {
            await api.deleteLevel(project.id, btn.dataset.id);
            await refreshLevels();
        };
    });
}

function showAddGridlineDialog() {
    if (!project) return;
    const m = modal(`
        <h2>Add Gridline</h2>
        <div class="form-group"><label>Direction</label>
            <select id="dlg-dir"><option value="x">X (horizontal →)</option><option value="y">Y (vertical ↑)</option></select></div>
        <div class="form-group"><label>Name (e.g. A, B, 1, 2)</label><input type="text" id="dlg-gl-name" autofocus></div>
        <div class="form-group"><label>Position (m)</label><input type="number" id="dlg-gl-pos" step="0.1" value="0"></div>
        <div class="btn-row">
            <button class="btn btn-secondary" id="dlg-cancel">Cancel</button>
            <button class="btn btn-primary" id="dlg-confirm">Add</button>
        </div>
    `);
    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-confirm').onclick = async () => {
        const name = $('dlg-gl-name').value.trim();
        if (!name) return;
        await api.addGridline(project.id, {
            direction: $('dlg-dir').value,
            name,
            position: parseFloat($('dlg-gl-pos').value) || 0,
        });
        m.remove();
        await refreshGridlines();
        showToast(`Gridline ${name} added`);
    };
    $('dlg-gl-name').onkeydown = (e) => { if (e.key === 'Enter') $('dlg-confirm').click(); };
}

function showAddLevelDialog() {
    if (!project) return;
    const m = modal(`
        <h2>Add Level</h2>
        <div class="form-group"><label>Name (e.g. Ground, First, Roof)</label><input type="text" id="dlg-lv-name" autofocus></div>
        <div class="form-group"><label>Height (m)</label><input type="number" id="dlg-lv-height" step="0.1" value="0"></div>
        <div class="btn-row">
            <button class="btn btn-secondary" id="dlg-cancel">Cancel</button>
            <button class="btn btn-primary" id="dlg-confirm">Add</button>
        </div>
    `);
    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-confirm').onclick = async () => {
        const name = $('dlg-lv-name').value.trim();
        if (!name) return;
        await api.addLevel(project.id, {
            name,
            height: parseFloat($('dlg-lv-height').value) || 0,
        });
        m.remove();
        await refreshLevels();
        showToast(`Level ${name} added`);
    };
    $('dlg-lv-name').onkeydown = (e) => { if (e.key === 'Enter') $('dlg-confirm').click(); };
}

// ── Import ─────────────────────────────────────────
function showImportDialog() {
    if (!project) return;
    const m = modal(`
        <h2>Import Steel Schedule</h2>
        <div class="form-group">
            <label>Upload CSV or Excel file</label>
            <input type="file" id="dlg-file" accept=".csv,.xlsx,.xls" style="width:100%">
        </div>
        <div id="dlg-import-preview" style="display:none">
            <div id="dlg-import-info" style="margin-bottom:8px;font-size:12px;color:#666"></div>
            <div id="dlg-mapping" style="margin-bottom:12px"></div>
            <div id="dlg-import-sample" style="max-height:150px;overflow:auto;font-size:11px;border:1px solid #ddd;border-radius:4px"></div>
        </div>
        <div class="btn-row">
            <button class="btn btn-secondary" id="dlg-cancel">Cancel</button>
            <button class="btn btn-primary" id="dlg-import" disabled>Import</button>
        </div>
    `);

    let parsedData = null;
    let currentMapping = {};

    $('dlg-file').onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/import/parse', { method: 'POST', body: formData });
            parsedData = await resp.json();
            if (parsedData.error) { showToast(parsedData.error, 'error'); return; }

            currentMapping = parsedData.suggested_mapping || {};
            $('dlg-import-preview').style.display = 'block';
            $('dlg-import-info').textContent = `Found ${parsedData.total_rows} rows, ${parsedData.headers.length} columns`;

            // Show mapping UI
            const fields = ['section', 'quantity', 'length', 'zone', 'level'];
            $('dlg-mapping').innerHTML = '<label style="font-size:12px;font-weight:600">Column Mapping</label>' +
                fields.map(f => {
                    const opts = parsedData.headers.map((h, i) =>
                        `<option value="${i}" ${currentMapping[f] === i ? 'selected' : ''}>${h}</option>`
                    ).join('');
                    return `<div style="display:flex;align-items:center;gap:8px;margin:4px 0">
                        <span style="width:60px;font-size:12px;font-weight:500">${f}</span>
                        <select data-field="${f}" style="flex:1;font-size:12px;padding:3px 6px">
                            <option value="">— Skip —</option>${opts}
                        </select>
                    </div>`;
                }).join('');

            // Sample data preview
            const sample = parsedData.sample_rows.slice(0, 3);
            $('dlg-import-sample').innerHTML = `<table style="width:100%;border-collapse:collapse">
                <tr>${parsedData.headers.map(h => `<th style="padding:3px 6px;border-bottom:1px solid #ddd;font-size:11px;text-align:left">${h}</th>`).join('')}</tr>
                ${sample.map(row => `<tr>${row.map(c => `<td style="padding:2px 6px;border-bottom:1px solid #f0f0f0">${c}</td>`).join('')}</tr>`).join('')}
            </table>`;

            $('dlg-import').disabled = false;
        } catch (e) {
            showToast(`Parse failed: ${e.message}`, 'error');
        }
    };

    $('dlg-cancel').onclick = () => m.remove();
    $('dlg-import').onclick = async () => {
        if (!parsedData) return;

        // Read mapping from dropdowns
        const mapping = {};
        m.querySelectorAll('[data-field]').forEach(sel => {
            if (sel.value !== '') mapping[sel.dataset.field] = parseInt(sel.value);
        });

        const sectionCol = mapping.section;
        if (sectionCol === undefined) { showToast('Map the Section column', 'error'); return; }

        // Build member list from parsed rows
        const members = [];
        for (const row of parsedData.all_rows) {
            const sectionQuery = row[sectionCol];
            if (!sectionQuery) continue;

            // Search for the section
            const results = await api.searchSections(sectionQuery, project.origin_id);
            if (!results.length) continue;

            const section = results[0];
            members.push({
                section_id: section.id,
                quantity: mapping.quantity !== undefined ? parseInt(row[mapping.quantity]) || 1 : 1,
                length_m: mapping.length !== undefined ? parseFloat(row[mapping.length]) || 0 : 0,
                zone: mapping.zone !== undefined ? row[mapping.zone] || '' : '',
                level: mapping.level !== undefined ? row[mapping.level] || '' : '',
            });
        }

        if (!members.length) { showToast('No valid members found', 'error'); return; }

        try {
            const result = await api.importMembers(project.id, members);
            m.remove();
            // Reload project to get all members
            project = await api.getProject(project.id);
            gridApi.setGridOption('rowData', project.members);
            updateSummary();
            showToast(`Imported ${result.added_count} members${result.error_count ? ` (${result.error_count} errors)` : ''}`);
        } catch (e) {
            showToast(`Import failed: ${e.message}`, 'error');
        }
    };
}

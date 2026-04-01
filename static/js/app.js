import { api } from './api.js';
import { initSidebar, onProjectChange, loadProject, getProject } from './sidebar.js';
import * as gridManager from './grid-manager.js';

let currentFireRatings = [];
let currentFailureTemps = [];

async function init() {
    await initSidebar();

    onProjectChange(async (project) => {
        if (!project) return;

        // Fetch options for grid dropdowns
        currentFireRatings = await api.getProductFireRatings(project.product_id);
        currentFailureTemps = await api.getProductFailureTemps(project.product_id, project.fire_rating_id);

        const gridDiv = document.getElementById('member-grid');
        await gridManager.initGrid(gridDiv, project.id, project, currentFireRatings, currentFailureTemps);
        gridManager.updateSummary();

        // Enable toolbar buttons
        document.getElementById('btn-add-member').disabled = false;
        document.getElementById('btn-delete-selected').disabled = false;
    });

    // Toolbar buttons
    document.getElementById('btn-add-member').addEventListener('click', showAddMemberDialog);
    document.getElementById('btn-delete-selected').addEventListener('click', () => gridManager.deleteSelected());

    // Check for health
    try {
        const health = await api.health();
        if (health.status !== 'ok') console.warn('API health check failed:', health);
    } catch (e) {
        console.error('Cannot reach API:', e);
    }
}

async function showAddMemberDialog() {
    const project = getProject();
    if (!project) return;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal" style="min-width:500px">
            <h2>Add Steel Member</h2>
            <div class="form-group">
                <label>Section (type to search)</label>
                <input type="text" id="add-section-search" placeholder="e.g. 254x102 or UB 305" autofocus style="width:100%">
                <div id="add-section-results" style="max-height:200px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;display:none"></div>
            </div>
            <div class="form-group">
                <label>Exposure</label>
                <select id="add-exposure" style="width:100%"><option value="">Select section first</option></select>
            </div>
            <div style="display:flex;gap:12px">
                <div class="form-group" style="flex:1">
                    <label>Quantity</label>
                    <input type="number" id="add-qty" value="1" min="1" style="width:100%">
                </div>
                <div class="form-group" style="flex:1">
                    <label>Length (m)</label>
                    <input type="number" id="add-length" value="0" step="0.1" min="0" style="width:100%">
                </div>
            </div>
            <div style="display:flex;gap:12px">
                <div class="form-group" style="flex:1">
                    <label>Zone</label>
                    <input type="text" id="add-zone" placeholder="Optional" style="width:100%">
                </div>
                <div class="form-group" style="flex:1">
                    <label>Level</label>
                    <input type="text" id="add-level" placeholder="Optional" style="width:100%">
                </div>
            </div>
            <div class="btn-row">
                <button class="btn btn-secondary" id="btn-cancel-add">Cancel</button>
                <button class="btn btn-primary" id="btn-confirm-add" disabled>Add Member</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    let selectedSection = null;
    let searchTimeout = null;
    const searchInput = document.getElementById('add-section-search');
    const resultsDiv = document.getElementById('add-section-results');
    const exposureSelect = document.getElementById('add-exposure');

    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = searchInput.value.trim();
        if (q.length < 2) { resultsDiv.style.display = 'none'; return; }
        searchTimeout = setTimeout(async () => {
            const origin = project.origin_id;
            const results = await api.searchSections(q, origin);
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = results.map(s => `
                <div class="search-result" data-id="${s.id}" style="padding:6px 10px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px">
                    <strong>${s.serial_size}</strong>
                    <span style="color:#666;margin-left:8px">${s.steel_type_abbrev}</span>
                    <span style="color:#999;margin-left:8px">${s.weight || ''}kg/m</span>
                </div>
            `).join('') || '<div style="padding:8px;color:#999">No results</div>';

            resultsDiv.querySelectorAll('.search-result').forEach(el => {
                el.addEventListener('click', async () => {
                    const section = results.find(r => String(r.id) === el.dataset.id);
                    if (!section) return;
                    selectedSection = section;
                    searchInput.value = section.serial_size;
                    resultsDiv.style.display = 'none';

                    // Load profiles
                    const profiles = await api.getSectionProfiles(section.id, project.product_id);
                    exposureSelect.innerHTML = profiles.map(p =>
                        `<option value="${p.name}">${p.description} (${p.abbreviation})</option>`
                    ).join('');

                    // Auto-select default based on steel type
                    const defaultMap = { 7: 'U1', 8: 'U4' }; // UB→3-sided, UC→4-sided
                    const defaultProfile = defaultMap[section.steel_type_id];
                    if (defaultProfile && profiles.some(p => p.name === defaultProfile)) {
                        exposureSelect.value = defaultProfile;
                    }

                    document.getElementById('btn-confirm-add').disabled = false;
                    document.getElementById('add-qty').focus();
                });
                el.addEventListener('mouseenter', () => el.style.background = '#f5f5f5');
                el.addEventListener('mouseleave', () => el.style.background = '');
            });
        }, 150);
    });

    // Keyboard nav in search results
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { overlay.remove(); return; }
        if (e.key === 'Enter' && resultsDiv.style.display === 'block') {
            const first = resultsDiv.querySelector('.search-result');
            if (first) first.click();
        }
    });

    document.getElementById('btn-cancel-add').onclick = () => overlay.remove();
    document.getElementById('btn-confirm-add').onclick = async () => {
        if (!selectedSection) return;
        const profile = exposureSelect.value;
        if (!profile) return;

        await gridManager.addMember(selectedSection.id, profile, {
            quantity: parseInt(document.getElementById('add-qty').value) || 1,
            length_m: parseFloat(document.getElementById('add-length').value) || 0,
            zone: document.getElementById('add-zone').value.trim(),
            level: document.getElementById('add-level').value.trim(),
        });
        overlay.remove();
    };

    // Enter on length field triggers add
    document.getElementById('add-level').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('btn-confirm-add').click();
    });
    document.getElementById('add-length').addEventListener('keydown', (e) => {
        if (e.key === 'Tab' && !e.shiftKey) { /* natural tab to zone */ }
    });
}

document.addEventListener('DOMContentLoaded', init);

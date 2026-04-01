import { api } from './api.js';

let currentProject = null;
let products = [];
let fireRatings = [];
let failureTemps = [];
let origins = [];
let onChangeCallback = null;

export function onProjectChange(cb) { onChangeCallback = cb; }
export function getProject() { return currentProject; }

export async function initSidebar() {
    products = await api.getProducts();
    origins = await api.getOrigins();

    populateSelect('product-select', products.map(p => ({ value: p.id, label: p.name })));
    populateSelect('origin-select', origins.map(o => ({ value: o.id, label: `${o.code} — ${o.description}` })));

    document.getElementById('product-select').addEventListener('change', onProductChange);
    document.getElementById('fire-rating-select').addEventListener('change', onFireRatingChange);
    document.getElementById('failure-temp-select').addEventListener('change', saveProjectSettings);
    document.getElementById('origin-select').addEventListener('change', saveProjectSettings);

    document.getElementById('btn-new-project').addEventListener('click', showNewProjectDialog);
    document.getElementById('btn-load-project').addEventListener('click', showLoadProjectDialog);

    // If product is pre-selected, cascade
    const prodSelect = document.getElementById('product-select');
    if (prodSelect.value) await onProductChange();
}

function populateSelect(id, options, selectedValue) {
    const select = document.getElementById(id);
    select.innerHTML = '';
    for (const opt of options) {
        const el = document.createElement('option');
        el.value = opt.value;
        el.textContent = opt.label;
        if (selectedValue !== undefined && String(opt.value) === String(selectedValue)) el.selected = true;
        select.appendChild(el);
    }
}

async function onProductChange() {
    const productId = document.getElementById('product-select').value;
    if (!productId) return;
    fireRatings = await api.getProductFireRatings(productId);
    populateSelect('fire-rating-select', fireRatings.map(fr => ({ value: fr.id, label: fr.description })),
        currentProject?.fire_rating_id);
    await onFireRatingChange();
}

async function onFireRatingChange() {
    const productId = document.getElementById('product-select').value;
    const frId = document.getElementById('fire-rating-select').value;
    if (!productId || !frId) return;
    failureTemps = await api.getProductFailureTemps(productId, frId);
    populateSelect('failure-temp-select', failureTemps.map(ft => ({ value: ft.id, label: ft.description })),
        currentProject?.failure_temp_id);
    await saveProjectSettings();
}

async function saveProjectSettings() {
    if (!currentProject) return;
    const data = {
        product_id: parseInt(document.getElementById('product-select').value),
        fire_rating_id: parseInt(document.getElementById('fire-rating-select').value),
        failure_temp_id: parseInt(document.getElementById('failure-temp-select').value),
        origin_id: parseInt(document.getElementById('origin-select').value),
    };
    if (isNaN(data.product_id) || isNaN(data.fire_rating_id) || isNaN(data.failure_temp_id)) return;
    currentProject = await api.updateProject(currentProject.id, data);
    if (onChangeCallback) onChangeCallback(currentProject);
}

export async function loadProject(projectId) {
    currentProject = await api.getProject(projectId);
    if (!currentProject) return;

    document.getElementById('project-name-display').textContent = currentProject.name;
    document.getElementById('project-client').value = currentProject.client || '';

    populateSelect('product-select', products.map(p => ({ value: p.id, label: p.name })), currentProject.product_id);
    await onProductChange();
    populateSelect('fire-rating-select', fireRatings.map(fr => ({ value: fr.id, label: fr.description })), currentProject.fire_rating_id);
    await onFireRatingChange();
    populateSelect('failure-temp-select', failureTemps.map(ft => ({ value: ft.id, label: ft.description })), currentProject.failure_temp_id);
    populateSelect('origin-select', origins.map(o => ({ value: o.id, label: `${o.code} — ${o.description}` })), currentProject.origin_id);

    document.querySelector('.header .project-name').textContent = currentProject.name;

    if (onChangeCallback) onChangeCallback(currentProject);
}

function showNewProjectDialog() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <h2>New Project</h2>
            <div class="form-group">
                <label>Project Name</label>
                <input type="text" id="new-project-name" placeholder="Enter project name" autofocus>
            </div>
            <div class="form-group">
                <label>Client</label>
                <input type="text" id="new-project-client" placeholder="Client name (optional)">
            </div>
            <div class="form-group">
                <label>Reference</label>
                <input type="text" id="new-project-ref" placeholder="Reference number (optional)">
            </div>
            <div class="btn-row">
                <button class="btn btn-secondary" id="btn-cancel-new">Cancel</button>
                <button class="btn btn-primary" id="btn-create-project">Create</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById('btn-cancel-new').onclick = () => overlay.remove();
    document.getElementById('btn-create-project').onclick = async () => {
        const name = document.getElementById('new-project-name').value.trim();
        if (!name) return;
        const productId = parseInt(document.getElementById('product-select').value) || products[0]?.id;
        const frId = parseInt(document.getElementById('fire-rating-select').value) || 3;
        const ftId = parseInt(document.getElementById('failure-temp-select').value) || 7;
        const project = await api.createProject({
            name,
            client: document.getElementById('new-project-client').value.trim(),
            reference: document.getElementById('new-project-ref').value.trim(),
            product_id: productId,
            fire_rating_id: frId,
            failure_temp_id: ftId,
            origin_id: parseInt(document.getElementById('origin-select').value) || 1,
        });
        overlay.remove();
        await loadProject(project.id);
    };
    document.getElementById('new-project-name').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('btn-create-project').click();
    });
}

async function showLoadProjectDialog() {
    const projectList = await api.listProjects();
    if (!projectList.length) {
        alert('No saved projects found.');
        return;
    }
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <h2>Load Project</h2>
            <div style="max-height:300px;overflow-y:auto">
                ${projectList.map(p => `
                    <div class="project-list-item" data-id="${p.id}" style="padding:8px 12px;cursor:pointer;border-bottom:1px solid #eee;display:flex;justify-content:space-between">
                        <span><strong>${p.name}</strong>${p.client ? ` — ${p.client}` : ''}</span>
                        <span style="font-size:11px;color:#999">${p.updated_at?.substring(0, 10) || ''}</span>
                    </div>
                `).join('')}
            </div>
            <div class="btn-row">
                <button class="btn btn-secondary" id="btn-cancel-load">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.getElementById('btn-cancel-load').onclick = () => overlay.remove();
    overlay.querySelectorAll('.project-list-item').forEach(el => {
        el.addEventListener('click', async () => {
            overlay.remove();
            await loadProject(el.dataset.id);
        });
        el.addEventListener('mouseenter', () => el.style.background = '#f0f0f0');
        el.addEventListener('mouseleave', () => el.style.background = '');
    });
}

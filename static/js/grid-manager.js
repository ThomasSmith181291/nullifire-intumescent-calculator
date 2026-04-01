import { api } from './api.js';

let gridApi = null;
let currentProjectId = null;
let projectDefaults = {};

export function getGridApi() { return gridApi; }

const STATUS_COLORS = {
    ok: '#22c55e', no_section_factor: '#f59e0b', no_band_mapping: '#f59e0b',
    no_coverage: '#f59e0b', no_dft_data: '#f59e0b', error: '#ef4444', pending: '#9ca3af'
};

function statusRenderer(params) {
    const color = STATUS_COLORS[params.value] || STATUS_COLORS.pending;
    return `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color}" title="${params.value || 'pending'}"></span>`;
}

function dftFormatter(params) {
    if (params.value == null) return '';
    const mm = params.value;
    return `${mm.toFixed(3)} (${Math.round(mm * 1000)}um)`;
}

function numFormatter(dp) {
    return (params) => params.value != null ? params.value.toFixed(dp) : '';
}

export function getColumnDefs(fireRatingOptions, failureTempOptions) {
    return [
        {
            headerName: '', checkboxSelection: true, headerCheckboxSelection: true,
            width: 40, pinned: 'left', suppressMenu: true, resizable: false
        },
        {
            field: 'section_name', headerName: 'Section', editable: true, width: 160,
            cellEditor: 'agTextCellEditor',
        },
        { field: 'steel_type', headerName: 'Type', width: 60, editable: false },
        {
            field: 'hp_profile_name', headerName: 'Exposure', editable: true, width: 100,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: { values: [] },
        },
        { field: 'hp_over_a', headerName: 'Hp/A', width: 70, editable: false, valueFormatter: (p) => p.value != null ? `${Math.round(p.value)}` : '' },
        {
            field: 'fire_rating_id', headerName: 'Fire Rating', editable: true, width: 110,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: { values: fireRatingOptions.map(fr => fr.id) },
            valueFormatter: (p) => {
                if (p.value == null) return '(default)';
                const fr = fireRatingOptions.find(f => f.id === p.value);
                return fr ? fr.description : String(p.value);
            },
        },
        {
            field: 'failure_temp_id', headerName: 'Temp', editable: true, width: 80,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: { values: failureTempOptions.map(ft => ft.id) },
            valueFormatter: (p) => {
                if (p.value == null) return '(default)';
                const ft = failureTempOptions.find(f => f.id === p.value);
                return ft ? ft.description : String(p.value);
            },
        },
        { field: 'dft_mm', headerName: 'DFT (mm)', width: 130, editable: false, valueFormatter: dftFormatter },
        { field: 'quantity', headerName: 'Qty', editable: true, width: 60, cellEditor: 'agNumberCellEditor' },
        { field: 'length_m', headerName: 'Length (m)', editable: true, width: 90, cellEditor: 'agNumberCellEditor', valueFormatter: numFormatter(2) },
        { field: 'surface_area_m2', headerName: 'Area (m2)', width: 90, editable: false, valueFormatter: numFormatter(3) },
        { field: 'volume_litres', headerName: 'Litres', width: 80, editable: false, valueFormatter: numFormatter(2) },
        { field: 'zone', headerName: 'Zone', editable: true, width: 100, cellEditor: 'agTextCellEditor' },
        { field: 'level', headerName: 'Level', editable: true, width: 80, cellEditor: 'agTextCellEditor' },
        { field: 'status', headerName: '', width: 40, editable: false, cellRenderer: statusRenderer, suppressMenu: true },
    ];
}

export async function initGrid(gridDiv, projectId, project, fireRatings, failureTemps) {
    currentProjectId = projectId;
    projectDefaults = {
        product_id: project.product_id,
        fire_rating_id: project.fire_rating_id,
        failure_temp_id: project.failure_temp_id,
    };

    const columnDefs = getColumnDefs(fireRatings, failureTemps);

    const gridOptions = {
        columnDefs,
        rowData: project.members || [],
        rowSelection: 'multiple',
        enableCellChangeFlash: true,
        animateRows: true,
        defaultColDef: {
            resizable: true,
            sortable: true,
            filter: true,
        },
        getRowId: (params) => params.data.id,
        onCellValueChanged: onCellValueChanged,
        tabToNextCell: tabToNextCell,
        suppressClickEdit: false,
        singleClickEdit: true,
    };

    if (gridApi) gridApi.destroy();
    gridApi = agGrid.createGrid(gridDiv, gridOptions);
    return gridApi;
}

export function setRowData(members) {
    if (gridApi) gridApi.setGridOption('rowData', members);
}

async function onCellValueChanged(event) {
    const { data, colDef, newValue, oldValue } = event;
    if (newValue === oldValue) return;
    if (!data.id || !currentProjectId) return;

    const field = colDef.field;
    const updateData = { [field]: newValue };

    try {
        const updated = await api.updateMember(currentProjectId, data.id, updateData);
        if (updated && updated.id) {
            event.api.applyTransaction({ update: [updated] });
            updateSummary();
        }
    } catch (err) {
        console.error('Update failed:', err);
    }
}

function tabToNextCell(params) {
    const editableCols = ['section_name', 'hp_profile_name', 'fire_rating_id',
        'failure_temp_id', 'quantity', 'length_m', 'zone', 'level'];
    let nextCol = params.nextCellPosition;
    if (!nextCol) return nextCol;

    // Skip non-editable columns
    while (nextCol && !editableCols.includes(nextCol.column.getColId())) {
        nextCol = {
            ...nextCol,
            column: params.api.getColumnDefs()
                ? nextCol.column
                : nextCol.column,
        };
        break; // AG Grid handles this natively with editable flag
    }
    return nextCol;
}

export async function addMember(sectionId, hpProfileName, extraData = {}) {
    if (!currentProjectId) return null;
    const member = await api.addMember(currentProjectId, {
        section_id: sectionId,
        hp_profile_name: hpProfileName,
        quantity: extraData.quantity || 1,
        length_m: extraData.length_m || 0,
        zone: extraData.zone || '',
        level: extraData.level || '',
    });
    if (member && gridApi) {
        gridApi.applyTransaction({ add: [member] });
        updateSummary();
    }
    return member;
}

export async function deleteSelected() {
    if (!gridApi || !currentProjectId) return;
    const selected = gridApi.getSelectedRows();
    if (!selected.length) return;
    const ids = selected.map(r => r.id);
    await api.batchDeleteMembers(currentProjectId, ids);
    gridApi.applyTransaction({ remove: selected });
    updateSummary();
}

export function updateSummary() {
    let totalLitres = 0, totalKg = 0, totalArea = 0, count = 0;
    if (gridApi) {
        gridApi.forEachNode(node => {
            const d = node.data;
            totalLitres += d.volume_litres || 0;
            totalKg += d.weight_kg || 0;
            totalArea += d.surface_area_m2 || 0;
            count++;
        });
    }
    const el = document.getElementById('summary-bar');
    if (el) {
        el.innerHTML = `
            <div class="summary-item"><span class="summary-label">Members:</span><span class="summary-value">${count}</span></div>
            <div class="summary-item"><span class="summary-label">Area:</span><span class="summary-value">${totalArea.toFixed(1)} m2</span></div>
            <div class="summary-item"><span class="summary-label">Litres:</span><span class="summary-value">${totalLitres.toFixed(1)} L</span></div>
            <div class="summary-item"><span class="summary-label">Weight:</span><span class="summary-value">${totalKg.toFixed(1)} kg</span></div>
        `;
    }
}

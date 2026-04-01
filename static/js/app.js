import { api } from './api.js';

let project = null, gridApi = null;
let products = [], fireRatings = [], failureTemps = [], origins = [], steelTypes = [];
let shortlist = []; // [{section_id, serial_size, steel_type_abbrev, steel_type_name, steel_type_id, weight, hp_profile_name}]
let usedZones = new Set(), usedLevels = new Set();

const $ = id => document.getElementById(id);
function toast(m, ok=true) { const t=document.createElement('div'); t.className=`toast ${ok?'toast-ok':'toast-err'}`; t.textContent=m; document.body.appendChild(t); setTimeout(()=>t.remove(),3000); }
function fillSel(id, opts, val) { $(id).innerHTML = opts.map(o=>`<option value="${o.v}"${String(o.v)===String(val)?' selected':''}>${o.t}</option>`).join(''); }
function modal(html) { const o=document.createElement('div'); o.className='modal-overlay'; o.innerHTML=`<div class="modal">${html}</div>`; document.body.appendChild(o); o.onclick=e=>{if(e.target===o)o.remove()}; return o; }

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
    [products, origins, steelTypes] = await Promise.all([api.getProducts(), api.getOrigins(), api.getSteelTypes()]);
    fillSel('sel-origin', origins.map(o=>({v:o.id,t:`${o.code} - ${o.description}`})));

    $('btn-new').onclick = $('btn-new2').onclick = newProject;
    $('btn-load').onclick = $('btn-load2').onclick = loadDialog;
    $('btn-add').onclick = addMemberDialog;
    $('btn-import').onclick = importDialog;
    $('btn-del').onclick = deleteSelected;
    $('btn-close-cp').onclick = () => $('compare-panel').classList.remove('open');
    $('btn-export-excel').onclick = () => project && window.open(api.exportExcelUrl(project.id));
    $('btn-export-pdf').onclick = () => project && window.open(api.exportPdfUrl(project.id));
    $('btn-toggle-shortlist').onclick = toggleShortlist;
    $('btn-close-shortlist').onclick = () => $('shortlist-panel').classList.remove('open');
    $('btn-add-to-shortlist').onclick = manageShortlistDialog;
    $('sel-origin').onchange = saveOrigin;

    // Context bar: fire rating cascades to failure temp
    $('ctx-fr').onchange = cascadeCtxTemps;
});

// ── Project ──
async function newProject() {
    const frs = products.length ? await api.getProductFireRatings(products[0].id) : [];
    const fts = frs.length ? await api.getProductFailureTemps(products[0].id, frs.find(f=>f.id===3)?.id||frs[0]?.id) : [];
    const m = modal(`<h2>New Project</h2>
        <div class="field"><label>Project Name *</label><input id="d-name" autofocus></div>
        <div class="field"><label>Client</label><input id="d-client"></div>
        <div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-ok">Create</button></div>`);
    $('d-x').onclick = () => m.remove();
    $('d-ok').onclick = async () => {
        const n=$('d-name').value.trim(); if(!n)return;
        const p = await api.createProject({name:n, client:$('d-client').value.trim(),
            product_id:products[0]?.id||284, fire_rating_id:3, failure_temp_id:7, origin_id:1});
        m.remove(); await openProject(p.id); toast('Project created');
    };
    $('d-name').onkeydown = e => { if(e.key==='Enter') $('d-ok').click(); };
}

async function loadDialog() {
    const list = await api.listProjects(); if(!list.length){toast('No projects',false);return;}
    const m = modal(`<h2>Load Project</h2><div style="max-height:300px;overflow-y:auto">${list.map(p=>`<div class="sr" data-id="${p.id}" style="padding:8px"><b>${p.name}</b>${p.client?' - '+p.client:''}</div>`).join('')}</div><div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button></div>`);
    $('d-x').onclick=()=>m.remove();
    m.querySelectorAll('[data-id]').forEach(el=>{el.onclick=async()=>{m.remove();await openProject(el.dataset.id);}});
}

async function openProject(pid) {
    project = await api.getProject(pid); if(!project) return;
    $('welcome').style.display='none'; $('work').classList.add('visible');
    $('panel-settings').style.display='block'; $('header-btns').style.display='flex';
    $('header-project').textContent=project.name;
    $('inp-name').value=project.name; $('inp-client').value=project.client||'';
    fillSel('sel-origin', origins.map(o=>({v:o.id,t:`${o.code} - ${o.description}`})), project.origin_id);

    // Context bar: populate fire ratings and temps
    fireRatings = await api.getProductFireRatings(products[0]?.id || project.product_id);
    fillSel('ctx-fr', fireRatings.map(f=>({v:f.id,t:f.description})), project.fire_rating_id);
    await cascadeCtxTemps();
    $('ctx-ft').value = String(project.failure_temp_id);

    // Collect used zones/levels from existing members
    usedZones = new Set(); usedLevels = new Set();
    (project.members||[]).forEach(m => { if(m.zone) usedZones.add(m.zone); if(m.level) usedLevels.add(m.level); });
    updateDataLists();

    // Load shortlist from project (stored as JSON in project reference field for now)
    try { shortlist = JSON.parse(project.reference || '[]'); } catch { shortlist = []; }
    renderShortlist();

    buildGrid();
    updateSummary();
}

async function cascadeCtxTemps() {
    const pid = products[0]?.id, frid = $('ctx-fr').value;
    if(!pid||!frid) return;
    failureTemps = await api.getProductFailureTemps(pid, frid);
    const prev = $('ctx-ft').value;
    fillSel('ctx-ft', failureTemps.map(f=>({v:f.id,t:f.description})), prev);
}

async function saveOrigin() {
    if(!project) return;
    project = await api.updateProject(project.id, {origin_id:+$('sel-origin').value});
}

function updateDataLists() {
    $('zone-list').innerHTML = [...usedZones].map(z=>`<option value="${z}">`).join('');
    $('level-list').innerHTML = [...usedLevels].map(l=>`<option value="${l}">`).join('');
}

function getContextValues() {
    return {
        fire_rating_id: +$('ctx-fr').value || null,
        failure_temp_id: +$('ctx-ft').value || null,
        zone: $('ctx-zone').value.trim(),
        level: $('ctx-level').value.trim(),
    };
}

// ── Shortlist ──
function toggleShortlist() {
    const p = $('shortlist-panel');
    p.classList.toggle('open');
    $('btn-toggle-shortlist').textContent = p.classList.contains('open') ? 'Shortlist ◀' : 'Shortlist ▶';
}

function renderShortlist() {
    const body = $('shortlist-body');
    if (!shortlist.length) {
        body.innerHTML = '<div class="muted" style="padding:12px;text-align:center">No sections in shortlist.<br>Click "+ Add Sections" to browse.</div>';
        return;
    }
    // Group by steel type
    const groups = {};
    shortlist.forEach(s => {
        const key = s.steel_type_name || s.steel_type_abbrev || 'Other';
        if (!groups[key]) groups[key] = [];
        groups[key].push(s);
    });

    let html = '';
    for (const [typeName, items] of Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0]))) {
        html += `<div class="sl-type-group"><div class="sl-type-header">${typeName}</div>`;
        for (const s of items) {
            html += `<div class="sl-item" data-sid="${s.section_id}" data-prof="${s.hp_profile_name}">
                <span><b>${s.serial_size}</b> <span class="sl-weight">${s.weight?s.weight+'kg/m':''}</span></span>
                <button class="sl-remove" data-idx="${shortlist.indexOf(s)}" title="Remove from shortlist">✕</button>
            </div>`;
        }
        html += '</div>';
    }
    body.innerHTML = html;

    // Click to add member instantly
    body.querySelectorAll('.sl-item').forEach(el => {
        el.onclick = async (e) => {
            if (e.target.classList.contains('sl-remove')) return;
            await quickAdd(+el.dataset.sid, el.dataset.prof);
        };
    });

    // Remove buttons
    body.querySelectorAll('.sl-remove').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            shortlist.splice(+btn.dataset.idx, 1);
            saveShortlist();
            renderShortlist();
        };
    });
}

async function quickAdd(sectionId, hpProfileName) {
    if (!project) return;
    const ctx = getContextValues();
    try {
        const mem = await api.addMember(project.id, {
            section_id: sectionId, hp_profile_name: hpProfileName,
            quantity: 1, length_m: 0,
            fire_rating_id: ctx.fire_rating_id, failure_temp_id: ctx.failure_temp_id,
            zone: ctx.zone, level: ctx.level, member_type: 'beam',
        });
        if (mem && gridApi) {
            gridApi.applyTransaction({add:[mem]}); updateSummary();
            if (ctx.zone) usedZones.add(ctx.zone);
            if (ctx.level) usedLevels.add(ctx.level);
            updateDataLists();
            toast(`Added ${mem.section_name} — ${mem.dft_mm?(mem.dft_mm*1000).toFixed(0)+'µm':'N/A'}`);
        }
    } catch(e) { toast(e.message, false); }
}

function saveShortlist() {
    if (!project) return;
    // Store shortlist as JSON in the project reference field
    api.updateProject(project.id, {reference: JSON.stringify(shortlist)});
}

async function manageShortlistDialog() {
    const cats = steelTypes.map(s=>`<button class="cat" data-tid="${s.id}">${s.abbrev} (${s.section_count})</button>`).join('');
    const m = modal(`<h2>Add Sections to Shortlist</h2>
        <div class="field"><label>Search</label><input id="d-q" placeholder="Type section e.g. 254x102" autofocus></div>
        <div class="cats">${cats}</div>
        <div id="d-res" style="max-height:280px;overflow-y:auto;border:1px solid #ddd;border-radius:4px"></div>
        <div class="btn-row"><button class="btn btn-secondary" id="d-x">Done</button></div>`);

    let to = null;
    m.querySelectorAll('.cat').forEach(b => {
        b.onclick = async () => {
            m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on')); b.classList.add('on');
            $('d-q').value = '';
            showSections(await api.getSectionsByType(b.dataset.tid, project.origin_id));
        };
    });
    $('d-q').oninput = () => {
        clearTimeout(to); m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on'));
        const q=$('d-q').value.trim(); if(q.length<2){$('d-res').innerHTML='';return;}
        to = setTimeout(async()=>showSections(await api.searchSections(q,project.origin_id)),150);
    };

    function showSections(secs) {
        $('d-res').innerHTML = secs.length ? secs.map(s => {
            const inList = shortlist.some(x=>x.section_id===s.id);
            return `<div class="sr" data-id="${s.id}" style="${inList?'background:#f0fdf4':''}">
                <span><b>${s.serial_size}</b> <span style="color:#666">${s.steel_type_abbrev}</span></span>
                <span>${inList?'<span style="color:var(--green)">✓ In list</span>':
                    `<span style="color:#999">${s.weight?s.weight+'kg/m':''}</span>`}</span>
            </div>`;
        }).join('') : '<div style="padding:10px;text-align:center" class="muted">No results</div>';

        $('d-res').querySelectorAll('.sr').forEach(el => {
            const sec = secs.find(s=>String(s.id)===el.dataset.id);
            el.onclick = async () => {
                if (shortlist.some(x=>x.section_id===sec.id)) return; // already in list
                // Get default profile
                const profs = await api.getSectionProfiles(sec.id, project.product_id);
                const defs = {7:'U1',8:'U4',3:'C1',4:'R1',5:'S1',1:'A5',2:'F1',6:'T1'};
                let prof = defs[sec.steel_type_id];
                if (!prof || !profs.some(p=>p.name===prof)) prof = profs[0]?.name||'U1';

                shortlist.push({
                    section_id: sec.id, serial_size: sec.serial_size,
                    steel_type_abbrev: sec.steel_type_abbrev, steel_type_name: sec.steel_type_name,
                    steel_type_id: sec.steel_type_id, weight: sec.weight, hp_profile_name: prof,
                });
                saveShortlist(); renderShortlist();
                el.style.background = '#f0fdf4';
                el.querySelector('span:last-child').innerHTML = '<span style="color:var(--green)">✓ In list</span>';
                toast(`${sec.serial_size} added to shortlist`);
            };
        });
    }

    $('d-x').onclick = () => m.remove();
}

// ── AG Grid ──
function buildGrid() {
    const frOpts = fireRatings.map(f=>f.id);
    const frMap = Object.fromEntries(fireRatings.map(f=>[f.id,f.description]));
    const ftOpts = failureTemps.map(f=>f.id);
    const ftMap = Object.fromEntries(failureTemps.map(f=>[f.id,f.description]));
    const SC = {ok:'#22c55e',warning:'#f59e0b',exceeds:'#ef4444',pending:'#9ca3af'};

    const cols = [
        {headerName:'', checkboxSelection:true, headerCheckboxSelection:true, width:40, pinned:'left', suppressMenu:true, resizable:false},
        {field:'member_type', headerName:'Type', minWidth:80, flex:0.6, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:['beam','column','bracing']}},
        {field:'section_name', headerName:'Section', minWidth:150, flex:1.4},
        {field:'steel_type', headerName:'Steel', minWidth:70, flex:0.5},
        {field:'hp_profile_name', headerName:'Exposure', minWidth:80, flex:0.6},
        {field:'hp_over_a', headerName:'Hp/A', minWidth:70, flex:0.5,
         valueFormatter:p=>p.value!=null?Math.round(p.value):''},
        {field:'fire_rating_id', headerName:'Fire Rating', minWidth:110, flex:0.9, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:frOpts},
         valueFormatter:p=>p.value!=null?(frMap[p.value]||String(p.value)):'—'},
        {field:'failure_temp_id', headerName:'Failure Temp', minWidth:100, flex:0.8, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:ftOpts},
         valueFormatter:p=>p.value!=null?(ftMap[p.value]||String(p.value)):'—'},
        {field:'product_id', headerName:'Product', minWidth:120, flex:0.9,
         valueFormatter:p=>{if(!p.value)return'—';const pr=products.find(x=>x.id===p.value);return pr?pr.name.replace('Nullifire ',''):'—';}},
        {field:'dft_mm', headerName:'DFT (mm)', minWidth:130, flex:1,
         valueFormatter:p=>p.value!=null?`${p.value.toFixed(3)}  (${Math.round(p.value*1000)} µm)`:'—'},
        {field:'quantity', headerName:'Qty', minWidth:60, flex:0.4, editable:true, cellEditor:'agNumberCellEditor'},
        {field:'length_m', headerName:'Length (m)', minWidth:90, flex:0.7, editable:true, cellEditor:'agNumberCellEditor',
         valueFormatter:p=>p.value!=null&&p.value>0?p.value.toFixed(2):''},
        {field:'surface_area_m2', headerName:'Area (m²)', minWidth:90, flex:0.7,
         valueFormatter:p=>p.value!=null&&p.value>0?p.value.toFixed(2):''},
        {field:'volume_litres', headerName:'Litres', minWidth:70, flex:0.5,
         valueFormatter:p=>p.value!=null&&p.value>0?p.value.toFixed(2):''},
        {field:'weight_kg', headerName:'Weight (kg)', minWidth:85, flex:0.6,
         valueFormatter:p=>p.value!=null&&p.value>0?p.value.toFixed(1):''},
        {field:'zone', headerName:'Zone', minWidth:90, flex:0.7, editable:true},
        {field:'level', headerName:'Level', minWidth:80, flex:0.6, editable:true},
        {field:'status', headerName:'', minWidth:45, flex:0.3, suppressMenu:true,
         cellRenderer:p=>`<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${SC[p.value]||SC.pending}" title="${p.value||''}"></span>`},
        {headerName:'', minWidth:65, flex:0.4, suppressMenu:true,
         cellRenderer:()=>`<button class="btn btn-sm btn-secondary" style="padding:2px 5px;font-size:9px" data-act="cmp">Compare</button>`,
         onCellClicked:e=>{if(e.event.target.dataset.act==='cmp')showCompare(e.data);}},
    ];

    if(gridApi)gridApi.destroy();
    gridApi = agGrid.createGrid($('grid'), {
        columnDefs:cols, rowData:project?.members||[], rowSelection:'multiple',
        enableCellChangeFlash:true, animateRows:true, singleClickEdit:true,
        defaultColDef:{resizable:true, sortable:true, filter:true},
        getRowId:p=>p.data.id,
        onCellValueChanged:onEdit,
        onSelectionChanged:()=>{
            const n=gridApi.getSelectedRows().length;
            $('btn-del').disabled=n===0;
            $('btn-del').textContent=n?`Delete (${n})`:'Delete Selected';
        },
    });
}

async function onEdit(ev) {
    const{data,colDef,newValue,oldValue}=ev;
    if(!data.id||!project||newValue===oldValue)return;
    try{
        const u=await api.updateMember(project.id,data.id,{[colDef.field]:newValue});
        if(u?.id){ev.api.applyTransaction({update:[u]});updateSummary();}
    }catch(e){toast(e.message,false);}
}

async function deleteSelected() {
    if(!gridApi||!project)return;
    const sel=gridApi.getSelectedRows(); if(!sel.length)return;
    await api.batchDeleteMembers(project.id,sel.map(r=>r.id));
    gridApi.applyTransaction({remove:sel}); updateSummary();
    toast(`Deleted ${sel.length}`);
}

function updateSummary() {
    let L=0,K=0,A=0,N=0,ok=0,w=0,x=0;
    if(gridApi)gridApi.forEachNode(n=>{const d=n.data;L+=d.volume_litres||0;K+=d.weight_kg||0;A+=d.surface_area_m2||0;N++;
        if(d.status==='ok')ok++;else if(d.status==='warning')w++;else if(d.status==='exceeds')x++;});
    $('s-count').textContent=N; $('s-area').textContent=A.toFixed(1)+' m\u00B2';
    $('s-litres').textContent=L.toFixed(1)+' L'; $('s-weight').textContent=K.toFixed(1)+' kg';
    $('s-ok').textContent=ok; $('s-warn').textContent=w; $('s-exc').textContent=x;
    $('info-count').textContent=`${N} member${N!==1?'s':''}`;
}

// ── Add Member Dialog ──
async function addMemberDialog() {
    if(!project)return;
    const ctx = getContextValues();
    // Show shortlist quick-picks at top if available
    let quickHtml = '';
    if (shortlist.length) {
        const groups = {};
        shortlist.forEach(s => { const k=s.steel_type_name||'Other'; if(!groups[k])groups[k]=[]; groups[k].push(s); });
        quickHtml = '<div style="margin-bottom:8px;border:1px solid #ddd;border-radius:4px;max-height:150px;overflow-y:auto">';
        for (const [t, items] of Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0]))) {
            quickHtml += `<div style="font-size:9px;font-weight:700;color:var(--grey);padding:3px 6px;background:#f9f9f9;text-transform:uppercase">${t}</div>`;
            items.forEach(s => {
                quickHtml += `<div class="sr quick-pick" data-sid="${s.section_id}" data-prof="${s.hp_profile_name}"><b>${s.serial_size}</b> <span style="color:#999">${s.weight?s.weight+'kg/m':''}</span></div>`;
            });
        }
        quickHtml += '</div>';
    }

    const cats = steelTypes.map(s=>`<button class="cat" data-tid="${s.id}">${s.abbrev} (${s.section_count})</button>`).join('');
    const m = modal(`<h2>Add Steel Member</h2>
        ${quickHtml?'<div class="sb-title">Quick Pick (from shortlist)</div>'+quickHtml:''}
        <div class="sb-title" style="margin-top:4px">Search / Browse All</div>
        <div class="field"><input id="d-q" placeholder="Type section e.g. 254x102" ${shortlist.length?'':'autofocus'}></div>
        <div class="cats">${cats}</div>
        <div id="d-res" style="max-height:180px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;margin-bottom:8px"></div>
        <div id="d-sel" style="display:none;padding:7px 9px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;margin-bottom:8px"><b id="d-sn"></b> <span id="d-st" style="color:#666"></span></div>
        <div class="field"><label>Exposure</label><select id="d-exp" disabled><option>Select section first</option></select></div>
        <div class="field"><label>Member Type</label><select id="d-mt"><option value="beam">Beam</option><option value="column">Column</option><option value="bracing">Bracing</option></select></div>
        <div style="display:flex;gap:8px"><div class="field" style="flex:1"><label>Qty</label><input type="number" id="d-qty" value="1" min="1"></div><div class="field" style="flex:1"><label>Length (m)</label><input type="number" id="d-len" value="0" step="0.1"></div></div>
        <div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-go" disabled>Add Member</button></div>`);

    // Quick picks — click to add instantly and close
    m.querySelectorAll('.quick-pick').forEach(el => {
        el.onclick = async () => {
            await quickAdd(+el.dataset.sid, el.dataset.prof);
            m.remove();
        };
    });

    let selSec = null, to = null;
    m.querySelectorAll('.cat').forEach(b=>{b.onclick=async()=>{m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on'));b.classList.add('on');$('d-q').value='';showRes(await api.getSectionsByType(b.dataset.tid,project.origin_id));}});
    $('d-q').oninput=()=>{clearTimeout(to);m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on'));const q=$('d-q').value.trim();if(q.length<2){$('d-res').innerHTML='';return;}to=setTimeout(async()=>showRes(await api.searchSections(q,project.origin_id)),150);};

    function showRes(secs) {
        $('d-res').innerHTML=secs.length?secs.map(s=>`<div class="sr" data-id="${s.id}"><span><b>${s.serial_size}</b> <span style="color:#666">${s.steel_type_abbrev}</span></span><span style="color:#999">${s.weight?s.weight+'kg/m':''}</span></div>`).join(''):'<div style="padding:10px;text-align:center" class="muted">No results</div>';
        $('d-res').querySelectorAll('.sr').forEach(el=>{
            const sec=secs.find(s=>String(s.id)===el.dataset.id);
            el.onclick=async()=>{selSec=sec;$('d-sn').textContent=sec.serial_size;$('d-st').textContent=sec.steel_type_name;$('d-sel').style.display='block';$('d-res').innerHTML='';
                const profs=await api.getSectionProfiles(sec.id,project.product_id);
                $('d-exp').disabled=false;$('d-exp').innerHTML=profs.map(p=>`<option value="${p.name}">${p.description}</option>`).join('');
                const defs={7:'U1',8:'U4',3:'C1',4:'R1',5:'S1',1:'A5',2:'F1',6:'T1'};const d=defs[sec.steel_type_id];
                if(d&&profs.some(p=>p.name===d))$('d-exp').value=d;
                $('d-go').disabled=false;$('d-qty').focus();};
        });
    }

    $('d-x').onclick=()=>m.remove();
    $('d-go').onclick=async()=>{if(!selSec)return;
        try{const mem=await api.addMember(project.id,{section_id:selSec.id,hp_profile_name:$('d-exp').value,member_type:$('d-mt').value,
            quantity:+$('d-qty').value||1,length_m:+$('d-len').value||0,
            fire_rating_id:ctx.fire_rating_id, failure_temp_id:ctx.failure_temp_id,
            zone:ctx.zone, level:ctx.level});
            if(mem&&gridApi){gridApi.applyTransaction({add:[mem]});updateSummary();
                if(ctx.zone)usedZones.add(ctx.zone);if(ctx.level)usedLevels.add(ctx.level);updateDataLists();
                toast(`Added ${selSec.serial_size}`);}m.remove();
        }catch(e){toast(e.message,false);}};
}

// ── Compare ──
async function showCompare(row) {
    if(!project||!row.section_id)return;
    const panel=$('compare-panel'); panel.classList.add('open');
    $('cp-body').innerHTML='<p class="muted" style="padding:12px">Loading...</p>';
    try{
        const frId=row.fire_rating_id||+$('ctx-fr').value;
        const ftId=row.failure_temp_id||+$('ctx-ft').value;
        const r=await fetch('/api/dft/compare',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({section_id:row.section_id,hp_profile_name:row.hp_profile_name,fire_rating_id:frId,failure_temp_id:ftId})}).then(r=>r.json());
        const frN=fireRatings.find(f=>f.id===frId)?.description||'';
        const ftN=failureTemps.find(f=>f.id===ftId)?.description||'';
        let h=`<div style="margin-bottom:8px;font-size:11px;color:var(--grey);line-height:1.4"><b>${row.section_name}</b> — ${row.hp_profile_name}<br>Hp/A: ${row.hp_over_a?Math.round(row.hp_over_a):'-'} | ${frN} | ${ftN}<br><b>${r.products_with_coverage}/${r.total_products}</b> products</div>`;
        r.all_results.forEach((p,i)=>{const ok=p.status==='ok',best=ok&&i===0;
            h+=`<div class="pc ${best?'best':''} ${ok?'':'dim'}"><div class="pc-top"><span class="pc-name">${p.product_name.replace('Nullifire ','')}${best?' ★':''}</span><span class="badge ${ok?'badge-ok':'badge-no'}">${ok?'Available':p.status.replace(/_/g,' ')}</span></div>${ok?`<div class="pc-dft">${p.dft_mm.toFixed(3)} mm <span class="pc-um">(${Math.round(p.dft_mm*1000)} µm)</span></div><button class="btn btn-sm ${best?'btn-primary':'btn-secondary'}" style="width:100%;margin-top:3px" data-pid="${p.product_id}" data-mid="${row.id}">${best?'Assign Best':'Assign'}</button>`:''}${!ok&&p.error?`<div style="font-size:9px;color:#999;margin-top:3px">${p.error}</div>`:''}</div>`;});
        $('cp-body').innerHTML=h;
        $('cp-body').querySelectorAll('[data-pid]').forEach(btn=>{btn.onclick=async()=>{
            const u=await api.updateMember(project.id,btn.dataset.mid,{product_id:+btn.dataset.pid});
            if(u&&gridApi){gridApi.applyTransaction({update:[u]});updateSummary();toast(`Assigned ${products.find(p=>p.id===+btn.dataset.pid)?.name||'product'}`);panel.classList.remove('open');}};});
    }catch(e){$('cp-body').innerHTML=`<p style="color:var(--err);padding:12px">${e.message}</p>`;}
}

// ── Import ──
async function importDialog() {
    if(!project)return;
    const m=modal(`<h2>Import Steel Schedule</h2><div class="field"><label>Upload CSV or Excel</label><input type="file" id="d-file" accept=".csv,.xlsx,.xls"></div><div id="d-prev" style="display:none"><div id="d-info" style="margin-bottom:5px;font-size:10px;color:var(--grey)"></div><div id="d-map" style="margin-bottom:6px"></div><div id="d-sample" style="max-height:100px;overflow:auto;font-size:9px;border:1px solid #ddd;border-radius:3px"></div></div><div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-go" disabled>Import</button></div>`);
    let parsed=null;
    $('d-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;const fd=new FormData();fd.append('file',file);const r=await fetch('/api/import/parse',{method:'POST',body:fd});parsed=await r.json();if(parsed.error){toast(parsed.error,false);return;}
        $('d-prev').style.display='block';$('d-info').textContent=`${parsed.total_rows} rows, ${parsed.headers.length} columns`;
        const fields=['section','quantity','length','zone','level'];
        $('d-map').innerHTML='<label style="font-size:10px;font-weight:600">Column Mapping</label>'+fields.map(f=>`<div style="display:flex;gap:5px;align-items:center;margin:2px 0"><span style="width:50px;font-size:10px">${f}</span><select data-f="${f}" style="flex:1;font-size:10px;padding:2px"><option value="">Skip</option>${parsed.headers.map((h,i)=>`<option value="${i}"${parsed.suggested_mapping[f]===i?' selected':''}>${h}</option>`).join('')}</select></div>`).join('');
        $('d-sample').innerHTML=`<table style="width:100%;border-collapse:collapse"><tr>${parsed.headers.map(h=>`<th style="padding:2px 3px;border-bottom:1px solid #ddd;text-align:left">${h}</th>`).join('')}</tr>${parsed.sample_rows.slice(0,3).map(r=>`<tr>${r.map(c=>`<td style="padding:1px 3px">${c}</td>`).join('')}</tr>`).join('')}</table>`;
        $('d-go').disabled=false;};
    $('d-x').onclick=()=>m.remove();
    $('d-go').onclick=async()=>{if(!parsed)return;const map={};m.querySelectorAll('[data-f]').forEach(s=>{if(s.value!=='')map[s.dataset.f]=+s.value;});if(map.section===undefined){toast('Map Section column',false);return;}
        const ctx=getContextValues();
        const members=[];for(const row of parsed.all_rows){const q=row[map.section];if(!q)continue;const res=await api.searchSections(q,project.origin_id);if(!res.length)continue;
            members.push({section_id:res[0].id,quantity:map.quantity!==undefined?+row[map.quantity]||1:1,length_m:map.length!==undefined?+row[map.length]||0:0,
                zone:map.zone!==undefined?row[map.zone]||'':ctx.zone,level:map.level!==undefined?row[map.level]||'':ctx.level});}
        if(!members.length){toast('No valid members',false);return;}
        const result=await api.importMembers(project.id,members);m.remove();project=await api.getProject(project.id);gridApi.setGridOption('rowData',project.members);updateSummary();toast(`Imported ${result.added_count} members`);};
}

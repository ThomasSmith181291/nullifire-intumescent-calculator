import { api } from './api.js';

let project = null, gridApi = null;
let products = [], fireRatings = [], failureTemps = [], origins = [], steelTypes = [];

const $ = id => document.getElementById(id);
function toast(m, ok=true) { const t=document.createElement('div'); t.className=`toast ${ok?'toast-ok':'toast-err'}`; t.textContent=m; document.body.appendChild(t); setTimeout(()=>t.remove(),3000); }
function fillSel(id, opts, val) { $(id).innerHTML = opts.map(o=>`<option value="${o.v}"${String(o.v)===String(val)?' selected':''}>${o.t}</option>`).join(''); }
function modal(html) { const o=document.createElement('div'); o.className='modal-overlay'; o.innerHTML=`<div class="modal">${html}</div>`; document.body.appendChild(o); o.onclick=e=>{if(e.target===o)o.remove()}; return o; }

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
    $('sel-fr').onchange = async () => { await cascadeTemps(); await saveDefaults(); };
    $('sel-ft').onchange = saveDefaults;
    $('sel-origin').onchange = saveDefaults;
});

// ── Project ──
async function newProject() {
    const frs = products.length ? await api.getProductFireRatings(products[0].id) : [];
    const fts = frs.length ? await api.getProductFailureTemps(products[0].id, frs.find(f=>f.id===3)?.id||frs[0]?.id) : [];
    const m = modal(`<h2>New Project</h2>
        <div class="field"><label>Project Name *</label><input id="d-name" autofocus></div>
        <div class="field"><label>Client</label><input id="d-client"></div>
        <div class="field"><label>Fire Rating</label><select id="d-fr">${frs.map(f=>`<option value="${f.id}"${f.id===3?' selected':''}>${f.description}</option>`).join('')}</select></div>
        <div class="field"><label>Failure Temp</label><select id="d-ft">${fts.map(f=>`<option value="${f.id}"${f.id===7?' selected':''}>${f.description}</option>`).join('')}</select></div>
        <div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-ok">Create</button></div>`);
    $('d-fr').onchange = async () => { const ft2 = await api.getProductFailureTemps(products[0].id,$('d-fr').value); $('d-ft').innerHTML=ft2.map(f=>`<option value="${f.id}">${f.description}</option>`).join(''); };
    $('d-x').onclick = () => m.remove();
    $('d-ok').onclick = async () => { const n=$('d-name').value.trim(); if(!n)return; const p=await api.createProject({name:n,client:$('d-client').value.trim(),product_id:products[0]?.id||284,fire_rating_id:+$('d-fr').value||3,failure_temp_id:+$('d-ft').value||7,origin_id:1}); m.remove(); await openProject(p.id); toast('Project created'); };
    $('d-name').onkeydown = e => { if(e.key==='Enter') $('d-ok').click(); };
}

async function loadDialog() {
    const list = await api.listProjects(); if(!list.length){toast('No projects',false);return;}
    const m = modal(`<h2>Load Project</h2><div style="max-height:300px;overflow-y:auto">${list.map(p=>`<div class="sr load-item" data-id="${p.id}"><strong>${p.name}</strong>${p.client?' - '+p.client:''}</div>`).join('')}</div><div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button></div>`);
    $('d-x').onclick=()=>m.remove();
    m.querySelectorAll('.load-item').forEach(el=>{el.onclick=async()=>{m.remove();await openProject(el.dataset.id);}});
}

async function openProject(pid) {
    project = await api.getProject(pid); if(!project) return;
    $('welcome').style.display='none';
    $('work').classList.add('visible');
    $('panel-settings').style.display='block';
    $('header-btns').style.display='flex';
    $('header-project').textContent=project.name;
    $('inp-name').value=project.name;
    $('inp-client').value=project.client||'';

    fireRatings = await api.getProductFireRatings(products[0]?.id||project.product_id);
    fillSel('sel-fr', fireRatings.map(f=>({v:f.id,t:f.description})), project.fire_rating_id);
    await cascadeTemps();
    fillSel('sel-origin', origins.map(o=>({v:o.id,t:`${o.code} - ${o.description}`})), project.origin_id);

    buildGrid();
    updateSummary();
}

async function cascadeTemps() {
    const pid=products[0]?.id||project?.product_id, frid=$('sel-fr').value;
    if(!pid||!frid)return;
    failureTemps = await api.getProductFailureTemps(pid, frid);
    fillSel('sel-ft', failureTemps.map(f=>({v:f.id,t:f.description})), project?.failure_temp_id);
}

async function saveDefaults() {
    if(!project)return;
    const d={fire_rating_id:+$('sel-fr').value, failure_temp_id:+$('sel-ft').value, origin_id:+$('sel-origin').value};
    if(isNaN(d.fire_rating_id)||isNaN(d.failure_temp_id))return;
    project = await api.updateProject(project.id, d);
    if(gridApi && project.members){gridApi.setGridOption('rowData',project.members); updateSummary();}
}

// ── AG Grid ──
function buildGrid() {
    const frOpts = fireRatings.map(f=>f.id);
    const frMap = Object.fromEntries(fireRatings.map(f=>[f.id,f.description]));
    const ftOpts = failureTemps.map(f=>f.id);
    const ftMap = Object.fromEntries(failureTemps.map(f=>[f.id,f.description]));
    const SC = {ok:'#22c55e',warning:'#f59e0b',exceeds:'#ef4444',pending:'#9ca3af'};

    const cols = [
        {headerName:'', checkboxSelection:true, headerCheckboxSelection:true, width:42, pinned:'left', suppressMenu:true, resizable:false},
        {field:'member_type', headerName:'Type', width:90, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:['beam','column','bracing']}},
        {field:'section_name', headerName:'Section', minWidth:160, flex:1.5},
        {field:'steel_type', headerName:'Steel Type', minWidth:100, flex:0.8},
        {field:'hp_profile_name', headerName:'Exposure', minWidth:90, flex:0.8},
        {field:'hp_over_a', headerName:'Hp/A (m⁻¹)', minWidth:90, flex:0.7,
         valueFormatter:p=>p.value!=null?Math.round(p.value):''},
        {field:'fire_rating_id', headerName:'Fire Rating', minWidth:120, flex:1, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:frOpts},
         valueFormatter:p=>p.value!=null?(frMap[p.value]||'(default)'):'(default)'},
        {field:'failure_temp_id', headerName:'Failure Temp', minWidth:110, flex:0.8, editable:true,
         cellEditor:'agSelectCellEditor', cellEditorParams:{values:ftOpts},
         valueFormatter:p=>p.value!=null?(ftMap[p.value]||'(default)'):'(default)'},
        {field:'product_id', headerName:'Product', minWidth:130, flex:1,
         valueFormatter:p=>{if(!p.value)return'(default)';const pr=products.find(x=>x.id===p.value);return pr?pr.name.replace('Nullifire ',''):'(default)';}},
        {field:'dft_mm', headerName:'DFT (mm)', minWidth:140, flex:1,
         valueFormatter:p=>p.value!=null?`${p.value.toFixed(3)}  (${Math.round(p.value*1000)} µm)`:'-'},
        {field:'quantity', headerName:'Quantity', minWidth:80, flex:0.6, editable:true, cellEditor:'agNumberCellEditor'},
        {field:'length_m', headerName:'Length (m)', minWidth:100, flex:0.7, editable:true, cellEditor:'agNumberCellEditor',
         valueFormatter:p=>p.value!=null?p.value.toFixed(2):''},
        {field:'surface_area_m2', headerName:'Area (m²)', minWidth:100, flex:0.7,
         valueFormatter:p=>p.value!=null?p.value.toFixed(2):''},
        {field:'volume_litres', headerName:'Litres', minWidth:80, flex:0.6,
         valueFormatter:p=>p.value!=null?p.value.toFixed(2):''},
        {field:'weight_kg', headerName:'Weight (kg)', minWidth:90, flex:0.7,
         valueFormatter:p=>p.value!=null?p.value.toFixed(1):''},
        {field:'zone', headerName:'Zone', minWidth:100, flex:0.8, editable:true},
        {field:'level', headerName:'Level', minWidth:80, flex:0.6, editable:true},
        {field:'status', headerName:'Status', minWidth:60, flex:0.4, suppressMenu:true,
         cellRenderer:p=>`<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${SC[p.value]||SC.pending}" title="${p.value||''}"></span>`},
        {headerName:'', minWidth:70, flex:0.5, suppressMenu:true,
         cellRenderer:()=>`<button class="btn btn-sm btn-secondary" style="padding:2px 6px;font-size:10px" data-act="cmp">Compare</button>`,
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
    toast(`Deleted ${sel.length} member(s)`);
}

function updateSummary() {
    let L=0,K=0,A=0,N=0,ok=0,w=0,x=0;
    if(gridApi)gridApi.forEachNode(n=>{const d=n.data;L+=d.volume_litres||0;K+=d.weight_kg||0;A+=d.surface_area_m2||0;N++;
        if(d.status==='ok')ok++;else if(d.status==='warning')w++;else if(d.status==='exceeds')x++;});
    $('s-count').textContent=N; $('s-area').textContent=A.toFixed(1)+' m²';
    $('s-litres').textContent=L.toFixed(1)+' L'; $('s-weight').textContent=K.toFixed(1)+' kg';
    $('s-ok').textContent=ok; $('s-warn').textContent=w; $('s-exc').textContent=x;
    $('info-count').textContent=`${N} member${N!==1?'s':''}`;
}

// ── Add Member ──
async function addMemberDialog() {
    if(!project)return;
    const cats=steelTypes.map(s=>`<button class="cat" data-tid="${s.id}">${s.abbrev} (${s.section_count})</button>`).join('');
    const m=modal(`<h2>Add Steel Member</h2>
        <div class="field"><label>Search or browse sections</label><input id="d-q" placeholder="Type e.g. 254x102 or select category below" autofocus></div>
        <div class="cats">${cats}</div>
        <div id="d-res" style="max-height:200px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;margin-bottom:8px"></div>
        <div id="d-sel" style="display:none;padding:8px 10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;margin-bottom:8px"><b id="d-sn"></b> <span id="d-st" style="color:#666"></span></div>
        <div class="field"><label>Exposure</label><select id="d-exp" disabled><option>Select section first</option></select></div>
        <div class="field"><label>Member Type</label><select id="d-mt"><option value="beam">Beam</option><option value="column">Column</option><option value="bracing">Bracing</option></select></div>
        <div style="display:flex;gap:10px"><div class="field" style="flex:1"><label>Quantity</label><input type="number" id="d-qty" value="1" min="1"></div><div class="field" style="flex:1"><label>Length (m)</label><input type="number" id="d-len" value="0" step="0.1"></div></div>
        <div style="display:flex;gap:10px"><div class="field" style="flex:1"><label>Zone</label><input id="d-zone"></div><div class="field" style="flex:1"><label>Level</label><input id="d-lev"></div></div>
        <div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-go" disabled>Add Member</button></div>`);

    let selSec=null, to=null;
    m.querySelectorAll('.cat').forEach(b=>{b.onclick=async()=>{m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on'));b.classList.add('on');$('d-q').value='';showResults(await api.getSectionsByType(b.dataset.tid,project.origin_id));}});
    $('d-q').oninput=()=>{clearTimeout(to);m.querySelectorAll('.cat').forEach(x=>x.classList.remove('on'));const q=$('d-q').value.trim();if(q.length<2){$('d-res').innerHTML='';return;}to=setTimeout(async()=>showResults(await api.searchSections(q,project.origin_id)),150);};

    function showResults(secs){
        $('d-res').innerHTML=secs.length?secs.map(s=>`<div class="sr" data-id="${s.id}"><span><b>${s.serial_size}</b> <span style="color:#666">${s.steel_type_abbrev}</span></span><span style="color:#999">${s.weight?s.weight+'kg/m':''}</span></div>`).join(''):'<div style="padding:10px;color:#999;text-align:center">No results</div>';
        $('d-res').querySelectorAll('.sr').forEach(el=>{
            const sec=secs.find(s=>String(s.id)===el.dataset.id);
            el.onclick=async()=>{selSec=sec;$('d-sn').textContent=sec.serial_size;$('d-st').textContent=sec.steel_type_name;$('d-sel').style.display='block';$('d-res').innerHTML='';
                const profs=await api.getSectionProfiles(sec.id,project.product_id);
                $('d-exp').disabled=false;$('d-exp').innerHTML=profs.map(p=>`<option value="${p.name}">${p.description}</option>`).join('');
                const defs={7:'U1',8:'U4',3:'C1',4:'R1',5:'S1',1:'A5',2:'F1',6:'T1'};
                const d=defs[sec.steel_type_id]; if(d&&profs.some(p=>p.name===d))$('d-exp').value=d;
                $('d-go').disabled=false; $('d-qty').focus();};
        });
    }

    $('d-x').onclick=()=>m.remove();
    $('d-go').onclick=async()=>{if(!selSec)return;
        try{const mem=await api.addMember(project.id,{section_id:selSec.id,hp_profile_name:$('d-exp').value,member_type:$('d-mt').value,quantity:+$('d-qty').value||1,length_m:+$('d-len').value||0,zone:$('d-zone').value.trim(),level:$('d-lev').value.trim()});
            if(mem&&gridApi){gridApi.applyTransaction({add:[mem]});updateSummary();toast(`Added ${selSec.serial_size} — DFT: ${mem.dft_mm?(mem.dft_mm*1000).toFixed(0)+'µm':'N/A'}`);}m.remove();
        }catch(e){toast(e.message,false);}};
    $('d-lev').onkeydown=e=>{if(e.key==='Enter')$('d-go').click();};
}

// ── Compare Panel ──
async function showCompare(row) {
    if(!project||!row.section_id)return;
    const panel=$('compare-panel'); panel.classList.add('open');
    $('cp-body').innerHTML='<p style="color:#999;font-size:12px">Loading...</p>';
    try{
        const frId=row.fire_rating_id||project.fire_rating_id;
        const ftId=row.failure_temp_id||project.failure_temp_id;
        const r=await fetch('/api/dft/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section_id:row.section_id,hp_profile_name:row.hp_profile_name,fire_rating_id:frId,failure_temp_id:ftId})}).then(r=>r.json());
        const frN=fireRatings.find(f=>f.id===frId)?.description||'';
        const ftN=failureTemps.find(f=>f.id===ftId)?.description||'';
        let h=`<div style="margin-bottom:10px;font-size:12px;color:#666;line-height:1.4"><b>${row.section_name}</b> — ${row.hp_profile_name}<br>Hp/A: ${row.hp_over_a?Math.round(row.hp_over_a):'-'} | ${frN} | ${ftN}<br><b>${r.products_with_coverage}/${r.total_products}</b> products available</div>`;
        r.all_results.forEach((p,i)=>{const ok=p.status==='ok',best=ok&&i===0;
            h+=`<div class="pc ${best?'best':''} ${ok?'':'dim'}"><div class="pc-top"><span class="pc-name">${p.product_name.replace('Nullifire ','')}${best?' ★':''}</span><span class="badge ${ok?'badge-ok':'badge-no'}">${ok?'Available':p.status.replace(/_/g,' ')}</span></div>${ok?`<div class="pc-dft">${p.dft_mm.toFixed(3)} mm <span class="pc-um">(${Math.round(p.dft_mm*1000)} µm)</span></div><button class="btn btn-sm ${best?'btn-primary':'btn-secondary'}" style="width:100%;margin-top:4px" data-pid="${p.product_id}" data-mid="${row.id}">${best?'Assign Best Product':'Assign This Product'}</button>`:''}${!ok&&p.error?`<div style="font-size:10px;color:#999;margin-top:4px">${p.error}</div>`:''}</div>`;});
        $('cp-body').innerHTML=h;
        $('cp-body').querySelectorAll('[data-pid]').forEach(btn=>{btn.onclick=async()=>{
            const u=await api.updateMember(project.id,btn.dataset.mid,{product_id:+btn.dataset.pid});
            if(u&&gridApi){gridApi.applyTransaction({update:[u]});updateSummary();toast(`Assigned ${products.find(p=>p.id===+btn.dataset.pid)?.name||'product'}`);panel.classList.remove('open');}};});
    }catch(e){$('cp-body').innerHTML=`<p style="color:var(--red-s)">${e.message}</p>`;}
}

// ── Import ──
async function importDialog() {
    if(!project)return;
    const m=modal(`<h2>Import Steel Schedule</h2><div class="field"><label>Upload CSV or Excel</label><input type="file" id="d-file" accept=".csv,.xlsx,.xls"></div><div id="d-prev" style="display:none"><div id="d-info" style="margin-bottom:6px;font-size:11px;color:#666"></div><div id="d-map" style="margin-bottom:8px"></div><div id="d-sample" style="max-height:120px;overflow:auto;font-size:10px;border:1px solid #ddd;border-radius:4px"></div></div><div class="btn-row"><button class="btn btn-secondary" id="d-x">Cancel</button><button class="btn btn-primary" id="d-go" disabled>Import</button></div>`);
    let parsed=null;
    $('d-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;const fd=new FormData();fd.append('file',file);const r=await fetch('/api/import/parse',{method:'POST',body:fd});parsed=await r.json();if(parsed.error){toast(parsed.error,false);return;}
        $('d-prev').style.display='block';$('d-info').textContent=`${parsed.total_rows} rows, ${parsed.headers.length} columns`;
        const fields=['section','quantity','length','zone','level'];
        $('d-map').innerHTML='<label style="font-size:11px;font-weight:600">Column Mapping</label>'+fields.map(f=>`<div style="display:flex;gap:6px;align-items:center;margin:3px 0"><span style="width:55px;font-size:11px">${f}</span><select data-f="${f}" style="flex:1;font-size:11px;padding:2px 4px"><option value="">Skip</option>${parsed.headers.map((h,i)=>`<option value="${i}"${parsed.suggested_mapping[f]===i?' selected':''}>${h}</option>`).join('')}</select></div>`).join('');
        $('d-sample').innerHTML=`<table style="width:100%;border-collapse:collapse"><tr>${parsed.headers.map(h=>`<th style="padding:2px 4px;border-bottom:1px solid #ddd;font-size:10px;text-align:left">${h}</th>`).join('')}</tr>${parsed.sample_rows.slice(0,3).map(r=>`<tr>${r.map(c=>`<td style="padding:2px 4px;font-size:10px">${c}</td>`).join('')}</tr>`).join('')}</table>`;
        $('d-go').disabled=false;};
    $('d-x').onclick=()=>m.remove();
    $('d-go').onclick=async()=>{if(!parsed)return;const map={};m.querySelectorAll('[data-f]').forEach(s=>{if(s.value!=='')map[s.dataset.f]=+s.value;});if(map.section===undefined){toast('Map Section column',false);return;}
        const members=[];for(const row of parsed.all_rows){const q=row[map.section];if(!q)continue;const res=await api.searchSections(q,project.origin_id);if(!res.length)continue;members.push({section_id:res[0].id,quantity:map.quantity!==undefined?+row[map.quantity]||1:1,length_m:map.length!==undefined?+row[map.length]||0:0,zone:map.zone!==undefined?row[map.zone]||'':'',level:map.level!==undefined?row[map.level]||'':''});}
        if(!members.length){toast('No valid members',false);return;}
        const result=await api.importMembers(project.id,members);m.remove();project=await api.getProject(project.id);gridApi.setGridOption('rowData',project.members);updateSummary();toast(`Imported ${result.added_count} members`);};
}

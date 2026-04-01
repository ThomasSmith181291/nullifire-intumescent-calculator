const BASE = '/api';

async function fetchJson(url, options = {}) {
    const resp = await fetch(BASE + url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (resp.status === 204) return null;
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: resp.statusText }));
        throw new Error(err.error || resp.statusText);
    }
    return resp.json();
}

export const api = {
    // Projects
    createProject: (data) => fetchJson('/projects', { method: 'POST', body: JSON.stringify(data) }),
    listProjects: () => fetchJson('/projects'),
    getProject: (id) => fetchJson(`/projects/${id}`),
    updateProject: (id, data) => fetchJson(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteProject: (id) => fetchJson(`/projects/${id}`, { method: 'DELETE' }),

    // Members
    addMember: (pid, data) => fetchJson(`/projects/${pid}/members`, { method: 'POST', body: JSON.stringify(data) }),
    updateMember: (pid, mid, data) => fetchJson(`/projects/${pid}/members/${mid}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteMember: (pid, mid) => fetchJson(`/projects/${pid}/members/${mid}`, { method: 'DELETE' }),
    batchDeleteMembers: (pid, ids) => fetchJson(`/projects/${pid}/members/batch-delete`, { method: 'POST', body: JSON.stringify({ ids }) }),

    // Sections
    getSteelTypes: () => fetchJson('/sections/types'),
    getSectionsByType: (typeId, origin) => {
        let url = `/sections/types/${typeId}`;
        if (origin) url += `?origin=${origin}`;
        return fetchJson(url);
    },
    searchSections: (q, origin) => {
        let url = `/sections/search?q=${encodeURIComponent(q)}`;
        if (origin) url += `&origin=${origin}`;
        return fetchJson(url);
    },
    getSectionProfiles: (id, productId) => {
        let url = `/sections/${id}/profiles`;
        if (productId) url += `?product_id=${productId}`;
        return fetchJson(url);
    },

    // Products
    getProducts: () => fetchJson('/products'),
    getProductFireRatings: (pid) => fetchJson(`/products/${pid}/fire-ratings`),
    getProductFailureTemps: (pid, frId) => fetchJson(`/products/${pid}/failure-temps?fire_rating_id=${frId}`),

    // Origins
    getOrigins: () => fetchJson('/origins'),

    // DFT
    lookupDft: (data) => fetchJson('/dft/lookup', { method: 'POST', body: JSON.stringify(data) }),

    // Summary
    getProjectSummary: (pid) => fetchJson(`/projects/${pid}/summary`),

    // Grid & Levels
    getGridlines: (pid) => fetchJson(`/projects/${pid}/gridlines`),
    addGridline: (pid, data) => fetchJson(`/projects/${pid}/gridlines`, { method: 'POST', body: JSON.stringify(data) }),
    deleteGridline: (pid, gid) => fetchJson(`/projects/${pid}/gridlines/${gid}`, { method: 'DELETE' }),
    getLevels: (pid) => fetchJson(`/projects/${pid}/levels`),
    addLevel: (pid, data) => fetchJson(`/projects/${pid}/levels`, { method: 'POST', body: JSON.stringify(data) }),
    deleteLevel: (pid, lid) => fetchJson(`/projects/${pid}/levels/${lid}`, { method: 'DELETE' }),
    getSceneData: (pid) => fetchJson(`/projects/${pid}/scene`),

    // Import/Export
    exportExcelUrl: (pid) => `${BASE}/projects/${pid}/export/excel`,
    exportPdfUrl: (pid) => `${BASE}/projects/${pid}/export/pdf`,
    importMembers: (pid, members) => fetchJson(`/projects/${pid}/import`, { method: 'POST', body: JSON.stringify({ members }) }),

    // Health
    health: () => fetchJson('/health'),
};

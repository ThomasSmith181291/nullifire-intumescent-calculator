const BASE = '/api';

async function fetchJson(url, options = {}) {
    const resp = await fetch(BASE + url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (resp.status === 204) return null;
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
    addMember: (projectId, data) => fetchJson(`/projects/${projectId}/members`, { method: 'POST', body: JSON.stringify(data) }),
    updateMember: (projectId, memberId, data) => fetchJson(`/projects/${projectId}/members/${memberId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteMember: (projectId, memberId) => fetchJson(`/projects/${projectId}/members/${memberId}`, { method: 'DELETE' }),
    batchDeleteMembers: (projectId, ids) => fetchJson(`/projects/${projectId}/members/batch-delete`, { method: 'POST', body: JSON.stringify({ ids }) }),

    // Reference data
    searchSections: (q, origin) => {
        let url = `/sections/search?q=${encodeURIComponent(q)}`;
        if (origin) url += `&origin=${origin}`;
        return fetchJson(url);
    },
    getSection: (id) => fetchJson(`/sections/${id}`),
    getSectionProfiles: (sectionId, productId) => {
        let url = `/sections/${sectionId}/profiles`;
        if (productId) url += `?product_id=${productId}`;
        return fetchJson(url);
    },
    getSectionFactor: (sectionId, profile) => fetchJson(`/sections/${sectionId}/factor?profile=${encodeURIComponent(profile)}`),

    // Products
    getProducts: () => fetchJson('/products'),
    getProduct: (id) => fetchJson(`/products/${id}`),
    getProductFireRatings: (productId) => fetchJson(`/products/${productId}/fire-ratings`),
    getProductFailureTemps: (productId, fireRatingId) => fetchJson(`/products/${productId}/failure-temps?fire_rating_id=${fireRatingId}`),

    // Origins
    getOrigins: () => fetchJson('/origins'),

    // DFT
    lookupDft: (data) => fetchJson('/dft/lookup', { method: 'POST', body: JSON.stringify(data) }),

    // Health
    health: () => fetchJson('/health'),
};

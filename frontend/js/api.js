export function createApi(getToken, onUnauthorized) {
  async function req(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(path, { ...options, headers });
    let body = null;
    const text = await res.text();
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { detail: text };
    }
    if (res.status === 401) {
      onUnauthorized && onUnauthorized();
    }
    if (!res.ok) {
      const detail = body && (body.detail || body.message);
      const err = new Error(typeof detail === "string" ? detail : res.statusText);
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return body;
  }

  return {
    get: (path) => req(path),
    post: (path, data) =>
      req(path, { method: "POST", body: JSON.stringify(data || {}) }),
    chambers: () => req("/api/chambers"),
    chamber: (id) => req(`/api/chambers/${id}`),
    createChamber: (data) => req("/api/chambers", { method: "POST", body: JSON.stringify(data) }),
    probes: (chamberId) =>
      req(chamberId ? `/api/probes?chamber_id=${chamberId}` : "/api/probes"),
    probe: (id) => req(`/api/probes/${id}`),
    registerProbe: (data) => req("/api/probes", { method: "POST", body: JSON.stringify(data) }),
    batches: (status) =>
      req(status ? `/api/batches?status=${encodeURIComponent(status)}` : "/api/batches"),
    batch: (id) => req(`/api/batches/${id}`),
    createBatch: (data) => req("/api/batches", { method: "POST", body: JSON.stringify(data) }),
    excursions: (status) =>
      req(status ? `/api/excursions?status=${encodeURIComponent(status)}` : "/api/excursions"),
    openExcursion: (data) =>
      req("/api/excursions/open", { method: "POST", body: JSON.stringify(data) }),
    closeExcursion: (data) =>
      req("/api/excursions/close", { method: "POST", body: JSON.stringify(data) }),
    seals: () => req("/api/seals"),
    seal: (data) => req("/api/seals", { method: "POST", body: JSON.stringify(data) }),
    spectrumList: () => req("/api/spectrum"),
    spectrumExport: (data) =>
      req("/api/spectrum/export", { method: "POST", body: JSON.stringify(data) }),
    spectrumOne: (ref) => req(`/api/spectrum/${encodeURIComponent(ref)}`),
    lineage: () => req("/api/lineage"),
    lineageBatch: (id) => req(`/api/lineage/batch/${id}`),
    addLineage: (data) => req("/api/lineage", { method: "POST", body: JSON.stringify(data) }),
    reconcile: () => req("/api/reconcile"),
    reconcileOne: (code) => req(`/api/reconcile/${encodeURIComponent(code)}`),
    proofBatch: (code) => req(`/api/proof/batch/${encodeURIComponent(code)}`),
    calibrations: (probeId) =>
      req(probeId ? `/api/calibrations?probe_id=${probeId}` : "/api/calibrations"),
    addCalibration: (data) =>
      req("/api/calibrations", { method: "POST", body: JSON.stringify(data) }),
    routes: () => req("/api/routes"),
    createRoute: (data) => req("/api/routes", { method: "POST", body: JSON.stringify(data) }),
    audit: () => req("/api/audit?limit=150"),
    contention: () => req("/api/contention"),
    locks: () => req("/api/locks"),
    dashboard: () => req("/api/dashboard"),
    carrierJobs: () => req("/api/carrier-ingest/jobs"),
    carrierStub: (data) =>
      req("/api/carrier-ingest-stub", { method: "POST", body: JSON.stringify(data) }),
    thawJobs: () => req("/api/thaw/jobs"),
    thawStub: (data) => req("/api/thaw-stub", { method: "POST", body: JSON.stringify(data) }),
  };
}
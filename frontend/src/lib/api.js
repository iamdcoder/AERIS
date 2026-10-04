const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 1200;

async function requestJson(path, options = {}) {
  const controller = new AbortController();

  const timeout = window.setTimeout(() => {
    controller.abort();
  }, options.timeoutMs || DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    const contentType = response.headers.get("content-type") || "";

    const body = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      return {
        ok: false,
        fallback: true,
        status: response.status,
        data: body,
      };
    }

    return {
      ok: true,
      fallback: false,
      status: response.status,
      data: body,
    };
  } catch (error) {
    return {
      ok: false,
      fallback: true,
      status: null,
      data: null,
      error: error?.message || "Network request failed.",
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchAirspace() {
  return requestJson("/airspace");
}

export async function fetchDisruptions() {
  return requestJson("/disruptions");
}

export async function fetchFlight(flightId) {
  return requestJson(`/flights/${encodeURIComponent(flightId)}`);
}

export async function fetchNetworkMetrics() {
  return requestJson("/network/metrics");
}

export async function requestRecommendation(payload) {
  return requestJson("/copilot/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function applyIntervention(payload) {
  return requestJson("/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyIntervention(payload) {
  return requestJson("/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
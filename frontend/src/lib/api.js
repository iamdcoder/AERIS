const RAW_API_BASE_URL =
  import.meta.env.PROD
    ? import.meta.env.VITE_API_URL ||
      import.meta.env.VITE_API_BASE_URL ||
      ""
    : "";

const API_BASE_URL =
  String(RAW_API_BASE_URL || "/api")
    .replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 15000;

const FLAGSHIP_DEFAULTS = {
  target_flight_id: "F102",
  scenario_id: "mumbai_weather_crisis_v2",
  decision_time_min: 19,
};

function normalizePath(path) {
  return path.startsWith("/") ? path : `/${path}`;
}

function makeError({
  message,
  errorType,
  method,
  path,
  status = null,
}) {
  return {
    ok: false,
    status,
    data: null,
    errorType,
    method,
    path,
    error: message,
  };
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const normalizedPath = normalizePath(path);
  const method = String(options.method || "GET").toUpperCase();
  const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;

  const timeout = window.setTimeout(
    () => controller.abort(),
    timeoutMs,
  );

  try {
    const {
      timeoutMs: _ignoredTimeout,
      ...fetchOptions
    } = options;

    const response = await fetch(
      `${API_BASE_URL}${normalizedPath}`,
      {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(fetchOptions.headers || {}),
        },
      },
    );

    const contentType =
      response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail =
        typeof data === "object"
          ? data?.detail || data?.message
          : data;

      return makeError({
        status: response.status,
        method,
        path: normalizedPath,
        errorType:
          response.status === 404
            ? "NOT_FOUND"
            : response.status === 409
              ? "CONFLICT"
              : response.status === 422
                ? "VALIDATION"
                : response.status >= 500
                  ? "SERVER_ERROR"
                  : "HTTP_ERROR",
        message:
          detail ||
          `Backend request failed with HTTP ${response.status}.`,
      });
    }

    return {
      ok: true,
      status: response.status,
      data,
      errorType: null,
      method,
      path: normalizedPath,
      error: null,
    };
  } catch (error) {
    if (error?.name === "AbortError") {
      return makeError({
        method,
        path: normalizedPath,
        errorType: "TIMEOUT",
        message:
          `AERIS backend request timed out after ${Math.round(
            timeoutMs / 1000,
          )}s.`,
      });
    }

    return makeError({
      method,
      path: normalizedPath,
      errorType: "NETWORK",
      message:
        "AERIS backend is unreachable. Start FastAPI on port 8000 and retry.",
    });
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchBaseline(flightId = "F102") {
  const [airspace, disruptions, flight, network] =
    await Promise.all([
      requestJson("/airspace", { timeoutMs: 5000 }),
      requestJson("/disruptions", { timeoutMs: 5000 }),
      requestJson(
        `/flights/${encodeURIComponent(flightId)}`,
        { timeoutMs: 5000 },
      ),
      requestJson("/network/metrics", { timeoutMs: 5000 }),
    ]);

  const responses = { airspace, disruptions, flight, network };
  const failed = Object.entries(responses).filter(
    ([, result]) => !result.ok,
  );

  if (failed.length) {
    return {
      ok: false,
      data: responses,
      error: failed
        .map(
          ([name, result]) =>
            `${name}: ${result.error}`,
        )
        .join(" | "),
    };
  }

  return {
    ok: true,
    data: {
      airspace: airspace.data,
      disruptions: disruptions.data,
      flight: flight.data,
      network: network.data,
    },
    error: null,
  };
}

export async function resetCopilot() {
  return requestJson("/copilot/reset", {
    method: "POST",
    timeoutMs: 5000,
    body: JSON.stringify({}),
  });
}

export async function runCopilotRecommendation(payload = {}) {
  return requestJson("/copilot/recommend", {
    method: "POST",
    timeoutMs: 30000,
    body: JSON.stringify({
      ...FLAGSHIP_DEFAULTS,
      ...payload,
    }),
  });
}

export async function runCopilotInvestigation(payload = {}) {
  return requestJson("/copilot/investigate", {
    method: "POST",
    timeoutMs: 20000,
    body: JSON.stringify({
      ...FLAGSHIP_DEFAULTS,
      ...payload,
    }),
  });
}

export async function approveCopilotRun(payload) {
  return requestJson("/copilot/approve", {
    method: "POST",
    timeoutMs: 15000,
    body: JSON.stringify(payload),
  });
}

export async function rejectCopilotRun(payload) {
  return requestJson("/copilot/reject", {
    method: "POST",
    timeoutMs: 15000,
    body: JSON.stringify(payload),
  });
}

export async function applyIntervention(payload) {
  return requestJson("/apply", {
    method: "POST",
    timeoutMs: 10000,
    body: JSON.stringify(payload),
  });
}

export async function verifyIntervention(payload) {
  return requestJson("/verify", {
    method: "POST",
    timeoutMs: 10000,
    body: JSON.stringify(payload),
  });
}

export async function healthCheck() {
  return requestJson("/health", {
    timeoutMs: 5000,
  });
}

export async function fetchLiveOperations() {
  return requestJson("/operations/live", {
    timeoutMs: 5000,
  });
}

export async function startLiveReplay({
  stopAtMinute = 19,
  resetFirst = true,
} = {}) {
  return requestJson("/operations/replay/start", {
    method: "POST",
    timeoutMs: 5000,
    body: JSON.stringify({
      stop_at_minute: stopAtMinute,
      reset_first: resetFirst,
    }),
  });
}

export async function stopLiveReplay() {
  return requestJson("/operations/replay/stop", {
    method: "POST",
    timeoutMs: 5000,
    body: JSON.stringify({}),
  });
}

export async function resetLiveReplay() {
  return requestJson("/operations/replay/reset", {
    method: "POST",
    timeoutMs: 5000,
    body: JSON.stringify({}),
  });
}

export async function stepLiveReplay(minutes = 1) {
  return requestJson("/operations/replay/step", {
    method: "POST",
    timeoutMs: 5000,
    body: JSON.stringify({ minutes }),
  });
}

export function buildOperationsWebSocketUrl() {
  const explicit =
    import.meta.env.VITE_OPERATIONS_WS_URL;

  if (explicit) {
    return explicit;
  }

  const protocol =
    window.location.protocol === "https:"
      ? "wss:"
      : "ws:";

  return `${protocol}//${window.location.host}/ws/operations`;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function getFlagshipDefaults() {
  return { ...FLAGSHIP_DEFAULTS };
}

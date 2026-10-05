const RAW_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "/api";

const API_BASE_URL = String(RAW_API_BASE_URL).replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 15000;

const FLAGSHIP_DEFAULTS = {
  target_flight_id: "F102",
  scenario_id: "mumbai_weather_crisis_v2",
  decision_time_min: 19,
};


async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
  const method = (options.method || "GET").toUpperCase();
  const fullPath = `${API_BASE_URL}${path}`;

  const timeout = window.setTimeout(
    () => controller.abort(),
    timeoutMs,
  );

  try {
    const { timeoutMs: _ignoredTimeout, ...fetchOptions } = options;

    const response = await fetch(fullPath, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(fetchOptions.headers || {}),
      },
    });

    const contentType = response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      let detailMsg = "";
      if (typeof data === "object" && data !== null) {
        detailMsg = data.detail || data.error || data.message || JSON.stringify(data);
      } else {
        detailMsg = String(data);
      }

      let formattedError = "";
      let errorType = "CLIENT_ERROR";

      if (response.status === 404 && (path.includes("copilot") || String(detailMsg).toLowerCase().includes("run"))) {
        errorType = "RUN_NOT_FOUND";
        formattedError = [
          "Copilot run not found.",
          `${method} ${fullPath}`,
          `HTTP 404.`,
          detailMsg || "The backend no longer has this active run_id.",
          "Start a new AERIS run.",
        ].join("\n");
      } else if (response.status >= 500) {
        errorType = "SERVER_ERROR";
        formattedError = [
          "Backend server error.",
          `${method} ${fullPath}`,
          `HTTP ${response.status}.`,
          detailMsg || "Internal server error occurred on the backend.",
        ].join("\n");
      } else {
        formattedError = [
          "Request failed.",
          `${method} ${fullPath}`,
          `HTTP ${response.status}.`,
          detailMsg || "Request could not be processed.",
        ].join("\n");
      }

      return {
        ok: false,
        status: response.status,
        data: null,
        error: formattedError,
        detail: detailMsg,
        errorType,
        method,
        path: fullPath,
      };
    }

    return {
      ok: true,
      status: response.status,
      data,
      error: null,
      errorType: null,
      method,
      path: fullPath,
    };
  } catch (error) {
    let formattedError = "";
    let errorType = "CONNECTION_REFUSED";

    if (error?.name === "AbortError") {
      errorType = "TIMEOUT";
      formattedError = [
        "Backend request timed out.",
        `${method} ${fullPath}`,
        `No response received within ${timeoutMs / 1000}s.`,
        "Check backend status or network latency.",
      ].join("\n");
    } else {
      formattedError = [
        "Backend unavailable.",
        `${method} ${fullPath}`,
        `Unable to connect to AERIS backend.`,
        "Ensure the backend server is running on 127.0.0.1:8000.",
      ].join("\n");
    }

    return {
      ok: false,
      status: null,
      data: null,
      error: formattedError,
      detail: error?.message || null,
      errorType,
      method,
      path: fullPath,
    };
  } finally {
    window.clearTimeout(timeout);
  }
}


export async function fetchBaseline(
  flightId = "F102",
) {
  const [
    airspace,
    disruptions,
    flight,
    network,
  ] = await Promise.all([
    requestJson(
      "/airspace",
      {
        timeoutMs: 5000,
      },
    ),

    requestJson(
      "/disruptions",
      {
        timeoutMs: 5000,
      },
    ),

    requestJson(
      `/flights/${encodeURIComponent(
        flightId,
      )}`,
      {
        timeoutMs: 5000,
      },
    ),

    requestJson(
      "/network/metrics",
      {
        timeoutMs: 5000,
      },
    ),
  ]);

  const responses = {
    airspace,
    disruptions,
    flight,
    network,
  };

  const failed =
    Object.entries(
      responses,
    ).filter(
      ([, result]) =>
        !result.ok,
    );

  if (failed.length) {
    return {
      ok: false,
      data: responses,
      error:
        failed
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
      airspace:
        airspace.data,
      disruptions:
        disruptions.data,
      flight:
        flight.data,
      network:
        network.data,
    },

    error: null,
  };
}


export async function resetCopilot() {
  return requestJson(
    "/copilot/reset",
    {
      method: "POST",

      timeoutMs: 5000,

      body:
        JSON.stringify(
          {},
        ),
    },
  );
}


export async function runCopilotRecommendation(
  payload = {},
) {
  const requestPayload = {
    ...FLAGSHIP_DEFAULTS,
    ...payload,
  };

  return requestJson(
    "/copilot/recommend",
    {
      method: "POST",

      timeoutMs: 30000,

      body:
        JSON.stringify(
          requestPayload,
        ),
    },
  );
}


export async function runCopilotInvestigation(
  payload = {},
) {
  const requestPayload = {
    ...FLAGSHIP_DEFAULTS,
    ...payload,
  };

  return requestJson(
    "/copilot/investigate",
    {
      method: "POST",

      timeoutMs: 20000,

      body:
        JSON.stringify(
          requestPayload,
        ),
    },
  );
}


export async function approveCopilotRun(
  payload,
) {
  return requestJson(
    "/copilot/approve",
    {
      method: "POST",

      timeoutMs: 15000,

      body:
        JSON.stringify(
          payload,
        ),
    },
  );
}


export async function rejectCopilotRun(
  payload,
) {
  return requestJson(
    "/copilot/reject",
    {
      method: "POST",

      timeoutMs: 15000,

      body:
        JSON.stringify(
          payload,
        ),
    },
  );
}


export async function applyIntervention(
  payload,
) {
  return requestJson(
    "/apply",
    {
      method: "POST",

      timeoutMs: 10000,

      body:
        JSON.stringify(
          payload,
        ),
    },
  );
}


export async function verifyIntervention(
  payload,
) {
  return requestJson(
    "/verify",
    {
      method: "POST",

      timeoutMs: 10000,

      body:
        JSON.stringify(
          payload,
        ),
    },
  );
}


export async function healthCheck() {
  return requestJson(
    "/health",
    {
      timeoutMs: 5000,
    },
  );
}


export function getApiBaseUrl() {
  return API_BASE_URL;
}


export function getFlagshipDefaults() {
  return {
    ...FLAGSHIP_DEFAULTS,
  };
}
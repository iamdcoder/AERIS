const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

const DEFAULT_TIMEOUT_MS = 15000;

async function requestJson(
  path,
  options = {},
) {
  const controller =
    new AbortController();

  const timeoutMs =
    options.timeoutMs ||
    DEFAULT_TIMEOUT_MS;

  const timeout = window.setTimeout(
    () => controller.abort(),
    timeoutMs,
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      },
    );

    const contentType =
      response.headers.get(
        "content-type",
      ) || "";

    const data =
      contentType.includes(
        "application/json",
      )
        ? await response.json()
        : await response.text();

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error:
          typeof data === "object"
            ? data?.detail ||
              "Backend request failed."
            : String(data),
      };
    }

    return {
      ok: true,
      status: response.status,
      data,
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      data: null,
      error:
        error?.name === "AbortError"
          ? "Backend request timed out."
          : error?.message ||
            "Unable to reach AERIS backend.",
    };
  } finally {
    window.clearTimeout(
      timeout,
    );
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

  const failed = Object.entries(
    responses,
  ).filter(
    ([, result]) => !result.ok,
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
      airspace: airspace.data,
      disruptions: disruptions.data,
      flight: flight.data,
      network: network.data,
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
      body: JSON.stringify({}),
    },
  );
}


export async function runCopilotRecommendation(
  payload,
) {
  return requestJson(
    "/copilot/recommend",
    {
      method: "POST",
      timeoutMs: 30000,
      body: JSON.stringify(
        payload,
      ),
    },
  );
}


export async function runCopilotInvestigation(
  payload,
) {
  return requestJson(
    "/copilot/investigate",
    {
      method: "POST",
      timeoutMs: 20000,
      body: JSON.stringify(
        payload,
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
      body: JSON.stringify(
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
      body: JSON.stringify(
        payload,
      ),
    },
  );
}


/*
 * Low-level engine endpoints remain available.
 * They are useful for direct API testing and future
 * engine-specific UI workflows.
 */

export async function applyIntervention(
  payload,
) {
  return requestJson(
    "/apply",
    {
      method: "POST",
      timeoutMs: 10000,
      body: JSON.stringify(
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
      body: JSON.stringify(
        payload,
      ),
    },
  );
}


export function getApiBaseUrl() {
  return API_BASE_URL;
}
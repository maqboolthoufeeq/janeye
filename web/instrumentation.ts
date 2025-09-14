import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./instrumentation.node");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./instrumentation.edge");
  }
}

export async function onRequestError(
  error: unknown,
  request: { url: string; method: string }
) {
  Sentry.captureException(error, {
    tags: {
      url: request.url,
      method: request.method,
    },
  });
}

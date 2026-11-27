import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 5000;
const REQUEST_TIMEOUT_MS = 8000;
const continuePolling = () => true;

export function useMonitoringPoll(resourceId, read, {
  enabled = true,
  shouldContinue = continuePolling,
} = {}) {
  const [snapshot, setSnapshot] = useState(null);
  const lastObservation = useRef(null);

  useEffect(() => {
    if (resourceId == null || !enabled) return;

    let stopped = false;
    let terminal = false;
    let finished = false;
    let timer;
    let request;

    async function poll() {
      if (stopped || request || terminal || finished) return;

      const controller = new AbortController();
      request = controller;
      const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

      try {
        const data = await read(resourceId, controller.signal);
        if (stopped) return;
        if (controller.signal.aborted) throw new Error("The monitoring update timed out.");
        const observedAt = Date.parse(data.observed_at);
        if (Number.isFinite(observedAt)) {
          const previous = lastObservation.current;
          if (previous?.resourceId === resourceId && observedAt < previous.observedAt) {
            return;
          }
          lastObservation.current = { resourceId, observedAt };
        }

        setSnapshot({
          resourceId,
          data,
          receivedAt: Date.now(),
          receivedMonotonicAt: performance.now(),
          error: "",
          unavailable: false,
        });
        finished = !shouldContinue(data);
      } catch (error) {
        if (stopped) return;
        terminal = [401, 403, 404, 410].includes(error.status);
        setSnapshot((previous) => {
          const available = !terminal && previous?.resourceId === resourceId;
          return {
            resourceId,
            data: available ? previous.data : null,
            receivedAt: available ? previous.receivedAt : null,
            receivedMonotonicAt: available ? previous.receivedMonotonicAt : null,
            error: controller.signal.aborted ? "The monitoring update timed out." : error.message,
            unavailable: terminal,
          };
        });
      } finally {
        controller.abort();
        request = null;
        window.clearTimeout(timeout);
        if (!stopped && !terminal && !finished) timer = window.setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    function reconnect() {
      if (!stopped && !request && !terminal && !finished) {
        window.clearTimeout(timer);
        void poll();
      }
    }

    void poll();
    window.addEventListener("online", reconnect);
    return () => {
      stopped = true;
      request?.abort();
      window.clearTimeout(timer);
      window.removeEventListener("online", reconnect);
    };
  }, [resourceId, read, enabled, shouldContinue]);

  const updateData = useCallback((update) => {
    setSnapshot((previous) => previous?.resourceId === resourceId && previous.data
      ? { ...previous, data: update(previous.data) }
      : previous);
  }, [resourceId]);

  const current = snapshot?.resourceId === resourceId ? snapshot : null;
  return {
    data: current?.data ?? null,
    receivedAt: current?.receivedAt ?? null,
    receivedMonotonicAt: current?.receivedMonotonicAt ?? null,
    loading: resourceId != null && current === null,
    error: current?.error ?? "",
    unavailable: current?.unavailable ?? false,
    updateData,
  };
}

export function useMonitoringClock(enabled, receivedAt, clock = Date.now) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => setNow(clock()), 1000);
    return () => window.clearInterval(timer);
  }, [enabled, clock]);
  return Math.max(now, receivedAt ?? 0);
}


import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";

const API_URL = "http://127.0.0.1:8000";

function clearSession() {
  sessionStorage.removeItem("nexasense_token");
}

function getTokenExpiration(token) {
  const encodedPayload = token.split(".")[1];

  if (!encodedPayload) {
    throw new Error("Invalid token format");
  }

  const base64 = encodedPayload
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const paddedBase64 = base64.padEnd(
    Math.ceil(base64.length / 4) * 4,
    "="
  );

  const payload = JSON.parse(atob(paddedBase64));

  if (typeof payload.exp !== "number") {
    throw new Error("Missing token expiration");
  }

  return payload.exp * 1000;
}

export default function ProtectedRoute() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    const controller = new AbortController();
    let expirationTimer;
    let cancelled = false;

    const token = sessionStorage.getItem("nexasense_token");

    if (!token) {
  queueMicrotask(() => {
    if (!cancelled) {
      setStatus("unauthenticated");
    }
  });

  return () => {
    cancelled = true;
    controller.abort();
  };
}

    function expireSession() {
      if (cancelled) return;

      clearSession();
      setStatus("unauthenticated");
    }

    async function verifySession() {
      try {
        const expiresAt = getTokenExpiration(token);
        const remainingTime = expiresAt - Date.now();

        if (remainingTime <= 0) {
          throw new Error("Session expired");
        }

        const response = await fetch(`${API_URL}/api/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Session validation failed");
        }

        if (cancelled) return;

        const updatedRemainingTime = expiresAt - Date.now();

        if (updatedRemainingTime <= 0) {
          throw new Error("Session expired");
        }

        setStatus("authenticated");

        expirationTimer = window.setTimeout(
          expireSession,
          Math.min(updatedRemainingTime, 2147483647)
        );
      } catch (error) {
        if (cancelled || error.name === "AbortError") {
          return;
        }

        expireSession();
      }
    }

    function checkExpiration() {
      if (cancelled) return;

      const currentToken = sessionStorage.getItem(
        "nexasense_token"
      );

      if (!currentToken || currentToken !== token) {
        expireSession();
        return;
      }

      try {
        if (getTokenExpiration(token) <= Date.now()) {
          expireSession();
        }
      } catch {
        expireSession();
      }
    }

    verifySession();

    window.addEventListener("focus", checkExpiration);
    document.addEventListener(
      "visibilitychange",
      checkExpiration
    );

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(expirationTimer);
      window.removeEventListener("focus", checkExpiration);
      document.removeEventListener(
        "visibilitychange",
        checkExpiration
      );
    };
  }, []);

  if (status === "checking") {
    return (
      <main role="status" style={{ padding: "40px" }}>
        Verifying your session...
      </main>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

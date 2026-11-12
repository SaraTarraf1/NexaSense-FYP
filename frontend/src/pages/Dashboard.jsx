
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API_URL = "http://127.0.0.1:8000";

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    const token = sessionStorage.getItem("nexasense_token");

    fetch(`${API_URL}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Session expired");
        }
        return response.json();
      })
      .then((data) => setUser(data))
      .catch((error) => {
        if (error.name === "AbortError") return;
        sessionStorage.removeItem("nexasense_token");
        navigate("/login", { replace: true });
      });

    return () => controller.abort();
  }, [navigate]);

  
async function handleLogout() {
  const token = sessionStorage.getItem("nexasense_token");

  try {
    if (token) {
      const response = await fetch(
        "http://127.0.0.1:8000/api/auth/logout",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Server logout failed");
      }
    }
  } catch (error) {
    console.error("Logout request failed:", error);
    // Clear the local session even if the server is unavailable.
    // The token may remain valid server-side until expiration.
  } finally {
    sessionStorage.removeItem("nexasense_token");
    navigate("/login", { replace: true });
  }
}


  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "40px",
        background: "#f7f9fc",
        color: "#172c42",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "20px",
          flexWrap: "wrap",
        }}
      >
        <h1>NexaSense Dashboard</h1>

        <button
          onClick={handleLogout}
          style={{
            padding: "12px 24px",
            background: "#087e79",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Log out
        </button>
      </header>

      <section style={{ marginTop: "50px" }}>
        <h2>
          {user
            ? `Welcome, ${user.full_name}!`
            : "Loading your profile..."}
        </h2>

        <p>
          You have successfully logged in to NexaSense.
        </p>

        <p>
          This is your protected inspection workspace.
        </p>

        {user && (
          <div
            style={{
              marginTop: "24px",
              padding: "24px",
              background: "white",
              borderRadius: "12px",
              maxWidth: "500px",
            }}
          >
            <h3>Account Information</h3>
            <p><strong>Name:</strong> {user.full_name}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Role:</strong> {user.role}</p>
            <p>
              <strong>Status:</strong>{" "}
              {user.is_active ? "Active" : "Inactive"}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}

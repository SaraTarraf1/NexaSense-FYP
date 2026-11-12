
const API_BASE_URL = "http://127.0.0.1:8000";

export async function registerUser(formData) {
  const response = await fetch(
    `${API_BASE_URL}/api/auth/register`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        full_name: formData.fullName.trim(),
        email: formData.email.trim(),
        password: formData.password,
        accept_terms: formData.acceptTerms,
      }),
    }
  );

  const result = await response.json();

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error("This email address is already registered.");
    }

    if (response.status === 422) {
      throw new Error("Please check your registration information.");
    }

    throw new Error("Registration failed. Please try again.");
  }

  return result;
}

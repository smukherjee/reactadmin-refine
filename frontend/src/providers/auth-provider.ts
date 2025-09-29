import { AuthProvider } from "@refinedev/core";

export const authProvider: AuthProvider = {
  login: async ({ email, password }) => {
    try {
      const response = await fetch("http://localhost:8000/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (response.status === 200) {
        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        return {
          success: true,
          redirectTo: "/",
        };
      } else {
        return {
          success: false,
          error: {
            message: "Login failed",
            name: "Invalid credentials",
          },
        };
      }
    } catch (error) {
      return {
        success: false,
        error: {
          message: "Login failed",
          name: "Network error",
        },
      };
    }
  },

  logout: async () => {
    localStorage.removeItem("token");
    return {
      success: true,
      redirectTo: "/login",
    };
  },

  check: async () => {
    const token = localStorage.getItem("token");
    if (token) {
      return {
        authenticated: true,
      };
    }
    return {
      authenticated: false,
      redirectTo: "/login",
    };
  },

  getPermissions: async () => {
    // Implement based on JWT token claims
    return null;
  },

  getIdentity: async () => {
    // Implement to get user identity
    return null;
  },

  onError: async (error) => {
    console.error(error);
    return { error };
  },
};
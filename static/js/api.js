const STORAGE_KEYS = {
  accessToken: "access_token",
  refreshToken: "refresh_token",
  accessExpires: "access_token_expires_at",
  refreshExpires: "refresh_token_expires_at",
};

const API = {
  _refreshPromise: null,

  token() {
    return localStorage.getItem(STORAGE_KEYS.accessToken) || "";
  },

  refreshToken() {
    return localStorage.getItem(STORAGE_KEYS.refreshToken) || "";
  },

  accessExpiresAt() {
    return this._getTimestamp(STORAGE_KEYS.accessExpires);
  },

  refreshExpiresAt() {
    return this._getTimestamp(STORAGE_KEYS.refreshExpires);
  },

  setTokens(tokens = {}) {
    const { accessToken, refreshToken, expiresAt, refreshExpiresAt } = tokens;
    if (accessToken) {
      localStorage.setItem(STORAGE_KEYS.accessToken, accessToken);
    } else {
      localStorage.removeItem(STORAGE_KEYS.accessToken);
    }
    if (refreshToken) {
      localStorage.setItem(STORAGE_KEYS.refreshToken, refreshToken);
    } else {
      localStorage.removeItem(STORAGE_KEYS.refreshToken);
    }
    this._storeTimestamp(STORAGE_KEYS.accessExpires, expiresAt);
    this._storeTimestamp(STORAGE_KEYS.refreshExpires, refreshExpiresAt);
    localStorage.removeItem("token");
  },

  clearTokens() {
    localStorage.removeItem(STORAGE_KEYS.accessToken);
    localStorage.removeItem(STORAGE_KEYS.refreshToken);
    localStorage.removeItem(STORAGE_KEYS.accessExpires);
    localStorage.removeItem(STORAGE_KEYS.refreshExpires);
    localStorage.removeItem("token");
    this._refreshPromise = null;
    window.dispatchEvent(new CustomEvent("api:session-ended"));
  },

  hasSession() {
    if (!this.token()) return false;
    if (!this.isAccessExpired(0)) return true;
    const refresh = this.refreshToken();
    if (!refresh) return false;
    return !this.isRefreshExpired();
  },

  isAccessExpired(padding = 30000) {
    const exp = this.accessExpiresAt();
    if (!exp) return true;
    return Date.now() + padding >= exp;
  },

  isRefreshExpired(padding = 30000) {
    const exp = this.refreshExpiresAt();
    if (!exp) return false;
    return Date.now() + padding >= exp;
  },

  async ensureAccessToken() {
    if (!this.token()) return false;
    if (!this.isAccessExpired()) return true;
    return this.refreshAccessToken();
  },

  async refreshAccessToken() {
    if (!this.refreshToken() || this.isRefreshExpired()) {
      this.clearTokens();
      return false;
    }

    if (this._refreshPromise) {
      try {
        await this._refreshPromise;
        return true;
      } catch (err) {
        return false;
      }
    }

    this._refreshPromise = (async () => {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + this.refreshToken(),
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) {
        const msg = await this._extractError(res);
        throw new Error(msg);
      }
      const data = await res.json();
      this.setTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresAt: data.expires_at,
        refreshExpiresAt: data.refresh_expires_at,
      });
      return true;
    })();

    try {
      await this._refreshPromise;
      return true;
    } catch (err) {
      this.clearTokens();
      throw err;
    } finally {
      this._refreshPromise = null;
    }
  },

  async request(path, options = {}) {
    const { auth = "access", retry = true } = options;
    const fetchOptions = { ...options };
    delete fetchOptions.auth;
    delete fetchOptions.retry;

    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    if (auth === "access") {
      if (this.token()) {
        try {
          await this.ensureAccessToken();
        } catch (err) {
          this.clearTokens();
          throw err;
        }
      }
      const access = this.token();
      if (access) {
        headers.set("Authorization", "Bearer " + access);
      }
    } else if (auth === "refresh") {
      const refresh = this.refreshToken();
      if (refresh) {
        headers.set("Authorization", "Bearer " + refresh);
      }
    }

    const headerEntries = Array.from(headers.entries());
    if (headerEntries.length) {
      fetchOptions.headers = Object.fromEntries(headerEntries);
    } else {
      delete fetchOptions.headers;
    }

    const response = await fetch(path, fetchOptions);

    if (response.status === 401 && retry && auth === "access" && this.refreshToken()) {
      const refreshed = await this._handleUnauthorized();
      if (refreshed) {
        return this.request(path, { ...options, retry: false });
      }
    }

    if (!response.ok) {
      throw new Error(await this._extractError(response));
    }

    const ct = response.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      return response.json();
    }
    return response;
  },

  async _handleUnauthorized() {
    try {
      await this.refreshAccessToken();
      return this.token() !== "";
    } catch (err) {
      return false;
    }
  },

  _getTimestamp(key) {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const asNumber = Number(raw);
    if (!Number.isNaN(asNumber)) return asNumber;
    const parsed = Date.parse(raw);
    return Number.isNaN(parsed) ? null : parsed;
  },

  _storeTimestamp(key, value) {
    if (!value) {
      localStorage.removeItem(key);
      return;
    }
    const ts = typeof value === "number" ? value : Date.parse(value);
    if (Number.isNaN(ts)) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, String(ts));
    }
  },

  async _extractError(res) {
    let message = "Error " + res.status;
    try {
      const clone = res.clone();
      const data = await clone.json();
      message = data.message || data.error || data.msg || message;
    } catch (err) {
      try {
        const text = await res.text();
        if (text) message = text;
      } catch (err2) {
        // ignore
      }
    }
    return message;
  },
};

window.API = API;

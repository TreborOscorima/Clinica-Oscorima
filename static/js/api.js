const API = {
  token() { return localStorage.getItem("token") || ""; },
  setToken(t){ localStorage.setItem("token", t); },
  async request(path, options={}){
    const headers = options.headers || {};
    if (!headers["Content-Type"] && !(options.body instanceof FormData)){
      headers["Content-Type"] = "application/json";
    }
    const auth = this.token();
    if (auth) headers["Authorization"] = "Bearer " + auth;
    const res = await fetch(path, {...options, headers});
    if (!res.ok){
      let msg = "Error " + res.status;
      try { const j = await res.json(); msg = j.message || msg; } catch(e){}
      throw new Error(msg);
    }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json();
    return res;
  }
}
window.API = API;

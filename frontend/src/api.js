export const API = "http://localhost:8000";

const TOKEN_KEY = "token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Erreur levee quand le serveur repond 401 : le token est absent, invalide
 * ou expire. L'appelant doit deconnecter l'utilisateur cote client.
 */
export class ErreurAuth extends Error {}

async function requete(chemin, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API}${chemin}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    let detail = "Session expiree";
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new ErreurAuth(detail);
  }

  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return res.json();
}

export function inscription(email, motDePasse) {
  return requete("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, mot_de_passe: motDePasse }),
  });
}

export function connexion(email, motDePasse) {
  return requete("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, mot_de_passe: motDePasse }),
  });
}

export function moi() {
  return requete("/auth/me");
}

export function poserQuestion(question) {
  return requete("/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function statsAdmin() {
  return requete("/admin/stats");
}

export function listerUtilisateurs() {
  return requete("/admin/users");
}

export function changerRole(id, role) {
  return requete(`/admin/users/${id}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function supprimerUtilisateur(id) {
  return requete(`/admin/users/${id}`, { method: "DELETE" });
}

export function listerDocuments() {
  return requete("/admin/documents");
}

/**
 * Upload multipart : pas de Content-Type manuel, le navigateur doit fixer
 * lui-meme l'en-tete avec la boundary du FormData.
 */
export async function uploaderDocument(fichier) {
  const token = getToken();
  const corps = new FormData();
  corps.append("fichier", fichier);

  const res = await fetch(`${API}/admin/documents/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: corps,
  });

  if (res.status === 401) {
    clearToken();
    throw new ErreurAuth("Session expiree");
  }
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function supprimerDocument(nom) {
  return requete(`/admin/documents/${encodeURIComponent(nom)}`, { method: "DELETE" });
}

export function relancerIndexation() {
  return requete("/admin/documents/reindex", { method: "POST" });
}

export function statutIndexation() {
  return requete("/admin/documents/reindex/status");
}

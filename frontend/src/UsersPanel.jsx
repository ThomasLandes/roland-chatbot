import { useEffect, useState } from "react";
import { changerRole, listerUtilisateurs, supprimerUtilisateur } from "./api";

function formaterDate(iso) {
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export default function UsersPanel({ moi }) {
  const [utilisateurs, setUtilisateurs] = useState(null);
  const [erreur, setErreur] = useState("");
  const [enCours, setEnCours] = useState(null); // id de la ligne en cours de modif

  function charger() {
    setErreur("");
    listerUtilisateurs()
      .then(setUtilisateurs)
      .catch((e) => setErreur(e.message));
  }

  useEffect(() => {
    charger();
  }, []);

  async function basculerRole(u) {
    const nouveauRole = u.role === "admin" ? "user" : "admin";
    setEnCours(u.id);
    setErreur("");
    try {
      const maj = await changerRole(u.id, nouveauRole);
      setUtilisateurs((liste) => liste.map((x) => (x.id === u.id ? maj : x)));
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnCours(null);
    }
  }

  async function supprimer(u) {
    if (!window.confirm(`Supprimer definitivement le compte ${u.email} ?`)) return;
    setEnCours(u.id);
    setErreur("");
    try {
      await supprimerUtilisateur(u.id);
      setUtilisateurs((liste) => liste.filter((x) => x.id !== u.id));
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnCours(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Utilisateurs</h2>
          <button
            onClick={charger}
            className="text-sm text-slate-500 hover:text-slate-900 border border-slate-300 rounded-lg px-3 py-1.5"
          >
            Rafraichir
          </button>
        </div>

        {erreur && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
            {erreur}
          </p>
        )}

        {utilisateurs === null ? (
          <p className="text-sm text-slate-500">Chargement...</p>
        ) : (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="text-left font-medium px-4 py-2.5">E-mail</th>
                  <th className="text-left font-medium px-4 py-2.5">Role</th>
                  <th className="text-left font-medium px-4 py-2.5">Inscrit le</th>
                  <th className="text-right font-medium px-4 py-2.5">Actions</th>
                </tr>
              </thead>
              <tbody>
                {utilisateurs.map((u) => {
                  const soi = u.id === moi.id;
                  const occupe = enCours === u.id;
                  return (
                    <tr key={u.id} className="border-t border-slate-100">
                      <td className="px-4 py-2.5 text-slate-800">
                        {u.email}
                        {soi && <span className="text-xs text-slate-400 ml-1.5">(toi)</span>}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                            u.role === "admin"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {u.role === "admin" ? "Administrateur" : "Utilisateur"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-slate-500">{formaterDate(u.created_at)}</td>
                      <td className="px-4 py-2.5">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => basculerRole(u)}
                            disabled={soi || occupe}
                            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            {u.role === "admin" ? "Retrograder" : "Promouvoir admin"}
                          </button>
                          <button
                            onClick={() => supprimer(u)}
                            disabled={soi || occupe}
                            className="text-xs border border-red-200 text-red-600 rounded-lg px-2.5 py-1 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-xs text-slate-400 mt-3">
          Impossible de modifier ton propre compte ici, ou de retirer/supprimer le dernier
          administrateur : ces actions sont bloquees cote serveur.
        </p>
      </div>
    </div>
  );
}

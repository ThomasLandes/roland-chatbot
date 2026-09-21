import { useState } from "react";
import { connexion, inscription, setToken } from "./api";

export default function Login({ onAuth }) {
  const [mode, setMode] = useState("connexion"); // "connexion" | "inscription"
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(false);

  async function valider(e) {
    e.preventDefault();
    setErreur("");

    if (mode === "inscription" && motDePasse !== confirmation) {
      setErreur("Les mots de passe ne correspondent pas");
      return;
    }

    setChargement(true);
    try {
      const data =
        mode === "connexion"
          ? await connexion(email, motDePasse)
          : await inscription(email, motDePasse);
      setToken(data.access_token);
      onAuth({ email: data.email, role: data.role });
    } catch (err) {
      setErreur(err.message || "Une erreur est survenue");
    } finally {
      setChargement(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold text-slate-900 text-center">Assistant Roland</h1>
        <p className="text-xs text-slate-500 text-center mt-1 mb-6">
          Documentation technique instruments Roland
        </p>

        <div className="flex bg-slate-100 rounded-lg p-1 mb-6 text-sm">
          <button
            type="button"
            onClick={() => {
              setMode("connexion");
              setErreur("");
            }}
            className={`flex-1 rounded-md py-1.5 font-medium transition ${
              mode === "connexion" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
            }`}
          >
            Connexion
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("inscription");
              setErreur("");
            }}
            className={`flex-1 rounded-md py-1.5 font-medium transition ${
              mode === "inscription" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
            }`}
          >
            Creer un compte
          </button>
        </div>

        <form onSubmit={valider} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">E-mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-900"
              placeholder="vous@exemple.com"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Mot de passe</label>
            <input
              type="password"
              required
              minLength={8}
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-900"
              placeholder="8 caracteres minimum"
            />
          </div>

          {mode === "inscription" && (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Confirmer le mot de passe
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-slate-900"
              />
            </div>
          )}

          {erreur && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {erreur}
            </p>
          )}

          <button
            type="submit"
            disabled={chargement}
            className="w-full bg-slate-900 text-white rounded-lg py-2.5 text-sm font-medium disabled:opacity-40 mt-2"
          >
            {chargement
              ? "..."
              : mode === "connexion"
              ? "Se connecter"
              : "Creer mon compte"}
          </button>
        </form>
      </div>
    </div>
  );
}

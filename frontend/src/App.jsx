import { useState, useEffect, useRef } from "react";
import Login from "./Login.jsx";
import UsersPanel from "./UsersPanel.jsx";
import DocumentsPanel from "./DocumentsPanel.jsx";
import { ErreurAuth, clearToken, getToken, moi, poserQuestion, statsAdmin } from "./api";

export default function App() {
  const [user, setUser] = useState(null);
  const [verificationEnCours, setVerificationEnCours] = useState(true);
  const [vue, setVue] = useState("chat"); // "chat" | "utilisateurs" | "documents"

  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [chargement, setChargement] = useState(false);
  const [stats, setStats] = useState(null);
  const bas = useRef(null);
  const envoiEnCours = useRef(false);

  function deconnecter() {
    clearToken();
    setUser(null);
    setMessages([]);
    setStats(null);
  }

  // Au chargement : si un token est deja stocke, on verifie qu'il est
  // toujours valide aupres du serveur avant d'afficher le chat.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setVerificationEnCours(false);
      return;
    }
    moi()
      .then((u) => setUser(u))
      .catch(() => {})
      .finally(() => setVerificationEnCours(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    if (user.role === "admin") {
      statsAdmin()
        .then(setStats)
        .catch((e) => {
          if (e instanceof ErreurAuth) deconnecter();
          setStats(null);
        });
    } else {
      setStats(null);
    }
  }, [user]);

  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chargement]);

  async function envoyer() {
    const q = question.trim();
    // Un verrou en ref (pas seulement l'etat React) : l'etat "chargement" ne
    // se met a jour qu'au prochain rendu, ce qui laisse une fenetre ou un
    // appui prolonge sur Entree (repetition clavier) peut declencher
    // plusieurs envois avant que React n'ait re-rendu.
    if (!q || envoiEnCours.current) return;
    envoiEnCours.current = true;

    setMessages((m) => [...m, { role: "user", texte: q }]);
    setQuestion("");
    setChargement(true);

    try {
      const data = await poserQuestion(q);
      setMessages((m) => [...m, { role: "bot", ...data }]);
    } catch (e) {
      if (e instanceof ErreurAuth) {
        deconnecter();
        return;
      }
      setMessages((m) => [
        ...m,
        { role: "bot", reponse: `Erreur de connexion a l'API : ${e.message}`, sources: [], erreur: true },
      ]);
    } finally {
      setChargement(false);
      envoiEnCours.current = false;
    }
  }

  if (verificationEnCours) {
    return <div className="min-h-screen bg-slate-100" />;
  }

  if (!user) {
    return <Login onAuth={setUser} />;
  }

  const exemples = [
    "Comment sauvegarder un pattern sur le TR-1000 ?",
    "Comment regler le tempo sur le TB-03 ?",
    "Comment synchroniser le JU-06A en MIDI ?",
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Assistant Roland</h1>
          <p className="text-xs text-slate-400">
            Documentation technique instruments Roland
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-300">{user.email}</span>
          <span
            className={`text-xs rounded-full px-2.5 py-1 font-medium ${
              user.role === "admin"
                ? "bg-amber-500/20 text-amber-300"
                : "bg-slate-700 text-slate-300"
            }`}
          >
            {user.role === "admin" ? "Administrateur" : "Utilisateur"}
          </span>
          {user.role === "admin" && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setVue(vue === "utilisateurs" ? "chat" : "utilisateurs")}
                className="text-sm text-slate-300 hover:text-white border border-slate-600 rounded-lg px-3 py-1.5"
              >
                {vue === "utilisateurs" ? "Retour au chat" : "Utilisateurs"}
              </button>
              <button
                onClick={() => setVue(vue === "documents" ? "chat" : "documents")}
                className="text-sm text-slate-300 hover:text-white border border-slate-600 rounded-lg px-3 py-1.5"
              >
                {vue === "documents" ? "Retour au chat" : "Documents"}
              </button>
            </div>
          )}
          <button
            onClick={deconnecter}
            className="text-sm text-slate-300 hover:text-white border border-slate-600 rounded-lg px-3 py-1.5"
          >
            Deconnexion
          </button>
        </div>
      </header>

      {vue === "utilisateurs" && user.role === "admin" ? (
        <UsersPanel moi={user} />
      ) : vue === "documents" && user.role === "admin" ? (
        <DocumentsPanel />
      ) : (
        <>
      {user.role === "admin" && stats && (
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-3 text-xs text-amber-900 flex flex-wrap gap-6">
          <span><b>{stats.documents}</b> documents</span>
          <span><b>{stats.chunks_total}</b> chunks</span>
          <span>Fournisseur : <b>{stats.config.provider}</b></span>
          <span>Seuil : <b>{stats.config.seuil_hors_perimetre}</b></span>
          <span>Questions : <b>{stats.usage.questions_posees}</b></span>
          <span>Refus : <b>{stats.usage.refus}</b></span>
          <span>Temps moyen : <b>{stats.usage.duree_moyenne_s}s</b></span>
        </div>
      )}

      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 mt-12">
              <p className="mb-4">Posez une question sur votre instrument Roland.</p>
              <div className="flex flex-col gap-2 items-center">
                {exemples.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setQuestion(ex)}
                    className="text-sm bg-white border border-slate-300 rounded-full px-4 py-1.5 hover:bg-slate-50"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="bg-slate-900 text-white rounded-2xl rounded-br-sm px-4 py-2.5 max-w-[75%]">
                  {m.texte}
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start">
                <div
                  className={`rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%] ${
                    m.erreur
                      ? "bg-red-50 border border-red-200"
                      : m.hors_perimetre
                      ? "bg-orange-50 border border-orange-200"
                      : "bg-white border border-slate-200"
                  }`}
                >
                  <p className="whitespace-pre-wrap text-slate-800">{m.reponse}</p>

                  {m.sources?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <p className="text-xs font-semibold text-slate-500 mb-1">
                        Sources
                      </p>
                      {m.sources.map((s) => (
                        <div key={s.n} className="text-xs text-slate-600">
                          [{s.n}] {s.source} &mdash; page {s.page}
                          {user.role === "admin" && ` (distance ${s.distance})`}
                        </div>
                      ))}
                    </div>
                  )}

                  {m.duree != null && (
                    <p className="text-xs text-slate-400 mt-2">{m.duree}s</p>
                  )}

                  {user.role === "admin" && m.debug && (
                    <details className="mt-3 pt-3 border-t border-slate-200">
                      <summary className="text-xs font-semibold text-slate-500 cursor-pointer">
                        Details techniques
                      </summary>
                      <div className="mt-2 text-xs text-slate-600 space-y-1">
                        <p>Modele detecte : {m.debug.modele_detecte || "aucun"}</p>
                        <p>Requete enrichie : {m.debug.requete_enrichie}</p>
                        {m.debug.cause_refus && <p>Cause du refus : {m.debug.cause_refus}</p>}
                      </div>
                      <div className="mt-2 space-y-2">
                        {m.debug.chunks.map((c) => (
                          <div key={c.n} className="bg-slate-50 rounded p-2 text-xs">
                            <div className="font-mono text-slate-500">
                              [{c.n}] {c.source} p.{c.page} &mdash; distance {c.distance}
                            </div>
                            <div className="text-slate-600 mt-1">{c.extrait}...</div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            )
          )}

          {chargement && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 text-slate-400 text-sm">
                Recherche dans la documentation...
              </div>
            </div>
          )}
          <div ref={bas} />
        </div>
      </main>

      <footer className="border-t border-slate-300 bg-white px-6 py-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.repeat && envoyer()}
            disabled={chargement}
            placeholder="Posez votre question..."
            className="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-slate-900 disabled:opacity-60"
          />
          <button
            onClick={envoyer}
            disabled={chargement || !question.trim()}
            className="bg-slate-900 text-white px-6 rounded-lg disabled:opacity-40"
          >
            Envoyer
          </button>
        </div>
        <p className="max-w-3xl mx-auto text-xs text-slate-400 mt-2">
          Cet assistant repond uniquement a partir de la documentation Roland indexee.
          Verifiez les informations critiques dans le manuel officiel.
        </p>
      </footer>
        </>
      )}
    </div>
  );
}

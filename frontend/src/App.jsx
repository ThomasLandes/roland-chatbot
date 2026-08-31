import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";

export default function App() {
  const [profil, setProfil] = useState(
    () => localStorage.getItem("profil") || "user"
  );
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [chargement, setChargement] = useState(false);
  const [stats, setStats] = useState(null);
  const bas = useRef(null);

  useEffect(() => {
    localStorage.setItem("profil", profil);
    if (profil === "admin") {
      fetch(`${API}/admin/stats`)
        .then((r) => r.json())
        .then(setStats)
        .catch(() => setStats(null));
    }
  }, [profil]);

  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chargement]);

  async function envoyer() {
    const q = question.trim();
    if (!q || chargement) return;

    setMessages((m) => [...m, { role: "user", texte: q }]);
    setQuestion("");
    setChargement(true);

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, profil }),
      });
      if (!res.ok) throw new Error(`Erreur ${res.status}`);
      const data = await res.json();
      setMessages((m) => [...m, { role: "bot", ...data }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "bot", reponse: `Erreur de connexion a l'API : ${e.message}`, sources: [], erreur: true },
      ]);
    } finally {
      setChargement(false);
    }
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
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-300">Profil</label>
          <select
            value={profil}
            onChange={(e) => setProfil(e.target.value)}
            className="bg-slate-700 text-white text-sm rounded px-3 py-1.5 outline-none"
          >
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
        </div>
      </header>

      {profil === "admin" && stats && (
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
                          {profil === "admin" && ` (distance ${s.distance})`}
                        </div>
                      ))}
                    </div>
                  )}

                  {m.duree != null && (
                    <p className="text-xs text-slate-400 mt-2">{m.duree}s</p>
                  )}

                  {profil === "admin" && m.debug && (
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
            onKeyDown={(e) => e.key === "Enter" && envoyer()}
            placeholder="Posez votre question..."
            className="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-slate-900"
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
    </div>
  );
}
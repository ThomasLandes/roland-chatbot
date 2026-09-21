import { useEffect, useRef, useState } from "react";
import {
  listerDocuments,
  relancerIndexation,
  statutIndexation,
  supprimerDocument,
  uploaderDocument,
} from "./api";

function formaterTaille(octets) {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${(octets / 1024).toFixed(1)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

const LIBELLE_PHASE = {
  chargement: "Chargement du modele d'embeddings...",
  indexation: "Indexation des documents...",
};

export default function DocumentsPanel() {
  const [documents, setDocuments] = useState(null);
  const [erreur, setErreur] = useState("");
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [indexationEnCours, setIndexationEnCours] = useState(false);
  const [progression, setProgression] = useState(null);
  const [dernierResume, setDernierResume] = useState(null);
  const [suppressionEnCours, setSuppressionEnCours] = useState(null); // nom du fichier en cours de suppression
  const inputFichier = useRef(null);

  function charger() {
    setErreur("");
    listerDocuments()
      .then(setDocuments)
      .catch((e) => setErreur(e.message));
  }

  useEffect(() => {
    charger();
  }, []);

  async function envoyerFichier(e) {
    const fichier = e.target.files?.[0];
    if (!fichier) return;
    setErreur("");
    setDernierResume(null);
    setEnvoiEnCours(true);
    try {
      await uploaderDocument(fichier);
      charger();
    } catch (err) {
      setErreur(err.message);
    } finally {
      setEnvoiEnCours(false);
      if (inputFichier.current) inputFichier.current.value = "";
    }
  }

  async function relancer() {
    setErreur("");
    setDernierResume(null);
    setProgression(null);
    setIndexationEnCours(true);

    // La requete /reindex ne repond qu'une fois l'indexation terminee (elle
    // peut prendre du temps). On interroge /reindex/status en parallele,
    // a intervalle regulier, pour afficher une vraie progression pendant
    // l'attente plutot qu'un simple message statique.
    const intervalle = setInterval(() => {
      statutIndexation()
        .then(setProgression)
        .catch(() => {});
    }, 600);

    try {
      const resume = await relancerIndexation();
      setDernierResume(resume);
      charger();
    } catch (err) {
      setErreur(err.message);
    } finally {
      clearInterval(intervalle);
      setIndexationEnCours(false);
      setProgression(null);
    }
  }

  async function supprimer(nom) {
    if (!window.confirm(`Supprimer ${nom} du corpus ?`)) return;
    setErreur("");
    setDernierResume(null);
    setSuppressionEnCours(nom);
    try {
      await supprimerDocument(nom);
      charger();
    } catch (err) {
      setErreur(err.message);
    } finally {
      setSuppressionEnCours(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Documents</h2>
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

        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4 flex flex-wrap items-center gap-3">
          <label className="text-sm bg-slate-900 text-white rounded-lg px-4 py-2 cursor-pointer hover:bg-slate-800 disabled:opacity-40">
            {envoiEnCours ? "Envoi..." : "Choisir un PDF"}
            <input
              ref={inputFichier}
              type="file"
              accept="application/pdf"
              onChange={envoyerFichier}
              disabled={envoiEnCours || indexationEnCours}
              className="hidden"
            />
          </label>

          <button
            onClick={relancer}
            disabled={indexationEnCours || envoiEnCours}
            className="text-sm border border-slate-300 rounded-lg px-4 py-2 hover:bg-slate-50 disabled:opacity-40 flex items-center gap-2"
          >
            {indexationEnCours && (
              <span className="inline-block h-3.5 w-3.5 rounded-full border-2 border-slate-400 border-t-transparent animate-spin" />
            )}
            {indexationEnCours ? "Indexation en cours..." : "Relancer l'indexation"}
          </button>

          <p className="text-xs text-slate-400 w-full">
            Le nouveau PDF n'est pris en compte par le chatbot qu'apres avoir
            relance l'indexation (recalcule l'ensemble du corpus, peut prendre
            un moment).
          </p>

          {indexationEnCours && (
            <div className="w-full">
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span>
                  {LIBELLE_PHASE[progression?.phase] || "Preparation..."}
                  {progression?.fichier && ` (${progression.fichier})`}
                </span>
                {progression?.total > 0 && (
                  <span>
                    {progression.traites} / {progression.total}
                  </span>
                )}
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                {progression?.total > 0 ? (
                  <div
                    className="h-full bg-slate-900 rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${Math.min(
                        100,
                        (progression.traites / progression.total) * 100
                      )}%`,
                    }}
                  />
                ) : (
                  <div className="h-full w-full bg-slate-900 rounded-full animate-pulse" />
                )}
              </div>
            </div>
          )}
        </div>

        {dernierResume && (
          <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 mb-4">
            Indexation terminee : {dernierResume.documents} document(s),{" "}
            {dernierResume.chunks_total} chunks, modeles reconnus :{" "}
            {dernierResume.modeles?.join(", ") || "aucun"}.
          </p>
        )}

        {documents === null ? (
          <p className="text-sm text-slate-500">Chargement...</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-slate-500">Aucun document indexe pour le moment.</p>
        ) : (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="text-left font-medium px-4 py-2.5">Fichier</th>
                  <th className="text-left font-medium px-4 py-2.5">Taille</th>
                  <th className="text-right font-medium px-4 py-2.5">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.nom} className="border-t border-slate-100">
                    <td className="px-4 py-2.5 text-slate-800">{d.nom}</td>
                    <td className="px-4 py-2.5 text-slate-500">
                      {formaterTaille(d.taille_octets)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => supprimer(d.nom)}
                        disabled={suppressionEnCours === d.nom || indexationEnCours}
                        className="text-xs border border-red-200 text-red-600 rounded-lg px-2.5 py-1 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        {suppressionEnCours === d.nom ? "Suppression..." : "Supprimer"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {documents !== null && documents.length > 0 && (
          <p className="text-xs text-slate-400 mt-3">
            La suppression retire le fichier du disque mais pas encore ses
            passages du chatbot : pense a relancer l'indexation ensuite pour
            que ca prenne effet.
          </p>
        )}
      </div>
    </div>
  );
}

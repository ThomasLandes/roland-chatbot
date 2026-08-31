import requests

BASE = "http://localhost:8000"

print("--- /health")
print(requests.get(f"{BASE}/health").json())

print("\n--- /ask profil user")
r = requests.post(f"{BASE}/ask", json={
    "question": "Comment regler le tempo sur le TR-1000 ?",
    "profil": "user",
}).json()
print(r["reponse"][:400])
print("Sources :", r["sources"])
print("Duree :", r["duree"], "s")

print("\n--- /ask profil admin")
r = requests.post(f"{BASE}/ask", json={
    "question": "Comment regler le tempo sur le TR-1000 ?",
    "profil": "admin",
}).json()
print("Modele detecte :", r["debug"]["modele_detecte"])
print("Requete enrichie :", r["debug"]["requete_enrichie"])
for c in r["debug"]["chunks"][:3]:
    print(f"  [{c['n']}] {c['source']} p.{c['page']} dist={c['distance']}")

print("\n--- /ask hors perimetre")
r = requests.post(f"{BASE}/ask", json={
    "question": "Quelle est la recette de la tarte aux pommes ?",
    "profil": "user",
}).json()
print("Hors perimetre :", r["hors_perimetre"])

print("\n--- /admin/stats")
print(requests.get(f"{BASE}/admin/stats").json())
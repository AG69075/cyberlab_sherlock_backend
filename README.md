# Sherlock — Backend

Backend Flask du module Sherlock de [cyberlab](https://github.com/AG69075), une webapp Flutter d'outils de reconnaissance réseau. Ce service expose [Sherlock](https://github.com/sherlock-project/sherlock) (recherche de pseudos sur des réseaux sociaux/plateformes) via une petite API HTTP en streaming (Server-Sent Events). 

## Architecture

```
Flutter webapp (navigateur)
        │  HTTPS, CORS
        ▼
Cloudflare Worker
        │  HTTPS
        ▼
Cloudflare Tunnel (cloudflared)
        │  réseau Docker interne
        ▼
Backend Flask + Gunicorn (ce repo, port 7100) ── sherlock
```

Le backend n'a pas vocation à être exposé directement : `cloudflared` établit une connexion sortante vers Cloudflare, et le Worker est le point d'entrée public. La réponse SSE est relayée en flux par le Worker jusqu'au navigateur.

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/sherlock-stream?username=<pseudo>` | Lance une recherche Sherlock et streame la sortie ligne par ligne (SSE) |

Détails de `/api/sherlock-stream` :

- `username` : requis, `[a-zA-Z0-9._-]`, 1 à 64 caractères, ne peut pas commencer par `-`. Sinon : `400`.
- Réponse : `text/event-stream`, un événement `data: ...` par ligne de sortie de Sherlock (séquences ANSI/OSC retirées), terminé par `data: Recherche terminée`.
- Limité à 5 requêtes/minute et 30/heure par IP (`429` au-delà). L'IP réelle est lue dans l'en-tête `CF-Connecting-IP` (repli sur l'adresse source), sinon tous les visiteurs partageraient le compteur du proxy.

## Variables d'environnement

| Variable | Requise | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | Non | Liste d'origines autorisées en CORS, séparées par des virgules. Par défaut : `*` (à restreindre en production). |

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

Le serveur écoute sur `http://0.0.0.0:7100`. Sherlock est installé par `requirements.txt` (paquet `sherlock-project`), aucune dépendance système supplémentaire.

## Déploiement (Docker + Cloudflare Tunnel)

```bash
docker build -t cyberlab-sherlock-backend .
docker run -p 7100:7100 -e ALLOWED_ORIGINS=https://ton-frontend.com cyberlab-sherlock-backend
```

L'image est multi-stage (`python:3.11-alpine`), tourne en utilisateur non-root (`10001`) et embarque un `HEALTHCHECK` TCP sur le port `7100`. En production, ne pas publier le port sur l'hôte : `cloudflared` (même réseau Docker) route le *Public Hostname* du tunnel vers `http://<nom-du-service>:7100`, et le Worker Cloudflare appelle ce hostname. Gunicorn tourne avec `--worker-class gthread --threads 4` et **1 seul process**, pour que le rate limiting en mémoire soit cohérent entre toutes les requêtes.

## Sécurité

Ce service exécute une commande système (`sherlock`) à partir d'une entrée utilisateur. Les protections en place :

- **Pas de shell** : `subprocess.Popen` avec tableau d'arguments, jamais de concaténation de chaîne shell.
- **Validation stricte** en entrée : regex `[a-zA-Z0-9._-]{1,64}`, rejet des valeurs commençant par `-`.
- **Séparateur `--`** : le pseudo est passé à `sherlock` après `--`, pour empêcher toute interprétation comme flag CLI.
- **Rate limiting** : 5 requêtes/min et 30/h par IP.
- **Durée bornée** : 120 s max par recherche (kill du process au-delà).
- **Nettoyage des processus** : le process est tué si le client se déconnecte en cours de stream.
- **Sortie assainie** : séquences d'échappement ANSI/OSC supprimées avant envoi au client.
- **CORS configurable** via `ALLOWED_ORIGINS`.
- **Conteneur non-root**, sans privilèges supplémentaires.
- **Exposition réseau limitée** : accès public uniquement via le Worker et le tunnel Cloudflare sortant.

> Contrairement au backend DNS Analyzer, ce service ne vérifie pas de token `X-Internal-Token` : la confiance repose sur le fait qu'il n'est joignable que via le tunnel. `CF-Connecting-IP` n'est fiable que dans ce cas ; si le port `7100` était publié directement, un client pourrait falsifier l'en-tête et contourner le rate limiting.

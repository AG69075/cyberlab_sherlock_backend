# Sherlock — Backend

Backend Flask du module Sherlock de [cyberlab](https://github.com/AG69075), une webapp Flutter d'outils de reconnaissance réseau. Ce service expose [Sherlock](https://github.com/sherlock-project/sherlock) (recherche de pseudos sur des réseaux sociaux/plateformes) via une petite API HTTP en streaming (Server-Sent Events).

## Architecture

```
Flutter webapp (navigateur)
        │  HTTP(S), CORS (ALLOWED_ORIGINS)
        ▼
Backend Flask + Gunicorn (ce repo, port 7100) ── sherlock
```

Le backend est un service unique : le navigateur l'appelle directement et lit la réponse en flux (`EventSource` / `fetch` streaming). Le conteneur Docker écoute sur le port `7100`.

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/sherlock-stream?username=<pseudo>` | Lance une recherche Sherlock et streame la sortie ligne par ligne (SSE) |

Détails de `/api/sherlock-stream` :

- `username` : requis, `[a-zA-Z0-9._-]`, 1 à 64 caractères, ne peut pas commencer par `-`. Sinon : `400`.
- Réponse : `text/event-stream`, un événement `data: ...` par ligne de sortie de Sherlock (séquences ANSI/OSC retirées), terminé par `data: Recherche terminée`.
- Limité à 5 requêtes/minute et 30/heure par IP (`429` au-delà).

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

## Déploiement (Docker)

```bash
docker build -t cyberlab-sherlock-backend .
docker run -p 7100:7100 -e ALLOWED_ORIGINS=https://ton-frontend.com cyberlab-sherlock-backend
```

L'image est multi-stage (`python:3.11-alpine`), tourne en utilisateur non-root (`10001`) et embarque un `HEALTHCHECK` TCP sur le port `7100`. Gunicorn tourne avec `--worker-class gthread --threads 4` et **1 seul process**, pour que le rate limiting en mémoire soit cohérent entre toutes les requêtes.

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

> Contrairement au backend DNS Analyzer, ce service n'a pas d'authentification par token ni de tunnel : si le port `7100` est exposé sur Internet, restreindre `ALLOWED_ORIGINS` et placer un reverse proxy ou un tunnel devant.

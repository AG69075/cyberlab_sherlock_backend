# cyberlab_sherlock_backend

Backend Flask minimaliste qui expose [Sherlock](https://github.com/sherlock-project/sherlock) (recherche de pseudos sur des réseaux sociaux/plateformes) via un endpoint HTTP en streaming (Server-Sent Events).

## Endpoint

### `GET /api/sherlock-stream?username=<pseudo>`

Lance une recherche Sherlock pour `username` et streame les résultats ligne par ligne au format SSE.

- `username` : requis, `[a-zA-Z0-9._-]`, 1 à 64 caractères, ne peut pas commencer par `-`.
- Réponse : `text/event-stream`, un événement `data: ...` par ligne de sortie de Sherlock, terminé par `data: Recherche terminée`.
- Limité à 5 requêtes/minute et 30/heure par IP.

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

Le serveur écoute sur `http://0.0.0.0:7100`.

## Lancer avec Docker

```bash
docker build -t cyberlab-sherlock-backend .
docker run -p 7100:7100 cyberlab-sherlock-backend
```

## Variables d'environnement

| Variable          | Défaut | Description                                                                 |
|--------------------|--------|-------------------------------------------------------------------------------|
| `ALLOWED_ORIGINS`  | `*`    | Liste d'origines CORS autorisées, séparées par des virgules. À restreindre en production. |

## Notes de sécurité

- Le nom d'utilisateur est passé à la commande `sherlock` après un séparateur `--` pour empêcher toute interprétation comme flag CLI.
- Chaque recherche est bornée à 120s max (kill du process au-delà).
- Le process est tué si le client se déconnecte en cours de stream.
- Gunicorn tourne avec `--worker-class gthread --threads 4` (1 seul process) pour que le rate limiting in-memory soit cohérent entre toutes les requêtes.

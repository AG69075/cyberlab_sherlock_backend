import os
import re
import subprocess
import threading

from flask import Flask, Response, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# En prod, fixe ALLOWED_ORIGINS="https://ton-frontend.com" pour ne pas rester en wildcard.
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
CORS(app, origins=ALLOWED_ORIGINS.split(",") if ALLOWED_ORIGINS != "*" else "*")

limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["30 per hour"])

USERNAME_RE = re.compile(r'^[a-zA-Z0-9._-]{1,64}$')
SHERLOCK_MAX_RUNTIME_SECONDS = 120  # borne dure sur la durée totale du scan


def is_valid_username(username):
    return bool(username) and not username.startswith('-') and bool(USERNAME_RE.match(username))


@app.route('/api/sherlock-stream', methods=['GET'])
@limiter.limit("5 per minute")
def sherlock_stream():
    username = request.args.get('username', '')

    if not is_valid_username(username):
        return Response("Nom d'utilisateur invalide", status=400)

    def generate():
        process = subprocess.Popen(
            # "--" empêche username d'être interprété comme un flag sherlock
            ["sherlock", "--timeout", "10", "--", username],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        killer = threading.Timer(SHERLOCK_MAX_RUNTIME_SECONDS, process.kill)
        killer.start()
        try:
            for line in iter(process.stdout.readline, b''):
                texte = line.decode(errors='ignore').strip()
                yield f"data: {texte}\n\n"
            process.wait()
            yield "data: Recherche terminée\n\n"
        finally:
            killer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7100, threaded=True)

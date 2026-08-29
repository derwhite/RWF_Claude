import os

from waitress import serve

from app import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    threads = int(os.environ.get("WAITRESS_THREADS", "4"))
    print(f"Race to World First Tracker laeuft auf http://{host}:{port}")
    serve(app, host=host, port=port, threads=threads)

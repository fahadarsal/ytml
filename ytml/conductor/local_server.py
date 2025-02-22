import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread


def start_local_server(port=8000):
    """
    Start a local HTTP server to serve files from the specified directory.
    Returns the server object for later shutdown.
    """
    server = HTTPServer(('localhost', port), SimpleHTTPRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

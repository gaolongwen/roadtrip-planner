#!/usr/bin/env python3
"""简单的 HTTPS 静态文件服务器"""
import http.server
import ssl
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
DIRECTORY = sys.argv[2] if len(sys.argv) > 2 else '.'

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    
    # SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/tmp/cert.pem', '/tmp/key.pem')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    
    print(f"HTTPS Server running on https://0.0.0.0:{PORT}")
    print(f"Serving directory: {DIRECTORY}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()

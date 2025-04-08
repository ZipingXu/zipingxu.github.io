from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys

class NoCacheHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add headers to prevent caching
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        
    print(f"Starting development server on port {port}...")
    print("No caching enabled - changes should be visible immediately")
    print("Use Ctrl+C to stop the server")
    
    httpd = HTTPServer(('', port), NoCacheHTTPRequestHandler)
    httpd.serve_forever() 
#!/usr/bin/env python3
"""
Simple HTTP server with Range request support for video streaming.
Handles both .mp4 and .MP4 extensions.
Usage: python3 serve.py
"""
import http.server
import socketserver
import os
import mimetypes

PORT = 3000

# Ensure both lowercase and uppercase MP4 are registered
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/mp4', '.MP4')
mimetypes.add_type('video/mp4', '.m4v')

class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404)
            return

        file_size = os.path.getsize(path)
        range_header = self.headers.get('Range')

        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'

        if range_header:
            # Parse "bytes=start-end"
            range_val = range_header.strip().replace('bytes=', '')
            parts = range_val.split('-')
            start = int(parts[0]) if parts[0] else 0
            end   = int(parts[1]) if parts[1] else file_size - 1
            end   = min(end, file_size - 1)
            length = end - start + 1

            self.send_response(206)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.end_headers()

            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        else:
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(file_size))
            self.end_headers()

            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

    def log_message(self, fmt, *args):
        # Only log errors and first requests, not every byte range
        if args and (str(args[1]) not in ('206', '304')):
            super().log_message(fmt, *args)


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), RangeHTTPRequestHandler) as httpd:
    print(f'Serving at http://localhost:{PORT}')
    httpd.serve_forever()

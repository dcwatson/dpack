from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.packer = kwargs.pop("packer")
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = self.path
        if path.startswith(self.packer.prefix):
            chop = len(self.packer.prefix)
            path = path[chop:]
        if path in self.packer.assets:
            self.send_response(200)
            self.end_headers()
            self.packer.pack_to(path, self.wfile)
        else:
            super().do_GET()


def serve(packer_class, config_file, overrides, address="localhost", port=8000):
    def handler(*args, **kwargs):
        kwargs["packer"] = packer_class(config_file, **overrides)
        return RequestHandler(*args, **kwargs)

    httpd = ThreadingHTTPServer((address, port), handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    serve()

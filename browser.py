import socket
import ssl


class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["https", "http", "file"]

        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)

        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

        self.path = "/" + url

        if self.scheme == "https":
            self.port = 443
        elif self.scheme == "http":
            self.port = 80

    def request(self):
        if self.scheme in ["https", "http"]:
            s = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)

            s.connect((self.host, self.port))
            request = f"GET {self.path} HTTP/1.0\r\n"
            request += f"Host: {self.host}\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"
            s.send(request.encode("utf8"))

            # Receiving response
            response = s.makefile("r", encoding="utf8", newline="\r\n")
            statuslne = response.readline()
            version, status, explanation = statuslne.split(" ", 2)
            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n":
                    break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()
                assert "transfer-encoding" not in response_headers
                assert "content-encoding" not in response_headers
            content = response.read()
            s.close()
        elif self.scheme == "file":
            with open(self.path) as f:
                content = f.read()
        return content


def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


def load(url):
    body = url.request()
    show(body)


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        load(URL("file:///home/amkhrjee/Code/bowser/test.txt"))
    else:
        load(URL(sys.argv[1]))

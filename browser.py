import platform
import socket
import ssl
import tkinter

# Global config
WIDTH = 800
HEIGHT = 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18
os_name = platform.system()


class URL:
    def __init__(self, url):
        self.redirects_count = 0
        self.is_view_source = False
        self.too_many_redirects = False
        self.parse_url(url)

    def parse_url(self, url):
        if url.startswith("data:text/html"):
            self.scheme, self.content = url.split(",", 1)
        elif url.startswith("view-source:"):
            self.is_view_source = True
            _, url = url.split(":", 1)

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
            request = f"GET {self.path} HTTP/1.1\r\n"
            request += f"Host: {self.host}\r\n"
            request += "Connection: close\r\n"
            # TODO: make this keep-alive
            # request += "Connection: keep-alive\r\n"
            # connection is keep-alive by default
            request += "\r\n"
            s.send(request.encode("utf8"))

            # Receiving response
            response = s.makefile("r", encoding="utf8", newline="\r\n")
            statuslne = response.readline()
            version, self.status, explanation = statuslne.split(" ", 2)

            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n":
                    break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()
                assert "transfer-encoding" not in response_headers
                assert "content-encoding" not in response_headers

            while int(self.status) in range(300, 400):
                print("Current number of redirects:", self.redirects_count)
                # handle redirects
                if self.redirects_count < 50:
                    url = response_headers["location"]
                    if not url.startswith("http"):
                        url = self.scheme + "://" + self.host + url
                    print("Redirect Request:", url)
                    response, response_headers = self.send_redirect_request(
                        url, self.host, self.port
                    )
                else:
                    self.too_many_redirects = True

            if self.too_many_redirects:
                content = "Too many redirects!"
            else:
                content = response.read(int(response_headers.get("content-length")))
            s.close()
            if self.is_view_source:
                content = "1729" + content
        elif self.scheme == "file":
            with open(self.path) as f:
                content = f.read()
        elif self.scheme == "data:text/html":
            content = self.content.strip()
        return content

    def send_redirect_request(self, url, old_host, old_port):
        self.redirects_count += 1
        self.parse_url(url)
        if self.scheme in ["https", "http"]:
            skt = socket.socket(
                family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                skt = ctx.wrap_socket(skt, server_hostname=self.host)
            # make annother request:
            # if self.host != old_host or self.port != old_port:
            skt.connect((self.host, self.port))
            request = f"GET {self.path} HTTP/1.1\r\n"
            request += f"Host: {self.host}\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"
            skt.send(request.encode("utf8"))
            # receive the response
            response = skt.makefile("r", encoding="utf8", newline="\r\n")
            statusline = response.readline()
            version, self.status, explanation = statusline.split(" ", 2)
            print("In redirect:", self.status)
            skt.close()

            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n":
                    break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()
                assert "transfer-encoding" not in response_headers
                assert "content-encoding" not in response_headers
            return response, response_headers

        elif self.scheme == "file":
            with open(self.path) as f:
                content = f.read()
            return content

        elif self.scheme == "data:text/html":
            content = self.content.strip()
            return content


def show(body):
    if body.startswith("1729"):
        print(body[4:])
    else:
        in_tag = False
        characters = []
        for c in body:
            if c == "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                characters.append(c)
        body = "".join(characters)
        body = body.replace("&lt;", "<")
        body = body.replace("&gt;", ">")
        body += "\n"
        print(body)


def load(url):
    body = url.request()
    show(body)


def lex(body):
    if body.startswith("1729"):
        return body[4:]
    else:
        text = ""
        in_tag = False
        for c in body:
            if c == "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                text += c
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text


def layout(text, width):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        if c == "\n":
            cursor_y += VSTEP
            cursor_x = HSTEP
        else:
            cursor_x += HSTEP
        if cursor_x >= width - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.window.title("Bowser v0.0.1")
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill="both", expand=1)
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        # Works for Windows + Mac
        self.window.bind("<MouseWheel>", self.mouse_scroll)
        # Works for Linux
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)
        self.window.bind("<Configure>", self.configure)

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def load(self, url):
        self.text = lex(url.request())
        self.display_list = layout(self.text, WIDTH)
        self.y_max = max([y[1] for y in self.display_list])
        self.draw()

    def scrolldown(self, e):
        if self.scroll < self.y_max - HEIGHT:
            self.scroll += SCROLL_STEP
            self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll -= SCROLL_STEP
            self.draw()

    def mouse_scroll(self, e):
        if e.delta > 0:
            if os_name == "Windows":
                self.scrollup(e)
            elif os_name == "Darwin":
                self.scrolldown(e)
        elif e.delta < 0:
            if os_name == "Windows":
                self.scrolldown()
            elif os_name == "Darwin":
                self.scrollup()

    def configure(self, e):
        self.display_list = layout(self.text, e.width)
        self.y_max = max([y[1] for y in self.display_list])
        self.draw()


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        Browser().load(URL("file:///home/amkhrjee/Code/bowser/test.txt"))
    else:
        Browser().load(URL(sys.argv[1]))
        tkinter.mainloop()

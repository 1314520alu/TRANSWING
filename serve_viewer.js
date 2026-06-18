const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = 8788;

http.createServer((req, res) => {
  let urlPath = decodeURIComponent(req.url.split("?")[0]);
  if (urlPath === "/") {
    urlPath = "/transwing_kinematic_viewer.html";
  }
  const filePath = path.normalize(path.join(root, urlPath));
  if (!filePath.startsWith(root)) {
    res.writeHead(403);
    res.end("forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    const contentTypes = {
      ".html": "text/html; charset=utf-8",
      ".js": "application/javascript; charset=utf-8",
      ".mjs": "application/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".csv": "text/csv; charset=utf-8",
    };
    res.writeHead(200, {
      "content-type": contentTypes[ext] || "text/plain; charset=utf-8",
    });
    res.end(data);
  });
}).listen(port, "127.0.0.1", () => {
  console.log(`viewer: http://127.0.0.1:${port}/`);
});

"""docs/technical-report.md -> docs/technical-report.pdf via python-markdown + headless Chrome."""
import subprocess, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
md = (ROOT / "docs/technical-report.md").read_text()
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
css = """body{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;line-height:1.4;max-width:900px;margin:auto;color:#111}
table{border-collapse:collapse;margin:8px 0;font-size:9pt}th,td{border:1px solid #bbb;padding:3px 6px;vertical-align:top}
th{background:#eee}img{max-width:100%}td img{width:260px}blockquote{border-left:4px solid #e0a000;margin:0;padding:4px 12px;background:#fff8e6}
code{background:#f2f2f2;padding:0 3px}pre{background:#f2f2f2;padding:8px}h2{border-bottom:1px solid #ddd;page-break-after:avoid}
img[alt=Architecture]{max-height:900px;display:block;margin:auto}"""
html = ROOT / "docs/.report.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>")
chrome = sys.argv[1] if len(sys.argv) > 1 else "google-chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ROOT/'docs/technical-report.pdf'}", html.as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
html.unlink()
print("wrote docs/technical-report.pdf")

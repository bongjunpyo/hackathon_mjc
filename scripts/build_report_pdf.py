"""docs/REPORT_FINAL.md → docs/REPORT_FINAL.pdf

실행: ~/venv/bin/python scripts/build_report_pdf.py
필요: pip install markdown · macOS Chrome
"""

import pathlib
import subprocess

import markdown

ROOT = pathlib.Path(__file__).parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

md = (ROOT / "docs/REPORT_FINAL.md").read_text()
body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])

# 브랜드 토큰 그대로 — navy #002d65 · sky #6dcbf9 · gold #ffba00
html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{ font-family: "Apple SD Gothic Neo", Pretendard, "Noto Sans KR", sans-serif;
    color: #0b2038; font-size: 10.5pt; line-height: 1.62; margin: 0; }}
  h1 {{ font-size: 19pt; color: #002d65; border-bottom: 3px solid #ffba00;
       padding-bottom: 6pt; margin: 0 0 10pt; }}
  h2 {{ font-size: 14pt; color: #002d65; margin: 18pt 0 6pt;
       border-left: 4px solid #ffba00; padding-left: 8pt; page-break-after: avoid; }}
  h3 {{ font-size: 11.5pt; color: #002d65; margin: 12pt 0 4pt; page-break-after: avoid; }}
  p {{ margin: 5pt 0; }}
  blockquote {{ margin: 8pt 0; padding: 8pt 12pt; background: #e8f0fe;
    border-left: 4px solid #6dcbf9; border-radius: 4px; }}
  blockquote p {{ margin: 3pt 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 7pt 0;
    font-size: 9.5pt; page-break-inside: avoid; }}
  th, td {{ border: 1px solid #c9d8ea; padding: 4pt 7pt; text-align: left; vertical-align: top; }}
  th {{ background: #002d65; color: #fff; font-weight: 700; }}
  tr:nth-child(even) td {{ background: #f3f7fc; }}
  code {{ font-family: "SF Mono", Menlo, monospace; font-size: 9pt;
    background: #e8f0fe; padding: 1pt 3pt; border-radius: 3px; }}
  pre {{ background: #f3f7fc; border: 1px solid #c9d8ea; border-radius: 6px;
    padding: 8pt 10pt; white-space: pre-wrap; page-break-inside: avoid; }}
  pre code {{ background: none; padding: 0; }}
  a {{ color: #002d65; }}
  hr {{ border: none; border-top: 1px solid #c9d8ea; margin: 14pt 0; }}
  strong {{ color: #002d65; }}
</style></head><body>{body}</body></html>"""

tmp = ROOT / "docs" / ".report.html"
tmp.write_text(html)
subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={ROOT}/docs/REPORT_FINAL.pdf", str(tmp)], check=True)
tmp.unlink()
print("docs/REPORT_FINAL.pdf 생성 완료")

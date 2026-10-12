#!/usr/bin/env python3
"""index.html + project.json  ->  배포용 단일 파일 / Confluence 임베드 조각.

  python3 build.py --data data/project.json --out dist/sample
  python3 build.py --data data/project.json --out dist/aiss --page-id 5555638677

생성물
  <out>.html             standalone : 더블클릭/메일첨부로 바로 열리는 단일 HTML
  <out>.confluence.html  fragment   : Confluence 'HTML' 매크로에 붙여넣는 조각
                                     --page-id 를 주면 '위키에 저장' 버튼이 활성화된다
"""
import argparse, json, pathlib, sys, datetime

HERE = pathlib.Path(__file__).resolve().parent


def slice_between(src: str, start_mark: str, end_mark: str) -> str:
    i = src.index(start_mark)
    j = src.index(end_mark, i)
    return src[i:j].rstrip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=str(HERE / "index.html"))
    ap.add_argument("--data", default=str(HERE / "data" / "project.json"))
    ap.add_argument("--out", required=True, help="확장자 없는 출력 경로 (예: dist/sample)")
    ap.add_argument("--page-id", default=None, help="Confluence 페이지 ID (위키 저장 활성화)")
    a = ap.parse_args()

    tpl = pathlib.Path(a.template).read_text(encoding="utf-8")
    data = json.loads(pathlib.Path(a.data).read_text(encoding="utf-8"))
    data.setdefault("meta", {})["asOf"] = data["meta"].get("asOf") or datetime.date.today().isoformat()

    style = slice_between(tpl, '<style id="rm-style">', "</style>") + "</style>"
    root = slice_between(tpl, '<div id="rm-root">', '<script id="rm-script">')
    script = slice_between(tpl, '<script id="rm-script">', "</script>\n</body>")
    script_body = script[len('<script id="rm-script">'):]

    cfg = {"data": data, "key": "wiki:" + a.page_id if a.page_id else "file:" + pathlib.Path(a.out).name}
    if a.page_id:
        cfg["confluencePageId"] = str(a.page_id)
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    title = data["meta"].get("title", "Project Roadmap")

    config_tag = "<script>window.RM_CONFIG=%s;</script>" % cfg_json
    fragment = "\n".join([style, root, config_tag, '<script id="rm-script">' + script_body + "</script>", ""])

    standalone = (
        "<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>%s</title>\n%s\n</head>\n<body>\n%s\n%s\n<script id=\"rm-script\">%s</script>\n</body>\n</html>\n"
        % (title, style, root, config_tag, script_body)
    )

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".html").write_text(standalone, encoding="utf-8")
    pathlib.Path(str(out) + ".confluence.html").write_text(fragment, encoding="utf-8")
    print("✓ %s.html (%d KB)" % (out, len(standalone) // 1024))
    print("✓ %s.confluence.html (%d KB)%s" % (out, len(fragment) // 1024,
          "  [wiki page %s]" % a.page_id if a.page_id else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

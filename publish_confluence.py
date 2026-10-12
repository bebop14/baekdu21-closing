#!/usr/bin/env python3
"""로드맵을 Confluence 페이지로 발행한다 (HTML 매크로 + 페이지 내 저장 활성화).

  export CONFLUENCE_URL=https://wiki.navercorp.com
  export CONFLUENCE_TOKEN=...
  python3 publish_confluence.py --space '~NB11356' --title '프로젝트 로드맵' --data data/project.json

페이지가 없으면 만들고, 있으면 본문을 교체한다. 페이지 ID를 HTML 안에 심기 때문에
발행 후에는 위키 화면에서 바로 편집하고 [위키에 저장]으로 팀 전체에 공유할 수 있다.
"""
import argparse, json, os, pathlib, subprocess, sys, urllib.error, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
BASE = os.environ.get("CONFLUENCE_URL", "https://wiki.navercorp.com").rstrip("/")
TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
MACRO_END = "]]></ac:plain-text-body></ac:structured-macro>"


def api(path, method="GET", payload=None):
    req = urllib.request.Request(
        BASE + "/rest/api" + path, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/json",
                 "Content-Type": "application/json", "X-Atlassian-Token": "no-check"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s %s\n%s" % (e.code, path, e.read().decode()[:800]))


def find_page(space, title):
    q = urllib.parse.urlencode({"spaceKey": space, "title": title, "expand": "version"})
    res = api("/content?" + q)
    return res["results"][0] if res.get("results") else None


def wrap(fragment):
    inner = fragment.replace("]]>", "]]&gt;")
    return ('<ac:structured-macro ac:name="html" ac:schema-version="1"><ac:plain-text-body>'
            "<![CDATA[" + inner + "]]></ac:plain-text-body></ac:structured-macro>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--data", default=str(HERE / "data" / "project.json"))
    ap.add_argument("--parent", default=None, help="상위 페이지 ID")
    a = ap.parse_args()
    if not TOKEN:
        sys.exit("CONFLUENCE_TOKEN 이 설정되어 있지 않습니다.")

    page = find_page(a.space, a.title)
    if not page:
        body = {"type": "page", "title": a.title, "space": {"key": a.space},
                "body": {"storage": {"value": "<p>로드맵 발행 준비 중…</p>", "representation": "storage"}}}
        if a.parent:
            body["ancestors"] = [{"id": str(a.parent)}]
        page = api("/content", "POST", body)
        print("· 페이지 생성:", page["id"])
    else:
        print("· 기존 페이지 사용:", page["id"])

    out = HERE / "dist" / ("wiki-" + page["id"])
    subprocess.run([sys.executable, str(HERE / "build.py"), "--data", a.data,
                    "--out", str(out), "--page-id", page["id"]], check=True)
    fragment = pathlib.Path(str(out) + ".confluence.html").read_text(encoding="utf-8")

    cur = api("/content/%s?expand=version,body.storage" % page["id"])
    old = cur.get("body", {}).get("storage", {}).get("value", "")
    tail = old.split(MACRO_END, 1)[1] if MACRO_END in old else ""
    api("/content/%s" % page["id"], "PUT", {
        "id": page["id"], "type": "page", "title": cur["title"],
        "version": {"number": cur["version"]["number"] + 1, "message": "roadmap publish"},
        "body": {"storage": {"value": wrap(fragment) + tail, "representation": "storage"}}})
    print("✓ 발행 완료 (v%d)  %s/pages/viewpage.action?pageId=%s"
          % (cur["version"]["number"] + 1, BASE, page["id"]))


if __name__ == "__main__":
    main()

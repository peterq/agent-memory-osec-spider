#!/usr/bin/env python3
"""
Markdown → 简约 HTML 邮件 → cf-worker notify_admin 接口

给不在电脑旁的用户汇报任务进度 / 异常 / 完成情况（2026-09-15 用户要求）。
正文用 Markdown 写, 脚本渲染成内联样式的 HTML 卡片(邮件客户端兼容), 再 POST 到通知接口。

用法:
  scripts/mail/notify.py -s "主题" -f body.md                     # 从文件读正文
  echo "- 进度 30%" | scripts/mail/notify.py -s "主题" -l progress  # 从 stdin 读正文
  scripts/mail/notify.py -s "主题" -m "**一句话**正文" -l error    # 直接给正文字符串
  scripts/mail/notify.py -s "主题" -f body.md --preview out.html   # 只渲染到文件, 不发送
  scripts/mail/notify.py -s "主题" -f body.md --dry-run            # 打印 payload 摘要, 不发送

级别 -l: progress(默认, 蓝) | done(绿) | warn(黄) | error(红) | info(灰), 决定色条与主题前缀。
其它: --source 来源标识(缺省 agent-task), --url 接口地址, --no-prefix 主题不加级别前缀,
      --kv "键=值" 可重复, 渲染成顶部的元信息行(如 --kv 阶段=D --kv 进度=31%)。
退出码: 0 发送成功(接口 2xx) / 2 参数错误 / 3 发送失败。
依赖: python3-markdown(已装 3.5.2); 若缺失自动退化为 <pre> 包裹。
"""
import argparse
import datetime as dt
import html
import json
import re
import socket
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://cf-worker.peterq.cn/notify_admin"

# 级别 → (主题前缀, 色条颜色, 淡底色)
LEVELS = {
    "progress": ("进度", "#2f6fed", "#eaf1fd"),
    "done": ("完成", "#1f9d55", "#e8f7ee"),
    "warn": ("注意", "#d98a00", "#fff5e0"),
    "error": ("异常", "#d93025", "#fdeceb"),
    "info": ("通知", "#6b7280", "#f1f3f5"),
}

# 各标签的内联样式(邮件客户端普遍不认 <style>, 只能内联)
TAG_STYLE = {
    "h1": "margin:20px 0 8px;font-size:20px;font-weight:600;color:#111827;line-height:1.35;",
    "h2": "margin:18px 0 6px;font-size:17px;font-weight:600;color:#111827;line-height:1.35;",
    "h3": "margin:14px 0 4px;font-size:15px;font-weight:600;color:#111827;line-height:1.35;",
    "h4": "margin:12px 0 4px;font-size:14px;font-weight:600;color:#374151;",
    "p": "margin:8px 0;font-size:14px;line-height:1.7;color:#1f2937;",
    "ul": "margin:6px 0 6px 0;padding-left:22px;font-size:14px;line-height:1.7;color:#1f2937;",
    "ol": "margin:6px 0 6px 0;padding-left:22px;font-size:14px;line-height:1.7;color:#1f2937;",
    "li": "margin:2px 0;",
    "a": "color:#2f6fed;text-decoration:none;",
    "blockquote": "margin:10px 0;padding:6px 12px;border-left:3px solid #d1d5db;color:#4b5563;background:#f9fafb;",
    "hr": "border:0;border-top:1px solid #e5e7eb;margin:16px 0;",
    "table": "border-collapse:collapse;margin:10px 0;font-size:13px;width:100%;",
    "th": "border:1px solid #e5e7eb;padding:6px 10px;background:#f3f4f6;text-align:left;font-weight:600;color:#111827;",
    "td": "border:1px solid #e5e7eb;padding:6px 10px;color:#1f2937;vertical-align:top;",
    "pre": "margin:10px 0;padding:10px 12px;background:#0f172a;color:#e2e8f0;border-radius:6px;font-size:12.5px;line-height:1.55;overflow-x:auto;white-space:pre-wrap;word-break:break-all;",
    "strong": "font-weight:600;color:#111827;",
    "img": "max-width:100%;height:auto;",
}
CODE_INLINE = "font-family:SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;background:#f3f4f6;color:#b42318;padding:1px 5px;border-radius:4px;"
CODE_IN_PRE = "font-family:SFMono-Regular,Menlo,Consolas,monospace;background:transparent;color:inherit;padding:0;"


def md_to_html(md: str) -> str:
    """Markdown 渲染为 HTML 片段; markdown 库缺失时退化为 <pre>。"""
    try:
        import markdown  # type: ignore
    except ImportError:
        return "<pre>%s</pre>" % html.escape(md)
    return markdown.markdown(
        md,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        output_format="html",
    )


def inline_styles(fragment: str) -> str:
    """给渲染结果的常见标签补内联 style(仅处理没有 style 属性的开标签)。"""
    def repl(m):
        tag = m.group(1).lower()
        attrs = m.group(2) or ""
        if "style=" in attrs:
            return m.group(0)
        style = TAG_STYLE.get(tag)
        if style is None:
            return m.group(0)
        return "<%s%s style=\"%s\">" % (tag, attrs, style)

    tags = "|".join(TAG_STYLE.keys())
    out = re.sub(r"<(%s)(\s[^>]*)?>" % tags, repl, fragment, flags=re.I)
    # <pre><code> 内的 code 与行内 code 样式不同
    out = re.sub(r"<pre([^>]*)><code([^>]*)>", lambda m: "<pre%s><code%s style=\"%s\">" % (m.group(1), m.group(2), CODE_IN_PRE), out)
    out = re.sub(r"<code(?![^>]*style=)([^>]*)>", lambda m: "<code%s style=\"%s\">" % (m.group(1), CODE_INLINE), out)
    return out


def build_page(subject: str, body_html: str, level: str, source: str, kv: list, now: dt.datetime) -> str:
    """套外层卡片: 顶部色条 + 标题 + 元信息 + 正文 + 页脚。"""
    label, color, tint = LEVELS[level]
    host = socket.gethostname()
    meta_items = [("时间", now.strftime("%Y-%m-%d %H:%M")), ("来源", source), ("主机", host)] + kv
    meta_html = "".join(
        "<span style=\"display:inline-block;margin:0 14px 4px 0;\">"
        "<span style=\"color:#9ca3af;\">%s</span> <span style=\"color:#374151;\">%s</span></span>"
        % (html.escape(k), html.escape(v))
        for k, v in meta_items
    )
    return (
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>%(title)s</title></head>"
        "<body style=\"margin:0;padding:24px 12px;background:#f3f4f6;"
        "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',Arial,'Microsoft YaHei',sans-serif;\">"
        "<table role=\"presentation\" width=\"100%%\" cellpadding=\"0\" cellspacing=\"0\"><tr><td align=\"center\">"
        "<table role=\"presentation\" width=\"100%%\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"max-width:640px;background:#ffffff;border-radius:10px;overflow:hidden;"
        "box-shadow:0 1px 3px rgba(0,0,0,.08);\">"
        "<tr><td style=\"height:5px;background:%(color)s;font-size:0;line-height:0;\">&nbsp;</td></tr>"
        "<tr><td style=\"padding:20px 24px 12px;\">"
        "<span style=\"display:inline-block;padding:2px 9px;border-radius:999px;background:%(tint)s;color:%(color)s;"
        "font-size:12px;font-weight:600;letter-spacing:.5px;\">%(label)s</span>"
        "<div style=\"margin-top:10px;font-size:19px;font-weight:600;color:#111827;line-height:1.4;\">%(title)s</div>"
        "<div style=\"margin-top:8px;font-size:12px;line-height:1.6;\">%(meta)s</div>"
        "</td></tr>"
        "<tr><td style=\"padding:0 24px;\"><div style=\"border-top:1px solid #e5e7eb;\"></div></td></tr>"
        "<tr><td style=\"padding:8px 24px 22px;\">%(body)s</td></tr>"
        "<tr><td style=\"padding:12px 24px;background:#f9fafb;font-size:11.5px;color:#9ca3af;line-height:1.6;\">"
        "由 Agent 自动发送 · agent-memory-osec-spider/scripts/mail/notify.py</td></tr>"
        "</table></td></tr></table></body></html>"
    ) % {"title": html.escape(subject), "color": color, "tint": tint, "label": label, "meta": meta_html, "body": body_html}


def send(url: str, subject: str, html_content: str, source: str) -> tuple:
    data = json.dumps({"subject": subject, "htmlContent": html_content, "source": source}, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                          # Cloudflare 对 python-urllib 默认 UA 返回 403 code 1010, 必须自定义 UA
                                          "User-Agent": "agent-notify/1.0 (curl-compatible)"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode("utf-8", "replace")
    except Exception as e:  # 网络错误
        return 0, str(e)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-s", "--subject", required=True, help="邮件主题(不含级别前缀)")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("-f", "--file", help="Markdown 正文文件, '-' 表示 stdin")
    src.add_argument("-m", "--markdown", help="Markdown 正文字符串")
    ap.add_argument("-l", "--level", choices=LEVELS.keys(), default="progress")
    ap.add_argument("--source", default="agent-task")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--kv", action="append", default=[], help="元信息 键=值, 可重复")
    ap.add_argument("--no-prefix", action="store_true", help="主题不加【级别】前缀")
    ap.add_argument("--preview", metavar="OUT.html", help="只渲染写到文件, 不发送")
    ap.add_argument("--dry-run", action="store_true", help="不发送, 打印主题与正文长度")
    a = ap.parse_args()

    if a.markdown is not None:
        md = a.markdown
    elif a.file and a.file != "-":
        with open(a.file, encoding="utf-8") as fp:
            md = fp.read()
    else:
        md = sys.stdin.read()
    if not md.strip():
        print("正文为空", file=sys.stderr)
        return 2

    kv = []
    for item in a.kv:
        if "=" not in item:
            print("--kv 格式应为 键=值: %s" % item, file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        kv.append((k.strip(), v.strip()))

    now = dt.datetime.now().astimezone()
    label = LEVELS[a.level][0]
    subject = a.subject if a.no_prefix else "【%s】%s" % (label, a.subject)
    page = build_page(subject, inline_styles(md_to_html(md)), a.level, a.source, kv, now)

    if a.preview:
        with open(a.preview, "w", encoding="utf-8") as fp:
            fp.write(page)
        print("已写入 %s (%d 字节)" % (a.preview, len(page.encode())))
        return 0
    if a.dry_run:
        print("dry-run subject=%s level=%s html=%d 字节 url=%s" % (subject, a.level, len(page.encode()), a.url))
        return 0

    code, text = send(a.url, subject, page, a.source)
    ok = 200 <= code < 300
    print("%s http=%s %s" % ("已发送" if ok else "发送失败", code, text.strip()[:120]))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())

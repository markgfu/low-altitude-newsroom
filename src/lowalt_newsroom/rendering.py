import base64
import html
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit


def safe_link(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("原文链接必须为不含账号密码的HTTP(S)链接")
    return html.escape(url, quote=True)


def inline(text: str) -> str:
    def replace(match):
        if match.group(1) is not None:
            return f'<a href="{safe_link(match.group(2))}" rel="noopener noreferrer">{html.escape(match.group(1))}</a>'
        if match.group(3) is not None:
            return '<strong>' + html.escape(match.group(3)) + '</strong>'
        return html.escape(match.group(0))
    # 仅支持正文实际使用的链接/加粗子集；原始HTML一律转义。
    pattern = r"\[([^\]]+)\]\(([^\s]+)\)|\*\*(.+?)\*\*"
    parts, offset = [], 0
    for match in re.finditer(pattern, text):
        parts.extend([html.escape(text[offset:match.start()]), replace(match)])
        offset = match.end()
    parts.append(html.escape(text[offset:]))
    result = "".join(parts)
    if result.startswith("*") and result.endswith("*") and not result.startswith("**"):
        result = '<em>' + result[1:-1] + '</em>'
    return result


def embedded_image(name: str, base: Path) -> str:
    if urlsplit(name).scheme:
        raise ValueError("请先核对并下载原图到稿件目录；不自动下载远程图片")
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError("图片缺失或超出稿件目录")
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0]
    signatures = {"image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
                  "image/jpeg": data.startswith(b"\xff\xd8\xff"),
                  "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP"}
    if len(data) > 20 * 1024 * 1024 or not signatures.get(mime):
        raise ValueError("仅支持20MB以内的PNG/JPEG/WebP原图")
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode("ascii")


def render_markdown(source: Path) -> str:
    text = source.read_text(encoding="utf-8-sig")
    body = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if len(lines) == 1 and (heading := re.fullmatch(r"(#{1,3}) (.+)", block)):
            size = len(heading[1])
            body.append(f"<h{size}>{inline(heading[2])}</h{size}>")
        elif len(lines) == 1 and (image := re.fullmatch(r"!\[([^\]]*)\]\(([^\s]+)\)", block)):
            uri = embedded_image(image[2], source.parent)
            body.append(f'<figure><img src="{uri}" alt="{html.escape(image[1], quote=True)}"></figure>')
        elif block == "---":
            body.append("<hr>")
        else:
            body.append("<p>" + "<br>".join(inline(line.removesuffix("  ")) for line in lines) + "</p>")
    title = text.splitlines()[0].removeprefix("# ")
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + html.escape(title) + '</title><style>'
            'body{max-width:760px;margin:32px auto;padding:0 20px;font:16px/1.85 system-ui,"Microsoft YaHei",sans-serif;color:#202830}'
            'h1{font-size:26px;line-height:1.5}h2{margin-top:32px;color:#185a6b;font-size:22px}'
            'h3{font-size:18px;margin-top:24px}a{color:#12657a;overflow-wrap:anywhere}'
            'p{margin:16px 0;text-align:justify}figure{margin:20px 0}img{max-width:100%;height:auto}'
            'em{font-size:13px;color:#52616b}hr{border:0;border-top:1px solid #ddd}'
            '</style></head><body>' + "\n".join(body) + '</body></html>')


def check_draft(text: str) -> dict:
    errors, warnings = [], []
    if not text.startswith("# "):
        errors.append("缺少标题")
    if not re.search(r"\*\*今日总结\*\*：|\*\*今日总结：\*\*", text):
        errors.append("缺少今日总结")
    for token in ["补收", "研究补充", "source_level:", "waiting-review", "needs-verification", "采集截止："]:
        if token in text:
            errors.append(f"公开正文含内部标签：{token}")
    articles = re.split(r"(?m)^### \d+\. ", text)[1:]
    for index, article in enumerate(articles, 1):
        blocks = article.split("\n\n")
        paragraphs = []
        for block in blocks[1:]:
            stripped = block.strip()
            if not stripped or stripped.startswith(("![", "*图", "来源：", "题名：", "DOI：", "## ")):
                break
            paragraphs.append(stripped)
        if len(paragraphs) != 1:
            errors.append(f"第{index}条摘要不是一个自然段")
        if "来源：" not in article or not re.search(r"\]\(https?://", article):
            errors.append(f"第{index}条缺少来源或链接")
        if paragraphs and len(paragraphs[0]) > 200:
            warnings.append(f"第{index}条摘要超过200字，请人工核查必要性")
    if not articles:
        errors.append("没有新闻条目")
    return {"articles": len(articles), "errors": errors, "warnings": warnings,
            "boundary": "仅格式检查，不代替原文、版权、日期、数字或项目阶段核验。"}

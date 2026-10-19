"""社交信源取证：参考叙事雷达的公开详情试采，正文取得与事实核验分开。"""

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .feeds import MAX_BYTES, parse_feed, public_url, publication_time
from .intake_schema import records_from_pack, heat

PLATFORMS = {"x", "xiaohongshu", "wechat", "weibo", "xueqiu"}


class VisibleText(HTMLParser):
    def __init__(self, element_id=None):
        super().__init__()
        self.element_id = element_id
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        selected = self.element_id is None or attrs.get("id") == self.element_id or any(x[1] for x in self.stack)
        hidden = tag in {"script", "style"} or any(x[2] for x in self.stack)
        if tag not in {"br", "img", "meta", "link", "input", "hr", "source", "wbr"}:
            self.stack.append((tag, selected, hidden))
        if selected and not hidden and tag in {"p", "div", "section", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        selected = self.element_id is None or any(x[1] for x in self.stack)
        if selected and not any(x[2] for x in self.stack):
            self.parts.append(text)


def text_content(markup, element_id=None):
    parser = VisibleText(element_id)
    parser.feed(markup)
    return re.sub(r"\n[ \t\n]+", "\n", "".join(parser.parts)).strip()


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def capture(record):
    """接收API、浏览器或本人导出正文；不接受调用者传入已核实状态。"""
    if record.get("platform") not in PLATFORMS:
        raise ValueError("未知社交平台")
    for key in ("source_id", "route", "sampling_method", "captured_at"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"缺少{key}")
    captured = publication_time(record["captured_at"])
    if captured is None:
        raise ValueError("captured_at必须为带时区的实际采集时间")
    url = public_url(record.get("url", ""))
    body = record.get("body", "")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("缺少实际正文；登录页或搜索摘要不能导入为正文")
    extent = record.get("body_extent", "unknown")
    if extent not in {"full", "partial", "unknown"}:
        raise ValueError("body_extent须为full/partial/unknown")
    raw_time = record.get("published_at_raw") or ""
    if not isinstance(raw_time, str):
        raise ValueError("published_at_raw须为字符串")
    return {"source_id": record["source_id"], "platform": record["platform"], "url": url,
            "document_id": record.get("document_id") or digest(url),
            "author": record.get("author"), "author_identity_verified": False,
            "title": record.get("title"), "body": body, "body_sha256": digest(body),
            "body_extent": extent, "published_at_raw": raw_time,
            "published_at_utc": publication_time(raw_time), "captured_at": captured,
            "available_at": captured, "route": record["route"],
            "sampling_method": record["sampling_method"], "query": record.get("query"),
            "status": "已取得正文待核", "fact_verified": False, "review_status": "waiting_review"}


def import_intake(data, source_id, policy=None):
    """接入技能的真实观察包；结构有效、热度和日报事实验收分开。"""
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("intake需要来源ID")
    if len(data) > MAX_BYTES:
        raise ValueError("采集包超过大小限制")
    try:
        pack = json.loads(data.decode("utf-8-sig"))
        records = records_from_pack(pack)
    except (UnicodeError, TypeError, ValueError):
        raise ValueError("采集包无效；检查结构、正文哈希、计数一致性及敏感字段") from None
    documents = []
    for record in records:
        published = record.get("published") or {}
        doc = capture({"platform": record["platform"], "source_id": source_id,
                       "url": record["source_url"], "body": record["text"],
                       "captured_at": record["observed_at"], "route": record["capture_method"],
                       "sampling_method": "provided_capture_pack", "title": record.get("title"),
                       "author": record.get("author"), "query": record.get("query"),
                       "published_at_raw": published.get("display") or "",
                       "body_extent": {True: "full", False: "partial", None: "unknown"}[record.get("body_complete")]})
        # 显示字符串不证明首发时间；只用明确核定为 published 的带时区时刻。
        doc["published_at_utc"] = (publication_time(published.get("at") or "")
                                    if published.get("kind") == "published" else None)
        text_without_tags = re.sub(r"#[^\s#]+", "", record["text"]).strip()
        no_discussion = (not any(char.isalnum() for char in text_without_tags)
                         or record["text"].strip() == (record.get("title") or "").strip())
        doc.update(published=record.get("published"), edited=record.get("edited"),
                   interactions=record.get("interactions", {}), body_scope=record.get("body_scope"),
                   evidence=record.get("evidence"), gaps=record.get("gaps", []),
                   simulation=record.get("simulation", False),
                   content_review="missing_independent_discussion" if no_discussion else "waiting_review",
                   theme_status="waiting_review", time_window_status="waiting_review",
                   heat=heat(record, policy if policy is not None else {"platforms": {}}),
                   metric_eligible=False, quote_eligible=False, daily_eligible=False,
                   source_observation=record)
        # AX转录的读取区间保留原记录；不把导入时钟改作DOM观察时刻。
        for key in ("observed_interval", "actual_dom_observed_at", "recorded_at"):
            if key in record:
                doc[key] = record[key]
        documents.append(doc)
    return {"schema_version": "newsroom-social-intake-v1", "documents": documents,
            "source_pack_sha256": hashlib.sha256(data).hexdigest(),
            "source_schema": pack.get("schema_version"), "source_status": pack.get("status"),
            "source_coverage_complete": pack.get("coverage_complete"),
            "candidates": pack.get("candidates", []), "failures": pack.get("failures", []),
            "simulation": pack.get("simulation", False) or any(x["simulation"] for x in documents),
            "accepted": False, "status": "已导入待核" if documents else "无正文；保留原失败记录"}


def inspect_html(markup, platform):
    """只读公开HTML中的明确内容结构；不执行网页脚本或解验证码。"""
    visible = text_content(markup)
    result = {"body": None, "body_extent": "unknown", "published_at_raw": "", "author": None}
    if platform == "wechat":
        body = text_content(markup, "js_content")
        if body:
            result.update(body=body, author=text_content(markup, "js_name") or None,
                          published_at_raw=text_content(markup, "publish_time"))
    elif platform == "xueqiu":
        match = re.search(r"window\.SNOWMAN_STATUS\s*=\s*", markup)
        if match:
            try:
                obj, _ = json.JSONDecoder().raw_decode(markup[match.end():])
                result.update(body=text_content(obj.get("text", "")) or None,
                              body_extent="full" if obj.get("truncated") is False else "unknown",
                              author=str(obj.get("user_id", "")) or None)
                if isinstance(obj.get("created_at"), (int, float)):
                    result["published_at_raw"] = datetime.fromtimestamp(obj["created_at"] / 1000, timezone.utc).isoformat()
            except (ValueError, TypeError, AttributeError, OverflowError, OSError):
                pass
    if result["body"]:
        result["status"] = "已取得正文待核"
    elif re.search(r"验证码|安全验证|访问频次|访问过于频繁|captcha|challenge", visible, re.I):
        result["status"] = "验证或限流"
    elif re.search(r"登录|登錄|log in|sign in", visible, re.I):
        result["status"] = "需要登录或仅有登录页"
    else:
        result["status"] = "未取得可确认正文"
    return result


def probe(url, platform, source_id, timeout=12):
    public_url(url)
    if platform not in PLATFORMS or not 0 < timeout <= 60 or not source_id.strip():
        raise ValueError("检查平台、信源ID和超时参数")
    result = {"url": url, "source_id": source_id, "platform": platform,
              "captured_at": datetime.now(timezone.utc).isoformat(), "route": "public_html",
              "session": "anonymous_no_cookie", "http_status": None, "status": "读取失败",
              "error": None, "document": None, "raw_sha256": None}
    try:
        with urlopen(Request(url, headers={"User-Agent": "Newsroom/0.2 (source verification)"}), timeout=timeout) as response:
            result["http_status"] = response.status
            result["final_url"] = response.url
            raw = response.read(MAX_BYTES + 1)
            charset = response.headers.get_content_charset() or "utf-8"
        if len(raw) > MAX_BYTES:
            raise ValueError("页面超过大小限制")
        result["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        parsed = inspect_html(raw.decode(charset, errors="replace"), platform)
        result["status"] = parsed["status"]
        if parsed["body"]:
            result["document"] = capture({**result, **parsed, "sampling_method": "selected_public_permalink"})
    except HTTPError as error:
        result["http_status"] = error.code
        result["error"] = f"HTTP {error.code}"
        if error.code in {401, 403, 429}:
            result["status"] = "访问受限"
    except (OSError, ValueError, LookupError) as error:
        result["error"] = type(error).__name__
    return result


def import_feed(data, platform, source_id, captured_at):
    """兼容WeRSS等RSS/Atom导出；不把description当作全文。"""
    leads = parse_feed(data)  # 复用大小、实体与格式检查
    root = ET.fromstring(data)
    atom = "{http://www.w3.org/2005/Atom}"
    nodes = root.findall("channel/item") if root.tag == "rss" else root.findall(atom + "entry")
    results = []
    for lead, node in zip(leads, nodes):
        content = node.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        if content is None:
            content = node.find(atom + "content")
        if content is None:
            results.append({**lead, "status": "仅有订阅线索", "document": None})
            continue
        markup = content.text or ""
        if len(content):
            markup += "".join(ET.tostring(child, encoding="unicode") for child in content)
        body = text_content(markup)
        if not body:
            results.append({**lead, "status": "订阅正文为空", "document": None})
            continue
        document = capture({"platform": platform, "source_id": source_id, "url": lead["url"],
                            "title": lead["title"], "body": body, "published_at_raw": lead["publication_raw"],
                            "captured_at": captured_at, "route": "rss_export", "body_extent": "unknown",
                            "sampling_method": "provided_feed_export"})
        results.append({**lead, "status": "已取得订阅正文待核", "document": document})
    return results

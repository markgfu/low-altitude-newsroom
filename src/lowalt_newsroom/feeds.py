from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

MAX_BYTES = 8 * 1024 * 1024


def public_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("仅支持不含账号密码的HTTP(S)链接")
    return value


def publication_time(value: str) -> str | None:
    if not value.strip():
        return None
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            stamp = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    # 不为无时区的时间补造时区；保留原字段供核查。
    return stamp.astimezone(timezone.utc).isoformat() if stamp.tzinfo is not None else None


def parse_feed(data: bytes) -> list[dict]:
    if len(data) > MAX_BYTES or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XML过大或含不支持的实体定义")
    root = ET.fromstring(data)
    atom = {"a": "http://www.w3.org/2005/Atom"}
    if root.tag == "rss":
        nodes = root.findall("channel/item")
        return [{"title": x.findtext("title", "").strip(), "url": x.findtext("link", "").strip(),
                 "publication_raw": x.findtext("pubDate", "").strip(),
                 "publication_utc": publication_time(x.findtext("pubDate", "")),
                 "full_text_read": False} for x in nodes]
    if root.tag == "{http://www.w3.org/2005/Atom}feed":
        results = []
        for x in root.findall("a:entry", atom):
            links = x.findall("a:link", atom)
            link = next((v.get("href", "") for v in links if v.get("rel", "alternate") == "alternate"), "")
            published = x.findtext("a:published", "", atom)
            results.append({"title": x.findtext("a:title", "", atom).strip(), "url": link,
                            "publication_raw": published, "publication_utc": publication_time(published),
                            "updated_raw": x.findtext("a:updated", "", atom), "full_text_read": False})
        return results
    raise ValueError("不是支持的RSS2/Atom订阅；HTTP200不代表解析成功")


def fetch_feed(url: str, timeout: float = 12) -> dict:
    public_url(url)
    result = {"feed_url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
              "http_status": None, "status": "读取失败", "items": [], "error": None}
    try:
        request = Request(url, headers={"User-Agent": "LowAltitudeNewsroom/0.1 (+manual editorial review)"})
        with urlopen(request, timeout=timeout) as response:
            result["http_status"] = response.status
            body = response.read(MAX_BYTES + 1)
        result["items"] = parse_feed(body)
        result["status"] = "已解析订阅样本"
    except HTTPError as error:
        result["http_status"] = error.code
        result["error"] = f"HTTPError: {error.code} {error.reason}"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result

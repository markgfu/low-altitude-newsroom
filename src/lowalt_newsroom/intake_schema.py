# Adapted from user-provided social-source-intake/scripts/intake.py.
# Source SHA-256: 7bd6a927bc1d1a0a54ad71e053a3ab39832141dbe4f2d6a4ce77d6578e6acf16
#!/usr/bin/env python3
"""Offline social-capture validation, text hashing and per-platform heat checks.

No network, browser-storage or credential access. Python standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import parse_qsl, urlsplit

PLATFORMS = {"xueqiu", "weibo", "xiaohongshu", "x"}
COUNTERS = {"like_count", "comment_count", "repost_count", "collect_count"}
SECRET_KEYS = {"cookie", "cookies", "password", "authorization", "access_token",
               "auth_token", "ct0", "storage_state", "headers", "request_headers"}
URL_SECRET_KEYS = SECRET_KEYS | {"xsec_token", "token", "session", "sessionid"}
PERMALINKS = {
    "xueqiu": ({"xueqiu.com", "www.xueqiu.com"}, r"/\d+/\d+/?"),
    "weibo": ({"weibo.com", "www.weibo.com", "m.weibo.cn", "weibo.cn"},
              r"/(?:\d+/[A-Za-z0-9]+|(?:detail|status|comment)/[A-Za-z0-9]+)/?"),
    "xiaohongshu": ({"xiaohongshu.com", "www.xiaohongshu.com"},
                    r"/(?:explore|search_result|discovery/item)/[0-9a-fA-F]{24}/?"),
    "x": ({"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
          r"/[A-Za-z0-9_]+/status/\d+/?"),
}


class IntakeError(ValueError):
    """A deliberately authored error that contains no input values."""


def fail(message):
    raise IntakeError(message)


def no_secrets(value):
    if isinstance(value, dict):
        if any(str(key).lower() in SECRET_KEYS for key in value):
            fail("采集包含凭证/请求头字段；先在本机移除，不输出字段内容")
        for item in value.values():
            no_secrets(item)
    elif isinstance(value, list):
        for item in value:
            no_secrets(item)
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        url = urlsplit(value)
        if url.username or url.password or any(key.lower() in URL_SECRET_KEYS for key, _ in parse_qsl(url.query)):
            fail("采集包链接含登录/访问参数；原链接仅留私有证据")


def aware_time(value, label):
    if not isinstance(value, str):
        fail(label + " 必须是带偏移的 ISO 日期时间")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        fail(label + " 缺少时区偏移")
    return parsed


def date_record(value, label):
    if value is None:
        return
    if not isinstance(value, dict):
        fail(label + " 必须是对象或 null")
    if not isinstance(value.get("display"), str) or not value["display"].strip():
        fail(label + " 必须保留日期原始显示")
    if value.get("kind") not in {"published", "edited", "current_version", "unknown"}:
        fail(label + " kind 未定义")
    if label == "published" and value.get("kind") == "edited":
        fail("编辑日期不能写入 published")
    if label == "edited" and value.get("kind") != "edited":
        fail("edited 必须标记为 edited")
    at, day, precision = value.get("at"), value.get("date"), value.get("precision")
    if precision not in {"day", "minute", "second", "unknown"}:
        fail(label + " precision 未定义")
    if day is not None:
        date.fromisoformat(day)
    if at is not None:
        parsed = aware_time(at, label + ".at")
        if precision not in {"minute", "second"}:
            fail(label + " 有时刻时需声明 minute/second 精度")
        if day is not None and parsed.date().isoformat() != day:
            fail(label + " at/date 不一致")
    elif precision in {"minute", "second"}:
        fail(label + " 声明时刻精度但缺少 at")
    if precision == "day" and day is None:
        fail(label + " 日精度缺少 date")
    if (at is not None or day is not None) and not value.get("basis"):
        fail(label + " 已解释日期但缺少证据 basis")


def validate(record):
    if not isinstance(record, dict):
        fail("采集包必须为 JSON 对象")
    no_secrets(record)
    if "simulation" in record and type(record["simulation"]) is not bool:
        fail("simulation 标记只能是 boolean")
    if record.get("schema_version") != "social-capture-v1":
        fail("schema_version 应为 social-capture-v1")
    if record.get("platform") not in PLATFORMS:
        fail("不支持的平台")
    if record.get("capture_method") not in {"browser_visible", "adapter_api", "official_api"}:
        fail("必须声明采集方法")
    url = urlsplit(record.get("source_url", ""))
    if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
        fail("来源必须是没有登录凭证的 HTTP(S) 原文链接")
    if any(key.lower() in URL_SECRET_KEYS for key, _ in parse_qsl(url.query)):
        fail("原文链接含会话/访问参数；原链接仅留私有证据，发布采集包使用公开 permalink")
    hosts, pattern = PERMALINKS[record["platform"]]
    if url.hostname.lower() not in hosts or not re.fullmatch(pattern, url.path):
        fail("来源链接不符合声明平台的公开帖子 permalink 结构")
    aware_time(record.get("observed_at"), "observed_at")
    if not isinstance(record.get("text"), str) or not record["text"].strip():
        fail("缺少实际正文")
    complete = record.get("body_complete")
    if complete is not None and not isinstance(complete, bool):
        fail("body_complete 只能是 boolean/null")
    if complete is True and not record.get("body_scope"):
        fail("完整性声明缺少 body_scope")
    date_record(record.get("published"), "published")
    date_record(record.get("edited"), "edited")
    counters = record.get("interactions", {})
    if not isinstance(counters, dict):
        fail("interactions 必须是对象")
    for name, counter in counters.items():
        if name not in COUNTERS or not isinstance(counter, dict):
            fail("互动字段需为已知计数字段对象")
        amount = counter.get("value")
        if amount is not None and (type(amount) is not int or amount < 0):
            fail("互动 value 只能是非负整数/null")
        if amount is not None and not isinstance(counter.get("display"), str):
            fail("精确互动数必须保留显示/接口字段证据")
        if amount is not None:
            display = unicodedata.normalize("NFKC", counter["display"]).strip()
            exact_display = re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)", display)
            displayed = int(display.replace(",", "")) if exact_display else None
            raw_value = counter.get("raw_value")
            api_exact = (record["capture_method"] in {"adapter_api", "official_api"}
                         and type(raw_value) is int and raw_value == amount)
            if displayed != amount and not api_exact:
                fail("互动显示不是与 value 一致的精确整数；近似值保持未知")
    if not isinstance(record.get("evidence"), dict) or not record["evidence"].get("body"):
        fail("缺少正文 evidence")
    gaps = record.get("gaps", [])
    if not isinstance(gaps, list) or not all(isinstance(gap, str) for gap in gaps):
        fail("gaps 必须是字符串数组")
    expected = record.get("text_sha256")
    if expected is not None and expected != hashlib.sha256(record["text"].encode("utf-8")).hexdigest():
        fail("正文哈希不一致")
    return record


def heat(record, policy):
    validate(record)
    platform = record["platform"]
    if not isinstance(policy, dict) or not isinstance(policy.get("platforms"), dict):
        fail("热度策略需包含 platforms 对象")
    limits = policy["platforms"].get(platform)
    if not isinstance(limits, dict) or not limits:
        return {"status": "unconfigured", "platform": platform, "checks": []}
    checks = []
    for name, threshold in limits.items():
        if name not in COUNTERS or type(threshold) is not int or threshold <= 0:
            fail("热度门槛必须是已知字段的正整数")
        amount = record.get("interactions", {}).get(name, {}).get("value")
        checks.append({"metric": name, "value": amount, "minimum": threshold,
                       "passed": None if amount is None else amount >= threshold})
    passed = [check["passed"] for check in checks]
    status = "pass" if True in passed else "unknown" if None in passed else "below_threshold"
    return {"status": status, "platform": platform, "observed_at": record["observed_at"],
            "rule": "any_exact_counter", "checks": checks}


def browser_record(record, platform):
    if not isinstance(record, dict) or record.get("page_status") != "captured":
        fail("浏览器包只将实际 captured 详情转为正文记录，失败应在 failures")
    if record.get("platform", platform) != platform:
        fail("浏览器包平台不一致")
    if "simulation" in record and type(record["simulation"]) is not bool:
        fail("simulation 标记只能是 boolean")
    body = record.get("body")
    if not isinstance(body, str):
        fail("浏览器记录缺少 body")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if record.get("body_hash") is not None and record["body_hash"] != digest:
        fail("浏览器原文哈希不一致")
    raw_counters, parsed = record.get("engagement_raw", {}), record.get("engagement", {})
    if not isinstance(raw_counters, dict) or not isinstance(parsed, dict):
        fail("浏览器互动字段需是对象")
    counters = {}
    for short, canonical in (("likes", "like_count"), ("comments", "comment_count"),
                             ("reposts", "repost_count"), ("bookmarks", "collect_count")):
        if short in parsed and canonical in parsed and parsed[short] != parsed[canonical]:
            fail("浏览器互动别名字段冲突")
        if short in raw_counters and canonical in raw_counters and raw_counters[short] != raw_counters[canonical]:
            fail("浏览器互动原始显示别名字段冲突")
        counters[canonical] = {"value": parsed.get(short, parsed.get(canonical)),
                               "display": raw_counters.get(short, raw_counters.get(canonical))}
    result = {
        "schema_version": "social-capture-v1", "platform": platform,
        "post_id": record.get("post_id"), "source_url": record.get("source_url"),
        "capture_method": "browser_visible", "observed_at": record.get("observed_at"),
        "text": body, "text_sha256": digest, "title": record.get("title"),
        "author": record.get("author"), "body_complete": record.get("body_complete"),
        "body_scope": record.get("body_scope"), "query": record.get("query"),
        "body_completeness_basis": record.get("body_completeness_basis"),
        "interactions": counters,
        "evidence": {"body": "visible own-post DOM; see browser_dom_proof",
                     "browser_dom_proof": record.get("dom_proof", {})},
        "gaps": ["日期仅保留原始显示，未核定年月日/时区", "完整性与主题匹配待复核"],
        "metric_eligible": False, "quote_eligible": False, "daily_eligible": False,
    }
    if record.get("simulation") is True:
        result["simulation"] = True
    for key in ("observed_interval", "actual_dom_observed_at", "recorded_at"):
        if key in record:
            result[key] = record[key]
    if isinstance(record.get("gaps"), list):
        result["gaps"].extend(record["gaps"])
    for raw_key, target in (("publication_raw", "published"), ("edited_raw", "edited")):
        display = record.get(raw_key)
        if display is not None and not isinstance(display, str):
            fail("浏览器日期显示需是字符串或 null")
        result[target] = ({"display": display, "at": None, "date": None,
                           "precision": "unknown", "kind": "edited" if target == "edited" else "unknown",
                           "basis": "实际可见日期元素；尚未解释日期"} if display else None)
    return validate(result)


def records_from_pack(pack):
    if not isinstance(pack, dict):
        fail("采集包必须为 JSON 对象")
    no_secrets(pack)
    if "simulation" in pack and type(pack["simulation"]) is not bool:
        fail("simulation 标记只能是 boolean")
    schema = pack.get("schema_version")
    if schema == "social-capture-v1":
        return [validate(pack)]
    if schema not in {"social-browser-observation-v1", "social-intake-batch-v1"}:
        fail("不支持的采集包 schema")
    if schema == "social-browser-observation-v1" and "body" in pack:
        return [browser_record(pack, pack.get("platform"))]
    records = pack.get("records")
    if not isinstance(records, list) or len(records) > 1000:
        fail("批量包 records 应为至多 1000 条的数组")
    if schema == "social-intake-batch-v1":
        normalized = [dict(validate(item)) for item in records]
        if pack.get("simulation") is True:
            for item in normalized:
                item["simulation"] = True
        return normalized
    platform = pack.get("platform")
    if platform not in PLATFORMS:
        fail("浏览器包缺少支持的平台")
    normalized = [browser_record(item, platform) for item in records]
    if pack.get("simulation") is True:
        for item in normalized:
            item["simulation"] = True
    return normalized


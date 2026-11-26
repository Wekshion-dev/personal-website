import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

from VARS import (
    NETFETCH_LAPTOP_URL,
    NETFETCH_OUTPUT_PATH,
    NETFETCH_PC_URL,
    NETFETCH_SERVER_URL,
    NETFETCH_TIMEOUT,
)

MACHINES = [
    ("pc", "Desktop PC", NETFETCH_PC_URL),
    ("laptop", "Laptop", NETFETCH_LAPTOP_URL),
    ("server", "Server", NETFETCH_SERVER_URL),
]


class NetfetchHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, set[str]]] = []
        self._in_logo = False
        self._in_header = False
        self._in_key = False
        self._in_value = False
        self._in_info_line = False

        self._logo_chunks: list[str] = []
        self._header_chunks: list[str] = []
        self._current_key: list[str] = []
        self._current_value: list[str] = []

        self.header: str | None = None
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set()
        for attr_name, attr_val in attrs:
            if attr_name == "class" and attr_val:
                classes = set(attr_val.split())
                break

        self._stack.append((tag, classes))

        if tag == "div" and "logo" in classes:
            self._in_logo = True
        elif tag == "div" and "header" in classes:
            self._in_header = True
            self._header_chunks = []
        elif tag == "div" and "info-line" in classes:
            self._in_info_line = True
            self._current_key = []
            self._current_value = []
        elif self._in_info_line and tag == "span" and "key" in classes:
            self._in_key = True
        elif self._in_info_line and tag == "span" and "value" in classes:
            self._in_value = True

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return

        # Pop until matching tag to stay resilient to minor HTML quirks
        while self._stack:
            popped_tag, classes = self._stack.pop()
            if popped_tag == "div" and "logo" in classes:
                self._in_logo = False
            elif popped_tag == "div" and "header" in classes:
                self._in_header = False
                header_text = " ".join("".join(self._header_chunks).split())
                if header_text:
                    self.header = header_text
            elif popped_tag == "span" and "key" in classes:
                self._in_key = False
            elif popped_tag == "span" and "value" in classes:
                self._in_value = False
            elif popped_tag == "div" and "info-line" in classes:
                self._in_info_line = False
                key = " ".join("".join(self._current_key).split())
                value = " ".join("".join(self._current_value).split())
                if key or value:
                    self.items.append({"key": key, "value": value})
            if popped_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._in_logo:
            self._logo_chunks.append(data)
        elif self._in_header:
            self._header_chunks.append(data)
        elif self._in_key:
            self._current_key.append(data)
        elif self._in_value:
            self._current_value.append(data)

    def get_logo_lines(self) -> list[str]:
        raw = "".join(self._logo_chunks).replace("\r\n", "\n").replace("\r", "\n")
        if not raw:
            return []

        raw_lines = raw.split("\n")
        subsequent_non_empty = [line for line in raw_lines[1:] if line.strip() != ""]
        strip_template_indent = bool(subsequent_non_empty) and all(
            line.startswith("        ") for line in subsequent_non_empty
        )

        cleaned: list[str] = []
        for idx, line in enumerate(raw_lines):
            # netfetch's neofetch.html indents every line after the first with 8 spaces
            if idx > 0 and strip_template_indent and line.startswith("        "):
                line = line[8:]
            cleaned.append(line.rstrip())

        while cleaned and cleaned[0] == "":
            cleaned.pop(0)
        while cleaned and cleaned[-1] == "":
            cleaned.pop()

        return cleaned


GPU_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
GPU_IGNORED_TAGS = {"discrete", "integrated", "unknown"}


def clean_gpu_value(val: str) -> str:
    for match in GPU_BRACKET_RE.findall(val):
        inside = match.strip()
        if inside and inside.lower() not in GPU_IGNORED_TAGS:
            return inside
    return val


def parse_netfetch_html(html: str) -> dict:
    parser = NetfetchHTMLParser()
    parser.feed(html)
    parser.close()

    items = []
    for item in parser.items:
        key = item["key"]
        val = item["value"]
        if key.lower().startswith("gpu"):
            val = clean_gpu_value(val)
        items.append({"key": key, "value": val})

    return {
        "header": parser.header,
        "logo": parser.get_logo_lines(),
        "items": items,
    }


def mark_offline(existing: dict | None, label: str) -> dict:
    if existing and existing.get("items"):
        items: list[dict[str, str]] = []
        uptime_found = False
        for item in existing.get("items", []):
            key = str(item.get("key", ""))
            value = str(item.get("value", ""))
            if key.strip().lower().rstrip(":") == "uptime":
                items.append({"key": key or "Uptime:", "value": "offline"})
                uptime_found = True
            else:
                items.append({"key": key, "value": value})

        if not uptime_found:
            items.append({"key": "Uptime:", "value": "offline"})

        return {
            "label": label,
            "online": False,
            "header": existing.get("header"),
            "logo": existing.get("logo", []),
            "items": items,
            "last_seen": existing.get("last_seen"),
        }

    return {
        "label": label,
        "online": False,
        "header": None,
        "logo": [],
        "items": [{"key": "Uptime:", "value": "offline"}],
        "last_seen": None,
    }


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[netfetch-fetcher] Failed to read cache {path}: {exc}")
        return {}


def save_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def fetch_machine(url: str, timeout: float) -> dict | None:
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "PersonalPage-NetfetchFetcher/1.0"},
        )
        resp.raise_for_status()
        parsed = parse_netfetch_html(resp.text)
        if not parsed["items"] and not parsed["header"]:
            return None
        return parsed
    except requests.RequestException as exc:
        print(f"[netfetch-fetcher] Request failed for {url}: {exc}")
        return None


def main() -> None:
    output_path = Path(NETFETCH_OUTPUT_PATH)
    cache = load_cache(output_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    result: dict[str, dict] = {}

    for machine_id, label, url in MACHINES:
        existing = cache.get(machine_id) if isinstance(cache.get(machine_id), dict) else None
        fetched = fetch_machine(url, NETFETCH_TIMEOUT)

        if fetched is not None:
            result[machine_id] = {
                "label": label,
                "online": True,
                "header": fetched["header"],
                "logo": fetched["logo"],
                "items": fetched["items"],
                "last_seen": now_iso,
            }
        else:
            result[machine_id] = mark_offline(existing, label)

    save_atomic(output_path, result)


if __name__ == "__main__":
    main()

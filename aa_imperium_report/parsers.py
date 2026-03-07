"""
parsers.py — Parse IMP ESI compliance report text into structured data.

Expected format (one corporation per line):
  [PASS]  Corp Name  (0 unregistered)
  [FAIL]  Corp Name  (5 unregistered: Pilot A, Pilot B, ...)
  [NO TOKEN]  Corp Name
"""
import re
import logging

logger = logging.getLogger(__name__)

# Status keywords to detect
_STATUS_MAP = {
    "PASS":     "PASS",
    "FAIL":     "FAIL",
    "NO TOKEN": "NO_TOKEN",
    "NO_TOKEN": "NO_TOKEN",
}

_LINE_RE = re.compile(
    r"\[(?P<status>[A-Z_ ]+)\]\s*(?P<corp>.+?)(?:\s*\((?P<detail>[^)]*)\))?\s*$",
    re.IGNORECASE,
)
_UNREG_COUNT_RE = re.compile(r"(\d+)\s+unregistered", re.IGNORECASE)
_UNREG_NAMES_RE = re.compile(r"unregistered\s*:\s*(.+)", re.IGNORECASE)


def parse_imp_esi_report(raw_text: str) -> list:
    """
    Parse a raw IMP ESI compliance text report.

    Returns a list of dicts:
      {
        "corp":         str,
        "status":       "PASS" | "FAIL" | "NO_TOKEN" | "UNKNOWN",
        "unregistered": [str, ...]   # pilot names, may be empty
      }
    """
    results = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = _LINE_RE.match(line)
        if not m:
            logger.debug("ESI parser: skipping unrecognised line: %r", line)
            continue

        raw_status = m.group("status").strip().upper()
        status = _STATUS_MAP.get(raw_status, "UNKNOWN")
        corp   = m.group("corp").strip()
        detail = m.group("detail") or ""

        # Extract unregistered pilot names from detail string
        unregistered = []
        names_m = _UNREG_NAMES_RE.search(detail)
        if names_m:
            raw_names = names_m.group(1)
            unregistered = [n.strip() for n in raw_names.split(",") if n.strip()]
        elif status == "FAIL":
            # Try to get a count even if no names
            count_m = _UNREG_COUNT_RE.search(detail)
            if count_m:
                unregistered = [""] * int(count_m.group(1))

        results.append({
            "corp":         corp,
            "status":       status,
            "unregistered": unregistered,
        })

    logger.info("ESI parser: %d corps parsed", len(results))
    return results


def summarize_results(parsed: list) -> dict:
    """
    Return aggregate counts from parse_imp_esi_report() output.

    Returns:
      {
        "total":        int,
        "pass":         int,
        "fail":         int,
        "no_token":     int,
        "unknown":      int,
        "unregistered": int   # total unregistered pilot count across all corps
      }
    """
    total        = len(parsed)
    pass_count   = sum(1 for r in parsed if r["status"] == "PASS")
    fail_count   = sum(1 for r in parsed if r["status"] == "FAIL")
    no_tok_count = sum(1 for r in parsed if r["status"] == "NO_TOKEN")
    unknown      = sum(1 for r in parsed if r["status"] == "UNKNOWN")
    unreg_total  = sum(len(r["unregistered"]) for r in parsed)

    return {
        "total":        total,
        "pass":         pass_count,
        "fail":         fail_count,
        "no_token":     no_tok_count,
        "unknown":      unknown,
        "unregistered": unreg_total,
    }

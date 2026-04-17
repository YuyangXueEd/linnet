import json
import re
from html import unescape
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx


def _normalize_job_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url.strip())
    except Exception:
        return url.strip().lower().rstrip("/")

    # Drop query and fragment to avoid feed-specific tracking params causing duplicates.
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def _dedupe_job_key(job: dict[str, Any]) -> str:
    normalized_url = _normalize_job_url(job.get("url", ""))
    if normalized_url:
        return f"url:{normalized_url}"

    title = re.sub(r"\s+", " ", job.get("title", "")).strip().lower()
    institution = re.sub(r"\s+", " ", job.get("institution", "")).strip().lower()
    deadline = re.sub(r"\s+", " ", job.get("deadline", "")).strip().lower()
    return f"fallback:{title}|{institution}|{deadline}"


def dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in jobs:
        key = _dedupe_job_key(job)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)
    return deduped


def filter_job(
    job: dict,
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> bool:
    """
    Return True if job text contains at least one include keyword
    AND zero exclude keywords.
    """
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    if any(ex.lower() in text for ex in exclude_keywords):
        return False
    return any(inc.lower() in text for inc in include_keywords)


def _clean_html_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_job_posting_schema(html: str) -> dict[str, Any] | None:
    scripts = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for script in scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                return candidate
    return None


def _extract_jobs_ac_uk_table_details(html: str) -> dict[str, str]:
    """Extract key details from jobs.ac.uk advert details table."""
    details = {
        "institution": "",
        "location": "",
        "salary": "",
        "hours": "",
        "contract_type": "",
        "placed_on": "",
        "deadline": "",
        "job_ref": "",
    }

    employer_match = re.search(
        r'<h3\b[^>]*class="[^"]*j-advert__employer[^"]*"[^>]*>(.*?)</h3>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if employer_match:
        details["institution"] = _clean_html_text(employer_match.group(1))

    row_pattern = re.compile(
        r"<tr>\s*<th\b[^>]*>(.*?)</th>\s*<td\b[^>]*>(.*?)</td>\s*</tr>",
        re.IGNORECASE | re.DOTALL,
    )
    key_map = {
        "location": "location",
        "salary": "salary",
        "hours": "hours",
        "contract type": "contract_type",
        "placed on": "placed_on",
        "closes": "deadline",
        "job ref": "job_ref",
    }

    for raw_key, raw_value in row_pattern.findall(html):
        key = _clean_html_text(raw_key).rstrip(":").lower()
        value = _clean_html_text(raw_value)
        target = key_map.get(key)
        if target and value:
            details[target] = value

    return details


def _extract_location_from_posting(posting: dict[str, Any]) -> str:
    job_location = posting.get("jobLocation")
    locations = job_location if isinstance(job_location, list) else [job_location]
    parts: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if isinstance(address, str):
            cleaned = address.strip()
            if cleaned:
                parts.append(cleaned)
            continue
        if isinstance(address, dict):
            locality = address.get("addressLocality", "")
            region = address.get("addressRegion", "")
            country = address.get("addressCountry", "")
            location_parts = [item for item in [locality, region, country] if item]
            if location_parts:
                parts.append(", ".join(location_parts))
    return " / ".join(dict.fromkeys(parts))


def _coerce_salary(base_salary: Any) -> str:
    if isinstance(base_salary, str):
        return base_salary.strip()
    if not isinstance(base_salary, dict):
        return ""

    value = base_salary.get("value")
    currency = base_salary.get("currency", "")
    if isinstance(value, dict):
        min_value = value.get("minValue")
        max_value = value.get("maxValue")
        unit = value.get("unitText", "")
        if min_value and max_value:
            salary = (
                f"{currency}{min_value}-{currency}{max_value}"
                if currency
                else f"{min_value}-{max_value}"
            )
        elif min_value:
            salary = f"{currency}{min_value}" if currency else str(min_value)
        elif value.get("value"):
            salary = f"{currency}{value['value']}" if currency else str(value["value"])
        else:
            salary = ""
        return f"{salary} {unit}".strip()
    if value:
        return f"{currency}{value}".strip()
    return ""


def enrich_job_details(job: dict[str, Any], request_timeout: float = 20.0) -> dict[str, Any]:
    url = job.get("url", "")
    if not url:
        return job

    try:
        response = httpx.get(
            url,
            timeout=request_timeout,
            follow_redirects=True,
            headers={"User-Agent": "Linnet/1.0"},
        )
        response.raise_for_status()
    except Exception:
        return job

    enriched = dict(job)
    posting = _extract_job_posting_schema(response.text)
    if posting:
        organization = posting.get("hiringOrganization") or {}
        enriched["description"] = _clean_html_text(posting.get("description", "")) or enriched.get(
            "description", ""
        )
        if isinstance(organization, dict):
            enriched["institution"] = organization.get("name", enriched.get("institution", ""))
        enriched["deadline"] = posting.get(
            "validThrough", enriched.get("deadline", "")
        ) or enriched.get("deadline", "")
        enriched["salary"] = _coerce_salary(posting.get("baseSalary")) or enriched.get("salary", "")
        posting_location = _extract_location_from_posting(posting)
        if posting_location:
            enriched["location"] = posting_location

    # Fallback for jobs.ac.uk pages where JSON-LD is absent/incomplete.
    details = _extract_jobs_ac_uk_table_details(response.text)
    for field in [
        "institution",
        "location",
        "salary",
        "hours",
        "contract_type",
        "placed_on",
        "job_ref",
    ]:
        if not enriched.get(field) and details.get(field):
            enriched[field] = details[field]
    if not enriched.get("deadline") and details.get("deadline"):
        enriched["deadline"] = details["deadline"]

    return enriched


def parse_feed_entry(entry: Any, source_name: str) -> dict[str, Any]:
    return {
        "title": getattr(entry, "title", ""),
        "url": getattr(entry, "link", ""),
        "description": getattr(entry, "summary", ""),
        "posted_date": getattr(entry, "published", ""),
        "source": source_name,
        "deadline": "",  # extracted later by summarizer
        "requirements": "",  # filled by summarizer
        "relevance_score": 0.0,
        "institution": "",
        "location": "",
        "salary": "",
        "hours": "",
        "contract_type": "",
        "placed_on": "",
        "job_ref": "",
    }


def _parse_findapostdoc_markdown(md: str, source_name: str) -> list[dict[str, Any]]:
    """Parse findapostdoc.com markdown returned by r.jina.ai."""
    jobs = []
    # Each job block is preceded by the shortlist button pattern
    blocks = re.split(r"\[\]\(javascript:void\(0\)[^)]*\)", md)
    for block in blocks:
        title_match = re.search(
            r"\[([^\]]+)\]\((https://www\.findapostdoc\.com/search/Job-Details\.aspx\?jobcode=\d+)[^)]*\)",
            block,
        )
        if not title_match:
            continue
        title = title_match.group(1).strip()
        url = title_match.group(2).strip()
        after = block[title_match.end() :]
        lines = [ln.strip() for ln in after.split("\n") if ln.strip() and not ln.startswith("[")]
        institution = lines[0] if lines else ""
        posted_date = ""
        deadline = ""
        date_m = re.search(r"Date Posted:\s*(.+)", after)
        dl_m = re.search(r"Application Deadline:\s*(.+)", after)
        if date_m:
            posted_date = date_m.group(1).strip()
        if dl_m:
            deadline = dl_m.group(1).strip()
        description = ""
        read_more = re.search(r"\[Read more\]", after)
        if read_more:
            raw = after[: read_more.start()]
            # Strip the institution line from the front
            raw = re.sub(r"^\s*" + re.escape(institution) + r"\s*", "", raw)
            description = re.sub(r"\s+", " ", raw).strip()
        jobs.append(
            {
                "title": title,
                "url": url,
                "description": description,
                "institution": institution,
                "posted_date": posted_date,
                "deadline": deadline,
                "source": source_name,
                "requirements": "",
                "relevance_score": 0.0,
                "location": "",
                "salary": "",
                "hours": "",
                "contract_type": "",
                "placed_on": "",
                "job_ref": "",
            }
        )
    return jobs


def _parse_euraxess_markdown(md: str, source_name: str) -> list[dict[str, Any]]:
    """Parse euraxess.ec.europa.eu/jobs/search markdown returned by r.jina.ai.

    Entries are rendered as ### headings by jina when URL filters are applied.
    """
    jobs = []
    # Split on ### job entry headings; each block ends at the next ### or ####
    blocks = re.split(r"\n(?=### \[)", md)
    for block in blocks:
        title_m = re.match(
            r"### \[([^\]]+)\]\((https://euraxess\.ec\.europa\.eu/jobs/[^)]+)\)",
            block,
        )
        if not title_m:
            continue
        # Skip footer navigation entries (e.g. "Jobs & Opportunities")
        if "euraxess.ec.europa.eu/jobs/search" in title_m.group(2):
            continue

        title = title_m.group(1).strip()
        url = title_m.group(2).strip()
        body = block[title_m.end() :]

        # Description: all prose text, stopping before metadata bullets or "Posted on"
        desc_end = re.search(r"\n\s*[\*\-]\s+\*\*|Posted on:", body)
        raw_desc = body[: desc_end.start()] if desc_end else body
        description = re.sub(r"\s+", " ", raw_desc).strip()

        # Posted date
        posted_date = ""
        posted_m = re.search(r"Posted on:\s*(.+)", body)
        if posted_m:
            posted_date = posted_m.group(1).strip()

        # Research field from bullet metadata
        field = ""
        field_m = re.search(r"Research Field:\s*\[([^\]]+)\]", body)
        if field_m:
            field = field_m.group(1).strip()

        # Deadline from body text
        deadline = ""
        dl_m = re.search(r"(?:deadline|closing date|apply by):\s*([^\n.]+)", body, re.IGNORECASE)
        if dl_m:
            deadline = dl_m.group(1).strip()

        jobs.append(
            {
                "title": title,
                "url": url,
                "description": f"{description} [Field: {field}]" if field else description,
                "institution": "",
                "posted_date": posted_date,
                "deadline": deadline,
                "source": source_name,
                "requirements": "",
                "relevance_score": 0.0,
                "location": "",
                "salary": "",
                "hours": "",
                "contract_type": "",
                "placed_on": "",
                "job_ref": "",
            }
        )
    return jobs


def _parse_academicpositions_markdown(md: str, source_name: str) -> list[dict[str, Any]]:
    """Parse academicpositions.com markdown returned by r.jina.ai."""
    jobs = []
    job_pattern = re.compile(r"\[####\s+([^\]]+)\]\((https://academicpositions\.com/ad/[^)]+)\)")
    for match in job_pattern.finditer(md):
        title_desc = match.group(1).strip()
        url = match.group(2).strip()
        # Split title from inline description: find first sentence boundary
        # that isn't inside an abbreviation (e.g. "Ph.D.", "Prof.")
        sent_m = re.search(r"(?<!Prof)(?<!Mrs)(?<![A-Z][a-z])\.\s+(?=[A-Z])", title_desc)
        if sent_m:
            title = title_desc[: sent_m.start() + 1].strip()
            description = title_desc[sent_m.end() :].strip()
        else:
            title = title_desc
            description = ""
        # Look back for employer link and location
        before = md[max(0, match.start() - 400) : match.start()]
        inst_m = re.search(
            r"\[([^\]]+)\]\(https://academicpositions\.com/employer/[^)]+\)",
            before,
        )
        institution = inst_m.group(1).strip() if inst_m else ""
        location = ""
        if inst_m:
            after_inst = before[inst_m.end() :]
            loc_lines = [
                ln.strip()
                for ln in after_inst.split("\n")
                if ln.strip() and not ln.strip().startswith("[") and not ln.strip().startswith("#")
            ]
            if loc_lines:
                location = loc_lines[0]
        # Published date
        after = md[match.end() : match.end() + 300]
        pub_m = re.search(r"Published\s+(.+?)(?:\n|$)", after)
        posted_date = pub_m.group(1).strip() if pub_m else ""
        jobs.append(
            {
                "title": title,
                "url": url,
                "description": description,
                "institution": institution,
                "posted_date": posted_date,
                "deadline": "",
                "source": source_name,
                "requirements": "",
                "relevance_score": 0.0,
                "location": location,
                "salary": "",
                "hours": "",
                "contract_type": "",
                "placed_on": "",
                "job_ref": "",
            }
        )
    return jobs


def fetch_jina_source(source: dict[str, Any], jina_timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch a job listing page via r.jina.ai and parse the returned markdown."""
    url = source["url"]
    name = source["name"]
    source_type = source.get("type", "")
    jina_url = f"https://r.jina.ai/{url}"
    try:
        resp = httpx.get(
            jina_url,
            headers={"Accept": "text/markdown", "X-Return-Format": "markdown"},
            timeout=jina_timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        print(f"  [warn] jina fetch failed for {name}: {exc}")
        return []
    md = resp.text
    if source_type == "findapostdoc":
        return _parse_findapostdoc_markdown(md, name)
    if source_type == "academicpositions":
        return _parse_academicpositions_markdown(md, name)
    if source_type == "euraxess":
        return _parse_euraxess_markdown(md, name)
    return []


def fetch_jobs(
    rss_sources: list[dict],
    filter_keywords: list[str],
    exclude_keywords: list[str],
    jina_sources: list[dict] | None = None,
    request_timeout: float = 20.0,
    jina_timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Parse all RSS and Jina sources, filter for relevant jobs."""
    jobs = []
    for source in rss_sources:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            job = parse_feed_entry(entry, source_name=source["name"])
            if filter_job(job, filter_keywords, exclude_keywords):
                jobs.append(enrich_job_details(job, request_timeout=request_timeout))
    for source in jina_sources or []:
        for job in fetch_jina_source(source, jina_timeout=jina_timeout):
            if filter_job(job, filter_keywords, exclude_keywords):
                jobs.append(job)
    return dedupe_jobs(jobs)

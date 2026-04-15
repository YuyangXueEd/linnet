from extensions.postdoc_jobs.collector import (
    _extract_job_posting_schema,
    _extract_jobs_ac_uk_table_details,
    dedupe_jobs,
    enrich_job_details,
    filter_job,
    parse_feed_entry,
)


def test_filter_job_passes_relevant():
    job = {
        "title": "Postdoc in Medical Imaging AI",
        "description": "We seek candidates with expertise in deep learning for MRI segmentation.",
    }
    assert (
        filter_job(
            job,
            include_keywords=["medical imaging", "deep learning", "postdoc"],
            exclude_keywords=["chemistry"],
        )
        is True
    )


def test_filter_job_blocks_excluded():
    job = {
        "title": "Research Associate in Computational Chemistry",
        "description": "Machine learning for drug discovery and molecular modelling.",
    }
    assert (
        filter_job(
            job,
            include_keywords=["machine learning", "research associate"],
            exclude_keywords=["chemistry"],
        )
        is False
    )


def test_filter_job_blocks_irrelevant():
    job = {
        "title": "Lecturer in Economics",
        "description": "Teaching undergraduate economics and supervising postgraduates.",
    }
    assert (
        filter_job(
            job,
            include_keywords=["computer vision", "LLM", "deep learning"],
            exclude_keywords=["economics"],
        )
        is False
    )


def test_parse_feed_entry_extracts_fields():
    entry = type(
        "Entry",
        (),
        {
            "title": "Research Associate in AI",
            "link": "https://jobs.ac.uk/job/XYZ",
            "summary": "Deadline: 1 May 2026. Requires deep learning expertise.",
            "published": "Mon, 13 Apr 2026 09:00:00 +0000",
        },
    )()
    job = parse_feed_entry(entry, source_name="jobs.ac.uk")
    assert job["title"] == "Research Associate in AI"
    assert job["url"] == "https://jobs.ac.uk/job/XYZ"
    assert job["source"] == "jobs.ac.uk"
    assert "description" in job


def test_extract_job_posting_schema():
    html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Research Associate in AI",
            "description": "<p>Great role.</p>",
            "validThrough": "2026-05-01",
            "hiringOrganization": {"name": "Example University"},
            "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
            "baseSalary": {"currency": "GBP", "value": {"minValue": 40000, "maxValue": 50000, "unitText": "YEAR"}}
        }
        </script>
        </head></html>
        """
    posting = _extract_job_posting_schema(html)
    assert posting is not None
    assert posting["@type"] == "JobPosting"
    assert posting["title"] == "Research Associate in AI"


def test_enrich_job_details_from_job_posting(httpx_mock):
    httpx_mock.add_response(
        url="https://jobs.ac.uk/job/XYZ",
        text="""
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "description": "<p>Needs deep learning and MRI experience.</p>",
                    "validThrough": "2026-05-01",
                    "hiringOrganization": {"name": "Example University"},
                    "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
                    "baseSalary": {"currency": "GBP", "value": {"minValue": 40000, "maxValue": 50000, "unitText": "YEAR"}}
                }
                </script>
                """,
    )
    job = {
        "title": "Research Associate in AI",
        "url": "https://jobs.ac.uk/job/XYZ",
        "description": "Short summary",
        "source": "jobs.ac.uk",
        "deadline": "",
        "requirements": "",
        "relevance_score": 0.0,
        "institution": "",
        "location": "",
        "salary": "",
    }
    enriched = enrich_job_details(job)
    assert enriched["institution"] == "Example University"
    assert enriched["deadline"] == "2026-05-01"
    assert enriched["location"] == "London, UK"
    assert enriched["salary"] == "GBP40000-GBP50000 YEAR"
    assert "deep learning" in enriched["description"]


def test_extract_jobs_ac_uk_table_details_from_html():
    html = """
        <h3 class="j-advert__employer row-4"><b><span>Queen Mary University of London</span></b> - Blizard Institute</h3>
        <div class="j-advert-details__container row-5">
            <table>
                <tr><th class="j-advert-details__table-header">Location:</th><td>London</td></tr>
                <tr><th class="j-advert-details__table-header">Salary:</th><td>£38,419 to £46,618 per annum.</td></tr>
                <tr><th class="j-advert-details__table-header">Hours:</th><td>Full Time</td></tr>
                <tr><th class="j-advert-details__table-header">Contract Type:</th><td>Fixed-Term/Contract</td></tr>
                <tr><th class="j-advert-details__table-header">Placed On:</th><td>13th April 2026</td></tr>
                <tr><th class="j-advert-details__table-header">Closes:</th><td>26th April 2026</td></tr>
                <tr><th class="j-advert-details__table-header">Job Ref:</th><td>9461</td></tr>
            </table>
        </div>
        """
    details = _extract_jobs_ac_uk_table_details(html)
    assert details["institution"] == "Queen Mary University of London - Blizard Institute"
    assert details["location"] == "London"
    assert details["salary"] == "£38,419 to £46,618 per annum."
    assert details["hours"] == "Full Time"
    assert details["contract_type"] == "Fixed-Term/Contract"
    assert details["placed_on"] == "13th April 2026"
    assert details["deadline"] == "26th April 2026"
    assert details["job_ref"] == "9461"


def test_enrich_job_details_falls_back_to_jobs_ac_uk_table(httpx_mock):
    httpx_mock.add_response(
        url="https://jobs.ac.uk/job/ABC",
        text="""
                <h3 class="j-advert__employer row-4"><b><span>Queen Mary University of London</span></b> - Blizard Institute</h3>
                <div class="j-advert-details__container row-5">
                    <table>
                        <tr><th class="j-advert-details__table-header">Location:</th><td>London</td></tr>
                        <tr><th class="j-advert-details__table-header">Salary:</th><td>£38,419 to £46,618 per annum.</td></tr>
                        <tr><th class="j-advert-details__table-header">Closes:</th><td>26th April 2026</td></tr>
                    </table>
                </div>
                """,
    )
    job = {
        "title": "Postdoctoral Researcher",
        "url": "https://jobs.ac.uk/job/ABC",
        "description": "Short summary",
        "source": "jobs.ac.uk",
        "deadline": "",
        "requirements": "",
        "relevance_score": 0.0,
        "institution": "",
        "location": "",
        "salary": "",
        "hours": "",
        "contract_type": "",
        "placed_on": "",
        "job_ref": "",
    }
    enriched = enrich_job_details(job)
    assert enriched["institution"] == "Queen Mary University of London - Blizard Institute"
    assert enriched["location"] == "London"
    assert enriched["salary"] == "£38,419 to £46,618 per annum."
    assert enriched["deadline"] == "26th April 2026"


def test_dedupe_jobs_by_normalized_url_removes_tracking_variants():
    jobs = [
        {
            "title": "Postdoctoral Researcher in Medical Imaging",
            "url": "https://jobs.ac.uk/job/ABC?utm_source=rss",
            "institution": "Example University",
            "deadline": "2026-05-01",
            "source": "jobs.ac.uk Research",
        },
        {
            "title": "Postdoctoral Researcher in Medical Imaging",
            "url": "https://jobs.ac.uk/job/ABC?ref=computer-science",
            "institution": "Example University",
            "deadline": "2026-05-01",
            "source": "jobs.ac.uk CS",
        },
    ]

    deduped = dedupe_jobs(jobs)
    assert len(deduped) == 1


def test_dedupe_jobs_fallback_key_when_url_missing():
    jobs = [
        {
            "title": "Research Associate in AI",
            "url": "",
            "institution": "Example University",
            "deadline": "2026-05-01",
            "source": "FindAPostDoc",
        },
        {
            "title": "Research Associate in AI",
            "url": "",
            "institution": "Example University",
            "deadline": "2026-05-01",
            "source": "AcademicPositions",
        },
        {
            "title": "Research Associate in AI",
            "url": "",
            "institution": "Another University",
            "deadline": "2026-05-01",
            "source": "FindAPostDoc",
        },
    ]

    deduped = dedupe_jobs(jobs)
    assert len(deduped) == 2

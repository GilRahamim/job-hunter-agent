---
name: job-sources
description: How to fetch job postings for the Job Hunter project — verified endpoints and field mappings for Greenhouse, Lever, Ashby, SmartRecruiters, JobSpy (LinkedIn/Indeed/Glassdoor/Google), Remotive, RemoteOK, Himalayas, WeWorkRemotely and SerpAPI, plus the collector contract and error handling. Use this whenever writing, fixing or debugging anything in jobhunter/collectors/, adding a new job site or company to companies.yaml, or when a source returns zero jobs or errors.
---

# Job sources

Every collector turns one external source into `list[Job]`. The rest of the system never knows where a job came from except via `Job.source`.

## Collector contract

```python
# collectors/base.py
@dataclass
class CollectorResult:
    source: str
    jobs: list[Job]
    error: str | None = None      # shown on the dashboard "Sources" tab

def collect_greenhouse(cfg: dict, companies: list[str]) -> CollectorResult: ...
```

Rules, and why:
- **Never raise.** Wrap the body, return `CollectorResult(source, partial_jobs, error=str(e))`. One site being down or changing format must not kill the daily run.
- **Partial success is success.** For per-company sources, a failing slug adds to an error summary (`"2/31 companies failed: foo(404), bar(timeout)"`) but the other companies' jobs are kept.
- **Normalize at the edge.** Convert HTML to plain text, dates to ISO `YYYY-MM-DD`, and set `is_remote`/`remote_region` inside the collector; downstream code assumes clean fields.
- **Do not filter by role/seniority here** — that is `filters.py`'s job, so filter rules live in one place. The only filtering allowed in a collector is what the API forces (e.g. a search query).
- One shared `requests.Session` (`base.get_session()`): User-Agent `Mozilla/5.0 (JobHunterAgent)`, timeout 15s, retry 3× with exponential backoff on 429/5xx (`urllib3.Retry`).
- Company sources: run companies in a `ThreadPoolExecutor(max_workers=8)`.

Helpers to put in `base.py`:
```python
def html_to_text(html: str) -> str:
    # Greenhouse content is HTML-ESCAPED HTML: unescape first, then strip tags.
    text = html_lib.unescape(html or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html_lib.unescape(text)).strip()

def to_iso(value) -> str | None:  # handles ISO strings, unix seconds, unix ms
```

## Sources at a glance

| Source key | What it covers | Auth | Notes |
|---|---|---|---|
| `jobspy` | LinkedIn, Indeed IL, Glassdoor, Google Jobs | none | Biggest coverage of Israeli jobs (Elbit, Mobileye, Google IL, startups). Slowest; can be rate-limited. |
| `company_boards` | ~40 Israeli tech companies' own boards | none | Highest-quality data (full descriptions). Slugs in `companies.yaml`. |
| `workday` | Large employers' boards (Intel, Nvidia, Marvell…) | none | POST JSON API; Israel filter via location facet. Entries in `companies.yaml` → `workday`. |
| `remotive`, `remoteok`, `himalayas`, `weworkremotely`, `arbeitnow` | Remote jobs worldwide | none | Most are US-only; region filtering matters. |
| `techmap` | Israeli Tech Map daily job CSVs (github.com/mluggy/techmap, ODbL), ~470 Israeli companies | none | One download per category; title/company/level/city, **no description** (links are mostly LinkedIn). |
| `getro` | VC portfolio job boards (Israel VC Forum ≈880 companies) | none | `POST api.getro.com/api/v2/collections/{id}/search/jobs` with `Accept: application/json` (406 without), `filters: {searchable_locations: ["Israel"]}`, 20 per page; seniority tag, no description. |
| `serpapi_google_jobs` | Google Jobs (indexes AllJobs, Drushim, Comeet pages…) | `SERPAPI_API_KEY` | Free plan 250 searches/month, one per query: uses its own short `queries` list (falls back to `search.queries`). |

Exact endpoints, response shapes and field mappings for each source: **read `references/endpoints.md`** before writing a collector. Those mappings were verified against live responses on 2026-10-13.

## JobSpy usage

```python
from jobspy import scrape_jobs
df = scrape_jobs(
    site_name=["linkedin", "indeed", "glassdoor", "google"],
    search_term=query,
    google_search_term=f"{query} jobs in Israel since last week",
    location="Israel",
    country_indeed="israel",
    results_wanted=cfg["search"]["results_per_query"],
    hours_old=cfg["search"]["hours_old"],
    linkedin_fetch_description=cfg["sources"]["jobspy"]["fetch_linkedin_descriptions"],
)
```
- Run **one query at a time** with `time.sleep(2–4)` between queries; parallel queries get LinkedIn to block you.
- Also run a remote pass: `location="Remote"` with `is_remote=True` for the AI/ML queries.
- Columns used: `site, title, company, location, job_url, job_url_direct, description, date_posted, is_remote`. Values can be `NaN` — coerce with `str(x) if pd.notna(x) else ""`.
- Prefer `job_url_direct` as the URL when present (it is the company's own page and dedupes better); fall back to `job_url`.
- Indeed Israel returns Hebrew city names (`רחובות, M, Israel`) — that is fine; `filters.py` handles Hebrew.
- `source` = `f"jobspy:{site}"` so the dashboard can show LinkedIn vs Indeed separately.
- Established employers (banks, health funds, insurance, defense, IT services) come in through `search.employers`: `employer_queries()` turns each group into one Israel-only Boolean search, `("Bank Leumi" OR Isracard) AND (developer OR "data analyst")` (multi-word terms quoted, roles from `search.employer_roles`). They run after the regular and remote passes. Keep groups short and names unambiguous; a bare "Max" or "Cal" matches every posting.
- Wrap each site separately if one fails: a Glassdoor error should not lose the LinkedIn results (call `scrape_jobs` per site when the combined call raises).

## Adding companies in bulk
`python scripts/sync_companies.py [--scan-careers] [--dry-run]` reads the Israeli Tech Map company files (comeetId / greenhouseId / leverId / careersUrl), its job links and the Getro boards' job links, checks every board live, and appends the ones with Israel jobs to `companies.yaml`.

## Missing descriptions
`collectors/details.py` reads a LinkedIn job's description with JobSpy's own job-page reader (`LinkedIn()._fetch_details`), never custom LinkedIn scraping. The pipeline does it for the best-pre-scored kept jobs without one (`matching.fetch_descriptions`), then re-applies the experience rules; the agent does it in `read_posting`.
The same page request (`fetch_posting`) also reports closed jobs: LinkedIn marks them with
`<figcaption class="closed-job__flavor--closed">No longer accepting applications</figcaption>`
(verified 2026-10-15). JobSpy's `_fetch_details` ignores that banner, so we GET the page with JobSpy's
session and parse it with JobSpy's helpers. Closed jobs are dropped (reason `closed`) in the pipeline,
and the agent's `save_match` refuses them.

## Adding a company

1. Open the company's careers page; look at the job links or "Apply" URL:
   - `boards.greenhouse.io/<slug>` or `?gh_jid=` → Greenhouse (slug sometimes differs from the name: `wizinc`, `gongio`)
   - `jobs.lever.co/<slug>` → Lever
   - `jobs.ashbyhq.com/<slug>` → Ashby
   - `jobs.smartrecruiters.com/<Slug>` → SmartRecruiters
   - `{tenant}.wd{N}.myworkdayjobs.com/{site}` → Workday: add `{tenant: ..., wd: wdN, site: ...}`
   - `comeet.com/jobs/...` → Comeet: needs uid + token from the page (see endpoints.md, not yet verified); until implemented, covered via JobSpy/Google.
2. Add the slug to `companies.yaml` and run `python scripts/check_boards.py` (copy it from this skill's `scripts/check_boards.py`) — it prints total jobs and Israel jobs per slug, and lists dead slugs.
3. A slug that returns jobs but 0 in Israel can still be worth keeping if the company hires remote.

## Debugging a source that returns 0 jobs
1. Hit the endpoint with `curl` and compare the JSON keys to `references/endpoints.md` — APIs drift.
2. 404 on a company board usually means the company moved ATS; re-check its careers page.
3. JobSpy returning empty for LinkedIn usually means rate-limiting: wait, lower `results_per_query`, keep sleeps.
4. Add a fixture for the new response shape and a failing parser test before fixing (see `offline-testing`).

# Endpoints and field mappings

Verified against live responses on 2026-10-13. If a source breaks, compare its current JSON keys with this file first.

Contents: Greenhouse · Lever · Ashby · SmartRecruiters · Remotive · RemoteOK · Himalayas · WeWorkRemotely · Arbeitnow · SerpAPI · JobSpy columns

---

## Greenhouse
`GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
Response: `{"jobs": [...], "meta": {...}}`

| Job field | From | Notes |
|---|---|---|
| title | `title` | |
| company | `company_name` | fallback: slug |
| url | `absolute_url` | may point to the company's own site (`join.jfrog.com/...?gh_jid=`) — fine |
| location | `location.name` | e.g. `"Tel Aviv, Israel"`, `"Sunnyvale, California, United States"`; also `offices[].name` |
| description | `content` | **HTML-escaped HTML** (`&lt;p&gt;...`) → `html_to_text` unescapes twice |
| date_posted | `first_published` or `updated_at` | ISO with offset |
| is_remote | `"remote" in location.name.lower()` | |

## Lever
`GET https://api.lever.co/v0/postings/{slug}?mode=json`
Response: a JSON **list**.

| Job field | From | Notes |
|---|---|---|
| title | `text` | |
| company | slug (title-cased) | not in payload |
| url | `hostedUrl` | |
| location | `categories.location`; all: `categories.allLocations` | |
| description | `descriptionPlain` + `additionalPlain` | plain text already; `lists[]` holds requirement bullets (`text` + HTML `content`) |
| date_posted | `createdAt` | **unix milliseconds** |
| is_remote | `workplaceType == "remote"` | values seen: `onsite`, `hybrid`, `remote` |
| extra | `categories.team`, `categories.commitment` | |

## Ashby
`GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false`
Response: `{"jobs": [...]}`

| Job field | From | Notes |
|---|---|---|
| title | `title` | |
| company | slug | |
| url | `jobUrl` | |
| location | `location` (+ `secondaryLocations[].location`) | e.g. `"Tel Aviv"` |
| description | `descriptionPlain` | |
| date_posted | `publishedAt` | ISO |
| is_remote | `isRemote` or `workplaceType == "Remote"` | values: `OnSite`, `Hybrid`, `Remote` |
| skip if | `isListed == False` | |

## SmartRecruiters
List: `GET https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset=0`
Response: `{"totalFound", "content": [...]}` — paginate with `offset` while `offset < totalFound`.
List items have **no description**. Detail: `GET .../postings/{id}` → `jobAd.sections.{companyDescription, jobDescription, qualifications, additionalInformation}.text` (HTML) and `postingUrl`.

| Job field | From |
|---|---|
| title | `name` |
| company | `company.name` |
| url | detail `postingUrl` (or `https://jobs.smartrecruiters.com/{slug}/{id}`) |
| location | `location.fullLocation`; country code `location.country` (`"il"`) |
| is_remote | `location.remote` |
| date_posted | `releasedDate` |
| description | detail `jobDescription.text + qualifications.text` → `html_to_text` |

Only fetch details for postings that pass a quick location check (country `il` or remote) to save requests.

## Workday (Intel, Nvidia, Marvell and many large companies)
Each company is a tenant + data-center number + site name, read from its careers URL:
`https://{tenant}.{wd}.myworkdayjobs.com/{site}` → e.g. `intel / wd1 / External`, `nvidia / wd5 / NVIDIAExternalCareerSite`, `marvell / wd1 / MarvellCareers`. A wrong site name returns **422**.

Search: `POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
Headers: `Content-Type: application/json`, `Accept: application/json`, browser User-Agent.
Body: `{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "Israel"}` — `limit` max 20; paginate with `offset` until `offset >= total`.
Response: `{"total", "jobPostings": [...], "facets": [...]}`; each posting has `title, externalPath, locationsText, postedOn ("Posted 9 Days Ago"), bulletFields`.

Filter to Israel precisely: in `facets`, find the location facet (name varies per tenant — `locationMainGroup`, `locations`, `locationCountry`…; values can be nested under `values[].values`), take the `id` of entries whose `descriptor` contains "Israel", and send them as `"appliedFacets": {"<facetParameter>": [ids]}` with `searchText: ""`. Fallback: `searchText: "Israel"` + `is_israel(locationsText)` (note `locationsText` can be "2 Locations" — then check the detail).

Detail: `GET https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{externalPath}` → `jobPostingInfo`:

| Job field | From |
|---|---|
| title | `title` |
| url | `externalUrl` |
| location | `location` + `additionalLocations[]` |
| description | `jobDescription` (HTML) |
| date_posted | `startDate` (ISO date) |
| company | tenant (title-cased) |

Fetch details only for Israel/remote postings. `postedOn` is relative text — use `startDate` from the detail instead.

## Comeet (common at Israeli startups) — not verified
Comeet's careers API needs a per-company `uid` and public `token`, which are embedded in the company's Comeet careers widget/page. Endpoint pattern: `https://www.comeet.co/careers-api/2.0/company/{uid}/positions?token={token}&details=true`. Could not verify a working example on 2026-10-13 — before implementing, take one company that uses Comeet, read the uid/token from its careers page HTML, and record a fixture. Until then these jobs arrive via JobSpy (LinkedIn/Google).

## Remotive
`GET https://remotive.com/api/remote-jobs?category={slug}` for `software-development`, `artificial-intelligence`, `data`, `devops`, `qa` (full list: `GET /api/remote-jobs/categories`). `?search=python` also works.
Response: `{"jobs": [...]}`. Their terms ask to not call more than a few times per day — once per run is fine.

| Job field | From |
|---|---|
| title / company / url | `title` / `company_name` / `url` |
| remote_region | `candidate_required_location` (e.g. `"Worldwide"`, `"USA"`, `"Europe"`) |
| description | `description` (HTML) |
| date_posted | `publication_date` (ISO, no tz) |
| is_remote | always `True` |

## RemoteOK
`GET https://remoteok.com/api` — **send a browser User-Agent**. Response: list whose **first element is a legal notice** (`{"legal", "last_updated"}`) — skip items without `position`. Attribution to RemoteOK is required by their terms if displayed publicly (personal use is fine).

| Job field | From |
|---|---|
| title / company | `position` / `company` |
| url | `url` (or `apply_url`) |
| remote_region | `location` (often empty = worldwide) |
| description | `description` (HTML) |
| date_posted | `date` (ISO) |
| extra | `tags[]` — useful for skill matching |

## Himalayas
`GET https://himalayas.app/jobs/api?limit=100&offset=0` (paginate; `totalCount`). Response: `{"jobs": [...], "totalCount", "offset", "limit"}`

| Job field | From |
|---|---|
| title / company / url | `title` / `companyName` / `applicationLink` |
| remote_region | `", ".join(locationRestrictions)` — **empty list = worldwide** |
| description | `description` (HTML) or `excerpt` |
| date_posted | `pubDate` (**unix seconds**) |
| extra | `seniority[]`, `categories[]` |

Himalayas returns all categories; cap pages (e.g. 5) and rely on filters.

## WeWorkRemotely (RSS)
`GET https://weworkremotely.com/categories/{cat}.rss` for `remote-back-end-programming-jobs`, `remote-full-stack-programming-jobs`, `remote-programming-jobs`, `remote-devops-sysadmin-jobs` (verified 200). `remote-data-science-jobs` redirects (301) — follow redirects or drop it. Parse with `xml.etree.ElementTree`.

| Job field | From |
|---|---|
| title, company | `title` is `"Company: Job Title"` → split on the first `": "` |
| url | `link` |
| remote_region | `region` (e.g. `"Anywhere in the World"`, `"USA Only"`) |
| description | `description` (HTML) |
| date_posted | `pubDate` (RFC 822 → `email.utils.parsedate_to_datetime`) |

## Arbeitnow
`GET https://www.arbeitnow.com/api/job-board-api?page=1` → `{"data": [...], "links", "meta"}`. Mostly Germany/EU; keep only `remote == True`.
Fields: `title, company_name, location, remote (bool), url, description (HTML), created_at (unix seconds), tags[]`.

## SerpAPI — Google Jobs (optional)
`GET https://serpapi.com/search.json?engine=google_jobs&q={query}&location=Israel&hl=en&api_key=...`
Results in `jobs_results[]`: `title, company_name, location, description, detected_extensions.posted_at, apply_options[].link, share_link, job_id`. Use the first `apply_options[].link` as URL (fallback `share_link`). Paginate with `next_page_token`. Skip the source entirely when `SERPAPI_API_KEY` is missing (not an error).

## JobSpy DataFrame columns (v1.3)
`id, site, job_url, job_url_direct, title, company, location, date_posted, job_type, is_remote, description, min_amount, max_amount, currency, job_level, company_industry, skills, experience_range, ...`
Known limitation: for Indeed, `hours_old` cannot be combined with `job_type`/`is_remote` — use only `hours_old` for Indeed.

# Additional job sources — research (2026-10-15)

Which job sites could the agent add, how each one can be read, and what it would add for the owner's search: **junior / no-experience CS roles in Israel, plus remote roles open to Israel**.

> **Verification status.** This is desk research. The research container's network blocked every job-site host (only GitHub was reachable), so **no endpoint below was called live**. Each source is marked:
> - ✅ **docs**: official documentation read on 2026-10-15
> - 🟡 **seen**: the endpoint appears in third-party code, scraper listings or search-index URLs, but was not called
> - ❔ **unknown**: the site exists, but no access method was found
>
> Before writing a collector, run the `job-sources` skill's check (curl the endpoint, compare its keys, record a fixture). Then move the verified details into `.claude/skills/job-sources/references/endpoints.md`.

---

## 1. Summary

**What is missing today**
1. **AllJobs, Drushim and JobMaster are not reached at all.** `docs/ARCHITECTURE.md` expects them to arrive through Google Jobs. But Google is off in JobSpy (`config.yaml`: "Google Jobs blocks scraping"), and `serpapi_google_jobs` is `enabled: false`.
2. **Junior-only channels.** Israel has a few curated feeds of no-experience tech jobs. These are exactly the target, and none is read.
3. **Big employers outside Workday.** Microsoft Israel (about 3,000 R&D staff) and Amazon (AWS, Annapurna Labs) both have JSON search endpoints.
4. **Companies on ATSs the agent does not read**: Workable, Breezy, BambooHR, Recruitee and others.
5. **Remote boards with an EMEA or Israel filter.** The current remote boards are mostly US-only.

**Top picks, best value for effort first**

| # | Source | What it adds | Effort | Status |
|---|---|---|---|---|
| 1 | More **Workday** tenants (Dell, Workday, GM, Forcepoint) | Israeli R&D centers incl. student roles | config only | 🟡 |
| 2 | More **Getro** boards (Aleph, others) | VC portfolio startups | config only | 🟡 |
| 3 | **SerpAPI Google Jobs**: enable it with its own small query list | AllJobs / Drushim / JobMaster / Comeet pages, legally | small code change | ✅ (collector exists) |
| 4 | **Goozali Telegram channels** (`hitechjobsjunior`, `hitechjobsisrael`) | hand-picked **no-experience** Israeli tech jobs | small collector | 🟡 |
| 5 | **Jobicy** API | remote jobs with a geo filter (an Israel region page exists) and a seniority field | small collector | ✅ |
| 6 | **Microsoft Careers** (Eightfold PCSX) as a new `eightfold` ATS type | Microsoft Israel R&D; PayPal and others use the same platform | small–medium | 🟡 |
| 7 | **Amazon Jobs** `search.json` | AWS / Annapurna Labs Israel | small | 🟡 |
| 8 | **Drushim** internal JSON search | Hebrew-only postings, a "no experience" filter, integrators and placement firms | medium, check ToS | 🟡 |
| 9 | **Workable** (and maybe Breezy, BambooHR…) as new ATS types | startups not on Greenhouse, Lever, Ashby or Comeet | medium; count users first | 🟡 |
| 10 | **Job-alert emails** (LinkedIn, Drushim, AllJobs…) read from a mailbox | sites without an API, using your own alert emails | medium | n/a |

**Avoid:** custom scrapers for AllJobs/Techit (PerimeterX and Radware bot protection), Wellfound, Glassdoor (no Israel search), Careerjet (no Israel locale), Adzuna (no Israel), the SimplifyJobs repos (US/Canada/Remote only), and the HiBob and Consider APIs (both need customer credentials). Details are in §8.

---

## 2. Current coverage (for reference)

| Area | Sources today |
|---|---|
| Aggregators | JobSpy → LinkedIn, Indeed IL |
| Israeli datasets | Israeli Tech Map CSVs (`techmap`), Getro: Israel VC Forum + Innovation Endeavors (`getro`) |
| Company boards (`companies.yaml`) | Comeet 153, Greenhouse 62, Ashby 17, Lever 6, Workday 3, SmartRecruiters 1 |
| Remote | Remotive, RemoteOK, Himalayas, WeWorkRemotely, Arbeitnow |
| Optional | SerpAPI Google Jobs (disabled) |

**What the Israeli Tech Map data says** (repo `mluggy/techmap`, cloned 2026-10-15):
- 7,950 companies. Only 1,291 have a `careersUrl`. ATS ids: `comeetId` 147, `greenhouseId` 27, `leverId` 7, `breezyId` 4.
- 2,727 jobs in the tech categories. Their links go to **LinkedIn in 2,257 cases (83%)**, Comeet in 463 and Lever in 7.

So the Tech Map cannot show which other ATSs Israeli companies use. That has to be measured from the companies' careers pages (§6).

---

## 3. Tier 1: config-only additions (no new code)

### 3.1 More Workday tenants 🟡
The Workday collector already exists: add entries under `workday:` in `companies.yaml`, then run `python run_agent.py --check-companies`. These tenants had postings in Israel in 2025–2026 (job URLs found through web search). **Added to `companies.yaml` on 2026-10-15; not live-checked yet.**

```yaml
  - {tenant: dell, wd: wd1, site: External}                     # Herzliya (Dell Israel R&D)
  - {tenant: workday, wd: wd5, site: Workday}                   # Tel Aviv (Workday / HiredScore): LLM, backend, DevOps
  - {tenant: generalmotors, wd: wd5, site: Careers_GM}          # Herzliya (GM Israel tech center), incl. student roles
  - {tenant: forcepoint, wd: wd1, site: external-careers}       # Tel Aviv: "Software Engineer - Student"
```

To check next (all have Israeli sites): KLA, Applied Materials, Salesforce, HP / HP Indigo, PayPal, Cadence, Philips, Motorola Solutions, Mastercard, Citi. Open each careers page. If the job links contain `{tenant}.wd{N}.myworkdayjobs.com/{site}`, add the entry.

### 3.2 More Getro boards 🟡
The Getro collector takes `{name, id}` in `config.yaml → sources.getro.boards`.
- **Aleph**: `jobs.aleph.vc`. Aleph says the board syncs with its portfolio companies' careers pages (Bringg, Anecdotes, Nexar, Healthy.io, Fabric…). It is in `config.yaml` as a commented-out line until its network id is known. It is not yet confirmed that the board runs on Getro.
- Worth checking for a Getro board: OurCrowd, Pitango, Viola, TLV Partners, Team8, Glilot, 83North, Vertex Israel, Grove, JVP, Entrée. Many of their companies are already among the Israel VC Forum's 876 companies, so expect partial overlap.
- **How to find a board's `id`:** open the board, then in the browser dev tools watch the request `POST api.getro.com/api/v2/collections/{id}/search/jobs`. Or search the page source for `"network":{"id"`.

### 3.3 SerpAPI Google Jobs: enable it, but give it its own query budget ✅
**Done on 2026-10-15:** enabled, with 8 queries of its own in `config.yaml` and relative-date parsing. A live run still needs `SERPAPI_API_KEY` in `.env`.

This is the cheapest legal way to reach **AllJobs, Drushim, JobMaster and Comeet-hosted pages**, because Google for Jobs indexes all of them. The collector exists, but it sends **every** `search.queries` entry (24 today) on every run. Third-party 2026 pricing pages report a free plan of **250 searches a month**. Daily runs would need

$$24 \times 30 = 720 > 250.$$

The fix is a small code change: add `sources.serpapi_google_jobs.queries` (a short list, Hebrew included) and use it instead of `search.queries`. With daily runs the budget allows

$$q \cdot 30 \le 250 \;\Rightarrow\; q \le 8 \text{ queries per run.}$$

Suggested queries: `מפתח תוכנה ג'וניור`, `ללא ניסיון פיתוח תוכנה`, `דרוש/ה בוגר/ת מדעי המחשב`, `Junior Software Engineer`, `Junior Data Analyst`, `Junior Python Developer`, `סטודנט תוכנה`, `QA ללא ניסיון`.

Gotchas:
- `detected_extensions.posted_at` is relative text ("3 days ago"), and `to_iso` probably returns `None` for it. Parse "N days/hours ago".
- The first `apply_options[].link` is often an AllJobs or Drushim page. That is fine, because dedupe works on company and title.

---

## 4. Tier 2: new small collectors

### 4.1 Goozali Telegram channels: junior-only, hand-picked 🟡
- **What:** Goozali (goozali.com, run by Avi Lewis) keeps a table of about 4,000 Israeli tech openings at about 900 companies, with a minimum-experience field. It also runs Telegram channels by field:
  - `t.me/hitechjobsjunior`: *"משרות ג׳וניור בהיי טק ללא ניסיון קודם — Israel Hi Tech Positions Entry Level"* (about 3,500 subscribers)
  - `t.me/hitechjobsisrael`: software engineering
  - (`t.me/hitechjobsales`: sales, not relevant)
- **Why:** every post in the junior channel is a no-experience role, the exact target. Expect low volume and high precision. A Globes article mentions about one junior post every two days, but that figure is older.
- **How:** the public web preview `GET https://t.me/s/<channel>` returns HTML with the latest ~20 posts and needs no login. Parse the `.tgme_widget_message` blocks: text in `.tgme_widget_message_text`, time in `time[datetime]`, post id in `data-post`. Page back with `?before=<id>`. Pull the apply link out of the text. For LinkedIn links, `details.py` already fetches descriptions.
- **Collector notes:** the source key is `telegram:<channel>`. Treat every job from the junior channel as junior; the filters still run. List the channels in `config.yaml` (`sources.telegram.channels`).
- **Risk:** posts are free text, so title and company extraction is best effort. The preview page shows only channels that enable it.

### 4.2 Jobicy: remote jobs with geo and seniority ✅
- `GET https://jobicy.com/api/v2/remote-jobs?count=100&geo=<slug>&industry=<slug>&tag=<kw>`, no key needed. Paginate with `nextCursor` until `hasMore` is `false`. Results cover the last 7 days.
- Get the valid slugs from `?get=locations` and `?get=industries`. A `jobicy.com/job-region/israel` page exists, so an `israel` geo slug is likely; also try `emea` and `europe`. Industry `engineering` (the old `dev`) and `data-science`.
- Fields: `id, url, jobTitle, companyName, jobIndustry[], jobType[], jobGeo, jobLevel, jobExcerpt, jobDescription (HTML), pubDate`, plus salary fields.
  - `jobLevel` is a seniority field. Put it in the description, as the Getro collector does, so the experience rules can see it.
- **Terms:** poll at most once an hour, keep the canonical `url`, and credit Jobicy. A batch status endpoint (`/remote-jobs/status?ids=…`) reports closed jobs.
- Effort: about 40 lines in `remote_boards.py`, plus a fixture.

### 4.3 Microsoft Careers: a new `eightfold` ATS type 🟡
- Microsoft moved its careers site to Eightfold (`apply.careers.microsoft.com`). Microsoft Israel R&D has about 3,000 employees and was hiring about 100 people (Calcalist, 2026).
- **Endpoint** (from third-party code, 2026): `GET https://microsoft.eightfold.ai/api/pcsx/search?domain=microsoft.com&location=Israel&start=0`. The response is `data.positions[]` with `id, name, locations, postedTs, positionUrl, atsJobId…`. Full text comes from `GET /api/pcsx/position_details?...`.
  - A 2026 measurement got 200 OK with 2,395 positions unfiltered.
  - The older `/api/apply/v2/jobs` returns **403 "Not authorized for PCSX"** on migrated tenants. Classic tenants (for example Netflix) still use it.
- **Rate limits:** about 5 quick pages trigger a 429. 1 request per second with backoff worked for about 20 pages.
- **Generic design:** `companies.yaml → eightfold: - {host: microsoft.eightfold.ai, domain: microsoft.com}`. Try PCSX first; on a 403 fall back to `/api/apply/v2/jobs`. The careers page embeds a `pcsxConfig` block that contains the `domain`. Other Eightfold tenants mentioned: PayPal (Israel R&D), Morgan Stanley.

### 4.4 Amazon Jobs 🟡
- `GET https://www.amazon.jobs/en/search.json?normalized_country_code[]=ISR&result_limit=100&offset=0&sort=recent`. This is undocumented; third-party scrapers use it.
- Response: `hits` (total) and `jobs[]`. Each job has `title, normalized_location, posted_date, job_path, description, basic_qualifications, preferred_qualifications`.
  - Build the URL as `https://www.amazon.jobs` + `job_path`.
  - Put the qualifications into the description, because that is where the experience rules look.
- Filter by **country code**. A scraper reports that `loc_query` alone returns other countries.
- Coverage: AWS Israel, Annapurna Labs (Haifa, Tel Aviv) and Amazon's other Israeli teams.

---

## 5. Tier 3: Israeli job boards (high value, harder access)

| Site | What it is | Access found | Recommendation |
|---|---|---|---|
| **Drushim** (drushim.co.il, Yad2 group) | Big Hebrew board; filters for experience ("ללא ניסיון"), category, region, scope | 🟡 The site's own **internal JSON search** (results in `ResultList`, about 10 per page; region ids like `geoLexId` 539071 = Center). No official API. | **Best direct Israeli collector.** Check `robots.txt` and the terms first. Personal use only, low rate (one query per field, a few pages, sleep between pages). Alternative: SerpAPI (§3.3) or alert emails (§7). |
| **AllJobs** and **Techit** (AllJobs' tech site) | Largest Israeli board | Bot protection: PerimeterX and Radware. Scraper vendors need Israeli residential proxies. | **Do not scrape.** Reach it through SerpAPI Google Jobs or alert emails. |
| **JobMaster, JobNet, JobKarov** | General Israeli boards | ❔ No API or feed found; only paid Apify actors | Through Google Jobs or alert emails. |
| **GotFriends** (SQLink group), **Ethosia**, **Nisha**, **SQLink** | Tech placement agencies | ❔ No API found | Many junior-tagged roles, but often anonymous ("לחברת הייטק מובילה"), which hurts dedupe and company matching. Low priority. |
| **Goozali** jobs table | About 4,000 roles, about 900 companies, min-experience field | ❔ Embedded table; access method not confirmed | Use its **Telegram channels** (§4.1). Its company list could feed `scripts/sync_companies.py`. |
| **Junio** (junio.co.il) | Israel's first junior-only tech job board (since 2022) | ❔ | Check the site manually. If it exposes a feed or JSON, it is a strong candidate. |
| **Jobify360** (jobify360.co.il) | Aggregator: claims 90k+ listings and about 3,000 new a day | ❔ No API. Re-aggregates other boards (job-id suffixes look like source tags). | Mostly duplicates. Skip. |
| **Expoint** (expoint.co) | Big-tech jobs in Israel, filter by title and location (`?location=israel&title=junior`) | ❔ | Check manually. Probably duplicates of the Workday, Eightfold and Amazon sources. |
| **NBN Job Board** (nbn.org.il/jobboard) | English-language jobs in Israel (Nefesh B'Nefesh), hi-tech and programming categories | 🟡 WordPress REST route `/jobboard/wp-json/wp/v2/job-listings` exists (listing URLs appear in the search index). Supports `per_page≤100`, `page`, `search`, `after`. | Easy (about 30 lines), but mostly mid/senior roles. Low–medium value. |
| **Secret Tel Aviv Jobs** | English tech board | Fed by Greenhouse and Comeet integrations | Mostly copies of company boards. Use it to **find companies**, not as a source. |
| **John Bryce Jobs** (jobs.johnbryce.co.il) | Training-to-hire and no-experience roles (for example COBOL bootcamp → job) | ❔ Also posts on Drushim | Covered once Drushim or Google Jobs is in. |
| **jobiz.gov.il** (government) | Government jobs and tenders | ❔ No API or data.gov.il dataset found | Government software roles found mostly ask for 2+ years. Low. |
| **Elbit, Rafael, IAI** | Large graduate and student hirers | ❔ Career platforms not identified | Check each careers site for an ATS. They already reach us via LinkedIn and Drushim. |
| **Technion and other alumni job pages** | Junior R&D listings | ❔ Public pages | Manual or low priority. |

---

## 6. Tier 4: more ATS types for `companies.yaml`

Every ATS type added lets `scripts/sync_companies.py` turn more companies into boards with full descriptions. **Measure before building.** Extend `sync_companies.py --scan-careers` to label each `careersUrl` (host and page HTML) with these ATS signatures and print counts. Then build only the types used by at least ~10 Israeli companies.

| ATS | Public endpoint (no auth) | Status | Notes |
|---|---|---|---|
| **Workable** | `GET https://apply.workable.com/api/v1/widget/accounts/{slug}` (same payload as `www.workable.com/api/accounts/{slug}`); `?details=true` adds `description` / `full_description` | 🟡 | Common at Israeli startups. No pagination; `locations[]` are structured. A company may turn the widget off, in which case it returns 0 jobs. |
| **Breezy HR** | `GET https://{slug}.breezy.hr/json` | 🟡 | Tech Map lists 4 Israeli companies with `breezyId`. |
| **BambooHR** | `GET https://{slug}.bamboohr.com/careers/list` (JSON) | 🟡 | Path from memory and third-party tools; check it. |
| **Recruitee** | `GET https://{slug}.recruitee.com/api/offers/` | 🟡 | Mostly EU companies. |
| **Teamtailor** / **Personio** | Teamtailor RSS; `https://{slug}.jobs.personio.de/xml` | 🟡 | Mostly EU companies. |
| **Eightfold** | see §4.3 | 🟡 | Microsoft, PayPal… |
| **HiBob (Bob Hiring)** | `POST api.hibob.com/v1/hiring/job-ads/search` | ✅ docs | **Needs the employer's service-user token**, so it cannot be used. |
| **Oracle Recruiting Cloud, SuccessFactors, Taleo, iCIMS** | Per-company, inconsistent | ❔ | Only for a specific large employer worth the effort. |

---

## 7. Other channels

### 7.1 Job-alert emails, read from your own mailbox
LinkedIn, Drushim, AllJobs, Indeed and Glassdoor all email saved-search alerts. A collector could read a dedicated label or folder over **IMAP** (app password in `.env`) or the Gmail API, pull job links and titles from each sender's template, and hand them to dedupe and the detail fetch.
- **Pros:** covers AllJobs and Drushim without scraping, and the alerts use the sites' own filters (e.g. "ללא ניסיון").
- **Cons:** one parser per email template, and the templates change.
- Effort: medium.

### 7.2 Remote and global boards (low junior yield)
| Source | Access | Status | Notes |
|---|---|---|---|
| **The Muse** | `GET https://www.themuse.com/api/public/jobs?page=N&level=Entry%20Level&category=Software%20Engineering&location=…` (key optional: 500 → 3,600 requests/hour) | 🟡 | Has an **Entry Level** filter and carries Israeli postings: Augury Haifa (junior IT), Cadence Haifa, Applied Materials Rehovot. Also `Flexible / Remote`. Worth a small collector. |
| **Working Nomads** | `GET https://www.workingnomads.com/api/exposed_jobs/` | 🟡 | Remote only, no key, no pagination. Field names differ between third-party descriptions, so record a fixture. |
| **Hacker News "Who is hiring?"** | Algolia `search_by_date?tags=story,author_whoishiring` → thread id → `items/{id}` (or Firebase `item/{id}.json`) | 🟡 | Monthly thread. Comments are free text ("Company \| Role \| Location \| REMOTE"); keep only those mentioning Israel, Tel Aviv, EMEA or worldwide. Few junior roles. |
| **Python.org Jobs** | RSS (offered on python.org/jobs; exact path not confirmed) | 🟡 | Python-specific. Low volume. |
| AI-specific boards (ai-jobs.net RSS, others) | RSS / small APIs | 🟡 | Mostly senior, low volume. Skip for now. |
| Jobgether | ❔ no API | | Lists about 3,600 "remote in Israel" roles; mostly re-aggregated. Skip. |

### 7.3 Paid or keyed aggregators (optional)
| Service | What | Notes |
|---|---|---|
| **Apify actors** for Israeli boards | AllJobs, Drushim, JobMaster, JobNet, GotFriends, Ethosia ("Israeli Job Boards Scraper" covers all six) | About $1–3 per 1,000 jobs. At $N$ jobs a day and price $p$ per 1,000, the monthly cost is $N \cdot 30 \cdot p / 1000$; for example $N=500,\ p=2 \Rightarrow \$30$. The vendor handles the bot protection. |
| **JSearch** (OpenWeb Ninja / RapidAPI) | Google for Jobs data | Small free tier; Israel support not confirmed. |
| **Jooble** API | `POST https://jooble.org/api/{key}` with `{keywords, location}` | Free key on request. il.jooble.org exists, but Israel coverage through the API is not confirmed. |
| **TheirStack / Fantastic.jobs** | Commercial job APIs built from ATS data | Paid. Only if a budget appears. |

---

## 8. Not recommended

| Source | Why not |
|---|---|
| Custom scrapers for **AllJobs / Techit** | Bot protection (PerimeterX, Radware); vendors need residential proxies. Use Google Jobs or email alerts. |
| **LinkedIn** custom scraping | Project rule: JobSpy only. |
| **Glassdoor** | No Israel search in JobSpy (already noted in `config.yaml`). |
| **Wellfound (AngelList), Otta / Welcome to the Jungle, Built In** | No public API, strong anti-bot measures, little Israel coverage. |
| **Careerjet** | The official client lists 68 locales and **none is Israel**. Also needs an affiliate id, the user's IP and user agent. |
| **Adzuna** | No Israel country endpoint. |
| **Indeed Publisher API** | Closed; JobSpy covers Indeed IL. |
| **SimplifyJobs New-Grad / Internship repos** | US, Canada and Remote only. |
| **HiBob, Consider (VC boards) APIs** | Need customer credentials. |
| **Facebook / WhatsApp groups** | No API; scraping them breaks their terms. Telegram's public preview (§4.1) is the exception. |

---

## 9. Suggested order of work

| Phase | Work | Size | Acceptance check |
|---|---|---|---|
| A | Add 4 Workday tenants and the Aleph Getro board | config | `python run_agent.py --check-companies` shows Israel jobs for each |
| A | SerpAPI: separate `queries` list (≤ 8, Hebrew included), relative-date parsing, enable it | small | `python run_agent.py --sources serpapi --no-llm` returns AllJobs/Drushim-hosted jobs; the source-health error is empty |
| B | `telegram` collector (Goozali channels) | small | Fixture-based parser test; a live run returns the channel's recent posts with links |
| B | `jobicy` in `remote_boards.py` | small | Fixture test; live run with the `geo` slugs from `?get=locations` |
| B | `amazon` collector; `eightfold` ATS type (Microsoft) | small–medium | Israel postings with descriptions; no 429 in a full run |
| C | `sync_companies.py --scan-careers` ATS detection → counts per ATS | small | A table of Israeli companies per ATS |
| C | Workable (and others above the ~10-company threshold) | medium | `check_boards.py` lists live slugs with Israel jobs |
| D | Pick the route for Drushim/AllJobs: Drushim internal API, alert emails, or a paid Apify actor | medium | The decision recorded in `docs/ARCHITECTURE.md` |

For every new source, follow the project rules:
- The collector never raises and returns a `CollectorResult`.
- It uses the shared `requests.Session` and reads its settings from `config.yaml`.
- It has a recorded fixture and a parser test (`offline-testing` skill).
- It gets an entry in `collectors/__init__.py → _SOURCES`.
- Its verified endpoint goes into `job-sources/references/endpoints.md`.

---

## 10. Sources consulted (2026-10-15)

Official docs and code
- Jobicy API: https://github.com/Jobicy/remote-jobs-api
- Careerjet Python client (locale list): https://github.com/careerjet/careerjet-api-client-python
- HiBob Hiring API (job ads): https://apidocs.hibob.com/reference/job-ads , https://apidocs.hibob.com/docs/explore-hiring-api
- Eightfold PCSX in third-party code: https://github.com/career-ops-hq/career-ops/pull/4297 , https://github.com/oconnesp/trackeir/pull/11
- Israeli Tech Map data: https://github.com/mluggy/techmap (ODbL)

Israeli boards and channels
- Goozali: https://goozali.com/ , https://en.goozali.com/ ; Telegram: https://t.me/hitechjobsjunior , https://t.me/hitechjobsisrael
- Globes on junior jobs and Goozali's Telegram groups: https://www.globes.co.il/news/article.aspx?did=1001512461 , https://en.globes.co.il/en/article-jobs-scarce-for-juniors-in-israels-tech-industry-1001512559
- Junio: https://junio.co.il/
- Jobify360: https://jobify360.co.il/llms.txt
- NBN Job Board: https://www.nbn.org.il/jobboard/job-category/hi-tech/ , https://www.nbn.org.il/jobboard/wp-json/wp/v2/job-listings/100038766
- Secret Tel Aviv / Greenhouse integration: https://integrations.greenhouse.com/partners/secret-tel-aviv
- Techit (AllJobs) junior data: https://www.calcalist.co.il/calcalistech/article/s1cxkzgpr
- Drushim scraper listings (internal JSON API, `ResultList`, `geoLexId`): https://apify.com/memo23/drushim-scraper , https://apify.com/bovi/drushim-co-il-scraper
- AllJobs bot protection, multi-board actor: https://apify.com/devanshlive/alljobs-scraper , https://apify.com/amrameng/israeli-job-boards-scraper
- John Bryce Jobs: https://jobs.johnbryce.co.il/
- Civil service applications: https://www.gov.il/he/service/apply_for_a_civil_service_job_via_tenders_system

Companies, ATS and VC boards
- Workday postings in Israel: https://dell.wd1.myworkdayjobs.com/en-US/External/job/Herzliya-Israel/Software-Senior-Engineer_R282830 , https://workday.wd5.myworkdayjobs.com/en-US/Workday/job/Israel-Tel-Aviv/LLM-Software-Engineer_JR-0102898 , https://generalmotors.wd5.myworkdayjobs.com/en-US/Careers_GM/job/Herzliya-Tel-Aviv-District-Israel/Software-Engineer_JR-202600532 , https://forcepoint.wd1.myworkdayjobs.com/external-careers/job/Israel---Tel-Aviv---Ha-Shlosha---Office/Software-Engineer--Student_JR467299-1
- Workday page-size gotcha: https://dev.to/juancarlosguti/ask-workdays-public-api-for-100-jobs-and-you-get-zero-with-no-error-54b2
- Microsoft / Nvidia hiring in Israel: https://www.calcalistech.com/ctechnews/article/cdzdrd6pl
- Aleph jobs: https://jobs.aleph.vc/ ; Israel VC Forum: https://israelvcforum.getro.com/companies
- Workable widget endpoint: https://dev.to/zsevic/integration-with-workable-public-jobs-api-3nk4 , https://100hires.com/workable-api.html
- Breezy feed: https://jobspipe.dev/sources/breezy
- Amazon `search.json`: https://apify.com/automation-lab/amazon-jobs-scraper
- Consider API (needs a key): https://blog.consider.com/posts/introducing-considers-api

Remote and global
- Jobicy Israel region: https://jobicy.com/job-region/israel
- Working Nomads feed: https://apify.com/automation-lab/working-nomads-jobs-scraper
- The Muse API: https://apis.apievangelist.com/store/themuse-jobs-api/ ; Israeli postings on The Muse: https://www.themuse.com/jobs/augury/junior-it-support-technician , https://www.themuse.com/jobs/cadence/software-engineer-ii-ec3310
- Python.org jobs: https://www.python.org/jobs/
- SimplifyJobs New-Grad scope: https://gh.nn.ci/SimplifyJobs/New-Grad-Positions
- SerpApi free tier (2026): https://costbench.com/software/web-scraping/serpapi/free-plan/
- Jooble API: https://in.jooble.org/api/about

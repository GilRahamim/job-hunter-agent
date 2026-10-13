# Location patterns (tested)

These patterns and functions pass all 22 cases at the bottom of this file. Copy them into `filters.py` and the cases into `tests/test_filters.py`. When you add a city or rule, add a test case first.

```python
import re

ISRAEL_EN = (
    r"\bisrael\b|tel[\s-]?aviv|\btlv\b|jaffa|herzli?ya|haifa|jerusalem|petah?[\s-]?tikva|petach|"
    r"ramat[\s-]?gan|givatayim|bnei[\s-]?brak|ra'?anana|netanya|rehovot|ness?[\s-]?ziona|"
    r"rishon[\s-]?le[\s-]?zion|holon|bat[\s-]?yam|or[\s-]?yehuda|airport[\s-]?city|yokneam|"
    r"kiryat[\s-]?gat|be'?er[\s-]?sheva|beersheba|caesarea|hod[\s-]?hasharon|kfar[\s-]?saba|"
    r"modi'?in|rosh[\s-]?ha'?ayin|nazareth|ashdod|ashkelon|\blod\b|ramla"
)
ISRAEL_HE = (
    r"ישראל|תל[\s-]?אביב|יפו|הרצליה|חיפה|ירושלים|פתח[\s-]?תקו?וה|רמת[\s-]?גן|גבעתיים|בני[\s-]?ברק|"
    r"רעננה|נתניה|רחובות|נס[\s-]?ציונה|ראשון[\s-]?לציון|חולון|בת[\s-]?ים|אור[\s-]?יהודה|יקנעם|"
    r"קרי?ית[\s-]?גת|באר[\s-]?שבע|קיסריה|הוד[\s-]?השרון|כפר[\s-]?סבא|מודיעין|ראש[\s-]?העין|"
    r"אשדוד|אשקלון|לוד|רמלה|נצרת"
)
IL_CODE = r"(?:^|[,(\s])IL(?:$|[,)\s])"          # case-SENSITIVE: "Petah Tikva, IL"
REMOTE_WORD = r"\bremote\b|work from home|\bwfh\b|anywhere|worldwide|מהבית|מרחוק"
OK_REGION = r"worldwide|anywhere|global|emea|europe|israel|middle east|international"   # from config
EXCLUDE_REGION = (
    r"\b(us|usa|u\.s\.a?|united states|canada|latam|latin america|uk|united kingdom|apac|"
    r"australia|india|brazil|mexico|philippines|north america|americas)\b|\b(est|pst|cst|mst|et|pt)\b"
)

_isr = re.compile(ISRAEL_EN + "|" + ISRAEL_HE, re.I)
_il = re.compile(IL_CODE)
_remote = re.compile(REMOTE_WORD, re.I)
_ok = re.compile(OK_REGION, re.I)
_ex = re.compile(EXCLUDE_REGION, re.I)


def is_israel(text: str) -> bool:
    return bool(_isr.search(text) or _il.search(text))


def remote_ok(location: str, region: str = "", is_remote: bool = False) -> bool:
    text = f"{location} {region}"
    if not (is_remote or _remote.search(text)):
        return False
    if is_israel(text) or _ok.search(text):   # an explicit OK wins: "US or EMEA" is fine
        return True
    if _ex.search(text):
        return False
    # bare "Remote" with no other location words and no region → assume open
    return region.strip() == "" and not re.search(r"\w", _remote.sub("", location))


def location_ok(location: str, region: str = "", is_remote: bool = False) -> bool:
    return is_israel(location) or remote_ok(location, region, is_remote)
```

Build `_ok` from `config.filters.remote_regions_ok` rather than the constant, so the owner can change it.

## Test cases — `(location, remote_region, is_remote, expected)`

```python
CASES = [
    ("Tel Aviv-Yafo, Tel Aviv District, Israel", "", False, True),
    ("Remote - Worldwide", "", False, True),
    ("Remote (US only)", "", False, False),
    ("Remote, EMEA", "", False, True),
    ("New York, NY", "", False, False),
    ("קריית גת", "", False, True),
    ("", "Anywhere in the World", True, True),
    ("", "USA Only", True, False),
    ("רחובות, M, Israel", "", False, True),
    ("Herzliya", "", False, True),
    ("Remote", "", False, True),
    ("Remote", "USA", True, False),
    ("Remote", "Europe", True, True),
    ("Remote - US or EMEA", "", False, True),
    ("Petah Tikva, IL", "", False, True),
    ("Illinois", "", False, False),
    ("Lodz, Poland", "", False, False),
    ("Remote, EST timezone", "", False, False),
    ("Testing City", "", False, False),
    ("Remote", "United Kingdom, United States", True, False),
    ("London, UK", "", False, False),
    ("Remote - Canada", "", True, False),
]
```

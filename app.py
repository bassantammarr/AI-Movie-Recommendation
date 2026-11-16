import html
import json
import re
import urllib.parse

import requests
import streamlit as st
from groq import Groq

st.set_page_config(page_title="CineMatch AI", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

ACCENT = "#E21221"
TOP_N, MORE_N = 3, 6  

PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]
NON_CHAT = ("whisper", "tts", "guard", "playai", "orpheus", "prompt-guard", "distil")

MOODS = {
    "Thoughtful": {"color": "#2f63a0", "icon": ":material/lightbulb:", "rule": "deep themes, slower pace, ideas that linger"},
    "Cozy": {"color": "#a8701a", "icon": ":material/local_cafe:", "rule": "warm, comforting, feel-good, low stakes"},
    "Thrilled": {"color": "#c2410c", "icon": ":material/bolt:", "rule": "fast-paced, high energy, suspenseful"},
    "Heartbroken": {"color": "#9d3c72", "icon": ":material/heart_broken:", "rule": "emotional and cathartic, but ultimately hopeful"},
    "Curious": {"color": "#2f7a52", "icon": ":material/explore:", "rule": "mind-expanding: mysteries, big ideas, discovery"},
    "Surprise me": {"color": "#474747", "icon": ":material/shuffle:", "rule": "anything goes: varied, unexpected but acclaimed picks"},
}
GENRES = ["Drama", "Comedy", "Thriller", "Romance", "Sci-Fi", "Animation", "Documentary",
          "Action", "Horror", "Fantasy", "Mystery", "Crime"]
LANGUAGES = ["Any", "English", "Arabic", "French", "Spanish", "Korean", "Japanese", "Hindi", "Italian", "German"]
ERAS = ["Any era", "Classics (pre-1980)", "80s & 90s", "2000s", "2010s", "2020s"]
ERA_RANGES = {
    "Classics (pre-1980)": (1900, 1979),
    "80s & 90s": (1980, 1999),
    "2000s": (2000, 2009),
    "2010s": (2010, 2019),
    "2020s": (2020, 2100),
}

LANG_QIDS = {
    "English": ["Q1860"],
    "Arabic": ["Q13955", "Q29919", "Q56426", "Q56240", "Q56499"],  # + Egyptian, Moroccan, Tunisian, Algerian
    "French": ["Q150"],
    "Spanish": ["Q1321"],
    "Korean": ["Q9176"],
    "Japanese": ["Q5287"],
    "Hindi": ["Q1568"],
    "Italian": ["Q652"],
    "German": ["Q188"],
}

LANG_COUNTRIES = {
    "Arabic": ["Q79", "Q851", "Q822", "Q858", "Q810", "Q796", "Q1028", "Q262", "Q948", "Q878",
               "Q817", "Q846", "Q398", "Q842", "Q805", "Q1016", "Q1049", "Q219060"],
    "French": ["Q142", "Q31", "Q39"],
    "Spanish": ["Q29", "Q96", "Q414", "Q739", "Q298", "Q241", "Q419", "Q717"],
    "Korean": ["Q884", "Q423"],
    "Japanese": ["Q17"],
    "Hindi": ["Q668"],
    "Italian": ["Q38"],
    "German": ["Q183", "Q40", "Q39", "Q713750", "Q16957"],
}
FILM_TYPES = ["Q11424", "Q202866", "Q29168811"]  
EXTRA_CANDIDATES = 3  

POSTER_COLORS = ["#1d3a4a", "#4a3320", "#2b2552", "#24402f", "#1c2d4f", "#3a2440", "#3d2a2a", "#2f3a3f", "#42381c"]
CHAT_SUGGESTIONS = ["Compare all three", "Which is shortest?", "Same mood, but lighter", "Anything not in English?"]


# --------------------------------------------------------------------------- styles
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap');

.stApp {{ background:#141414; color:#ffffff; font-family: Inter, system-ui, sans-serif; }}
.stApp p, .stApp label, .stApp input, .stApp button {{ font-family: Inter, system-ui, sans-serif; }}
header[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display:none; }}
.block-container {{ max-width:100%; padding: 1rem 4vw 3rem; }}

.bebas {{ font-family:'Bebas Neue', Impact, sans-serif; font-weight:400; letter-spacing:1px; line-height:.9; }}
.logo {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:40px; letter-spacing:1px; line-height:1; color:{ACCENT}; }}
.muted {{ color:#8c8c8c; font-size:13px; }}

/* buttons */
.stApp button[data-testid="stBaseButton-primary"] {{
  background:{ACCENT}; border:0; color:#fff; font-weight:700; border-radius:4px; min-height:46px; font-size:17px;
}}
.stApp button[data-testid="stBaseButton-primary"]:hover {{ background:#b80f1b; color:#fff; }}
.stApp button[data-testid="stBaseButton-secondary"] {{
  background:rgba(109,109,110,.7); color:#fff; border:0; border-radius:4px; font-weight:700; min-height:44px;
}}
.stApp button[data-testid="stBaseButton-secondary"]:hover {{ background:rgba(109,109,110,.45); color:#fff; }}
.stApp button[data-testid="stBaseButton-tertiary"] {{ color:#d6d6d6; font-weight:600; min-height:44px; }}
.stApp button[data-testid="stBaseButton-tertiary"]:hover {{ color:#fff; }}
.stApp a[data-testid^="stBaseLinkButton"] {{ border-radius:4px; font-weight:700; min-height:44px; }}
[class*="st-key-watch"] a {{ background:#ffffff !important; color:#141414 !important; border:0 !important; }}
[class*="st-key-watch"] a:hover {{ background:#e5e5e5 !important; }}
.stApp [class*="st-key-round_"] button {{
  width:50px; height:50px; min-height:50px; border-radius:50%; border:2px solid rgba(255,255,255,.7);
  background:rgba(20,20,20,.5); padding:0;
}}
.stApp [class*="st-key-round_"] button:hover {{ border-color:#fff; background:rgba(60,60,60,.7); }}

/* pills */
.stApp button[data-testid="stBaseButton-pills"] {{
  border-radius:999px; border:1px solid #5a5a5a; background:transparent; color:#e6e6e6;
  min-height:44px; padding:0 20px; font-weight:600;
}}
.stApp button[data-testid="stBaseButton-pillsActive"] {{
  border-radius:999px; border:1px solid #fff; background:#fff; color:#141414; min-height:44px; padding:0 20px; font-weight:600;
}}
.st-key-genre_pills div:has(> button[data-testid^="stBaseButton-pills"]) {{ justify-content:center; }}

/* form labels */
.st-key-filters label p, .st-key-header label p {{ font-size:12px; letter-spacing:1px; font-weight:600; color:#b3b3b3; text-transform:uppercase; }}

/* mood tiles */
[class*="st-key-mood_"] {{ display:flex; justify-content:center; }}
.stApp [class*="st-key-mood_"] button {{
  width:150px; height:150px; border-radius:6px; border:0; color:#fff; opacity:.85;
  outline:4px solid transparent; transition: transform .15s ease, opacity .15s ease;
}}
.stApp [class*="st-key-mood_"] button:hover {{ opacity:1; transform:scale(1.04); color:#fff; }}
.stApp [class*="st-key-mood_"] button span[data-has-shortcut] {{ display:flex; flex-direction:column; align-items:center; gap:14px; }}
[class*="st-key-mood_"] button span[data-testid="stIconMaterial"] {{ font-size:60px; }}
[class*="st-key-mood_"] button p {{ font-size:17px; font-weight:600; }}

/* hero */
.st-key-hero {{
  position:relative; min-height:600px; justify-content:flex-end;
  margin:0 -4vw; width:calc(100% + 8vw) !important; max-width:none !important; box-sizing:border-box; padding:110px 4vw 150px; overflow:hidden;
}}
.hero-art {{
  position:absolute; right:3vw; top:40px; max-width:55%; text-align:right; pointer-events:none;
  font-family:'Bebas Neue', Impact, sans-serif; font-size:clamp(120px,16vw,260px); line-height:.82;
  color:transparent; -webkit-text-stroke:2px rgba(255,255,255,.16); overflow:hidden;
}}
.kicker {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
.kicker .cm {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:24px; line-height:1; color:{ACCENT}; }}
.kicker span:last-child {{ font-size:13px; letter-spacing:3px; font-weight:600; color:#d6d6d6; }}
.hero-title {{ margin:0; font-family:'Bebas Neue', Impact, sans-serif; font-weight:400;
  font-size:clamp(60px,7.5vw,112px); line-height:.88; letter-spacing:1px; max-width:760px; color:#fff; }}
.hero-original {{ font-size:22px; color:#d6d6d6; margin-top:6px; unicode-bidi:plaintext; }}
.meta-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:14px; margin-top:20px; font-size:15px; color:#d6d6d6; }}
.match {{ color:#46d369; font-weight:700; }}
.badge {{ display:inline-flex; align-items:center; gap:4px; border:1px solid rgba(255,255,255,.45); border-radius:3px; padding:2px 7px; font-size:12px; }}
.badge.warn {{ border-color:#f5c26b; color:#f5c26b; }}
.star {{ color:#f5c518; }}
.hero-tagline {{ margin:18px 0 0; font-size:22px; font-style:italic; font-weight:500; max-width:640px; }}
.hero-why {{ margin:10px 0 0; font-size:17px; line-height:1.55; color:#d6d6d6; max-width:600px; }}

/* vibe bar */
.st-key-vibe_bar {{
  position:relative; z-index:3; margin-top:-110px; background:rgba(35,35,35,.92);
  border:1px solid #3a3a3a; border-radius:6px; padding:12px 18px; height:auto !important; flex:0 0 auto !important;
}}
.vibe-chips {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; }}
.vibe-chips .label {{ font-size:12px; letter-spacing:2px; font-weight:700; color:#b3b3b3; margin-right:4px; }}
.vibe-chips .chip {{ padding:7px 14px; border-radius:999px; background:#3a3a3a; font-size:13px; }}
.vibe-chips .chip.on {{ background:#fff; color:#141414; font-weight:600; }}

/* rows */
.row-title {{ margin:36px 0 14px; font-size:22px; font-weight:700; color:#fff; }}
.top-item {{ display:flex; align-items:flex-start; }}
.top-rank {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:250px; line-height:.82; color:#141414;
  -webkit-text-stroke:4px #6b6b6b; margin-right:-24px; margin-top:16px; }}
.poster {{ position:relative; z-index:1; width:200px; height:290px; box-sizing:border-box; padding:14px; border-radius:4px;
  display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 10px 30px rgba(0,0,0,.5);
  transition: transform .2s ease; }}
.poster:hover {{ transform:scale(1.03); }}
.poster-top {{ display:flex; align-items:center; justify-content:space-between; }}
.poster-top .cm {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:20px; line-height:1; color:{ACCENT}; }}
.poster-top .rate {{ font-size:12px; font-weight:700; background:rgba(0,0,0,.6); padding:3px 7px; border-radius:3px; }}
.poster-title {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:36px; line-height:.9; color:#fff; overflow-wrap:anywhere; }}
.poster-meta {{ font-size:12px; color:#e6e6e6; margin-top:8px; }}
.top-tagline {{ font-size:13px; line-height:1.4; font-style:italic; color:#b3b3b3; margin:10px 0 2px; }}

.stApp [class*="st-key-more_"] button {{
  width:100%; height:152px; border-radius:4px; border:0; color:#fff; padding:14px 16px;
  justify-content:flex-start; align-items:flex-end; text-align:left; transition: transform .2s ease;
}}
.stApp [class*="st-key-more_"] button:hover {{ transform:scale(1.04); color:#fff; }}
.stApp [class*="st-key-more_"] button > div {{ width:100%; justify-content:flex-start; }}
.stApp [class*="st-key-more_"] button p {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:28px; line-height:.95; letter-spacing:1px; }}
.tile-meta {{ font-size:12px; color:#b3b3b3; margin-top:-6px; }}

.mylist {{ display:flex; flex-wrap:wrap; gap:10px; }}
.mylist a {{ padding:8px 14px; border-radius:4px; background:#2a2a2a; color:#fff !important; text-decoration:none; font-size:14px; }}
.mylist a:hover {{ background:#3a3a3a; }}

/* ask box */
.st-key-ask_box {{ max-width:920px; background:#1f1f1f; border:1px solid #333; border-radius:8px; padding:24px 26px; margin-top:44px; }}
.ask-title {{ font-size:20px; font-weight:700; }}
.ask-sub {{ margin:4px 0 4px; font-size:14px; color:#b3b3b3; }}
.stApp [class*="st-key-chip_"] button {{ min-height:36px; border-radius:999px; border:1px solid #4d4d4d; background:transparent; color:#e6e6e6; font-weight:500; padding:0 14px; }}
.stApp [class*="st-key-chip_"] button:hover {{ border-color:#fff; color:#fff; background:transparent; }}
.st-key-ask_box [data-testid="stForm"] {{ border:0; padding:0; }}
[data-testid="stChatMessage"] {{ background:#181818; border:1px solid #2a2a2a; border-radius:8px; }}

/* detail dialog */
div[role="dialog"] {{ background:#181818; }}
.d-banner {{ position:relative; border-radius:6px; padding:28px 32px 28px; min-height:240px; display:flex; flex-direction:column;
  justify-content:flex-end; overflow:hidden; }}
.d-banner .hero-art {{ top:10px; font-size:180px; }}
.d-title {{ margin:0; font-family:'Bebas Neue', Impact, sans-serif; font-weight:400; font-size:72px; line-height:.88; color:#fff; position:relative; }}
.reason {{ display:flex; gap:14px; margin:14px 0; }}
.reason .bar {{ width:4px; flex:0 0 auto; border-radius:2px; background:{ACCENT}; }}
.reason .bar.grey {{ background:#5a5a5a; }}
.reason h4 {{ margin:0 0 4px; font-size:13px; letter-spacing:1.5px; color:#b3b3b3; font-weight:700; }}
.reason p {{ margin:0; font-size:16px; line-height:1.55; color:#e6e6e6; }}
.facts {{ font-size:14px; line-height:1.5; }}
.facts div {{ margin-bottom:10px; }}
.facts span {{ color:#8c8c8c; }}
.facts a {{ color:#54b9c5; }}
.like-card {{ border-radius:6px; overflow:hidden; background:#2a2a2a; }}
.like-card .top {{ height:110px; display:flex; align-items:flex-end; padding:12px; box-sizing:border-box;
  font-family:'Bebas Neue', Impact, sans-serif; font-size:26px; line-height:.9; color:#fff; }}
.like-card .body {{ padding:12px 14px; font-size:14px; line-height:1.5; color:#d6d6d6; }}
.like-card .body b {{ display:block; font-size:13px; color:#b3b3b3; font-weight:500; margin-bottom:4px; }}
footer.cm-footer {{ padding:48px 0 8px; font-size:13px; color:#8c8c8c; }}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- data helpers
def secret_api_key():
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def available_models(api_key):
    """Chat models this key can use, preferred ones first."""
    ids = [m.id for m in Groq(api_key=api_key).models.list().data if getattr(m, "active", True)]
    chat = [i for i in ids if not any(x in i.lower() for x in NON_CHAT)]
    preferred = [m for m in PREFERRED_MODELS if m in chat]
    return preferred + sorted(m for m in chat if m not in preferred)


def parse_json(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("The model didn't return valid JSON. Try again or pick another model.")
        return json.loads(match.group(0))


def wanted_count(profile):
    strict = profile["language"] != "Any" or profile["era"] in ERA_RANGES
    return profile["count"] + (EXTRA_CANDIDATES if strict else 0)


def build_prompt(profile, exclude, pool=None, liked=None):
    genres = ", ".join(profile["genres"]) if profile["genres"] else "Any"
    exclude_txt = ", ".join(exclude) if exclude else "none"
    lang = profile["language"]
    hard_rules = []
    if lang != "Any":
        hard_rules.append(
            f"- LANGUAGE IS MANDATORY: every movie's ORIGINAL spoken language must be {lang}, i.e. films produced "
            f"in {lang}-language cinema. English-language/Hollywood films are NOT allowed, even if dubbed or "
            f"subtitled in {lang}. If few films fit every wish, keep the language and relax the genre instead."
        )
    if profile["era"] in ERA_RANGES:
        lo, hi = ERA_RANGES[profile["era"]]
        hard_rules.append(f"- ERA IS MANDATORY: every movie must be first released between {lo} and {min(hi, 2026)}.")
    if pool:
        hard_rules.append(
            "- PICK ONLY FROM THE CANDIDATE LIST below (real films from Wikidata). Copy the title and year "
            "exactly as written. Never invent a film or pick one that is not on the list."
        )
    hard_rules_txt = "\n".join(hard_rules)
    pool_txt = ""
    if pool:
        lines = [f"- {f['title']} ({f['year']})" + (f" [{f['genres']}]" if f["genres"] else "") for f in pool]
        pool_txt = "\nCandidate list (most famous first):\n" + "\n".join(lines) + "\n"
    popularity = (
        "well-known, acclaimed or popular within that language's cinema"
        if lang not in ("Any", "English")
        else "well-known, mainstream (IMDb ~7+)"
    )
    liked_txt = f"- The user liked these earlier picks, so lean toward films in a similar spirit: {', '.join(liked)}\n" if liked else ""
    return f"""You are an explainable AI movie recommendation system.

User profile:
- Age: {profile['age']}
- Mood: {profile['mood']} ({MOODS[profile['mood']]['rule']})
- Preferred genres: {genres}
- Language: {profile['language']}
- Era: {profile['era']}
- Extra wishes: {profile['notes'] or 'none'}

Rules:
- Recommend ONLY real movies that are {popularity}.
{hard_rules_txt}
- Match the mood and the genres. Order the list from best match to weakest match.
- Content must be age-appropriate for the user's age.
- Do NOT recommend any of these already-suggested titles: {exclude_txt}
{liked_txt}- Write all text fields in English.
{pool_txt}
Return ONLY valid JSON, no extra text, with exactly {wanted_count(profile)} movies:
{{"movies": [{{
  "title": "the film's common English title",
  "original_title": "title in its original language/script",
  "year": 2010,
  "genres": ["Genre", "Genre"],
  "runtime": "2h 28m",
  "rating": 8.8,
  "tagline": "a short, catchy one-line hook (no spoilers)",
  "mood_match": "one or two sentences on why it fits the mood",
  "genre_match": "one sentence on why it fits the genres/wishes",
  "why_you": "one sentence on why it suits this particular viewer (their age and wishes)",
  "heads_up": "one honest caveat: tone, pacing, intensity or content to expect"
}}]}}"""


def fetch_movies(client, model, profile, exclude, pool=None, liked=None):
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": build_prompt(profile, exclude, pool, liked)}],
        temperature=0.8,
    )
    try:
        resp = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
    except Exception as ex:
        
        if "response_format" not in str(ex) and "json" not in str(ex).lower():
            raise
        resp = client.chat.completions.create(**kwargs)
    data = parse_json(resp.choices[0].message.content)
    movies = data.get("movies", [])
    return [m for m in movies if isinstance(m, dict) and m.get("title")]


WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
HTTP_HEADERS = {
    "User-Agent": "CineMatchAI/1.0 (Streamlit movie recommender)",
    "Accept": "application/sparql-results+json",
}


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def wikidata_lookup(title_variants):
    """Find films on Wikidata by exact title (any of several spellings), in one request.
    Returns {index: {qid: info}}."""
    values = " ".join(
        f"({i} {json.dumps(t)}@{lang})"
        for i, variants in enumerate(title_variants)
        for t in variants
        for lang in ("en", "mul")
    )
    query = f"""SELECT ?i ?item ?date ?dur ?imdb ?links ?langLabel WHERE {{
  VALUES (?i ?label) {{ {values} }}
  {{ ?item rdfs:label ?label }} UNION {{ ?item skos:altLabel ?label }}
  ?item wdt:P57 [] ; wdt:P577 ?date ; wikibase:sitelinks ?links .
  OPTIONAL {{ ?item wdt:P2047 ?dur }}
  OPTIONAL {{ ?item wdt:P345 ?imdb }}
  OPTIONAL {{ ?item wdt:P364 ?lang . ?lang rdfs:label ?langLabel FILTER(lang(?langLabel) = "en") }}
}}"""
    r = requests.post(WIKIDATA_SPARQL, data={"query": query}, headers=HTTP_HEADERS, timeout=15)
    r.raise_for_status()
    found = {}
    for b in r.json()["results"]["bindings"]:
        i, qid = int(b["i"]["value"]), b["item"]["value"].rsplit("/", 1)[-1]
        c = found.setdefault(i, {}).setdefault(
            qid,
            {"years": set(), "durations": set(), "languages": set(), "imdb": None,
             "links": int(b["links"]["value"])},
        )
        if "langLabel" in b:
            c["languages"].add(b["langLabel"]["value"])
        c["years"].add(int(b["date"]["value"][:4]))
        if "dur" in b:
            c["durations"].add(round(float(b["dur"]["value"])))
        if b.get("imdb", {}).get("value", "").startswith("tt"):
            c["imdb"] = b["imdb"]["value"]
    return found


def sparql(query, timeout=45):
    for attempt in range(2):  # Wikidata occasionally returns a transient 502/503
        r = requests.post(WIKIDATA_SPARQL, data={"query": query}, headers=HTTP_HEADERS, timeout=timeout)
        if r.status_code < 500:
            break
    r.raise_for_status()
    return r.json()["results"]["bindings"]


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def candidate_pool(language, era_name, limit=400):
    """The best-known real films in a language (and era), so the AI picks from facts, not memory."""
    langs = " ".join("wd:" + q for q in LANG_QIDS[language])
    types = " ".join("wd:" + q for q in FILM_TYPES)
    countries = " ".join("wd:" + q for q in LANG_COUNTRIES.get(language, []))
    country_rule = f"VALUES ?country {{ {countries} }} ?item wdt:P495 ?country ." if countries else ""
    rows = sparql(f"""SELECT DISTINCT ?item ?links WHERE {{
  VALUES ?lang {{ {langs} }} VALUES ?type {{ {types} }}
  ?item wdt:P364 ?lang ; wdt:P31 ?type ; wikibase:sitelinks ?links .
  {country_rule}
}} ORDER BY DESC(?links) LIMIT {limit}""")
    links = {b["item"]["value"].rsplit("/", 1)[-1]: int(b["links"]["value"]) for b in rows}
    if not links:
        return []
    ids = " ".join("wd:" + q for q in links)
    rows = sparql(f"""SELECT ?item ?d ?title ?gl WHERE {{
  VALUES ?item {{ {ids} }}
  ?item wdt:P577 ?d .
  OPTIONAL {{ ?item rdfs:label ?title FILTER(lang(?title) = "en") }}
  OPTIONAL {{ ?item wdt:P136 ?g . ?g rdfs:label ?gl FILTER(lang(?gl) = "en") }}
}}""", timeout=45)
    films = {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        f = films.setdefault(qid, {"years": set(), "genres": set(), "title": None})
        f["years"].add(int(b["d"]["value"][:4]))
        if "title" in b:
            f["title"] = b["title"]["value"]
        if "gl" in b:
            f["genres"].add(b["gl"]["value"].replace(" film", ""))
    lo, hi = ERA_RANGES.get(era_name, (1800, 2200))
    pool = [
        {"title": f["title"], "year": min(f["years"]), "genres": ", ".join(sorted(f["genres"])[:4]),
         "links": links[qid]}
        for qid, f in films.items()
        if f["title"] and lo <= min(f["years"]) <= hi
    ]
    return sorted(pool, key=lambda f: -f["links"])


def get_pool(profile, exclude):
    """Candidate list for non-English languages; None means 'let the AI choose freely'."""
    if profile["language"] in ("Any", "English") or profile["language"] not in LANG_QIDS:
        return None
    try:
        pool = candidate_pool(profile["language"], profile["era"])
    except Exception:
        return None  
    seen = {t.lower() for t in exclude}
    return [f for f in pool if f["title"].lower() not in seen][:200] or None


def title_variants(movie):

    small = {"a", "an", "and", "at", "for", "in", "of", "on", "the", "to", "vs", "vs."}

    def cap_all(t):
        return " ".join(w[:1].upper() + w[1:] for w in t.split(" "))

    def cap_title(t):
        words = t.split(" ")
        return " ".join(
            w if (i and w.lower() in small) else w[:1].upper() + w[1:] for i, w in enumerate(words)
        )

    def cap_keep_vs(t):
        return " ".join(w.lower() if w.lower() in ("vs", "vs.") else w for w in cap_all(t).split(" "))

    out = []
    for t in (movie.get("title"), movie.get("original_title")):
        t = str(t or "").strip()
        if not t:
            continue
        for v in (t, cap_keep_vs(t), cap_title(t), t.replace(".", ""), cap_keep_vs(t).replace(".", ""),
                  t.replace(" vs ", " vs. "), t.replace(" & ", " and "), t.replace(" and ", " & "),
                  t.replace("’", "'"), t.replace("'", "’")):
            if v not in out:
                out.append(v)
    return tuple(out[:14])


def fmt_runtime(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def parse_minutes(text):
    m = re.match(r"\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", str(text or ""))
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    m = re.search(r"\d+", str(text or ""))
    return int(m.group(0)) if m else None


def verify_movies(movies, profile):
   
    try:
        found = wikidata_lookup(tuple(title_variants(m) for m in movies))
    except Exception:
        found = {}
    lang = profile["language"]

    def lang_match(c):
        return lang == "Any" or any(lang.lower() in l.lower() for l in c["languages"])

    for i, movie in enumerate(movies):
        cands = list(found.get(i, {}).values())
        movie["verified"] = False
        if not cands:
            continue
        try:
            ai_year = int(str(movie.get("year"))[:4])
        except ValueError:
            ai_year = None
        near = [c for c in cands if ai_year and abs(min(c["years"]) - ai_year) <= 2]
        pool = near or cands
        pool = [c for c in pool if lang_match(c)] or pool 
        best = max(pool, key=lambda c: c["links"])  
        movie["year"] = min(best["years"])  
        if best["durations"]:
            
            durs = sorted(best["durations"])
            guess = parse_minutes(movie.get("runtime"))
            mins = min(durs, key=lambda d: abs(d - guess)) if guess else durs[len(durs) // 2]
        
            if guess and abs(mins - guess) <= 8:
                mins = guess
            movie["runtime"] = fmt_runtime(mins)
        elif parse_minutes(movie.get("runtime")):
            movie["runtime"] = fmt_runtime(parse_minutes(movie.get("runtime")))
        movie["imdb_id"] = best["imdb"]
        movie["languages"] = sorted(best["languages"])
        movie["lang_ok"] = lang_match(best) if best["languages"] else None
        movie["verified"] = True

    era = ERA_RANGES.get(profile["era"])

    def rank(m):
        """2 = confirmed match, 1 = can't confirm, 0 = confirmed mismatch (dropped)."""
        try:
            year = int(str(m.get("year"))[:4])
        except ValueError:
            year = None
        if era and year and not era[0] <= year <= era[1]:
            return 0
        if lang != "Any":
            if m.get("lang_ok") is False or not m.get("verified"):
                return 0  # wrong language, or a film Wikidata can't find (likely invented)
            if m.get("lang_ok") is None:
                return 1
        return 2 if m.get("verified") else 1

    ranked = sorted(((rank(m), i, m) for i, m in enumerate(movies)), key=lambda x: (-x[0], x[1]))
    return [m for r, _, m in ranked if r > 0][: profile["count"]]


def stream_answer(client, model, question, history, focus=None):
    movies_ctx = json.dumps(
        [{k: m.get(k) for k in ("title", "year", "runtime", "genres", "languages", "tagline", "mood_match")}
         for m in st.session_state.movies],
        ensure_ascii=False,
    )
    p = st.session_state.profile
    system = (
        "You are CineMatch, a friendly, knowledgeable movie buddy continuing a conversation about recommendations "
        f"you already gave. User profile: age {p['age']}, mood {p['mood']}, genres {', '.join(p['genres']) or 'any'}. "
        f"The recommended movies, best match first, are: {movies_ctx}. "
        + (f"The user is asking specifically about '{focus}'. " if focus else "Focus on these movies unless the user asks for others. ")
        + "Never reveal major spoilers unless asked. Keep answers concise and use markdown."
    )
    msgs = [{"role": "system", "content": system}] + history + [{"role": "user", "content": question}]
    stream = client.chat.completions.create(model=model, messages=msgs, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# --------------------------------------------------------------------------- view helpers
def esc(v):
    return html.escape(str(v)) if v not in (None, "") else ""


def lang_label(lang):
    return "Any language" if lang == "Any" else lang


def movie_color(m):
    return POSTER_COLORS[sum(map(ord, str(m.get("title", "")))) % len(POSTER_COLORS)]


def first_genre(m):
    return (m.get("genres") or [""])[0]


def watch_url(m):
    return "https://www.justwatch.com/us/search?q=" + urllib.parse.quote_plus(str(m.get("title", "")))


def imdb_url(m):
    if m.get("imdb_id"):
        return f"https://www.imdb.com/title/{m['imdb_id']}/"
    return "https://www.imdb.com/find/?q=" + urllib.parse.quote_plus(f"{m.get('title', '')} {m.get('year', '')}")


def meta_row(m, match_label=None):
    parts = []
    if match_label:
        parts.append(f'<span class="match">{esc(match_label)}</span>')
    parts += [f"<span>{esc(x)}</span>" for x in (m.get("year"), m.get("runtime")) if x]
    if m.get("rating"):
        parts.append(f'<span title="AI estimate"><span class="star">★</span> ~{esc(m["rating"])}</span>')
    if m.get("verified"):
        parts.append('<span class="badge" title="Year &amp; runtime checked against Wikidata">✓ Verified</span>')
    else:
        parts.append('<span class="badge warn" title="Could not verify on Wikidata">≈ Unverified</span>')
    lang = (m.get("languages") or [None])[0] or (
        st.session_state.profile.get("language") if st.session_state.profile.get("language") != "Any" else None)
    if lang:
        parts.append(f'<span class="badge">{esc(lang)}</span>')
    return f'<div class="meta-row">{"".join(parts)}</div>'


def original_title_html(m, cls="hero-original"):
    original = str(m.get("original_title") or "").strip()
    if original and original.lower() != str(m.get("title", "")).strip().lower():
        return f'<div class="{cls}">{esc(original)}</div>'
    return ""


def toggle_in(list_key, title):
    items = st.session_state[list_key]
    if title in items:
        items.remove(title)
    else:
        items.append(title)


def init_state():
    defaults = {
        "stage": "setup",
        "profile": {},
        "movies": [],
        "seen_titles": [],
        "chat": [],
        "film_chat": {},
        "my_list": [],
        "liked": [],
        "detail_idx": 0,
        "pending_question": None,
        "mood_sel": "Thoughtful",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def reset():
    for k in ["stage", "profile", "movies", "seen_titles", "chat", "film_chat", "liked", "detail_idx",
              "pending_question", "mood_sel"]:
        st.session_state.pop(k, None)


def set_mood(name):
    st.session_state.mood_sel = name


def open_detail(idx):
    st.session_state.detail_idx = idx
    st.session_state.show_detail = True


# --------------------------------------------------------------------------- detail dialog
@st.dialog("Why this pick", width="large", on_dismiss="rerun")
def detail_dialog(client, model):
    movies = st.session_state.movies
    idx = min(st.session_state.detail_idx, len(movies) - 1)
    m = movies[idx]
    title = m["title"]
    p = st.session_state.profile
    kicker = f"PICK #{idx + 1} OF {min(TOP_N, len(movies))}" if idx < TOP_N else "ALSO FITS YOUR VIBE"

    st.markdown(
        f"""<div class="d-banner" style="background: radial-gradient(circle at 80% 20%, rgba(255,255,255,.12), transparent 55%), {movie_color(m)}">
  <div class="hero-art" aria-hidden="true">{esc(title)}</div>
  <div class="kicker"><span class="cm">CM</span><span>{kicker}</span></div>
  <h2 class="d-title">{esc(title)}</h2>{original_title_html(m)}
</div>""",
        unsafe_allow_html=True,
    )

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        with st.container(key="watch_dialog", width="content"):
            st.link_button("Where to watch", watch_url(m), icon=":material/play_arrow:")
        in_list = title in st.session_state.my_list
        if st.button("", key="round_dlist", icon=":material/check:" if in_list else ":material/add:",
                     help="Remove from My list" if in_list else "Add to My list"):
            toggle_in("my_list", title)
            st.rerun(scope="fragment")
        liked = title in st.session_state.liked
        if st.button("", key="round_dlike", icon=":material/thumb_up:" if not liked else ":material/thumb_up_off_alt:",
                     help="Undo good pick" if liked else "Good pick: more like this next time"):
            toggle_in("liked", title)
            st.rerun(scope="fragment")
        if idx < TOP_N and len(movies) > TOP_N:
            if st.button("Swap this pick", key="swap_pick", help="Replace it with the next best match"):
                movies[idx] = movies.pop(TOP_N)
                st.session_state.show_detail = False
                st.rerun()

    left, right = st.columns([2, 1], gap="large")
    with left:
        match = f"Top match for {p['mood']}" if idx == 0 else f"Great match for {p['mood']}"
        st.markdown(
            meta_row(m, match)
            + f'<p class="hero-tagline" style="font-size:20px">“{esc(m.get("tagline"))}”</p>'
            + "".join(
                f'<div class="reason"><span class="bar{" grey" if grey else ""}"></span><div><h4>{h}</h4><p>{esc(t)}</p></div></div>'
                for h, t, grey in (
                    ("MOOD FIT", m.get("mood_match"), False),
                    ("WHY YOU", m.get("why_you") or m.get("genre_match"), False),
                    ("HEADS-UP", m.get("heads_up"), True),
                )
                if t
            ),
            unsafe_allow_html=True,
        )
    with right:
        facts = [
            ("Genre", ", ".join(m.get("genres") or []) or "—"),
            ("Language", ", ".join(m.get("languages") or []) or lang_label(p["language"])),
            ("Released", m.get("year") or "—"),
            ("Runtime", m.get("runtime") or "—"),
            ("Picked for", " · ".join([p["mood"], f"Age {p['age']}"] + (p["genres"][:2] or []))),
            ("Model", model or "—"),
        ]
        st.markdown(
            '<div class="facts">'
            + "".join(f"<div><span>{k}: </span>{esc(v)}</div>" for k, v in facts)
            + f'<div><span>IMDb: </span><a href="{imdb_url(m)}" target="_blank">Open page ↗</a></div></div>',
            unsafe_allow_html=True,
        )

    others = [(j, o) for j, o in enumerate(movies[:TOP_N]) if j != idx]
    if others:
        st.markdown('<div class="row-title" style="margin-top:12px">Your other picks</div>', unsafe_allow_html=True)
        cols = st.columns(len(others))
        for col, (j, o) in zip(cols, others):
            with col:
                st.markdown(
                    f'<div class="like-card"><div class="top" style="background:{movie_color(o)}">{esc(o["title"])}</div>'
                    f'<div class="body"><b>#{j + 1} · {esc(o.get("year"))} · {esc(o.get("runtime"))}</b>“{esc(o.get("tagline"))}”</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Open", key=f"dother_{j}", type="tertiary", icon=":material/info:"):
                    st.session_state.detail_idx = j
                    st.rerun(scope="fragment")

    similar = [(j, o) for j, o in enumerate(movies) if j >= TOP_N and j != idx][:3]
    if similar:
        st.markdown('<div class="row-title" style="margin-top:12px">More like this</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for col, (j, o) in zip(cols, similar):
            with col:
                st.markdown(
                    f'<div class="like-card"><div class="top" style="background:{movie_color(o)}">{esc(o["title"])}</div>'
                    f'<div class="body"><b>{esc(o.get("year"))} · {esc(first_genre(o))}</b>{esc(o.get("mood_match"))}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Open", key=f"dsim_{j}", type="tertiary", icon=":material/info:"):
                    st.session_state.detail_idx = j
                    st.rerun(scope="fragment")

    st.divider()
    history = st.session_state.film_chat.setdefault(title, [])
    for msg in history:
        with st.chat_message(msg["role"], avatar=":material/person:" if msg["role"] == "user" else ":material/movie:"):
            st.markdown(msg["content"])
    with st.form(f"ask_film_{idx}", clear_on_submit=True, border=False):
        c1, c2 = st.columns([10, 1], vertical_alignment="bottom")
        q = c1.text_input(f"Ask about {title}", placeholder="e.g. Is it too sad to watch alone?")
        sent = c2.form_submit_button("", icon=":material/arrow_upward:", type="primary")
    if sent and q.strip() and client:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(q)
        with st.chat_message("assistant", avatar=":material/movie:"):
            try:
                answer = st.write_stream(stream_answer(client, model, q, history, focus=title))
            except Exception as ex:
                answer = None
                st.error(f"Something went wrong: {ex}")
        if answer:
            history += [{"role": "user", "content": q}, {"role": "assistant", "content": answer}]


# --------------------------------------------------------------------------- app
init_state()

# ---------------- header: logo + model
api_key = secret_api_key()
client, model = None, None
with st.container(key="header"):
    h_left, h_right = st.columns([3, 2], vertical_alignment="bottom")
    h_left.markdown('<div class="logo">CineMatch</div>', unsafe_allow_html=True)
    with h_right:
        if not api_key:
            api_key = st.text_input("Groq API key", type="password", key="user_api_key",
                                    placeholder="Paste a key, or add GROQ_API_KEY to secrets")
        if api_key:
            try:
                models = available_models(api_key)
                if models:
                    client = Groq(api_key=api_key)
                    model = st.selectbox("Model", models, key="model")
                else:
                    st.warning("No chat models are available for this key.")
            except Exception as ex:
                st.error(f"Couldn't reach Groq with this key: {ex}")

# ---------------- stage 1: pick your vibe
if st.session_state.stage == "setup":
    prof = st.session_state.profile
    if prof and st.session_state.get("_prefilled") is not True:
        st.session_state.mood_sel = prof.get("mood", "Thoughtful")
        st.session_state._prefilled = True
    sel = st.session_state.mood_sel

    tile_css = "".join(
        f".stApp .st-key-mood_{i} button{{background:{d['color']} !important;}}" for i, d in enumerate(MOODS.values())
    )
    sel_i = list(MOODS).index(sel)
    tile_css += (f".stApp .st-key-mood_{sel_i} button{{opacity:1;outline:4px solid #ffffff;}}"
                 f".st-key-mood_{sel_i} button p{{font-weight:700;}}")
    st.markdown(f"<style>{tile_css}</style>", unsafe_allow_html=True)

    st.markdown(
        '<h1 style="text-align:center;margin:40px 0 36px;font-size:54px;font-weight:500;letter-spacing:-.5px;color:#fff">'
        "What's your vibe tonight?</h1>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 8, 1])
    with mid:
        cols = st.columns(len(MOODS))
        for i, (name, d) in enumerate(MOODS.items()):
            with cols[i]:
                st.button(name, key=f"mood_{i}", icon=d["icon"], on_click=set_mood, args=(name,))

    st.write("")
    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        with st.container(key="genre_pills"):
            genres = st.pills("Genres", GENRES, selection_mode="multi", default=prof.get("genres") or ["Drama"],
                              label_visibility="collapsed")

    st.write("")
    with st.container(key="filters"):
        _, c1, c2, c3, c4, _ = st.columns([1.2, 0.8, 1.4, 1.4, 1.4, 1.2], vertical_alignment="bottom")
        age = c1.number_input("Age", min_value=5, max_value=100, value=int(prof.get("age", 22)), step=1)
        language = c2.selectbox("Language", LANGUAGES, index=LANGUAGES.index(prof.get("language", "Any")),
                                format_func=lang_label)
        era = c3.selectbox("Era", ERAS, index=ERAS.index(prof.get("era", "Any era")))
        go = c4.button("Find my movies", type="primary", icon=":material/chevron_right:", use_container_width=True)
        _, n1, _ = st.columns([1.2, 5, 1.2])
        notes = n1.text_input("Anything else? (optional)", value=prof.get("notes", ""),
                              placeholder="e.g. something like Interstellar, no gore, has a twist ending…")

    if go:
        if not client:
            st.error("Add a working Groq API key at the top right to continue.")
        else:
            st.session_state.profile = {
                "mood": sel,
                "genres": genres or [],
                "age": int(age),
                "language": language,
                "era": era,
                "notes": notes.strip(),
                "count": TOP_N + MORE_N,
            }
            st.session_state._prefilled = False
            st.session_state.stage = "loading"
            st.rerun()

# ---------------- loading (also used for "different picks")
if st.session_state.stage == "loading":
    profile = st.session_state.profile
    lang_name = profile.get("language", "Any")
    spinner_txt = (
        f"Finding real {lang_name} films for your {profile['mood'].lower()} mood… (the first search for a language can take ~15s)"
        if lang_name not in ("Any", "English") else f"Finding films for your {profile['mood'].lower()} mood…"
    )
    st.markdown('<div style="height:18vh"></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid, st.spinner(spinner_txt):
        movies, tried = [], list(st.session_state.seen_titles)
        try:
            for _ in range(2): 
                pool = get_pool(profile, tried)
                batch = fetch_movies(client, model, profile, tried, pool, st.session_state.liked)
                tried += [m["title"] for m in batch]
                movies += verify_movies(batch, profile)
                if len(movies) >= TOP_N + 3:
                    break
            movies = movies[: profile["count"]]
            if not movies:
                st.warning(
                    f"Couldn't find {'' if lang_name == 'Any' else lang_name + ' '}films matching all your choices. "
                    "Try fewer genres or a wider era."
                )
        except Exception as ex:
            movies = []
            st.error(f"Couldn't get recommendations: {ex}")
    if movies:
        st.session_state.movies = movies
        st.session_state.seen_titles += [m["title"] for m in movies]
        st.session_state.chat = []
        st.session_state.stage = "results"
        st.rerun()
    else:
        with mid:
            b1, b2 = st.columns(2)
            if b1.button("Try again", type="primary", use_container_width=True):
                st.rerun()
            if b2.button("Edit vibe", use_container_width=True):
                st.session_state.stage = "setup"
                st.rerun()

# ---------------- stage 2: tonight's picks
if st.session_state.stage == "results":
    p = st.session_state.profile
    movies = st.session_state.movies
    top, more = movies[:TOP_N], movies[TOP_N:]
    hero = top[0]

    st.markdown(
        f"""<style>
.st-key-hero {{
  background:
    linear-gradient(90deg, #141414 0%, rgba(20,20,20,.9) 30%, rgba(20,20,20,.25) 65%, rgba(20,20,20,0) 100%),
    linear-gradient(0deg, #141414 6%, rgba(20,20,20,0) 45%),
    radial-gradient(circle at 78% 30%, rgba(255,255,255,.14), transparent 55%),
    {movie_color(hero)};
}}
{"".join(f".stApp .st-key-more_{j} button{{background:{movie_color(o)} !important;}}" for j, o in enumerate(movies) if j >= TOP_N)}
</style>""",
        unsafe_allow_html=True,
    )

    with st.container(key="hero"):
        st.markdown(
            f"""<div class="hero-art" aria-hidden="true">{esc(hero['title'])}</div>
<div class="kicker"><span class="cm">CM</span><span>PICK #1 FOR TONIGHT</span></div>
<h1 class="hero-title">{esc(hero['title'])}</h1>{original_title_html(hero)}
{meta_row(hero, f"Top match for {p['mood']}")}
<p class="hero-tagline">“{esc(hero.get('tagline'))}”</p>
<p class="hero-why">{esc(hero.get('mood_match'))}</p>""",
            unsafe_allow_html=True,
        )
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            with st.container(key="watch_hero", width="content"):
                st.link_button("Where to watch", watch_url(hero), icon=":material/play_arrow:")
            st.button("Why this pick", key="why_hero", icon=":material/info:", on_click=open_detail, args=(0,))
            in_list = hero["title"] in st.session_state.my_list
            st.button("", key="round_hlist", icon=":material/check:" if in_list else ":material/add:",
                      help="Remove from My list" if in_list else "Add to My list",
                      on_click=toggle_in, args=("my_list", hero["title"]))
            liked = hero["title"] in st.session_state.liked
            st.button("", key="round_hlike", icon=":material/thumb_up:" if not liked else ":material/thumb_up_off_alt:",
                      help="Undo good pick" if liked else "Good pick: more like this next time",
                      on_click=toggle_in, args=("liked", hero["title"]))

    
    with st.container(key="vibe_bar"), st.container(horizontal=True, vertical_alignment="center",
                                                    horizontal_alignment="distribute"):
        chips = [f'<span class="chip on">{esc(p["mood"])}</span>', f'<span class="chip">Age {p["age"]}</span>']
        chips += [f'<span class="chip">{esc(g)}</span>' for g in p["genres"]] or ['<span class="chip">Any genre</span>']
        chips += [f'<span class="chip">{esc(lang_label(p["language"]))}</span>', f'<span class="chip">{esc(p["era"])}</span>']
        st.markdown(f'<div class="vibe-chips"><span class="label">YOUR VIBE</span>{"".join(chips)}</div>',
                    unsafe_allow_html=True, width="content")
        with st.container(horizontal=True, width="content", gap="small"):
            if st.button("Different picks", type="tertiary", icon=":material/autorenew:"):
                st.session_state.stage = "loading"
                st.rerun()
            if st.button("Edit vibe", type="tertiary", icon=":material/tune:"):
                st.session_state.stage = "setup"
                st.rerun()
            if st.button("Start over", type="tertiary", icon=":material/restart_alt:"):
                reset()
                st.rerun()

    
    st.markdown(f'<div class="row-title">Top {len(top)} for your {esc(p["mood"].lower())} mood</div>',
                unsafe_allow_html=True)
    cols = st.columns(TOP_N, gap="medium")
    for i, m in enumerate(top):
        with cols[i]:
            rating = f'<span class="rate">★ ~{esc(m["rating"])}</span>' if m.get("rating") else ""
            meta = " · ".join(esc(x) for x in (m.get("year"), m.get("runtime"), first_genre(m)) if x)
            st.markdown(
                f"""<div class="top-item">
  <span class="top-rank" aria-hidden="true">{i + 1}</span>
  <div>
    <div class="poster" style="background:{movie_color(m)}">
      <div class="poster-top"><span class="cm">CM</span>{rating}</div>
      <div><div class="poster-title">{esc(m['title'])}</div><div class="poster-meta">{meta}</div></div>
    </div>
    <div class="top-tagline" style="width:200px">“{esc(m.get('tagline'))}”</div>
  </div>
</div>""",
                unsafe_allow_html=True,
            )
            st.button("More info", key=f"info_{i}", type="tertiary", icon=":material/info:",
                      on_click=open_detail, args=(i,))

   
    if more:
        st.markdown('<div class="row-title">Also fits your vibe</div>', unsafe_allow_html=True)
        cols = st.columns(MORE_N, gap="small")
        for k, m in enumerate(more[:MORE_N]):
            j = TOP_N + k
            with cols[k]:
                st.button(m["title"], key=f"more_{j}", on_click=open_detail, args=(j,), width="stretch")
                st.markdown(f'<div class="tile-meta">{" · ".join(esc(x) for x in (m.get("year"), first_genre(m)) if x)}</div>',
                            unsafe_allow_html=True)

    # my list
    if st.session_state.my_list:
        st.markdown('<div class="row-title">My list</div>', unsafe_allow_html=True)
        by_title = {m["title"]: m for m in movies}
        links = "".join(
            f'<a href="{imdb_url(by_title.get(t, {"title": t}))}" target="_blank">{esc(t)}</a>'
            for t in st.session_state.my_list
        )
        st.markdown(f'<div class="mylist">{links}</div>', unsafe_allow_html=True)

    # ask box
    with st.container(key="ask_box"):
        st.markdown(
            '<div class="ask-title">Ask CineMatch about these picks</div>'
            '<div class="ask-sub">Compare them, check what to expect, or nudge the vibe.</div>',
            unsafe_allow_html=True,
        )
        with st.form("ask_form", clear_on_submit=True, border=False):
            c1, c2 = st.columns([12, 1], vertical_alignment="bottom")
            typed = c1.text_input("Question", label_visibility="collapsed",
                                  placeholder="e.g. Which one is the least heavy for a weeknight?")
            sent = c2.form_submit_button("", icon=":material/arrow_upward:", type="primary", use_container_width=True)
        with st.container(horizontal=True, gap="small"):
            for n, s in enumerate(CHAT_SUGGESTIONS):
                if st.button(s, key=f"chip_{n}"):
                    st.session_state.pending_question = s

        for msg in st.session_state.chat:
            with st.chat_message(msg["role"], avatar=":material/person:" if msg["role"] == "user" else ":material/movie:"):
                st.markdown(msg["content"])

        question = (typed.strip() if sent else "") or st.session_state.pending_question
        st.session_state.pending_question = None
        if question and client:
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(question)
            with st.chat_message("assistant", avatar=":material/movie:"):
                try:
                    answer = st.write_stream(stream_answer(client, model, question, st.session_state.chat))
                except Exception as ex:
                    answer = None
                    st.error(f"Something went wrong: {ex}")
            if answer:
                st.session_state.chat += [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]

    st.markdown(f'<footer class="cm-footer">Powered by Groq · {esc(model)} · Facts checked against Wikidata</footer>',
                unsafe_allow_html=True)

    if st.session_state.pop("show_detail", False) and movies:
        detail_dialog(client, model)

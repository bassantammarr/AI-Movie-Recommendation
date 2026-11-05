import html
import json
import re
import urllib.parse

import requests
import streamlit as st
from groq import Groq

st.set_page_config(page_title="CineMatch AI", page_icon="🎬", layout="wide")


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
    "Happy": "😄",
    "Sad": "😢",
    "Excited": "🤩",
    "Romantic": "💕",
    "Adventurous": "🧭",
    "Thoughtful": "🤔",
    "Scared": "😱",
    "Chill": "😌",
}
MOOD_RULES = {
    "Happy": "light, uplifting, optimistic tone",
    "Sad": "comforting, emotional but hopeful",
    "Excited": "fast-paced, high energy",
    "Romantic": "relationship-driven, emotional",
    "Adventurous": "exploration, action, discovery",
    "Thoughtful": "deep themes, slower pace",
    "Scared": "suspenseful, tense, spooky",
    "Chill": "cozy, easy-going, low stakes",
}
GENRES = {
    "Action": "💥", "Comedy": "😂", "Drama": "🎭", "Horror": "👻", "Romance": "❤️",
    "Sci-Fi": "🚀", "Fantasy": "🧙", "Thriller": "🔪", "Mystery": "🕵️",
    "Animation": "🎨", "Documentary": "🎥", "Crime": "🚔",
}
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

GRADIENTS = [
    "linear-gradient(135deg,#ff4d6d 0%,#7b2ff7 100%)",
    "linear-gradient(135deg,#00c6ff 0%,#0072ff 100%)",
    "linear-gradient(135deg,#f7971e 0%,#ffd200 100%)",
    "linear-gradient(135deg,#11998e 0%,#38ef7d 100%)",
    "linear-gradient(135deg,#fc5c7d 0%,#6a82fb 100%)",
    "linear-gradient(135deg,#8e2de2 0%,#4a00e0 100%)",
]

# --------------------------------------------------------------------------- styles
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

html, body, [class*="css"], .stMarkdown, button, input, textarea { font-family: 'Outfit', sans-serif !important; }

.stApp {
  background:
    radial-gradient(900px 500px at 10% -10%, rgba(255,77,109,.18), transparent 60%),
    radial-gradient(900px 600px at 110% 10%, rgba(123,47,247,.20), transparent 60%),
    #0b0b14;
}
.block-container { padding-top: 2rem; max-width: 1200px; }
header[data-testid="stHeader"] { background: transparent; }

.hero { text-align:center; padding: 1.5rem 0 1rem; }
.hero .badge {
  display:inline-block; padding:.3rem .9rem; border-radius:999px; font-size:.8rem; letter-spacing:.08em;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#cfcfe6; text-transform:uppercase;
}
.hero h1 {
  font-size: clamp(2.4rem, 5vw, 4rem); font-weight:800; margin:.6rem 0 .2rem; line-height:1.05;
  background: linear-gradient(90deg,#ff4d6d,#ff9a5a,#c86bff,#6a82fb);
  background-size: 300% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent;
  animation: shine 8s ease-in-out infinite;
}
.hero p { color:#a9a9c2; font-size:1.1rem; margin:0; }
@keyframes shine { 0%,100%{background-position:0% 50%} 50%{background-position:100% 50%} }

.section-title { font-size:1.05rem; font-weight:600; color:#e6e6f5; margin: .2rem 0 .6rem; }
.section-title span { color:#ff4d6d; }

.st-key-setup_panel {
  background: rgba(22,22,38,.65) !important;
  border: 1px solid rgba(255,255,255,.08) !important;
  border-radius: 20px !important;
  padding: 1.4rem 1.6rem !important;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0,0,0,.35);
}

/* pills */
button[data-testid="stBaseButton-pills"] {
  border-radius:999px !important; border:1px solid rgba(255,255,255,.14) !important;
  background:rgba(255,255,255,.04) !important; transition: all .15s ease;
}
button[data-testid="stBaseButton-pills"]:hover { border-color:#ff4d6d !important; transform: translateY(-1px); }
button[data-testid="stBaseButton-pillsActive"] {
  border-radius:999px !important; border:1px solid transparent !important;
  background: linear-gradient(135deg,#ff4d6d,#7b2ff7) !important; color:#fff !important;
  box-shadow: 0 4px 18px rgba(255,77,109,.35);
}

/* primary button */
button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg,#ff4d6d,#7b2ff7) !important; border:none !important;
  border-radius: 14px !important; font-weight:600 !important; padding:.7rem 1rem !important;
  box-shadow: 0 8px 30px rgba(255,77,109,.35); transition: transform .15s ease, box-shadow .15s ease;
}
button[data-testid="stBaseButton-primary"]:hover { transform: translateY(-2px); box-shadow: 0 12px 36px rgba(123,47,247,.45); }
button[data-testid="stBaseButton-secondary"] { border-radius: 12px !important; }

/* movie cards */
.movie-card {
  min-height:545px; display:flex; flex-direction:column; border-radius:20px; overflow:hidden;
  background: rgba(22,22,38,.85); border:1px solid rgba(255,255,255,.08);
  box-shadow: 0 10px 40px rgba(0,0,0,.4);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
  animation: rise .5s ease both;
}
.movie-card:hover { transform: translateY(-6px); border-color: rgba(255,77,109,.5); box-shadow: 0 18px 50px rgba(255,77,109,.18); }
@keyframes rise { from{opacity:0; transform:translateY(16px)} to{opacity:1; transform:none} }
.poster { position:relative; height:170px; display:flex; align-items:center; justify-content:center; overflow:hidden; }
.poster .emoji { font-size:4.2rem; line-height:1; white-space:nowrap; filter: drop-shadow(0 6px 16px rgba(0,0,0,.35)); }
.poster .rank {
  position:absolute; top:12px; left:12px; background:rgba(0,0,0,.45); color:#fff;
  padding:.15rem .6rem; border-radius:999px; font-weight:600; font-size:.85rem;
}
.poster .rating {
  position:absolute; top:12px; right:12px; background:rgba(0,0,0,.45); color:#ffd166;
  padding:.15rem .6rem; border-radius:999px; font-weight:600; font-size:.85rem;
}
.card-body { padding: 1rem 1.1rem 1.2rem; flex:1; display:flex; flex-direction:column; }
.card-body h3 { margin:0; font-size:1.3rem; font-weight:700; color:#fff; line-height:1.2; }
.meta { color:#9a9ab5; font-size:.88rem; margin:.25rem 0 .6rem; }
.verified, .unverified { font-size:.72rem; padding:.08rem .45rem; border-radius:999px; margin-left:.3rem; }
.verified { color:#5be49b; background:rgba(91,228,155,.12); border:1px solid rgba(91,228,155,.3); }
.unverified { color:#f5c26b; background:rgba(245,194,107,.12); border:1px solid rgba(245,194,107,.3); }
.chips { display:flex; flex-wrap:wrap; gap:.35rem; margin-bottom:.7rem; }
.chip {
  font-size:.75rem; padding:.18rem .6rem; border-radius:999px;
  background:rgba(255,77,109,.12); color:#ff8fa3; border:1px solid rgba(255,77,109,.25);
}
.chip.lang { background:rgba(106,130,251,.14); color:#a9b8ff; border-color:rgba(106,130,251,.3); }
.original { color:#c9c9e0; font-size:.95rem; margin-top:.15rem; unicode-bidi:plaintext; }
.tagline { font-style:italic; color:#d4d4e8; margin-bottom:.8rem; font-size:.95rem; }
.why { font-size:.88rem; color:#c0c0d8; margin:.3rem 0; }
.why b { color:#fff; }
.links { display:flex; gap:.5rem; margin-top:auto; padding-top:.9rem; }
.links a {
  flex:1; text-align:center; text-decoration:none !important; font-size:.85rem; font-weight:600;
  padding:.45rem .5rem; border-radius:10px; color:#fff !important;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); transition: background .15s ease;
}
.links a:hover { background:rgba(255,77,109,.25); }

.profile-line { color:#b8b8d0; text-align:center; margin: -.2rem 0 1.2rem; }
.profile-line b { color:#fff; }

[data-testid="stChatMessage"] {
  background: rgba(22,22,38,.6); border:1px solid rgba(255,255,255,.06); border-radius:16px;
}
section[data-testid="stSidebar"] { background: #10101c; border-right:1px solid rgba(255,255,255,.06); }
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- helpers
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


def init_state():
    defaults = {
        "stage": "setup",
        "profile": {},
        "movies": [],
        "seen_titles": [],
        "chat": [],
        "pending_question": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def wanted_count(profile):
    strict = profile["language"] != "Any" or profile["era"] in ERA_RANGES
    return profile["count"] + (EXTRA_CANDIDATES if strict else 0)


def build_prompt(profile, exclude, pool=None):
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
    return f"""You are an explainable AI movie recommendation system.

User profile:
- Age: {profile['age']}
- Mood: {profile['mood']} ({MOOD_RULES[profile['mood']]})
- Preferred genres: {genres}
- Language: {profile['language']}
- Era: {profile['era']}
- Extra wishes: {profile['notes'] or 'none'}

Rules:
- Recommend ONLY real movies that are {popularity}.
{hard_rules_txt}
- Match the mood and the genres.
- Content must be age-appropriate for the user's age.
- Do NOT recommend any of these already-suggested titles: {exclude_txt}
- Write the tagline, mood_match and genre_match in English.
{pool_txt}
Return ONLY valid JSON, no extra text, with exactly {wanted_count(profile)} movies:
{{"movies": [{{
  "title": "the film's common English title",
  "original_title": "title in its original language/script",
  "year": 2010,
  "genres": ["Genre", "Genre"],
  "runtime": "2h 28m",
  "rating": 8.8,
  "emoji": "exactly ONE emoji character, no words (e.g. 🚀)",
  "tagline": "a short, catchy one-line hook (no spoilers)",
  "mood_match": "one sentence on why it fits the mood",
  "genre_match": "one sentence on why it fits the genres/wishes"
}}]}}"""


def fetch_movies(client, model, profile, exclude, pool=None):
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": build_prompt(profile, exclude, pool)}],
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
                  t.replace("\u2019", "'"), t.replace("'", "\u2019")):
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


def clean_emoji(movie):

    em = str(movie.get("emoji") or "").strip()
    if em and len(em) <= 8 and not re.search(r"[A-Za-z0-9\u0600-\u06FF]", em):
        return em
    for g in movie.get("genres") or []:
        for name, icon in GENRES.items():
            if name.lower() in str(g).lower():
                return icon
    return "🎬"


def render_card(movie, idx):
    e = lambda v: html.escape(str(v)) if v not in (None, "") else ""
    title, year = e(movie.get("title")), e(movie.get("year"))
    query = urllib.parse.quote_plus(f"{movie.get('title', '')} {movie.get('year', '')}")
    chips = "".join(f'<span class="chip">{e(g)}</span>' for g in (movie.get("genres") or [])[:4])
    if movie.get("languages"):
        chips += f'<span class="chip lang">🗣 {e(", ".join(movie["languages"][:2]))}</span>'
    original = str(movie.get("original_title") or "").strip()
    original_html = (
        f'<div class="original">{e(original)}</div>'
        if original and original.lower() != str(movie.get("title", "")).strip().lower() else ""
    )
    rating = movie.get("rating")
    rating_html = f'<div class="rating" title="AI estimate">⭐ ~{e(rating)}</div>' if rating else ""
    meta = " • ".join(x for x in [year, e(movie.get("runtime"))] if x)
    if movie.get("verified"):
        meta += ' <span class="verified" title="Year &amp; runtime checked against Wikidata">✓ verified</span>'
    else:
        meta += ' <span class="unverified" title="Could not verify — AI-provided details may be off">≈ unverified</span>'
    imdb_url = (
        f"https://www.imdb.com/title/{e(movie['imdb_id'])}/"
        if movie.get("imdb_id") else f"https://www.imdb.com/find/?q={query}"
    )
    return f"""
<div class="movie-card" style="animation-delay:{idx * 0.08:.2f}s">
  <div class="poster" style="background:{GRADIENTS[idx % len(GRADIENTS)]}">
    <div class="rank">#{idx + 1}</div>{rating_html}
    <div class="emoji">{e(clean_emoji(movie))}</div>
  </div>
  <div class="card-body">
    <h3>{title}</h3>{original_html}
    <div class="meta">{meta}</div>
    <div class="chips">{chips}</div>
    <div class="tagline">“{e(movie.get('tagline'))}”</div>
    <div class="why"><b>Mood:</b> {e(movie.get('mood_match'))}</div>
    <div class="why"><b>Genre:</b> {e(movie.get('genre_match'))}</div>
    <div class="links">
      <a href="https://www.youtube.com/results?search_query={query}+trailer" target="_blank">▶ Trailer</a>
      <a href="{imdb_url}" target="_blank">IMDb</a>
    </div>
  </div>
</div>"""


def stream_answer(client, model, question):
    movies_ctx = json.dumps(st.session_state.movies, ensure_ascii=False)
    p = st.session_state.profile
    system = (
        "You are a friendly, knowledgeable movie buddy continuing a conversation about recommendations "
        f"you already gave. User profile: age {p['age']}, mood {p['mood']}, genres {', '.join(p['genres']) or 'any'}. "
        f"The recommended movies are: {movies_ctx}. Focus on these movies unless the user asks for others. "
        "Never reveal major spoilers unless asked. Keep answers concise and use markdown."
    )
    msgs = [{"role": "system", "content": system}] + st.session_state.chat + [
        {"role": "user", "content": question}
    ]
    stream = client.chat.completions.create(model=model, messages=msgs, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def reset():
    for k in ["stage", "profile", "movies", "seen_titles", "chat", "pending_question"]:
        st.session_state.pop(k, None)


# --------------------------------------------------------------------------- app
init_state()

with st.sidebar:
    st.markdown("### 🎬 CineMatch AI")
    st.caption("Powered by Groq")
    api_key = secret_api_key()
    if not api_key:
        st.info("No `GROQ_API_KEY` in secrets — paste one below.")
        api_key = st.text_input("Groq API key", type="password", key="user_api_key")

    client, model = None, None
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
    if st.session_state.profile:
        p = st.session_state.profile
        st.divider()
        st.markdown("**Your vibe**")
        st.markdown(
            f"{MOODS[p['mood']]} {p['mood']}  \n"
            f"🎂 Age {p['age']}  \n"
            f"🎞️ {', '.join(p['genres']) or 'Any genre'}  \n"
            f"🌍 {p['language']} · 📅 {p['era']}"
        )
    if st.session_state.stage != "setup":
        st.divider()
        if st.button("↺ Start over", use_container_width=True):
            reset()
            st.rerun()


st.markdown(
    """
<div class="hero">
  <div class="badge">✨ AI-powered · Explainable picks</div>
  <h1>Find your perfect movie</h1>
  <p>Tell us your vibe, and we'll hand-pick films that match it — and explain why.</p>
</div>""",
    unsafe_allow_html=True,
)

# ---------------- setup stage
if st.session_state.stage == "setup":
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        with st.container(key="setup_panel"):
            st.markdown('<div class="section-title"><span>01</span> · How are you feeling?</div>', unsafe_allow_html=True)
            mood = st.pills(
                "Mood", list(MOODS), default="Happy", selection_mode="single",
                format_func=lambda m: f"{MOODS[m]} {m}", label_visibility="collapsed",
            )

            st.markdown('<div class="section-title"><span>02</span> · Pick your genres</div>', unsafe_allow_html=True)
            genres = st.pills(
                "Genres", list(GENRES), selection_mode="multi",
                format_func=lambda g: f"{GENRES[g]} {g}", label_visibility="collapsed",
            )

            st.markdown('<div class="section-title"><span>03</span> · A few details</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            age = c1.number_input("Your age", min_value=5, max_value=100, value=22, step=1)
            language = c2.selectbox("Language", LANGUAGES)
            era = c3.selectbox("Era", ERAS)

            c4, c5 = st.columns([3, 1])
            notes = c4.text_input(
                "Anything else? (optional)",
                placeholder="e.g. something like Interstellar, no gore, has a twist ending…",
            )
            count = c5.slider("How many?", 3, 6, 3)

            st.write("")
            go = st.button("🍿 Get my recommendations", type="primary", use_container_width=True)

        if go:
            if not client:
                st.error("Add a working Groq API key in the sidebar to continue.")
            else:
                st.session_state.profile = {
                    "mood": mood or "Happy",
                    "genres": genres or [],
                    "age": int(age),
                    "language": language,
                    "era": era,
                    "notes": notes.strip(),
                    "count": count,
                }
                st.session_state.stage = "loading"
                st.rerun()

# ---------------- loading stage (also used for "new picks")
if st.session_state.stage == "loading":
    lang_name = st.session_state.profile.get("language", "Any")
    spinner_txt = (
        f"🎞️ Finding real {lang_name} films and your perfect matches… (first search for a language can take ~15s)"
        if lang_name not in ("Any", "English") else "🎞️ Rolling the film… finding your perfect matches"
    )
    with st.spinner(spinner_txt):
        profile = st.session_state.profile
        movies, tried = [], list(st.session_state.seen_titles)
        try:
            for _ in range(2): 
                pool = get_pool(profile, tried)
                batch = fetch_movies(client, model, profile, tried, pool)
                tried += [m["title"] for m in batch]
                movies += verify_movies(batch, profile)
                if len(movies) >= profile["count"]:
                    break
            movies = movies[: profile["count"]]
            if not movies:
                st.warning(
                    f"Couldn't find {'' if profile['language'] == 'Any' else profile['language'] + ' '}films matching all your choices. "
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
        if st.button("Try again", type="primary"):
            st.rerun()
        if st.button("Back"):
            st.session_state.stage = "setup"
            st.rerun()

# ---------------- results stage
if st.session_state.stage == "results":
    p = st.session_state.profile
    st.markdown(
        f'<div class="profile-line">Picks for a <b>{MOODS[p["mood"]]} {p["mood"].lower()}</b> mood'
        f'{" · <b>" + html.escape(", ".join(p["genres"])) + "</b>" if p["genres"] else ""}</div>',
        unsafe_allow_html=True,
    )

    movies = st.session_state.movies
    per_row = 3
    for start in range(0, len(movies), per_row):
        cols = st.columns(per_row, gap="medium")
        for i, movie in enumerate(movies[start:start + per_row]):
            with cols[i]:
                st.markdown(render_card(movie, start + i), unsafe_allow_html=True)
        st.write("")

    _, b1, b2, _ = st.columns([2, 2, 2, 2])
    if b1.button("🔄 Show me different picks", use_container_width=True, type="primary"):
        st.session_state.stage = "loading"
        st.rerun()
    if b2.button("✏️ Change preferences", use_container_width=True):
        reset()
        st.rerun()

    st.divider()
    st.markdown('<div class="section-title"><span>💬</span> Ask about these picks</div>', unsafe_allow_html=True)

    suggestions = [
        "Which one should I watch tonight?",
        "Are these good to watch with family?",
        "Recommend something similar to #1",
        "Tell me more about #2 (no spoilers)",
    ]
    if not st.session_state.chat:
        sc = st.columns(len(suggestions))
        for col, s in zip(sc, suggestions):
            if col.button(s, use_container_width=True):
                st.session_state.pending_question = s
                st.rerun()

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🎬"):
            st.markdown(msg["content"])

    typed = st.chat_input("Ask anything about these movies…")
    question = typed or st.session_state.pending_question
    st.session_state.pending_question = None

    if question:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🎬"):
            try:
                answer = st.write_stream(stream_answer(client, model, question))
            except Exception as ex:
                answer = None
                st.error(f"Something went wrong: {ex}")
        if answer:
            st.session_state.chat += [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
            st.rerun()

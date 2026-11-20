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
GENRES = ["Drama", "Comedy", "Rom-Com", "Romance", "Thriller", "Action", "Adventure", "Sci-Fi", "Fantasy",
          "Mystery", "Crime", "Horror", "Animation", "Anime", "Family", "Documentary", "Biography", "History",
          "War", "Musical", "Sport", "Superhero", "Teen", "Western"]
KINDS = ["Movies", "Series", "Both"]
KIND_NOUN = {"Movies": "movies", "Series": "TV series", "Both": "movies or TV series"}
COMPANY = {
    "Just me": "watching alone",
    "Date night": "a date night: romantic, fun or conversation-starting",
    "Friends": "a group of friends: crowd-pleasers that are fun to watch together",
    "Family & kids": "a family with kids: MUST be family-friendly (G/PG), no strong violence, sex or swearing",
}
LENGTHS = {"Any length": None, "Under 1h 45m": 105, "Under 2h 15m": 135}
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
FILM_TYPES = ["Q11424", "Q202866", "Q29168811"]  # film, animated film, animated feature film
SERIES_TYPES = ["Q5398426", "Q1259759", "Q581714", "Q526877", "Q63952888"]  # TV/mini/animated/web/anime series  
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
.stApp button[data-testid="stBaseButton-segmented_control"] {{
  background:transparent; color:#d6d6d6; border-color:#5a5a5a; min-height:44px; padding:0 26px; font-weight:600;
}}
.stApp button[data-testid="stBaseButton-segmented_controlActive"] {{
  background:#fff; color:#141414; border-color:#fff; min-height:44px; padding:0 26px; font-weight:700;
}}
.st-key-search_row label p {{ font-size:12px; letter-spacing:1px; font-weight:600; color:#b3b3b3; text-transform:uppercase; }}
.badge.star-badge {{ border-color:#f5c518; color:#f5c518; }}

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
.hero-title {{ margin:0; font-family:'Bebas Neue', Impact, sans-serif !important; font-weight:400 !important; padding:0 !important;
  font-size:clamp(60px,7.5vw,112px) !important; line-height:.88 !important; letter-spacing:1px; max-width:760px; color:#fff; }}
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
.top-name {{ width:200px; font-size:15px; font-weight:700; color:#fff; margin-top:10px; }}
.hero-poster {{ width:100% !important; max-width:240px !important; aspect-ratio:2/3; object-fit:cover; border-radius:6px;
  box-shadow:0 24px 60px rgba(0,0,0,.6); display:block; margin-left:auto; }}
.st-key-hero {{ isolation:isolate; }}
.st-key-hero::after {{ content:""; position:absolute; inset:0; z-index:-1; pointer-events:none;
  background: linear-gradient(90deg, #141414 0%, rgba(20,20,20,.9) 30%, rgba(20,20,20,.35) 65%, rgba(20,20,20,.15) 100%),
              linear-gradient(0deg, #141414 6%, rgba(20,20,20,0) 45%); }}
.d-banner > .kicker, .d-banner > .hero-original {{ position:relative; z-index:1; }}
.d-banner {{ padding-right:190px !important; }}
.st-key-hero::before {{ content:""; position:absolute; inset:-40px; z-index:-1; background:var(--hero-bg);
  filter: blur(var(--hero-blur)); transform: scale(1.05); }}
.d-blur {{ position:absolute; inset:-40px; background-size:cover; background-position:center 25%;
  filter:blur(22px) brightness(.55); }}
.d-poster {{ position:absolute; right:28px; bottom:24px; width:130px; aspect-ratio:2/3; object-fit:cover;
  border-radius:4px; box-shadow:0 12px 30px rgba(0,0,0,.6); }}
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
.d-title {{ margin:0; font-family:'Bebas Neue', Impact, sans-serif !important; font-weight:400 !important; padding:0 !important; font-size:72px !important; line-height:.88 !important; color:#fff; position:relative; }}
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

/* ---------- motion ---------- */
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(18px); }} to {{ opacity:1; transform:none; }} }}
@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
@keyframes popIn {{ 0% {{ opacity:0; transform:scale(.85); }} 70% {{ transform:scale(1.04); }} 100% {{ opacity:1; transform:none; }} }}
@keyframes drift {{ from {{ transform:scale(1.08) translate(0,0); }} to {{ transform:scale(1.18) translate(-2%,-1.5%); }} }}
@keyframes floaty {{ 0%,100% {{ transform:translateY(0) rotate(-1deg); }} 50% {{ transform:translateY(-10px) rotate(1deg); }} }}
@keyframes glow {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(255,255,255,.0), 0 10px 30px rgba(0,0,0,.4); }}
                   50% {{ box-shadow:0 0 28px 4px rgba(255,255,255,.22), 0 10px 30px rgba(0,0,0,.4); }} }}
@keyframes shimmer {{ from {{ background-position:-400px 0; }} to {{ background-position:400px 0; }} }}
@keyframes logoIn {{ from {{ letter-spacing:12px; opacity:0; }} to {{ letter-spacing:1px; opacity:1; }} }}
@keyframes barGrow {{ from {{ width:0; }} }}

.logo {{ animation: logoIn .9s cubic-bezier(.2,.8,.2,1) both; }}
.st-key-hero .kicker {{ animation: fadeUp .6s .05s both; }}
.st-key-hero .hero-title {{ animation: fadeUp .7s .15s both; }}
.st-key-hero .hero-original, .st-key-hero .meta-row {{ animation: fadeUp .7s .28s both; }}
.st-key-hero .hero-tagline {{ animation: fadeUp .7s .38s both; }}
.st-key-hero .hero-why {{ animation: fadeUp .7s .46s both; }}
.st-key-hero::before {{ animation: drift 22s ease-in-out infinite alternate; }}
.hero-poster {{ animation: fadeIn .9s .2s both, floaty 7s 1.1s ease-in-out infinite; transition: transform .3s ease; }}
.hero-poster:hover {{ animation-play-state: paused; transform: perspective(700px) rotateY(-8deg) scale(1.04); }}
.st-key-vibe_bar {{ animation: fadeUp .6s .5s both; }}

.top-item {{ animation: fadeUp .6s both; }}
[data-testid="stColumn"]:nth-child(2) .top-item {{ animation-delay:.1s; }}
[data-testid="stColumn"]:nth-child(3) .top-item {{ animation-delay:.2s; }}
.top-rank {{ transition: -webkit-text-stroke-color .3s ease, transform .3s ease; }}
.top-item:hover .top-rank {{ -webkit-text-stroke-color:{ACCENT}; transform:translateX(-6px); }}
.top-item:hover .poster {{ transform:translateY(-8px) scale(1.03); box-shadow:0 22px 50px rgba(226,18,33,.28), 0 10px 30px rgba(0,0,0,.5); }}
.poster {{ transition: transform .3s cubic-bezier(.2,.8,.2,1), box-shadow .3s ease; }}

[class*="st-key-more_"] {{ animation: fadeUp .5s both; }}
.stApp [class*="st-key-more_"] button {{ transition: transform .25s cubic-bezier(.2,.8,.2,1), box-shadow .25s ease; }}
.stApp [class*="st-key-more_"] button:hover {{ transform:translateY(-4px) scale(1.05); box-shadow:0 16px 36px rgba(0,0,0,.6); z-index:2; }}

[class*="st-key-mood_"] {{ animation: popIn .5s both; }}
.stApp button[data-testid="stBaseButton-pills"], .stApp button[data-testid="stBaseButton-pillsActive"] {{ transition: all .18s ease; }}
.stApp button[data-testid="stBaseButton-pills"]:hover {{ border-color:#fff; transform:translateY(-2px); }}
.stApp button[data-testid="stBaseButton-primary"] {{ transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }}
.stApp button[data-testid="stBaseButton-primary"]:hover {{ transform:translateY(-2px); box-shadow:0 10px 26px rgba(226,18,33,.4); }}
.like-card {{ transition: transform .25s ease; }}
.like-card:hover {{ transform: translateY(-4px); }}
div[role="dialog"] .d-banner {{ animation: fadeIn .4s both; }}
div[role="dialog"] .d-poster {{ animation: popIn .6s .15s both; }}
div[role="dialog"] .reason {{ animation: fadeUp .5s both; }}
div[role="dialog"] .reason:nth-of-type(2) {{ animation-delay:.08s; }}
div[role="dialog"] .reason:nth-of-type(3) {{ animation-delay:.16s; }}
[data-testid="stChatMessage"] {{ animation: fadeUp .35s both; }}

/* ---------- loading screen ---------- */
.loader {{ max-width:880px; margin:8vh auto 0; text-align:center; }}
.loader .logo-big {{ font-family:'Bebas Neue', Impact, sans-serif; font-size:64px; color:{ACCENT}; letter-spacing:2px; line-height:1;
  animation: fadeIn .6s both, pulse 1.6s ease-in-out infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; text-shadow:0 0 0 rgba(226,18,33,0); }} 50% {{ opacity:.75; text-shadow:0 0 30px rgba(226,18,33,.6); }} }}
.loader .step {{ margin:18px 0 6px; font-size:20px; font-weight:600; color:#fff; animation: fadeUp .4s both; }}
.loader .sub {{ font-size:14px; color:#8c8c8c; }}
.loader .bar {{ height:3px; background:#2a2a2a; border-radius:2px; margin:22px auto 0; max-width:420px; overflow:hidden; }}
.loader .bar span {{ display:block; height:100%; background:{ACCENT}; border-radius:2px; animation: barGrow .8s ease both; }}
.loader .strip {{ display:flex; gap:14px; justify-content:center; margin-top:34px; }}
.loader .ghost {{ width:120px; height:178px; border-radius:6px; animation: fadeUp .5s both;
  background: linear-gradient(90deg, #1f1f1f 0%, #2c2c2c 40%, #1f1f1f 80%); background-size:800px 100%; }}
.loader .ghost {{ animation: fadeUp .5s both, shimmer 1.4s linear infinite; }}
.loader .steps {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top:26px; font-size:13px; }}
.loader .steps span {{ padding:6px 12px; border-radius:999px; background:#1f1f1f; color:#6b6b6b; }}
.loader .steps span.done {{ background:#1f2e22; color:#46d369; }}
.loader .steps span.now {{ background:#fff; color:#141414; font-weight:700; }}

/* ---------- phones ---------- */
@media (max-width: 700px) {{
  .block-container {{ padding: .6rem 16px 2rem; }}
  .st-key-hero {{ margin:0 -16px; width:calc(100% + 32px) !important; padding:60px 16px 120px; min-height:auto; }}
  .hero-title {{ font-size:58px !important; }}
  .hero-tagline {{ font-size:18px; }}
  .top-rank {{ font-size:150px; margin-right:-16px; }}
  .poster, .top-tagline, .top-name {{ width:160px !important; }}
  .poster {{ height:232px; }}
  .stApp [class*="st-key-mood_"] button {{ width:120px; height:120px; }}
  .stApp [class*="st-key-mood_"] button span[data-testid="stIconMaterial"] {{ font-size:44px; }}
  .loader .ghost:nth-child(n+4) {{ display:none; }}
  .hero-poster {{ max-width:150px !important; margin:8px auto 0 !important; }}
  .d-banner {{ padding-right:24px !important; }}
  .d-poster {{ display:none; }}
}}

/* ---------- respect "reduce motion" ---------- */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation:none !important; transition:none !important; }}
}}
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
    strict = (profile["language"] != "Any" or profile["era"] in ERA_RANGES or profile.get("actor")
              or profile.get("kind", "Movies") != "Both" or LENGTHS.get(profile.get("length")))
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
    kind = profile.get("kind", "Movies")
    if kind == "Movies":
        hard_rules.append("- TYPE IS MANDATORY: recommend feature films only, no TV series.")
    elif kind == "Series":
        hard_rules.append("- TYPE IS MANDATORY: recommend TV series or miniseries only, no films.")
    else:
        hard_rules.append("- Mix feature films and TV series.")
    fav = profile.get("favourite")
    if fav:
        hard_rules.append(
            f"- SIMILAR TO '{fav}': the user loves '{fav}'. Recommend titles with a similar feel, themes, style "
            f"or tone, while still respecting the other wishes. Never recommend '{fav}' itself, and say in "
            f"why_you what each pick shares with it."
        )
    actor = profile.get("actor")
    if actor:
        hard_rules.append(f"- STARRING {actor}: every pick must have {actor} in its main cast.")
    limit = LENGTHS.get(profile.get("length"))
    if limit and kind != "Series":
        hard_rules.append(f"- Films must be shorter than {limit} minutes.")
    if pool:
        hard_rules.append(
            "- PICK ONLY FROM THE CANDIDATE LIST below (real titles from Wikidata). Copy the title and year "
            "exactly as written. Never invent a title or pick one that is not on the list."
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
    noun = KIND_NOUN[kind]
    return f"""You are an explainable AI movie and TV recommendation system.

User profile:
- Looking for: {noun}
- Age: {profile['age']}
- Mood: {profile['mood']} ({MOODS[profile['mood']]['rule']})
- Preferred genres: {genres}  (Rom-Com = romantic comedy)
- Language: {profile['language']}
- Era: {profile['era']}
- Watching with: {COMPANY.get(profile.get('company', 'Just me'), 'watching alone')}
- Favourite to match: {fav or 'none'}
- Favourite actor: {actor or 'none'}
- Extra wishes: {profile['notes'] or 'none'}

Rules:
- Recommend ONLY real {noun} that are {popularity}.
{hard_rules_txt}
- Match the mood and the genres. Order the list from best match to weakest match.
- Content must be age-appropriate for the user's age.
- Do NOT recommend any of these already-suggested titles: {exclude_txt}
{liked_txt}- Write all text fields in English.
{pool_txt}
Return ONLY valid JSON, no extra text, with exactly {wanted_count(profile)} titles:
{{"movies": [{{
  "title": "the common English title",
  "original_title": "title in its original language/script",
  "type": "movie or series",
  "year": 2010,
  "genres": ["Genre", "Genre"],
  "runtime": "film: total length like 2h 28m; series: episode length like 45m",
  "seasons": "number of seasons for a series, otherwise null",
  "cast": ["2 or 3 lead actors"],
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
    series = " ".join("wd:" + q for q in SERIES_TYPES)
    query = f"""SELECT ?i ?item ?date ?dur ?imdb ?links ?langLabel ?wiki ?isSeries ?seasons WHERE {{
  VALUES (?i ?label) {{ {values} }}
  {{ ?item rdfs:label ?label }} UNION {{ ?item skos:altLabel ?label }}
  {{ ?item wdt:P57 [] }} UNION {{ VALUES ?stype {{ {series} }} ?item wdt:P31 ?stype }}
  ?item wdt:P577|wdt:P580 ?date ; wikibase:sitelinks ?links .
  OPTIONAL {{ VALUES ?stype2 {{ {series} }} ?item wdt:P31 ?stype2 . BIND(true AS ?isSeries) }}
  OPTIONAL {{ ?item wdt:P2437 ?seasons }}
  OPTIONAL {{ ?item wdt:P2047 ?dur }}
  OPTIONAL {{ ?item wdt:P345 ?imdb }}
  OPTIONAL {{ ?item wdt:P364 ?lang . ?lang rdfs:label ?langLabel FILTER(lang(?langLabel) = "en") }}
  OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?wiki }}
}}"""
    r = requests.post(WIKIDATA_SPARQL, data={"query": query}, headers=HTTP_HEADERS, timeout=25)
    r.raise_for_status()
    found = {}
    for b in r.json()["results"]["bindings"]:
        i, qid = int(b["i"]["value"]), b["item"]["value"].rsplit("/", 1)[-1]
        c = found.setdefault(i, {}).setdefault(
            qid,
            {"qid": qid, "years": set(), "durations": set(), "languages": set(), "imdb": None, "wiki": None,
             "series": False, "seasons": None, "links": int(b["links"]["value"])},
        )
        if "isSeries" in b:
            c["series"] = True
        if "seasons" in b:
            try:
                c["seasons"] = max(c["seasons"] or 0, int(float(b["seasons"]["value"])))
            except ValueError:
                pass
        if "wiki" in b:
            c["wiki"] = b["wiki"]["value"]
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


def kind_types(kind):
    return {"Movies": FILM_TYPES, "Series": SERIES_TYPES}.get(kind, FILM_TYPES + SERIES_TYPES)


def name_variants(name):
    name = " ".join(str(name).split())
    return tuple(dict.fromkeys([name, " ".join(w[:1].upper() + w[1:] for w in name.split(" "))]))


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def actor_pool(actor, kind, era_name, limit=200):
    """The actor's best-known real films/series from Wikidata, so 'Starring X' picks are real."""
    names = " ".join(f"{json.dumps(n)}@{l}" for n in name_variants(actor) for l in ("en", "mul"))
    types = " ".join("wd:" + q for q in kind_types(kind))
    rows = sparql(f"""SELECT DISTINCT ?item ?links WHERE {{
  VALUES ?name {{ {names} }} VALUES ?type {{ {types} }}
  ?person rdfs:label ?name ; wdt:P31 wd:Q5 .
  ?item wdt:P161 ?person ; wdt:P31 ?type ; wikibase:sitelinks ?links .
}} ORDER BY DESC(?links) LIMIT {limit}""", timeout=30)
    links = {b["item"]["value"].rsplit("/", 1)[-1]: int(b["links"]["value"]) for b in rows}
    return pool_details(links, era_name)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def candidate_pool(language, era_name, kind="Movies", limit=400):
    """The best-known real titles in a language (and era), so the AI picks from facts, not memory."""
    langs = " ".join("wd:" + q for q in LANG_QIDS[language])
    types = " ".join("wd:" + q for q in kind_types(kind))
    countries = " ".join("wd:" + q for q in LANG_COUNTRIES.get(language, []))
    country_rule = f"VALUES ?country {{ {countries} }} ?item wdt:P495 ?country ." if countries else ""
    rows = sparql(f"""SELECT DISTINCT ?item ?links WHERE {{
  VALUES ?lang {{ {langs} }} VALUES ?type {{ {types} }}
  ?item wdt:P364 ?lang ; wdt:P31 ?type ; wikibase:sitelinks ?links .
  {country_rule}
}} ORDER BY DESC(?links) LIMIT {limit}""")
    links = {b["item"]["value"].rsplit("/", 1)[-1]: int(b["links"]["value"]) for b in rows}
    return pool_details(links, era_name)


def pool_details(links, era_name):
    """Title, first year and genres for a set of Wikidata items, filtered to the era."""
    if not links:
        return []
    ids = " ".join("wd:" + q for q in links)
    rows = sparql(f"""SELECT ?item ?d ?title ?gl WHERE {{
  VALUES ?item {{ {ids} }}
  ?item wdt:P577|wdt:P580 ?d .
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
    """Real candidates from Wikidata for an actor's work or a non-English language;
    None means 'let the AI choose freely'."""
    kind = profile.get("kind", "Movies")
    try:
        if profile.get("actor"):
            pool = actor_pool(profile["actor"], kind, profile["era"])
        elif profile["language"] not in ("Any", "English") and profile["language"] in LANG_QIDS:
            pool = candidate_pool(profile["language"], profile["era"], kind)
        else:
            return None
    except Exception:
        return None  
    seen = {t.lower() for t in exclude} | {str(profile.get("favourite") or "").lower()}
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
        if best["series"] and best["durations"]:
            movie["runtime"] = f"{fmt_runtime(min(best['durations']))} episodes"
        movie["qid"] = best["qid"]
        movie["is_series"] = best["series"]
        if best["seasons"]:
            movie["seasons"] = best["seasons"]
        movie["imdb_id"] = best["imdb"]
        movie["wiki"] = best.get("wiki")
        movie["languages"] = sorted(best["languages"])
        movie["lang_ok"] = lang_match(best) if best["languages"] else None
        movie["verified"] = True

    era = ERA_RANGES.get(profile["era"])
    kind = profile.get("kind", "Movies")
    limit = LENGTHS.get(profile.get("length"))
    fav = str(profile.get("favourite") or "").strip().lower()

    def rank(m):
        """2 = confirmed match, 1 = can't confirm, 0 = confirmed mismatch (dropped)."""
        try:
            year = int(str(m.get("year"))[:4])
        except ValueError:
            year = None
        if era and year and not era[0] <= year <= era[1]:
            return 0
        is_series = m["is_series"] if m.get("verified") else str(m.get("type", "")).lower().startswith("series")
        m["is_series"] = is_series
        if (kind == "Movies" and is_series) or (kind == "Series" and not is_series):
            return 0
        mins = parse_minutes(m.get("runtime"))
        if limit and not is_series and mins and mins > limit:
            return 0
        if fav and str(m.get("title", "")).strip().lower() == fav:
            return 0
        if lang != "Any":
            if m.get("lang_ok") is False or not m.get("verified"):
                return 0  # wrong language, or a film Wikidata can't find (likely invented)
            if m.get("lang_ok") is None:
                return 1
        return 2 if m.get("verified") else 1

    ranked = sorted(((rank(m), i, m) for i, m in enumerate(movies)), key=lambda x: (-x[0], x[1]))
    return [m for r, _, m in ranked if r > 0][: profile["count"]]


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def wikidata_cast(qids):
    
    if not qids:
        return {}
    ids = " ".join("wd:" + q for q in qids)
    rows = sparql(f"""SELECT ?item ?name WHERE {{
  VALUES ?item {{ {ids} }}
  ?item wdt:P161 ?a . ?a rdfs:label ?name FILTER(lang(?name) IN ("en", "mul"))
}}""", timeout=25)
    out = {}
    for b in rows:
        out.setdefault(b["item"]["value"].rsplit("/", 1)[-1], set()).add(b["name"]["value"])
    return out


def norm_name(n):
    import unicodedata
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", n.lower()).split())


def attach_cast(movies, actor=None):
    
    qids = tuple(dict.fromkeys(m["qid"] for m in movies if m.get("qid")))
    try:
        cast = wikidata_cast(qids)
    except Exception:
        cast = {}
    want = norm_name(actor) if actor else None
    for m in movies:
        names = cast.get(m.get("qid"), set())
        by_norm = {norm_name(n): n for n in names}
        ai_cast = m.get("cast") if isinstance(m.get("cast"), list) else []
        m["cast"] = [by_norm[norm_name(n)] for n in ai_cast if norm_name(n) in by_norm][:4]
        if want:
            m["with_actor"] = want in by_norm
            if m["with_actor"] and by_norm[want] not in m["cast"]:
                m["cast"] = [by_norm[want]] + m["cast"][:3]
    if want and sum(1 for m in movies if m.get("with_actor")) >= TOP_N:
        movies = [m for m in movies if m.get("with_actor")]
    elif want:
        movies = sorted(movies, key=lambda m: not m.get("with_actor"))
    return movies


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def wikipedia_posters(wiki_titles):
    """Poster image for each English Wikipedia article (the infobox image), in one request."""
    if not wiki_titles:
        return {}
    r = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params=dict(action="query", titles="|".join(wiki_titles), prop="pageimages", piprop="thumbnail",
                    pithumbsize=500, pilicense="any", redirects=1, format="json", formatversion=2),
        headers={"User-Agent": HTTP_HEADERS["User-Agent"]},
        timeout=15,
    )
    r.raise_for_status()
    q = r.json().get("query", {})
    alias = {}  # requested title -> final page title (after normalising / redirects)
    for step in q.get("normalized", []) + q.get("redirects", []):
        alias[step["from"]] = step["to"]
    by_page = {p["title"]: p.get("thumbnail", {}).get("source") for p in q.get("pages", [])}
    out = {}
    for t in wiki_titles:
        final = t
        while final in alias:
            final = alias[final]
        if by_page.get(final):
            out[t] = by_page[final]
    return out


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def tvmaze_poster(imdb_id, title):
    
    headers = {"User-Agent": HTTP_HEADERS["User-Agent"]}
    try:
        r = None
        if imdb_id:
            r = requests.get("https://api.tvmaze.com/lookup/shows", params={"imdb": imdb_id}, headers=headers, timeout=8)
        if r is None or not r.ok:
            r = requests.get("https://api.tvmaze.com/singlesearch/shows", params={"q": title}, headers=headers, timeout=8)
        if not r.ok:
            return None
        image = r.json().get("image") or {}
        return image.get("original") or image.get("medium")
    except Exception:
        return None


def attach_posters(movies):
    """Add a 'poster' URL: TVmaze for series, the Wikipedia infobox image for films (and as a fallback)."""
    def guesses(m):
        # Unverified films have no known article, so try the usual Wikipedia naming patterns.
        if m.get("wiki"):
            return [m["wiki"]]
        t, y = str(m.get("title", "")).strip(), str(m.get("year", "")).strip()[:4]
        return [f"{t} ({y} film)", f"{t} (film)", t] if t else []

    titles = tuple(dict.fromkeys(g for m in movies for g in guesses(m)))[:50]
    try:
        found = wikipedia_posters(titles)
    except Exception:
        found = {}  
    for m in movies:
        series = m.get("is_series") or str(m.get("type", "")).lower().startswith("series")
        poster = tvmaze_poster(m.get("imdb_id"), m["title"]) if series else None
        wiki_poster = next((found[g] for g in guesses(m) if g in found), None)
        m["poster"] = poster or wiki_poster or m.get("poster")
        if not m["poster"]:
            m.pop("poster")
    return movies


def stream_answer(client, model, question, history, focus=None):
    movies_ctx = json.dumps(
        [{k: m.get(k) for k in ("title", "is_series", "year", "runtime", "seasons", "genres", "cast", "languages",
                                "tagline", "mood_match")}
         for m in st.session_state.movies],
        ensure_ascii=False,
    )
    p = st.session_state.profile
    system = (
        "You are CineMatch, a friendly, knowledgeable movie and TV buddy continuing a conversation about recommendations "
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


def clean_html(block):
    
    return " ".join(line.strip() for line in block.splitlines() if line.strip())


def lang_label(lang):
    return "Any language" if lang == "Any" else lang


def movie_color(m):
    return POSTER_COLORS[sum(map(ord, str(m.get("title", "")))) % len(POSTER_COLORS)]


def css_url(u):
    return "url('" + str(u).replace("'", "%27").replace('"', "%22").replace(" ", "%20") + "')"


def poster_bg(m, overlay="linear-gradient(0deg, rgba(0,0,0,.85) 0%, rgba(0,0,0,0) 55%)", pos="center 20%"):
    """CSS background for a card: the film's poster (if any) over its fallback colour."""
    if m.get("poster"):
        return f"{overlay}, {css_url(m['poster'])} {pos} / cover no-repeat, {movie_color(m)}"
    return movie_color(m)


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
    if m.get("is_series"):
        parts.append('<span class="badge">Series</span>')
    seasons = f"{m['seasons']} season{'s' if str(m['seasons']) != '1' else ''}" if m.get("seasons") else None
    parts += [f"<span>{esc(x)}</span>" for x in (m.get("year"), seasons, m.get("runtime")) if x]
    if m.get("rating"):
        parts.append(f'<span title="AI estimate"><span class="star">★</span> ~{esc(m["rating"])}</span>')
    if m.get("verified"):
        parts.append('<span class="badge" title="Year &amp; runtime checked against Wikidata">✓ Verified</span>')
    else:
        parts.append('<span class="badge warn" title="Could not verify on Wikidata">≈ Unverified</span>')
    if m.get("with_actor"):
        parts.append(f'<span class="badge star-badge">★ {esc(st.session_state.profile.get("actor"))}</span>')
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
    adding = title not in items
    if adding:
        items.append(title)
    else:
        items.remove(title)
    if list_key == "my_list":
        st.toast(f"Added “{title}” to My list" if adding else f"Removed “{title}” from My list",
                 icon=":material/bookmark_added:" if adding else ":material/bookmark_remove:")
    else:
        st.toast(f"Noted! Next picks will lean toward “{title}”" if adding else f"Un-liked “{title}”",
                 icon=":material/thumb_up:")


def trailer_url(m):
    q = f"{m.get('title', '')} {m.get('year', '')} {'series' if m.get('is_series') else ''} official trailer"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)


def share_text(movies, p):
    head = f"My CineMatch picks ({p.get('kind', 'Movies')}, {p['mood']} mood)"
    lines = [head, ""]
    for i, m in enumerate(movies, 1):
        bits = [str(m.get("year") or ""), str(m.get("runtime") or "")]
        lines.append(f"{i}. {m['title']} ({' · '.join(b for b in bits if b)}) {imdb_url(m)}")
    return "\n".join(lines)


LOAD_STEPS = ["Reading your vibe", "Finding real titles", "Asking the AI", "Checking facts", "Fetching posters"]


def show_loader(slot, step, headline, sub=""):
    
    chips = "".join(
        f'<span class="{"done" if i < step else "now" if i == step else ""}">'
        f'{"✓ " if i < step else ""}{name}</span>'
        for i, name in enumerate(LOAD_STEPS)
    )
    ghosts = "".join(f'<div class="ghost" style="animation-delay:{i * .08:.2f}s, {i * .15:.2f}s"></div>' for i in range(5))
    pct = int((step + 0.5) / len(LOAD_STEPS) * 100)
    slot.markdown(
        f'<div class="loader"><div class="logo-big">CineMatch</div>'
        f'<div class="step">{esc(headline)}</div><div class="sub">{esc(sub)}</div>'
        f'<div class="bar"><span style="width:{pct}%"></span></div>'
        f'<div class="strip">{ghosts}</div><div class="steps">{chips}</div></div>',
        unsafe_allow_html=True,
    )


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


def find_more_like(title):
   
    st.session_state.profile["favourite"] = title
    st.session_state.show_detail = False
    st.session_state.stage = "loading"


def vibe_title(p, n):
    if p.get("favourite"):
        return f"Top {n} like {p['favourite']}"
    if p.get("actor"):
        return f"Top {n} starring {p['actor']}"
    return f"Top {n} for your {p['mood'].lower()} mood"


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
        clean_html(f"""<div class="d-banner" style="background: radial-gradient(circle at 80% 20%, rgba(255,255,255,.12), transparent 55%), {movie_color(m)}">
  {f'<div class="d-blur" style="background-image:{css_url(m["poster"])}"></div><img class="d-poster" src="{esc(m["poster"])}" alt="Poster for {esc(title)}">'
   if m.get("poster") else f'<div class="hero-art" aria-hidden="true">{esc(title)}</div>'}
  <div class="kicker"><span class="cm">CM</span><span>{kicker}</span></div>
  <h2 class="d-title">{esc(title)}</h2>{original_title_html(m)}
</div>"""),
        unsafe_allow_html=True,
    )

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        with st.container(key="watch_dialog", width="content"):
            st.link_button("Where to watch", watch_url(m), icon=":material/play_arrow:")
        st.link_button("Trailer", trailer_url(m), icon=":material/smart_display:")
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
        if st.button("More like this", key="like_this", icon=":material/travel_explore:",
                     help=f"New picks similar to {title}"):
            find_more_like(title)
            st.rerun()
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
            ("Type", "TV series" if m.get("is_series") else "Film"),
            ("Genre", ", ".join(m.get("genres") or []) or "—"),
            ("Starring", ", ".join(m.get("cast") or []) or "—"),
            ("Language", ", ".join(m.get("languages") or []) or lang_label(p["language"])),
            ("Released", m.get("year") or "—"),
            ("Seasons" if m.get("is_series") else "Runtime",
             (m.get("seasons") or "—") if m.get("is_series") else (m.get("runtime") or "—")),
            ("Picked for", " · ".join([p["mood"], f"Age {p['age']}"] + (p["genres"][:2] or [])
                                      + ([f"like {p['favourite']}"] if p.get("favourite") else [])
                                      + ([f"with {p['actor']}"] if p.get("actor") else []))),
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
                    f'<div class="like-card"><div class="top" style="background:{poster_bg(o, pos="center 25%")}">{esc(o["title"])}</div>'
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
                    f'<div class="like-card"><div class="top" style="background:{poster_bg(o, pos="center 25%")}">{esc(o["title"])}</div>'
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
                    model = models[0]
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
    tile_css += (f".stApp .st-key-mood_{sel_i} button{{opacity:1;outline:4px solid #ffffff;"
                 f"animation: glow 2.4s ease-in-out infinite;}}"
                 f".st-key-mood_{sel_i} button p{{font-weight:700;}}")
    tile_css += "".join(f".st-key-mood_{i}{{animation-delay:{i * 0.06:.2f}s;}}" for i in range(len(MOODS)))
    st.markdown(f"<style>{tile_css}</style>", unsafe_allow_html=True)

    st.markdown(
        '<h1 style="text-align:center;margin:32px 0 18px;font-size:54px;font-weight:500;letter-spacing:-.5px;color:#fff">'
        "What's your vibe tonight?</h1>",
        unsafe_allow_html=True,
    )
    with st.container(key="kind_seg", horizontal=True, horizontal_alignment="center"):
        kind = st.segmented_control("Looking for", KINDS, default=prof.get("kind", "Movies"),
                                    label_visibility="collapsed", width="content") or "Movies"
    st.write("")
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
    with st.container(key="search_row"):
        _, s1, s2, _ = st.columns([1, 2.5, 2.5, 1])
        favourite = s1.text_input(
            "Similar to a favourite (optional)", value=prof.get("favourite", ""),
            placeholder="e.g. Inception, Breaking Bad, Parasite",
            help="We'll find titles with a similar feel, themes or style.")
        actor = s2.text_input(
            "Starring (optional)", value=prof.get("actor", ""),
            placeholder="e.g. Tom Hanks, Song Kang-ho, Adel Emam",
            help="Picks come from this actor's real filmography on Wikidata.")

    with st.container(key="filters"):
        _, c1, c2, c3, c4, c5, _ = st.columns([1, 0.8, 1.3, 1.3, 1.3, 1.3, 1], vertical_alignment="bottom")
        age = c1.number_input("Age", min_value=5, max_value=100, value=int(prof.get("age", 22)), step=1)
        language = c2.selectbox("Language", LANGUAGES, index=LANGUAGES.index(prof.get("language", "Any")),
                                format_func=lang_label)
        era = c3.selectbox("Era", ERAS, index=ERAS.index(prof.get("era", "Any era")))
        company = c4.selectbox("Watching with", list(COMPANY),
                               index=list(COMPANY).index(prof.get("company", "Just me")))
        length = c5.selectbox("Length", list(LENGTHS), index=list(LENGTHS).index(prof.get("length", "Any length")),
                              disabled=kind == "Series", help="Applies to films only")
        _, n1, n2, _ = st.columns([1, 4.2, 1.6, 1], vertical_alignment="bottom")
        notes = n1.text_input("Anything else? (optional)", value=prof.get("notes", ""),
                              placeholder="e.g. no gore, has a twist ending, set in Paris…")
        go_label = {"Movies": "Find my movies", "Series": "Find my series", "Both": "Find my picks"}[kind]
        go = n2.button(go_label, type="primary", icon=":material/chevron_right:", use_container_width=True)

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
                "kind": kind,
                "favourite": favourite.strip(),
                "actor": actor.strip(),
                "company": company,
                "length": length,
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
    noun = KIND_NOUN[profile.get("kind", "Movies")]
    if profile.get("actor"):
        spinner_txt = f"Looking through {profile['actor']}'s real {noun} on Wikidata…"
    elif profile.get("favourite"):
        spinner_txt = f"Finding {noun} like {profile['favourite']}…"
    elif lang_name not in ("Any", "English"):
        spinner_txt = (f"Finding real {lang_name} {noun} for your {profile['mood'].lower()} mood… "
                       "(the first search for a language can take ~15s)")
    else:
        spinner_txt = f"Finding {noun} for your {profile['mood'].lower()} mood…"
    
    st.markdown('<style>.stApp [data-stale="true"]{display:none !important;}</style>', unsafe_allow_html=True)
    slot = st.empty()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        movies, tried = [], list(st.session_state.seen_titles)
        try:
            show_loader(slot, 0, spinner_txt)
            for round_no in range(2):  
                show_loader(slot, 1, spinner_txt,
                            "Pulling a list of real titles from Wikidata" if profile.get("actor") or lang_name
                            not in ("Any", "English") else "Narrowing things down")
                pool = get_pool(profile, tried)
                show_loader(slot, 2, "Asking the AI for your best matches…",
                            "Hunting for a few more" if round_no else "Matching mood, genres and wishes")
                batch = fetch_movies(client, model, profile, tried, pool, st.session_state.liked)
                tried += [m["title"] for m in batch]
                show_loader(slot, 3, "Checking years, runtimes and cast…", "Every title is verified on Wikidata")
                movies += verify_movies(batch, profile)
                if len(movies) >= TOP_N + 3:
                    break
            movies = attach_cast(movies, profile.get("actor"))[: profile["count"]]
            show_loader(slot, 4, "Fetching posters…", "Almost there")
            movies = attach_posters(movies)
            slot.empty()
            if not movies:
                st.warning(
                    f"Couldn't find {'' if lang_name == 'Any' else lang_name + ' '}{noun} matching all your choices. "
                    "Try fewer genres, a wider era, or switch Movies/Series."
                )
        except Exception as ex:
            slot.empty()
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
  --hero-bg: {poster_bg(hero, "radial-gradient(circle at 78% 30%, rgba(255,255,255,.10), transparent 55%)", "center 30%")};
  --hero-blur: {"28px" if hero.get("poster") else "0px"};
}}
{"".join(f".stApp .st-key-more_{j} button{{background:{poster_bg(o, pos='center 25%')} !important;}}" for j, o in enumerate(movies) if j >= TOP_N)}
</style>""",
        unsafe_allow_html=True,
    )

    with st.container(key="hero"):
      hero_text, hero_img = st.columns([3, 1], vertical_alignment="bottom")
      if hero.get("poster"):
          hero_img.markdown(f'<img class="hero-poster" src="{esc(hero["poster"])}" alt="Poster for {esc(hero["title"])}">',
                            unsafe_allow_html=True)
      with hero_text:
        st.markdown(
            clean_html(f"""{"" if hero.get("poster") else f'<div class="hero-art" aria-hidden="true">{esc(hero["title"])}</div>'}
<div class="kicker"><span class="cm">CM</span><span>{esc(("BECAUSE YOU LIKED " + p["favourite"]).upper() if p.get("favourite") else "PICK #1 FOR TONIGHT")}</span></div>
<h1 class="hero-title">{esc(hero['title'])}</h1>{original_title_html(hero)}
{meta_row(hero, f"Top match for {p['mood']}")}
<p class="hero-tagline">“{esc(hero.get('tagline'))}”</p>
<p class="hero-why">{esc(hero.get('mood_match'))}</p>"""),
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
            st.button("More like this", key="like_hero", type="tertiary", icon=":material/travel_explore:",
                      on_click=find_more_like, args=(hero["title"],))
            liked = hero["title"] in st.session_state.liked
            st.button("", key="round_hlike", icon=":material/thumb_up:" if not liked else ":material/thumb_up_off_alt:",
                      help="Undo good pick" if liked else "Good pick: more like this next time",
                      on_click=toggle_in, args=("liked", hero["title"]))

    
    with st.container(key="vibe_bar"), st.container(horizontal=True, vertical_alignment="center",
                                                    horizontal_alignment="distribute"):
        chips = [f'<span class="chip on">{esc(p.get("kind", "Movies"))}</span>',
                 f'<span class="chip on">{esc(p["mood"])}</span>']
        if p.get("favourite"):
            chips.append(f'<span class="chip on">Like {esc(p["favourite"])}</span>')
        if p.get("actor"):
            chips.append(f'<span class="chip on">★ {esc(p["actor"])}</span>')
        chips.append(f'<span class="chip">Age {p["age"]}</span>')
        if p.get("company", "Just me") != "Just me":
            chips.append(f'<span class="chip">{esc(p["company"])}</span>')
        if LENGTHS.get(p.get("length")) and p.get("kind") != "Series":
            chips.append(f'<span class="chip">{esc(p["length"])}</span>')
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
            with st.popover("Share", icon=":material/ios_share:", type="tertiary"):
                st.caption("Copy your picks to send to a friend")
                st.code(share_text(movies, p), language=None, wrap_lines=True)
            if st.button("Start over", type="tertiary", icon=":material/restart_alt:"):
                reset()
                st.rerun()

    
    st.markdown(f'<div class="row-title">{esc(vibe_title(p, len(top)))}</div>', unsafe_allow_html=True)
    cols = st.columns(TOP_N, gap="medium")
    for i, m in enumerate(top):
        with cols[i]:
            rating = f'<span class="rate">★ ~{esc(m["rating"])}</span>' if m.get("rating") else ""
            seasons = f"{m['seasons']} seasons" if m.get("seasons") else ("Series" if m.get("is_series") else None)
            meta = " · ".join(esc(x) for x in (m.get("year"), seasons or m.get("runtime"), first_genre(m)) if x)
            st.markdown(
                clean_html(f"""<div class="top-item">
  <span class="top-rank" aria-hidden="true">{i + 1}</span>
  <div>
    <div class="poster" role="img" aria-label="{esc(m['title'])}" style="background:{poster_bg(m)}">
      <div class="poster-top"><span class="cm">CM</span>{rating}</div>
      <div>{"" if m.get("poster") else f'<div class="poster-title">{esc(m["title"])}</div>'}<div class="poster-meta">{meta}</div></div>
    </div>
    {f'<div class="top-name">{esc(m["title"])}</div>' if m.get("poster") else ""}
    <div class="top-tagline" style="width:200px">“{esc(m.get('tagline'))}”</div>
  </div>
</div>"""),
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

    st.markdown('<footer class="cm-footer">Powered by Groq · Facts checked against Wikidata</footer>',
                unsafe_allow_html=True)

    if st.session_state.pop("show_detail", False) and movies:
        detail_dialog(client, model)

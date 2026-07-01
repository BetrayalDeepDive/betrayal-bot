#!/usr/bin/env python3
"""
THE ARCHIVE — ANIMATED HISTORY/GEOPOLITICS PIPELINE v1.0
Channel 4 of DeepDive Empire

Niches: Geopolitics Investigative, Military Secrets, Military Strategies,
        World War II, Ancient Civilizations, Dark History, Espionage/Intelligence,
        Islamic Civilization, Vikings, DNA History

Format: MAP mode (parchment-warm palette, border draws, territory reveals)
        BLUEPRINT mode (cool palette, measurement grids, excavation/document layers)
        Hybrid mode for crossover topics

Phase: PIPELINE_PHASE=generate / upload / full
"""
import os, sys, re, json, time, datetime, random, asyncio, subprocess, shutil
from pathlib import Path
from collections import Counter

# ── PATHS ────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
WORK_DIR     = Path(os.environ.get("WORK_DIR", "/tmp/archive"))
WORK_DIR.mkdir(parents=True, exist_ok=True)

# ── WORD COUNT: 15-minute target ─────────────────────────────
MIN_WORDS   = 1900
MAX_WORDS   = 2100

# ── NICHES ───────────────────────────────────────────────────
NICHES = [
    {
        "name": "geopolitics_investigative", "rpm": 11.50,
        "series": "The Archive: Geopolitical Files",
        "animation_mode": "MAP",
        "viral_search": "geopolitics investigative documentary animated history territory borders",
        "archive_search": "geopolitics investigative documentary viral history explained 2022 2023",
        "thumbnail_triggers": ["1916 BORDER","SIX DAYS","40 YEARS","CLASSIFIED MAP"],
        "seed_topics": [
            "The secret Sykes-Picot agreement drawn in 1916 by two men who never visited the Middle East",
            "The classified intelligence failure that cost a government its capital in six days in 1975",
            "A 40-year proxy war fought entirely with other countries' soldiers on their own soil",
            "The trade agreement that transferred an entire manufacturing industry to a single country in nine years",
            "The partition that was supposed to prevent war — and caused three within a decade",
            "A border dispute over 11 square kilometers that has involved 4 wars and is still unresolved today",
            "The declassified NSC memo proving the US knew about a coup 72 hours before it happened",
        ],
    },
    {
        "name": "military_secrets", "rpm": 10.50,
        "series": "The Archive: Declassified Files",
        "animation_mode": "BLUEPRINT",
        "viral_search": "military secrets declassified documentary animated investigation history",
        "archive_search": "military secrets declassified documentary viral history exposed 2022 2023",
        "thumbnail_triggers": ["STILL CLASSIFIED","22 BILLION","FOUR MORE YEARS","DECLASSIFIED NOW"],
        "seed_topics": [
            "Operation Northwoods: the declassified 1962 plan to stage attacks on American citizens for a pretext",
            "The B-52 that accidentally dropped a nuclear weapon on North Carolina in 1961 — one switch prevented detonation",
            "A black-budget program that spent $22B over 20 years and was never officially acknowledged to Congress",
            "The KH-11 satellite system could read a newspaper from orbit in 1976. It was classified until 2011.",
            "A biological weapons program officially ended in 1969 — internal documents confirm it ran until 1973",
            "Project MKUltra: 150 documented sub-projects across 80 institutions. The records were destroyed in 1973.",
            "The Venona Project: a code-breaking operation that ran for 37 years that the public learned about in 1995",
        ],
    },
    {
        "name": "military_strategies", "rpm": 10.50,
        "series": "The Archive: Strategy Files",
        "animation_mode": "MAP",
        "viral_search": "military strategy battle history documentary animated explained tactics",
        "archive_search": "military strategy battle decisive explained documentary viral 2022 2023",
        "thumbnail_triggers": ["WRONG BEACH","1100 DAYS","ONE LETTER","COST EVERYTHING"],
        "seed_topics": [
            "Operation Overlord's deception plan convinced the entire German High Command the real invasion was elsewhere",
            "The Battle of the Somme lost 60,000 men on day one. The same strategy was used the following day.",
            "A siege that lasted 1,100 days and ended not with an assault but with a single negotiated letter",
            "The general who won every engagement for three years and lost the war in a single strategic miscalculation",
            "Operation Bagration: the offensive that destroyed an entire German Army Group in 8 weeks — rarely taught",
            "The Battle of Cannae: a tactical encirclement that has been studied and replicated for 2,200 years",
            "The tactical retreat that became the decisive victory of the entire Pacific campaign in 1942",
        ],
    },
    {
        "name": "world_war_ii", "rpm": 9.50,
        "series": "The Archive: WWII Files",
        "animation_mode": "MAP",
        "viral_search": "world war 2 history documentary animated secrets explained untold stories",
        "archive_search": "world war 2 untold story history documentary viral 2022 2023",
        "thumbnail_triggers": ["TWO YEARS SHORTER","NEVER TAUGHT","MORE THAN COMBAT","EASTERN FRONT"],
        "seed_topics": [
            "The Bletchley Park codebreakers shortened the war by an estimated two years — and could never tell anyone",
            "A logistics failure in 1944 killed more American soldiers than any German offensive that autumn",
            "Operation Mincemeat: a dead man carrying false plans convinced the German High Command of the wrong invasion target",
            "The Eastern Front accounted for 80 percent of German military casualties — the Western Front learned from it",
            "The kamikaze program: 3,800 pilots, 14 percent hit rate, the documented internal arguments against it",
            "How a single decoded message about Midway changed the Pacific war's trajectory in 72 hours",
            "The 442nd Infantry Regiment: the most decorated unit in US history, fighting for a country that imprisoned their families",
        ],
    },
    {
        "name": "ancient_civilizations", "rpm": 9.50,
        "series": "The Archive: Ancient Files",
        "animation_mode": "BLUEPRINT",
        "viral_search": "ancient civilization history documentary animated mystery collapse explained",
        "archive_search": "ancient civilization mystery collapse history documentary viral 2022 2023",
        "thumbnail_triggers": ["JUST VANISHED","12000 YEARS","ALL AT ONCE","STILL UNKNOWN"],
        "seed_topics": [
            "The Indus Valley civilization had standardized weights and running water in 2600 BCE — then vanished completely",
            "Cahokia was larger than London in 1100 CE. Within 200 years, everyone had left. No one knows why.",
            "The Aksumite empire controlled the most strategically important trade route on Earth for 700 continuous years",
            "Gobekli Tepe: a 12,000-year-old stone temple built before agriculture. It upends the sequence we teach.",
            "The Bronze Age Collapse of 1200 BCE destroyed every major civilization in the eastern Mediterranean within 50 years",
            "Teotihuacan housed 125,000 people at its peak. Its rulers are unknown. Its language has never been decoded.",
            "The Harappan script has never been deciphered. 4,000 inscriptions. Zero confirmed translation. 100 years of attempts.",
        ],
    },
    {
        "name": "dark_history", "rpm": 9.50,
        "series": "The Archive: Dark History Files",
        "animation_mode": "HYBRID",
        "viral_search": "dark history atrocity documentary animated investigation truth exposed",
        "archive_search": "dark history atrocity truth exposed documentary viral 2022 2023",
        "thumbnail_triggers": ["NEVER CHARGED","STILL CLASSIFIED","NOT IN CURRICULUM","70 YEARS SEALED"],
        "seed_topics": [
            "Unit 731 conducted documented human experiments for 13 years. The majority of perpetrators were given immunity.",
            "The Holodomor: a forced famine killed between 3.5 and 7.5 million people while the government exported grain",
            "The Tuskegee Study continued for 40 years after penicillin was established as the standard treatment",
            "The Tulsa Race Massacre of 1921 was suppressed from state history books until 2020 — 99 years later",
            "King Leopold II's Congo Free State: the first internationally documented human rights crisis, 10 million deaths",
            "Project Paperclip recruited 1,600 Nazi scientists. Their files remained classified for decades after the Nuremberg trials.",
            "The Armenian Genocide was the first genocide of the 20th century. The documentation is complete. Recognition is not.",
        ],
    },
    {
        "name": "espionage_intelligence", "rpm": 10.00,
        "series": "The Archive: Intelligence Files",
        "animation_mode": "HYBRID",
        "viral_search": "espionage intelligence spy documentary animated cold war secrets investigation",
        "archive_search": "espionage intelligence spy cold war secrets documentary viral 2022 2023",
        "thumbnail_triggers": ["NINE YEARS","STILL REDACTED","BOTH SIDES KNEW","DOUBLE AGENT"],
        "seed_topics": [
            "Aldrich Ames: the CIA counterintelligence chief who was a KGB mole for 9 years. He identified 25 assets.",
            "Operation RYAN: the Soviet nuclear early-warning system that nearly triggered a first strike in November 1983",
            "The Double Cross System: every German agent in Britain during WWII was actually working for British intelligence",
            "A CIA black site operated inside a foreign friendly-government intelligence building for 11 years",
            "The ECHELON signals intelligence program monitored every transatlantic cable and satellite signal for 40 years",
            "Kim Philby: the British intelligence officer who was a Soviet agent from 1934 until his defection in 1963",
            "Operation CHAOS: the CIA's domestic surveillance program that monitored 300,000 American citizens for 7 years",
        ],
    },
    {
        "name": "islamic_civilization", "rpm": 8.50,
        "series": "The Archive: Islamic Civilization",
        "animation_mode": "HYBRID",
        "viral_search": "islamic civilization history documentary animated golden age scholarship science",
        "archive_search": "islamic golden age civilization history documentary explained viral 2022 2023",
        "thumbnail_triggers": ["300 YEARS","117000 KM","400 YEARS LATER","HOUSE OF WISDOM"],
        "seed_topics": [
            "The House of Wisdom in Baghdad preserved and translated Greek, Persian and Indian knowledge that would have been lost",
            "Al-Andalus ran the most advanced medical system in the world for 300 continuous years under Islamic rule",
            "Ibn Battuta traveled 117,000 kilometers between 1325 and 1354 — more than any person before Magellan",
            "Al-Khwarizmi's algebra manuscript was the primary mathematics textbook in European universities 400 years after his death",
            "The Abbasid postal system transmitted a message from Baghdad to Morocco in under 12 days in the 9th century",
            "Ibn al-Haytham's Book of Optics explained how vision works 600 years before Newton — the original experiment",
            "The Mansa Musa hajj of 1324 was so large it crashed the gold markets of Cairo, Medina and Mecca simultaneously",
        ],
    },
    {
        "name": "vikings", "rpm": 8.00,
        "series": "The Archive: Viking Files",
        "animation_mode": "MAP",
        "viral_search": "vikings history documentary animated raids trade routes saga explained",
        "archive_search": "vikings history documentary animated viral explained 2022 2023",
        "thumbnail_triggers": ["500 YEARS BEFORE","ELEVEN YEARS","BAGHDAD TRADE","STILL UNKNOWN"],
        "seed_topics": [
            "L'Anse aux Meadows: the confirmed Viking settlement in North America built 500 years before Columbus",
            "The Great Heathen Army occupied half of England and collected Danegeld for eleven consecutive years",
            "A Viking trade network connected Scandinavia directly to Baghdad through Russian river routes in the 9th century",
            "The Varangian Guard: Viking mercenaries who protected the Byzantine Emperor for 300 years in Constantinople",
            "Ragnar Lothbrok: what the sagas claim, what archaeology confirms, and what remains genuinely unknown",
            "The Viking settlement in Greenland survived for 400 years before disappearing — the theories remain contested",
            "How Viking longship technology enabled both ocean crossings and inland river raids from the same vessel design",
        ],
    },
    {
        "name": "dna_history", "rpm": 8.00,
        "series": "The Archive: DNA History Files",
        "animation_mode": "BLUEPRINT",
        "viral_search": "dna genetics history migration documentary animated ancestry science explained",
        "archive_search": "dna genetics ancestry history documentary viral explained 2022 2023",
        "thumbnail_triggers": ["1400 YEARS AGO","16 MILLION PEOPLE","200 YEARS WRONG","DNA PROOF"],
        "seed_topics": [
            "Ancient DNA from a Turkish burial site disproves 200 years of accepted historical narrative about population origins",
            "Every person of European descent shares a common ancestor who lived approximately 1,400 years ago",
            "The genetic signature of the Mongol expansion is still detectable in 16 million living people today",
            "DNA evidence proves a previously unknown migration route into the Americas 5,000 years earlier than the accepted date",
            "The Yamnaya expansion: a single Bronze Age population whose DNA now dominates Europe and South Asia",
            "A population that genetics says should not exist — proving two civilizations merged in ways history never recorded",
            "Ancient DNA from plague victims reveals how the Black Death spread across Europe 40 years before recorded accounts",
        ],
    },
]

# ── NICHE VOICES ─────────────────────────────────────────────
NICHE_VOICES = {
    "geopolitics_investigative": ["en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-RyanNeural","en-US-BrianNeural"],
    "military_secrets":          ["en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural","en-GB-RyanNeural"],
    "military_strategies":       ["en-GB-RyanNeural","en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
    "world_war_ii":              ["en-GB-ThomasNeural","en-US-BrianNeural","en-GB-RyanNeural","en-US-ChristopherNeural"],
    "ancient_civilizations":     ["en-US-ChristopherNeural","en-GB-ThomasNeural","en-GB-RyanNeural","en-US-BrianNeural"],
    "dark_history":              ["en-GB-ThomasNeural","en-US-BrianNeural","en-US-ChristopherNeural","en-GB-RyanNeural"],
    "espionage_intelligence":    ["en-US-ChristopherNeural","en-GB-ThomasNeural","en-US-BrianNeural","en-GB-RyanNeural"],
    "islamic_civilization":      ["en-GB-ThomasNeural","en-GB-RyanNeural","en-US-ChristopherNeural","en-US-BrianNeural"],
    "vikings":                   ["en-GB-RyanNeural","en-US-BrianNeural","en-GB-ThomasNeural","en-US-ChristopherNeural"],
    "dna_history":               ["en-US-ChristopherNeural","en-GB-ThomasNeural","en-US-BrianNeural","en-GB-RyanNeural"],
}

GUARANTEED_VOICES = [
    "en-GB-ThomasNeural",
    "en-GB-RyanNeural",
    "en-US-BrianNeural",
    "en-US-ChristopherNeural",
    "en-US-AndrewNeural",
    "en-US-EricNeural",
    "en-US-GuyNeural",
    "en-US-SteffanNeural",
]

# ── ANIMATION MODES ──────────────────────────────────────────
ANIMATION_MODES = {
    "MAP": {
        "palette": {"bg":(18,12,5),"primary":(220,190,140),"accent":(200,120,30),"secondary":(160,130,80)},
        "style": "parchment-warm — border draws, territory reveals, troop movements, trade routes",
        "use_for": "geopolitics, military strategy, wwii, vikings, empires, trade networks",
    },
    "BLUEPRINT": {
        "palette": {"bg":(4,8,20),"primary":(100,180,255),"accent":(0,220,255),"secondary":(60,120,180)},
        "style": "cool technical — measurement grids, excavation layers, document reveals, data visualization",
        "use_for": "ancient civilizations, military secrets, dna history, archaeology, classified documents",
    },
    "HYBRID": {
        "palette": {"bg":(8,5,15),"primary":(200,180,220),"accent":(150,50,200),"secondary":(100,80,140)},
        "style": "cinematic dark — combines map reveals with document/data layers for investigative content",
        "use_for": "dark history, espionage, intelligence, investigative geopolitics, crossover topics",
    },
}

# ── DREAD TRIGGERS ───────────────────────────────────────────
DREAD_TRIGGERS = {
    "erasure":       "What was built, achieved, or documented — and then deliberately removed from the record.",
    "scale":         "The exact numbers. Then make each number a specific human being or consequence.",
    "institutional": "The trusted institution — the government, the archive, the textbook — was the weapon.",
    "duration":      "Not decades — exact years, exact days. 1,100 days. 37 years. 400 years.",
    "reversal":      "Everything in the historical record was the cover story. The evidence survived anyway.",
    "proximity":     "This decision was made by one person. Its effects are still running today.",
    "competence":    "The sophistication. The patience. The cold architecture of how it was concealed.",
    "invisibility":  "It was hidden because it looked exactly like normal governance.",
}

# ── STAGE TARGETS (15-minute structure) ──────────────────────
STAGE_TARGETS = {1:120, 2:200, 3:280, 4:480, 5:150, 6:520, 7:150}

# ── AI PROVIDERS ─────────────────────────────────────────────
CEREBRAS_KEY   = os.environ.get("CEREBRAS_API_KEY","")
SAMBANOVA_KEY  = os.environ.get("SAMBANOVA_API_KEY","")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY","")
GEMINI_KEY_2   = os.environ.get("GEMINI_API_KEY_2","")
GROQ_KEY       = os.environ.get("GROQ_API_KEY","")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY","")
COHERE_KEY     = os.environ.get("COHERE_API_KEY","")
MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY","")

# ── YOUTUBE SECRETS (Ch4) ────────────────────────────────────
YT_CLIENT_ID     = os.environ.get("ARCHIVE_YT_CLIENT_ID","")
YT_CLIENT_SECRET = os.environ.get("ARCHIVE_YT_CLIENT_SECRET","")
YT_REFRESH_TOKEN = os.environ.get("ARCHIVE_YT_REFRESH_TOKEN","")

# ── TELEGRAM ─────────────────────────────────────────────────
TG_TOKEN   = os.environ.get("TELEGRAM_TOKEN","")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","")

# ── PIXABAY / PEXELS ─────────────────────────────────────────
PIXABAY_KEY = os.environ.get("PIXABAY_KEY","")
PEXELS_KEY  = os.environ.get("PEXELS_API_KEY","")

MAX_CHUNK = 500  # chars per TTS chunk — keeps GitHub Actions edge-tts reliable

def log(msg):
    print(msg, flush=True)

def tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=15)
    except Exception as e:
        log(f"  TG error: {e}")

def strip_md(text):
    if not text: return ""
    text = re.sub(r"[#*_`\[\]{}|<>]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def get_media_duration(path):
    try:
        r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
            "-of","csv=p=0",str(path)], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception: pass
    return 0.0

def run_ffmpeg(cmd, label="ffmpeg", timeout=300):
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8","ignore")[-200:]
            log(f"  {label}: exit {result.returncode} — {err}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log(f"  {label}: timed out after {timeout}s")
        return False
    except Exception as e:
        log(f"  {label}: error — {e}")
        return False

# ── AI PROVIDER CHAIN ─────────────────────────────────────────
import requests

def _call_cerebras(prompt, tokens=2000, temp=0.85):
    if not CEREBRAS_KEY: return None
    for model in ["llama-3.3-70b","llama3.3-70b","llama-3.1-70b","llama3.1-70b"]:
        try:
            r = requests.post("https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization":f"Bearer {CEREBRAS_KEY}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],
                      "max_tokens":min(tokens,9000),"temperature":temp}, timeout=60)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt: log(f"  OK Cerebras ({model[:12]})"); return txt
            else:
                log(f"  Cerebras {model}: {r.status_code} (wrong model name, trying next)")
        except Exception as e:
            log(f"  Cerebras {model}: {e}")
    return None

def _call_sambanova(prompt, tokens=2000, temp=0.85):
    if not SAMBANOVA_KEY: return None
    try:
        r = requests.post("https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization":f"Bearer {SAMBANOVA_KEY}","Content-Type":"application/json"},
            json={"model":"Meta-Llama-3.3-70B-Instruct","messages":[{"role":"user","content":prompt}],
                  "max_tokens":tokens,"temperature":temp}, timeout=60)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK SambaNova (3.3)"); return txt
        else:
            log(f"  SambaNova {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"  SambaNova: {e}")
    return None

def _call_gemini(prompt, tokens=2000, temp=0.85):
    for key_name, key in [("primary", GEMINI_KEY), ("backup", GEMINI_KEY_2)]:
        if not key: continue
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"maxOutputTokens":tokens,"temperature":temp},
                      "safetySettings":[{"category":c,"threshold":"BLOCK_NONE"} for c in [
                          "HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH",
                          "HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]},
                timeout=90)
            if r.status_code == 200:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if txt: log(f"  OK Gemini ({key_name})"); return txt
            elif r.status_code == 429:
                log(f"  Gemini ({key_name}) quota exhausted — resets midnight PT")
            else:
                log(f"  Gemini ({key_name}): {r.status_code}")
        except Exception as e:
            log(f"  Gemini ({key_name}): {e}")
    return None

def _call_groq(prompt, tokens=2000, temp=0.85):
    if not GROQ_KEY: return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                  "max_tokens":min(tokens,4800),"temperature":temp}, timeout=60)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK Groq"); return txt
        else:
            log(f"  Groq {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"  Groq: {e}")
    return None

def _call_openrouter(prompt, tokens=2000, temp=0.85):
    if not OPENROUTER_KEY: return None
    for model in [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-2-9b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
    ]:
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"user","content":prompt}],
                      "max_tokens":tokens,"temperature":temp}, timeout=60)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt: log(f"  OK OpenRouter ({model.split('/')[-1][:20]})"); return txt
            else:
                log(f"  OpenRouter {model.split('/')[-1][:20]}: {r.status_code}")
        except Exception as e:
            log(f"  OpenRouter {model}: {e}")
    return None

def _call_cohere(prompt, tokens=2000, temp=0.85):
    if not COHERE_KEY: return None
    try:
        r = requests.post("https://api.cohere.ai/v1/generate",
            headers={"Authorization":f"Bearer {COHERE_KEY}","Content-Type":"application/json"},
            json={"model":"command-r-08-2024","prompt":prompt,"max_tokens":tokens,"temperature":temp}, timeout=60)
        if r.status_code == 200:
            txt = r.json().get("generations",[{}])[0].get("text","").strip()
            if txt: log(f"  OK Cohere"); return txt
        else:
            log(f"  Cohere {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"  Cohere: {e}")
    return None

def _call_mistral(prompt, tokens=2000, temp=0.85):
    if not MISTRAL_KEY: return None
    try:
        r = requests.post("https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization":f"Bearer {MISTRAL_KEY}","Content-Type":"application/json"},
            json={"model":"mistral-small-latest","messages":[{"role":"user","content":prompt}],
                  "max_tokens":tokens,"temperature":temp}, timeout=60)
        if r.status_code == 200:
            txt = r.json()["choices"][0]["message"]["content"].strip()
            if txt: log(f"  OK Mistral"); return txt
        else:
            log(f"  Mistral {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"  Mistral: {e}")
    return None

def ai(prompt, tokens=2000, temp=0.85, prefer=None):
    """7-provider chain — Cerebras first, Mistral last."""
    log(f"  Waiting 10s before next provider...")
    providers = [
        ("cerebras",   lambda: _call_cerebras(prompt, tokens, temp)),
        ("sambanova",  lambda: _call_sambanova(prompt, tokens, temp)),
        ("gemini",     lambda: _call_gemini(prompt, tokens, temp)),
        ("groq",       lambda: _call_groq(prompt, tokens, temp)),
        ("openrouter", lambda: _call_openrouter(prompt, tokens, temp)),
        ("cohere",     lambda: _call_cohere(prompt, tokens, temp)),
        ("mistral",    lambda: _call_mistral(prompt, tokens, temp)),
    ]
    if prefer:
        providers = sorted(providers, key=lambda x: 0 if x[0]==prefer else 1)
    for name, fn in providers:
        result = fn()
        if result and len(result.split()) > 20: return result
        time.sleep(10)
    return None

# ── NICHE ROTATION ────────────────────────────────────────────
STATE_FILE = WORK_DIR / "archive_state.json"

def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception: pass
    return {"niche_idx":0,"episode":0,"voice_history":{},"perf":{}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_niche(state):
    idx = state.get("niche_idx", 0) % len(NICHES)
    niche = NICHES[idx]
    state["niche_idx"] = (idx + 1) % len(NICHES)
    return niche

# ── TOPIC SELECTION ───────────────────────────────────────────
def get_topic(niche, intel_file=None):
    seed = random.choice(niche["seed_topics"])
    prompt = (
        f"You are a researcher for a dark history/geopolitics documentary channel.\n"
        f"Niche: {niche['name']} | Series: {niche['series']}\n"
        f"Seed topic: {seed}\n\n"
        f"Generate ONE compelling documentary topic for a 15-minute video.\n"
        f"Requirements:\n"
        f"- Must be historically documented, not speculative\n"
        f"- Must have a specific angle (not 'history of X' but 'the specific thing about X nobody mentions')\n"
        f"- Must connect to a current relevance or ongoing implication\n"
        f"- 1-2 sentences maximum\n"
        f"Return ONLY the topic. No preamble."
    )
    result = ai(prompt, tokens=200, temp=0.9)
    return result.strip() if result else seed

# ── SCRIPT GENERATION ─────────────────────────────────────────
def generate_script(niche, topic, episode):
    st = STAGE_TARGETS
    mode = niche.get("animation_mode", "MAP")
    mode_desc = ANIMATION_MODES[mode]["style"]

    prompt = f"""You are writing a 15-minute dark history/geopolitics documentary script for The Archive.

CHANNEL: The Archive | NICHE: {niche["series"]} | ANIMATION: {mode} mode ({mode_desc})
EPISODE TOPIC: {topic}
EPISODE NUMBER: {episode}

TONE AND STYLE — NON-NEGOTIABLE:
- DARK DOCUMENTARY. Every sentence carries weight. No filler. No padding.
- Dark psychological humor is permitted: the kind that makes viewers laugh then feel disturbed they laughed.
- Each stage must be darker than the last. Build dread deliberately.
- The viewer must feel they discovered something others do not know.
- Pacing: short sentences at revelation moments. They hit harder.

CRAVEABILITY TRIGGERS — use minimum 3 per script:
1. The statistic that sounds impossible but is verifiably documented.
2. The name everyone knows connected to something they never knew.
3. The system still running right now — not historical, not past tense.
4. The evidence that institutions tried to suppress or have never acknowledged.
5. The detail so specific it absolutely has to be true.
6. The uncomfortable implication left open in the final 30 seconds.
7. The question deliberately raised but not fully answered.

TITLE REQUIREMENTS — NON-NEGOTIABLE:
No generic YouTube titles. The title should make someone screenshot it and send to a friend.
TITLE FORMULAS: "[Number] [People/Years/Days] [Dark Specific Thing] Nobody Talked About"
"The [Institution] Knew. They Did It Anyway. Here Is The File."
"[System] Ran [Dark Operation] For [Duration]. Here Is The Evidence."
FORBIDDEN: Shocking, Incredible, Amazing, Unbelievable, Mind-Blowing

SEVEN-STAGE STRUCTURE — write continuously, no labels, no headers:

STAGE 1 — COLD OPEN ({st[1]} words)
First sentence: a specific documented number, date, or duration that immediately anchors scale.
Second sentence: places the viewer somewhere specific and recognizable.
Third sentence: opens a loop that the entire script must close.
Forbidden: "welcome back", "today we", "in this video", "join me"
Trigger: SCALE (s1) → PROXIMITY (s2) → unresolved loop (s3)

STAGE 2 — THE BEFORE ({st[2]} words)
Establish what existed before the event, decision, or system under investigation.
Specific details. Make the viewer understand what was normal. Make them care.
Final sentence: the first quiet signal that something is about to change permanently.
Forbidden: "little did they know", "nobody could have predicted"
Trigger: NORMALITY (s1-s3) → DURATION (s4-s5) → quiet wrongness (final)

STAGE 3 — FIRST SIGNALS ({st[3]} words)
Early documented anomalies. Each one individually explainable. One per sentence.
Start with the smallest. Each one more specific than the last.
Forbidden: "suddenly", "without warning", "shockingly"
Trigger: INVISIBILITY (s1) → DURATION (s3) → SCALE (s5) → INSTITUTIONAL (s7)

STAGE 4 — ESCALATION ({st[4]} words)
The documented record accumulates. Specific sources, dates, figures.
Each paragraph reveals another layer. The architecture of what actually happened.
This is the longest section. Make every sentence earn its place.
Forbidden: passive voice on the key facts
Trigger: DETAIL (para 1) → COMPETENCE (para 2) → COST (para 3) → INSTITUTIONAL (para 4)

STAGE 5 — FALSE RESOLUTION ({st[5]} words)
The official version. What was announced, published, or declared.
One short sentence shows the gap between the official record and what Stage 4 documented.
This is the breath before the real reveal.
Trigger: NORMALITY → REVERSAL (final sentence)

STAGE 6 — REAL REVEAL ({st[6]} words)
The complete documented picture assembled.
One paragraph per major finding. Ordered by impact — most significant last.
Cite specific document types, declassification dates, file references where possible.
Forbidden: "in conclusion", "to summarize", "as we have seen"
Trigger: REVERSAL (para 1) → DETAIL (para 2-4) → COST (para 5) → INSTITUTIONAL (para 6)

STAGE 7 — IMPLICATION AND CTA ({st[7]} words)
What the documented record implies for right now — not historically, currently.
The question that remains open. The file that is still classified. The system still running.
Subscribe CTA at emotional peak — framed as continued investigation.

RULES:
1. Maximum 13 words per sentence.
2. Zero markdown — no asterisks, hashtags, bold, bullets, headers.
3. No stage labels in the output.
4. Every claim must sound like it comes from a real document or record.
5. Total: {MIN_WORDS} to {MAX_WORDS} words. HARD LIMIT: never exceed {MAX_WORDS} words.

After the script, on a new line write exactly:
---METADATA---
TITLE: [your best dark documentary title]
THUMBNAIL: [3 words ALL CAPS — NUMBER+NOUN format]
TAGS: [10 comma-separated tags]
"""
    result = ai(prompt, tokens=8000, temp=0.85)
    return result

# ── SCRIPT PARSING ────────────────────────────────────────────
def parse_script_output(raw, niche):
    if not raw: return None, None, None, None, []
    parts  = raw.split("---METADATA---")
    script = strip_md(parts[0].strip()) if parts else ""
    meta   = parts[1].strip() if len(parts) > 1 else ""

    title = None
    thumb = None
    tags  = []
    for line in meta.split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"): title = line[6:].strip()
        elif line.startswith("THUMBNAIL:"): thumb = line[10:].strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip() for t in line[5:].split(",") if t.strip()]

    if not title:
        title = f"{niche['series']} — Episode Investigation"
    if not thumb:
        thumb = random.choice(niche["thumbnail_triggers"])

    return script, title, thumb, tags

# ── SCRIPT SCORING ────────────────────────────────────────────
def score_script(script, wc, violations):
    if not script: return 0.0, ["Empty script"]
    score  = 5.0
    issues = []

    if wc >= MIN_WORDS:      score += 2.8
    elif wc >= int(MIN_WORDS*0.8): score += 0.8
    else: score -= 2.0; issues.append(f"Under word target: {wc}w")

    if violations == 0:   score += 2.2
    elif violations <= 2: score += 0.8
    else: score -= 1.5; issues.append(f"{violations} markdown violations")

    words = script.split()
    total = len(words)
    if total >= 400:
        hook_signals = ["subscribe","coming up","what happens","revealed","documented",
                        "the evidence","what comes next","still classified","still running"]
        seg30 = " ".join(words[int(total*0.25):int(total*0.35)]).lower()
        seg60 = " ".join(words[int(total*0.55):int(total*0.65)]).lower()
        if not any(w in seg30 for w in hook_signals):
            score -= 0.4; issues.append("Missing 30% retention hook")
        h60 = sum(1 for w in hook_signals if w in seg60)
        if h60 < 2: score -= 0.8; issues.append("Weak 60% peak hook")
        elif h60 >= 3: score += 0.3
        if "subscribe" not in " ".join(words[-60:]).lower():
            score -= 0.3; issues.append("Missing subscribe CTA in final 60 words")

    return min(round(score, 1), 10.0), issues

# ── TITLE SCORING ─────────────────────────────────────────────
def score_title(title):
    score = 5.0
    bad_words = ["shocking","incredible","amazing","unbelievable","mind-blowing","you won't believe"]
    for bad in bad_words:
        if bad in title.lower(): score -= 1.0
    if any(c.isdigit() for c in title): score += 1.5
    if len(title) < 50: score += 0.5
    if "?" in title or ":" in title: score += 0.5
    return min(round(score,1), 10.0)

# ── CTA INJECTION ─────────────────────────────────────────────
def inject_ctas(script, niche_name):
    ctas = {
        "geopolitics_investigative": ["Subscribe to The Archive for more declassified geopolitical investigations.",
                                       "Follow The Archive — new investigative geopolitics every week.",
                                       "Subscribe to continue following this investigation with The Archive."],
        "military_secrets":          ["Subscribe to The Archive for more declassified military files.",
                                       "The Archive investigates declassified programs every week — subscribe.",
                                       "Subscribe for more documented military secrets at The Archive."],
        "military_strategies":       ["Subscribe to The Archive for more documented battle strategy analysis.",
                                       "Follow The Archive for weekly military history investigations.",
                                       "Subscribe to The Archive — new documented strategy files every week."],
        "world_war_ii":              ["Subscribe to The Archive for more untold WWII investigations.",
                                       "Follow The Archive for documented WWII stories nobody teaches.",
                                       "Subscribe for more verified WWII history at The Archive."],
        "ancient_civilizations":     ["Subscribe to The Archive for more ancient civilization investigations.",
                                       "Follow The Archive — new archaeological investigation every week.",
                                       "Subscribe for more documented ancient history at The Archive."],
        "dark_history":              ["Subscribe to The Archive for more documented dark history investigations.",
                                       "Follow The Archive — the suppressed historical record every week.",
                                       "Subscribe for more verified dark history files at The Archive."],
        "espionage_intelligence":    ["Subscribe to The Archive for more declassified intelligence investigations.",
                                       "Follow The Archive — new intelligence history files every week.",
                                       "Subscribe for more documented espionage at The Archive."],
        "islamic_civilization":      ["Subscribe to The Archive for more Islamic civilization history.",
                                       "Follow The Archive — documented Islamic Golden Age every week.",
                                       "Subscribe for more verified Islamic history investigations at The Archive."],
        "vikings":                   ["Subscribe to The Archive for more documented Viking history.",
                                       "Follow The Archive — new Viking investigation every week.",
                                       "Subscribe for more verified Viking files at The Archive."],
        "dna_history":               ["Subscribe to The Archive for more DNA history investigations.",
                                       "Follow The Archive — genetics meets history every week.",
                                       "Subscribe for more documented DNA ancestry investigations at The Archive."],
    }
    cta_list = ctas.get(niche_name, ["Subscribe to The Archive for more documented historical investigations.","Follow The Archive for weekly history investigations.","Subscribe for more verified historical files at The Archive."])

    words = script.split()
    total = len(words)
    if total < 400: return script

    marks = [int(total*0.30), int(total*0.60), int(total*0.80)]
    result = script
    inserted = 0

    for i, mark in enumerate(marks):
        cta = cta_list[i % len(cta_list)]
        target = mark + inserted
        all_w  = result.split()
        if target >= len(all_w): continue
        char_pos = len(" ".join(all_w[:target]))
        period   = result.find(". ", char_pos)
        if period == -1: continue
        insert_at = period + 2
        result = result[:insert_at] + cta + " " + result[insert_at:]
        inserted += len(cta.split()) + 1

    if "subscribe" not in " ".join(result.split()[-60:]).lower():
        result = result.rstrip() + " Subscribe to The Archive for more documented historical investigations."
    return result

# ── TTS AUDIO ─────────────────────────────────────────────────
def check_audio_quality(mp3_path, dur_expected):
    try:
        sz = Path(mp3_path).stat().st_size
        if sz < 200000: log(f"  Quality FAIL: {sz}b — file too small"); return False
        r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
            "-of","csv=p=0",str(mp3_path)], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            actual = float(r.stdout.strip())
            if actual < dur_expected * 0.20:
                log(f"  Quality FAIL: {actual:.0f}s vs {dur_expected:.0f}s expected"); return False
            log(f"  Quality OK: {actual:.0f}s ({actual/60:.1f}min)"); return True
    except Exception: pass
    return False

async def _tts(text, voice, path):
    import edge_tts
    chunks = []
    current = ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if len(current) + len(sent) > MAX_CHUNK and current:
            chunks.append(current.strip())
            current = sent
        else:
            current += " " + sent
    if current.strip(): chunks.append(current.strip())

    parts = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        part = str(WORK_DIR / f"chunk_{i:03d}.mp3")
        c = edge_tts.Communicate(chunk, voice, rate="-8%")
        await asyncio.wait_for(c.save(part), timeout=90)
        if Path(part).exists() and Path(part).stat().st_size > 1000:
            parts.append(part)
        else:
            log(f"    Chunk {i} failed")

    if not parts: raise RuntimeError("All chunks failed")
    if len(parts) == 1:
        shutil.copy(parts[0], path); return

    concat_file = str(WORK_DIR / "concat.txt")
    with open(concat_file, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    run_ffmpeg(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,
                "-c:a","libmp3lame","-q:a","2",path], "concat-audio", 120)

def run_stage3_audio(script_clean, voice_id, niche_name):
    _words = script_clean.split()
    if len(_words) > MAX_WORDS:
        script_clean = " ".join(_words[:MAX_WORDS])
        log(f"  Script truncated to {MAX_WORDS}w for TTS")

    wc           = len(script_clean.split())
    dur_expected = min((wc / 125.0) * 60.0, 900.0)

    preferred = NICHE_VOICES.get(niche_name, GUARANTEED_VOICES[:4])
    voice_queue = preferred + [v for v in GUARANTEED_VOICES if v not in preferred]

    audio_path = str(WORK_DIR / "audio.mp3")
    for _vi, v in enumerate(voice_queue[:12]):
        if _vi > 0: time.sleep(3)  # avoid edge-tts rate limit
        log(f"  Trying: {v}")
        try:
            asyncio.run(asyncio.wait_for(_tts(script_clean, v, audio_path), timeout=180))
            if not Path(audio_path).exists(): continue
            if not check_audio_quality(audio_path, dur_expected): continue
            log(f"  ACCEPTED: {v}")
            # Apply dark cinematic EQ
            eq_path = str(WORK_DIR / "audio_eq.mp3")
            af = ('"equalizer=f=60:width_type=o:width=2:g=4,"'
                  '"equalizer=f=250:width_type=o:width=2:g=2,"'
                  '"equalizer=f=3000:width_type=o:width=2:g=-1,"'
                  '"equalizer=f=8000:width_type=o:width=2:g=-2,"'
                  '"aecho=0.85:0.88:60:0.3,"'
                  '"acompressor=threshold=-20dB:ratio=3:attack=3:release=100:makeup=3dB,"'
                  '"loudnorm=I=-16:LRA=11:TP=-1.5"')
            if run_ffmpeg(["ffmpeg","-y","-i",audio_path,"-af",af,"-c:a","libmp3lame","-q:a","2",eq_path],"audio-eq",180):
                shutil.copy(eq_path, audio_path)
            return audio_path, get_media_duration(audio_path), None, v
        except Exception as e:
            log(f"  {v} err: {e}")
    raise RuntimeError("All voices failed — Stage 3 Audio")

# ── VIDEO ASSEMBLY (MAP + BLUEPRINT animation) ────────────────
def assemble_video(niche, audio_path, duration, topic):
    mode    = niche.get("animation_mode","MAP")
    palette = ANIMATION_MODES[mode]["palette"]
    W, H    = 1920, 1080

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log("  PIL not available — returning audio-only video")
        out = str(WORK_DIR / "final.mp4")
        run_ffmpeg(["ffmpeg","-y","-i",audio_path,"-vf",
            f"color=c=black:size={W}x{H}:rate=24","-shortest","-c:v","libx264","-c:a","aac",out], "video", 600)
        return out

    frames_dir = WORK_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)

    n_frames = max(1, int(duration * 24))
    bg_color = tuple(palette["bg"])
    acc_color = tuple(palette["accent"])
    pri_color = tuple(palette["primary"])

    for i in range(min(n_frames, 72000)):  # cap at 50min of frames
        img  = Image.new("RGB", (W,H), bg_color)
        draw = ImageDraw.Draw(img)
        t    = i / max(n_frames, 1)

        if mode == "MAP":
            # Parchment warm overlay with animated border reveals
            overlay = Image.new("RGBA", (W,H), (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            # Animated territory border line
            progress = min(t * 3.0, 1.0)
            x_end = int(W * progress)
            od.line([(0, H//2),(x_end, H//2)], fill=acc_color+(180,), width=3)
            # Corner frame elements
            for corner_x, corner_y in [(50,50),(W-50,50),(50,H-50),(W-50,H-50)]:
                od.rectangle([corner_x-20,corner_y-20,corner_x+20,corner_y+20],
                              outline=acc_color+(100,), width=2)
            img.paste(Image.fromarray([[bg_color]*W]*H), (0,0))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        elif mode == "BLUEPRINT":
            # Cool technical grid
            grid_alpha = int(30 + 20 * abs((t % 1.0) - 0.5))
            for gx in range(0, W, 80):
                draw.line([(gx,0),(gx,H)], fill=tuple(list(acc_color[:3])+[grid_alpha])[:3], width=1)
            for gy in range(0, H, 80):
                draw.line([(0,gy),(W,gy)], fill=tuple(list(acc_color[:3])+[grid_alpha])[:3], width=1)
            # Measurement marks
            for mx in range(0, W, 160):
                draw.line([(mx, H//2-10),(mx, H//2+10)], fill=pri_color, width=2)

        else:  # HYBRID
            # Dark cinematic with subtle elements
            pulse = int(10 + 8 * abs((t*2 % 1.0) - 0.5))
            draw.ellipse([W//2-pulse, H//2-pulse, W//2+pulse, H//2+pulse],
                         outline=acc_color, width=2)

        img.save(str(frames_dir / f"frame_{i:06d}.jpg"), quality=85)

    # Encode frames to video
    temp_video = str(WORK_DIR / "temp_video.mp4")
    run_ffmpeg(["ffmpeg","-y","-r","24","-i",str(frames_dir/"frame_%06d.jpg"),
                "-vf","scale=1920:1080","-c:v","libx264","-preset","ultrafast",
                "-pix_fmt","yuv420p",temp_video], "frames-to-video", 600)

    # Mux with audio
    final = str(WORK_DIR / "final.mp4")
    run_ffmpeg(["ffmpeg","-y","-i",temp_video,"-i",audio_path,
                "-c:v","copy","-c:a","aac","-shortest",final], "mux-av", 120)

    # Cleanup frames
    shutil.rmtree(str(frames_dir), ignore_errors=True)
    return final

# ── THUMBNAIL ─────────────────────────────────────────────────
def generate_thumbnail(niche, topic, title, thumb_text):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log("  PIL not available — skipping thumbnail"); return None

    W, H  = 1280, 720
    mode  = niche.get("animation_mode","MAP")
    pal   = ANIMATION_MODES[mode]["palette"]
    img   = Image.new("RGB", (W,H), tuple(pal["bg"]))
    draw  = ImageDraw.Draw(img)

    # Dark red accent bar
    draw.rectangle([0, H-8, W, H], fill=(200,0,0))
    draw.rectangle([0, 0, 8, H], fill=(200,0,0))

    # Thumbnail text (3 words, blood red)
    words = thumb_text.strip().upper().split()[:3]
    display = " ".join(words) if words else "CLASSIFIED FILE"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font

    # Main text
    bbox = draw.textbbox((0,0), display, font=font)
    x = (W - (bbox[2]-bbox[0])) // 2
    y = (H - (bbox[3]-bbox[1])) // 2 - 40
    draw.text((x+3,y+3), display, font=font, fill=(0,0,0))
    draw.text((x,y), display, font=font, fill=(255,255,255))

    # Series name
    series = niche.get("series","The Archive")[:40]
    draw.text((20, H-55), series, font=font_sm, fill=(200,0,0))

    path = str(WORK_DIR / "thumbnail.jpg")
    img.save(path, quality=95)
    return path

# ── YOUTUBE UPLOAD ────────────────────────────────────────────
def get_yt_token():
    import urllib.request, urllib.parse
    if not YT_CLIENT_ID or not YT_CLIENT_SECRET or not YT_REFRESH_TOKEN:
        raise RuntimeError("Missing YouTube credentials (ARCHIVE_YT_*)")
    data = urllib.parse.urlencode({
        "client_id":YT_CLIENT_ID,"client_secret":YT_CLIENT_SECRET,
        "refresh_token":YT_REFRESH_TOKEN,"grant_type":"refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token",
        data=data, headers={"Content-Type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["access_token"]

def upload_yt(video_path, title, description, tags, thumb_path=None):
    token = get_yt_token()
    import urllib.request, urllib.parse

    meta = json.dumps({
        "snippet": {"title":title[:100],"description":description,
                    "tags":tags[:30],"categoryId":"27","defaultLanguage":"en"},
        "status":  {"privacyStatus":"public","selfDeclaredMadeForKids":False}
    }).encode()

    boundary = "boundary_archive_upload"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
            + meta + f"\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n".encode()
            + open(video_path,"rb").read() + f"\r\n--{boundary}--".encode())

    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status",
        data=body,
        headers={"Authorization":f"Bearer {token}",
                 "Content-Type":f"multipart/related; boundary={boundary}",
                 "Content-Length":str(len(body))})
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
        vid_id = result.get("id","")
        log(f"  Uploaded: https://youtube.com/watch?v={vid_id}")
        if thumb_path and vid_id:
            try:
                thumb_data = open(thumb_path,"rb").read()
                treq = urllib.request.Request(
                    f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid_id}",
                    data=thumb_data,
                    headers={"Authorization":f"Bearer {token}","Content-Type":"image/jpeg"})
                urllib.request.urlopen(treq, timeout=60)
                log("  Thumbnail uploaded")
            except Exception as e:
                log(f"  Thumbnail upload failed: {e}")
        return vid_id

# ── PENDING STATE ─────────────────────────────────────────────
PENDING_FILE = WORK_DIR / "pending_upload.json"

def save_pending(data):
    PENDING_FILE.write_text(json.dumps(data, indent=2))

def load_pending():
    if PENDING_FILE.exists():
        return json.loads(PENDING_FILE.read_text())
    return None

def clear_pending():
    if PENDING_FILE.exists(): PENDING_FILE.unlink()

# ── MAIN ──────────────────────────────────────────────────────
def main():
    log("=" * 65)
    log(f"THE ARCHIVE v1.0 — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    log("=" * 65)

    phase = os.environ.get("PIPELINE_PHASE","generate").lower()
    log(f"Phase: {phase.upper()}")

    # ── UPLOAD PHASE ──────────────────────────────────────────
    if phase == "upload":
        pending = load_pending()
        if not pending:
            tg("⚠️ Archive Upload: no pending video found. Generate first.")
            return
        try:
            vid_id = upload_yt(
                pending["video_path"], pending["title"],
                pending["description"], pending["tags"],
                pending.get("thumb_path"))
            clear_pending()
            tg(f"✅ The Archive LIVE\n\n<b>{pending['title']}</b>\nhttps://youtube.com/watch?v={vid_id}")
        except Exception as e:
            tg(f"❌ Archive Upload FAILED: {e}")
            raise
        return

    # ── GENERATE PHASE ────────────────────────────────────────
    state   = load_state()
    niche   = get_niche(state)
    episode = state.get("episode", 0) + 1
    state["episode"] = episode
    save_state(state)

    log(f"\nNiche: {niche['name']} | Mode: {niche['animation_mode']} | Episode: {episode}")

    # Stage 1: Topic
    log("\nSTAGE 1: Topic Selection")
    topic = get_topic(niche)
    log(f"  Topic: {topic}")

    # Stage 2: Script
    log("\nSTAGE 2: Script Generation")
    raw   = generate_script(niche, topic, episode)
    if not raw:
        tg("❌ Archive: Script generation failed — all providers exhausted")
        sys.exit(1)

    script, title, thumb_text, tags = parse_script_output(raw, niche)
    if not script:
        tg("❌ Archive: Script parsing failed")
        sys.exit(1)

    # Enforce word count
    words = script.split()
    wc = len(words)
    log(f"  Script: {wc}w")

    # Expand if short
    exp_round = 0
    while wc < MIN_WORDS and wc <= MAX_WORDS and exp_round < 3:
        if wc > MAX_WORDS: break
        exp_round += 1
        deficit = MIN_WORDS - wc
        log(f"  {wc}w short — expanding round {exp_round}...")
        ep = (f"This documentary script is {wc} words. Needs {MIN_WORDS} minimum.\n"
              f"Expand Stage 4 (Escalation) and Stage 6 (Real Reveal) only.\n"
              f"Add specific documented evidence, exact dates, exact figures.\n"
              f"Max 13 words per sentence. Zero markdown.\n"
              f"Return COMPLETE expanded script:\n\n" + script[:3000])
        raw2 = ai(ep, tokens=7000, prefer="gemini")
        if raw2:
            s2 = strip_md(raw2)
            s2_wc = len(s2.split())
            if s2_wc > wc:
                if s2_wc > MAX_WORDS:
                    s2 = " ".join(s2.split()[:MAX_WORDS])
                    s2_wc = MAX_WORDS
                script = s2; wc = s2_wc
                log(f"  Expanded to {wc}w")
        else:
            break

    # Hard truncate
    if wc > MAX_WORDS:
        script = " ".join(script.split()[:MAX_WORDS])
        wc = len(script.split())
        log(f"  Truncated to {wc}w")

    violations = len(re.findall(r"[#*_`\[\]{}<>\\]", script))
    score, issues = score_script(script, wc, violations)
    log(f"  Score: {score}/10 | {wc}w | {violations} MD | {issues}")

    # Score gate
    FINAL_GATE = 6.9
    if score < FINAL_GATE:
        tg(f"⚠️ Archive: Script score {score}/10 below gate {FINAL_GATE} — skipping")
        sys.exit(0)

    # Inject CTAs
    script = inject_ctas(script, niche["name"])

    # Send approval
    preview = " ".join(script.split()[:80])
    tg(f"📖 Archive Script Ready: {score}/10\n\n<b>{title}</b>\n{preview}...")

    # Stage 3: Audio
    log("\nSTAGE 3: Audio")
    try:
        audio_path, duration, _, voice = run_stage3_audio(script, None, niche["name"])
        log(f"  Audio: {duration:.0f}s ({duration/60:.1f}min) | Voice: {voice}")
    except Exception as e:
        tg(f"❌ Archive Stage 3 FAILED: {e}")
        sys.exit(1)

    # Stage 4: Video
    log("\nSTAGE 4: Video Assembly")
    try:
        video_path = assemble_video(niche, audio_path, duration, topic)
        log(f"  Video: {video_path}")
    except Exception as e:
        tg(f"❌ Archive Stage 4 FAILED: {e}")
        sys.exit(1)

    # Stage 5: Thumbnail
    log("\nSTAGE 5: Thumbnail")
    thumb_path = generate_thumbnail(niche, topic, title, thumb_text)

    # Build description
    description = (
        f"{title}\n\n"
        f"The Archive investigates the documented historical record — the files, the transcripts, "
        f"the declassified evidence, and the implications nobody discusses.\n\n"
        f"Episode: {niche['series']} | Mode: {niche['animation_mode']} Animation\n\n"
        f"#TheArchive #History #Documentary #Geopolitics #DarkHistory"
    )

    # Save pending
    save_pending({
        "video_path": video_path,
        "audio_path": audio_path,
        "thumb_path": thumb_path,
        "title":      title,
        "description":description,
        "tags":       tags + ["history","documentary","archive","geopolitics","dark history"],
        "niche":      niche["name"],
        "score":      score,
        "wc":         wc,
        "episode":    episode,
    })

    tg(f"✅ Archive Generated — queued for upload\n\n<b>{title}</b>\nNiche: {niche['name']} | Score: {score}/10 | {wc}w | {duration/60:.1f}min")
    log("\nGenerate phase complete.")

if __name__ == "__main__":
    main()

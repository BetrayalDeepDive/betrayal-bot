"""
Content-matched sound design — direct user request, July 23 2026:
"it's not only the things that I told. There should be hundreds of
things that should be added, because there would be multiple things
that are there for each video, each title, and niche. I want it to
work, and I want the sound designs to be added according to the niche
and title."

Real constraint (documented honestly, same as the original 6-category
version this replaces): no real sound-effect sample library is reachable
from this environment (no network access for asset downloads). Every
cue here is synthesized procedurally via FFmpeg (sine tones, envelopes),
same primitives already proven working in add_horror_atmosphere_fx's
riser/impact/drone/stinger chains. To genuinely scale from 6 hand-tuned
categories to "hundreds of things" without hand-typing hundreds of
individual tone signatures (error-prone, and a maintenance dead end),
every category not explicitly hand-tuned gets a DETERMINISTIC
procedural signature derived from its own name — same category always
produces the same distinct tone, every category sounds different from
every other, and the library can keep growing by just adding keyword
lists with zero additional synth-design work.
"""
import hashlib
import re
import subprocess
from collections import Counter
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
# GENERAL CONTENT CATEGORIES — shared across every channel/niche. ~70
# categories covering money, violence/impact, communication, time,
# nature, human reaction, institutional/legal, technology, and the
# supernatural/historical/psychological categories specific niches lean
# on. This is the "hundreds of things" library — each category maps a
# real cluster of script vocabulary to its own distinct synthesized cue.
# ══════════════════════════════════════════════════════════════════════
GENERAL_SFX_KEYWORDS = {
    # -- Money / finance --
    "coin_drop":        ["coin", "coins", "change", "penny", "pennies"],
    "cash_register":     ["cash register", "receipt", "till", "checkout"],
    "money_stack":       ["money", "cash", "dollar", "dollars", "banknotes", "bills"],
    "bank_vault":        ["vault", "safe", "safety deposit", "lockbox"],
    "wire_transfer":     ["wire transfer", "bank transfer", "wired the money", "transaction"],
    "stock_ticker":      ["stock", "shares", "ticker", "market crash", "trading floor"],
    "bankruptcy_stamp":  ["bankruptcy", "foreclosure", "repossessed", "seized assets"],
    "inheritance":       ["inheritance", "will", "estate", "beneficiary"],
    "fraud_alert":       ["fraud", "scam", "embezzlement", "laundering"],
    "credit_decline":    ["credit card", "declined", "overdraft", "debt collector"],

    # -- Violence / impact --
    "gunshot_impact":    ["gunshot", "gun", "shot", "fired a weapon", "trigger"],
    "explosion":         ["explosion", "explode", "detonated", "blast", "bomb"],
    "glass_break":       ["glass shattered", "window broke", "broken glass", "shattered"],
    "punch_impact":      ["punched", "struck", "hit him", "hit her", "blow to"],
    "slam_door":         ["slammed the door", "door slammed", "slammed shut"],
    "car_crash":         ["car crash", "collision", "crashed into", "wreckage"],
    "stabbing":          ["stabbed", "stabbing", "knife", "blade"],
    "struggle":          ["struggled", "fought back", "wrestled", "grabbed her", "grabbed him"],
    "fall_impact":       ["fell down the stairs", "collapsed", "hit the ground", "fell to the floor"],

    # -- Communication / devices --
    "phone_ring":        ["phone rang", "the phone", "called her", "called him", "incoming call"],
    "text_notification": ["text message", "notification", "buzzed", "phone buzzed"],
    "voicemail_beep":    ["voicemail", "answering machine", "left a message"],
    "radio_static":      ["radio", "static", "transmission", "walkie talkie"],
    "dial_up":           ["dial-up", "modem", "connecting to the internet"],
    "keyboard_typing":   ["typed", "typing", "keyboard", "keystrokes"],
    "email_send":        ["sent the email", "email arrived", "inbox"],
    "camera_shutter":    ["photograph", "photo", "camera", "snapped a picture"],
    "morse_code":        ["morse code", "coded message", "signal"],

    # -- Time / countdown --
    "clock_tick":        ["clock", "ticking", "midnight", "countdown"],
    "alarm_clock":       ["alarm", "woke up to", "set an alarm"],
    "bell_toll":         ["bell tolled", "church bell", "bell rang"],
    "hourglass":         ["hourglass", "running out of time", "time was running out"],
    "deadline_pressure":  ["deadline", "final warning", "last chance", "time limit"],

    # -- Nature / weather --
    "thunder":           ["thunder", "lightning", "storm", "thunderstorm"],
    "rain_intensify":    ["rain", "downpour", "raining", "rainstorm"],
    "wind_howl":         ["wind howled", "gust of wind", "windstorm"],
    "fire_crackle":      ["fire", "flames", "burning", "blaze"],
    "ocean_waves":       ["ocean", "waves", "tide", "shoreline"],
    "earthquake_rumble": ["earthquake", "tremor", "ground shook"],

    # -- Human reaction --
    "heartbeat":         ["heart pounded", "heartbeat", "pulse racing", "heart raced"],
    "gasp_shock":        ["gasped", "gasp", "shocked", "stunned silence"],
    "scream_shock":      ["screamed", "scream", "shrieked", "shouted in fear"],
    "sob_cry":           ["sobbed", "crying", "wept", "tears"],
    "breathing_heavy":   ["breathing heavily", "out of breath", "gasping for air"],
    "whisper":           ["whispered", "whisper", "hushed voice"],
    "footsteps":         ["footsteps", "walked toward", "approaching footsteps"],
    "silence_dread":     ["dead silence", "silence fell", "nobody spoke"],
    "laughter_eerie":    ["laughed", "laughing", "eerie laugh"],

    # -- Institutional / legal --
    "gavel_bang":        ["gavel", "courtroom", "judge ruled", "the court"],
    "handcuffs":         ["handcuffed", "handcuffs", "arrested", "placed under arrest"],
    "siren_police":      ["police siren", "sirens", "squad car", "flashing lights"],
    "prison_door":       ["prison cell", "cell door", "locked up", "behind bars"],
    "file_stamp":        ["stamped", "case file", "official document", "filed the report"],
    "paper_rustle":      ["paperwork", "documents", "files", "records"],
    "typewriter":        ["typewriter", "report was written", "wrote the statement"],
    "interrogation_tape": ["interrogation", "interview room", "under questioning"],

    # -- Supernatural / horror-adjacent --
    "ghost_whisper":     ["ghost", "spirit", "haunted", "presence"],
    "door_creak":        ["creaked open", "door creaked", "creaking hinge"],
    "static_interference": ["static", "interference", "signal cut out", "went dark"],
    "footsteps_upstairs": ["footsteps upstairs", "something moved", "heard something"],
    "cold_spot":         ["cold spot", "temperature dropped", "sudden chill"],

    # -- Historical / military --
    "sword_clash":       ["sword", "blade clashed", "swordsman", "dueled"],
    "horse_gallop":      ["horse", "cavalry", "galloped", "horseback"],
    "war_drum":          ["war drum", "drums of war", "battle drum"],
    "trumpet_fanfare":   ["trumpet", "fanfare", "royal announcement", "herald"],
    "marching_army":     ["marching", "army marched", "soldiers advanced"],
    "cannon_fire":       ["cannon", "artillery", "cannon fire"],
    "castle_gate":       ["castle gate", "drawbridge", "fortress"],

    # -- Psychological / manipulation --
    "manipulation_tone":  ["manipulated", "gaslighting", "controlled her", "controlled him"],
    "isolation_tone":    ["isolated", "cut off from", "no one to turn to"],
    "surveillance_beep":  ["surveillance", "watched", "monitored", "tracked her every move"],
    "confession_tape":   ["confession", "admitted", "confessed"],
    "betrayal_sting":    ["betrayed", "betrayal", "backstabbed"],

    # -- Tech / startup / modern --
    "error_beep":        ["error", "system failure", "crashed", "malfunction"],
    "notification_ping": ["ping", "alert popped up", "push notification"],
    "server_hum":        ["server", "data center", "servers went down"],
    "video_call":        ["video call", "zoom call", "conference call"],
    "app_launch":        ["launched the app", "went live", "app store"],
}

# Hand-tuned tone signatures for the original 6 categories (already
# verified via standalone filter-graph tests this session).
_HAND_TUNED_SYNTH = {
    "coin_drop":      [(1800, 0.3, 0.05, 0.25, 1.1), (2600, 0.22, 0.03, 0.19, 0.8)],
    "gunshot_impact": [(55, 0.25, 0.02, 0.23, 2.2)],
    "phone_ring":     [(950, 0.2, 0.05, 0.15, 1.0), (1400, 0.2, 0.05, 0.15, 0.7)],
    "scream_shock":   [(1200, 0.35, 0.05, 0.3, 1.3), (2000, 0.3, 0.04, 0.26, 0.9)],
    "clock_tick":     [(2000, 0.06, 0.01, 0.05, 0.9)],
    "door_creak":     [(100, 0.15, 0.02, 0.13, 1.6)],
}


def _procedural_sfx_params(category_name):
    """
    Deterministic, distinct-but-safe synthesized tone signature derived
    from the category's own name — same category always sounds the
    same, every category sounds different from every other, all within
    the same safe frequency/duration/volume ranges already proven to
    render correctly. This is how the library scales to "hundreds of
    things" without hand-tuning each one individually.
    """
    h = int(hashlib.md5(category_name.encode()).hexdigest(), 16)
    freq = 60 + (h % 2500)                          # 60-2560 Hz
    dur = round(0.08 + ((h >> 8) % 35) / 100, 2)     # 0.08-0.42s
    fade_st = round(dur * 0.15, 2)
    fade_d = round(dur * 0.8, 2)
    vol = round(0.8 + ((h >> 16) % 15) / 10, 2)      # 0.8-2.3
    layers = [(freq, dur, fade_st, fade_d, vol)]
    if (h >> 24) % 3 == 0:  # ~1/3 of categories get a second harmonic layer for texture
        freq2 = min(2600, int(freq * 1.4))
        layers.append((freq2, round(dur * 0.7, 2), round(fade_st * 0.7, 2),
                        round(fade_d * 0.7, 2), round(vol * 0.7, 2)))
    return layers


def get_sfx_synth(category_name):
    return _HAND_TUNED_SYNTH.get(category_name) or _procedural_sfx_params(category_name)


# Niche-specific bonus categories — tried FIRST for that niche before
# falling through to the general library above, so a channel's own genre
# gets priority representation (e.g. a historical channel's script is
# more likely to trigger sword_clash/war_drum than a generic finance cue).
NICHE_SFX_PRIORITY = {
    "dark_horror": ["ghost_whisper", "door_creak", "scream_shock", "silence_dread"],
    "seduction_dark": ["whisper", "betrayal_sting", "manipulation_tone"],
    "psychological_trap": ["manipulation_tone", "isolation_tone", "surveillance_beep"],
    "supernatural_real": ["ghost_whisper", "cold_spot", "static_interference", "footsteps_upstairs"],
    "obsession_dark": ["surveillance_beep", "isolation_tone", "phone_ring"],
    "forensic_finance": ["fraud_alert", "wire_transfer", "file_stamp"],
    "criminal_investigation": ["handcuffs", "siren_police", "interrogation_tape"],
    "corporate_exposure": ["fraud_alert", "money_stack", "bankruptcy_stamp"],
    "digital_forensics": ["error_beep", "server_hum", "keyboard_typing"],
    "body_cam_police": ["siren_police", "gunshot_impact", "handcuffs"],
    "courtroom_drama": ["gavel_bang", "confession_tape", "file_stamp"],
    "robbery_documentaries": ["gunshot_impact", "siren_police", "cash_register"],
    "cult_psychology": ["manipulation_tone", "isolation_tone", "betrayal_sting"],
    "propaganda_systems": ["radio_static", "surveillance_beep", "trumpet_fanfare"],
    "social_engineering": ["phone_ring", "email_send", "manipulation_tone"],
    "mass_deception": ["radio_static", "fraud_alert", "betrayal_sting"],
    "dark_business_documentaries": ["bankruptcy_stamp", "money_stack", "fraud_alert"],
    "scams_fraud_exposed": ["fraud_alert", "credit_decline", "phone_ring"],
    "ai_startup_collapse": ["error_beep", "server_hum", "bankruptcy_stamp"],
    "tech_company_collapse": ["server_hum", "error_beep", "app_launch"],
    "crypto_collapse": ["stock_ticker", "money_stack", "fraud_alert"],
    "cybersecurity_disasters": ["error_beep", "server_hum", "static_interference"],
    "product_flops": ["app_launch", "bankruptcy_stamp", "error_beep"],
    "dotcom_era_collapse": ["dial_up", "stock_ticker", "bankruptcy_stamp"],
    "personal_finance_mistakes": ["credit_decline", "money_stack", "bankruptcy_stamp"],
    "investing_fundamentals": ["stock_ticker", "money_stack", "wire_transfer"],
    "retirement_planning": ["money_stack", "wire_transfer", "inheritance"],
    "credit_debt_repair": ["credit_decline", "bank_vault", "money_stack"],
    "real_estate_affordability": ["bankruptcy_stamp", "wire_transfer", "money_stack"],
    "budgeting_saving_strategies": ["coin_drop", "money_stack", "bank_vault"],
    "stock_market_crashes_history": ["stock_ticker", "bankruptcy_stamp", "money_stack"],
    "egyptian_civilization": ["war_drum", "trumpet_fanfare", "castle_gate"],
    "chinese_civilization": ["war_drum", "sword_clash", "marching_army"],
    "mesopotamian_lost_civilizations": ["war_drum", "castle_gate", "sword_clash"],
    "islamic_civilization_history": ["trumpet_fanfare", "marching_army", "sword_clash"],
    "fallen_empires_military_overstretch": ["cannon_fire", "marching_army", "war_drum"],
    "elite_betrayal_infighting": ["betrayal_sting", "sword_clash", "confession_tape"],
    "propaganda_institutional_decline": ["radio_static", "trumpet_fanfare", "surveillance_beep"],
    "modern_parallels": ["radio_static", "server_hum", "surveillance_beep"],
}

_TOPIC_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "this", "that", "was", "were", "had", "have",
    "it", "its", "he", "she", "they", "their", "his", "her", "be", "been",
    "not", "no", "so", "as", "if", "then", "than", "when", "what", "who",
    "part", "real", "documented", "real-life", "true", "story",
}


def detect_content_sfx_cues(script, audio_duration, niche_name="", topic="", max_cues=6):
    """
    Scans the script sentence-by-sentence (proportional position, same
    technique as extract_key_phrases) for the ~70 general categories plus
    this niche's priority categories, returning up to max_cues distinct
    (category, time_seconds) cues in script order -- so sound design
    reflects what THIS story actually contains AND this channel's own
    genre, not a fixed generic set. A topic-anchor cue (matching a real
    specific word from the topic/title itself, not just the fixed
    category vocabulary) is added when the topic contains a distinctive
    word that also appears in the script, satisfying the explicit
    "according to the niche and title" requirement.
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if s.strip()]
    if not sentences:
        return []
    total = len(sentences)

    priority = NICHE_SFX_PRIORITY.get(niche_name, [])
    ordered_categories = list(dict.fromkeys(priority + list(GENERAL_SFX_KEYWORDS.keys())))

    cues = []
    seen_categories = set()
    for idx, sent in enumerate(sentences):
        low = sent.lower()
        for category in ordered_categories:
            if category in seen_categories:
                continue
            keywords = GENERAL_SFX_KEYWORDS.get(category)
            if not keywords:
                continue
            if any(kw in low for kw in keywords):
                frac = idx / total
                if 0.05 < frac < 0.95:
                    cues.append((category, frac * audio_duration))
                    seen_categories.add(category)
        if len(cues) >= max_cues:
            break

    # Topic/title anchor cue — a real specific word from the topic that
    # also appears verbatim in the script, tagged as its own "topic_anchor"
    # category so it always gets a cue even if it didn't match any fixed
    # keyword list above.
    if len(cues) < max_cues and topic:
        topic_words = [w.strip(".,!?;:\"'()").lower() for w in topic.split()
                       if len(w) > 5 and w.strip(".,!?;:\"'()").lower() not in _TOPIC_STOPWORDS]
        script_lower = script.lower()
        for w in [w for w, _ in Counter(topic_words).most_common(5)]:
            if w in script_lower:
                sent_idx = next((i for i, s in enumerate(sentences) if w in s.lower()), None)
                if sent_idx is not None:
                    frac = sent_idx / total
                    if 0.05 < frac < 0.95:
                        cues.append(("topic_anchor", frac * audio_duration))
                        break

    return cues[:max_cues]


def apply_audio_only_content_sfx(video_path, script, audio_duration, niche_name, output_path,
                                  topic="", log_fn=print, max_cues=6):
    """
    Genre-neutral, AUDIO-ONLY content-matched SFX layer — no film grain,
    no jump-scare flash, no visual glitch. For channels that explicitly
    don't want horror-style visual treatment (Ch5 finance/collapse
    documentary, Ch2 forensic/crime, Ch3 psychological-manipulation
    documentary, Ch4 historical documentary all have their own genre
    identity, not Ch1's horror-movie language) but still want real
    content-matched sound design layered into the existing narration +
    ambient music mix. Non-fatal: returns the original video_path
    unchanged on any failure or if no cues were found.
    """
    try:
        content_cues = detect_content_sfx_cues(script, audio_duration, niche_name=niche_name,
                                                topic=topic, max_cues=max_cues)
        if not content_cues:
            return video_path

        stinger_filters = []
        stinger_labels = []
        for ci, (category, cue_t) in enumerate(content_cues):
            cue_delay_ms = int(max(0.3, cue_t) * 1000)
            for li, (freq, dur, fade_st, fade_d, vol) in enumerate(get_sfx_synth(category)):
                label = f"csfx{ci}_{li}"
                stinger_filters.append(
                    f"sine=frequency={freq}:duration={dur},"
                    f"afade=t=out:st={fade_st}:d={fade_d},volume={vol},"
                    f"adelay={cue_delay_ms}|{cue_delay_ms}[{label}]"
                )
                stinger_labels.append(f"[{label}]")

        stinger_chain = ";".join(stinger_filters)
        stinger_inputs = "".join(stinger_labels)
        n_mix = 1 + len(stinger_labels)
        filter_complex = (f"{stinger_chain};[0:a]{stinger_inputs}amix=inputs={n_mix}:"
                           f"duration=first:dropout_transition=0[mixedaudio]")

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-filter_complex", filter_complex,
             "-map", "0:v", "-map", "[mixedaudio]",
             "-c:v", "copy", "-c:a", "aac", "-ar", "44100", output_path],
            capture_output=True, timeout=600)

        if result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 1_000_000:
            log_fn(f"  Content-matched SFX (audio-only): {[c for c, _ in content_cues]}")
            return output_path
        log_fn(f"  Content SFX audio layer failed (non-fatal): "
               f"{result.stderr.decode(errors='ignore')[:200]}")
        return video_path
    except Exception as e:
        log_fn(f"  Content SFX audio layer failed (non-fatal): {e}")
        return video_path

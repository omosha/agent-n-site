#!/usr/bin/env python3
"""
build_race_narratives.py — generate data/race-narratives.json for the dynamic
candidate explorer on the Agent-N site.

For every race in data/sealed-board.json this emits one ILLUSTRATIVE representative
voter narrative (persona + reasoning + inner conflict) plus a reactive-shift scenario,
composed deterministically from the district's REAL structure (office, region, the two
candidates, incumbent party, and our sealed projected margin). It is explicitly labeled
illustrative: a plausible story, one representative agent, NOT a real person and NOT the
forecast. The projected numbers shown are the sealed statistical call; only the reasoning
and the what-if delta are generated.

This never touches data/sealed-board.json (that file is sha256-sealed). Re-run to rebuild:
    python3 scripts/build_race_narratives.py
"""
import json, hashlib, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HERE, "data", "sealed-board.json")
OUT   = os.path.join(HERE, "data", "race-narratives.json")

# Candidate names for the 28 national CDs (sealed-board.json leaves d/r blank there).
# Sourced 2026-10-13 (Ballotpedia / campaign sites / FEC). D first, R second.
NAT_NAMES = {
    "AZ-01": ("Amish Shah (D)", "Jay Feely (R)"),
    "AZ-06": ("JoAnna Mendoza (D)", "Juan Ciscomani (R)"),
    "CO-05": ("Jessica Killin (D)", "Jeff Crank (R)"),
    "CO-08": ("Manny Rutinel (D)", "Gabe Evans (R)"),
    "IA-01": ("Christina Bohannan (D)", "Mariannette Miller-Meeks (R)"),
    "IA-03": ("Sarah Trone Garriott (D)", "Zach Nunn (R)"),
    "ME-02": ("Matt Dunlap (D)", "Paul LePage (R)"),
    "MI-04": ("Sean McCann (D)", "Bill Huizenga (R)"),
    "MI-07": ("Will Lawrence (D)", "Tom Barrett (R)"),
    "MI-10": ("Christina Hines (D)", "Mike Bouchard (R)"),
    "MT-01": ("Sam Forstag (D)", "Aaron Flint (R)"),
    "NE-02": ("Denise Powell (D)", "Brinker Harding (R)"),
    "NH-01": ("Stefany Shaheen (D)", "Anthony DiLorenzo (R)"),
    "NM-02": ("Gabe Vasquez (D)", "Greg Cunningham (R)"),
    "NV-03": ("Susie Lee (D)", "Marty O'Donnell (R)"),
    "NY-03": ("Tom Suozzi (D)", "Mike LiPetri (R)"),
    "NY-04": ("Laura Gillen (D)", "Jeanine Driscoll (R)"),
    "NY-17": ("Cait Conley (D)", "Mike Lawler (R)"),
    "NY-19": ("Josh Riley (D)", "Peter Oberacker (R)"),
    "PA-07": ("Bob Brooks (D)", "Ryan Mackenzie (R)"),
    "PA-08": ("Paige Cognetti (D)", "Rob Bresnahan (R)"),
    "PA-10": ("Janelle Stelson (D)", "Scott Perry (R)"),
    "VA-01": ("Shannon Taylor (D)", "Rob Wittman (R)"),
    "VA-02": ("Elaine Luria (D)", "Jen Kiggans (R)"),
    "VA-05": ("Tom Perriello (D)", "John McGuire (R)"),
    "WA-03": ("Marie Gluesenkamp Perez (D)", "John Braun (R)"),
    "WI-01": ("Mitchell Berman (D)", "Bryan Steil (R)"),
    "WI-03": ("Rebecca Cooke (D)", "Derrick Van Orden (R)"),
}

# Region strings. CA CDs + national CDs are accurate-enough regional labels; state-leg
# and anything unmapped fall back to a generic office-aware region.
REGION = {
    "CA-Gov": "all 58 California counties",
    "OC-D5": "the Orange County coast, Costa Mesa to San Clemente",
    "OC-D4": "north Orange County, from Fullerton to Buena Park",
    "CA-01": "the far-north counties around Chico and Redding",
    "CA-02": "the North Coast and redwood country",
    "CA-03": "the Sierra foothills and Sacramento exurbs",
    "CA-05": "the Gold Country and Sierra",
    "CA-08": "the East Bay and Solano County",
    "CA-09": "San Joaquin County and Stockton",
    "CA-10": "central Contra Costa County",
    "CA-13": "the northern San Joaquin Valley",
    "CA-15": "the San Mateo Peninsula",
    "CA-16": "Silicon Valley and the Peninsula",
    "CA-17": "the heart of Silicon Valley",
    "CA-18": "San Jose and the South Bay",
    "CA-19": "the Monterey Bay and Central Coast",
    "CA-20": "the southern San Joaquin Valley",
    "CA-21": "Fresno and the central Valley",
    "CA-22": "the Kings and Tulare County Valley",
    "CA-23": "the High Desert and San Bernardino Mountains",
    "CA-24": "Santa Barbara and the Central Coast",
    "CA-25": "the Imperial Valley and desert",
    "CA-26": "Ventura County",
    "CA-27": "the Antelope Valley and northern LA County",
    "CA-28": "the San Gabriel Valley foothills",
    "CA-30": "the LA basin from Hollywood to Glendale",
    "CA-31": "the San Gabriel Valley",
    "CA-32": "the western San Fernando Valley",
    "CA-33": "the eastern Inland Empire",
    "CA-35": "the Inland Empire",
    "CA-36": "West LA and the beach cities",
    "CA-38": "southeast LA County",
    "CA-39": "the Riverside corridor",
    "CA-41": "Riverside and Corona",
    "CA-42": "Long Beach",
    "CA-43": "south Los Angeles",
    "CA-44": "southeast LA and the Gateway cities",
    "CA-45": "Little Saigon and northern Orange County",
    "CA-46": "Santa Ana and central Orange County",
    "CA-47": "coastal Orange County",
    "CA-48": "inland San Diego and southwest Riverside",
    "CA-49": "the north San Diego coast and south Orange County",
    "CA-50": "metro San Diego",
    "CA-51": "central San Diego",
    "CA-52": "San Diego and the border",
    "AZ-01": "the Scottsdale and north Phoenix suburbs",
    "AZ-06": "Tucson and southern Arizona",
    "CO-05": "Colorado Springs and El Paso County",
    "CO-08": "the north Denver suburbs",
    "IA-01": "southeast Iowa",
    "IA-03": "Des Moines and its suburbs",
    "ME-02": "rural northern and eastern Maine",
    "MI-04": "southwest Michigan",
    "MI-07": "mid-Michigan around Lansing",
    "MI-10": "Macomb County, north of Detroit",
    "MT-01": "western Montana",
    "NE-02": "the Omaha metro",
    "NH-01": "eastern New Hampshire and the Seacoast",
    "NM-02": "southern New Mexico and the border",
    "NV-03": "the Las Vegas suburbs",
    "NY-03": "Long Island and northeast Queens",
    "NY-04": "southern Nassau County",
    "NY-17": "the lower Hudson Valley",
    "NY-19": "the upstate Catskills and Hudson Valley",
    "PA-07": "the Lehigh Valley",
    "PA-08": "Scranton and northeast Pennsylvania",
    "PA-10": "the Harrisburg and York area",
    "VA-01": "the Northern Neck and Tidewater",
    "VA-02": "Virginia Beach and Hampton Roads",
    "VA-05": "central and southside Virginia",
    "WA-03": "southwest Washington",
    "WI-01": "southeast Wisconsin",
    "WI-03": "the western Wisconsin Driftless",
}

OFFICE = {
    "Governor": ("Governor of California", "the Governor's race"),
    "CA U.S. House": ("U.S. House", "this congressional race"),
    "National U.S. House": ("U.S. House", "this congressional race"),
    "CA State Legislature": ("the state legislature", "this legislative race"),
    "OC Supervisor": ("the county Board of Supervisors", "this supervisor race"),
}

def office_kind(g, dist):
    if g == "Governor": return "gov"
    if g == "OC Supervisor": return "county"
    if dist.startswith("SEN-"): return "senate"
    if dist.startswith("AD-"): return "assembly"
    return "house"

def region_for(r):
    dist = r["dist"]
    if dist in REGION: return REGION[dist]
    g = r["g"]
    if g == "CA State Legislature":
        return "this district in California"
    return "this district"

def clean_name(n):
    """'Katrina Foley (D)' -> 'Foley'. Falls back to full if no space."""
    if not n: return ""
    base = re.sub(r"\s*\((D|R|NPP|I|OPEN)\)\s*$", "", n).strip()
    parts = base.split()
    return parts[-1] if parts else base

def hpick(seed, options):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]

# ---- persona archetype pools, keyed by (office family, lean bucket) -----------------
# Each entry: (who, voice_template, conflict_template). Templates use {D} {R} {FAV}
# {UNDERDOG} {INC} {region} {office} {margin}. Kept compact; the real candidates + margin
# injected per race make each read specifically.

def lean_bucket(proj, call):
    m = abs(proj - 50)
    if call == "Toss-up" or m <= 3: return "tossup"
    if m <= 8: return "lean"
    return "safe"

AGES = ["34", "41", "52", "58", "63", "67", "71", "46", "29", "77"]
JOBS = {
    "house": ["a small-business owner", "a nurse", "a schoolteacher", "a warehouse supervisor",
              "a retired contractor", "an office manager", "a farmworker", "a software engineer"],
    "assembly": ["a small-business owner", "a home health aide", "a community-college instructor",
                 "a retired firefighter", "a dispatcher", "a grocery-store manager"],
    "senate": ["a small-business owner", "a union electrician", "a retired teacher",
               "a county caseworker", "a real-estate agent"],
    "county": ["a homeowner", "a retiree", "a renter and service worker", "a small landlord"],
    "gov": ["a small-business owner", "a nurse", "a retired engineer", "a teacher", "a rideshare driver"],
}

def persona(r, kind, bucket):
    seed = r["dist"]
    job = hpick(seed+"job", JOBS.get(kind, JOBS["house"]))
    age = hpick(seed+"age", ["63","67","71","77","58"] if "retire" in job else AGES)
    region = region_for(r)
    favored_is_d = r["proj"] > 50
    Dn, Rn = clean_name(r["d"]) or "the Democrat", clean_name(r["r"]) or "the Republican"
    FAV = Dn if favored_is_d else Rn
    UND = Rn if favored_is_d else Dn
    inc = r["inc"]
    incname = Dn if inc == "D" else (Rn if inc == "R" else None)
    margin = abs(round(r["proj"]) - (100-round(r["proj"])))
    office_noun = OFFICE.get(r["g"], ("this office","this race"))[0]

    if bucket == "tossup":
        who = f"{age}, {job}, registered independent, {region}"
        reg = "a registered independent who breaks late"
        voice = (f"I am {age}, {job} in {region}, and I am genuinely undecided here. "
                 f"{Dn} and {Rn} both keep showing up in my feed, and on paper this is a coin flip. "
                 f"I am not voting the party line in this one. I am waiting to see who sounds like they "
                 f"actually understand what the last two years cost people like me before I fill it in.")
        conflict = (f"I could still swing either way, or leave it blank if both camps spend the final week "
                    f"attacking instead of answering. A single local story about {region} could decide my vote.")
    elif bucket == "lean":
        who = f"{age}, {job}, soft partisan, {region}"
        voice = (f"I am {age}, {job} in {region}. My lean is toward {FAV}, but it is soft. "
                 f"{UND} is close enough in the numbers that I am still paying attention. "
                 f"What holds me with {FAV} is habit and a couple of issues that hit my household directly; "
                 f"what could move me is if {UND} shows up where {FAV} has gone quiet.")
        conflict = (f"A {margin}-point lean is not a lock. If turnout on my side sags, or {UND} runs a sharper "
                    f"final week in {region}, this is the kind of race that slips.")
    else:  # safe
        who = f"{age}, {job}, reliable {('Democrat' if favored_is_d else 'Republican')}, {region}"
        voice = (f"I am {age}, {job} in {region}, and I will almost certainly vote {FAV}. "
                 f"This is not a close seat and everyone knows it. The real question for me is whether I "
                 f"bother with the whole ballot or stop after the top of the ticket, because down here the "
                 f"result feels decided before I even open the envelope.")
        conflict = (f"The risk in {region} is not that I switch to {UND}, it is that I skip the race entirely. "
                    f"Safe seats lose votes to apathy, not to the other side.")
    return who, voice, conflict, incname, FAV, UND, Dn, Rn

# ---- reactive-shift scenarios -------------------------------------------------------
# (scenario text, direction: 'inc'|'D'|'R'|'turnout', magnitude pp)
SCEN = {
    "gov":    [("A major wildfire dominates statewide news in the final week and the sitting administration is visible managing the response.", "D", 6),
               ("A late cost-of-living story about rent and gas leads every California broadcast for days.", "R", 5)],
    "county": [("A late wildfire dominates county news in the final week and the incumbent is visible managing the emergency response.", "inc", 25),
               ("A property-tax and county-spending story breaks in the final stretch.", "turnout", 12)],
    "house":  [("Congress forces a government-shutdown vote days before the election and it leads national news.", "turnout", 9),
               ("A grocery-and-healthcare-cost story nationalizes the final week of the race.", "D", 7),
               ("A border-and-immigration story dominates cable in the closing stretch.", "R", 8)],
    "assembly":[("A local story about a plant or hospital closing in the district breaks in the final week.", "turnout", 10),
                ("A late mailer war over housing costs and homelessness floods the district.", "D", 6)],
    "senate": [("A statewide ballot-measure fight spills into the district and nationalizes turnout.", "turnout", 9),
               ("A closing-week story about public safety reshapes the conversation.", "R", 7)],
}

def shift(r, kind, Dn, Rn, incname, bucket):
    scen, direction, mag = hpick(r["dist"]+"scen", SCEN.get(kind, SCEN["house"]))
    d0 = round(r["proj"]); r0 = 100 - d0
    other = 0
    if bucket == "tossup":          # realistic undecided sliver in a coin-flip race
        other = 8; d0 = max(2, d0 - 4); r0 = 100 - d0 - other
    # apply the shock
    if direction == "inc" and incname:
        dd = mag if incname == Dn else -mag
    elif direction == "D": dd = mag
    elif direction == "R": dd = -mag
    else:  # turnout — base turnout rewards the already-favored side
        dd = (3 if r["proj"] >= 50 else -3); mag = abs(dd)
    d1 = max(2, min(98, round(r["proj"]) + dd)); r1 = 100 - d1  # shock resolves to two-way
    toward = Dn if dd > 0 else Rn
    note = f"{'+' if dd>0 else '−'}{abs(d1-round(r['proj']))}pp toward {toward}. N=12, illustrative."
    base = [d0, r0, other] if other else [d0, r0]
    return {"scenario": scen, "base": base, "shock": [d1, r1],
            "dName": Dn, "rName": Rn, "delta": note}

# Hand-authored narratives for the showcase races, so a search matches the gold
# card already on the page and the two marquee OC races + Governor read their best.
OVERRIDES = {
    "OC-D5": {
        "who": "89, male, white, registered Republican, homeowner, Irvine South",
        "voice": ("I am an 89-year-old registered Republican homeowner in Irvine South, retired, and I still "
                  "vote all the way down the ballot because county supervisor races affect property taxes and "
                  "how my money gets spent. Party registration is my strong default on a partisan-flavored seat "
                  "like this. What seals it is that Dixon reads as the reasonable, fiscally-conservative type of "
                  "Republican, not a culture warrior. Between an identifiable Republican and the Democratic "
                  "incumbent, I go with my party here rather than skipping or crossing over."),
        "conflict": ("There is a real chance I just skip this if the name does not ring a bell by the time I "
                     "reach it on a long ballot. But my pattern as a reliable down-ballot voter wins out, and "
                     "Dixon's Newport-Beach-Republican profile is exactly the kind I do not cross over on."),
        "scenario": ("A late wildfire dominates county news in the final week. The incumbent is visible managing "
                     "the emergency response. The same agents vote again."),
        "base": [42, 50, 8], "shock": [67, 33], "delta": "+25pp toward the incumbent. N=12, illustrative.",
    },
    "OC-D4": {
        "who": "47, female, Latina, registered Democrat, homeowner, Fullerton",
        "voice": ("I am 47, a Fullerton homeowner and a registered Democrat, and north Orange County is finally "
                  "a place a Democrat can win a supervisor seat. Traut is the Buena Park mayor who worked his way "
                  "up, and that local record matters to me more than the party label on a nonpartisan office. "
                  "Shaw is a known La Habra name, so this is not a gimme. I vote Traut, but I understand why my "
                  "neighbor two doors down is still deciding."),
        "conflict": ("The thing that could cost Traut my enthusiasm is if the race goes all-negative. I will still "
                     "vote for him, but a nasty final week keeps the softer Democrats in my cul-de-sac home."),
        "scenario": ("A late story about city-hall spending in one of the district's cities leads local news. "
                     "The same agents vote again."),
        "base": [47, 45, 8], "shock": [51, 49], "delta": "+4pp toward Traut. N=12, illustrative.",
    },
    "CA-Gov": {
        "who": "58, male, white, registered independent, small-business owner, Fresno County",
        "voice": ("I am 58, run a small business in the Central Valley, and I am a no-party-preference voter who "
                  "is tired of being told how California already voted. Statewide, Becerra is ahead of Hilton and "
                  "I know it. What I actually care about is my county: whether the Valley gets taken seriously on "
                  "water, costs, and crime. I will probably vote Hilton as a protest, knowing he loses the state."),
        "conflict": ("My vote barely moves the statewide number, so the honest question is turnout: do I bother, "
                     "or do I skip the top of the ticket and just vote the local races that actually change my life."),
        "scenario": ("A major wildfire dominates statewide news in the final week and the sitting administration "
                     "is visible managing the response. The same agents vote again."),
        "base": [60, 40], "shock": [66, 34], "delta": "+6pp toward Becerra statewide. N=12, illustrative. The map, not the topline, is the graded claim.",
    },
}

# Same-party / reference races. These are NOT on the 151 partisan board (the statistical
# method needs D-vs-R), but they are exactly where Agent-N's reasoning layer is most valuable
# (a party model is blind). Framed honestly: intelligence + what-if, no sealed partisan topline.
# AD-12 is the validated REFERENCE campaign; its content is from the real Lucan brief.
SAME_PARTY = {
    "AD-12": {
        "g": "CA State Legislature (same-party)", "office": "the state legislature",
        "region": "the Marin and Sonoma county split", "party": "D",
        "d": "Eric Lucan (D)", "r": "Jackie Elward (D)", "pct": [48, 30],
        "who": "75, Novato retiree, registered Democrat, Marin County",
        "voice": ("Lucan is literally my County Supervisor. His name is the one I have actually seen, and he "
                  "is from Novato, same as me. That is the shortcut that wins this for me. When I am filling out "
                  "a long ballot tired at my kitchen table, the Schiff and Huffman endorsements are a safe harbor, "
                  "and I am not going to go learn a Sonoma councilmember's record to change my mind."),
        "conflict": ("A Sonoma voter two counties over starts from the opposite place: Elward is the only one of "
                     "us from up here, and Marin people do not think about us. In a same-party race with no party "
                     "cue to lean on, home county is the whole ballgame, and that is exactly what a poll cannot see."),
        "scenario": ("A $500K billionaire-funded PAC (Grow California) floods the district with attack ads against "
                     "Elward over a water-rate vote, and the Press Democrat covers the crypto-money backlash. The "
                     "same agents vote again."),
        "base": [24, 29], "shock": [48, 30],
        "delta": ("+24pp to Lucan. The attack did not suppress Elward (29→30) — it collapsed the Marin three-way "
                  "and handed Lucan the pieces, an unintentional Lucan super-PAC. N=100 sim, from the sealed Lucan brief."),
    },
    "CA-07": {
        "g": "CA U.S. House (same-party)", "office": "U.S. House",
        "region": "Sacramento", "party": "D", "d": "Doris Matsui (D)", "r": "Mai Vang (D)", "pct": None,
        "who": "46, Sacramento office manager, registered Democrat",
        "voice": ("These are both Democrats, so my usual shortcut is gone. Matsui has been my congresswoman for "
                  "as long as I can remember and nothing is wrong exactly. Vang is the newer, hungrier name and "
                  "a lot of my neighbors are excited. I am deciding on tenure versus a change, not on party, which "
                  "is a totally different way to fill out a ballot."),
        "conflict": ("I could stay with the known name out of habit, or I could reward the challenger's energy. A "
                     "poll that models me by party registration learns nothing here, because party is not the lever."),
        "scenario": ("A high-turnout push in the Hmong and AAPI neighborhoods that are Vang's base lands in the final "
                     "week. The same agents vote again."),
        "base": [55, 45], "shock": [49, 51],
        "delta": "+6pp to Vang. In a D-vs-D race the swing is coalition turnout, not party. N=12, illustrative.",
    },
    "CA-11": {
        "g": "CA U.S. House (same-party)", "office": "U.S. House",
        "region": "San Francisco (Pelosi's open seat)", "party": "D", "d": "Scott Wiener (D)", "r": "Connie Chan (D)", "pct": None,
        "who": "34, San Francisco renter, registered Democrat",
        "voice": ("Pelosi's open seat, and both finalists are progressive Democrats, so I am not picking a party, I "
                  "am picking a flavor. Wiener is the build-more-housing YIMBY, Chan is the tenant-and-neighborhood "
                  "left. I agree with both of them most of the time, which is exactly why this is hard."),
        "conflict": ("My vote comes down to which precincts actually turn out: the denser renter blocks or the "
                     "west-side homeowners. That is a map question, not a party question, and it is where a normal "
                     "pollster goes blind."),
        "scenario": ("A late housing-and-cost-of-living story dominates the local race and sharpens the YIMBY-vs-tenant "
                     "contrast. The same agents vote again."),
        "base": [52, 48], "shock": [55, 45],
        "delta": "+3pp to Wiener. Same-party, so the move is turnout geography. N=12, illustrative.",
    },
    "CA-04": {
        "g": "CA U.S. House (same-party)", "office": "U.S. House",
        "region": "Napa and the North Bay", "party": "D", "d": "Mike Thompson (D)", "r": "Eric Jones (D)", "pct": None,
        "who": "63, Napa small-business owner, registered Democrat",
        "voice": ("Both Napa Democrats. Thompson has held this seat for fourteen terms and I have voted for him "
                  "every time without thinking. Jones is a Democrat too, self-funding a serious challenge, asking "
                  "whether fourteen terms is long enough. For once the question is not which party, it is whether "
                  "I want a change from my own side."),
        "conflict": ("I will probably stay with Thompson out of loyalty, but a well-funded same-party challenger "
                     "pulls at the soft-Democrat and crossover-curious vote in a way no R ever could here."),
        "scenario": ("The challenger's self-funded ad campaign saturates the district in the closing weeks. The "
                     "same agents vote again."),
        "base": [66, 34], "shock": [60, 40],
        "delta": "+6pp to Jones off a saturation buy. A party model cannot see this race at all. N=12, illustrative.",
    },
    "CA-40": {
        "g": "CA U.S. House (same-party)", "office": "U.S. House",
        "region": "the Orange–Riverside county line", "party": "R", "d": "Ken Calvert (R)", "r": "Young Kim (R)", "pct": None,
        "who": "58, Corona homeowner, registered Republican",
        "voice": ("Redistricting threw two sitting Republicans into the same seat, so I am choosing between Calvert "
                  "and Kim with no party cue to help me, both are my party. Calvert has represented Riverside "
                  "forever, Kim is the Orange County name. I am basically voting for whichever one feels like mine, "
                  "which mostly means whichever one is from my side of the county line."),
        "conflict": ("Where the new lines put my precinct decides this more than anything either of them says. In an "
                     "R-vs-R race the home-county map is the entire story, and that is precisely what Agent-N models "
                     "and a party-registration poll cannot."),
        "scenario": ("A final-week turnout surge in the Orange County half of the district, Kim's home base. The "
                     "same agents vote again."),
        "base": [60, 40], "shock": [54, 46],
        "delta": "+6pp to Kim on home-county turnout. Same party, so geography is the lever. N=12, illustrative.",
    },
}

def build():
    board = json.load(open(BOARD))
    out = {}
    index = []  # search index entries
    for r in board:
        dist = r["dist"]
        # fill national candidate names
        d, rr = r.get("d",""), r.get("r","")
        if (not d or not rr) and dist in NAT_NAMES:
            d, rr = NAT_NAMES[dist]
        rr_row = dict(r); rr_row["d"], rr_row["r"] = d, rr
        kind = office_kind(r["g"], dist)
        bucket = lean_bucket(r["proj"], r["call"])
        who, voice, conflict, incname, FAV, UND, Dn, Rn = persona(rr_row, kind, bucket)
        sh = shift(rr_row, kind, Dn, Rn, incname, bucket)
        rec = {
            "dist": dist, "g": r["g"], "d": d, "r": rr,
            "inc": r["inc"], "proj": r["proj"], "lo": r["lo"], "hi": r["hi"], "call": r["call"],
            "region": region_for(r), "office": OFFICE.get(r["g"], ("this office","this race"))[0],
            "bucket": bucket, "who": who, "voice": voice, "conflict": conflict,
            "scenario": sh["scenario"], "base": sh["base"], "shock": sh["shock"],
            "dName": sh["dName"], "rName": sh["rName"], "delta": sh["delta"],
        }
        if dist in OVERRIDES:
            rec.update(OVERRIDES[dist])
        out[dist] = rec
        # search tokens: district, both candidate full names, both surnames
        toks = [dist]
        for nm in (d, rr):
            if nm:
                toks.append(re.sub(r"\s*\((D|R|NPP|I|OPEN)\)\s*$","",nm).strip())
        index.append({"dist": dist, "label": f"{dist} — {out[dist]['d'] or 'D'} vs {out[dist]['r'] or 'R'}",
                       "tokens": [t for t in toks if t]})
    # append same-party / reference races (not on the partisan board)
    for dist, sp in SAME_PARTY.items():
        rec = {
            "dist": dist, "g": sp["g"], "d": sp["d"], "r": sp["r"],
            "inc": "", "proj": None, "lo": None, "hi": None, "call": "Same-party",
            "sameParty": True, "party": sp["party"], "pct": sp.get("pct"),
            "region": sp["region"], "office": sp["office"], "bucket": "sameparty",
            "who": sp["who"], "voice": sp["voice"], "conflict": sp["conflict"],
            "scenario": sp["scenario"], "base": sp["base"], "shock": sp["shock"],
            "dName": clean_name(sp["d"]), "rName": clean_name(sp["r"]), "delta": sp["delta"],
        }
        out[dist] = rec
        toks = [dist]
        for nm in (sp["d"], sp["r"]):
            toks.append(re.sub(r"\s*\((D|R|NPP|I|OPEN)\)\s*$","",nm).strip())
        index.append({"dist": dist, "label": f"{dist} — {rec['d']} vs {rec['r']} (same-party)", "tokens": toks})

    payload = {"races": out, "index": index,
               "meta": {"count": len(out), "note": "Illustrative voter narratives generated from district structure. Projections are the sealed statistical call; reasoning and what-if deltas are illustrative, not the forecast."}}
    json.dump(payload, open(OUT,"w"), ensure_ascii=False, indent=0)
    print(f"wrote {OUT}: {len(out)} races, {len(index)} search entries")

if __name__ == "__main__":
    build()

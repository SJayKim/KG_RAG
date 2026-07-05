"""Gate 4 step 2b: bidirectional recovery (DESIGN gate Finding 3).

Many perpetrator labels do not self-attribute their CYP3A4 role in the exact
"CYP3A4" spelling the single-direction LLM pass keys on, so that pass misses
them. This deterministic pass recovers those edges from the verbatim label text
via GENERAL cue-phrase + proximity rules (never drug-name hardcoding), so the
recall lift is auditable. Every recovered edge carries a real evidence_sentence
copied from the corpus and a ``recovered_from`` provenance tag.

Two recovery mechanisms, both over ALL labels in the corpus:

  1. ENUMERATION mining. A label enumerates other agents by role, e.g.
       lovastatin: "Strong inhibitors of CYP3A4 (e.g., itraconazole,
         ketoconazole, ... nefazodone, erythromycin, ...)"
       dronedarone: "Avoid rifampin or other CYP3A inducers such as
         phenobarbital, carbamazepine, phenytoin, ..."
       atorvastatin: "... cyclosporine, an inhibitor of CYP3A4 ..."
     For every crosswalk drug (other than the host) named in such a sentence we
     attribute the role whose cue phrase is *nearest* the drug's mention
     (proximity rule), so a sentence enumerating both inhibitors and inducers is
     not miscredited.

  2. SELF-ATTRIBUTION mining. A drug's OWN label predicates its role directly,
     e.g.
       dronedarone: "Dronedarone is metabolized by CYP3A and is a moderate
         inhibitor of CYP3A ..."          -> inhibitor (moderate) + substrate
       midazolam:   "the biotransformation of midazolam is mediated by
         cytochrome P450-3A4"             -> substrate
     These are recovered by NAME-ANCHORED predication templates ("<name> is a
     <strength> inhibitor of CYP3A", "<name> is metabolized by CYP3A4",
     "biotransformation of <name> ... CYP3A4"). Anchoring to the drug name (and
     a negation guard) prevents crediting a drug merely *named* in a sentence
     about some *other* drug's metabolism (e.g. fluconazole labels mention
     "drugs metabolized through ... CYP3A4" — those are other drugs, not
     fluconazole itself).

Subfamily tolerance: labels use "CYP3A" (the subfamily) and "CYP3A4" (the
isoform) interchangeably for these DDI agents (e.g. dronedarone is graded as a
"moderate inhibitor of CYP3A"). CYP3A4 is the dominant hepatic CYP3A isoform, so
a "CYP3A inhibitor/inducer" attribution grounds the CYP3A4 edge. Cue regexes
therefore make the trailing "4" optional; the verbatim (possibly "CYP3A")
evidence sentence is preserved so the normalization is auditable.

Negation guard: a substrate/metabolism claim is skipped if a negation token
(not / no / little / minimal / non ...) precedes the CYP3A4 token, so the
NON-CYP3A4 hard negatives ("pravastatin ... not metabolized by CYP3A4",
"Rosuvastatin clearance is not dependent on metabolism by cytochrome P450 3A4")
never fire.

Run:
  PYTHONUTF8=1 python scripts/extract/augment_bidirectional.py \
      fixtures/openfda-labels/corpus.json \
      fixtures/openfda-labels/extracted_llm.json \
      fixtures/crosswalk/ingredient_crosswalk_v0.csv \
      fixtures/openfda-labels/extracted_llm_bidir.json
"""
import csv
import json
import re
import sys

# --- CYP3A / CYP3A4 tokens (subfamily-tolerant; trailing "4" optional) --------
CYP = r"CYP\s?3\s?A\s?4?"                       # "CYP3A" or "CYP3A4"
CYP_TOKEN = (r"(?:CYP\s?3\s?A\s?4?"             # for metabolism sentences, also
            r"|cytochrome\s+P[\s\-]?450[\s\-]?3\s?A\s?4?"   # "cytochrome P450-3A4"
            r"|P[\s\-]?450[\s\-]?3\s?A\s?4?)")

INHIB_CTX = re.compile(rf"inhibitors?\s+of\s+{CYP}|{CYP}\s+inhibitors?", re.IGNORECASE)
STRONG_INHIB_CTX = re.compile(
    rf"(?:strong|potent)\s+(?:{CYP}\s+)?inhibitors?\s+of\s+{CYP}"
    rf"|(?:strong|potent)\s+{CYP}\s+inhibitors?", re.IGNORECASE)
INDUCER_CTX = re.compile(rf"inducers?\s+of\s+{CYP}|{CYP}\s+inducers?", re.IGNORECASE)
SUBSTRATE_CTX = re.compile(rf"substrates?\s+(?:of|for)\s+{CYP}|{CYP}\s+substrates?",
                           re.IGNORECASE)

NEG = re.compile(r"\b(?:not|no|little|neither|nor|without|minimal|non|un)\b",
                 re.IGNORECASE)
STRENGTH_WORDS = ("strong", "potent", "moderate", "weak")

# Enumeration membership: a cue attributes its role to a drug only when the drug
# is *structurally* part of the cue's enumeration, not merely nearby. This is
# what keeps precision at 1.00 across accidental sentence-splitter merges (e.g.
# ritonavir's contraindication block fuses a substrate drug-list with a later
# "drugs that are potent CYP3A inducers" clause — proximity alone would
# mis-tag the trailing substrate midazolam as an inducer).
#   * FORWARD list  — "<cue> such as / including / e.g. / : / ( X, Y, Z":
#       the drug follows the cue via an enumeration introducer and precedes any
#       list terminator (a closing paren or a new sentence).
#   * APPOSITIVE / subject — "X, an inhibitor of CYP3A4",
#       "X and Y are substrates of CYP3A4": the drug immediately precedes the
#       cue with only connective tokens between (no generic class noun like
#       "drugs"/"agents", no other role noun, no sentence break).
ENUM_INTRO = re.compile(
    r"^\s*(?:such as|including|includes?|like|e\.?\s?g\.?,?|:|\()", re.IGNORECASE)
# generic class noun or a competing role noun between drug and cue => the cue's
# subject is something other than this drug
BLOCK_NOUN = re.compile(
    r"\b(?:drugs?|agents?|medications?|compounds?|substances?|products?"
    r"|substrates?|inhibitors?|inducers?)\b", re.IGNORECASE)
FWD_MAX = 200   # a forward "such as ..." list rarely runs longer
BACK_MAX = 40   # appositive/subject phrases are short
# a co-administration preposition means the drug is used *with* the cue's agents,
# not that it *is* one ("clarithromycin ... concomitantly with CYP3A4 substrates"
# does NOT make clarithromycin a substrate)
CO_ADMIN = re.compile(
    r"\b(?:with|when|receiving|taking|concomitant\w*|co-?administ\w*"
    r"|administered|combination)\b", re.IGNORECASE)
# the drug must be bound to the cue by a copula / appositive ("X, an inhibitor",
# "X is a substrate", "X and Y are substrates") to be the cue's subject
COPULA_START = re.compile(r"^,?\s*(?:an?|is|are|was|were)\b", re.IGNORECASE)
COPULA_END = re.compile(r"\b(?:is|are|was|were)\s+(?:an?\s+|also\s+)*$", re.IGNORECASE)


def enum_member(sent, d0, d1, c0, c1):
    """Is the drug span [d0,d1) a member of the cue span [c0,c1)'s enumeration?"""
    if d0 >= c1:                              # drug AFTER cue -> forward list
        gap = sent[c1:d0]
        if len(gap) > FWD_MAX or not ENUM_INTRO.match(gap):
            return False
        return ")" not in gap and ". " not in gap
    gap = sent[d1:c0]                         # drug BEFORE cue -> appositive/subject
    if len(gap) > BACK_MAX or "." in gap or BLOCK_NOUN.search(gap):
        return False
    if CO_ADMIN.search(gap):
        return False
    return bool(COPULA_START.match(gap.strip()) or COPULA_END.search(gap))


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def load_crosswalk(path):
    drugs = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            drugs[row["ingredient_en"].strip().lower()] = row
    return drugs


def has_cyp_edge(edges, role):
    for e in edges:
        if str(e.get("enzyme", "")).upper().replace(" ", "") == "CYP3A4" \
                and e.get("role") == role and not e.get("negated"):
            return True
    return False


def strength_in(span):
    low = span.lower()
    if "strong" in low or "potent" in low:
        return "strong"
    if "moderate" in low:
        return "moderate"
    if "weak" in low:
        return "weak"
    return None


def negated_before(sent, pos, window=45):
    """True if a negation token appears in the `window` chars before `pos`."""
    return bool(NEG.search(sent[max(0, pos - window):pos]))


def _edge(role, strength):
    if role == "inhibitor":
        action = "contraindicated" if strength == "strong" else "dose-adjust"
    elif role == "inducer":
        action = "monitor"
    else:
        action = None
    return strength, action


# --- Mechanism 1: enumeration mining ------------------------------------------
def mine_enumeration(host, sent, xwalk, drugs, out):
    cues = [("inhibitor", m.start(), m.end()) for m in INHIB_CTX.finditer(sent)]
    cues += [("inducer", m.start(), m.end()) for m in INDUCER_CTX.finditer(sent)]
    cues += [("substrate", m.start(), m.end()) for m in SUBSTRATE_CTX.finditer(sent)
             if not negated_before(sent, m.start())]
    if not cues:
        return
    is_strong_inhib = bool(STRONG_INHIB_CTX.search(sent))
    strong_inducer = "strong" in sent.lower()
    low = sent.lower()
    for name in xwalk:
        best = None  # (distance, role)
        for dm in re.finditer(rf"\b{re.escape(name)}\b", low):
            for role, c0, c1 in cues:
                if not enum_member(sent, dm.start(), dm.end(), c0, c1):
                    continue
                dist = dm.start() - c1 if dm.start() >= c1 else c0 - dm.end()
                if best is None or dist < best[0]:
                    best = (dist, role)
        if best is None:
            continue
        role = best[1]
        # perpetrator roles are never self-attributed by enumeration (the host
        # of an enumeration is the victim/substrate, not the inhibitor/inducer)
        if role in ("inhibitor", "inducer") and name == host:
            continue
        if role == "inhibitor":
            strength = "strong" if is_strong_inhib else None
        elif role == "inducer":
            strength = "strong" if strong_inducer else None
        else:
            strength = None
        out.append((name, role, strength, host, sent))


# --- Mechanism 2: name-anchored self-attribution ------------------------------
def mine_self_attribution(host, sent, xwalk, out):
    n = re.escape(host)
    if host not in xwalk:
        return
    if not re.search(rf"\b{n}\b", sent, re.IGNORECASE):
        return
    # substrate / metabolism predication about the host itself
    sub_pats = [
        rf"\b{n}\b[^.;]{{0,25}}?\bis\b[^.;]{{0,20}}?substrates?\s+(?:of|for)\s+{CYP}",
        rf"\b{n}\b\s+is\s+(?:primarily\s+|extensively\s+|mainly\s+)?"
        rf"metaboli[sz]ed\s+(?:primarily\s+|mainly\s+)?(?:by|via|through)\s+"
        rf"(?:the\s+)?(?:hepatic\s+)?(?:enzyme\s+)?{CYP_TOKEN}",
        rf"biotransformation\s+of\s+{n}\b[^.;]{{0,30}}?{CYP_TOKEN}",
        rf"metabolism\s+of\s+{n}\b[^.;]{{0,30}}?{CYP_TOKEN}",
    ]
    for pat in sub_pats:
        m = re.search(pat, sent, re.IGNORECASE)
        if m and not negated_before(sent, m.end() - 4, window=60) \
                and not NEG.search(m.group(0)):
            out.append((host, "substrate", None, host, sent))
            break
    # inhibitor predication: "<host> ... is a <strength> inhibitor of CYP3A(4)"
    inhib_pats = [
        rf"\b{n}\b[^.;]{{0,40}}?\bis\b[^.;]{{0,30}}?(?:an?\s+)?"
        rf"((?:strong|potent|moderate|weak)\s+)?(?:{CYP}\s+)?inhibitor\s+of\s+{CYP}",
        rf"\b{n}\b[^.;]{{0,40}}?\bis\b[^.;]{{0,30}}?(?:an?\s+)?"
        rf"((?:strong|potent|moderate|weak)\s+){CYP}\s+inhibitors?",
    ]
    for pat in inhib_pats:
        m = re.search(pat, sent, re.IGNORECASE)
        if m and not NEG.search(m.group(0)):
            out.append((host, "inhibitor", strength_in(m.group(0)), host, sent))
            break
    # inducer predication: "<host> ... is a <strength> inducer of CYP3A(4)"
    induc_pats = [
        rf"\b{n}\b[^.;]{{0,40}}?\bis\b[^.;]{{0,30}}?(?:an?\s+)?"
        rf"((?:strong|potent|moderate|weak)\s+)?(?:{CYP}\s+)?inducer\s+of\s+{CYP}",
        rf"\b{n}\b[^.;]{{0,40}}?\bis\b[^.;]{{0,30}}?(?:an?\s+)?"
        rf"((?:strong|potent|moderate|weak)\s+){CYP}\s+inducers?",
    ]
    for pat in induc_pats:
        m = re.search(pat, sent, re.IGNORECASE)
        if m and not NEG.search(m.group(0)):
            out.append((host, "inducer", strength_in(m.group(0)), host, sent))
            break


def main():
    corpus_p, ext_p, xwalk_p, out_p = sys.argv[1:5]
    corpus = json.load(open(corpus_p, encoding="utf-8"))
    extracted = json.load(open(ext_p, encoding="utf-8"))
    xwalk = load_crosswalk(xwalk_p)
    drugs = extracted["drugs"]

    raw = []  # (target, role, strength, source_host, sentence)
    for host, rec in corpus.items():
        for sec, text in rec.get("sections", {}).items():
            for sent in split_sentences(text):
                mine_enumeration(host, sent, xwalk, drugs, raw)
                mine_self_attribution(host, sent, xwalk, raw)

    # keep only edges whose role the single-direction pass missed
    raw = [r for r in raw
           if not has_cyp_edge(drugs.get(r[0], {}).get("edges", []), r[1])]

    # dedupe by (target, role); prefer a graded-strength witness
    best = {}
    for target, role, strength, host, sent in raw:
        k = (target, role)
        cur = best.get(k)
        if cur is None or (strength and not cur[1]):
            best[k] = (target, role, strength, host, sent)

    out = json.loads(json.dumps(extracted))  # deep copy
    out["direction"] = ("bidirectional (own-label self-attribution + "
                        "cross-label enumeration recovery)")
    n_added = 0
    for target, role, strength, host, sent in sorted(best.values()):
        strength, action = _edge(role, strength)
        edge = {
            "role": role, "enzyme": "CYP3A4", "strength": strength,
            "clinical_action": action,
            "evidence_sentence": sent[:300], "negated": False,
            "confidence": 0.75,
            "recovered_from": f"{role}-cue:{host}-label",
        }
        out["drugs"].setdefault(target, {"edges": []})["edges"].append(edge)
        n_added += 1
        print(f"  recovered {target:14s} {role:9s} (strength={strength}) "
              f"<- {host} label")

    json.dump(out, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nrecovered {n_added} edge(s) -> {out_p}")


if __name__ == "__main__":
    main()

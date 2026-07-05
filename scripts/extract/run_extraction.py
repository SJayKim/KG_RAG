"""Gate 4 step 2: extract typed CYP edges from the openFDA label corpus.

Two extractors, same output schema, so the scorer compares apples to apples:

  --extractor regex   deterministic, no API key, runs today. Baseline that
                      shows how far "the sentences are clean" (Gate 2) gets us.
  --extractor llm     Claude, the real strategy. Needs ANTHROPIC_API_KEY.

Output schema per edge (DESIGN C1/H4):
  role            substrate | inhibitor | inducer
  enzyme          e.g. CYP3A4
  strength        strong | moderate | weak | null
  clinical_action contraindicated | avoid | dose-adjust | monitor | none | null
  evidence_sentence  verbatim label quote (provenance)
  negated         bool
  confidence      0..1

The extractor's job is the DRUG'S OWN enzyme relationships, not roles of other
drugs the label happens to name. That subject-attribution problem is the whole
reason the LLM path exists — the regex baseline is deliberately literal so the
gap is measurable.

Run:
  PYTHONUTF8=1 python scripts/extract/run_extraction.py --extractor regex \
      fixtures/openfda-labels/corpus.json fixtures/openfda-labels/extracted_regex.json
  ANTHROPIC_API_KEY=... python scripts/extract/run_extraction.py --extractor llm \
      --model claude-sonnet-5 fixtures/openfda-labels/corpus.json \
      fixtures/openfda-labels/extracted_llm.json
"""
import argparse
import json
import os
import re
import sys

CYP_RE = re.compile(r"CYP\s?3\s?A\s?4", re.IGNORECASE)


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


# --------------------------------------------------------------------------- #
# Regex baseline extractor (deterministic, no key)
# --------------------------------------------------------------------------- #

# Self-attribution: the sentence must name THIS drug as the subject of the CYP
# relationship. We accept the generic name or a leading pronoun-ish reference.
STRONG_RE = re.compile(r"\b(strong|potent)\b", re.IGNORECASE)
MODERATE_RE = re.compile(r"\bmoderate\b", re.IGNORECASE)
WEAK_RE = re.compile(r"\bweak\b", re.IGNORECASE)

NEG_RE = re.compile(
    r"\b(not|no|neither|does not|is not|are not|without)\b", re.IGNORECASE
)


def _strength(sent):
    if STRONG_RE.search(sent):
        return "strong"
    if MODERATE_RE.search(sent):
        return "moderate"
    if WEAK_RE.search(sent):
        return "weak"
    return None


def _clinical_action(sent):
    s = sent.lower()
    if "contraindicated" in s:
        return "contraindicated"
    if re.search(r"\bavoid\b", s):
        return "avoid"
    if re.search(r"do not exceed|not exceed|limit|reduce (the )?dose|lower (the )?dose|dose reduction|maximum", s):
        return "dose-adjust"
    if "monitor" in s:
        return "monitor"
    return None


def regex_extract(drug, sections):
    """Emit the drug's OWN CYP3A4 edges, requiring self-attribution."""
    name = re.escape(drug)
    # subject patterns: "<drug> is (a|an) ... substrate/inhibitor/inducer of CYP3A4"
    # or "<drug> is metabolized by CYP3A4" / "<drug> inhibits/induces CYP3A4"
    subj = rf"\b{name}\b"
    edges = []
    seen = set()
    for sec, text in sections.items():
        for sent in split_sentences(text):
            if not CYP_RE.search(sent):
                continue
            if not re.search(subj, sent, re.IGNORECASE):
                continue  # not about THIS drug -> skip (honest baseline limit)
            low = sent.lower()
            role = None
            if re.search(rf"{subj}[^.]*\b(substrate|metaboli[sz]ed by)\b", sent, re.IGNORECASE) \
                    and "cyp3a4" in low.replace(" ", ""):
                role = "substrate"
            if re.search(rf"{subj}[^.]*\b(inhibitor|inhibits|inhibition)\b", sent, re.IGNORECASE):
                role = "inhibitor"
            if re.search(rf"{subj}[^.]*\b(inducer|induces|induction)\b", sent, re.IGNORECASE):
                role = "inducer"
            if role is None:
                continue
            negated = bool(NEG_RE.search(low.split("cyp")[0])) and role != "substrate"
            key = (role, "CYP3A4")
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "role": role,
                "enzyme": "CYP3A4",
                "strength": _strength(sent) if role != "substrate" else None,
                "clinical_action": _clinical_action(sent) if role != "substrate" else None,
                "evidence_sentence": sent[:400],
                "negated": negated,
                "confidence": 0.5,
            })
    return edges


# --------------------------------------------------------------------------- #
# LLM extractor (Claude)
# --------------------------------------------------------------------------- #

LLM_SYSTEM = """You are a clinical pharmacology extraction engine. Given a US
drug label, extract ONLY the labeled drug's OWN cytochrome-P450 enzyme
relationships. Do not report roles that belong to OTHER drugs the label
mentions (labels for a substrate often name their inhibitors, and vice versa —
attribute the role to the correct subject).

Return STRICT JSON: a list of edge objects. One object per (role, enzyme) the
LABELED DRUG has. Fields:
  role: "substrate" | "inhibitor" | "inducer"
  enzyme: e.g. "CYP3A4"
  strength: "strong" | "moderate" | "weak" | null   (null for substrate)
  clinical_action: "contraindicated" | "avoid" | "dose-adjust" | "monitor" | "none" | null
  evidence_sentence: the verbatim sentence you based this on
  negated: true if the label states the drug is NOT this role
  confidence: 0.0-1.0

If the labeled drug has no CYP relationship of its own, return [].
Output ONLY the JSON array, no prose."""


def llm_extract(drug, sections, model):
    import anthropic

    client = anthropic.Anthropic()
    body = "\n\n".join(f"## {sec}\n{text}" for sec, text in sections.items())
    user = f"Labeled drug: {drug}\n\nLabel sections:\n{body}\n\nExtract {drug}'s own CYP edges as JSON."
    resp = client.messages.create(
        model=model,
        max_tokens=1500,
        system=LLM_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    # models with extended thinking emit a ThinkingBlock before the text block,
    # so pick the text block(s) rather than assuming content[0] is text
    raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    # tolerate ```json fences
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        edges = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    # keep only well-formed edges
    out = []
    for e in edges:
        if not isinstance(e, dict) or "role" not in e or "enzyme" not in e:
            continue
        out.append({
            "role": e.get("role"),
            "enzyme": e.get("enzyme"),
            "strength": e.get("strength"),
            "clinical_action": e.get("clinical_action"),
            "evidence_sentence": (e.get("evidence_sentence") or "")[:400],
            "negated": bool(e.get("negated", False)),
            "confidence": e.get("confidence", 0.5),
        })
    return out


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("out")
    ap.add_argument("--extractor", choices=["regex", "llm"], default="regex")
    ap.add_argument("--model", default="claude-sonnet-5")
    args = ap.parse_args()

    with open(args.corpus, encoding="utf-8") as f:
        corpus = json.load(f)

    if args.extractor == "llm" and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: --extractor llm needs ANTHROPIC_API_KEY in the environment.")

    results = {"extractor": args.extractor, "model": args.model if args.extractor == "llm" else None, "drugs": {}}
    for drug, rec in corpus.items():
        if not rec.get("found"):
            results["drugs"][drug] = {"edges": [], "skipped": "label not found"}
            continue
        sections = rec.get("sections", {})
        if args.extractor == "regex":
            edges = regex_extract(drug, sections)
        else:
            edges = llm_extract(drug, sections, args.model)
        results["drugs"][drug] = {"edges": edges}
        cyp = [e for e in edges if str(e.get("enzyme", "")).upper().replace(" ", "") == "CYP3A4"]
        print(f"  {drug:16s} {len(cyp)} CYP3A4 edge(s): {[e['role'] for e in cyp]}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()

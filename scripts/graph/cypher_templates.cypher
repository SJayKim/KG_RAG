// PolyPharmGraph — transitive CYP interaction query templates.
// Both templates are parameterized on $regimen (a list of Ingredient D-codes).
// The significance filter (strength IN ['strong','moderate'], NOT negated,
// clinical_action <> 'none') is LOAD-BEARING: it is what separates a real
// interaction from a shared-enzyme false positive (see gold case G4).

// ---------------------------------------------------------------------------
// Template 1: inhibitor + substrate, DIRECT exposure rise.
// Fires only when both drugs are in the regimen and the label supports a
// clinical action (contraindicated / dose-adjust), not a bare mention.
// ---------------------------------------------------------------------------
// :param regimen => ['D000027','D000373', ...]
MATCH (a:Ingredient)-[i:INHIBITS]->(e:Enzyme)<-[s:SUBSTRATE_OF]-(c:Ingredient)
WHERE a.code IN $regimen AND c.code IN $regimen AND a <> c
  AND i.strength IN ['strong','moderate']
  AND i.clinical_action <> 'none' AND NOT i.negated
RETURN a.name_eng AS inhibitor, e.name AS enzyme, c.name_eng AS affected_substrate,
       i.evidence_sentence AS why, i.strength AS strength;

// ---------------------------------------------------------------------------
// Template 2: inducer + substrate, TRANSITIVE exposure drop (therapy failure).
// This is the direction naive toxicity scanners miss — the typed INDUCES edge
// preserves the "decreased exposure" semantics.
// ---------------------------------------------------------------------------
// :param regimen => ['D000314','D000027', ...]
MATCH (a:Ingredient)-[d:INDUCES]->(e:Enzyme)<-[s:SUBSTRATE_OF]-(c:Ingredient)
WHERE a.code IN $regimen AND c.code IN $regimen AND a <> c
  AND d.strength IN ['strong','moderate'] AND NOT d.negated
RETURN a.name_eng AS inducer, e.name AS enzyme, c.name_eng AS affected_substrate;

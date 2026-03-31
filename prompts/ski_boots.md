Additional instructions for SKI BOOTS analysis:

Pay special attention to:
- Flex index (stiffness) — determine from model name or visible markings
- Shell size vs mondo size — check if stated size matches what you see
- Buckle condition — all buckles present and functional?
- Sole condition — worn down? Compatible with modern bindings (GripWalk, ISO 5355)?
- Liner condition — visible wear, compression, or damage?
- Shell cracks — check around the cuff, toe box, and heel
- Age of the boot — polyurethane degrades over time (boots older than 8-10 years may be unsafe)
- Skill level match — is this a beginner, intermediate, or advanced boot?

Add these fields to your JSON response:
{
  "flex_index": "... or null",
  "sole_type": "ISO 5355 | GripWalk | Touring | unknown",
  "sole_condition": "good | worn | needs_replacement",
  "buckles_ok": true/false,
  "estimated_age_years": ...,
  "skill_level": "beginner | intermediate | advanced | race",
  "safety_warning": "... or null"
}
Additional instructions for SKIS analysis:

Pay special attention to:
- Ski length — does it match what's stated?
- Base condition — scratches, core shots, edge damage visible?
- Edge condition — rusty, sharp, or rounded?
- Top sheet condition — delamination, chips, cracks?
- Bindings included? If yes — brand, model, DIN range, condition
- Ski type — all-mountain, piste, freeride, touring, park
- Rocker profile — camber, rocker, flat (if visible)
- Recommended skier weight/height for the stated length

Add these fields to your JSON response:
{
  "ski_length_cm": ...,
  "ski_type": "piste | all-mountain | freeride | touring | park | race",
  "base_condition": "good | scratched | core_shots | needs_service",
  "edge_condition": "sharp | dull | rusty | damaged",
  "bindings_included": true/false,
  "binding_info": {"brand": "...", "model": "...", "din_range": "..."} or null,
  "recommended_skier": "height and weight range"
}
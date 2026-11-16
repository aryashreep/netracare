"""Centralised, safety-critical string constants.

These live in code, not in LLM prompts or UI strings, because they are
part of the clinic's public safety contract (brief §04-R4, §05, §09).
Changing any of these requires a spec amendment.
"""

# Shown verbatim to the patient and Staff on every red-flag outcome,
# before any booking result. The LLM NEVER produces this text — it is
# always appended by the backend so a prompt regression cannot
# weaken it.
EMERGENCY_MESSAGE = (
    "What you describe needs urgent attention. "
    "Please come to the clinic now or go to the nearest emergency department. "
    "Our staff have been notified."
)

# Shown under every Fact of the Day. Rendered by the Fact endpoint and the
# UI; never templated through the LLM so a prompt regression cannot drop it.
FACT_CAVEAT = "General information, not medical advice"

# Shown in place of a generated fact when the LLM is unavailable.
FACT_FALLBACK = (
    "Looking at something 20 feet away for 20 seconds every 20 minutes "
    "helps rest tired eyes."
)

# Shown in the summary slot when the LLM is unavailable. The raw notes are
# ALWAYS rendered beneath this line.
SUMMARY_FALLBACK = "Summary unavailable. See the notes below."

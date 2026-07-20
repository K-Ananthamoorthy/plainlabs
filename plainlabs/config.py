"""Single place to tune PlainLabs. Model choice is config, not architecture."""
import os

# Local SLM (Ollama). gemma4:e2b-it-qat is the target; llama3.2:3b is a fallback
# for machines without the gemma pull yet.
SLM_MODEL = os.getenv("PLAINLABS_SLM", "gemma4:e2b-it-qat")
SLM_TEMPERATURE = 0.0          # deterministic-ish: we want stable narrow answers

# Escalation (heterogeneous cascade). Empty key or --local-only disables it.
GROQ_MODEL = os.getenv("PLAINLABS_GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CONFIDENCE_SAMPLES = 3         # self-consistency runs for the confidence gate
DISCLAIMER = (
    "This is an automated explanation for general understanding only. "
    "It is not a diagnosis. Always discuss your results with a doctor."
)

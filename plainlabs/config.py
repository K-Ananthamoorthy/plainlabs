"""Single place to tune PlainLabs. Model choice is config, not architecture."""
import os

# Local SLM (Ollama). MedGemma 4B — Google's medically-tuned Gemma 3, trained for
# medical text and lab-report extraction (HAI-DEF license). Still used for LANGUAGE
# only; the medical decisions remain deterministic code. Override for any Ollama model.
SLM_MODEL = os.getenv("PLAINLABS_SLM", "medgemma:4b")
SLM_TEMPERATURE = 0.0          # deterministic-ish: we want stable narrow answers

# Escalation (heterogeneous cascade). Empty key or --local-only disables it.
GROQ_MODEL = os.getenv("PLAINLABS_GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CONFIDENCE_SAMPLES = 3         # self-consistency runs for the confidence gate
DISCLAIMER = (
    "This is an automated explanation for general understanding only. "
    "It is not a diagnosis. Always discuss your results with a doctor."
)

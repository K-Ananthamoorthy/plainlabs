"""Make `streamlit run app.py` self-sufficient: start Ollama and ready MedGemma.

So the user runs one command and everything comes up — no separate `ollama serve`
terminal, and the model is warmed so the first report isn't slow.
"""
import json
import subprocess
import time
import urllib.request

from plainlabs.config import SLM_MODEL

HOST = "http://localhost:11434"


def _up() -> bool:
    try:
        urllib.request.urlopen(HOST, timeout=1)
        return True
    except Exception:
        return False


def _model_present(model: str) -> bool:
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=3) as r:
            names = {m["name"] for m in json.load(r).get("models", [])}
        return model in names or f"{model}:latest" in names or any(n.startswith(model) for n in names)
    except Exception:
        return False


def ensure_ollama(model: str = SLM_MODEL) -> tuple[bool, str]:
    """Start `ollama serve` if needed and confirm the model is pulled."""
    if not _up():
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return False, "Ollama isn't installed. See https://ollama.com"
        for _ in range(30):
            if _up():
                break
            time.sleep(1)
        else:
            return False, "Could not start Ollama. Try running `ollama serve` manually."

    if not _model_present(model):
        return False, f"Ollama is running, but '{model}' isn't pulled. Run:  ollama pull {model}"
    return True, f"Ollama running · {model} ready"


def warm(model: str = SLM_MODEL, timeout: int = 180) -> None:
    """Best-effort: load the model into memory so the first real call is fast."""
    try:
        data = json.dumps({"model": model, "prompt": "hi", "stream": False}).encode()
        req = urllib.request.Request(
            f"{HOST}/api/generate", data=data, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=timeout)
    except Exception:
        pass  # not fatal — it will load on first use

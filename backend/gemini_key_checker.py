#!/usr/bin/env python3
"""
gemini_key_checker.py

- Lists models available to the provided Gemini / Generative Language API key.
- Infers whether Pro/paid models are available.
- Attempts a tiny generation test using a safe model (prefers Flash/Flash-Lite).
- Fixes the common "unexpected model name format" error by normalizing model names
  (strip leading "models/" before using in generate endpoint).

Usage:
  - Edit GEMINI_API_KEY below or set environment variable GEMINI_API_KEY.
  - Run: python gemini_key_checker.py
"""

import os
import sys
import json
from urllib.parse import quote_plus
import requests

# >>> Put your key here, or set environment variable GEMINI_API_KEY
GEMINI_API_KEY = "AIzaSyBlmGv3to46cdw5fjIfDWhfTDXsTd4_tsc"

# prefer environment variable if present
if os.getenv("GEMINI_API_KEY"):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 15  # seconds


def pretty(o):
    print(json.dumps(o, indent=2, ensure_ascii=False))


def interpret_status(code):
    if code is None:
        return "No HTTP response (network error)."
    if code == 200:
        return "OK (200) — request succeeded."
    if code == 401:
        return "Unauthorized (401) — API key is invalid or not accepted."
    if code == 403:
        return ("Forbidden (403) — API key is valid but access to the resource is denied. "
                "This can mean the key is restricted, the model is paywalled, or billing is required.")
    if code == 404:
        return "Not Found (404) — resource (model/endpoint) not found for this API version or key."
    if code == 429:
        return "Rate limited / quota exceeded (429)."
    if 400 <= code < 500:
        return f"Client error ({code})."
    if 500 <= code < 600:
        return f"Server error ({code}) — try again later."
    return f"HTTP {code}"


def get_models(api_key):
    url = f"{BASE_MODELS_URL}?key={quote_plus(api_key)}"
    try:
        r = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        return {"status_code": None, "error": f"Network error: {e}"}
    result = {"status_code": r.status_code}
    try:
        result["json"] = r.json()
    except Exception:
        result["text"] = r.text
    return result


def infer_tier_from_models(models_json):
    models = models_json.get("models", []) or []
    found = {"pro": [], "flash": [], "flash_lite": [], "other": []}
    for m in models:
        name = (m.get("name") or "") + " " + (m.get("displayName") or "") + " " + (m.get("baseModelId") or "")
        joined = name.lower()
        # classify
        if "pro" in joined:
            found["pro"].append(m.get("name") or m.get("displayName") or "")
        elif "flash-lite" in joined or "lite" in joined:
            found["flash_lite"].append(m.get("name") or m.get("displayName") or "")
        elif "flash" in joined:
            found["flash"].append(m.get("name") or m.get("displayName") or "")
        else:
            found["other"].append(m.get("name") or m.get("displayName") or "")
    return found


def normalize_model_name(raw):
    """Strip leading 'models/' if present and return model id string."""
    if not raw:
        return raw
    if raw.startswith("models/"):
        return raw.split("/", 1)[1]
    return raw


def pick_model_for_test(models_json):
    """
    Heuristics:
      1. Prefer Flash-Lite or Flash models (lower cost / safer).
      2. Otherwise pick a generate-capable model if metadata suggests generation.
      3. Fallback to the first model in the list.
    Returns the normalized model id (without 'models/' prefix).
    """
    models = models_json.get("models", []) or []
    if not models:
        return None

    # helper to get candidate name strings
    def nm(m):
        return (m.get("name") or "") + " " + (m.get("displayName") or "") + " " + (m.get("baseModelId") or "")

    # prefer flash-lite
    for m in models:
        if "flash-lite" in nm(m).lower() or "flash lite" in nm(m).lower() or "lite" in nm(m).lower():
            return normalize_model_name(m.get("name") or m.get("displayName") or m.get("baseModelId"))

    # prefer flash
    for m in models:
        if "flash" in nm(m).lower():
            return normalize_model_name(m.get("name") or m.get("displayName") or m.get("baseModelId"))

    # try to detect generate-capable models by searching the JSON body for keywords
    for m in models:
        joined = json.dumps(m).lower()
        if any(tok in joined for tok in ("generatecontent", "generatemessage", "predict", "outputs", "generate_text")):
            return normalize_model_name(m.get("name") or m.get("displayName") or m.get("baseModelId"))

    # fallback: first model
    first = models[0]
    return normalize_model_name(first.get("name") or first.get("displayName") or first.get("baseModelId"))


def test_generate(api_key, model_name, prompt="Ping. Respond only with: OK"):
    """POST models/{model}:generateContent?key=KEY  -- model_name must be normalized (no leading 'models/')."""
    if not model_name:
        return {"status_code": None, "error": "No model provided for generate test."}

    model_name = normalize_model_name(model_name)
    url = f"{BASE_MODELS_URL}/{quote_plus(model_name)}:generateContent?key={quote_plus(api_key)}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        # small request body to minimize cost; adjust for API changes if needed
    }
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        return {"status_code": None, "error": f"Network error: {e}"}
    result = {"status_code": r.status_code}
    try:
        result["json"] = r.json()
    except Exception:
        result["text"] = r.text
    return result


def extract_text_from_generate_response(j):
    # Many possible shapes; try reasonable heuristics
    if not isinstance(j, dict):
        return None
    # common shapes
    # look at top-level 'candidates'
    if "candidates" in j and isinstance(j["candidates"], list) and j["candidates"]:
        cand = j["candidates"][0]
        for k in ("content", "text", "output"):
            if k in cand:
                return cand[k]
    # outputs / output
    for k in ("outputs", "output", "response", "result", "content"):
        v = j.get(k)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, dict):
                for tk in ("text", "content", "output", "response"):
                    if tk in first:
                        return first[tk]
            elif isinstance(first, str):
                return first
        elif isinstance(v, dict):
            for tk in ("text", "content", "output", "response"):
                if tk in v:
                    return v[tk]
        elif isinstance(v, str):
            return v
    # fallback: search for any string field
    def walk(o):
        if isinstance(o, str):
            return o
        if isinstance(o, dict):
            for _, val in o.items():
                res = walk(val)
                if res:
                    return res
        if isinstance(o, list):
            for item in o:
                res = walk(item)
                if res:
                    return res
        return None
    return walk(j)


def main():
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("<YOUR"):
        print("ERROR: Put your Gemini API key in GEMINI_API_KEY variable or set environment GEMINI_API_KEY.")
        sys.exit(1)

    print("\n1) Listing models (this checks whether the key is accepted by the Models API)...\n")
    models_resp = get_models(GEMINI_API_KEY)
    status = models_resp.get("status_code")
    print(f"HTTP status: {status}")
    print(interpret_status(status))

    if status != 200:
        if "json" in models_resp:
            print("\nServer JSON response:")
            pretty(models_resp["json"])
        elif "text" in models_resp:
            print("\nServer text response:")
            print(models_resp["text"])
        else:
            print("\nNo additional server response available.")
        print("\nInterpretation & next steps: check key, restrictions and billing in Google AI Studio / Cloud Console.")
        return

    models_json = models_resp.get("json", {})
    models_list = models_json.get("models", []) or []
    print(f"\nFound {len(models_list)} models available to this key (first 30 listed):")
    for i, m in enumerate(models_list[:30], start=1):
        # show the returned full name (may include 'models/...' prefix)
        full = m.get("name") or m.get("displayName") or "<unknown>"
        disp = m.get("displayName") or ""
        print(f" {i:2d}. {full}  ({disp})")

    # infer tier
    inferred = infer_tier_from_models(models_json)
    if inferred["pro"]:
        print("\n=> PRO models are visible to this key (examples):")
        for x in inferred["pro"][:10]:
            print("   -", x)
        print("\nInterpretation: Your key appears to have access to Pro-class models (likely paid/premium access).")
    else:
        print("\n=> No 'Pro' model names detected among returned models.")
        sample = (inferred["flash_lite"][:2] or inferred["flash"][:2] or inferred["other"][:2])
        if sample:
            print("   Example available models:", ", ".join(sample))

    # pick model for test (prefer flash / flash-lite to reduce billing risk)
    model_for_test = pick_model_for_test(models_json)
    if not model_for_test:
        print("\nNo suitable model found to run a generate test. You can still inspect the models list above.")
        return

    print(f"\n2) Will attempt a tiny generateContent using model: {model_for_test}")
    # warn user if model name contains 'pro' just in case
    if "pro" in (model_for_test or "").lower():
        print("WARNING: The model name suggests 'pro'. Invoking it may incur charges if your account is on a paid tier.")
    gen_resp = test_generate(GEMINI_API_KEY, model_for_test, prompt="Ping. Reply only with: OK")
    print(f"HTTP status: {gen_resp.get('status_code')}")
    print(interpret_status(gen_resp.get('status_code')))

    if gen_resp.get("status_code") == 200 and "json" in gen_resp:
        j = gen_resp["json"]
        extracted = extract_text_from_generate_response(j)
        if extracted:
            print("\nReceived text (truncated):")
            print(str(extracted)[:1000])
        else:
            print("\nCouldn't extract plain text from response. Raw JSON (truncated):")
            pretty(j)
    else:
        # show server JSON or text for debugging
        if "json" in gen_resp:
            print("\nServer JSON response (for generate attempt):")
            pretty(gen_resp["json"])
        elif "text" in gen_resp:
            print("\nServer text response (for generate attempt):")
            print(gen_resp["text"])
        else:
            print("\nNo server response body available for the generate attempt.")

    print("\n3) Final notes & recommendations:")
    print("- Listing models succeeded → your key is valid for model listing.")
    print("- Seeing 'pro' models in the model list strongly suggests you have paid/pro access, but check Google Cloud / AI Studio billing to be sure.")
    print("- If you saw: 'GenerateContentRequest.model: unexpected model name format', it means you were passing 'models/<id>' instead of just '<id>'.")
    print("- To avoid accidental billing during tests, prefer Flash or Flash-Lite models (this script tries to do that).")
    print("\nDone.")


if __name__ == "__main__":
    main()

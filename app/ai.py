from __future__ import annotations
import base64
import os
from typing import Sequence
from .models import Bill

PROMPT = """
You are a receipt/bill extraction engine.

Read every uploaded restaurant bill image carefully. The images may be angled,
crumpled, faded, handwritten, multilingual, or may represent different parts
of the same long bill.

Return ONLY data matching the provided Bill schema.

Rules:
- Extract every purchased line item.
- quantity is the number printed for the line.
- unit_price is price per unit.
- total_price is quantity * unit_price as printed/calculated for that line.
- Extract subtotal, discount, service charge, CGST, SGST, other taxes and printed total.
- Do not invent a tax or charge that is not visible.
- Preserve the printed total even when it looks mathematically wrong.
- Confidence is a number from 0 to 1 for each item and an overall score.
- If a value is unreadable, use 0 for numeric optional fields and explain uncertainty
  in the confidence note instead of guessing.
- For multiple images, combine them into ONE bill and do not duplicate overlapping lines.
- Currency should be inferred from the bill; use INR when the bill is clearly Indian.
"""


def demo_bill() -> Bill:
    return Bill.model_validate({
        "restaurant_name": "Demo Spice House",
        "currency": "INR",
        "items": [
            {"name": "Chicken Biryani", "quantity": 2, "unit_price": 240,
             "total_price": 480, "confidence": {"value": 0.98}},
            {"name": "Coke", "quantity": 1, "unit_price": 60,
             "total_price": 60, "confidence": {"value": 0.96}},
            {"name": "Paneer Tikka", "quantity": 1, "unit_price": 320,
             "total_price": 320, "confidence": {"value": 0.89}},
        ],
        "subtotal": 860,
        "discount": 0,
        "service_charge": 86,
        "cgst": 42.3,
        "sgst": 42.3,
        "other_tax": 0,
        "printed_total": 1030.6,
        "overall_confidence": {"value": 0.94}
    })


def extract_bill(images: Sequence[tuple[bytes, str]]) -> Bill:
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        return demo_bill()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to .env or set DEMO_MODE=true."
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    contents = [PROMPT]
    for data, mime in images:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime))

    primary = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    fallback_raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash")
    models = [primary] + [m.strip() for m in fallback_raw.split(",") if m.strip() and m.strip() != primary]

    last_error = None
    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Bill,
                    temperature=0,
                ),
            )
            if not response.text:
                raise RuntimeError("Gemini returned an empty response.")
            return Bill.model_validate_json(response.text)
        except Exception as exc:
            last_error = exc
            error_text = str(exc).upper()
            # If a model is temporarily overloaded, automatically try the next one.
            if "503" in error_text or "UNAVAILABLE" in error_text or "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                continue
            raise

    raise RuntimeError(
        "Gemini models are temporarily unavailable. Tried: " + ", ".join(models)
        + f". Last error: {last_error}"
    )

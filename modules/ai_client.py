"""
X簿 - ai_client.py
Gemini API通信の抽象化モジュール
モデル名・Structured Outputの管理を一箇所に集約する
"""

from google import genai
from google.genai import types

# ===================================================
# モデル名（一箇所のみで管理。変更時はここだけ直す）
# ===================================================
MODEL_NAME = "gemini-3-flash-preview"


# ===================================================
# 振り返り用スキーマ
# ===================================================
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "good_points":  {"type": "string", "nullable": True},
        "concerns":     {"type": "string", "nullable": True},
        "next_actions": {
            "type": "array",
            "nullable": True,
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "keep_doing":   {"type": "string", "nullable": True},
        "data_status":  {
            "type": "string",
            "enum": ["sufficient", "insufficient", "no_data"],
        },
    },
    "required": ["data_status"],
}

# ===================================================
# Analytics抽出用スキーマ
# ===================================================
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "period_start":          {"type": "string", "nullable": True},
        "period_end":            {"type": "string", "nullable": True},
        "total_impressions":     {"type": "integer", "nullable": True},
        "total_likes":           {"type": "integer", "nullable": True},
        "total_reposts":         {"type": "integer", "nullable": True},
        "total_replies":         {"type": "integer", "nullable": True},
        "total_profile_clicks":  {"type": "integer", "nullable": True},
        "post_count":            {"type": "integer", "nullable": True},
        "summary":               {"type": "string", "nullable": True},
    },
    "required": ["summary"],
}


def _client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def generate_review(api_key: str, system_prompt: str, contents: str) -> dict:
    """
    日々の記録・Analyticsデータをもとに振り返りJSONを生成する。
    Structured Outputを使い、AIが必ずREVIEW_SCHEMAに沿ったJSONを返すようにする。
    """
    client = _client(api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.5,
            response_mime_type="application/json",
            response_schema=REVIEW_SCHEMA,
        ),
    )
    import json
    return json.loads(response.text)


def extract_from_csv(api_key: str, system_prompt: str, csv_text: str) -> dict:
    """CSVテキストから数値を抽出する（Structured Output）"""
    client = _client(api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"以下のCSVデータを読み取ってください。\n\n{csv_text}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=EXTRACT_SCHEMA,
        ),
    )
    import json
    return json.loads(response.text)


def extract_from_image(api_key: str, system_prompt: str, image_bytes: bytes, mime_type: str) -> dict:
    """画像から数値を抽出する（Structured Output）"""
    import base64
    client = _client(api_key)
    b64 = base64.b64encode(image_bytes).decode()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part(inline_data=types.Blob(mime_type=mime_type, data=b64)),
            types.Part(text="このスクショのデータを読み取ってください。"),
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=EXTRACT_SCHEMA,
        ),
    )
    import json
    return json.loads(response.text)

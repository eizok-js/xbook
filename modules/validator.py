"""
X簿 - validator.py
アップロードファイルのバリデーション（実体検証）
"""

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ファイル種別ごとのマジックバイト（ファイル先頭の固有バイト列）
MAGIC_BYTES = {
    "png":  [b"\x89PNG\r\n\x1a\n"],
    "jpg":  [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],  # WEBPは先頭4バイトがRIFF、8〜11バイト目がWEBP
}


def validate_size(file_bytes: bytes) -> tuple[bool, str]:
    """ファイルサイズを検証する"""
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "5MB以内のファイルを選択してください。"
    return True, ""


def validate_image_magic_bytes(file_bytes: bytes, extension: str) -> tuple[bool, str]:
    """
    画像ファイルの実体（マジックバイト）を確認する。
    拡張子を偽装したファイルを検出する。
    標準ライブラリのみで判定できるため追加ライブラリは不要。
    """
    ext = extension.lower().lstrip(".")
    patterns = MAGIC_BYTES.get(ext)
    if not patterns:
        return False, "対応していない画像形式です。"

    if ext == "webp":
        # WEBP: 先頭4バイト RIFF、8〜11バイト目 WEBP
        if len(file_bytes) < 12 or file_bytes[:4] != b"RIFF" or file_bytes[8:12] != b"WEBP":
            return False, "画像ファイルの内容が破損しているか、形式が正しくありません。"
        return True, ""

    if not any(file_bytes.startswith(p) for p in patterns):
        return False, "画像ファイルの内容が破損しているか、形式が正しくありません。"
    return True, ""


def validate_csv(file_bytes: bytes) -> tuple[bool, str]:
    """
    CSVファイルの実体を確認する。
    テキストとしてデコードできるか、CSVとして解析できるかを確認する。
    """
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False, "CSVの文字コードを確認してください（UTF-8を推奨）。"

    if "," not in text.splitlines()[0] if text.splitlines() else True:
        return False, "CSV形式として読み取れませんでした。"

    return True, ""

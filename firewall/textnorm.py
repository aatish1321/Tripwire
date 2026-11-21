"""Undo the disguises attackers use, so the Scanner's patterns and R2's leak check see the plain text.
fold(): fullwidth/compatibility forms (NFKC), Cyrillic/Greek look-alike letters, invisible and bidi characters.
reveal(): fold() plus URL-decoding, with any base64 or hex blobs decoded and appended."""
import base64
import binascii
import re
import unicodedata
import urllib.parse

# shortcut: the common Cyrillic/Greek look-alikes only, not the full Unicode confusables list; extend if a test finds one
LOOKALIKES = str.maketrans("АВЕКМНОРСТХаеорсуххіјѕԁɡΑΒΕΗΙΚΜΝΟΡΤΧΥΖαοιρτυνκ",
                           "ABEKMHOPCTXaeopcyxxijsdgABEHIKMNOPTXYZaoiptuvk")
INVISIBLE = re.compile("[​-‏⁠﻿‪-‮⁦-⁩\U000E0000-\U000E007F]")
BASE64_BLOB = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,2}")
HEX_BLOB = re.compile(r"\b(?:[0-9a-fA-F]{2}){8,}\b")


def fold(text: str) -> str:
    return INVISIBLE.sub("", unicodedata.normalize("NFKC", text).translate(LOOKALIKES))


def _printable(raw: bytes) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text if text and sum(c.isprintable() for c in text) / len(text) > 0.9 else None


def reveal(text: str) -> str:
    text = fold(text)
    for _ in range(2):  # twice, so %255F (double-encoded) is caught too
        text = urllib.parse.unquote(text)
    hidden = []
    for blob in BASE64_BLOB.findall(text):
        for decode in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                decoded = _printable(decode(blob + "=" * (-len(blob) % 4)))
            except (binascii.Error, ValueError):
                decoded = None
            if decoded:
                hidden.append(decoded)
                break
    for blob in HEX_BLOB.findall(text):
        decoded = _printable(bytes.fromhex(blob))
        if decoded:
            hidden.append(decoded)
    return fold(" ".join([text, *hidden]))

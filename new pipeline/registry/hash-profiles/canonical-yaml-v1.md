# Canonical YAML hash profile v1

**Profile ID:** `canonical-yaml-v1`  
**Status:** proposed for owner approval

This profile turns a restricted YAML record into deterministic bytes for semantic self-hashing:

1. Decode UTF-8 without BOM and parse YAML 1.2 Core.
2. Reject duplicate keys, merge keys, aliases/anchors, custom tags, non-string mapping keys and values outside the JSON data model.
3. Remove only the field paths explicitly supplied by the calling contract.
4. Normalize every string and mapping key to Unicode NFC.
5. Serialize the data with RFC 8785 JSON Canonicalization Scheme as UTF-8, without BOM or trailing newline.
6. Calculate SHA-256 and encode it as 64 lowercase hexadecimal characters.

Approval receipts exclude `receipt_sha256`; approval envelopes exclude `integrity.canonical_payload_sha256`. Complete-file SHA-256 remains a separate external binding and does not use this semantic canonicalization.

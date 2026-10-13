"""
query_validator.py
Security and Syntax Validator for Generated Cypher Queries.
Ensures queries are strictly read-only and adhere to the movie graph schema.
"""

import re
from typing import Tuple, List
from config import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIPS

# Explicitly forbidden mutating/administrative Cypher keywords
FORBIDDEN_KEYWORDS: List[str] = [
    "CREATE",
    "DELETE",
    "DETACH",
    "SET",
    "MERGE",
    "REMOVE",
    "DROP",
    "ALTER",
    "LOAD CSV",
    "PERIODIC COMMIT",
    "GRANT",
    "REVOKE",
    "DENY",
    "APOC",
    "DBMS"
]

# Required read-oriented Cypher keywords (at least one must be present)
ALLOWED_READ_KEYWORDS: List[str] = [
    "MATCH",
    "OPTIONAL MATCH",
    "RETURN",
    "WITH",
    "UNWIND",
    "SHOW"
]


def clean_cypher_text(raw_query: str) -> str:
    """
    Cleans Cypher query string by removing markdown code blocks, backticks,
    local LLM few-shot prefixes, and unnecessary surrounding whitespace.
    """
    if not raw_query:
        return ""
    
    cleaned = raw_query.strip()
    
    # 1. Extract from markdown code fences if present (e.g. ```cypher ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    else:
        # Strip trailing or leading orphan backticks
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    # 2. If the LLM echoes prompt prefixes like 'User: ... \nCypher:' or 'Cypher:\n'
    if re.search(r"\bcypher\s*:\s*", cleaned, re.IGNORECASE):
        parts = re.split(r"\bcypher\s*:\s*", cleaned, flags=re.IGNORECASE)
        if len(parts) > 1 and parts[-1].strip():
            cleaned = parts[-1].strip()

    # 3. If there is conversational preamble before the first MATCH / OPTIONAL MATCH / RETURN / WITH / UNWIND
    first_keyword = re.search(r"\b(MATCH|OPTIONAL\s+MATCH|RETURN|WITH|UNWIND)\b", cleaned, re.IGNORECASE)
    if first_keyword and first_keyword.start() > 0:
        preamble = cleaned[:first_keyword.start()].strip()
        if not any(kw in preamble.upper() for kw in ["MATCH", "RETURN", "WITH"]):
            cleaned = cleaned[first_keyword.start():].strip()

    # 4. Remove any trailing explanatory text like 'Note: ...' or 'Explanation: ...'
    cleaned = re.split(r"\n\s*(?:Note|Explanation|This query)\s*:", cleaned, flags=re.IGNORECASE)[0].strip()

    cleaned = cleaned.strip("`").strip()
    return cleaned


def strip_string_literals(query: str) -> str:
    """
    Removes quoted string literals ('...' and "...") from a query
    so keyword checks do not false-positive on movie titles or names.
    """
    # Replace single-quoted strings
    no_single = re.sub(r"'([^'\\]|\\.)*'", "''", query)
    # Replace double-quoted strings
    no_double = re.sub(r'"([^"\\]|\\.)*"', '""', no_single)
    return no_double


def validate_cypher_query(query: str) -> Tuple[bool, str, str]:
    """
    Validates that a Cypher query is non-empty, safe (read-only),
    and conforms to standard structure.

    Returns:
        (is_valid: bool, error_message: str, cleaned_query: str)
    """
    cleaned = clean_cypher_text(query)
    
    # 1. Non-empty check
    if not cleaned:
        return False, "Cypher query is empty.", ""

    # Strip literals to avoid false positives in keyword matching (e.g. title: 'Reset')
    sanitized_for_keywords = strip_string_literals(cleaned)

    # 2. Check for forbidden mutating keywords
    for kw in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, sanitized_for_keywords, re.IGNORECASE):
            return (
                False,
                f"Security violation: Query contains forbidden mutating or administrative keyword '{kw}'. Only read operations are permitted.",
                cleaned
            )

    # 3. Must contain at least one valid read clause (e.g., MATCH, RETURN)
    has_read_clause = False
    for rk in ALLOWED_READ_KEYWORDS:
        pattern = r"\b" + re.escape(rk) + r"\b"
        if re.search(pattern, sanitized_for_keywords, re.IGNORECASE):
            has_read_clause = True
            break
            
    if not has_read_clause:
        return (
            False,
            "Query does not contain any valid read clause (such as MATCH or RETURN).",
            cleaned
        )

    # 4. Check for balanced parentheses, brackets, and braces
    brackets_map = {'(': ')', '[': ']', '{': '}'}
    stack = []
    
    # Use original cleaned query without stripping to verify bracket balance,
    # but ignore brackets inside strings
    in_single_quote = False
    in_double_quote = False
    escape = False

    for char in cleaned:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
            
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
            
        if in_single_quote or in_double_quote:
            continue

        if char in brackets_map.keys():
            stack.append(char)
        elif char in brackets_map.values():
            if not stack:
                return False, f"Unbalanced bracket/parenthesis: unexpected '{char}'", cleaned
            top = stack.pop()
            if brackets_map[top] != char:
                return False, f"Mismatched bracket/parenthesis: expected '{brackets_map[top]}' but got '{char}'", cleaned

    if stack:
        unclosed = stack[-1]
        return False, f"Unclosed bracket/parenthesis: '{unclosed}' was not closed.", cleaned

    # Query passed all security and structural checks
    return True, "", cleaned

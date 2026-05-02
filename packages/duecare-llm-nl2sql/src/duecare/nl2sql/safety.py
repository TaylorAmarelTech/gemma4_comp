"""SQL safety guard. The DB is single-user but the NL2SQL layer must
NEVER let a Gemma-generated query mutate state -- otherwise a typo'd
question could DROP TABLE bad_actors."""
from __future__ import annotations

import re


class SQLSafetyError(ValueError):
    pass


_FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
    "CREATE", "GRANT", "REVOKE", "REPLACE", "MERGE", "ATTACH",
    "DETACH", "VACUUM", "PRAGMA", "EXEC", "CALL", "COPY",
)
_SQL_COMMENT_RX = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_TOKEN_RX = re.compile(r"\b([A-Z]+)\b")


def validate_readonly(sql: str, max_statements: int = 1) -> str:
    """Reject any SQL that isn't a single read-only SELECT (or WITH ...
    SELECT). Returns the cleaned SQL on success; raises SQLSafetyError
    otherwise. Strips comments before checking so a `-- DROP TABLE`
    suffix can't sneak in.
    """
    if not sql or not isinstance(sql, str):
        raise SQLSafetyError("empty or non-string SQL")
    cleaned = _SQL_COMMENT_RX.sub(" ", sql).strip()
    if not cleaned:
        raise SQLSafetyError("SQL is empty after stripping comments")
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if len(statements) > max_statements:
        raise SQLSafetyError(
            f"SQL contains {len(statements)} statements; max allowed "
            f"is {max_statements}.")
    upper = cleaned.upper()
    leading = upper.lstrip()
    if not (leading.startswith("SELECT") or leading.startswith("WITH ")):
        raise SQLSafetyError(
            f"only SELECT / WITH ... SELECT allowed; got: "
            f"{cleaned[:60]!r}")
    for token in _TOKEN_RX.findall(upper):
        if token in _FORBIDDEN_KEYWORDS:
            raise SQLSafetyError(
                f"forbidden SQL keyword detected: {token}")
    return cleaned

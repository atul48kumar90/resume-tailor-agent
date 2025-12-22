import difflib


def diff_text(old: str, new: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )

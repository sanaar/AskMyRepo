"""Split fetched files into chunks: paragraphs for docs, function/class blocks for code."""
import re

# Matches a top-level def/class/function (Python or JS/TS). Anchored to column
# zero on purpose: a method indented inside a class must NOT start a new chunk,
# or the class declaration gets severed from its own methods.
CODE_BLOCK_START = re.compile(
    r"^(async def |def |class |function |const \w+\s*=\s*(?:async\s*)?\(|export (default )?(function|class))"
)

MIN_CHUNK_CHARS = 20


def chunk_markdown(text: str, path: str) -> list[dict]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    for para in paragraphs:
        para = para.strip()
        if len(para) >= MIN_CHUNK_CHARS:
            chunks.append({"path": path, "type": "doc", "text": para})
    return chunks


def chunk_code(text: str, path: str) -> list[dict]:
    """Split on lines that look like a function/class definition, keeping each
    definition (and the body that follows, until the next definition) together.
    A regex heuristic, not a real parser - good enough to avoid slicing a
    function in half, which is the actual goal.
    """
    lines = text.split("\n")
    start_indices = [i for i, line in enumerate(lines) if CODE_BLOCK_START.match(line)]

    if not start_indices:
        # No recognizable functions/classes (e.g. a script or config file) -
        # just treat the whole file as one chunk.
        joined = text.strip()
        return [{"path": path, "type": "code", "text": joined}] if joined else []

    chunks = []
    # Anything before the first def/class (imports, module docstring, constants).
    preamble = "\n".join(lines[: start_indices[0]]).strip()
    if len(preamble) >= MIN_CHUNK_CHARS:
        chunks.append({"path": path, "type": "code", "text": preamble})

    for idx, start in enumerate(start_indices):
        end = start_indices[idx + 1] if idx + 1 < len(start_indices) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        if len(block) >= MIN_CHUNK_CHARS:
            chunks.append({"path": path, "type": "code", "text": block})

    return chunks


def chunk_file(path: str, content: str) -> list[dict]:
    if path.endswith(".md"):
        return chunk_markdown(content, path)
    return chunk_code(content, path)


def chunk_repo(files: list[dict]) -> list[dict]:
    all_chunks = []
    for f in files:
        all_chunks.extend(chunk_file(f["path"], f["content"]))
    return all_chunks

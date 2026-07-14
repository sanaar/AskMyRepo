# AskMyRepo

Paste a public GitHub repo URL, ask questions about it, get answers grounded in the actual code and docs.

**Live demo:** _add your Streamlit Cloud link here_

## How it works

```
GitHub URL -> fetch (README, file tree, source files)
           -> chunk (paragraphs for docs, function/class blocks for code)
           -> embed (sentence-transformers, local)
           -> store (ChromaDB, cached per repo)
           -> retrieve top-k chunks for a question
           -> answer (Groq / Llama 3.1), with source files shown
```

## Design decision: chunking code differently than docs

Docs get split by paragraph — that's the natural unit of a README. Code gets
split so each chunk is a whole function or class body (via a regex heuristic
in [`chunker.py`](chunker.py)), never cut in half mid-definition. Slicing code
by a fixed line count is the easy path, but it routinely splits a function
across two chunks, so the retriever ends up handing the model half a function
with no signature, or a signature with no body.

## Limitations

- Only public repos (no auth flow for private repos).
- Skips very large files (>100KB) and non-code/doc extensions (binaries,
  lockfiles, images).
- Uses GitHub's REST API without pagination beyond one page for the tree
  listing, so extremely large monorepos may not be fully indexed.
- Retrieval is a single embedding similarity search — no re-ranking or
  hybrid (keyword + vector) search.

## Running locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and add your Groq API key
streamlit run app.py
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

## Deploying

Push this repo to GitHub, then deploy on
[Streamlit Community Cloud](https://streamlit.io/cloud). Add `GROQ_API_KEY`
(and optionally `GITHUB_TOKEN` for higher GitHub API rate limits) under the
app's Secrets settings — never commit them to the repo.

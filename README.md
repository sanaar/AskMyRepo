# AskMyRepo

Paste a public GitHub repo URL, ask questions about it, get answers grounded in the actual code and docs.

**Live demo:** [askmyrepo-nre8uscmfoadq7sfwn6eyh.streamlit.app](https://askmyrepo-nre8uscmfoadq7sfwn6eyh.streamlit.app/)

## How it works

```
GitHub URL -> fetch (README, file tree, source files)
           -> chunk (paragraphs for docs, function/class blocks for code)
           -> embed (sentence-transformers, local)
           -> store (ChromaDB, cached per repo)
           -> retrieve top-k chunks for a question
           -> answer (Groq / Llama 3.1), with source files shown
```

## Tech stack

- **GitHub REST API** — fetch repo metadata, file tree, README, and source files (no auth needed for public repos; an optional token raises the rate limit)
- **[`sentence-transformers`](https://www.sbert.net/)** (`all-MiniLM-L6-v2`) — local, free embeddings
- **[ChromaDB](https://www.trychroma.com/)** — vector storage, one persisted collection per repo
- **[Groq](https://groq.com/) / Llama 3.1** — free-tier LLM inference for the final answer
- **Streamlit** — UI and free hosting (Streamlit Community Cloud)

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
- The ChromaDB cache lives on local disk, which is ephemeral on Streamlit
  Community Cloud — it persists across questions in a running session, but
  gets wiped whenever the app restarts (redeploys, wakes from sleep after
  inactivity), so a previously-analyzed repo will re-index after that.
- Unauthenticated GitHub API calls are capped at 60 requests/hour, which a
  single medium-sized repo can exhaust — add a `GITHUB_TOKEN` to raise this
  to 5,000/hour.

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

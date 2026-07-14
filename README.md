# AskMyRepo

AskMyRepo lets you paste a link to any public GitHub repository and ask it questions in plain English, like you would ask a teammate who already read the whole codebase.

Instead of clicking through folders and files trying to piece together how a project works, you type something like "how does authentication work here?" or "what does the `parse_config` function do?" and get an answer that points back to the actual files it came from. Under the hood, the app reads the repo's README and source files, breaks them into meaningful chunks, and uses an AI model to answer your question using only what it found in that specific repo, not general guesses.

**Live demo:** [askmyrepo-nre8uscmfoadq7sfwn6eyh.streamlit.app](https://askmyrepo-nre8uscmfoadq7sfwn6eyh.streamlit.app/)

## How it works

1. You paste a GitHub URL.
2. The app fetches the repo's README, file list, and source files using the GitHub API.
3. It splits the docs into paragraphs and the code into whole functions and classes, so nothing gets cut in half.
4. Each chunk is turned into an embedding (a numeric representation of its meaning) and saved in a small local database called ChromaDB, so the same repo does not need to be reprocessed every time.
5. When you ask a question, the app finds the chunks that are most related to it and sends them, along with your question, to an AI model (Llama 3.1, through Groq) to write the answer.
6. The answer is shown along with the file paths it was based on, so you can double check the source yourself.

## What it's built with

- **GitHub REST API** to fetch repo metadata, the file tree, the README, and source files. Public repos work without any login, and adding a personal access token just raises how many requests you can make per hour.
- **sentence-transformers** (the `all-MiniLM-L6-v2` model) to turn text into embeddings. This runs locally and is free.
- **ChromaDB** to store those embeddings, with one saved collection per repo so repeat visits are fast.
- **Groq**, running Llama 3.1, to generate the actual answers. Groq has a free tier that's plenty for a project like this.
- **Streamlit** for the web interface and free hosting on Streamlit Community Cloud.

## Why code is chunked differently than docs

A README reads naturally paragraph by paragraph, so that's how it's split. Code is different. If you split code by a fixed number of lines, you'll eventually cut a function in half, so the AI ends up seeing a function's body with no signature, or a signature with nothing underneath it. To avoid that, `chunker.py` keeps each function or class together as one whole chunk.

## Good questions to try

Once a repo is indexed, here are a few kinds of questions that work well:

- A general one, like "What does this project do?" or "How do I install this?"
- Something about specific code, like "How does routing work?" or asking about a function you noticed in the file list.
- A question the repo genuinely doesn't answer, just to check that the app says "I don't know" instead of making something up.

You can also expand the "Sources" section under any answer to see exactly which files it used.

## Limitations

- Only works with public repositories. There's no login flow for private repos.
- Skips very large files (over 100KB) and file types other than code and docs, like images, lockfiles, and binaries.
- Only reads one page of results from GitHub's file tree API, so extremely large repositories may not be fully indexed.
- Uses a single similarity search to find relevant chunks. There's no more advanced re-ranking or keyword search layered on top yet.
- The saved ChromaDB cache lives on disk, which is temporary on Streamlit Community Cloud. It speeds things up while the app is running, but gets cleared whenever the app restarts, so a repo you already analyzed may need to reindex after the app has been idle for a while.
- Unauthenticated GitHub API requests are limited to 60 per hour, and a single medium sized repo can use that up quickly. Adding a `GITHUB_TOKEN` raises the limit to 5,000 per hour.

## Running it on your own computer

1. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy the example secrets file and fill in your own key:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Then open `.streamlit/secrets.toml` and add your Groq API key. You can get a free one at [console.groq.com](https://console.groq.com).
3. Start the app:
   ```bash
   streamlit run app.py
   ```

## Deploying your own copy

1. Push this repo to your own GitHub account.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud) and sign in with GitHub.
3. Click "New app," then pick your repo, the `main` branch, and `app.py` as the entry point.
4. Before deploying, open "Advanced settings" and add your secrets in this format:
   ```toml
   GROQ_API_KEY = "your-groq-api-key"
   GITHUB_TOKEN = "your-github-token"
   ```
   The GitHub token is optional. Never commit these values directly into the repo.
5. Click "Deploy" and wait a minute or two for the first build to finish.

import os

import streamlit as st

import github_fetcher
import qa
import vectorstore
from chunker import chunk_repo

# Pull secrets (Streamlit Cloud) into the environment so the other modules,
# which read os.environ directly, pick them up either locally or when deployed.
# st.secrets raises if no secrets.toml exists at all, so guard with a try.
try:
    for key in ("GROQ_API_KEY", "GITHUB_TOKEN"):
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except FileNotFoundError:
    pass

st.set_page_config(page_title="AskMyRepo", page_icon="📦")
st.title("📦 AskMyRepo")
st.caption("Paste a public GitHub repo URL, then ask questions about it.")

if "repo_ref" not in st.session_state:
    st.session_state.repo_ref = None  # (owner, repo, branch)

url = st.text_input("GitHub repo URL", placeholder="https://github.com/owner/repo")
analyze_clicked = st.button("Analyze Repo")

if analyze_clicked and url:
    try:
        owner, repo = github_fetcher.parse_github_url(url)
        branch = github_fetcher.get_default_branch(owner, repo)

        if vectorstore.collection_exists(owner, repo, branch):
            st.info(f"Found a cached index for {owner}/{repo} — skipping re-analysis.")
        else:
            with st.spinner("Fetching repo contents..."):
                repo_data = github_fetcher.fetch_repo(url)
            with st.spinner(f"Chunking and embedding {len(repo_data['files'])} files..."):
                chunks = chunk_repo(repo_data["files"])
                vectorstore.build_collection(owner, repo, branch, chunks)
            st.success(f"Indexed {len(chunks)} chunks from {len(repo_data['files'])} files.")

        st.session_state.repo_ref = (owner, repo, branch)
    except github_fetcher.GitHubFetchError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Something went wrong analyzing that repo: {e}")

if st.session_state.repo_ref:
    owner, repo, branch = st.session_state.repo_ref
    st.divider()
    st.subheader(f"Ask about {owner}/{repo}")
    question = st.text_input("Your question", key="question")

    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            try:
                chunks = vectorstore.query(owner, repo, branch, question)
                if not chunks:
                    st.warning("No relevant content found in the indexed repo.")
                else:
                    response = qa.answer_question(question, chunks)
                    st.markdown(response)
                    with st.expander("Sources"):
                        for c in chunks:
                            st.markdown(f"**{c['path']}** ({c['type']})")
                            st.code(c["text"][:500])
            except RuntimeError as e:
                st.error(str(e))

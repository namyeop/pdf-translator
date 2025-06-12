import streamlit as st
import random
import time
import os

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough  # For passing input through
from langchain_community.document_loaders import (
    PyPDFLoader,
)  # For loading PDF documents
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)  # For splitting text into chunks
from pdf2docx import Converter  # Added for PDF to DOCX conversion


@st.cache_data  # Cache the loaded and chunked documents
def load_and_chunk_documents(docs_path: str) -> list:
    """
    Loads documents from the specified directory, processes PDF files,
    and splits them into manageable chunks.
    """
    all_chunks = []
    if not os.path.isdir(docs_path):
        st.error(f"Docs directory not found: {docs_path}")
        return all_chunks

    try:
        doc_files = [f for f in os.listdir(docs_path) if f.lower().endswith(".pdf")]
        if not doc_files:
            st.info(f"No PDF documents found in {docs_path}")
            return all_chunks

        loaded_documents = []
        for doc_file in doc_files:
            file_path = os.path.join(docs_path, doc_file)
            try:
                loader = PyPDFLoader(file_path)
                loaded_documents.extend(
                    loader.load()
                )  # PyPDFLoader loads pages as individual documents
                st.write(f"Loaded {doc_file}")
            except Exception as e:
                st.error(f"Error loading {doc_file}: {e}")

        if not loaded_documents:
            st.warning("No documents were successfully loaded.")
            return all_chunks

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Size of each chunk
            chunk_overlap=200,  # Overlap between chunks
            length_function=len,
        )
        all_chunks = text_splitter.split_documents(loaded_documents)
        st.success(
            f"Successfully loaded and chunked {len(loaded_documents)} page(s) into {len(all_chunks)} chunks."
        )

    except Exception as e:
        st.error(f"An error occurred during document loading and chunking: {e}")

    return all_chunks


def convert_pdf_to_docx(pdf_file_path: str, docx_file_path: str) -> bool:
    """
    Converts a PDF file to a DOCX file using pdf2docx.

    Args:
        pdf_file_path: Path to the input PDF file.
        docx_file_path: Path to save the output DOCX file.

    Returns:
        True if conversion was successful, False otherwise.
    """
    if not os.path.exists(pdf_file_path):
        st.error(f"PDF file not found: {pdf_file_path}")
        return False

    try:
        st.write(f"Converting {os.path.basename(pdf_file_path)} to DOCX...")
        # Initialize Converter
        cv = Converter(pdf_file_path)
        # Convert to DOCX
        cv.convert(docx_file_path, start=0, end=None)  # Converts all pages
        # Close the converter
        cv.close()
        st.success(f"Successfully converted PDF to DOCX: {docx_file_path}")
        return True
    except Exception as e:
        st.error(f"Error during PDF to DOCX conversion: {e}")
        return False


# Determine the absolute path to the docs directory
# Assumes test.py is in /app and docs is in /app/docs
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(APP_DIR, "docs")

# Load documents when the app starts
chunked_documents = load_and_chunk_documents(DOCS_DIR)

st.title("✨ Chat with RAG ✨")  # Updated title

# --- PDF to DOCX Converter UI ---
st.sidebar.header("PDF to DOCX Converter")
uploaded_pdf = st.sidebar.file_uploader(
    "Upload PDF for DOCX Conversion", type="pdf", key="pdf_converter_uploader"
)

if uploaded_pdf is not None:
    # Generate a unique name for the temporary PDF to avoid conflicts if multiple users use the app
    # or if the same user uploads multiple files with the same name.
    # For simplicity, we'll just use the uploaded name directly in APP_DIR.
    # In a production app, consider using a dedicated temp directory or more robust naming.
    temp_pdf_filename = uploaded_pdf.name
    temp_pdf_path = os.path.join(APP_DIR, temp_pdf_filename)

    with open(temp_pdf_path, "wb") as f:
        f.write(uploaded_pdf.getbuffer())

    docx_filename = os.path.splitext(temp_pdf_filename)[0] + ".docx"
    # Save the converted DOCX also in APP_DIR for simplicity
    temp_docx_path = os.path.join(APP_DIR, docx_filename)

    if st.sidebar.button(
        f"Convert '{temp_pdf_filename}' to DOCX", key="convert_to_docx_button"
    ):
        with st.spinner(f"Converting {temp_pdf_filename} to DOCX..."):
            success = convert_pdf_to_docx(temp_pdf_path, temp_docx_path)

        if success:
            st.sidebar.success(f"Successfully converted to {docx_filename}!")
            try:
                with open(temp_docx_path, "rb") as f_docx:
                    st.sidebar.download_button(
                        label=f"Download {docx_filename}",
                        data=f_docx,
                        file_name=docx_filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="download_docx_button",
                    )
            except FileNotFoundError:
                st.sidebar.error(
                    f"Could not find the converted file to download: {temp_docx_path}"
                )
            # Clean up the temporary PDF file after successful conversion and download button is available
            if os.path.exists(temp_pdf_path):
                try:
                    os.remove(temp_pdf_path)
                except Exception as e:
                    st.sidebar.warning(f"Could not remove temporary PDF: {e}")
            # Note: Temporary DOCX file is left for download.
            # Consider a strategy for cleaning up these files eventually (e.g., on session end, or after download).
        else:
            st.sidebar.error("PDF to DOCX conversion failed.")
            # Clean up the temporary PDF file even if conversion failed
            if os.path.exists(temp_pdf_path):
                try:
                    os.remove(temp_pdf_path)
                except Exception as e:
                    st.sidebar.warning(f"Could not remove temporary PDF: {e}")

# --- End PDF to DOCX Converter UI ---


# Langsmith & OpenAI API Key Setup
# Using Streamlit secrets (recommended for deployment)
# Ensure these secrets are set in your Streamlit Cloud config or a .streamlit/secrets.toml file
try:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"  # Enable Langsmith tracing

    langchain_api_key = st.secrets.get("LANGCHAIN_API_KEY")
    if langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = langchain_api_key
    else:
        st.warning(
            "LANGCHAIN_API_KEY not found in Streamlit secrets. Langsmith tracing might not work."
        )
        # For local testing without secrets, you might set it directly if needed, but not recommended for shared code.
        # if "YOUR_FALLBACK_LANGCHAIN_API_KEY" != "YOUR_FALLBACK_LANGCHAIN_API_KEY": # Replace with actual key if using fallback
        #     os.environ["LANGCHAIN_API_KEY"] = "YOUR_FALLBACK_LANGCHAIN_API_KEY"

    langchain_project = st.secrets.get(
        "LANGCHAIN_PROJECT", "Streamlit RAG Chat"
    )  # Default project name
    os.environ["LANGCHAIN_PROJECT"] = langchain_project

    openai_api_key = st.secrets.get("OPENAI_API_KEY")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
        llm = ChatOpenAI(model="gpt-4.1-2025-04-14")
    else:
        st.error(
            "OPENAI_API_KEY not found in Streamlit secrets. RAG functionality requires an OpenAI API key."
        )
        llm = None
        # For local testing without secrets, you might set it directly if needed
        # if "YOUR_FALLBACK_OPENAI_API_KEY" != "YOUR_FALLBACK_OPENAI_API_KEY": # Replace
        #     os.environ["OPENAI_API_KEY"] = "YOUR_FALLBACK_OPENAI_API_KEY"
        #     llm = ChatOpenAI(model="gpt-3.5-turbo")


except (
    AttributeError
):  # Handles cases where st.secrets might not be available (e.g. very old Streamlit or specific local setups)
    st.warning(
        "Streamlit secrets (st.secrets) not available. Attempting to use environment variables directly."
    )
    if not os.getenv("LANGCHAIN_API_KEY"):
        st.warning("LANGCHAIN_API_KEY environment variable not set.")
    if not os.getenv("OPENAI_API_KEY"):
        st.error(
            "OPENAI_API_KEY environment variable not set. RAG functionality requires an OpenAI API key."
        )
        llm = None
    else:
        llm = ChatOpenAI(model="gpt-4.1-2025-04-14")
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "Streamlit RAG Chat (direct env)"


# --- RAG Setup ---
# The old get_dummy_retriever is no longer needed.

# Prompt Template for RAG
rag_prompt_template = ChatPromptTemplate.from_template(
    """Answer the following question based only on the provided context. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}
"""
)  # Simplified RAG Chain


def retrieve_context_from_chunks(query: str, chunks: list):
    if not chunks:
        return "No documents have been loaded or processed. Cannot retrieve context."
    # For now, concatenate all document chunks as context.
    # This is a placeholder for a more sophisticated retrieval (e.g., vector search).
    # Consider limiting the amount of context if it becomes too large.
    context = "\n\n---\n\n".join([doc.page_content for doc in chunks])
    return context


if llm:
    if chunked_documents:
        rag_chain = (
            RunnablePassthrough.assign(
                context=lambda x: retrieve_context_from_chunks(
                    x["question"], chunked_documents
                )
            )
            | rag_prompt_template
            | llm
            | StrOutputParser()
        )
    else:
        st.error(
            "Documents could not be loaded. RAG chain will not use document context."
        )
        # Fallback: Initialize rag_chain to None or a version that doesn't rely on docs
        # For now, if docs fail, RAG_response_generator will indicate issues.
        rag_chain = None
else:
    rag_chain = None  # LLM is not initialized

# --- End RAG Setup ---


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def RAG_response_generator(user_input: str):
    if not llm or not rag_chain:
        yield "RAG chain is not configured (likely due to missing API keys or LLM initialization failure). "
        return

    try:
        # The input to the chain should be a dictionary
        input_dict = {"question": user_input}
        full_response_parts = []
        for chunk in rag_chain.stream(input_dict):
            yield chunk
            full_response_parts.append(chunk)
            # time.sleep(0.02) # Optional: small delay for typing effect, adjust as needed
        # The full response is now "".join(full_response_parts)
        # This will be handled by st.write_stream which returns the full string.
    except Exception as e:
        st.error(f"Error during RAG generation: {e}")
        yield f"Sorry, I encountered an error while generating a response: {str(e)}. "


# React to user input
if prompt := st.chat_input("메시지를 입력하세요..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        if llm and rag_chain:  # Check if LLM and chain are ready
            full_response = st.write_stream(RAG_response_generator(prompt))
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )
        else:
            # Fallback if LLM/RAG is not set up
            fallback_message = "RAG system not fully configured. Please check API key settings and ensure the LLM is available."
            st.markdown(fallback_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": fallback_message}
            )

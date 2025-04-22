from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import tempfile
import os
import uvicorn
import json
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS (Cross-Origin Resource Sharing) setup
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5555",  # Ensure this matches your frontend port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FAISS database persistence directory
persist_directory = "faiss_index"

# Global variables to manage state
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
llm = Ollama(model="mistral:latest")
db = None
qa_chain = None

# Initialize FAISS and QA chain (load if exists)
def init_qa_chain():
    global db, qa_chain
    logger.debug("Initializing QA chain...")
    if os.path.exists(persist_directory):
        logger.debug("Loading existing FAISS database...")
        db = FAISS.load_local(persist_directory, embeddings, allow_dangerous_deserialization=True)
    else:
        logger.debug("No existing FAISS database found. Initializing new database...")
        db = None

    if db:
        logger.debug("Initializing QA chain with existing database...")
        retriever = db.as_retriever()
        prompt_template = """Use the following pieces of context to answer the question at the end.
        If you don't know the answer, just say that you don't know, don't try to make up an answer.

        {context}

        Question: {question}
        Helpful Answer:"""
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False,
            chain_type_kwargs={"prompt": PROMPT}
        )
    logger.debug("QA chain initialization complete.")
    return db, qa_chain

db, qa_chain = init_qa_chain()

class Query(BaseModel):
    query: str

@app.post("/uploadpdf/")
async def upload_pdf(file: UploadFile = File(...)):
    global db, qa_chain
    logger.debug("Received request to upload PDF.")
    if not file.filename.endswith(".pdf"):
        logger.error("Uploaded file is not a PDF.")
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        logger.debug("Creating temporary file for PDF...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(await file.read())
            temp_filepath = tmp_file.name

        logger.debug("Loading PDF content...")
        loader = PyPDFLoader(temp_filepath)
        documents = loader.load()
        logger.debug(f"Loaded {len(documents)} documents from PDF.")

        logger.debug("Splitting text into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        logger.debug(f"Split into {len(texts)} text chunks.")

        if db is None:
            logger.debug("Creating new FAISS database...")
            db = FAISS.from_documents(texts, embeddings)
            db.save_local(persist_directory)
        else:
            logger.debug("Adding documents to existing FAISS database...")
            db.add_documents(texts)
            db.save_local(persist_directory)

        logger.debug("Reinitializing QA chain with updated database...")
        retriever = db.as_retriever()
        prompt_template = """Use the following pieces of context to answer the question at the end.
                If you don't know the answer, just say that you don't know, don't try to make up an answer.

                {context}

                Question: {question}
                Helpful Answer:"""
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False,
            chain_type_kwargs={"prompt": PROMPT}
        )

        logger.debug("PDF processed successfully.")
        return {"message": "PDF processed successfully"}

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_filepath):
            logger.debug("Cleaning up temporary file...")
            os.remove(temp_filepath)

def is_conversational_query(query: str) -> bool:
    """Determine if the query is conversational (e.g., greetings, general chit-chat)."""
    query_lower = query.lower().strip()
    conversational_keywords = [
        "salam", "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "what's up", "how's it going", "thank you", "thanks", "bye", "goodbye"
    ]
    return any(keyword in query_lower for keyword in conversational_keywords)

@app.post("/ask/")
async def ask_question(query: Query):
    global db, llm
    logger.debug("Received question: %s", query.query)
    
    try:
        # Check if the query is conversational (e.g., greetings, general chit-chat)
        if is_conversational_query(query.query):
            logger.debug("Conversational query detected. Using language model directly...")
            result = llm(query.query)
            logger.debug("Result from language model: %s", result)
            return {"answer": result}

        if db:  # If a PDF has been uploaded, enhance the answer with PDF content
            logger.debug("PDF mode: Retrieving relevant context from FAISS database...")
            # Retrieve relevant documents from the FAISS database
            retriever = db.as_retriever(search_kwargs={"k": 3})  # Retrieve top 3 relevant chunks
            relevant_docs = retriever.get_relevant_documents(query.query)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            logger.debug("Retrieved context: %s", context)

            # Create a prompt that includes the PDF context but allows the model to use general knowledge
            prompt_template = """You are a helpful chatbot with access to additional context from uploaded PDFs. Your primary goal is to provide accurate and helpful answers. Use the following guidelines:

            1. If the question is a greeting or general chit-chat (e.g., "Salam", "Hello", "How are you"), respond conversationally without referencing the PDF context, even if it is available.
            2. If the question is related to the PDF context, use the context to provide a precise answer, and supplement with your general knowledge if necessary.
            3. If the question is unrelated to the PDF context, ignore the context and use your general knowledge to answer.
            4. If you don't know the answer, say so and offer to help with something else.

            ### Context from PDF (use only if relevant):
            {context}

            ### Question:
            {question}

            ### Answer:
            """
            prompt = PromptTemplate(
                template=prompt_template, input_variables=["context", "question"]
            )
            # Format the prompt with the retrieved context and user query
            formatted_prompt = prompt.format(context=context, question=query.query)
            # Invoke the Mistral model directly with the formatted prompt
            result = llm(formatted_prompt)
            logger.debug("Result from Mistral model: %s", result)
            return {"answer": result}
        else:  # If no PDF has been uploaded, use the language model directly
            logger.debug("General mode: Using language model directly...")
            result = llm(query.query)
            logger.debug("Result from language model: %s", result)
            return {"answer": result}

    except Exception as e:
        logger.error("An exception occurred in ask_question: %s", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

if __name__ == "__main__":
    logger.debug("Starting FastAPI server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
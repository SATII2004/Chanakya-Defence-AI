import pathway as pw
# Use Local Embedder (Free, Unlimited, Fast)
from pathway.xpacks.llm.embedders import SentenceTransformerEmbedder
from pathway.xpacks.llm.llms import LiteLLMChat
from pathway.xpacks.llm.question_answering import BaseRAGQuestionAnswerer
from pathway.xpacks.llm.document_store import DocumentStore
# Correct import for Index Factory
from pathway.stdlib.indexing import BruteForceKnnFactory 
import os
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class LiveRAGServer:
    def run(self):
        # 1. Input Data Stream
        # Read the raw JSONL stream
        raw_stream = pw.io.jsonlines.read(
            "live_data/",
            schema=pw.schema_from_dict({"text": str, "source": str, "timestamp": str}),
            mode="streaming"
        )

        # 2. Transform Step
        # Rename 'text' -> 'data' for the DocumentStore
        data_stream = raw_stream.select(
            data=pw.this.text,
            source=pw.this.source,
            timestamp=pw.this.timestamp
        )

        # 3. Define Components
        # Local Embedder (Runs on CPU, Free)
        embedder = SentenceTransformerEmbedder(model="all-MiniLM-L6-v2")
        
        # FIXED: Changed model to 'gemini/gemini-2.5-flash' based on your check_models.py output
        llm = LiteLLMChat(
            model="gemini/gemini-2.5-flash", 
            api_key=GEMINI_API_KEY,
            temperature=0.1
        )

        # 4. Create Retriever Factory
        # This tells the system how to search (BruteForce KNN is reliable)
        knn_factory = BruteForceKnnFactory(embedder=embedder)

        # 5. Build the RAG Pipeline
        rag_app = BaseRAGQuestionAnswerer(
            llm=llm,
            indexer=DocumentStore(
                docs=data_stream,
                retriever_factory=knn_factory
            ),
        )

        # 6. Build Server
        host = "0.0.0.0"
        port = 8000
        print(f"🚀 Pathway Engine Starting on {host}:{port}...")
        
        # This configures the REST API at /v1/pw_ai_answer
        rag_app.build_server(host=host, port=port)
        
        # 7. Run the Pipeline
        pw.run()

if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not found in .env")
    else:
        if not os.path.exists("live_data"):
            os.makedirs("live_data")
        LiveRAGServer().run()
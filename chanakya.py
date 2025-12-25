import pathway as pw
from pathway.xpacks.llm.vector_store import VectorStoreServer
from pathway.xpacks.llm import embedders, parsers

# 1. Define the Schema
class IntelInputSchema(pw.Schema):
    timestamp: str
    sector: str
    report: str
    priority: str

def run_chanakya():
    # 2. Read the CSV
    raw_data = pw.io.csv.read(
        "./intel_feed.csv",
        schema=IntelInputSchema,
        mode="streaming"
    )

    # 3. TRANSFORM: The Fix
    # We use pw.apply() to safely convert string to bytes for the parser
    documents = raw_data.select(
        data=pw.apply(lambda x: x.encode("utf-8"), pw.this.report),
        timestamp=pw.this.timestamp,
        sector=pw.this.sector,
        priority=pw.this.priority
    )

    # 4. Configure the Brain
    embedder_model = embedders.SentenceTransformerEmbedder("all-MiniLM-L6-v2")

    vector_server = VectorStoreServer(
        documents,
        embedder=embedder_model,
        parser=parsers.ParseUnstructured(),
    )

    # 5. Run Server
    vector_server.run_server(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_chanakya()
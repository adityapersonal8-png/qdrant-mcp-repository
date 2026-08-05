import os
import uuid
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient

# 1. Initialize the FastMCP Server
mcp = FastMCP("Qdrant Rule Metadata Server")

# 2. Initialize Qdrant Client (Uses Render Environment Variables)
# Falls back to local defaults if environment variables aren't set yet
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY", None)

qdrant_client = QdrantClient(
    url=qdrant_url, 
    api_key=qdrant_api_key
)

def generate_deterministic_uuid(key_string: str) -> str:
    """Generates a consistent, valid Qdrant UUID from a unique text key (like pzInsKey)."""
    # Uses Namespace DNS to ensure the same text string always yields the same UUID
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key_string))

@mcp.tool()
async def store_rule_metadata(collection_name: str, pz_ins_key: str, rule_text: str, metadata: dict) -> str:
    """
    Store rule text, auto-generate its embedding vector, and save application metadata to Qdrant.
    
    Args:
        collection_name: The target Qdrant collection name.
        pz_ins_key: The unique string identifier of the rule (e.g. pzInsKey).
        rule_text: The actual body or text representation of the rule to embed.
        metadata: A dictionary containing rule context (e.g. application name, version).
    """
    try:
        # Generate a clean, repeatable ID from the rule key string
        deterministic_id = generate_deterministic_uuid(pz_ins_key)
        
        # Merge the structural key into the metadata payload for absolute tracking
        payload = {**metadata, "pzInsKey": pz_ins_key}
        
        # Qdrant Client .add() handles tokenization and embedding generation using FastEmbed
        qdrant_client.add(
            collection_name=collection_name,
            documents=[rule_text],
            metadata=[payload],
            ids=[deterministic_id]
        )
        return f"Successfully stored rule. Generated ID: {deterministic_id}"
        
    except Exception as e:
        return f"Storage operation failed: {str(e)}"

@mcp.tool()
async def search_rule_metadata(collection_name: str, query: str, limit: int = 5) -> list:
    """
    Perform a global semantic vector search across application rule metadata.
    
    Args:
        collection_name: The Qdrant collection to query.
        query: The natural language search terms or description of the rule functionality.
        limit: Maximum number of relevant results to return (default is 5).
    """
    try:
        # Client query natively generates the vector for your string input and runs search
        search_results = qdrant_client.query(
            collection_name=collection_name,
            query_text=query,
            limit=limit
        )
        
        # Format results into a clean, human-readable JSON-like list for the AI model
        return [
            {
                "id": point.id, 
                "metadata": point.metadata, 
                "confidence_score": point.score
            } 
            for point in search_results
        ]
        
    except Exception as e:
        return [f"Search query failed: {str(e)}"]

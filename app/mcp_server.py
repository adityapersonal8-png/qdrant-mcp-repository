import os
import uuid
from fastmcp import FastMCP
from qdrant_client import QdrantClient

# 1. Initialize the FastMCP Server
mcp = FastMCP("Qdrant Rule Metadata Server")

# 2. Initialize Qdrant Client (Uses Render Environment Variables)
qdrant_url = os.getenv("QDRANT_URL", "https://qdrant.io")
qdrant_api_key = os.getenv("QDRANT_API_KEY", None)

qdrant_client = QdrantClient(
    url=qdrant_url, 
    api_key=qdrant_api_key
)

def generate_deterministic_uuid(key_string: str) -> str:
    """Generates a consistent, valid Qdrant UUID from a unique text key (like pzInsKey)."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key_string))

@mcp.tool()
async def store_rule_metadata(
    pz_ins_key: str, 
    rule_text: str, 
    metadata: dict,
    collection_name: str = "pega_application_knowledge"
) -> str:
    """
    Store rule text, auto-generate its embedding vector, and save application metadata to Qdrant.
    
    Args:
        pz_ins_key: The unique string identifier of the rule (e.g. pzInsKey).
        rule_text: The actual body or text representation of the rule to embed.
        metadata: A dictionary containing rule context (e.g. application name, version).
        collection_name: The target Qdrant collection name (Defaults to pega_application_knowledge).
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
        return f"Successfully stored rule in '{collection_name}'. Generated ID: {deterministic_id}"
        
    except Exception as e:
        return f"Storage operation failed: {str(e)}"

@mcp.tool()
async def search_rule_metadata(
    query: str, 
    limit: int = 5,
    collection_name: str = "pega_application_knowledge"
) -> list:
    """
    Perform a global semantic vector search across application rule metadata.
    
    Args:
        query: The natural language search terms or description of the rule functionality.
        limit: Maximum number of relevant results to return (default is 5).
        collection_name: The Qdrant collection to query (Defaults to pega_application_knowledge).
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

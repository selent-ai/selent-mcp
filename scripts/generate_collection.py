# /// script
# requires-python = ">=3.12"
# dependencies = ["meraki", "loguru", "pydantic", "qdrant-client", "fastembed"]
# ///

"""
Script to generate Qdrant collection from Meraki API structure.

This script discovers all available Meraki API methods and creates a Qdrant
collection with embeddings for semantic search.
"""

import inspect
from pathlib import Path
from typing import Any, Callable

import meraki
from loguru import logger
from pydantic import create_model
from qdrant_client import QdrantClient, models


def discover_api_structure() -> dict[str, list[dict[str, Any]]]:
    """Discover all available API sections and their methods"""

    dashboard = meraki.DashboardAPI(
        api_key="dummy-api-key",
        suppress_logging=True,
        maximum_retries=3,
        caller="SelentMCP/1.0 SelentAI",
        wait_on_rate_limit=True,
    )
    api_structure = {}

    # Get all API sections
    sections = [
        attr
        for attr in dir(dashboard)
        if not attr.startswith("_")
        and hasattr(getattr(dashboard, attr), "__class__")
        and "api" in str(type(getattr(dashboard, attr))).lower()
    ]

    def schema(func: Callable[..., Any]) -> dict[str, Any]:
        fields = {}
        for name, param in inspect.signature(func).parameters.items():
            annotation = (
                param.annotation if param.annotation != inspect.Parameter.empty else Any
            )
            default = ... if param.default == inspect.Parameter.empty else param.default
            fields[name] = (annotation, default)

        model = create_model(func.__name__, **fields)

        return model.model_json_schema()

    for section in sections:
        section_obj = getattr(dashboard, section)
        methods = [
            {
                "name": method,
                "description": getattr(section_obj, method).__doc__.strip(),
                "parameters": schema(getattr(section_obj, method)),
                "returns": inspect.signature(
                    getattr(section_obj, method)
                ).return_annotation.__name__,
            }
            for method in dir(section_obj)
            if not method.startswith("_") and callable(getattr(section_obj, method))
        ]
        api_structure[section] = methods

    return api_structure


def generate_collection(
    collection_path: str = "./data/meraki_api_collection",
    collection_name: str = "meraki_api_collection",
    model_name: str = "BAAI/bge-small-en-v1.5",
):
    """
    Generate Qdrant collection from Meraki API structure.

    Args:
        collection_path: Path to store the collection
        collection_name: Name of the collection
        model_name: Embedding model to use
    """
    logger.info("Discovering API structure...")
    api_structure = discover_api_structure()

    total_methods = sum(len(methods) for methods in api_structure.values())
    logger.info(f"Total methods discovered: {total_methods}")

    # Create collection directory if it doesn't exist
    Path(collection_path).mkdir(parents=True, exist_ok=True)

    # Initialize Qdrant client with persistent storage
    logger.info(f"Initializing Qdrant client at {collection_path}...")
    client = QdrantClient(path=collection_path)

    # Prepare documents for embedding
    logger.info("Preparing documents for embedding...")
    payload = [
        {
            "document": (
                f"method name: {method['name']}\n\ndescription: {method['description']}"
            ),
            "section": section,
            "method": method,
        }
        for section, methods in api_structure.items()
        for method in methods
    ]

    docs = [
        models.Document(text=data["document"], model=model_name) for data in payload
    ]
    ids = [
        hash(f"{section}.{method['name']}")
        for section, methods in api_structure.items()
        for method in methods
    ]

    # Create collection
    logger.info(f"Creating collection '{collection_name}'...")
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass  # Collection might not exist

    client.create_collection(
        collection_name,
        vectors_config=models.VectorParams(
            size=client.get_embedding_size(model_name), distance=models.Distance.COSINE
        ),
    )

    # Upload documents
    logger.info(f"Uploading {len(docs)} documents to collection...")
    client.upload_collection(
        collection_name,
        vectors=docs,
        ids=ids,
        payload=payload,
    )

    logger.info("Collection generation complete!")
    logger.info(f"Collection stored at: {collection_path}")
    logger.info(f"Total sections: {len(api_structure)}")
    logger.info(f"Total methods: {total_methods}")

    # Test search
    logger.info("\nTesting search with query: 'get my organizations'")
    search_result = client.query_points(
        collection_name,
        query=models.Document(text="get my organizations", model=model_name),
        limit=3,
    ).points

    logger.info("\nTop 3 results:")
    for point in search_result:
        logger.info(f"  Score: {point.score:.4f}")

        if point.payload is not None:
            logger.info(f"  Section: {point.payload['section']}")
            logger.info(f"  Method: {point.payload['method']['name']}")
            logger.info(
                f"  Description: {point.payload['method']['description'][:100]}..."
            )


if __name__ == "__main__":
    generate_collection()

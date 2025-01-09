import json
import os
import uuid
from typing import Optional, Union

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from service.bedrock_service import BedrockAsync

load_dotenv()

bedrock_service = BedrockAsync()


class QdrantVectorDB:
    def __init__(
        self,
        collection_name: str = "default_collection",
        vector_size: int = 1536,  # Default for Amazon Bedrock Titan Embeddings
    ):
        self.host = os.getenv("VECTORDB_HOST", "localhost")
        port_str = os.getenv("VECTORDB_PORT", "6333")
        self.port = int(port_str) if port_str else None
        self.client = QdrantClient(host=self.host, port=self.port)
        self.collection_name = collection_name
        self.vector_size = vector_size

    def check_collection_exists(self) -> bool:
        """Check if collection exists in Qdrant"""
        collections = self.client.get_collections().collections
        return any(
            collection.name == self.collection_name for collection in collections
        )

    def create_collection(self) -> bool:
        """Create a new collection if it doesn't exist"""
        try:
            if not self.check_collection_exists():
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                )
                return True
            return False
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    def delete_collection(self) -> bool:
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False

    async def upsert_points(self, excel_data: list[dict]) -> bool:
        """
        Upsert points into the collection
        Args:
            vectors: list of vector embeddings
            metadata: list of metadata dictionaries
            ids: Optional list of IDs for the points
        """
        try:
            points = []

            for doc in excel_data:
                # Store original data in payload
                document = {"original_data": doc}

                # Generate embedding using Bedrock
                payload = {"inputText": json.dumps(doc)}
                body = json.dumps(payload)
                embedding = await bedrock_service.create_embedding_async(body)

                # Create point for Qdrant
                point = models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=document,
                )

                points.append(point)

            # Bulk insert into Qdrant
            self.client.upsert(collection_name=self.collection_name, points=points)

            return True

        except Exception as e:
            raise ValueError(f"Failed to bulk insert: {str(e)}")

    def search_points(
        self,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Search for similar vectors in the collection
        Args:
            query_vector: Vector to search for
            limit: Number of results to return
            score_threshold: Minimum similarity score threshold
        """
        try:
            search_params = models.SearchParams(
                hnsw_ef=128,  # Higher values give better accuracy at the cost of speed
                exact=False,  # Set to True for exact search (slower but more accurate)
            )

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                search_params=search_params,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {"id": result.id, "score": result.score, "metadata": result.payload}
                )

            return formatted_results
        except Exception as e:
            print(f"Error searching points: {e}")
            return []

    def get_point_by_id(self, point_id: str | int) -> dict | None:
        """Retrieve a specific point by ID"""
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name, ids=[point_id]
            )
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "metadata": point.payload,
                }
            return None
        except Exception as e:
            print(f"Error retrieving point: {e}")
            return None

    def count_points(self) -> int:
        """Get the total number of points in the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.vectors_count
        except Exception as e:
            print(f"Error counting points: {e}")
            return 0

    def delete_points(self, point_ids: list[Union[str, int]]) -> bool:
        """Delete points by their IDs"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=point_ids),
            )
            return True
        except Exception as e:
            print(f"Error deleting points: {e}")
            return False

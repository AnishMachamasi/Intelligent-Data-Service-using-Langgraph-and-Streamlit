import asyncio
import json
from typing import Any

import boto3
from langchain_aws import ChatBedrock


class BedrockAsync:
    def __init__(self):
        self.client = boto3.client("bedrock-runtime")
        self.model_id = (
            "anthropic.claude-3-sonnet-20240229-v1:0"  # Claude 3.5 Sonnet model ID
        )
        self.embedding_model_id = "amazon.titan-embed-text-v1"

    async def create_llm(self):
        llm = ChatBedrock(
            model_id=self.model_id,  # Using the latest model
            model_kwargs=dict(temperature=0),
            streaming=True,
        )
        return llm

    async def invoke_model_async(
        self,
        prompt: str,
        max_tokens: int = 10000,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> dict[Any, Any]:
        try:
            # Prepare the request body for Claude 3.5
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            # Add system message if provided
            if system:
                request_body["system"] = system

            # Invoke the model
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            # Parse and return the response
            response_body = json.loads(response.get("body").read())
            return response_body.get("content")[0].get("text")

        except Exception as e:
            raise Exception(f"Error invoking Bedrock: {str(e)}")

    async def create_embedding_async(self, body: str) -> list[float]:
        """
        Create embeddings for the given text using Titan Text Embeddings model
        Args:
            text: Input text to embed
            dimensions: Size of embedding vector (256, 512, or 1024)
            normalize: Whether to normalize the embeddings
        Returns:
            List of embedding values
        """
        try:
            response = self.client.invoke_model(
                modelId=self.embedding_model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )

            response_body = json.loads(response.get("body").read())
            return response_body.get("embedding")

        except Exception as e:
            raise Exception(f"Error creating embedding: {str(e)}")

    async def batch_invoke(
        self,
        prompts: list[str],
        system: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ):
        """Process multiple prompts concurrently"""
        tasks = [
            self.invoke_model_async(
                prompt, max_tokens=max_tokens, temperature=temperature, system=system
            )
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def batch_embeddings(
        self, texts: list[str], dimensions: int = 1024, normalize: bool = True
    ) -> list[list[float]]:
        """Process multiple texts for embeddings concurrently"""
        tasks = [
            self.create_embedding_async(
                text, dimensions=dimensions, normalize=normalize
            )
            for text in texts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Convert to list of embeddings, replacing exceptions with None
        processed_results: list[list[float] | None] = [
            result if not isinstance(result, BaseException) else None
            for result in results
        ]

        # Filter out None values for type safety
        return [r for r in processed_results if r is not None]

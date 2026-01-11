import chromadb
from chromadb.config import Settings
from openai import OpenAI


class FinancialSituationMemory:
    def __init__(self, name, config):
        if config["backend_url"] == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
        else:
            self.embedding = "text-embedding-3-small"
        self.client = OpenAI(base_url=config["backend_url"])
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.get_or_create_collection(name=name)
        self._embedding_available = None  # Lazy check

    def _check_embedding_available(self):
        """Check if embedding model is available (cached result)"""
        if self._embedding_available is None:
            try:
                # Try a simple embedding to check availability
                self.client.embeddings.create(model=self.embedding, input="test")
                self._embedding_available = True
            except Exception as e:
                print(f"WARNING: Embedding model '{self.embedding}' not available: {e}")
                print("Memory features will be disabled. To enable, run: ollama pull nomic-embed-text")
                self._embedding_available = False
        return self._embedding_available

    def _truncate_text(self, text):
        """Truncate text to avoid context length errors"""
        max_chars = 2000  # ~500 tokens, safe for nomic-embed-text
        if len(text) > max_chars:
            return text[:max_chars], True
        return text, False

    def get_embedding(self, text):
        """Get OpenAI embedding for a text"""
        if not self._check_embedding_available():
            return [0.0] * 768  # nomic-embed-text dimension

        text, truncated = self._truncate_text(text)
        if truncated:
            print(f"WARNING: Truncated embedding input to {len(text)} chars")

        try:
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"WARNING: Embedding failed: {e}")
            return [0.0] * 768

    def get_embeddings_batch(self, texts):
        """Get embeddings for multiple texts in a single API call (much faster)"""
        if not self._check_embedding_available():
            return [[0.0] * 768 for _ in texts]

        if not texts:
            return []

        # Truncate all texts
        processed_texts = []
        for text in texts:
            truncated_text, _ = self._truncate_text(text)
            processed_texts.append(truncated_text)

        try:
            response = self.client.embeddings.create(
                model=self.embedding, input=processed_texts
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            print(f"WARNING: Batch embedding failed: {e}")
            return [[0.0] * 768 for _ in texts]

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""
        if not situations_and_advice:
            return

        situations = []
        advice = []
        ids = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))

        # Batch embedding - single API call instead of N calls
        embeddings = self.get_embeddings_batch(situations)

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings"""
        # Return empty if embedding not available
        if not self._check_embedding_available():
            return []

        try:
            query_embedding = self.get_embedding(current_situation)

            # Check if collection has any documents
            if self.situation_collection.count() == 0:
                return []

            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_matches, self.situation_collection.count()),
                include=["metadatas", "documents", "distances"],
            )

            matched_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    matched_results.append(
                        {
                            "matched_situation": results["documents"][0][i],
                            "recommendation": results["metadatas"][0][i]["recommendation"],
                            "similarity_score": 1 - results["distances"][0][i],
                        }
                    )

            return matched_results
        except Exception as e:
            print(f"WARNING: Memory retrieval failed: {e}")
            return []


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")

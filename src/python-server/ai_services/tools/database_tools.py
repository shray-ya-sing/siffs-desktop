from langchain.tools import tool
import os
from pinecone import Pinecone
import voyageai
import logging
from typing import List, Dict

# Initialize logger
logger = logging.getLogger(__name__)

pc = Pinecone(api_key='pcsk_QEA8e_RNPvdrhcXJLZQnNCq6U3BSeNbpTS7VMLaE4VEmh9ZSUUwgP5j23yu5psPbWBoo3')
index = pc.Index('prnewswire-articles')
voyage_client = voyageai.Client(api_key='pa-lkitG0Pwd7QpXkb7EUyATIlTGHY2aJ6oYHMvOydjfk7')

@tool
def search_financial_news(query: str, top_k: int = 5) -> List[Dict]:
    """
    Searches the financial news database and returns the full content of relevant articles.
    
    Args:
        query: The search query as a string (e.g., "KKR acquisitions", "private equity deals 2024").
        top_k: The number of top articles to return (default 5, max 10).

    Returns:
        A list of dictionaries, each containing the full article content, title, and URL.
    """
    try:
        # Limit top_k to prevent overwhelming the agent
        top_k = min(top_k, 10)
        
        # Generate embedding for the query
        query_embedding = voyage_client.embed(
            texts=[query],
            model="voyage-3-large",
            input_type="query"
        ).embeddings[0]

        # Search the index
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        articles = []
        for match in response.matches:
            article = {
                "title": match.metadata.get('title', 'Untitled'),
                "content": match.metadata.get('content', ''),
                "url": match.metadata.get('url', ''),
                "relevance_score": round(match.score, 4)
            }
            articles.append(article)

        logger.info(f"Found {len(articles)} articles for query: {query}")
        return articles

    except Exception as e:
        logger.error(f"Error during search_financial_news: {str(e)}")
        return []

DATABASE_TOOLS = [search_financial_news]
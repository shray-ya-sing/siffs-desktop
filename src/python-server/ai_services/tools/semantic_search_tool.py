from typing import Dict, List, Optional, TypedDict, Literal
from pydantic import BaseModel, Field
import sys
from pathlib import Path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import LLMProvider, Message, ToolCall
import numpy as np
import json
from langchain_core.tools import tool

class SearchResult(TypedDict):
    score: float
    content: str
    workbook_name: str
    metadata: Dict[str, any]

class SemanticSearchTool:
    def __init__(self, retriever):
        self.retriever = retriever
        self.name = "search_excel_content"
        self.description = """
        Search for content across Excel workbooks. Use this when you need to:
        - Find specific data in large spreadsheets
        - Locate formulas or values across multiple sheets
        - Search for specific patterns or data types
        - Audit spreadsheets for specific content
        """
    
    def get_tool_schema(self) -> dict:
        """Return the tool schema for the LLM provider."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant Excel content"
                        },
                        "workbook_path": {
                            "type": "string",
                            "description": "Optional path to a specific workbook to search within"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)",
                            "default": 5
                        },
                        "min_score": {
                            "type": "number",
                            "description": "Minimum relevance score (0-1) for results",
                            "default": 0.2
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def execute(self, tool_call: ToolCall) -> List[SearchResult]:
        """Execute the tool with the given arguments."""
        try:
            args = json.loads(tool_call.function.arguments)
            return await self.search_excel_content(**args)
        except Exception as e:
            return [{"error": f"Failed to execute search: {str(e)}"}]
    
    @tool
    async def search_excel_content(
        self,
        query: str,
        workbook_path: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.2
    ) -> List[SearchResult]:
        """Implementation remains the same as before"""
        try:
            if not query:
                return [{"error": "No search query provided"}]
            
            results = await self.retriever.search(
                query=query,
                workbook_path=workbook_path,
                top_k=top_k,
                score_threshold=min_score
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "score": result["score"],
                    "content": result.get("text", result.get("markdown", "")),
                    "workbook_name": result.get("workbook_name", "Unknown"),
                    "metadata": result.get("metadata", {})
                })
            
            return formatted_results
            
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]

    def as_tool(self):
        """Return the search method as a LangChain tool"""
        return self.search_excel_content
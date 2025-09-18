# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import numpy as np
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class EmbedChunksRequest(BaseModel):
    chunks: List[Dict[str, Any]] = Field(..., description="List of chunks with 'text', 'markdown', and 'metadata'")
    model_name: Optional[str] = Field(default="msmarco-MiniLM-L-6-v3", description="Sentence transformer model to use")
    normalize: Optional[bool] = Field(default=True, description="Whether to normalize embeddings")

class StoreEmbeddingsRequest(BaseModel):
    workbook_path: str = Field(..., description="Path to the Excel file")
    chunks: List[Dict[str, Any]] = Field(..., description="List of chunks with text, markdown, and metadata")
    embedding_model: str = Field(..., description="Name of the embedding model used")
    create_new_version: Optional[bool] = Field(default=True, description="Replace if workbook already exists")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    workbook_path: Optional[str] = Field(default=None, description="Limit search to specific workbook")
    top_k: Optional[int] = Field(default=5, description="Number of results to return")
    return_format: Optional[str] = Field(default="markdown", description="Format to return: 'text', 'markdown', or 'both'")

class StorePrecomputedEmbeddingsRequest(BaseModel):
    workbook_path: str = Field(..., description="Path to the Excel file")
    chunks: List[Dict[str, Any]] = Field(..., description="List of chunks with text, markdown, and metadata")
    embeddings: List[List[float]] = Field(..., description="Pre-computed embeddings for the chunks")
    embedding_model: str = Field(..., description="Name of the embedding model used")
    create_new_version: Optional[bool] = Field(default=True, description="Replace if workbook already exists")
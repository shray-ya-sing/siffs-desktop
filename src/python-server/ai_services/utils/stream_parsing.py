"""
Utility functions for parsing streaming outputs from LangGraph agents and workflows.

This module provides functions to handle different stream modes ('messages' and 'custom')
and extract meaningful content from streaming responses.
"""
from typing import Any, Dict, List, Optional, Tuple, Union, Literal
from dataclasses import dataclass


@dataclass
class StreamMessage:
    """Container for parsed stream message data."""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    message_type: Optional[str] = None
    node_name: Optional[str] = None


def parse_stream_messages(
    chunks: List[Tuple[str, Any]],
    stream_modes: List[Literal["messages", "custom"]] = ["messages", "custom"]
) -> List[StreamMessage]:
    """
    Parse streaming output from LangGraph's stream/astream methods.

    Args:
        chunks: List of (mode, chunk) tuples from LangGraph's streaming output
        stream_modes: Which stream modes to include in the output

    Returns:
        List of parsed StreamMessage objects
    """
    parsed_messages = []
    
    for mode, chunk in chunks:
        if mode not in stream_modes:
            continue
            
        if mode == "messages":
            # Handle LLM token streaming
            message_chunk, metadata = chunk
            if hasattr(message_chunk, 'content') and message_chunk.content:
                parsed_messages.append(StreamMessage(
                    content=message_chunk.content,
                    metadata=metadata,
                    message_type="llm_token",
                    node_name=metadata.get("langgraph_node") if metadata else None
                ))
        
        elif mode == "custom":
            # Handle custom data streaming
            if isinstance(chunk, dict):
                # If it's a dict, try to extract meaningful content
                content = chunk.get("content") or str(chunk)
                parsed_messages.append(StreamMessage(
                    content=content,
                    metadata=chunk,
                    message_type="custom_data"
                ))
            else:
                # For non-dict custom data, just convert to string
                parsed_messages.append(StreamMessage(
                    content=str(chunk),
                    message_type="custom_data"
                ))
    
    return parsed_messages


def get_llm_tokens(
    chunks: List[Tuple[str, Any]],
    node_name: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> str:
    """
    Extract LLM token content from streaming output.
    
    Args:
        chunks: List of (mode, chunk) tuples from LangGraph's streaming output
        node_name: If provided, only return tokens from this node
        tags: If provided, only return tokens with these tags
        
    Returns:
        Concatenated string of all matching LLM tokens
    """
    messages = parse_stream_messages(chunks, stream_modes=["messages"])
    
    filtered_messages = []
    for msg in messages:
        if msg.message_type != "llm_token":
            continue
            
        if node_name and msg.node_name != node_name:
            continue
            
        if tags and not (msg.metadata and any(tag in msg.metadata.get("tags", []) for tag in tags)):
            continue
            
        filtered_messages.append(msg.content)
    
    return "".join(filtered_messages)


def get_custom_data(
    chunks: List[Tuple[str, Any]],
    data_key: Optional[str] = None
) -> List[Any]:
    """
    Extract custom data from streaming output.
    
    Args:
        chunks: List of (mode, chunk) tuples from LangGraph's streaming output
        data_key: If provided, only return data with this key
        
    Returns:
        List of custom data items
    """
    messages = parse_stream_messages(chunks, stream_modes=["custom"])
    
    if not data_key:
        return [msg.content for msg in messages]
    
    return [
        msg.metadata[data_key] 
        for msg in messages 
        if msg.metadata and data_key in msg.metadata
    ]


def stream_to_string(
    chunks: List[Tuple[str, Any]],
    include_metadata: bool = False
) -> str:
    """
    Convert streaming output to a human-readable string.
    
    Args:
        chunks: List of (mode, chunk) tuples from LangGraph's streaming output
        include_metadata: Whether to include metadata in the output
        
    Returns:
        Formatted string representation of the stream
    """
    messages = parse_stream_messages(chunks)
    
    if not include_metadata:
        return "".join(msg.content for msg in messages if msg.content)
    
    result = []
    for msg in messages:
        if not msg.content:
            continue
            
        parts = [f"[{msg.message_type}]"]
        if msg.node_name:
            parts.append(f"[{msg.node_name}]")
        parts.append(msg.content)
        
        if msg.metadata and include_metadata:
            parts.append(f"\nMetadata: {msg.metadata}\n")
            
        result.append(" ".join(parts))
    
    return "\n".join(result)

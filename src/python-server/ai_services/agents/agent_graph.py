from langgraph.graph import Graph, END
from langgraph.prebuilt import ToolNode
from typing import Dict, List, Optional, AsyncGenerator, Any
import json
from pathlib import Path
import sys

# Add parent directory to path for local imports
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))

from llm_service import LLMService
from agents.agent_state import AgentState
from base_provider import Message, ToolCall, ChatResponse
from prompts.system_prompts import VOLUTE_SYSTEM_PROMPT

class AgentGraph:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.graph = Graph()
        self.system_prompt = VOLUTE_SYSTEM_PROMPT
        
        # Define nodes
        self.graph.add_node("decide", self.decide_next_step)
        self.graph.add_node("generate_response", self.generate_response)
        
        # Add tool execution node if tools are available
        if self.llm_service._tools:
            # Convert tools to proper format if they have as_tool() method
            tools = []
            for tool in self.llm_service._tools.values():
                if hasattr(tool, 'as_tool') and callable(tool.as_tool):
                    tools.append(tool.as_tool())
                else:
                    tools.append(tool)
            
            # Add tool node with proper tools
            tool_node = ToolNode(tools)
            self.graph.add_node("execute_tools", tool_node)
            
            # Add edge from tools back to decide
            self.graph.add_edge("execute_tools", "decide")
        
        # Define edges
        self.graph.add_conditional_edges(
            "decide",
            self.route_decision,
            {
                "generate_response": "generate_response",
                "use_tools": "execute_tools" if self.llm_service._tools else "generate_response",
                "end": END
            }
        )
        
        # Set entry point
        self.graph.set_entry_point("decide")
        
        # Compile the graph
        self.runnable = self.graph.compile()
    
    async def decide_next_step(self, state: AgentState) -> Dict[str, Any]:
        """Decide the next step in the agent's workflow"""
        messages = state["messages"]
        
        # Add system message if not present
        if not any(m.role == "system" for m in messages):
            messages.insert(0, Message(
                role="system",
                content=self.system_prompt
            ))
        # Get LLM decision
        response = await self.llm_service.chat_completion(
            messages=messages,
            model=state["model"],
            temperature=0.2,  # Lower temperature for more predictable decisions
            max_tokens=50
        )
        
        # Simple decision logic - can be enhanced
        decision = response.content.lower().strip()
        if any(keyword in decision for keyword in ["tool", "search", "lookup"]) and self.llm_service._tools:
            return {"next": "use_tools"}
        return {"next": "generate_response"}
    
    async def generate_response(self, state: AgentState) -> Dict[str, str]:
        """Generate final response to user with streaming support"""
        messages = state["messages"]
        
        # Stream the response
        full_response = ""
        async for chunk in self.llm_service.stream_chat_completion(
            messages=messages,
            model=state["model"],
            temperature=state.get("temperature", 0.7),
            max_tokens=state.get("max_tokens", 1000),
            tools=state.get("tools"),
            tool_choice=state.get("tool_choice", "auto"),
            client_id=state.get("client_id"),
            request_id=state.get("request_id")
        ):
            if chunk.content:
                full_response += chunk.content
                if "yield_chunk" in state:
                    await state["yield_chunk"](chunk)
        
        # Add final assistant message to state
        messages.append(Message(
            role="assistant",
            content=full_response,
            tool_calls=state.get("tool_calls")
        ))
        
        return {"next": "end"}
    
    async def execute_tools(self, state: AgentState) -> Dict[str, Any]:
        """Execute tools based on tool calls"""
        messages = state["messages"]
        last_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
        
        if not last_msg or not last_msg.tool_calls:
            return {"next": "generate_response"}
        
        # Execute each tool call
        for tool_call in last_msg.tool_calls:
            if tool_call.name in self.llm_service._tools:
                tool = self.llm_service._tools[tool_call.name]
                try:
                    # Emit tool call event
                    if "client_id" in state and "request_id" in state:
                        tool_args = json.loads(tool_call.arguments) if tool_call.arguments else {}
                        query = tool_args.get('query', '')
                        await manager.send_message(state["client_id"], {
                            'type': 'TOOL_CALL',
                            'toolName': tool_call.name,
                            'query': query,
                            'requestId': state["request_id"],
                            'status': 'started'
                        })
                    
                    # Handle both direct call and execute method
                    if hasattr(tool, 'arun'):
                        result = await tool.arun(tool_call.arguments)
                    elif hasattr(tool, 'run'):
                        result = await tool.run(tool_call.arguments)
                    else:
                        result = await tool(tool_call.arguments)
                    
                    # Emit tool result event
                    if "client_id" in state and "request_id" in state:
                        await manager.send_message(state["client_id"], {
                            'type': 'TOOL_RESULT',
                            'toolName': tool_call.name,
                            'result': result,
                            'requestId': state["request_id"],
                            'status': 'completed'
                        })
                    
                    # Add tool result to messages
                    messages.append(Message(
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=tool_call.id,
                        name=tool_call.name
                    ))
                except Exception as e:
                    error_msg = f"Error executing {tool_call.name}: {str(e)}"
                    if "client_id" in state and "request_id" in state:
                        await manager.send_message(state["client_id"], {
                            'type': 'TOOL_RESULT',
                            'toolName': tool_call.name,
                            'result': {'error': error_msg},
                            'requestId': state["request_id"],
                            'status': 'error'
                        })
                    
                    messages.append(Message(
                        role="tool",
                        content=error_msg,
                        tool_call_id=tool_call.id,
                        name=tool_call.name
                    ))
        
        return {"next": "decide"}
    
    def route_decision(self, state: AgentState) -> str:
        """Route to next node based on decision"""
        return state.get("next", "end")
    
    async def astream(self, state: Dict, yield_chunk=None):
        """Async stream through the agent's execution"""
        state = state.copy()
        if yield_chunk:
            state["yield_chunk"] = yield_chunk
        
        async for step in self.runnable.astream(state):
            yield step
# ai_services/llm_service.py
from typing import Dict, List, Optional, Union, AsyncGenerator
import sys
from pathlib import Path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import Message, ChatResponse, ToolCall, LLMProvider
from factory import ProviderFactory
from tools.semantic_search_tool import SemanticSearchTool

class LLMService:
    def __init__(self, retriever=None):
        self._providers: Dict[str, LLMProvider] = {}
        self._model_to_provider: Dict[str, str] = {}
        self._tools: Dict[str, Any] = {}
        
        # Initialize semantic search tool if retriever and storage are provided
        if retriever:
            self.register_tool(SemanticSearchTool(retriever))
        
        self._initialize_providers()
    
    def register_tool(self, tool) -> None:
        """Register a tool with the LLM service."""
        self._tools[tool.get_tool_schema()["function"]["name"]] = tool
    
    def _initialize_providers(self):
        """Initialize all available providers and build model mapping"""
        supported_models = ProviderFactory.get_supported_models()
        
        for provider_name in supported_models:
            # Initialize provider with any required config
            provider = ProviderFactory.get_provider(provider_name)
            if provider:
                self._providers[provider_name] = provider
                # Map each model to its provider
                for model in supported_models[provider_name]:
                    self._model_to_provider[model] = provider_name
    
    def get_provider_for_model(self, model: str) -> Optional[LLMProvider]:
        """Get the provider for a specific model"""
        provider_name = self._model_to_provider.get(model)
        if not provider_name:
            return None
        return self._providers.get(provider_name)
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        request_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> ChatResponse:
        """Unified chat completion with tool support"""
        provider = self.get_provider_for_model(model)
        if not provider:
            raise ValueError(f"No provider found for model: {model}")

        # Add registered tools to the request if tools are requested
        if tools is not None and self._tools:
            tools = tools or []
            # Add registered tools that aren't already in the request
            registered_tool_names = {t.get_tool_schema()["function"]["name"]: t.get_tool_schema() 
                                   for t in self._tools.values()}
            for tool_schema in registered_tool_names.values():
                if tool_schema not in tools:
                    tools.append(tool_schema)
        else:
            tools = []
        
        # Make the request
        response = await provider.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )
        
        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name in self._tools:
                    tool = self._tools[tool_call.function.name]
                    
                    # Emit tool call event
                    if client_id and request_id:
                        tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        query = tool_args.get('query', '')
                        from api.websocket_manager import manager
                        await manager.send_message(client_id, {
                            'type': 'TOOL_CALL',
                            'toolName': tool_call.function.name,
                            'query': query,
                            'requestId': request_id,
                            'status': 'started'
                        })
                    
                    # Execute the tool
                    tool_result = await tool.execute(tool_call)
                    
                    # Emit tool result event
                    if client_id and request_id:
                        from api.websocket_manager import manager
                        await manager.send_message(client_id, {
                            'type': 'TOOL_RESULT',
                            'toolName': tool_call.function.name,
                            'result': tool_result,
                            'requestId': request_id,
                            'status': 'completed'
                        })
                    
                    # Add the tool result to the messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(tool_result)
                    })
            
            # Get a new completion with the tool results
            return await self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                request_id=request_id,
                client_id=client_id
            )
        
        return response
    
    async def stream_chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        request_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Stream chat completion responses"""
        provider = self.get_provider_for_model(model)
        if not provider:
            raise ValueError(f"No provider found for model: {model}")
        
        # Add registered tools to the request if tools are requested
        if tools is not None and self._tools:
            tools = tools or []
            # Add registered tools that aren't already in the request
            registered_tool_names = {t.get_tool_schema()["function"]["name"]: t.get_tool_schema() 
                                   for t in self._tools.values()}
            for tool_schema in registered_tool_names.values():
                if tool_schema not in tools:
                    tools.append(tool_schema)
        else:
            tools = []
        
        # Buffer to accumulate tool calls
        tool_calls_buffer = []
        
        async for chunk in provider.stream_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        ):
            # If this chunk contains tool calls, buffer them
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                tool_calls_buffer.extend(chunk.tool_calls)
            
            # If we have buffered tool calls and this is the last chunk, execute them
            if tool_calls_buffer and chunk.finish_reason == 'tool_calls':
                for tool_call in tool_calls_buffer:
                    if tool_call.function.name in self._tools:
                        tool = self._tools[tool_call.function.name]
                        
                        # Emit tool call event
                        if client_id and request_id:
                            tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                            query = tool_args.get('query', '')
                            from api.websocket_manager import manager
                            await manager.send_message(client_id, {
                                'type': 'TOOL_CALL',
                                'toolName': tool_call.function.name,
                                'query': query,
                                'requestId': request_id,
                                'status': 'started'
                            })
                        
                        # Execute the tool
                        tool_result = await tool.execute(tool_call)
                        
                        # Emit tool result event
                        if client_id and request_id:
                            from api.websocket_manager import manager
                            await manager.send_message(client_id, {
                                'type': 'TOOL_RESULT',
                                'toolName': tool_call.function.name,
                                'result': tool_result,
                                'requestId': request_id,
                                'status': 'completed'
                            })
                        
                        # Add the tool result to the messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": json.dumps(tool_result)
                        })
                
                # Clear the buffer
                tool_calls_buffer = []
                
                # Get a new completion with the tool results
                async for new_chunk in self.stream_chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    request_id=request_id,
                    client_id=client_id
                ):
                    yield new_chunk
                return
            
            yield chunk
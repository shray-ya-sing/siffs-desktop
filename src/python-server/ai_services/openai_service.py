# C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\ai_services\openai_service.py
import os
import tiktoken
from typing import AsyncGenerator, Dict, List, Optional, Union
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('OpenAIService')

class OpenAIService:
    """
    A service class for interacting with OpenAI's chat models.
    Specialized in analyzing and evaluating model responses.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: Optional API key. If not provided, will use OPENAI_API_KEY environment variable.
        """
        self.client = AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY")
        )
        self.encodings = {}  # Cache for tokenizers

    async def get_chat_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Get a chat completion from OpenAI's API.
        
        Args:
            system_prompt: System message to set the behavior
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            model: Model to use (default: gpt-4-turbo-preview)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            
        Returns:
            String response or async generator for streaming
        """
        try:
            if stream:
                async def stream_generator():
                    stream = await self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt}] + messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True
                    )
                    
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                return stream_generator()
            else:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                return response.choices[0].message.content or ""
                
        except Exception as e:
            logger.error(f"Error in OpenAI chat completion: {str(e)}")
            raise Exception(f"OpenAI API Error: {str(e)}")

    async def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens for given text using tiktoken.
        
        Args:
            text: Text to count tokens for
            model: Model name to get proper encoding
            
        Returns:
            Number of tokens
        """
        try:
            # Get or create the appropriate encoding
            if model not in self.encodings:
                try:
                    enc = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback to cl100k_base which works with most models
                    enc = tiktoken.get_encoding("cl100k_base")
                self.encodings[model] = enc
            
            return len(self.encodings[model].encode(text))
            
        except Exception as e:
            logger.warning(f"Token counting failed, using approximation: {str(e)}")
            return self._approximate_token_count(text)

    def _approximate_token_count(self, text: str) -> int:
        """
        Fallback method for approximate token counting.
        Based on average characters per token in English text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
            
        # Average characters per token in English is ~4
        # For code/structured data, it's typically lower (~3)
        char_count = len(text)
        
        # Check if text looks like structured data
        if any(marker in text[:1000] for marker in ['|', 'addr=', 'val=', 'fmt=']):
            return int(char_count / 3.0)
        return int(char_count / 4.0)

    async def evaluate_response(
    self,
    model_response: str,
    golden_answer: str,
    criteria: Optional[List[str]] = None
) -> Dict[str, Union[float, str, Dict[str, float]]]:
        """
        Evaluate a model response against a golden answer using OpenAI's API.
        
        Args:
            model_response: The response from the model to evaluate
            golden_answer: The expected/correct response
            criteria: List of evaluation criteria to consider
            
        Returns:
            Dictionary containing:
            - score: float between 0.0 and 1.0
            - reasoning: str with explanation of the score
            - criteria_scores: Dict with scores for each criterion
        """
        import json
        from typing import Dict, Union
        
        if criteria is None:
            criteria = [
                "accuracy", "completeness"
            ]
            
        system_prompt = f"""You are an expert evaluator of AI model responses.
        Compare the MODEL RESPONSE with the GOLDEN ANSWER and provide a score from 0.0 to 1.0.
        Consider these criteria: {', '.join(criteria)}.
        Be strict but fair in your evaluation. Your evaluation will be solely based on whether all the errors from the golden answer were captured correctly in the model response. If all the errors were captured correctly give score of 1. Scores lower than 1 should represent the proportion of errors caught. For ex, 0.6 would imply that the model response caught 60% of the errors from the golden answer. 
        Scores should NOT be based on quality of the commentary, language, comprehensibility, phrasing, conciseness or other qualitative attributes of the model response. You are judging solely on accuracy whether the model response captured all the errors from the golden answer. 
        In no error situations, if the model response identifies that there are no errors in the section of the excel workbook and the the golden answer states 'No Error' that means the llm response was accurate, and you need to score it 1, even if the llm response contains other commentary like suggesting that the cells are empty and only formatted, which could imply potential issues with data entry or completeness. Disregard the commentary and just focus on checking whether it matched the errors from the golden answer. 
        The error type mentioned by the model response doesn't matter as much as it catching the error cell location and the core explanation of what the error is. So if the model response catches an error, count it as accurate even if it gives a different error type than in the golden answer.
        Remember that your job is to do a simplistic matching of the errors caught by the model response vs the errors in the golden answer. 
        Respond with a valid JSON object containing:
        1. "score": A float between 0.0 and 1.0
        2. "reasoning": A string explaining your evaluation. If the model response missed certain errors from the golden answer, mention what errors and error types it missed.
        3. "criteria_scores": An object with scores for each criterion
        """
        
        user_prompt = f"""GOLDEN ANSWER:
        {golden_answer}

        MODEL RESPONSE:
        {model_response}

        Provide your evaluation as a JSON object.
        """
        
        try:
            # Get the raw response from the model
            response = await self.get_chat_completion(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                stream=False,
                model="gpt-4o-mini"  # Using a known good model
            )
            
            # Parse the JSON response
            try:
                evaluation = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON if response contains markdown code blocks
                import re
                json_match = re.search(r'``[(?:json)?\n(.*?)\n](cci:1://file:///c:/Users/shrey/projects/cori-apps/cori_app/src/python-server/ai_services/openai_service.py:21:4-31:52)``', response, re.DOTALL)
                if json_match:
                    evaluation = json.loads(json_match.group(1).strip())
                else:
                    raise ValueError("Failed to parse evaluation response as JSON")
            
            # Validate the response structure
            required_keys = {"score", "reasoning", "criteria_scores"}
            if not all(key in evaluation for key in required_keys):
                missing = required_keys - evaluation.keys()
                raise ValueError(f"Invalid evaluation response. Missing keys: {missing}")
                
            # Ensure score is within valid range
            if not 0 <= float(evaluation["score"]) <= 1.0:
                evaluation["score"] = max(0.0, min(1.0, float(evaluation["score"])))
                logger.warning(f"Score was outside [0,1] range, clamped to {evaluation['score']}")
                
            return {
                "score": float(evaluation["score"]),
                "reasoning": str(evaluation["reasoning"]).strip(),
                "criteria_scores": {
                    str(k): float(v) 
                    for k, v in evaluation["criteria_scores"].items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in evaluation: {str(e)}")
            # Return a default error response
            return {
                "score": 0.0,
                "reasoning": f"Evaluation failed: {str(e)}",
                "criteria_scores": {c: 0.0 for c in criteria},
                "error": str(e)
            }
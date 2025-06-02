from typing import AsyncGenerator, Union, Dict, Optional
from anthropic.types import MessageStreamEvent
from pathlib import Path
import sys
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# Import from ai_services
from ai_services.anthropic_service import AnthropicService

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('LLMAnalyzer')

class LLMAnalyzer:
    """
    A class for analyzing Excel metadata using LLM models.
    Specialized in detecting errors in financial model metadata.
    """
    
    def __init__(self, anthropic_service: Optional[AnthropicService] = None):
        """
        Initialize the LLM Analyzer with an optional Anthropic service instance.
        If no service is provided, a new one will be created.
        """
        self.anthropic_service = anthropic_service or AnthropicService()

    @staticmethod
    def _get_error_detection_system_prompt() -> str:
        """Returns the system prompt for financial model error detection."""
        return """You are an expert at detecting errors in excel financial model metadata. 

You have expert financial knowledge so you understand the correct mathematical and excel formulae used in excel models to produce financial analyses like three statement modelling, DCF modelling, Merger accretion and dilution, leveraged buyout analysis. 

You are capable of detecting the following types of errors based on your analysis of the model metadata, which contains detailed information about cells. You analyze cells and their linked and surrounding cells to determine if there are any errors in the cells. 

If you find an error, respond with this string data: 
Error Cell(s): [which ever cell or cell range has the errors]
Error type: [type of error]
Error Explanation: [explain exactly what the error is]
Error Fix: [How to fix the error]

Create a new paragraph for each error found. Only group multiple cell errors in the same paragraph if its the same error being carried over to multiple cells. 

Pay attention to the precedents and dependents: if a cell has incorrect formulae or values then cells linking to that cell will have incorrect values as well and need to be called out. 

If there are no errors in the metadata respond by saying there is no error.

Remember your goal is to find the critical errors that are creating mistakes and invalid / incorrect values and analyses. Your job is not to suggest enhancements or best practices, there could be improvements to be made but that's not your job. You are here to detect errors only.

These are the types of errors you can detect extremely well: 

1) Incorrect or incomplete formula in cell: Cell contains a formula that doesn't make sense to use in the context of what the purpose is. 
2) Cell is linked to the wrong cell: The formula in the cell itself is appropriate but links to incorrect cells.
3) Inappropriate formula for the situation: The situation calls for a specific type of formula but an inappropriate one was used.
4) Non-link related mistake in the cell: Hardcoded values or constants in formulas that are incorrect.
"""

    async def analyze_metadata(
        self, 
        model_metadata: Union[str, Dict],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 20000,
        temperature: float = 0.3,
        stream: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Analyze Excel model metadata for errors using an LLM.
        """
        if isinstance(model_metadata, dict):
            model_metadata = str(model_metadata)
        
        system_prompt = self._get_error_detection_system_prompt()
        user_message = f"Please analyze this Excel model metadata for any errors:\n\n{model_metadata}"
        
        try:
            return await self.anthropic_service.get_anthropic_chat_completion(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
        except Exception as e:
            logger.error(f"Error analyzing metadata: {str(e)}")
            if stream:
                async def error_generator():
                    yield f"Error: {str(e)}"
                return error_generator()
            else:
                raise Exception(f"Error analyzing model metadata: {str(e)}")
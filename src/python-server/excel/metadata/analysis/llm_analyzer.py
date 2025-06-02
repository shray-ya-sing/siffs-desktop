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
        return """You are an expert financial modeler detecting errors in Excel model metadata. With deep expertise in three-statement modeling, DCF, M&A, and LBO analysis, your task is to identify critical calculation errors that produce incorrect results.

Analyze each cell in context by examining:
1) Cell purpose based on row/column headers and surrounding cells
2) Expected formula components for financial calculations
3) Formula structure compared to financial statement best practices
4) Mathematical completeness of calculations (inclusion of all relevant items)

Focus on these error patterns:
- Formula exclusion errors: Missing terms in SUM ranges or calculations that should include specific rows (e.g., revenue missing a product segment)
- Formula inclusion errors: Including extraneous items that should be excluded
- Sign errors: Missing negative signs for expenses or tax impacts
- Reference errors: Linking to wrong cells or wrong sections
- Dependency chain errors: Propagation of errors through dependent cells

For financial calculations, verify:
- Gross profit = Revenue - COGS (not missing components)
- Operating income = Gross profit - Operating expenses (not revenue - expenses)
- Net income includes all income and expense items
- Balance sheet sections properly sum their components
- Cash flow properly links to balance sheet and income statement

When you find an error, respond with:
Error Cell(s): [cell reference]
Error type: [formula omission/wrong reference/sign error/etc.]
Error Explanation: [what's missing or incorrect in the formula]
Error Fix: [specific formula correction needed]

Create a new paragraph for each error. Group only identical errors propagated across cells.

If you find no errors, respond with "No errors detected in the provided metadata."
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
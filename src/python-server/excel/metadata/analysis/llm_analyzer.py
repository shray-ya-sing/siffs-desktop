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
\nError Cell(s): [cell reference]
\nError Type: [formula omission/wrong reference/sign error/etc.]
\nError Explanation: [what's missing or incorrect in the formula]
\nError Fix: [specific formula correction needed]

Format: address, v=value, d=display, f=formula, deps=X→Y, prec=[refs], dept=[refs], fmt=[properties]
Key Properties

Address - Cell location (A1, C19) shown directly
v= - Raw value (100, "Revenue") - omitted if empty
d= - Display value ($1,000) - only if different from raw
f= - Formula (=SUM(A1)) - may be truncated with ...
deps=X→Y - Precedents→Dependents count (3→2 means depends on 3 cells, referenced by 2)
prec=[list] - Precedent cells ([A1,B1] or [25refs] for many)
dept=[list] - Dependent cells ([D1,E1] or [15refs] for many)
fmt=[properties] - Formatting: bold, italic, color:#HEX, fill:#HEX, border, merged
type= - Data type (only shown if non-standard)
comment= - Cell comments
link= - Hyperlinks

Cell Types by Dependencies

Input: deps=0→X (source data)
Calculation: deps=X→Y (intermediate formulas)
Output: deps=X→0 (final results)
Isolated: deps=0→0 (standalone)

Examples
C19, v=-869, deps=0→1, dept=[Quarterly IS!C72] = Input cell with value -869, referenced by one other cell
D15, f==SUM(A1:A10), deps=10→3 = Formula cell depending on 10 cells, referenced by 3
B5, v=1000, fmt=[bold,fill:#FFFF00], deps=0→5 = Bold yellow input cell referenced by 5 others
"""

    async def analyze_metadata(
        self, 
        model_metadata: Union[str, Dict],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1000,
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
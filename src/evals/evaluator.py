from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import re
import json
from pathlib import Path
import asyncio
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('Evaluator')

@dataclass
class ErrorCase:
    """Represents a single error case with expected error details."""
    test_case_id: str
    tab_name: str
    cell_reference: str
    error_type: str
    error_description: str
    metadata_snippet: str
    expected_response: str
    severity: str = "critical"  # critical or non-critical
    
    def to_dict(self) -> dict:
        return {
            'test_case_id': self.test_case_id,
            'tab_name': self.tab_name,
            'cell_reference': self.cell_reference,
            'error_type': self.error_type,
            'error_description': self.error_description,
            'severity': self.severity,
            'metadata_snippet': self.metadata_snippet,
            'expected_response': self.expected_response
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ErrorCase':
        return cls(**data)

@dataclass
class EvaluationResult:
    """Stores the results of evaluating a single test case."""
    test_case_id: str
    passed: bool
    detected_error_types: Set[str] = field(default_factory=set)
    detected_cells: Set[str] = field(default_factory=set)
    false_positives: Set[str] = field(default_factory=set)
    false_negatives: Set[str] = field(default_factory=set)
    response_text: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'test_case_id': self.test_case_id,
            'passed': self.passed,
            'detected_error_types': list(self.detected_error_types),
            'detected_cells': list(self.detected_cells),
            'false_positives': list(self.false_positives),
            'false_negatives': list(self.false_negatives),
            'response_text': self.response_text,
            'error': self.error
        }

class ErrorEvaluator:
    """
    Evaluates Claude's ability to detect and identify errors in Excel metadata.
    """
    
    def __init__(self, output_dir: str = "eval_results"):
        """
        Initialize the evaluator with an output directory for results.
        
        Args:
            output_dir: Directory to store evaluation results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Regular expressions for parsing Claude's responses
        self.cell_ref_pattern = re.compile(
            r'(?i)Error Cell\(s\):[\s\n]*(?:\[([^\]]+)\][,\s]*)*([A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*)',
            re.IGNORECASE | re.DOTALL
        )
        self.error_type_pattern = re.compile(
            r'(?i)Error Type:[\s\n]*([^\n]+)',
            re.IGNORECASE
        )
    
    def _parse_error_response(self, response: str) -> Tuple[Set[str], Set[str]]:
        """
        Parse Claude's response to extract detected errors and cells.
        
        Args:
            response: Raw response text from Claude
            
        Returns:
            Tuple of (detected_error_types, detected_cells)
        """
        error_types = set()
        cells = set()
        
        # Extract error types
        error_type_matches = self.error_type_pattern.findall(response)
        for match in error_type_matches:
            error_types.add(match.strip().lower())
        
        # Extract cell references
        cell_matches = self.cell_ref_pattern.findall(response)
        for tab_match, cell_refs in cell_matches:
            tab_name = tab_match.strip() if tab_match else ""
            for cell_ref in cell_refs.split(','):
                cell_ref = cell_ref.strip()
                if tab_name:
                    cells.add(f"{tab_name.upper()}!{cell_ref.upper()}")
                else:
                    cells.add(cell_ref.upper())
        
        return error_types, cells
    
    def _calculate_metrics(
        self, 
        test_case: ErrorCase, 
        detected_error_types: Set[str], 
        detected_cells: Set[str]
    ) -> EvaluationResult:
        """
        Calculate evaluation metrics for a test case.
        
        Args:
            test_case: The test case being evaluated
            detected_error_types: Set of error types detected by Claude
            detected_cells: Set of cell references detected by Claude
            
        Returns:
            EvaluationResult with metrics
        """
        expected_cell = f"{test_case.tab_name.upper()}!{test_case.cell_reference.upper()}"
        expected_error_type = test_case.error_type.lower()
        
        # Check if the error was detected
        error_detected = expected_error_type in detected_error_types
        cell_detected = expected_cell in detected_cells
        
        # Calculate false positives/negatives
        false_positives = detected_cells - {expected_cell}
        false_negatives = set() if (error_detected and cell_detected) else {expected_cell}
        
        # Determine if the test passed
        passed = error_detected and cell_detected and not false_positives
        
        return EvaluationResult(
            test_case_id=test_case.test_case_id,
            passed=passed,
            detected_error_types=detected_error_types,
            detected_cells=detected_cells,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
    
    async def evaluate_single_case(
        self,
        test_case: ErrorCase,
        llm_analyzer
    ) -> EvaluationResult:
        """
        Evaluate a single test case by running it through the LLM analyzer.
        
        Args:
            test_case: The test case to evaluate
            llm_analyzer: Initialized LLMAnalyzer instance
            
        Returns:
            EvaluationResult with the test results
        """
        try:
            # Get response from Claude
            response = await llm_analyzer.analyze_metadata(
                model_metadata=test_case.metadata_snippet,
                stream=False
            )
            
            if not response:
                return EvaluationResult(
                    test_case_id=test_case.test_case_id,
                    passed=False,
                    error="Empty response from LLM"
                )
            
            # Parse the response
            detected_error_types, detected_cells = self._parse_error_response(response)
            
            # Calculate metrics
            result = self._calculate_metrics(
                test_case=test_case,
                detected_error_types=detected_error_types,
                detected_cells=detected_cells
            )
            result.response_text = response
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating test case {test_case.test_case_id}: {str(e)}")
            return EvaluationResult(
                test_case_id=test_case.test_case_id,
                passed=False,
                error=str(e)
            )
    
    async def run_evaluation(
        self,
        test_cases: List[ErrorCase],
        llm_analyzer,
        batch_size: int = 5,
        save_results: bool = True
    ) -> dict:
        """
        Run evaluation on multiple test cases.
        
        Args:
            test_cases: List of ErrorCase instances to evaluate
            llm_analyzer: Initialized LLMAnalyzer instance
            batch_size: Number of test cases to process in parallel
            save_results: Whether to save results to a file
            
        Returns:
            Dictionary with evaluation summary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = []
        
        # Process test cases in batches
        for i in range(0, len(test_cases), batch_size):
            batch = test_cases[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(test_cases)-1)//batch_size + 1}")
            
            # Run batch in parallel
            batch_results = await asyncio.gather(*[
                self.evaluate_single_case(test_case, llm_analyzer)
                for test_case in batch
            ])
            
            results.extend(batch_results)
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(test_cases):
                await asyncio.sleep(1)
        
        # Calculate summary statistics
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        accuracy = (passed / total) * 100 if total > 0 else 0
        
        # Count errors by type
        error_type_counts = {}
        for case in test_cases:
            error_type = case.error_type.lower()
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
        
        # Count detected errors by type
        detected_error_type_counts = {}
        for result in results:
            for error_type in result.detected_error_types:
                detected_error_type_counts[error_type] = detected_error_type_counts.get(error_type, 0) + 1
        
        # Calculate precision and recall for each error type
        error_type_metrics = {}
        for error_type, count in error_type_counts.items():
            true_positives = sum(
                1 for r in results 
                if error_type in r.detected_error_types and 
                any(case.error_type.lower() == error_type 
                    for case in test_cases 
                    if case.test_case_id == r.test_case_id)
            )
            false_positives = sum(
                1 for r in results 
                if error_type in r.detected_error_types and 
                all(case.error_type.lower() != error_type 
                    for case in test_cases 
                    if case.test_case_id == r.test_case_id)
            )
            false_negatives = sum(
                1 for case in test_cases 
                if case.error_type.lower() == error_type and
                all(error_type not in r.detected_error_types 
                    for r in results 
                    if r.test_case_id == case.test_case_id)
            )
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            error_type_metrics[error_type] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': count
            }
        
        # Prepare summary
        summary = {
            'timestamp': timestamp,
            'total_test_cases': total,
            'passed': passed,
            'failed': total - passed,
            'accuracy': accuracy,
            'error_type_metrics': error_type_metrics,
            'results': [r.to_dict() for r in results]
        }
        
        # Save results to file
        if save_results:
            output_file = self.output_dir / f"evaluation_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Evaluation results saved to {output_file}")
        
        return summary

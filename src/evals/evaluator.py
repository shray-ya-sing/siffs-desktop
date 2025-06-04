import aiohttp
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Union
import os
import sys
from pathlib import Path

# Add the python-server directory to Python path
project_root = Path(__file__).parent.parent.absolute()
python_server_dir = project_root / "python-server"
sys.path.append(str(python_server_dir))

# Now import the OpenAIService
from ai_services.openai_service import OpenAIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('Evaluator')

@dataclass
class EvaluationResult:
    """Stores the results of evaluating a single test case."""
    test_case_id: str
    passed: bool
    score: float
    reasoning: str
    criteria_scores: Dict[str, float]
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
            'score': self.score,
            'reasoning': self.reasoning,
            'criteria_scores': self.criteria_scores,
            'detected_error_types': list(self.detected_error_types),
            'detected_cells': list(self.detected_cells),
            'false_positives': list(self.false_positives),
            'false_negatives': list(self.false_negatives),
            'response_text': self.response_text,
            'error': self.error
        }

class ErrorEvaluator:
    """
    Evaluates model's ability to detect and identify errors in Excel metadata.
    """
    
    def __init__(self, 
                output_dir: str = "eval_results",
                api_base_url: str = "http://localhost:3001",
                openai_api_key: Optional[str] = None):
        """
        Initialize the evaluator.
        
        Args:
            output_dir: Directory to store evaluation results
            api_base_url: Base URL of the API server
            openai_api_key: OpenAI API key for evaluation
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.api_base_url = api_base_url
        self.openai_service = OpenAIService(api_key=openai_api_key)
        
    async def _call_analyze_endpoint(self, chunk: str) -> str:
        """Call the analyze-chunks endpoint and collect the full response."""
        url = f"{self.api_base_url}/api/excel/analyze-chunks"
        payload = {
            "chunks": [chunk],
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.2,
            "max_tokens": 8000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise Exception(f"API error: {error}")
                    
                    # Collect all chunks of the response
                    full_response = []
                    async for line in response.content:
                        if line.startswith(b'data: '):
                            data = line[6:].strip()
                            if data == b'[DONE]':
                                break
                            try:
                                json_data = json.loads(data)
                                if 'chunk' in json_data:
                                    full_response.append(json_data['chunk'])
                            except json.JSONDecodeError:
                                continue
                    
                    return ''.join(full_response)
        except Exception as e:
            logger.error(f"Error calling analyze endpoint: {str(e)}")
            raise

    async def _process_chunk(self, chunk_path: Path, ga_path: Path) -> Dict:
        """Process a single chunk and its golden answer."""
        # Create output directories
        llm_response_dir = chunk_path.parent / "llm_response"
        eval_result_dir = chunk_path.parent / "llm_response" / "evaluation_result"
        llm_response_dir.mkdir(exist_ok=True)
        eval_result_dir.mkdir(exist_ok=True)
        
        # Generate output filenames
        chunk_name = chunk_path.stem
        output_file = llm_response_dir / f"{chunk_name}_response.txt"
        eval_file = eval_result_dir / f"{chunk_name}_eval.json"
        
        try:
            # Read the chunk content
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_content = f.read()
            
            # Get LLM response
            llm_response = await self._call_analyze_endpoint(chunk_content)
            
            # Save LLM response
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(llm_response)
            
            # Read golden answer
            with open(ga_path, 'r', encoding='utf-8') as f:
                golden_answer = f.read()
            
            # Evaluate response
            eval_result = await self.openai_service.evaluate_response(
                model_response=llm_response,
                golden_answer=golden_answer
            )
            
            # Save evaluation result
            with open(eval_file, 'w', encoding='utf-8') as f:
                json.dump(eval_result, f, indent=2)
            
            return {
                'chunk': chunk_name,
                'success': True,
                'score': eval_result.get('score', 0.0),
                'eval_file': str(eval_file)
            }
            
        except Exception as e:
            logger.error(f"Error processing {chunk_path}: {str(e)}")
            return {
                'chunk': chunk_name,
                'success': False,
                'error': str(e)
            }

    async def run_evaluation(self, test_cases_dir: str, batch_size: int = 3) -> dict:
        """
        Run evaluation on all test cases in the directory.
        
        Args:
            test_cases_dir: Directory containing test case directories
            batch_size: Number of chunks to process in parallel
            
        Returns:
            Dictionary with evaluation summary
        """
        test_cases_dir = Path(test_cases_dir)
        results = []
        
        # Find all test case directories
        test_case_dirs = [d for d in test_cases_dir.iterdir() if d.is_dir()]
        
        for test_case_dir in test_case_dirs:
            logger.info(f"Processing test case: {test_case_dir.name}")
            
            # Find all chunk files
            chunk_files = list(test_case_dir.glob("chunk_*.md"))
            ga_files = list((test_case_dir / "ga").glob("chunk*_ga.md"))
            
            # Process chunks in batches
            for i in range(0, len(chunk_files), batch_size):
                batch_chunks = chunk_files[i:i + batch_size]
                
                # Process batch in parallel
                batch_tasks = []
                for chunk_file in batch_chunks:
                    chunk_num = chunk_file.stem.split('_')[-1]
                    ga_file = test_case_dir / "ga" / f"chunk{chunk_num}_ga.md"
                    
                    if ga_file.exists():
                        batch_tasks.append(self._process_chunk(chunk_file, ga_file))
                    else:
                        logger.warning(f"Golden answer not found for {chunk_file}")
                
                # Wait for batch to complete
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
                
                # Log progress
                processed = i + len(batch_chunks)
                logger.info(f"Processed {processed}/{len(chunk_files)} chunks in {test_case_dir.name}")
        
        # Generate summary
        successful = sum(1 for r in results if r.get('success', False))
        scores = [r.get('score', 0) for r in results if 'score' in r]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_chunks': len(results),
            'successful': successful,
            'failed': len(results) - successful,
            'average_score': avg_score,
            'results': results
        }
        
        # Save summary
        summary_file = self.output_dir / f"evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Evaluation complete. Results saved to {summary_file}")
        return summary
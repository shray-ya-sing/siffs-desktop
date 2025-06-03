import asyncio
import json
from pathlib import Path
from evaluator import ErrorEvaluator, ErrorCase
from llm_analyzer import LLMAnalyzer  # Your existing analyzer

async def load_test_cases(directory: str = "test_cases") -> list[ErrorCase]:
    cases = []
    for file in Path(directory).glob("*.json"):
        with open(file) as f:
            cases.extend(ErrorCase.from_dict(case) for case in json.load(f))
    return cases

async def main():
    # Initialize components
    evaluator = ErrorEvaluator(output_dir="eval_results")
    llm_analyzer = LLMAnalyzer()  # Your existing analyzer
    
    # Load test cases
    test_cases = await load_test_cases("test_cases")
    print(f"Loaded {len(test_cases)} test cases")
    
    # Run evaluation
    results = await evaluator.run_evaluation(
        test_cases=test_cases,
        llm_analyzer=llm_analyzer,
        batch_size=3  # Adjust based on rate limits
    )
    
    print(f"Evaluation complete. Accuracy: {results['accuracy']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
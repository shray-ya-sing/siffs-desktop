import asyncio
import os
from pathlib import Path
from evaluator import ErrorEvaluator

async def main():
    # Get the base directory (src/evals)
    base_dir = Path(__file__).parent
    test_cases_dir = base_dir / "test_cases" / "data"
    
    # Get OpenAI API key from environment variable
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Initialize the evaluator
    evaluator = ErrorEvaluator(
        output_dir=base_dir / "eval_results",
        api_base_url="http://localhost:3001",  # Update if your API is on a different URL
        openai_api_key=openai_api_key
    )
    
    print(f"Starting evaluation of test cases in: {test_cases_dir}")
    
    # Run evaluation on all test cases
    results = await evaluator.run_evaluation(
        test_cases_dir=str(test_cases_dir),
        batch_size=3  # Adjust based on rate limits
    )
    
    print(f"\nEvaluation complete!")
    print(f"Total chunks processed: {results['total_chunks']}")
    print(f"Successful evaluations: {results['successful']}")
    print(f"Failed evaluations: {results['failed']}")
    print(f"Average score: {results['average_score']:.2f}")
    
    # Save the summary path for reference
    summary_file = Path(evaluator.output_dir) / f"evaluation_summary_*.json"
    print(f"\nDetailed results saved to: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main())
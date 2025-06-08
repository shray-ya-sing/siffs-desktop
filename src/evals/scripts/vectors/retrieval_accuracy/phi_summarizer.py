import json
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Any
from transformers import pipeline
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONSummarizer:
    def __init__(self, model_name="microsoft/Phi-3.5-mini-instruct"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            device=self.device,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True
        )

    def _truncate_json(self, json_data: Dict[str, Any], max_tokens: int = 1500) -> Dict[str, Any]:
        """Truncate JSON to fit within token limits"""
        if not isinstance(json_data, dict):
            return json_data
            
        # Keep only essential fields
        essential_fields = {
            'row', 'column', 'value', 'formula', 
            'dataType', 'formatting', 'directPrecedents', 'directDependents'
        }
        
        truncated = {}
        for key, value in json_data.items():
            if key in essential_fields:
                if isinstance(value, dict):
                    truncated[key] = self._truncate_json(value, max_tokens // 2)
                else:
                    truncated[key] = value
                    
            # Early exit if we've added too much
            if len(str(truncated)) > max_tokens * 4:  # Rough estimate
                break
                
        return truncated

    def generate_summary(self, json_data: dict) -> str:
        """Generate a structured summary of JSON data"""
        system_prompt = """You are a financial analyst creating natural language summaries of financial data. Your task is to transform structured JSON data into clear, flowing paragraphs that read like a professional financial report.

[Previous instructions and guidelines remain the same...]
"""
        # Truncate the JSON data
        truncated_data = self._truncate_json(json_data)
        
        prompt = f"""Generate a structured summary of the following JSON data in markdown format.
Focus on:
1. Data values and their relationships
2. Cell dependencies and references
3. Formatting information
4. Data types and units

Return only the markdown, no additional commentary.

JSON:
{json.dumps(truncated_data, indent=2)}

Summary:
"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Generate the response
            response = self.pipe(
                messages,
                max_new_tokens=1024,
                temperature=0.3,
                do_sample=False,
                eos_token_id=self.pipe.tokenizer.eos_token_id,
                pad_token_id=self.pipe.tokenizer.eos_token_id
            )
            
            # Extract the generated text
            if isinstance(response, list) and len(response) > 0:
                generated_text = response[0].get('generated_text', '')
                # Extract the last message's content
                if isinstance(generated_text, list):
                    if generated_text and isinstance(generated_text[-1], dict):
                        return generated_text[-1].get('content', '').split("Summary:")[-1].strip()
                return str(generated_text).split("Summary:")[-1].strip()
            return "No summary generated"
            
        except Exception as e:
            logger.error(f"Error in generate_summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

def process_json_chunks(input_dir: str, output_dir: str):
    """Process all JSON chunks in the input directory and save summaries to output directory"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize the summarizer
    summarizer = JSONSummarizer()
    
    # Process each JSON file
    json_files = list(input_path.glob("*.json"))
    for json_file in tqdm(json_files, desc="Processing JSON chunks"):
        try:
            output_file = output_path / f"{json_file.stem}_summary.md"
            
            # Skip if output already exists
            if output_file.exists():
                logger.info(f"Skipping {json_file.name} - output already exists")
                continue

            logger.info(f"Processing {json_file.name}...")
            
            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Generate summary
            summary = summarizer.generate_summary(data)
            
            # Save summary to markdown file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"Saved summary to {output_file}")
                
        except Exception as e:
            logger.error(f"Error processing {json_file.name}: {str(e)}")

if __name__ == "__main__":
    # Configuration
    input_directory = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\json\chunks"
    output_directory = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\generated_summaries"
    
    # Process all JSON chunks
    process_json_chunks(input_directory, output_directory)
    logger.info(f"Summaries saved to: {output_directory}")
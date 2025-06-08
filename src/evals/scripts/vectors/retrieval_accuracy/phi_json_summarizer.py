import json
import os
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from tqdm import tqdm
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#microsoft/Phi-3-mini-4k-instruct
class JSONSummarizer:
    def __init__(self, model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto"
        )
        self.model.eval()


    def _truncate_json(self, json_data: Dict[str, Any], max_tokens: int = 1500) -> Dict[str, Any]:
        """Truncate JSON to fit within token limits"""
        if not isinstance(json_data, dict):
            return json_data
            
        # Keep only essential fields - adjust based on your JSON structure
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
            if len(self.tokenizer.encode(str(truncated))) > max_tokens:
                break
                
        return truncated
        
    def generate_summary(self, json_data: dict) -> str:
        """Generate a structured summary of JSON data"""
        system_prompt = """You are a financial analyst creating natural language summaries of financial data. Your task is to transform structured JSON data into clear, flowing paragraphs that read like a professional financial report.

# INSTRUCTIONS
1. Write in complete, well-structured paragraphs
2. Use natural transitions between ideas
3. Present numbers in a readable format
4. Group related information together logically
5. Maintain a professional but conversational tone

# FORMATTING GUIDELINES
- Use markdown for basic formatting (bold, italics, lists)
- Organize content with clear section headers (##, ###)
- Use bullet points only for distinct items or categories
- Include all important values directly in the text
- Keep paragraphs focused and concise

# CONTENT FOCUS
- Describe trends and changes naturally
- Explain relationships between data points
- Note important values and their context
- Include relevant time periods
- Highlight any significant patterns

# STYLE GUIDELINES
- Write in the present tense
- Use active voice
- Be precise with numbers and calculations
- Avoid financial jargon when possible
- Maintain consistency in terminology

Example structure:
## [Section Name]
[Natural paragraph describing the data, including key values and changes. For example: "Revenue for Q1 2023 was $1.2 million, showing a 5% increase from the previous quarter. This growth was driven by..."]

## [Next Section]
[Continue with natural language description...]

Remember: The goal is to make the data easily understandable at a glance while maintaining a natural, flowing narrative.
"""

        prompt = f"""Generate a structured summary of the following JSON data in markdown format.
Focus on:
1. Data values and their relationships
2. Cell dependencies and references
3. Formatting information
4. Data types and units

Return only the markdown, no additional commentary.

JSON:
{json.dumps(self._truncate_json(json_data), indent=2)}

Summary:
"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            inputs = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    temperature=0.3,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return summary.split("Summary:")[-1].strip()
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
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
            print(f"Error processing {json_file.name}: {str(e)}")

if __name__ == "__main__":
    # Configuration
    input_directory = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\json\chunks"
    output_directory = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\generated_summaries"
    
    # Process all JSON chunks
    process_json_chunks(input_directory, output_directory)
    print(f"Summaries saved to: {output_directory}")
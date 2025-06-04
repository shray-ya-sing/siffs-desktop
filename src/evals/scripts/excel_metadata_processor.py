# C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\excel_metadata_processor.py
import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ExcelMetadataProcessor:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_output_dir(self, file_path: str, timestamp: str) -> Path:
        """Create and return the output directory path"""
        file_stem = Path(file_path).stem
        output_dir = (
            Path(__file__).parent.parent / 
            "test_cases" / 
            "data" / 
            f"{file_stem}_{timestamp}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to make HTTP requests"""
        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug(f"Making request to {url}")
            async with self.session.post(url, json=payload) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Request to {url} failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_text = await e.response.text()
                    logger.error(f"Response error: {error_text}")
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Unexpected error in _make_request: {str(e)}")
            raise

    async def process_excel_file(self, file_path: str, max_tokens: int = 18000) -> Dict[str, Any]:
        """
        Process an Excel file using the legacy endpoint and save the results.
        
        Args:
            file_path: Path to the Excel file
            max_tokens: Maximum tokens per chunk (default: 18000 for Sonnet)
            
        Returns:
            Dictionary containing all processing results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = Path(file_path).stem
        output_dir = self._get_output_dir(file_path, timestamp)
        
        results = {
            "file_path": str(file_path),
            "file_name": file_name,
            "timestamp": timestamp,
            "output_dir": str(output_dir),
            "output_files": []
        }

        try:
            # Single call to the legacy endpoint
            logger.info(f"Processing file: {file_path}")
            response = await self._make_request(
                "/api/excel/extract-metadata-legacy",
                {"filePath": file_path}
            )

            # Save the complete response
            response_file = output_dir / f"complete_response.json"
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, indent=2)
            results["output_files"].append(str(response_file))
            logger.info(f"Saved complete response to {response_file}")

            # Save markdown if available
            markdown = response.get("markdown", "")
            if markdown:
                markdown_file = output_dir / "markdown.md"
                with open(markdown_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                results["output_files"].append(str(markdown_file))
                logger.info(f"Saved markdown to {markdown_file}")

            # Save chunks
            chunks = response.get("chunks", [])
            chunk_info = response.get("chunk_info", [])
            
            for i, chunk in enumerate(chunks):
                chunk_file = output_dir / f"chunk_{i+1}.md"
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                results["output_files"].append(str(chunk_file))
            
            logger.info(f"Saved {len(chunks)} chunks to {output_dir}")

            # Save summary
            summary = {
                "file_path": str(file_path),
                "file_name": file_name,
                "timestamp": timestamp,
                "num_chunks": len(chunks),
                "chunk_info": chunk_info,
                "output_dir": str(output_dir),
                "output_files": [str(f.relative_to(output_dir)) for f in map(Path, results["output_files"])]
            }
            
            summary_file = output_dir / "summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            results["output_files"].append(str(summary_file))
            
            logger.info(f"Processing complete. Summary saved to {summary_file}")
            return summary

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            error_file = output_dir / "error.txt"
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error processing {file_path}:\n{str(e)}")
            results["error"] = str(e)
            results["output_files"].append(str(error_file))
            return results

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Excel file through metadata extraction pipeline")
    parser.add_argument("file_path", help="Path to the Excel file to process")
    parser.add_argument("--max-tokens", type=int, default=18000, 
                       help="Maximum tokens per chunk (default: 18000 for Sonnet)")
    parser.add_argument("--port", type=int, default=3001, 
                       help="Port number of the API server (default: 3001)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        async with ExcelMetadataProcessor(base_url=f"http://localhost:{args.port}") as processor:
            results = await processor.process_excel_file(
                file_path=args.file_path,
                max_tokens=args.max_tokens
            )
            
            # Print summary
            print("\n" + "="*50)
            print("Processing Summary")
            print("="*50)
            print(f"File: {results['file_path']}")
            print(f"Output directory: {results['output_dir']}")
            print(f"Status: {'Success' if 'error' not in results else 'Failed'}")
            
            if 'error' in results:
                print(f"Error: {results['error']}")
            
            print(f"\nOutput files:")
            for file_path in results.get('output_files', []):
                print(f"- {file_path}")
            
            if 'num_chunks' in results:
                print(f"\nChunks created: {results['num_chunks']}")
                print(f"Chunk info saved to summary file")
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
import os
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import sys


import time
# Path resolution
current_file = Path(__file__).resolve()  # Get absolute path of current file
# Go up to src directory (assuming the file is in src/evals/scripts/...)
src_path = current_file.parent.parent.parent.parent.parent.absolute()
python_server_path = src_path / "python-server"

# Add to Python path if not already there
if str(python_server_path) not in sys.path:
    sys.path.insert(0, str(python_server_path))
    print(f"Added to path: {python_server_path}")

# Now import the RAG components
from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.store.embedding_storage import EmbeddingStorage
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChunkLoader:
    @staticmethod
    def load_chunks_from_dir(directory: str, extension: str = '.txt', prefix: str = 'chunk_') -> List[Dict]:
        """Load chunks from a directory with given file extension and prefix."""
        import sentence_transformers
        import faiss
        chunks = []
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        for file_path in sorted(path.glob(f"{prefix}*{extension}")):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                chunks.append({
                    'text': content,
                    'metadata': {
                        'source': str(file_path),
                        'chunk_id': file_path.stem
                    },
                    'markdown': content
                })
        return chunks

    @staticmethod
    def load_json_chunks(file_path: str) -> List[Dict]:
        """Load chunks from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
            return data

class RetrievalTester:
    def __init__(self, data_dir: str, test_query: str, model_name: str = 'BAAI/bge-m3'):
        self.data_dir = Path(data_dir)
        self.test_query = test_query
        self.embedding_model = model_name
        self.results = []
        
        # Define scenarios with their respective directories and loaders
        self.scenarios = {
            'natural_verbose': {
                'dir': self.data_dir / 'natural_verbose',
                'extension': '_natural.txt',
                'prefix': 'chunk_'
            },
            'natural_summary': {
                'dir': self.data_dir / 'natural_summary',
                'extension': '.txt',
                'prefix': 'chunk_'
            },
            'markdown': {
                'dir': self.data_dir / 'markdown',
                'extension': '_markdown.md',
                'prefix': 'chunk_'
            },
            'clean_natural': {
                'dir': self.data_dir / 'clean_natural',
                'extension': '.txt',
                'prefix': 'chunk_'
            },
            'expanded_clean_natural': {
                'dir': self.data_dir / 'expanded_clean_natural',
                'extension': '.txt',
                'prefix': 'chunk_'
            },
        }
        
        # Initialize embedder with the specified model
        self.embedder = ChunkEmbedder(model_name=model_name)

        
    def _load_scenario_chunks(self, scenario_name: str, scenario_config: dict) -> List[Dict]:
        """Load chunks for a specific scenario."""
        try:
            if scenario_config.get('loader') == 'json':
                chunks = ChunkLoader.load_json_chunks(scenario_config['file'])
            else:
                chunks = ChunkLoader.load_chunks_from_dir(
                    directory=scenario_config['dir'],
                    extension=scenario_config['extension'],
                    prefix=scenario_config['prefix']
                )
            logger.info(f"Loaded {len(chunks)} chunks for scenario: {scenario_name}")
            return chunks
        except Exception as e:
            logger.error(f"Error loading chunks for {scenario_name}: {str(e)}")
            return []

    def run_tests(self, top_k: int = 5):
        """Run retrieval tests for all scenarios"""
        for scenario_name, scenario_config in self.scenarios.items():
            logger.info(f"\n{'='*50}\nTesting scenario: {scenario_name}\n{'='*50}")
            
            # Load chunks for this scenario
            chunks = self._load_scenario_chunks(scenario_name, scenario_config)
            if not chunks:
                logger.warning(f"No chunks loaded for scenario: {scenario_name}. Skipping...")
                continue
            
            # Create a unique database path for this scenario
            scenario_db = f"./test_{scenario_name}.db"
            if os.path.exists(scenario_db):
                os.remove(scenario_db)
            
            storage = EmbeddingStorage(scenario_db)
            
            try:
                logger.info(f"Starting to embed {len(chunks)} chunks...")
                start_time = time.time()
                # Generate embeddings for the chunks
                embeddings, processed_chunks = self.embedder.embed_chunks(chunks, batch_size=8)
                logger.info(f"Embedding completed in {time.time() - start_time:.2f} seconds")
                
                # Create a unique workbook path for this scenario
                workbook_path = str(Path(self.data_dir) / scenario_name)
                
                # Store embeddings with unique workbook path
                storage.add_workbook_embeddings(
                    workbook_path=workbook_path,
                    embeddings=embeddings,
                    chunks=chunks,
                    embedding_model=self.embedding_model,
                    create_new_version=True
                )
                
                # Initialize retriever and build index
                retriever = FAISSChunkRetriever(storage, self.embedder)
                retriever.build_index_for_workbook(workbook_path)
                
                # Run the query
                results = retriever.search(
                    query=self.test_query,
                    workbook_path=workbook_path,
                    top_k=min(top_k, len(chunks)),
                    return_format='text'
                )
                
                # Store results
                self.results.append({
                    'scenario': scenario_name,
                    'results': results,
                    'top_score': results[0]['score'] if results else 0,
                    'avg_score': np.mean([r['score'] for r in results]) if results else 0,
                    'num_chunks': len(chunks)
                })
                
            except Exception as e:
                logger.error(f"Error processing scenario {scenario_name}: {str(e)}", exc_info=True)
            finally:
                storage.close()
            
    def analyze_results(self):
        """Analyze and display test results, saving to a file"""
        if not self.results:
            logger.warning("No results to analyze. Run tests first.")
            return
        
        # Create results directory if it doesn't exist
        results_dir = Path(r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a timestamped filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"retrieval_results_{timestamp}.txt"

        # Get model information
        model_info = self.embedder.get_model_info()
        
        # Prepare summary data
        summary_data = []
        for result in sorted(self.results, key=lambda x: x['avg_score'], reverse=True):
            summary_data.append({
                'Scenario': result['scenario'],
                'Top Score': f"{result['top_score']:.4f}",
                'Avg Score': f"{result['avg_score']:.4f}",
                'Num Results': len(result['results']),
                'Num Chunks': result['num_chunks']
            })
        
        # Convert to DataFrame for nice formatting
        df_summary = pd.DataFrame(summary_data)
        
        # Build the output string
        output = []
        output.append("=" * 80)
        output.append("RETRIEVAL ACCURACY TEST RESULTS")
        output.append("=" * 80)

        # Add model information
        output.append("\n" + "-" * 80)
        output.append("MODEL INFORMATION")
        output.append("-" * 80)
        output.append(f"Model Name: {model_info['model_name']}")
        output.append(f"Embedding Dimension: {model_info['embedding_dimension']}")
        output.append(f"Max Sequence Length: {model_info['max_seq_length']}")
        output.append(f"Device: {model_info['device']}")
        output.append(f"Similarity Function: {model_info.get('similarity_function', 'N/A')}")
        
        output.append("\n" + "-" * 80)
        output.append("SUMMARY")
        output.append("-" * 80)
        output.append(df_summary.to_string(index=False))
        
        # Add detailed results for each scenario
        for result in sorted(self.results, key=lambda x: x['avg_score'], reverse=True):
            output.append("\n" + "-" * 80)
            output.append(f"SCENARIO: {result['scenario'].upper()}")
            output.append("-" * 80)
            output.append(f"Top Score: {result['top_score']:.4f}, Avg Score: {result['avg_score']:.4f}")
            output.append(f"Number of Results: {len(result['results'])}, Total Chunks: {result['num_chunks']}")
            
            # Add top 3 results
            output.append("\nTOP RESULTS:")
            for i, res in enumerate(result['results'][:3], 1):
                output.append(f"\n--- Result {i} (Score: {res['score']:.4f}) ---")
                text = res.get('text', res.get('markdown', 'No content'))
                output.append(text[:1000])  # Limit to first 1000 chars
                if len(text) > 1000:
                    output.append("\n[...truncated]")
        
        # Add query information
        output.append("\n" + "-" * 80)
        output.append("QUERY")
        output.append("-" * 80)
        output.append(self.test_query)
        
        # Join all lines and write to file
        final_output = "\n".join(output)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
            
        # Also print summary to console
        print("\n" + "="*80)
        print(f"Results saved to: {output_file}")
        print("MODEL USED:", model_info['model_name'])
        print("="*80)
        print(df_summary.to_string(index=False))

def main():
    # Configuration
    data_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1"
    test_query = "What is the total revenue in the quarter ending 31st March 2013?"
    
    # Initialize and run tests
    # Testing with 'all-MiniLM-L6-v2', 'msmarco-MiniLM-L-6-v3', all-MiniLM-L12-v2, paraphrase-MiniLM-L3-v2, multi-qa-MiniLM-L6-cos-v1, multi-qa-mpnet-base-dot-v1, sentence-t5-base, 
    # intfloat/e5-large-v2, BAAI/bge-base-en-v1.5, sentence-transformers/all-mpnet-base-v2, jinaai/jina-embeddings-v2-base-en
    tester = RetrievalTester(data_dir, test_query, model_name='sentence-t5-base')
    tester.run_tests(top_k=3)
    tester.analyze_results()

if __name__ == "__main__":
    main()
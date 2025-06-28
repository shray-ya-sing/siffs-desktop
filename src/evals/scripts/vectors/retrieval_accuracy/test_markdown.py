import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
import sys

import time
from datetime import datetime
import logging

# Path resolution
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent.parent.parent.parent.absolute()
python_server_path = src_path / "python-server"

# Add to Python path if not already there
if str(python_server_path) not in sys.path:
    sys.path.insert(0, str(python_server_path))

# Import the RAG components
from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.store.embedding_storage import EmbeddingStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChunkLoader:
    @staticmethod
    def load_chunks_from_dir(directory: str, extension: str = '.md', prefix: str = 'chunk_') -> list[dict]:
        """Load chunks from markdown files in a directory."""
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

class ModelTester:
    def __init__(self, data_dir: str, test_query: str):
        self.data_dir = Path(data_dir)
        self.test_query = test_query
        self.models = [
            'all-MiniLM-L6-v2',
            'msmarco-MiniLM-L-6-v3',
            'all-MiniLM-L12-v2',
            'paraphrase-MiniLM-L3-v2',
            'multi-qa-MiniLM-L6-cos-v1',
            'multi-qa-mpnet-base-dot-v1',
            'sentence-t5-base',
            'intfloat/e5-large-v2',
            'BAAI/bge-base-en-v1.5',
        ]
        self.large_models = [
            'intfloat/e5-large-v2',
            'BAAI/bge-base-en-v1.5',
            'sentence-transformers/all-mpnet-base-v2',
            'jinaai/jina-embeddings-v2-base-en'
        ]
        self.results = []
        
    def _contains_row_12(self, chunk_text: str) -> bool:
        """Check if the chunk contains row 12 data."""
        # Look for patterns like "Row: 12" or "Row | 12" in the markdown
        try:                
            if "Rows: 11-20" in chunk_text:
                return True
            if "Row: 12" in chunk_text:
                return True
            if "Row | 12" in chunk_text:
                return True
            if "| 12 |" in chunk_text:
                return True
            return False
        except Exception as e:
            print(f"Error checking for row 12: {e}")
            return False
    
    def _calculate_score(self, results: list[dict]) -> float:
        """Calculate accuracy score based on position of correct chunk."""
        try:
            for i, result in enumerate(results[:3], 1):  # Check top 3 results
                if self._contains_row_12(result['text']):
                    return 1.0 if i == 1 else 0.5
            return 0.0
        except Exception as e:
            print(f"Error calculating score: {e}")
            return 0.0

    def test_model(self, model_name: str) -> dict:
        """Test a single model and return results."""
        logger.info(f"\n{'='*50}\nTesting model: {model_name}\n{'='*50}")
        
        # Initialize embedder
        embedder = ChunkEmbedder(model_name=model_name)
        
        # Load markdown chunks
        chunks_dir = self.data_dir / 'markdown'
        chunks = ChunkLoader.load_chunks_from_dir(chunks_dir)
        
        if not chunks:
            logger.warning("No chunks loaded. Exiting test.")
            return {'model': model_name, 'score': 0.0, 'error': 'No chunks loaded'}
        
        # Setup storage
        db_path= r'C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\db'
        db_name = f"test_{model_name.replace('/', '_')}.db"
        if os.path.exists(db_name):
            os.remove(db_name)
        
        storage = EmbeddingStorage(db_path=db_path, db_name=db_name)
        
        try:
            # Generate and store embeddings
            logger.info(f"Generating embeddings using {model_name}...")
            start_time = time.time()
            embeddings, _ = embedder.embed_chunks(chunks, batch_size=8)
            logger.info(f"Embedding completed in {time.time() - start_time:.2f} seconds")
            
            workbook_path = str(self.data_dir / f'markdown_{model_name}')
            storage.add_workbook_embeddings(
                workbook_path=workbook_path,
                embeddings=embeddings,
                chunks=chunks,
                embedding_model=model_name,
                create_new_version=True
            )
            
            # Build index and search
            index_path = r'C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\index\faiss_indices'
            retriever = FAISSChunkRetriever(storage, embedder, index_path=index_path)
            retriever.build_index_for_workbook(workbook_path)
            
            results = retriever.search(
                query=self.test_query,
                workbook_path=workbook_path,
                top_k=3,  # We only need top 3 for scoring
                return_format='text'
            )
            
            # Calculate score
            score = self._calculate_score(results)
            
            logger.info(f"Model: {model_name} - Score: {score}")
            return {
                'model': model_name,
                'score': score,
                'top_result': results[0]['text'][:200] + '...' if results else 'No results'
            }
            
        except Exception as e:
            logger.error(f"Error testing model {model_name}: {str(e)}", exc_info=True)
            return {'model': model_name, 'score': 0.0, 'error': str(e)}
        finally:
            storage.close()
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except:
                pass

    def run_tests(self):
        """Run tests for all models."""
        for model_name in self.models:
            result = self.test_model(model_name)
            self.results.append(result)
            
    def save_results(self):
        """Save results to a CSV file."""
        results_dir = self.data_dir / 'result_markdown'
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"model_comparison_{timestamp}.csv"
        
        # Convert results to DataFrame
        df = pd.DataFrame(self.results)
        df = df.sort_values('score', ascending=False)
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Results saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("MODEL COMPARISON RESULTS")
        print("="*80)
        print(df[['model', 'score']].to_string(index=False))
        print("\nTop performing model:", df.iloc[0]['model'], f"(Score: {df.iloc[0]['score']})")

def main():
    # Configuration
    data_dir = Path(r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1")
    test_query = "What is the total revenue in the quarter ending 31st March 2013?"
    
    # Initialize and run tests
    tester = ModelTester(data_dir, test_query)
    tester.run_tests()
    tester.save_results()

if __name__ == "__main__":
    main()
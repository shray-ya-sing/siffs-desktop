import os
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path
import sys
import time
from datetime import datetime
import logging

# Path resolution
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent.parent.parent.parent.parent.parent.parent.absolute()
python_server_path = src_path / "python-server"

if str(python_server_path) not in sys.path:
    sys.path.insert(0, str(python_server_path))
    print(f"Added to path: {python_server_path}")

from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.store.embedding_storage import EmbeddingStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarcosRetrievalEvaluator:
    def __init__(self, chunks_dir: str, qa_pairs_base_dir: str, model_name: str = 'msmarco-MiniLM-L-6-v3'):
        self.chunks_dir = Path(chunks_dir)
        self.qa_pairs_base_dir = Path(qa_pairs_base_dir)
        self.model_name = model_name
        self.embedder = ChunkEmbedder(model_name=model_name)
        self.results_dir = Path(r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Define QA pairs file paths
        self.qa_files = {
            'multi_cell_answer': {
                'multi_chunk': self.qa_pairs_base_dir / "multi_cell_answer" / "multi_chunk" / "chunk_000_001_002.json",
                'single_chunk': [
                    self.qa_pairs_base_dir / "multi_cell_answer" / "single_chunk" / "chunk_000_qa.json",
                    self.qa_pairs_base_dir / "multi_cell_answer" / "single_chunk" / "chunk_006_qa.json",
                    self.qa_pairs_base_dir / "multi_cell_answer" / "single_chunk" / "chunk_007_qa.json"
                ]
            },
            'single_cell_answer': {
                'multi_chunk': self.qa_pairs_base_dir / "single_cell_answer" / "multi_chunk" / "chunk_000_001_002.json",
                'single_chunk': [
                    self.qa_pairs_base_dir / "single_cell_answer" / "scoped_chunk" / "chunk_000_qa.json",
                    self.qa_pairs_base_dir / "single_cell_answer" / "scoped_chunk" / "chunk_001_qa.json",
                    self.qa_pairs_base_dir / "single_cell_answer" / "scoped_chunk" / "chunk_002_qa.json",
                    self.qa_pairs_base_dir / "single_cell_answer" / "scoped_chunk" / "chunk_004_qa.json",
                    self.qa_pairs_base_dir / "single_cell_answer" / "scoped_chunk" / "chunk_005_qa.json"
                ]
            }
        }
        
        self.test_results = []
        self.detailed_results = {}

    def load_chunks(self) -> List[Dict]:
        """Load all chunks from the chunks directory"""
        chunks = []
        chunk_files = sorted(self.chunks_dir.glob("chunk_*.md"))
        
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                chunks.append({
                    'text': content,
                    'metadata': {
                        'source': str(chunk_file),
                        'chunk_id': chunk_file.stem
                    },
                    'markdown': content
                })
        
        logger.info(f"Loaded {len(chunks)} chunks from {self.chunks_dir}")
        return chunks

    def load_qa_pairs(self, qa_file: Path) -> List[Dict]:
        """Load QA pairs from a JSON file"""
        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                qa_pairs = json.load(f)
                if not isinstance(qa_pairs, list):
                    qa_pairs = [qa_pairs]
                logger.info(f"Loaded {len(qa_pairs)} QA pairs from {qa_file}")
                return qa_pairs
        except Exception as e:
            logger.error(f"Error loading QA pairs from {qa_file}: {str(e)}")
            return []

    def check_answer_in_chunk(self, chunk_text: str, golden_answer: Union[Dict, List[Dict]]) -> bool:
        """Check if the golden answer(s) are present in the chunk text"""
        if isinstance(golden_answer, dict):
            # Single cell answer
            cell_address = golden_answer['cell_address']
            value = str(golden_answer['value'])
            
            # Check if both cell address and value are in the chunk
            # Look for patterns like "C8, v=5601" or similar
            if cell_address in chunk_text and f"v={value}" in chunk_text:
                # Verify they're from the same cell by checking proximity
                cell_pattern = f"{cell_address}, v={value}"
                return cell_pattern in chunk_text
            return False
            
        else:
            # Multi cell answer - need to find ALL answers
            all_found = True
            for answer in golden_answer:
                if not self.check_answer_in_chunk(chunk_text, answer):
                    all_found = False
                    break
            return all_found

    def evaluate_single_chunk_scenario(self, qa_pair: Dict, retrieved_chunks: List[Dict]) -> Tuple[float, Dict]:
        """Evaluate a single chunk scenario"""
        golden_answer = qa_pair['golden_answer']
        
        # Check top chunk
        if retrieved_chunks:
            top_chunk = retrieved_chunks[0]
            if self.check_answer_in_chunk(top_chunk['text'], golden_answer):
                return 1.0, {'location': 'top_chunk', 'chunk_id': top_chunk['metadata']['chunk_id']}
        
        # Check if any of top 3 chunks contain answer
        for i, chunk in enumerate(retrieved_chunks[:3]):
            if self.check_answer_in_chunk(chunk['text'], golden_answer):
                return 0.5, {'location': f'chunk_{i+1}', 'chunk_id': chunk['metadata']['chunk_id']}
        
        return 0.0, {'location': 'not_found'}

    def evaluate_multi_chunk_scenario(self, qa_pair: Dict, retrieved_chunks: List[Dict]) -> Tuple[float, Dict]:
        """Evaluate a multi chunk scenario"""
        golden_answer = qa_pair['golden_answer']
        
        # Compose all chunks into one string
        composed_text = "\n".join([chunk['text'] for chunk in retrieved_chunks[:3]])
        
        if self.check_answer_in_chunk(composed_text, golden_answer):
            return 1.0, {
                'location': 'composed_chunks',
                'chunk_ids': [chunk['metadata']['chunk_id'] for chunk in retrieved_chunks[:3]]
            }
        
        return 0.0, {'location': 'not_found'}

    def run_evaluation(self):
        """Run the complete evaluation"""
        # Load chunks
        chunks = self.load_chunks()
        if not chunks:
            logger.error("No chunks loaded. Exiting.")
            return
        
        # Setup database
        db_path = "./marcos_eval.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        
        storage = EmbeddingStorage(db_path)
        
        try:
            # Generate embeddings
            logger.info("Generating embeddings for chunks...")
            start_time = time.time()
            embeddings, _ = self.embedder.embed_chunks(chunks, batch_size=8)
            logger.info(f"Embedding completed in {time.time() - start_time:.2f} seconds")
            
            # Store embeddings
            workbook_path = "marcos_eval_workbook"
            storage.add_workbook_embeddings(
                workbook_path=workbook_path,
                embeddings=embeddings,
                chunks=chunks,
                embedding_model=self.model_name,
                create_new_version=True
            )
            
            # Initialize retriever
            retriever = FAISSChunkRetriever(storage, self.embedder)
            retriever.build_index_for_workbook(workbook_path)
            
            # Process each category
            for answer_type, scenarios in self.qa_files.items():
                self.detailed_results[answer_type] = {}
                
                for scenario_type, qa_files in scenarios.items():
                    self.detailed_results[answer_type][scenario_type] = []
                    
                    # Handle both single file and list of files
                    if isinstance(qa_files, list):
                        files_to_process = qa_files
                    else:
                        files_to_process = [qa_files]
                    
                    for qa_file in files_to_process:
                        qa_pairs = self.load_qa_pairs(qa_file)
                        
                        for qa_pair in qa_pairs:
                            query = qa_pair['query']
                            
                            # Retrieve chunks
                            retrieved_chunks = retriever.search(
                                query=query,
                                workbook_path=workbook_path,
                                top_k=3,
                                return_format='text'
                            )
                            
                            # Evaluate based on scenario type
                            if scenario_type == 'single_chunk':
                                score, details = self.evaluate_single_chunk_scenario(qa_pair, retrieved_chunks)
                            else:  # multi_chunk
                                score, details = self.evaluate_multi_chunk_scenario(qa_pair, retrieved_chunks)
                            
                            # Store result
                            result = {
                                'query': query,
                                'golden_answer': qa_pair['golden_answer'],
                                'score': score,
                                'details': details,
                                'retrieved_chunks': [
                                    {
                                        'chunk_id': chunk['metadata']['chunk_id'],
                                        'score': chunk['score'],
                                        'text_preview': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text']
                                    }
                                    for chunk in retrieved_chunks
                                ],
                                'qa_file': str(qa_file),
                                'answer_type': answer_type,
                                'scenario_type': scenario_type
                            }
                            
                            self.test_results.append(result)
                            self.detailed_results[answer_type][scenario_type].append(result)
                            
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}", exc_info=True)
        finally:
            storage.close()

    def generate_report(self):
        """Generate comprehensive evaluation report"""
        if not self.test_results:
            logger.warning("No results to report.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results as JSON
        detailed_results_file = self.results_dir / f"detailed_results_{timestamp}.json"
        with open(detailed_results_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        # Generate summary report
        summary_file = self.results_dir / f"summary_report_{timestamp}.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write("MARCOS MINI MODEL RETRIEVAL EVALUATION REPORT\n")
            f.write("="*100 + "\n\n")
            
            # Model information
            model_info = self.embedder.get_model_info()
            f.write("MODEL INFORMATION\n")
            f.write("-"*50 + "\n")
            f.write(f"Model Name: {model_info['model_name']}\n")
            f.write(f"Embedding Dimension: {model_info['embedding_dimension']}\n")
            f.write(f"Max Sequence Length: {model_info['max_seq_length']}\n")
            f.write(f"Device: {model_info['device']}\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS\n")
            f.write("-"*50 + "\n")
            f.write(f"Total test cases: {len(self.test_results)}\n")
            
            # Calculate scores by category
            category_scores = {}
            for result in self.test_results:
                key = f"{result['answer_type']}_{result['scenario_type']}"
                if key not in category_scores:
                    category_scores[key] = []
                category_scores[key].append(result['score'])
            
            # Overall score
            all_scores = [r['score'] for r in self.test_results]
            f.write(f"Overall average score: {np.mean(all_scores):.3f}\n\n")
            
            # Scores by category
            f.write("SCORES BY CATEGORY\n")
            f.write("-"*50 + "\n")
            
            category_summary = []
            for category, scores in sorted(category_scores.items()):
                avg_score = np.mean(scores)
                category_summary.append({
                    'Category': category,
                    'Count': len(scores),
                    'Average Score': f"{avg_score:.3f}",
                    'Perfect (1.0)': sum(1 for s in scores if s == 1.0),
                    'Partial (0.5)': sum(1 for s in scores if s == 0.5),
                    'Failed (0.0)': sum(1 for s in scores if s == 0.0)
                })
            
            df_category = pd.DataFrame(category_summary)
            f.write(df_category.to_string(index=False) + "\n\n")
            
            # Detailed results by category
            f.write("="*100 + "\n")
            f.write("DETAILED RESULTS BY CATEGORY\n")
            f.write("="*100 + "\n\n")
            
            for answer_type, scenarios in self.detailed_results.items():
                for scenario_type, results in scenarios.items():
                    f.write(f"\n{answer_type.upper()} - {scenario_type.upper()}\n")
                    f.write("-"*80 + "\n")
                    
                    for i, result in enumerate(results, 1):
                        f.write(f"\nTest Case {i}:\n")
                        f.write(f"Query: {result['query']}\n")
                        f.write(f"Score: {result['score']}\n")
                        f.write(f"Location: {result['details'].get('location', 'N/A')}\n")
                        
                        # Show golden answer
                        f.write("Golden Answer: ")
                        if isinstance(result['golden_answer'], dict):
                            f.write(f"{result['golden_answer']['cell_address']}: {result['golden_answer']['value']}\n")
                        else:
                            f.write("\n")
                            for ans in result['golden_answer']:
                                f.write(f"  - {ans['cell_address']}: {ans['value']}\n")
                        
                        # Show retrieved chunks summary
                        f.write("Retrieved Chunks:\n")
                        for j, chunk in enumerate(result['retrieved_chunks'], 1):
                            f.write(f"  {j}. {chunk['chunk_id']} (score: {chunk['score']:.4f})\n")
                        
                        f.write("-"*40 + "\n")
            
            # Failed cases analysis
            f.write("\n" + "="*100 + "\n")
            f.write("FAILED CASES ANALYSIS\n")
            f.write("="*100 + "\n\n")
            
            failed_cases = [r for r in self.test_results if r['score'] == 0.0]
            if failed_cases:
                f.write(f"Total failed cases: {len(failed_cases)}\n\n")
                for i, result in enumerate(failed_cases[:10], 1):  # Show first 10
                    f.write(f"Failed Case {i}:\n")
                    f.write(f"Query: {result['query']}\n")
                    f.write(f"Category: {result['answer_type']} - {result['scenario_type']}\n")
                    f.write(f"Expected chunk(s) containing answer not retrieved\n")
                    f.write("-"*40 + "\n")
            else:
                f.write("No failed cases!\n")
        
        # Print summary to console
        print("\n" + "="*80)
        print("EVALUATION COMPLETE")
        print("="*80)
        print(f"Results saved to: {self.results_dir}")
        print(f"- Detailed results: {detailed_results_file}")
        print(f"- Summary report: {summary_file}")
        print("\nSUMMARY:")
        print(df_category.to_string(index=False))
        print(f"\nOverall average score: {np.mean(all_scores):.3f}")

def main():
    # Configuration
    chunks_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\data\markdown"
    qa_pairs_base_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location"
    
    # Initialize evaluator
    evaluator = MarcosRetrievalEvaluator(
        chunks_dir=chunks_dir,
        qa_pairs_base_dir=qa_pairs_base_dir,
        model_name='msmarco-MiniLM-L-6-v3'
    )
    
    # Run evaluation
    logger.info("Starting evaluation...")
    evaluator.run_evaluation()
    
    # Generate report
    logger.info("Generating report...")
    evaluator.generate_report()

if __name__ == "__main__":
    main()
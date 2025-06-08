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

class MultiModelRetrievalEvaluator:
    def __init__(self, chunks_dir: str, qa_pairs_base_dir: str, models: List[str]):
        self.chunks_dir = Path(chunks_dir)
        self.qa_pairs_base_dir = Path(qa_pairs_base_dir)
        self.models = models
        self.results_dir = Path(r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Store results for all models
        self.all_model_results = {}
        
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

    def run_evaluation_for_model(self, model_name: str) -> Dict:
        """Run evaluation for a single model"""
        logger.info(f"\n{'='*80}\nEvaluating model: {model_name}\n{'='*80}")
        
        test_results = []
        detailed_results = {}
        
        # Load chunks
        chunks = self.load_chunks()
        if not chunks:
            logger.error(f"No chunks loaded for model {model_name}. Skipping.")
            return {}
        
        # Setup database for this model
        db_path = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\db"
        db_name = f"eval_{model_name.replace('/', '_')}.db"
        
        storage = EmbeddingStorage(db_path = db_path, db_name = db_name)
        
        try:
            # Initialize embedder for this model
            embedder = ChunkEmbedder(model_name=model_name)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {model_name}...")
            start_time = time.time()
            embeddings, _ = embedder.embed_chunks(chunks, batch_size=8)
            embedding_time = time.time() - start_time
            logger.info(f"Embedding completed in {embedding_time:.2f} seconds")
            
            # Store embeddings
            workbook_path = f"eval_workbook_{model_name.replace('/', '_')}"
            storage.add_workbook_embeddings(
                workbook_path=workbook_path,
                embeddings=embeddings,
                chunks=chunks,
                embedding_model=model_name,
                replace_existing=True
            )
            
            # Initialize retriever
            index_base_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\index"
            index_name = f"faiss_indices"
            index_path = os.path.join(index_base_dir, index_name)
            retriever = FAISSChunkRetriever(storage, embedder, index_path=index_path)
            retriever.build_index_for_workbook(workbook_path)
            
            # Process each category
            for answer_type, scenarios in self.qa_files.items():
                detailed_results[answer_type] = {}
                
                for scenario_type, qa_files in scenarios.items():
                    detailed_results[answer_type][scenario_type] = []
                    
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
                            
                            test_results.append(result)
                            detailed_results[answer_type][scenario_type].append(result)
            
            # Get model info
            model_info = embedder.get_model_info()
            model_info['embedding_time'] = embedding_time
            
            return {
                'model_name': model_name,
                'model_info': model_info,
                'test_results': test_results,
                'detailed_results': detailed_results
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model {model_name}: {str(e)}", exc_info=True)
            return {}
        finally:
            storage.close()

    def run_all_evaluations(self):
        """Run evaluations for all models"""
        for model_name in self.models:
            model_results = self.run_evaluation_for_model(model_name)
            if model_results:
                self.all_model_results[model_name] = model_results

    def generate_individual_reports(self):
        """Generate individual reports for each model"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for model_name, results in self.all_model_results.items():
            if not results.get('test_results'):
                continue
                
            model_safe_name = model_name.replace('/', '_')
            
            # Save detailed results
            detailed_file = self.results_dir / f"detailed_{model_safe_name}_{timestamp}.json"
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump(results['test_results'], f, indent=2, ensure_ascii=False)
            
            # Generate summary report
            summary_file = self.results_dir / f"summary_{model_safe_name}_{timestamp}.txt"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*100 + "\n")
                f.write(f"RETRIEVAL EVALUATION REPORT - {model_name}\n")
                f.write("="*100 + "\n\n")
                
                # Model information
                model_info = results['model_info']
                f.write("MODEL INFORMATION\n")
                f.write("-"*50 + "\n")
                f.write(f"Model Name: {model_info['model_name']}\n")
                f.write(f"Embedding Dimension: {model_info['embedding_dimension']}\n")
                f.write(f"Max Sequence Length: {model_info['max_seq_length']}\n")
                f.write(f"Device: {model_info['device']}\n")
                f.write(f"Embedding Time: {model_info['embedding_time']:.2f} seconds\n\n")
                
                # Calculate statistics
                test_results = results['test_results']
                all_scores = [r['score'] for r in test_results]
                
                # Category scores
                category_scores = {}
                for result in test_results:
                    key = f"{result['answer_type']}_{result['scenario_type']}"
                    if key not in category_scores:
                        category_scores[key] = []
                    category_scores[key].append(result['score'])
                
                f.write("OVERALL STATISTICS\n")
                f.write("-"*50 + "\n")
                f.write(f"Total test cases: {len(test_results)}\n")
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
                f.write(df_category.to_string(index=False) + "\n")

    def generate_comparison_report(self):
        """Generate comparison report across all models"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = self.results_dir / f"model_comparison_{timestamp}.txt"
        
        # Collect summary data for all models
        model_summaries = []
        
        for model_name, results in self.all_model_results.items():
            if not results.get('test_results'):
                continue
                
            test_results = results['test_results']
            all_scores = [r['score'] for r in test_results]
            
            # Calculate category scores
            category_scores = {}
            for result in test_results:
                key = f"{result['answer_type']}_{result['scenario_type']}"
                if key not in category_scores:
                    category_scores[key] = []
                category_scores[key].append(result['score'])
            
            model_summary = {
                'Model': model_name,
                'Overall Score': f"{np.mean(all_scores):.3f}",
                'Embedding Time (s)': f"{results['model_info']['embedding_time']:.2f}",
                'Total Tests': len(test_results)
            }
            
            # Add category scores
            for category, scores in category_scores.items():
                model_summary[category] = f"{np.mean(scores):.3f}"
            
            model_summaries.append(model_summary)
        
        # Create comparison DataFrame
        df_comparison = pd.DataFrame(model_summaries)
        
        # Write comparison report
        with open(comparison_file, 'w', encoding='utf-8') as f:
            f.write("="*120 + "\n")
            f.write("MODEL COMPARISON REPORT\n")
            f.write("="*120 + "\n\n")
            f.write(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Number of Models Tested: {len(self.all_model_results)}\n\n")
            
            f.write("OVERALL COMPARISON\n")
            f.write("-"*120 + "\n")
            f.write(df_comparison.to_string(index=False) + "\n\n")
            
            # Best performers by category
            f.write("BEST PERFORMERS BY METRIC\n")
            f.write("-"*120 + "\n")
            
            # Find best overall
            if not df_comparison.empty:
                best_overall_idx = df_comparison['Overall Score'].apply(lambda x: float(x)).idxmax()
                f.write(f"Best Overall: {df_comparison.loc[best_overall_idx, 'Model']} "
                       f"(Score: {df_comparison.loc[best_overall_idx, 'Overall Score']})\n")
                
                # Find fastest
                fastest_idx = df_comparison['Embedding Time (s)'].apply(lambda x: float(x)).idxmin()
                f.write(f"Fastest Embedding: {df_comparison.loc[fastest_idx, 'Model']} "
                       f"(Time: {df_comparison.loc[fastest_idx, 'Embedding Time (s)']}s)\n\n")
            
            # Category-wise best performers
            category_columns = [col for col in df_comparison.columns 
                              if col not in ['Model', 'Overall Score', 'Embedding Time (s)', 'Total Tests']]
            
            if category_columns:
                f.write("BEST PERFORMERS BY CATEGORY\n")
                f.write("-"*120 + "\n")
                for category in category_columns:
                    try:
                        best_idx = df_comparison[category].apply(lambda x: float(x)).idxmax()
                        f.write(f"{category}: {df_comparison.loc[best_idx, 'Model']} "
                               f"(Score: {df_comparison.loc[best_idx, category]})\n")
                    except:
                        pass
        
        # Also save as CSV for easier analysis
        csv_file = self.results_dir / f"model_comparison_{timestamp}.csv"
        df_comparison.to_csv(csv_file, index=False)
        
        # Print summary to console
        print("\n" + "="*80)
        print("EVALUATION COMPLETE")
        print("="*80)
        print(f"Results saved to: {self.results_dir}")
        print("\nMODEL COMPARISON SUMMARY:")
        print(df_comparison.to_string(index=False))

def main():
    # Configuration
    chunks_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\data\markdown"
    qa_pairs_base_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location"
    
    # Models to evaluate
    models = [
        'msmarco-MiniLM-L-6-v3',
        'all-MiniLM-L6-v2',
        'all-MiniLM-L12-v2',
        'paraphrase-MiniLM-L3-v2',
        'multi-qa-MiniLM-L6-cos-v1',
        'multi-qa-mpnet-base-dot-v1',
        'sentence-t5-base',
        'intfloat/e5-large-v2',
        'BAAI/bge-base-en-v1.5'
    ]
    
    # Initialize evaluator
    evaluator = MultiModelRetrievalEvaluator(
        chunks_dir=chunks_dir,
        qa_pairs_base_dir=qa_pairs_base_dir,
        models=models
    )
    
    # Run evaluation for all models
    logger.info("Starting multi-model evaluation...")
    evaluator.run_all_evaluations()
    
    # Generate individual reports
    logger.info("Generating individual model reports...")
    evaluator.generate_individual_reports()
    
    # Generate comparison report
    logger.info("Generating comparison report...")
    evaluator.generate_comparison_report()

if __name__ == "__main__":
    main()
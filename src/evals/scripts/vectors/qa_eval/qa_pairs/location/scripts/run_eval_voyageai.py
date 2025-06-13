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
import voyageai
import faiss

# Path resolution
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent.parent.parent.parent.parent.parent.parent.absolute()
python_server_path = src_path / "python-server"

if str(python_server_path) not in sys.path:
    sys.path.insert(0, str(python_server_path))
    print(f"Added to path: {python_server_path}")

from vectors.store.embedding_storage import EmbeddingStorage
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoyageAIRetrievalEvaluator:
    def __init__(self, chunks_dir: str, qa_pairs_base_dir: str, models: List[Dict[str, any]]):
        self.logger = logging.getLogger(__name__)
        self.chunks_dir = Path(chunks_dir)
        self.qa_pairs_base_dir = Path(qa_pairs_base_dir)
        self.models = models  # List of dicts with 'name', 'output_dimension', etc.
        self.results_dir = Path(__file__).parent.parent / "results" / "voyageai"        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.store = None
        self.retriever = None
        # Initialize VoyageAI client
        # User should set VOYAGE_API_KEY environment variable
        self.vo_client = voyageai.Client(api_key="pa-lkitG0Pwd7QpXkb7EUyATIlTGHY2aJ6oYHMvOydjfk7")
        self.indices = None
        # Store results for all models
        self.all_model_results = {}
        self.index_path = Path(__file__).parent.parent / "index" / "faiss_indices"
        self.index_path.mkdir(parents=True, exist_ok=True)
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

    def embed_chunks_voyage(self, chunks: List[Dict], model_name: str, output_dimension: int = 1024) -> np.ndarray:
        """Embed chunks using VoyageAI API"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings_list = []
        
        # Process in batches to respect API limits
        batch_size = 10  # Adjust based on API limit

        # Store embeddings in local sqlite database
        DB_PATH = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\db\voyageai"
        DB_NAME = f"eval_voyage_{model_name}_{output_dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        self.store = EmbeddingStorage(DB_PATH, DB_NAME)

        workbook_path = f"{model_name}_{output_dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
  
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                result = self.vo_client.embed(
                    texts=batch_texts,
                    model=model_name,
                    input_type="document",
                    output_dimension=output_dimension
                )
                embeddings_list.extend(result.embeddings)
                embeddings_to_store = np.array(embeddings_list, dtype=np.float32)
 
                self.store.add_workbook_embeddings(
                    workbook_path=workbook_path,
                    embeddings=embeddings_to_store,
                    chunks=chunks,
                    embedding_model=model_name,
                    create_new_version=True
                )
            except Exception as e:
                logger.error(f"Error embedding batch {i//batch_size}: {str(e)}")
                raise
        
        return np.array(embeddings_list, dtype=np.float32)

    def embed_query_voyage(self, query: str, model_name: str, output_dimension: int = 1024) -> np.ndarray:
        """Embed a query using VoyageAI API"""
        try:
            result = self.vo_client.embed(
                texts=[query],
                model=model_name,
                input_type="query",
                output_dimension=output_dimension
            )
            return np.array(result.embeddings[0], dtype=np.float32)
        except Exception as e:
            logger.error(f"Error embedding query: {str(e)}")
            raise

    def search_with_faiss(self, model_name: str, query_text: str, query_embedding: np.ndarray, embeddings: np.ndarray, 
                         chunks: List[Dict], top_k: int = 10) -> List[Dict]:
        """Search using FAISS index"""

        # Build FAISS index
        dimension = embeddings.shape[1]
        workbook_path = f"{model_name}_{dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.indices = {}
        
        # Choose index type based on dataset size
        n_vectors = len(embeddings)
        
        if n_vectors < 1000:
            # For small datasets, use exact search
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            self.logger.info(f"Using exact search (IndexFlatIP) for {n_vectors} vectors")
        else:
            # For larger datasets, use IVF index for faster search
            nlist = min(100, n_vectors // 10)  # Number of clusters
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            
            # Train the index
            index.train(embeddings.astype('float32'))
            self.logger.info(f"Using IVF index with {nlist} clusters for {n_vectors} vectors")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings.astype('float32'))
        
        # Add embeddings to index
        index.add(embeddings.astype('float32'))
        
        # Cache the index
        self.indices[workbook_path] = {
            'index': index,
            'embedding_dim': dimension
        }
        
        # Save index to disk
        index_filename = f"index_{os.path.basename(workbook_path)}.faiss"
        index_file = os.path.join(self.index_path, index_filename)        
        faiss.write_index(index, index_file)

        # Normalize query
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = index.search(query_embedding.astype('float32'), min(top_k, len(chunks)))
        
        # Prepare results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx != -1:  # Valid index
                results.append({
                    'text': chunks[idx]['text'],
                    'metadata': chunks[idx]['metadata'],                    
                    'score': float(score),
                    'rank': i
                })

        # Save results to disk
        self._save_search_results(
            model_name=model_name,
            query_text=query_text or "unknown_query",
            results=results,
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        
        return results

    def _save_search_results(self, model_name: str, query_text: str, results: List[Dict], timestamp: str):
        """Save search results to a JSON file."""
        # Create results directory if it doesn't exist
        results_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\index"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Create a safe filename from the query text
        safe_query = "".join(c if c.isalnum() else "_" for c in query_text[:50])
        filename = f"search_{safe_query}_{timestamp}.json"
        filepath = Path(results_dir) / filename
        
        # Prepare data to save
        data_to_save = {
            'model': model_name,
            'query': query_text,
            'timestamp': timestamp,
            'results': results
        }
        
        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved search results to {filepath}")

    def rerank_with_voyage(self, query: str, initial_results: List[Dict], reranking_model_name: str = "rerank-2", embedding_model_name: str = '', top_k: int = 3) -> List[Dict]:
        """Rerank documents using VoyageAI reranking API"""
        try:
            # Extract texts from documents
            doc_texts = [doc['text'] for doc in initial_results]
            
            # Call reranking API
            reranking_result = self.vo_client.rerank(
                query=query,
                documents=doc_texts,
                model=reranking_model_name,
                top_k=min(top_k, len(initial_results))
            )
            
            # Map reranked results back to original documents
            reranked_docs = []
            for result in reranking_result.results:
                # Find the original document
                for i, doc_text in enumerate(doc_texts):
                    if doc_text == result.document:
                        reranked_doc = initial_results[i].copy()
                        reranked_doc['rerank_score'] = result.relevance_score
                        reranked_docs.append(reranked_doc)
                        break
            
            # Save reranking results to disk
            self._save_rerank_results(
                embedding_model_name=embedding_model_name,
                reranking_model_name=reranking_model_name,
                query_text=query,
                documents=reranked_docs,
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            # Fall back to original order
            return initial_results[:top_k]

    def _save_rerank_results(self, embedding_model_name: str, reranking_model_name: str, query_text: str, documents: List[Dict], timestamp: str):
        """Save reranking results to a JSON file."""
        # Create results directory if it doesn't exist
        results_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location\index\rerank_results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Create a safe filename from the query text
        safe_query = "".join(c if c.isalnum() else "_" for c in query_text[:50])
        filename = f"rerank_{embedding_model_name}_{reranking_model_name}_{safe_query}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # Prepare data to save
        data_to_save = {
            'embedding_model': embedding_model_name,
            'reranking_model': reranking_model_name,
            'query': query_text,
            'timestamp': timestamp,
            'reranked_documents': [
                {
                    'text': doc['text'],
                    'rerank_score': doc.get('rerank_score', 0.0),
                    'original_rank': i,
                    'metadata': doc.get('metadata', {})
                }
                for i, doc in enumerate(documents)
            ]
        }
        
        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved reranking results to {filepath}")

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

    def run_evaluation_for_model(self, model_config: Dict) -> Dict:
        """Run evaluation for a single model"""
        model_name = model_config['name']
        output_dimension = model_config.get('output_dimension', 1024)
        
        logger.info(f"\n{'='*80}\nEvaluating model: {model_name} (dim={output_dimension})\n{'='*80}")
        
        test_results = []
        detailed_results = {}
        
        # Load chunks
        chunks = self.load_chunks()
        if not chunks:
            logger.error(f"No chunks loaded for model {model_name}. Skipping.")
            return {}
        
        try:
            # Generate embeddings using VoyageAI
            logger.info(f"Generating embeddings for {model_name}...")
            start_time = time.time()
            embeddings = self.embed_chunks_voyage(chunks, model_name, output_dimension)
            embedding_time = time.time() - start_time
            logger.info(f"Embedding completed in {embedding_time:.2f} seconds")
            
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
                        if not qa_file.exists():
                            logger.warning(f"QA file not found: {qa_file}")
                            continue
                        qa_pairs = self.load_qa_pairs(qa_file)
                        
                        for qa_pair in qa_pairs:
                            query = qa_pair['query']
                            
                            # Embed query
                            logger.info(f"Embedding query: {query}")
                            query_embedding = self.embed_query_voyage(query, model_name, output_dimension)
                            
                            # Initial retrieval with FAISS
                            logger.info(f"Initial retrieval with FAISS")
                            initial_results = self.search_with_faiss(
                                model_name=model_name,
                                query_text=query,
                                query_embedding=query_embedding,
                                embeddings=embeddings,
                                chunks=chunks,
                                top_k=10
                            )
                            
                            # Rerank top results
                            logger.info(f"Rerank top results")
                            reranked_results = self.rerank_with_voyage(
                                embedding_model_name=model_name,
                                reranking_model_name="rerank-2",
                                query=query,
                                initial_results=initial_results,
                                top_k=3
                            )
                            
                            # Evaluate based on scenario type
                            logger.info(f"Evaluate based on scenario type")
                            if scenario_type == 'single_chunk':
                                score, details = self.evaluate_single_chunk_scenario(qa_pair, reranked_results)
                            else:  # multi_chunk
                                score, details = self.evaluate_multi_chunk_scenario(qa_pair, reranked_results)
                            
                            # Store result
                            logger.info(f"Store result")
                            result = {
                                'query': query,
                                'golden_answer': qa_pair['golden_answer'],
                                'score': score,
                                'details': details,
                                'retrieved_chunks': [
                                    {
                                        'chunk_id': chunk['metadata']['chunk_id'],
                                        'score': chunk.get('rerank_score', chunk['score']),
                                        'text_preview': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text']
                                    }
                                    for chunk in reranked_results
                                ],
                                'qa_file': str(qa_file),
                                'answer_type': answer_type,
                                'scenario_type': scenario_type
                            }
                            
                            test_results.append(result)
                            detailed_results[answer_type][scenario_type].append(result)
            
            # Model info
            model_info = {
                'model_name': model_name,
                'embedding_dimension': output_dimension,
                'max_seq_length': 32000,  # VoyageAI models support 32k tokens
                'device': 'API',
                'embedding_time': embedding_time
            }
            
            return {
                'model_name': model_name,
                'model_info': model_info,
                'test_results': test_results,
                'detailed_results': detailed_results
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model {model_name}: {str(e)}", exc_info=True)
            return {}

    def run_all_evaluations(self):
        """Run evaluations for all models"""
        for model_config in self.models:
            model_results = self.run_evaluation_for_model(model_config)
            if model_results:
                self.all_model_results[model_config['name']] = model_results

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
        comparison_file = self.results_dir / f"voyage_model_comparison_{timestamp}.txt"
        
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
            f.write("VOYAGEAI MODEL COMPARISON REPORT\n")
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
        csv_file = self.results_dir / f"voyage_model_comparison_{timestamp}.csv"
        df_comparison.to_csv(csv_file, index=False)
        
        # Print summary to console
        print("\n" + "="*80)
        print("VOYAGEAI EVALUATION COMPLETE")
        print("="*80)
        print(f"Results saved to: {self.results_dir}")
        print("\nMODEL COMPARISON SUMMARY:")
        print(df_comparison.to_string(index=False))

def main():
    # Configuration
    chunks_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\data\markdown"
    qa_pairs_base_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\qa_eval\qa_pairs\location"
    
    # VoyageAI models to evaluate with their configurations
    models = [
        {'name': 'voyage-3-large', 'output_dimension': 1024},
        {'name': 'voyage-3.5', 'output_dimension': 1024},
        {'name': 'voyage-3.5-lite', 'output_dimension': 512},  # Using smaller dimension for lite
        {'name': 'voyage-code-3', 'output_dimension': 1024},
        {'name': 'voyage-finance-2', 'output_dimension': 1024}
    ]
    
    # Note: Set your VoyageAI API key as environment variable VOYAGE_API_KEY
    # or pass it directly to the client: vo = voyageai.Client(api_key="your_key")
    
    # Initialize evaluator
    evaluator = VoyageAIRetrievalEvaluator(
        chunks_dir=chunks_dir,
        qa_pairs_base_dir=qa_pairs_base_dir,
        models=models
    )
    
    # Run evaluation for all models
    logger.info("Starting VoyageAI multi-model evaluation...")
    evaluator.run_all_evaluations()
    
    # Generate individual reports
    logger.info("Generating individual model reports...")
    evaluator.generate_individual_reports()
    
    # Generate comparison report
    logger.info("Generating comparison report...")
    evaluator.generate_comparison_report()

if __name__ == "__main__":
    main()
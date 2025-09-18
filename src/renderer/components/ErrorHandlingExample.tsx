/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React, { useState } from 'react';
import apiService from '../services/pythonApiService';
import { handleApiError, retryOperation } from '../utils/errorHandler';

// Types for API response
interface SlideResult {
  slide_id: string;
  score: number;
  file_path: string;
  file_name: string;
  slide_number: number;
  image_base64: string;
}

interface SearchResponse {
  success: boolean;
  query: string;
  results: SlideResult[];
  total_found: number;
  processing_time_ms: number;
  used_reranker: boolean;
  error?: string;
}

/**
 * Example component demonstrating improved error handling patterns
 * This shows how to use the error handling utilities in your components
 */
export const ErrorHandlingExample: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<SlideResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRetryOption, setShowRetryOption] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query.');
      return;
    }

    setLoading(true);
    setError(null);
    setShowRetryOption(false);

    try {
      // Example API call with improved error handling
      const response = await apiService.post('/slides/search', {
        query: searchQuery,
        top_k: 10,
        use_reranker: false
      });

      const data = response.data as unknown as SearchResponse;
      if (data.success) {
        setResults(data.results || []);
      } else {
        throw new Error(data.error || 'Search failed');
      }
      
    } catch (err) {
      // Use the centralized error handler
      const { message, shouldRetry } = handleApiError(
        err, 
        'slide_search',
        { query: searchQuery }
      );
      
      setError(message);
      setShowRetryOption(shouldRetry);
    } finally {
      setLoading(false);
    }
  };

  const handleRetryWithBackoff = async () => {
    setLoading(true);
    setError(null);
    setShowRetryOption(false);

    try {
      // Use the retry utility for automatic retries with exponential backoff
      const response = await retryOperation(
        () => apiService.post('/slides/search', {
          query: searchQuery,
          top_k: 10,
          use_reranker: false
        }),
        3, // max retries
        1000 // initial delay in ms
      );

      const data = response.data as unknown as SearchResponse;
      if (data.success) {
        setResults(data.results || []);
      } else {
        throw new Error(data.error || 'Search failed');
      }
      
    } catch (err) {
      const { message } = handleApiError(
        err,
        'slide_search_retry',
        { query: searchQuery, attempt: 'retry' }
      );
      
      setError(message);
      setShowRetryOption(false); // Don't show retry after failed retry
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Search Example with Error Handling</h2>
      
      <div className="mb-4">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Enter search query..."
          className="w-full p-2 border border-gray-300 rounded"
          disabled={loading}
        />
      </div>
      
      <div className="mb-4 space-x-2">
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
        
        {showRetryOption && (
          <button
            onClick={handleRetryWithBackoff}
            disabled={loading}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400"
          >
            Retry
          </button>
        )}
      </div>
      
      {/* User-friendly error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <p className="font-medium">Error:</p>
          <p>{error}</p>
        </div>
      )}
      
      {/* Results display */}
      {results.length > 0 && (
        <div className="mt-4">
          <h3 className="text-lg font-medium mb-2">
            Found {results.length} results:
          </h3>
          <div className="space-y-2">
            {results.map((result, index) => (
              <div key={index} className="p-2 border border-gray-200 rounded">
                <p className="font-medium">{result.file_name}</p>
                <p className="text-sm text-gray-600">
                  Slide {result.slide_number} - Score: {result.score.toFixed(3)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {!loading && !error && results.length === 0 && searchQuery && (
        <div className="text-gray-600 text-center mt-4">
          No results found for "{searchQuery}"
        </div>
      )}
    </div>
  );
};

export default ErrorHandlingExample;

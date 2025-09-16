import React, { useState, useEffect } from 'react';

// Types for search results
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

export const SearchPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [inputWidth, setInputWidth] = useState(500); // Default width
  const [previousWidth, setPreviousWidth] = useState(500);
  const [animationClass, setAnimationClass] = useState('');
  const [searchResults, setSearchResults] = useState<SlideResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchStats, setSearchStats] = useState<{processing_time: number, total_found: number} | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [copiedCardId, setCopiedCardId] = useState<string | null>(null);

  // Function to handle copying file path to clipboard
  const handleCopyFilePath = async (filePath: string, fileName: string, slideId: string) => {
    try {
      console.log('📋 Copying file path to clipboard:', fileName, 'at path:', filePath);
      
      // Type-safe access to electron API
      const electronAPI = (window as any).electron || (window as any).electronAPI;
      
      // Check if Electron API is available and has the fileSystem.copyToClipboard method
      if (electronAPI?.fileSystem?.copyToClipboard) {
        try {
          // Use Electron API if available
          const result = await electronAPI.fileSystem.copyToClipboard(filePath);
          
          if (result?.success) {
            console.log('✅ Successfully copied file path to clipboard:', fileName);
            // Show visual feedback
            setCopiedCardId(slideId);
            setTimeout(() => setCopiedCardId(null), 2000); // Hide after 2 seconds
            return;
          } else {
            console.error('❌ Failed to copy via Electron API:', result?.error);
          }
        } catch (electronError) {
          console.error('❌ Electron API error:', electronError);
        }
      }
      
      // Fallback to browser clipboard API
      await navigator.clipboard.writeText(filePath);
      console.log('✅ Copied file path to clipboard using browser API:', fileName);
      
      // Show visual feedback
      setCopiedCardId(slideId);
      setTimeout(() => setCopiedCardId(null), 2000); // Hide after 2 seconds
      
    } catch (error) {
      console.error('❌ Error copying file path to clipboard:', error);
      // You could show an error notification here if desired
    }
  };

  // Calculate dynamic width based on input length
  useEffect(() => {
    const baseWidth = 500; // Default width
    const maxWidth = 800; // Maximum width
    const minWidth = 300; // Minimum width when very short
    
    let newWidth;
    
    if (searchQuery.length === 0) {
      // Empty input - use default width
      newWidth = baseWidth;
    } else if (searchQuery.length <= 10) {
      // Very short queries - slightly smaller
      newWidth = Math.max(minWidth + (searchQuery.length * 20), minWidth);
    } else if (searchQuery.length <= 30) {
      // Short to medium queries - gradual expansion
      newWidth = baseWidth;
    } else {
      // Longer queries - expand proportionally
      const extraChars = searchQuery.length - 30;
      const expansionRate = 6; // pixels per character
      newWidth = Math.min(baseWidth + (extraChars * expansionRate), maxWidth);
    }
    
    // Add animation feedback based on width change
    if (newWidth > previousWidth) {
      setAnimationClass('expanding');
    } else if (newWidth < previousWidth) {
      setAnimationClass('contracting');
    }
    
    setPreviousWidth(inputWidth);
    setInputWidth(newWidth);
    
    // Clear animation class after animation completes
    const timer = setTimeout(() => setAnimationClass(''), 400);
    return () => clearTimeout(timer);
  }, [searchQuery, inputWidth, previousWidth]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!searchQuery.trim()) {
      return;
    }
    
    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setSearchStats(null);
    setHasSearched(true);
    
    try {
      console.log('🔍 Searching for:', searchQuery);
      
      const response = await fetch('http://localhost:3001/api/slides/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          top_k: 10,
          use_reranker: true
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.status} ${response.statusText}`);
      }
      
      const data: SearchResponse = await response.json();
      
      if (data.success) {
        console.log('✅ Search results:', data);
        setSearchResults(data.results);
        setSearchStats({
          processing_time: data.processing_time_ms,
          total_found: data.total_found
        });
      } else {
        throw new Error(data.error || 'Search failed');
      }
      
    } catch (error) {
      console.error('❌ Search error:', error);
      setSearchError(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };
  
  // SearchResults component
  const SearchResults = () => {
    if (isSearching) {
      return (
        <div className="search-results">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <div className="loading-text">Searching slides...</div>
          </div>
        </div>
      );
    }
    
    if (searchError) {
      return (
        <div className="search-results">
          <div className="error-message">
            <h3>Search Error</h3>
            <p>{searchError}</p>
          </div>
        </div>
      );
    }
    
    if (searchResults.length === 0 && searchQuery.trim()) {
      return (
        <div className="search-results">
          <div className="results-header">
            <p>No slides found for "{searchQuery}"</p>
          </div>
        </div>
      );
    }
    
    if (searchResults.length === 0) {
      return null;
    }
    
    return (
      <div className="search-results">
        <div className="results-header">
          <p>
            Found {searchStats?.total_found || searchResults.length} slides 
            {searchStats && ` in ${searchStats.processing_time.toFixed(1)}ms`}
          </p>
        </div>
        
        <div className="results-grid">
          {searchResults.map((result, index) => (
            <div 
              key={result.slide_id || index} 
              className="result-card clickable"
              onClick={() => handleCopyFilePath(result.file_path, result.file_name, result.slide_id || `slide-${index}`)}
              title={`Copy file path: ${result.file_path}`}
            >
              {result.image_base64 && (
                <img 
                  src={`data:image/png;base64,${result.image_base64}`}
                  alt={`Slide ${result.slide_number} from ${result.file_name}`}
                  className="slide-image"
                />
              )}
              
              <div className="result-info">
                <div className="result-title">
                  {result.file_name}
                </div>
                
                <div className="result-details">
                  <div>Slide #{result.slide_number}</div>
                  <div>Path: {result.file_path}</div>
                </div>
                
              <div className="result-score">
                  Score: {(result.score * 100).toFixed(1)}%
                </div>
              </div>
              
              <div className={`copy-button ${copiedCardId === (result.slide_id || `slide-${index}`) ? 'copied' : ''}`}>
                {copiedCardId === (result.slide_id || `slide-${index}`) ? (
                  <>
                    <svg className="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg className="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                    </svg>
                    Copy Path
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Embedded styles to match the exact CSS provided */}
      <style>{`
        .search-page {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
          overflow: hidden;
          width: 100vw;
          height: calc(100vh - 32px);
          margin-top: 32px;
          background: linear-gradient(135deg, 
            #F8F9FA 0%, 
            #F5F6F8 25%, 
            #F2F4F6 50%, 
            #EFF1F4 75%, 
            #ECEEF2 100%
          );
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        /* Add subtle morphism background elements */
        .search-page::before {
          content: '';
          position: absolute;
          top: 20%;
          left: 15%;
          width: 200px;
          height: 200px;
          background: rgba(255, 255, 255, 0.4);
          border-radius: 50%;
          filter: blur(60px);
          animation: search-float 6s ease-in-out infinite;
        }

        .search-page::after {
          content: '';
          position: absolute;
          bottom: 20%;
          right: 15%;
          width: 150px;
          height: 150px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          filter: blur(40px);
          animation: search-float 8s ease-in-out infinite reverse;
        }

        @keyframes search-float {
          0%, 100% {
            transform: translateY(0px) scale(1);
          }
          50% {
            transform: translateY(-20px) scale(1.1);
          }
        }

        .search-container {
          position: relative;
          z-index: 10;
          transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
          transform: translateY(0);
        }
        
        .search-container.has-results {
          transform: translateY(-25vh);
        }

        .search-form {
          display: flex;
          justify-content: center;
        }

        .search-input {
          max-width: 90vw;
          padding: 16px 24px;
          font-size: 18px;
          border: none;
          border-radius: 50px;
          background: rgba(255, 255, 255, 0.6);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.8),
            inset 0 -1px 0 rgba(255, 255, 255, 0.4);
          color: #3a3a3a;
          outline: none;
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          border: 1px solid rgba(255, 255, 255, 0.5);
          transform-origin: center;
        }
        
        .search-container.has-results .search-input {
          background: rgba(255, 255, 255, 0.9);
          box-shadow: 
            0 4px 20px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            inset 0 -1px 0 rgba(255, 255, 255, 0.6);
        }

        .search-input::placeholder {
          color: #8a8a8a;
          font-weight: 400;
        }

        .search-input:focus {
          background: rgba(255, 255, 255, 0.8);
          box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            inset 0 -1px 0 rgba(255, 255, 255, 0.5),
            0 0 0 3px rgba(255, 255, 255, 0.6);
          transform: translateY(-2px) scale(1.02);
        }

        .search-input:hover:not(:focus) {
          background: rgba(255, 255, 255, 0.7);
          transform: translateY(-1px);
        }

        .search-input.expanding {
          transform: scale(1.01);
        }

        .search-input.contracting {
          transform: scale(0.99);
        }
        
        /* Search results styles */
        .search-results {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 5;
          overflow-y: auto;
          padding-top: calc(25vh + 120px);
          padding-left: 20px;
          padding-right: 20px;
          padding-bottom: 20px;
          background: rgba(248, 249, 250, 0.95);
          backdrop-filter: blur(10px);
          opacity: 0;
          animation: fadeInResults 0.8s ease-out 0.3s forwards;
        }
        
        @keyframes fadeInResults {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .results-header {
          text-align: center;
          margin-bottom: 20px;
          color: #666;
          font-size: 14px;
        }
        
        .results-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
          max-width: 1400px;
          margin: 0 auto;
        }
        
        .result-card {
          background: rgba(255, 255, 255, 0.8);
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
          transition: all 0.3s ease;
          opacity: 0;
          transform: translateY(30px) scale(0.95);
          animation: slideInCard 0.6s ease-out forwards;
          position: relative;
        }
        
        .result-card.clickable {
          cursor: pointer;
        }
        
        .result-card:nth-child(1) { animation-delay: 0.1s; }
        .result-card:nth-child(2) { animation-delay: 0.2s; }
        .result-card:nth-child(3) { animation-delay: 0.3s; }
        .result-card:nth-child(4) { animation-delay: 0.4s; }
        .result-card:nth-child(5) { animation-delay: 0.5s; }
        .result-card:nth-child(n+6) { animation-delay: 0.6s; }
        
        @keyframes slideInCard {
          0% {
            opacity: 0;
            transform: translateY(30px) scale(0.95);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        
        .result-card:hover {
          transform: translateY(-4px) scale(1.02);
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }
        
        .result-card.clickable:hover .copy-button {
          opacity: 1;
          transform: translateY(0);
        }
        
        .result-card:active {
          transform: translateY(-2px) scale(1.01);
        }
        
        .slide-image {
          width: 100%;
          height: 200px;
          object-fit: contain;
          background: #f8f9fa;
        }
        
        .result-info {
          padding: 15px;
        }
        
        .result-title {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 8px;
          color: #333;
          word-break: break-word;
        }
        
        .result-details {
          font-size: 12px;
          color: #666;
          line-height: 1.4;
        }
        
        .result-score {
          display: inline-block;
          background: rgba(0, 120, 255, 0.1);
          color: #0078ff;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          margin-top: 8px;
        }
        
        .copy-button {
          position: absolute;
          top: 12px;
          right: 12px;
          background: rgba(255, 255, 255, 0.9);
          color: #6B7280;
          border: 1px solid rgba(107, 114, 128, 0.2);
          border-radius: 6px;
          padding: 6px 10px;
          font-size: 11px;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 5px;
          opacity: 0;
          transform: translateY(-4px);
          transition: all 0.2s ease;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          pointer-events: none; /* Let clicks pass through to the card */
        }
        
        .copy-icon, .check-icon {
          width: 13px;
          height: 13px;
          color: #6B7280;
          stroke-width: 1.5;
        }
        
        .result-card.clickable:hover .copy-button {
          background: rgba(255, 255, 255, 0.95);
          color: #4B5563;
          border-color: rgba(75, 85, 99, 0.3);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .result-card.clickable:hover .copy-button .copy-icon {
          color: #4B5563;
        }
        
        .copy-button.copied {
          background: rgba(34, 197, 94, 0.9);
          color: white;
          border-color: rgba(34, 197, 94, 0.3);
        }
        
        .copy-button.copied .check-icon {
          color: white;
        }
        
        .error-message {
          text-align: center;
          color: #ff4444;
          background: rgba(255, 68, 68, 0.1);
          padding: 20px;
          border-radius: 8px;
          margin-top: 20px;
        }
        
        .loading-spinner {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          margin-top: 40px;
          animation: fadeIn 0.3s ease-out;
        }
        
        .spinner {
          width: 50px;
          height: 50px;
          border: 4px solid rgba(255, 255, 255, 0.3);
          border-top: 4px solid #0078ff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 16px;
        }
        
        .loading-text {
          color: #666;
          font-size: 16px;
          font-weight: 500;
          opacity: 0.8;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes fadeIn {
          0% { opacity: 0; }
          100% { opacity: 1; }
        }
      `}</style>

      <div className="search-page">
        <div className={`search-container ${hasSearched ? 'has-results' : ''}`}>
          <form className="search-form" onSubmit={handleSubmit}>
            <input
              type="text"
              className={`search-input ${animationClass}`}
              placeholder={isSearching ? "Searching..." : "Search slides..."}
              value={searchQuery}
              onChange={handleInputChange}
              disabled={isSearching}
              style={{
                width: `${inputWidth}px`,
                minWidth: '300px',
                opacity: isSearching ? 0.7 : 1
              }}
              autoFocus
            />
          </form>
        </div>
        
        <SearchResults />
      </div>
    </>
  );
};

export default SearchPage;

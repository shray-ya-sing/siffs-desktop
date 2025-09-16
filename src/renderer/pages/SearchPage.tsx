import React, { useState, useEffect } from 'react';

export const SearchPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [inputWidth, setInputWidth] = useState(500); // Default width
  const [previousWidth, setPreviousWidth] = useState(500);
  const [animationClass, setAnimationClass] = useState('');

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle search submission here
    console.log('Search query:', searchQuery);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
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
      `}</style>

      <div className="search-page">
        <div className="search-container">
          <form className="search-form" onSubmit={handleSubmit}>
            <input
              type="text"
              className={`search-input ${animationClass}`}
              placeholder="Search..."
              value={searchQuery}
              onChange={handleInputChange}
              style={{
                width: `${inputWidth}px`,
                minWidth: '300px'
              }}
              autoFocus
            />
          </form>
        </div>
      </div>
    </>
  );
};

export default SearchPage;

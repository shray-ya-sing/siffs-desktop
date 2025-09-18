#!/usr/bin/env python3
"""
Test script to verify Pinecone API key functionality
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_pinecone_api():
    print("=" * 60)
    print("PINECONE API KEY TEST")
    print("=" * 60)
    
    # Load environment variables from .env file
    project_root = Path(__file__).parent.parent.parent.absolute()
    env_path = project_root / '.env'
    
    print(f"Project root: {project_root}")
    print(f"Environment file: {env_path}")
    print(f"Environment file exists: {env_path.exists()}")
    print()
    
    # Load the .env file
    load_dotenv(env_path)
    
    # Check environment variables
    print("ENVIRONMENT VARIABLES:")
    print("-" * 30)
    pinecone_key = os.getenv('PINECONE_API_KEY')
    voyage_key = os.getenv('VOYAGE_API_KEY')
    
    print(f"PINECONE_API_KEY: {'SET' if pinecone_key else 'NOT SET'}")
    if pinecone_key:
        print(f"  Length: {len(pinecone_key)}")
        print(f"  First 10 chars: {pinecone_key[:10]}...")
        print(f"  Last 5 chars: ...{pinecone_key[-5:]}")
        print(f"  Contains quotes: {pinecone_key.startswith('\"') or pinecone_key.endswith('\"')}")
    
    print(f"VOYAGE_API_KEY: {'SET' if voyage_key else 'NOT SET'}")
    if voyage_key:
        print(f"  Length: {len(voyage_key)}")
        print(f"  First 10 chars: {voyage_key[:10]}...")
    print()
    
    if not pinecone_key:
        print("❌ PINECONE_API_KEY not found!")
        return False
    
    # Test Pinecone connection
    print("TESTING PINECONE CONNECTION:")
    print("-" * 30)
    
    try:
        from pinecone import Pinecone
        print("✅ Pinecone module imported successfully")
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=pinecone_key)
        print("✅ Pinecone client initialized successfully")
        
        # Test API connection by listing indexes
        indexes = pc.list_indexes()
        print(f"✅ API connection successful!")
        print(f"   Found {len(indexes.indexes) if indexes.indexes else 0} indexes")
        
        if indexes.indexes:
            print("   Existing indexes:")
            for idx in indexes.indexes:
                print(f"     - {idx.name} (dimension: {idx.dimension}, metric: {idx.metric})")
        else:
            print("   No existing indexes found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Pinecone: {e}")
        print("   Make sure pinecone is installed: pip install pinecone-client")
        return False
        
    except Exception as e:
        print(f"❌ Pinecone API error: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for common error types
        if "401" in str(e) or "Unauthorized" in str(e):
            print("   This appears to be an authentication error.")
            print("   Check if your API key is correct and active.")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("   This appears to be a permissions error.")
            print("   Check if your API key has the necessary permissions.")
        
        return False

def test_voyage_api():
    print("\n" + "=" * 60)
    print("VOYAGE API KEY TEST")
    print("=" * 60)
    
    voyage_key = os.getenv('VOYAGE_API_KEY')
    
    if not voyage_key:
        print("❌ VOYAGE_API_KEY not found!")
        return False
    
    try:
        import voyageai
        print("✅ VoyageAI module imported successfully")
        
        # Initialize VoyageAI client
        client = voyageai.Client(api_key=voyage_key)
        print("✅ VoyageAI client initialized successfully")
        
        # Test with a simple embedding
        print("🔍 Testing text embedding...")
        result = client.embed(
            texts=["Hello, world!"],
            model="voyage-3"
        )
        
        if result and result.embeddings and len(result.embeddings) > 0:
            embedding = result.embeddings[0]
            print(f"✅ Text embedding successful!")
            print(f"   Embedding dimension: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
        else:
            print("❌ No embedding returned")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import VoyageAI: {e}")
        print("   Make sure voyageai is installed: pip install voyageai")
        return False
        
    except Exception as e:
        print(f"❌ VoyageAI API error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("Testing API Keys for Siffs Desktop Application\n")
    
    # Test Pinecone
    pinecone_success = test_pinecone_api()
    
    # Test VoyageAI
    voyage_success = test_voyage_api()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Pinecone API: {'✅ WORKING' if pinecone_success else '❌ FAILED'}")
    print(f"VoyageAI API: {'✅ WORKING' if voyage_success else '❌ FAILED'}")
    
    if pinecone_success and voyage_success:
        print("\n🎉 All API keys are working correctly!")
        print("   Your slide processing should work now.")
    else:
        print("\n⚠️  Some API keys are not working.")
        print("   Please fix the issues above before using the application.")
    
    print("\n" + "=" * 60)

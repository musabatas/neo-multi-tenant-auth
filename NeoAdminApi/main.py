"""Neo Admin API - Entry point for development and production.

Run with: python main.py or uvicorn main:app --reload
"""

from src.main import app, main

if __name__ == "__main__":
    main()
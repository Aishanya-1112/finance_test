#!/bin/bash
# Start backend in the background
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start frontend
cd frontend && streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0

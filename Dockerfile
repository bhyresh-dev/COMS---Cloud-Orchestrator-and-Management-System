# ── Stage 1: Build React frontend ────────────────────────────
FROM node:20-slim AS frontend-builder

ENV VITE_FIREBASE_API_KEY=AIzaSyCGWvqbKWCzqmEdnqPZccFGujhkN3Odr1w
ENV VITE_FIREBASE_AUTH_DOMAIN=coms-6177e.firebaseapp.com
ENV VITE_FIREBASE_PROJECT_ID=coms-6177e
ENV VITE_API_BASE_URL=""

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve frontend ─────────────────
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/   agents/
COPY config/   config/
COPY utils/    utils/
COPY server.py .

# Copy built React app
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

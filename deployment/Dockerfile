# --- BACKEND MULTI-STAGE BUILD ---
FROM python:3.11-alpine AS backend-base

WORKDIR /app
RUN apk add --no-cache gcc musl-dev libpcap-dev linux-headers curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM backend-base AS backend-prod
COPY src/ /app/src/
# Assuming uvicorn is used for FastAPI
CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]


# --- FRONTEND MULTI-STAGE BUILD ---
FROM node:18-alpine AS frontend-build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine AS frontend-prod
# Copy built assets to Nginx serving directory
COPY --from=frontend-build /app/dist /usr/share/nginx/html
# Copy custom nginx config if necessary, or let the main docker-compose nginx handle routing
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

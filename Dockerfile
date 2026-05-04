# EcoEye2: Node build + Python runtime (single image)
FROM node:22-alpine AS web
WORKDIR /app/ecoeye2/web
COPY ecoeye2/web/package.json ecoeye2/web/package-lock.json* ./
RUN npm ci
COPY ecoeye2/web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=web /app/ecoeye2/server/static ./ecoeye2/server/static
EXPOSE 8000
CMD ["uvicorn", "ecoeye2.server.main:app", "--host", "0.0.0.0", "--port", "8000"]

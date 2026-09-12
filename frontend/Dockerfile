# TrueIntent frontend — React + Vite portal (Module E).
# Build context is the REPO ROOT:  docker build -f frontend/Dockerfile .
# Served with `vite preview` (demo-grade static server, not hardened production hosting).
FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/. ./

# Baked into the bundle at build time. Defaults to a same-machine backend;
# override with:  docker compose build --build-arg VITE_API_URL=http://<host>:8000
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]

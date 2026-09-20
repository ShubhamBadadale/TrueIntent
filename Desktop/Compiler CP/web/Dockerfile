FROM node:24-alpine

WORKDIR /app
COPY web/package.json ./
RUN npm install
COPY web ./

EXPOSE 5173
CMD ["npm", "run", "dev"]

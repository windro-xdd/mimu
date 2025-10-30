# syntax=docker/dockerfile:1.5
FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache curl

COPY package*.json ./

# Install dependencies if package.json provides any (safe even if list is empty)
RUN if [ -f package.json ]; then npm install --omit=dev; fi

COPY . /app

EXPOSE 3000

CMD ["node", "server.js"]

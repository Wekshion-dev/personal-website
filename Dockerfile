FROM node:26-alpine AS builder

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY requirements.txt ./
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

COPY package.json ./
RUN npm install

COPY . .

RUN echo "[]" > public/data/games.json
RUN npm run build

FROM python:3-alpine

WORKDIR /app
RUN mkdir -p /app/public/data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/scripts /app/scripts
RUN mkdir -p /app/public

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
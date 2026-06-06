FROM node:20-slim
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY src/ ./src/

# Add Zscaler CA chain for corporate network SSL inspection
COPY zscaler-full-chain.pem /usr/local/share/ca-certificates/zscaler.crt
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && update-ca-certificates && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser
USER appuser
EXPOSE 3001
CMD ["node", "src/index.js"]

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --verbose

COPY . .

ENV WATCHPACK_POLLING=true
ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000
CMD ["npm","run","dev"]
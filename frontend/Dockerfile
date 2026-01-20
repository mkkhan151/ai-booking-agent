# Stage 1: Builder
from node:24-slim AS builder

WORKDIR /app

# Accept the argument from docker-compose
ARG NEXT_PUBLIC_BACKEND_URL
# Set it as an environment variable so the 'next build' process can see it
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

RUN npm run build

# Stage 2: Runner
FROM node:24-slim AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port
EXPOSE 3000

# Run the application
CMD [ "npm", "start" ]
# The web app as a container, for Cloud Run. Secrets arrive as environment
# variables at run time; .dockerignore keeps .env out of the image.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` and not `npm install` would be the reproducible choice, but the lock
# file is written on macOS and Sharp's Linux-only optional packages are not in
# it, so `npm ci` refuses on the build machine. The lock is still copied, so
# versions resolve the same way; only the platform binaries differ.
RUN npm install --no-audit --no-fund
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080 HOSTNAME=0.0.0.0
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 8080
CMD ["node", "server.js"]

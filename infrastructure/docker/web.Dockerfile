FROM node:22-alpine
WORKDIR /web
COPY apps/web/package.json apps/web/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile || pnpm install
COPY apps/web .
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]

# Isolated agent runner for clean-agent-code evaluations.
# The image contains no clean-agent-code files and no Claude Code configuration, so control
# runs see only the fixture mounted at /work.
FROM node:22.11.0-bookworm-slim

ARG CLAUDE_CODE_VERSION=2.1.289

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm cache clean --force

USER node
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /work

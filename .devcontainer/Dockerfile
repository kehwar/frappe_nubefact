ARG BENCH_IMAGE=docker.io/frappe/bench:latest@sha256:f0b9ec3dd99187af91e83787847dcb0c6c178d551cd22d3f52814d69604d8b25
FROM ${BENCH_IMAGE}

USER root

RUN mkdir -p /workspace/development \
    && chown -R frappe:frappe /workspace/development

USER frappe

ARG PYTHON_VERSION=3.10.13
ENV PYENV_VERSION=${PYTHON_VERSION}
RUN pyenv install -s "${PYTHON_VERSION}" \
    && PYENV_VERSION="${PYTHON_VERSION}" pip install --no-cache-dir --user -e /home/frappe/.bench

ARG NODE_VERSION=18.20.8
RUN bash -lc 'source "$NVM_DIR/nvm.sh" \
    && nvm install "$NODE_VERSION" \
    && nvm alias default "$NODE_VERSION" \
    && nvm use "$NODE_VERSION" \
    && npm install --global --force yarn@1.22.22 \
    && resolved="$(nvm version "$NODE_VERSION")" \
    && ln -sfn "$NVM_DIR/versions/node/$resolved" "$NVM_DIR/versions/node/current"'
ENV PATH=${NVM_DIR}/versions/node/current/bin:${PATH}

WORKDIR /workspace/development

#!/usr/bin/env bash

echo "=> Waiting for Ollama API to become ready =>"

# wait until ollama responds
until ollama list >/dev/null 2>&1; do
  echo "Ollama not ready yet, sleeping..."
  sleep 2
done

echo "=> Ollama is ready"
echo "Checking installed models ..."

# installed models
INSTALLED=$(ollama list | awk 'NR>1 {print $1}')

echo "Installed: $INSTALLED"
echo "Required:  $OLLAMA_MODELS"

# pull missing models
for MODEL in $OLLAMA_MODELS; do
  if echo "$INSTALLED" | grep -qw "$MODEL"; then
    echo "Model already present: $MODEL"
  else
    echo "Pulling model: $MODEL"
    ollama pull "$MODEL"
  fi
done

# warm default
if [ -n "$OLLAMA_MODEL_DEFAULT" ]; then
  echo "=> Warming-up model: $OLLAMA_MODEL_DEFAULT"
  echo "Wake up my friend!" | ollama run "$OLLAMA_MODEL_DEFAULT" >/dev/null 2>&1
fi

echo echo "All done!"

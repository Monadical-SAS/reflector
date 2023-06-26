#!/bin/sh

# Upgrade pip
pip install --upgrade pip

# Default to CPU Installation of JAX
jax_mode="jax[cpu]"

# Install JAX
if [ "$1" == "cpu" ]
then
  jax_mode="jax[cpu]"
elif [ "$1" == "cuda11" ]
then
  jax_mode="jax[cuda11_pip]"
elif [ "$1" == "cuda12" ]
then
  jax_mode="jax[cuda12_pip]"
fi

pip install --upgrade "$jax_mode"

# Install Whisper-JAX base
pip install git+https://github.com/sanchit-gandhi/whisper-jax.git

# Update to latest version
pip install --upgrade --no-deps --force-reinstall git+https://github.com/sanchit-gandhi/whisper-jax.git

pip install -r requirements.txt

# download spacy models
spacy download en_core_web_sm
spacy download en_core_web_md

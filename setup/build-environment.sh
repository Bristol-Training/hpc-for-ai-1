#!/usr/bin/env bash
# Build the shared Python environment (the course kernel) for HPC for AI.
#
# Run this over SSH on an Isambard-AI Phase 2 login node. The compute nodes
# (including JupyterHub sessions) can't reach the internet, so the packages
# can't be downloaded from there.
#
#     bash setup/build-environment.sh $PROJECTDIR/hpc-ai-1/venv
#
# Attendees then register it as a Jupyter kernel with:
#
#     $PROJECTDIR/hpc-ai-1/venv/bin/python -m ipykernel install --user \
#         --name hpc-ai-1 --display-name "Python (HPC for AI part 1)"

set -euo pipefail

VENV="${1:?Usage: bash setup/build-environment.sh <path-for-the-new-venv>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# uv downloads its own copy of Python. By default it goes in your home folder,
# which other people in the project can't read, so the kernel would only work
# for you. Put it next to the venv instead.
export UV_PYTHON_INSTALL_DIR="$(dirname "$VENV")/python"

# Install uv if it isn't already available
if ! command -v uv > /dev/null; then
    echo "Installing uv..."
    curl --location --silent --show-error --fail https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Creating the virtual environment in $VENV..."
uv venv --seed --managed-python --python 3.12 "$VENV"

# PyTorch first, with CUDA support, from the PyTorch package index
# (as in the BriCS distributed training tutorial). Installing it separately
# stops pip from swapping in a CPU-only build later.
echo "Installing PyTorch..."
uv pip install --python "$VENV/bin/python" \
    torch==2.9.0 torchvision \
    --extra-index-url https://download.pytorch.org/whl/cu128

echo "Installing the course packages..."
uv pip install --python "$VENV/bin/python" --requirement "$HERE/requirements.txt"

echo "Checking PyTorch was installed with CUDA support..."
"$VENV/bin/python" -c "import torch; print('PyTorch', torch.__version__, '| built for CUDA', torch.version.cuda)"
echo "(Login nodes have no GPUs, so check the GPUs themselves from a JupyterHub session.)"

echo "Checking Python is in the project folder, not your home folder..."
readlink -f "$VENV/bin/python"

# Let everyone in the project use it
chmod -R g+rX "$VENV" "$UV_PYTHON_INSTALL_DIR"

echo
echo "Done. Record the versions that worked with:"
echo "    uv pip freeze --python $VENV/bin/python"

uv pip uninstall jvm || true
deactivate || true
rm -rf .venv
uv sync
uv build
uv pip install dist/jvm_pybind-0.1.1-py3-none-any.whl
source .venv/bin/activate

"""Repository-local CLI utilities.

Run from the **repository root** so imports resolve:

    python -m tools.run_rag_eval
    python -m tools.check_api_contract_sync
    python -m tools.generate_llm_api_yaml

Do not rely on ``PYTHONPATH`` in ``.env`` for shells: that file is for app runtime, not
automatically exported to your terminal. Use ``python -m tools.<module>`` instead.
"""

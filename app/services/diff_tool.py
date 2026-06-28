# app/services/diff_tool.py
from back.diff_tool import compare_configs as _compare_configs
import tempfile
import json
import os

def assess_changes(current_state: dict, desired_config: dict) -> str:
    """
    Wrapper vers back/diff_tool.py → compare_configs()
    Prend des dictionnaires Python (pas des fichiers)
    """
    # On simule les fichiers temporaires
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as curr_f:
        json.dump(current_state, curr_f)
        current_path = curr_f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as desired_f:
        json.dump(desired_config, desired_f)
        desired_path = desired_f.name

    try:
        # On redéfinit print() pour capturer la sortie
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            _compare_configs(current_path, desired_path)
        
        return f.getvalue()
    finally:
        os.unlink(current_path)
        os.unlink(desired_path)

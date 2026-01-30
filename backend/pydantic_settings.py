import os
from typing import Any


class BaseSettings:
    def __init__(self, **kwargs: Any):
        # Load environment variables from a .env file if defined on the subclass
        cfg = getattr(self.__class__, 'Config', None)
        env_file = getattr(cfg, 'env_file', None) if cfg else None
        if env_file:
            path = env_file
            # Resolve relative path against current working directory
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), path)
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#') or '=' not in line:
                                continue
                            k, v = line.split('=', 1)
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

        # Populate fields from environment variables (or kwargs) using type hints
        annotations = getattr(self.__class__, '__annotations__', {})
        for name, typ in annotations.items():
            if name in kwargs:
                value = kwargs[name]
            else:
                value = os.environ.get(name)
            if value is None:
                continue
            # Basic type coercion for common types
            if typ is bool:
                if isinstance(value, str):
                    v = value.strip().lower()
                    if v in {'1', 'true', 'yes', 'on'}:
                        value = True
                    elif v in {'0', 'false', 'no', 'off'}:
                        value = False
                    else:
                        value = bool(value)
                else:
                    value = bool(value)
            elif typ is int:
                try:
                    value = int(value)
                except Exception:
                    value = 0
            # Assign to instance attribute using the exact field name (uppercase in this project)
            setattr(self, name, value)

"""Backfill de salidas automáticas (00:30) sobre anomalías de asistencia existentes.

Dry-run por defecto: lista qué se resolvería sin escribir. Con --apply escribe.
Idempotente (lo ya resuelto no vuelve a aparecer).

    uv run python scripts/backfill_salidas_0030.py            # solo lista
    uv run python scripts/backfill_salidas_0030.py --apply    # escribe

Usa DATABASE_URL del entorno: para producción, corre contra la URL de prod SOLO
tras revisar el dry-run.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import RegistroAsistencia  # noqa: E402
from app.services.jornada import backfill_salidas_automaticas  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="escribir cambios (default: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        resueltos = backfill_salidas_automaticas(db, aplicar=args.apply)
        restantes = (
            db.query(RegistroAsistencia)
            .filter(RegistroAsistencia.requiere_revision.is_(True))
            .count()
        )
        for registro_id, salida in resueltos:
            print(f"registro {registro_id} -> salida {salida.isoformat()}")
        modo = "APLICADO" if args.apply else "DRY-RUN (nada escrito)"
        print(f"{modo}: {len(resueltos)} resueltos; anomalías que siguen en revisión: {restantes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

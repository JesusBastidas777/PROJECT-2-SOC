"""Atomic, portable JSON report writer."""

import json
import os
from pathlib import Path
import tempfile

from soc.errors import QueryError
from storage.errors import StorageWriteError


class ReportExporter:
    @staticmethod
    def write(destination, report, *, overwrite=False):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            raise QueryError(f"report destination already exists: {destination}")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", delete=False,
                dir=destination.parent, prefix=destination.name + ".",
            ) as output:
                temporary = Path(output.name)
                json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            if overwrite:
                os.replace(temporary, destination)
            else:
                try:
                    os.link(temporary, destination)
                except FileExistsError as exc:
                    raise QueryError(f"report destination already exists: {destination}") from exc
                temporary.unlink()
            temporary = None
        except QueryError:
            raise
        except OSError as exc:
            raise StorageWriteError(f"cannot export report to: {destination}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {"path": str(destination), "bytes": destination.stat().st_size, "overwrite": overwrite}

# viewer/views.py
import os
import uuid
from pathlib import Path
import sqlite3

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


def looks_like_sqlite(file_path: str) -> bool:
    """Valida si el archivo es una BD SQLite intentando leer sqlite_master."""
    try:
        conn = sqlite3.connect(file_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master LIMIT 1;")
            cur.fetchall()
            return True
        finally:
            conn.close()
    except Exception:
        return False


@require_POST
@login_required
def upload_files(request):
    files = request.FILES.getlist("dbfiles")
    if not files:
        return HttpResponseBadRequest("No se recibieron archivos.")

    upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    rejected = []

    for f in files:
        original = Path(f.name).name
        ext = Path(original).suffix.lower()  # puede ser "" si no tiene extensión

        # nombre único (mantengo la extensión si existe)
        new_name = f"{Path(original).stem}_{uuid.uuid4().hex}{ext}"
        out_path = upload_dir / new_name

        with open(out_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)

        # validar que sea sqlite de verdad
        if not looks_like_sqlite(str(out_path)):
            try:
                os.remove(out_path)
            except Exception:
                pass
            rejected.append(original)
            continue

        saved.append(str(out_path))

    if not saved:
        msg = "Ningún archivo válido. No parecían ser SQLite: " + ", ".join(rejected[:10])
        return HttpResponseBadRequest(msg)

    request.session["db_paths"] = saved

    # Si algunos fallaron, igual seguimos (uso interno)
    return redirect("viewer_page")

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse

from .services.sqlite_service import get_schema, run_select
from .services.excel_service import build_xlsx_one_sheet

@login_required
def upload_page(request):
    return render(request, "viewer/upload.html")

@login_required
def viewer_page(request):
    dbs = request.session.get("db_paths", [])
    return render(request, "viewer/viewer.html", {"db_count": len(dbs)})

@login_required
def _get_session_dbs(request):
    dbs = request.session.get("db_paths", [])
    ok = [p for p in dbs if isinstance(p, str) and os.path.exists(p)]
    request.session["db_paths"] = ok
    return ok

@login_required
def api_schema(request):
    dbs = _get_session_dbs(request)
    if not dbs:
        return JsonResponse({"ok": False, "error": "No hay BDs cargadas."})

    payload = {"ok": True, "dbs": []}

    for p in dbs:
        name = Path(p).name
        try:
            schema = get_schema(p)
            payload["dbs"].append({
                "name": name,
                "schema": schema
            })
        except Exception as e:
            payload["dbs"].append({
                "name": name,
                "schema": {},
                "error": str(e)
            })

    return JsonResponse(payload)


@require_POST
@login_required
def api_query(request):
    dbs = _get_session_dbs(request)

    db_name = request.POST.get("db_name")
    table = request.POST.get("table")
    cols = request.POST.getlist("cols")
    filter_text = request.POST.get("filter") or None

    db_path = next((p for p in dbs if Path(p).name == db_name), None)

    if not db_path:
        return JsonResponse({"ok": False, "error": "BD no encontrada"})

    try:
        headers, rows = run_select(db_path, table, cols, filter_text)
        return JsonResponse({
            "ok": True,
            "headers": headers,
            "rows": [list(r) for r in rows]
        })
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})


@require_POST
@login_required
def api_export(request):
    dbs = _get_session_dbs(request)

    db_name = request.POST.get("db_name")
    table = request.POST.get("table")
    cols = request.POST.getlist("cols")
    filter_text = request.POST.get("filter") or None

    db_path = next((p for p in dbs if Path(p).name == db_name), None)

    headers, rows = run_select(db_path, table, cols, filter_text)

    wb = build_xlsx_one_sheet(f"{db_name}-{table}", headers, rows)

    from io import BytesIO
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = f'attachment; filename="export_{table}.xlsx"'
    return resp


@require_POST
@login_required
def api_clear_session(request):
    request.session.pop("db_paths", None)
    return JsonResponse({"ok": True})

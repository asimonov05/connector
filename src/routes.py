from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse

from src.config import get_settings

router = APIRouter(prefix="/service")


@router.get("/check", status_code=200)
def check() -> Response:
    return Response(
        status_code=status.HTTP_200_OK, content="serverapi", media_type="plain/text"
    )


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    config = get_settings()
    file_path = config.UPLOAD_DIR / file.filename

    with file_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # читаем 1MB за раз
            if not chunk:
                break
            f.write(chunk)

    return JSONResponse(
        {
            "filename": file.filename,
            "saved_to": str(file_path),
            "content_type": file.content_type,
        }
    )


@router.get("/file-list")
async def file_list() -> list[dict]:
    """
    Возвращает список файлов и папок в корневом каталоге UPLOAD_DIR.
    Формат:
    [
        {"name": "file1.txt", "type": "file"},
        {"name": "subfolder", "type": "directory"},
        ...
    ]
    """
    config = get_settings()
    base_path = config.UPLOAD_DIR

    if not base_path.exists():
        return []

    result = []
    for item in base_path.iterdir():
        result.append(
            {"name": item.name, "type": "directory" if item.is_dir() else "file"}
        )

    return result


@router.delete("/delete-file")
async def delete_file(name: str):
    config = get_settings()
    file_path = config.UPLOAD_DIR / name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    try:
        file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")

    return {"deleted": name, "status": "ok"}

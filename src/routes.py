from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/service")


@router.get("/check", status_code=200)
def check() -> Response:
    return Response(
        status_code=status.HTTP_200_OK, content="serverapi", media_type="plain/text"
    )

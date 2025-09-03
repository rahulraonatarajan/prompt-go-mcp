from fastapi import APIRouter

router = APIRouter()


@router.get("/roi")
def roi() -> dict[str, str]:
    return {"todo": "render markdown ROI report"}


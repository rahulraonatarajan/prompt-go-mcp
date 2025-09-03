from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def summary() -> dict[str, str]:
    return {"todo": "wire to storage and aggregator"}


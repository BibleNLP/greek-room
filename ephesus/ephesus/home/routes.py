from fastapi import APIRouter

router = APIRouter(tags=["home"])


@router.get("/")
async def get_index():
    return {"message": "Admin getting schwifty"}

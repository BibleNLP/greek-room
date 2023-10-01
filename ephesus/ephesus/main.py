from fastapi import Depends, FastAPI

from .dependencies import get_query_token, get_token_header
from .wildebeest import routes as wb_routes
from .routers import items

app = FastAPI(dependencies=[Depends(get_query_token)])


app.include_router(items.router)
app.include_router(
    wb_routes.router,
    prefix="/wildebeest",
    tags=["wildebeest"],
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .dependencies import get_query_token, get_token_header
from .wildebeest import routes as wb_routes
from .home import ui_routes as home_ui_routes
from .routers import items

app = FastAPI()
app.mount("/static", StaticFiles(packages=[("ephesus.home", "static")]), name="static")


app.include_router(home_ui_routes.router)
app.include_router(
    wb_routes.router,
    prefix="/wildebeest",
    tags=["wildebeest"],
)


# @app.get("/")
# async def root():
#     return {"message": "Hello Bigger Applications!"}

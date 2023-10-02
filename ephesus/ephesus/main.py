from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .dependencies import get_query_token, get_token_header
from .wildebeest import routes as wb_routes
from .home import routes as home_routes
from .routers import items
from .database.setup import SessionLocal, engine
from .database import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(packages=[("ephesus.home", "static")]), name="static")


app.include_router(home_routes.ui_router)
app.include_router(
    wb_routes.router,
    prefix="/wildebeest",
    tags=["wildebeest"],
)


# @app.get("/")
# async def root():
#     return {"message": "Hello Bigger Applications!"}

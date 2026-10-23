from fastapi import FastAPI

from app.errors import AppError, register_error_handlers

app = FastAPI()
register_error_handlers(app)

@app.get("/api/_demo-error")
def demo_error():
    raise AppError("demo", "Demo message.", 409)
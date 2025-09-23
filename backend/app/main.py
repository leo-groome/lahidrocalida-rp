from fastapi import FastAPI

app = FastAPI(title="La Hidrocálida POS API")

@app.get("/")
def root():
    return {"message": "La Hidrocálida POS API"}
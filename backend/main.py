# FatturaMVP Backend
# This file imports and runs the actual FastAPI app from app.main

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

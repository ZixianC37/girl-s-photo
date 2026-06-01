"""
灯光模拟工作台 — FastAPI 后端
支持：影棚场景配置、模型上传/管理、灯光渲染
"""
import asyncio
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from blender_renderer import render, load_presets

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="灯光模拟工作台")

# In-memory task store
tasks: dict[str, dict] = {}

ALLOWED_EXTENSIONS = {".glb", ".gltf", ".obj", ".fbx", ".stl"}


# ── Presets ──

@app.get("/api/presets")
async def get_presets():
    data = load_presets()
    return {"presets": data["presets"]}


# ── Model Management ──

@app.post("/api/models/upload")
async def upload_model(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    model_id = uuid.uuid4().hex[:8]
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / file.filename

    content = await file.read()
    with open(model_path, "wb") as f:
        f.write(content)

    return {
        "id": model_id,
        "name": file.filename,
        "path": str(model_path),
        "size": len(content),
        "format": ext,
    }


@app.get("/api/models")
async def list_models():
    models = []
    for model_dir in sorted(MODELS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        for f in model_dir.iterdir():
            if f.suffix.lower() in ALLOWED_EXTENSIONS:
                models.append({
                    "id": model_dir.name,
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "format": f.suffix.lower(),
                })
                break
    return {"models": models}


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    model_dir = MODELS_DIR / model_id
    if not model_dir.exists():
        raise HTTPException(404, "Model not found")
    for f in model_dir.iterdir():
        f.unlink()
    model_dir.rmdir()
    return {"ok": True}


# ── Rendering ──

@app.post("/api/render")
async def start_render(params: dict):
    task_id = uuid.uuid4().hex[:12]
    tasks[task_id] = {
        "status": "rendering",
        "progress": "",
        "image_url": None,
        "render_time": 0,
        "error": None,
    }

    preset_data = load_presets()
    scene_defaults = preset_data.get("scene_defaults", {})
    params.setdefault("scene", scene_defaults)

    # Resolve model path
    model = params.get("model", {})
    if model.get("type") == "import" and model.get("id"):
        model_dir = MODELS_DIR / model["id"]
        if model_dir.exists():
            for f in model_dir.iterdir():
                if f.suffix.lower() in ALLOWED_EXTENSIONS:
                    model["path"] = str(f)
                    break

    params["model"] = model

    asyncio.get_event_loop().run_in_executor(None, _do_render, task_id, params)
    return {"task_id": task_id}


def _do_render(task_id: str, params: dict):
    try:
        image_path, render_time, error = render(params)
        if error:
            tasks[task_id] = {"status": "error", "error": error, "render_time": render_time}
        else:
            filename = os.path.basename(image_path)
            tasks[task_id] = {
                "status": "done",
                "image_url": f"/output/{filename}",
                "render_time": round(render_time, 1),
            }
    except Exception as e:
        tasks[task_id] = {"status": "error", "error": str(e)}


@app.get("/api/render/{task_id}/status")
async def get_render_status(task_id: str):
    if task_id not in tasks:
        return JSONResponse({"status": "error", "error": "Task not found"}, status_code=404)
    return tasks[task_id]


# ── Static Files ──

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Photography Lighting Simulation - Parameter-Driven Tech Stack

Date: 2026-05-26
Context: Step-by-step photography lighting simulation tool (NOT real-time 3D drag-and-drop)

---

## Overview: 4-Step Workflow Architecture

```
Step 1: AI Scene Background Generation
    --> Step 2: 3D Mannequin/Model Integration
        --> Step 3: Lighting Parameter Configuration
            --> Step 4: Render / AI Relight Preview
```

Orchestration Layer: ComfyUI (self-hosted backend)

---

## Step 1: AI Scene Background Generation

### 1.1 Recommended Base Checkpoints (SDXL)

| Checkpoint | Base | Specialty | Source |
|-----------|------|-----------|--------|
| **Juggernaut XL** | SDXL | Best overall photorealism; skin texture, natural lighting | Civitai |
| **Realistic Vision XL** | SDXL | Lifelike portraits, landscapes, everyday photography | Civitai |
| **EpicRealism XL** | SDXL | Cinematic photography, skin texture, lighting realism | Civitai (DucHaiten) |
| **DreamShaper XL** | SDXL | Versatile: realistic + stylized outputs | Civitai |
| **CyberRealistic XL** | SDXL | Ultra-realistic human features | Civitai |
| **Stable Diffusion 3.5 Large** | SD3.5 | Official Stability AI; best prompt adherence | HuggingFace |

Download location: https://civitai.com (search checkpoint names)

### 1.2 ControlNet Models for Scene Control

| ControlNet Model | Use Case | Source |
|-----------------|----------|--------|
| **controlnet-depth-sdxl-1.0** | Control scene layout via depth maps | HuggingFace (diffusers) |
| **controlnet-canny-sdxl-1.0** | Edge-guided scene generation | HuggingFace (diffusers) |
| **controlnet-scribble-sdxl** | Rough sketch to scene | HuggingFace |
| **controlnet-qrcode-monster** | Creative pattern-based scenes | Civitai |

Installation via ComfyUI: Install via ComfyUI Manager; models go to `ComfyUI/models/controlnet/`

### 1.3 Photography-Specific LoRA Models

| LoRA | Specialty | Civitai ID |
|------|-----------|------------|
| **Cinematic Portrait Lighting (Zimg Turbo)** | Strong directional lighting, deep shadows, cinematic tones | civitai.com/models/2595570 |
| **Better Portrait Lighting** | Dramatic and realistic portrait lighting improvement | civitai.com/models/41809 |
| **Studio Lighting** | Key light, fill light, rim light studio setups | Search "studio lighting" on Civitai |

Deployment: LoRA files (.safetensors) placed in `ComfyUI/models/loras/`, referenced in workflows via LoRA Loader node.

### 1.4 Recommended Generation Pipeline (ComfyUI)

```
[Checkpoint Loader (SDXL)]
    --> [LoRA Loader (Photography Lighting)]
        --> [ControlNet Apply (Depth/Canny)]
            --> [CLIP Text Encode (Prompt)]
                --> [KSampler]
                    --> [VAE Decode]
                        --> [Save/Output Image]
```

For scene background specifically, use prompts like:
- "photography studio background, seamless paper roll, neutral gray"
- "outdoor garden scene, soft natural lighting, bokeh background"
- "industrial loft interior, exposed brick, large windows, golden hour"

---

## Step 2: 3D Human Model Integration

### 2.1 Avatar / Body Model Sources

#### WARNING: Ready Player Me is Sunsetting

**Status:** Ready Player Me has been acquired by Netflix and is sunsetting for third-party developers on **January 31, 2026**. Do NOT build new integrations on RPM.

Sources:
- https://www.mediapost.com/publications/article/411513/netflix-buys-avatar-creation-company-for-in-game-u.html
- https://avatarsdk.com/blog/2026/01/15/switch-from-ready-player-me-to-avatar-sdk-fast-familiar-production-ready/

#### Recommended: Avatar SDK (RPM Replacement)

| Feature | Details |
|---------|---------|
| **Website** | https://avatarsdk.com/ |
| **API Type** | REST API |
| **Output** | GLB/FBX head and body models |
| **Features** | Selfie-to-avatar, body morphing, clothing, hair styles |
| **Positioning** | Direct drop-in replacement for Ready Player Me |

#### Alternative: Avaturn

| Feature | Details |
|---------|---------|
| **Website** | https://avaturn.me/ |
| **API Type** | REST API + SDK (Unity, Unreal, Web) |
| **Output** | RPM-compatible GLB models |
| **Features** | Face scanning, body customization |
| **Note** | Output is compatible with RPM pipelines |

#### Open Source: SMPL / SMPL-X Body Models

| Feature | SMPL | SMPL-X |
|---------|------|--------|
| **Website** | https://smpl.is.tue.mpg.de/ | https://smpl-x.is.tue.mpg.de/ |
| **Parameters** | 10 shape (beta) + pose | 10 shape + pose + hand articulation + facial expressions |
| **License** | Non-commercial (academic) | Non-commercial (academic) |
| **Web Rendering** | Three.js (via THREESMPL) | Three.js, ONNX for web inference |
| **Integration** | Parameter-driven body shape/pose | Full body + hands + face |

**SMPL-X is recommended for the parameter-driven approach** because:
1. Body shape controlled by 10 numeric parameters (beta)
2. Pose controlled by joint rotation parameters
3. Expression controlled by expression blend shapes
4. Can be rendered in Three.js directly

**GitHub repos for web integration:**
- https://github.com/CalciferZh/SMPL (Python implementation)
- https://github.com/vchoutas/smplx (Official SMPL-X code)
- Multiple Three.js SMPL viewers exist on GitHub (search "three.js SMPL")

#### Pre-made 3D Mannequin Assets (Simpler Approach)

For a simpler MVP, use pre-made GLB/GLTF mannequin models:
- **Mixamo** (https://www.mixamo.com/) - Free rigged characters (manual download)
- **Sketchfab** (https://sketchfab.com) - Search "mannequin" or "dress form" (filter by downloadable GLB)
- **Three.js examples** include built-in humanoid models

### 2.2 Mixamo (Adobe) for Poses

| Feature | Details |
|---------|---------|
| **Website** | https://www.mixamo.com/ |
| **Cost** | Free (Adobe account required) |
| **Output** | FBX format with animation |
| **Poses** | Thousands of pre-made poses and animations |
| **API** | NONE - manual download only (no public API) |
| **Workaround** | Pre-download a library of pose FBX files; store as GLB for Three.js |

**Integration approach:**
1. Pre-download ~50-100 common photography poses from Mixamo
2. Convert FBX to GLB using Blender headless or `fbx2gltf` npm package
3. Store in asset library; user selects pose from dropdown
4. Apply pose to SMPL-X model or mannequin in Three.js scene

### 2.3 Compositing 3D Model into Generated Scene

**Approach A: Three.js Scene Composition (Recommended)**
1. Generate scene background via AI (Step 1) as an image/HDR
2. In Three.js, set the background image as scene background or environment map
3. Load 3D mannequin model (GLB) into the scene
4. Position model at correct depth/position relative to background
5. Match lighting to generated scene (or use the background as env map for ambient)

```javascript
// Pseudocode for compositing
const scene = new THREE.Scene();
// Set AI-generated scene as background
scene.background = new THREE.TextureLoader().load('ai_scene.jpg');
// Or use as environment for reflections
scene.environment = new THREE.RGBELoader().load('ai_scene.hdr');

// Load mannequin
const loader = new THREE.GLTFLoader();
const mannequin = await loader.loadAsync('mannequin.glb');
scene.add(mannequin);
```

**Approach B: Depth-Aware Compositing (AI Pipeline)**
1. Generate scene background
2. Generate depth map for the scene (using Depth Anything / MiDaS)
3. Composite 3D model render at correct depth layer
4. Use IC-Light or similar to harmonize lighting between model and scene

### 2.4 Recommended npm Packages for 3D Integration

| Package | Purpose |
|---------|---------|
| `three` (npm) | Core 3D engine |
| `@react-three/fiber` | React wrapper for Three.js |
| `@react-three/drei` | Helpers: GLTFLoader, Environment, etc. |
| `three-gpu-pathtracer` | Physically-based path tracing |
| `@react-three/gpu-pathtracer` | React wrapper for path tracer |
| `fbx2gltf` or `gltf-transform` | FBX to GLB conversion |

---

## Step 3: Lighting Parameter Configuration

### 3.1 Three.js Lighting API Reference

#### Light Types for Photography Simulation

| Light Type | Three.js Class | Photography Equivalent | Key Parameters |
|-----------|---------------|----------------------|----------------|
| Softbox | `RectAreaLight` | Studio softbox/panel | width, height, color, intensity, position, rotation |
| Spot/Strobe | `SpotLight` | Strobe with modifier | angle, penumbra, decay, distance, intensity, color |
| Key light | `DirectionalLight` | Sun or large strobe | intensity, color, position (direction), castShadow |
| Fill ambient | `HemisphereLight` | Ambient room light | skyColor, groundColor, intensity |
| Practical/point | `PointLight` | Bare bulb, candle | distance, decay, intensity, color |
| Photometric | `IESSpotLight` | Real-world light fixture | IES profile map, all SpotLight params |

#### RectAreaLight (Primary Studio Light)

```javascript
import { RectAreaLight } from 'three';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';

RectAreaLightUniformsLib.init();

const softbox = new RectAreaLight(
    0xffffff,  // color
    100,       // intensity (lumens)
    2.0,       // width
    1.0        // height
);
softbox.position.set(2, 2, 2);
softbox.lookAt(0, 1, 0); // point at subject

// IMPORTANT: RectAreaLight only works with MeshStandardMaterial and MeshPhysicalMaterial
```

#### IESSpotLight (Real-World Light Profiles)

```javascript
import { IESLoader } from 'three/addons/loaders/IESLoader.js';
import { IESSpotLight } from 'three/addons/lights/IESSpotLight.js';

const iesLoader = new IESLoader();
const iesTexture = await iesLoader.loadAsync('path/to/ies_profile.ies');

const spotLight = new IESSpotLight(0xffffff, 100);
spotLight.map = iesTexture;
spotLight.position.set(0, 3, 0);
spotLight.angle = Math.PI / 6;
```

**Three.js docs:**
- IESLoader: https://threejs.org/docs/#examples/en/loaders/IESLoader
- IESSpotLight: https://threejs.org/docs/#examples/en/lights/IESSpotLight

**IES profile sources:** Lighting manufacturer websites (Philips, Erco, Zumtobel), or search "IES profiles free download"

### 3.2 Photography Lighting Presets (Built-In)

| Preset Name | Description | Light Positions (3-point) |
|-------------|-------------|--------------------------|
| **Rembrandt** | Triangle of light on far cheek | Key: 45deg up, 45deg side; Fill: opposite, lower; Rim: behind |
| **Butterfly (Paramount)** | Shadow under nose, glamorous | Key: directly above/forward; Fill: below camera; Rim: behind |
| **Split** | Half face lit, half shadow | Key: 90deg side; Fill: none or very low; Rim: behind |
| **Loop** | Small nose shadow loop | Key: 30deg up, 30deg side; Fill: opposite; Rim: behind |
| **Broad** | Light on broad side of face | Key: 30deg on same side as camera; Fill: opposite; Rim: behind |
| **Short** | Light on short side of face | Key: 30deg opposite camera; Fill: same side as camera; Rim: behind |
| **Rim/Edge** | Only edge lighting visible | Key: behind subject, 45deg; Fill: very low front; Rim: opposite |
| **High Key** | Bright, even, minimal shadows | Key: large softbox front; Fill: large softbox opposite; BG: bright |
| **Low Key** | Dramatic, mostly dark | Key: small gridded spot, 45deg; Fill: none; BG: dark |
| **Beauty** | Soft, flattering, fashion | Key: large softbox above; Fill: reflector below; Rim: soft behind |

Each preset maps to specific Three.js light positions/intensities that can be applied as a parameter set.

### 3.3 Lighting Parameter Schema

```typescript
interface LightingSetup {
  lights: LightConfig[];
  preset?: PresetName;
}

interface LightConfig {
  type: 'rectArea' | 'spot' | 'directional' | 'point' | 'iesSpot';
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  color: string;           // hex color
  colorTemperature: number; // Kelvin (2700-6500)
  intensity: number;        // lumens or watts
  // RectAreaLight specific
  width?: number;
  height?: number;
  // SpotLight specific
  angle?: number;
  penumbra?: number;
  // IES specific
  iesProfile?: string;
  // Common
  castShadow: boolean;
  shadowBias: number;
  shadowMapSize: number;
}

// Color temperature to hex conversion helper
function kelvinToHex(kelvin: number): string {
  // 2700K = warm (orange), 6500K = cool (blue-white)
  // Use standard Kelvin-to-RGB algorithm
}
```

### 3.4 Three.js Lighting Resources

- Three.js lighting tutorial: https://dev.to/peter3riding/understanding-threejs-lighting-a-concise-reference-3e8b
- RectAreaLight studio setup: https://sbcode.net/threejs/lights/
- Realistic lighting setup (video): https://www.youtube.com/watch?v=7GGNzryHfTw

---

## Step 4: Render / AI Relight

### 4.1 Three.js Path Tracing (In-Browser Realistic Preview)

| Feature | Details |
|---------|---------|
| **Package** | `three-gpu-pathtracer` (npm) |
| **GitHub** | https://github.com/gkjohnson/three-gpu-pathtracer |
| **React wrapper** | `@react-three/gpu-pathtracer` (npm) |
| **Tech** | WebGL 2 + BVH acceleration (three-mesh-bvh) |
| **Quality** | Near-photorealistic with progressive refinement |
| **Requirements** | Decent GPU; progressive rendering (starts noisy, refines) |

```javascript
import { PathTracer } from 'three-gpu-pathtracer';

const pathTracer = new PathTracer(renderer);
pathTracer.tiles.set(2, 2); // render in tiles for performance
pathTracer.renderSample();  // call per frame for progressive refinement
```

**Use case in our tool:** After configuring lighting (Step 3), render a high-quality preview using path tracing. Progressive refinement means users see a quick noisy preview first, then it refines over 5-15 seconds.

### 4.2 IC-Light (Primary AI Relight - Open Source)

| Feature | Details |
|---------|---------|
| **GitHub** | https://github.com/lllyasviel/IC-Light |
| **Author** | Lvmin Zhang (creator of ControlNet) |
| **Paper** | "Scaling In-the-Wild Training for Diffusion-based Illumination Harmonization" (ICLR 2025) |
| **Models** | Text-conditioned relight, Background-conditioned relight |
| **V2** | Flux-based, 16ch VAE, native high resolution |
| **HuggingFace** | https://huggingface.co/lllyasviel/ic-light |
| **V2 Demo** | https://huggingface.co/spaces/lllyasviel/iclight-v2 |

**Model Files:**
- `iclight_sd15_fc.safetensors` - Default text-conditioned relighting
- `iclight_sd15_fcon.safetensors` - Offset noise variant
- `iclight_sd15_fbc.safetensors` - Background-conditioned (text + foreground + background)

**Lighting Preferences (Directions):**
- Left, Right, Top, Bottom (controlled via initial latent noise pattern)

**Deployment Options:**

| Method | How | Complexity |
|--------|-----|------------|
| **Gradio (built-in)** | `python gradio_demo.py` -- auto-generates API endpoints | Low |
| **ComfyUI Nodes** | Use kijai/ComfyUI-IC-Light or huchenlei/ComfyUI-IC-Light-Native | Medium |
| **FastAPI wrapper** | Load model in Python, expose REST endpoint via FastAPI | Medium |
| **HuggingFace Spaces** | V2 demo hosted; can access via API | Low |
| **RunPod/Replicate** | Deploy on cloud GPU; scale on demand | Medium |

**ComfyUI Integration (Recommended for our pipeline):**
- Custom node: https://github.com/kijai/ComfyUI-IC-Light (by Kijai, most popular)
- Native nodes: https://comfy.icu/extension/huchenlei__ComfyUI-IC-Light-Native
- Workflow tutorials:
  - https://www.youtube.com/watch?v=sMMYSmDHAY8 (IC-Light for product photography)
  - https://www.youtube.com/watch?v=E7ON1CTmQwQ (IC-Light nodes in ComfyUI)

**IMPORTANT NOTE from author:** "iclightai dot com" is a scam website with no affiliation. The only official IC-Light is the GitHub repo.

### 4.3 Photoroom API - AI Relight (Commercial SaaS)

| Feature | Details |
|---------|---------|
| **Docs** | https://docs.photoroom.com/image-editing-api-plus-plan/ai-relight |
| **API Endpoint** | `POST https://image-api.photoroom.com/v2/edit` |
| **Auth** | API key via `x-api-key` header |
| **Modes** | `ai.auto` (automatic), `ai.preserve-hue-and-saturation` (color-accurate) |
| **Max Resolution** | 3500x3500 pixels |
| **Code Samples** | https://github.com/Photoroom/api-code-samples |

**API Call Example:**
```bash
curl --request POST \
  --url https://image-api.photoroom.com/v2/edit \
  --header 'x-api-key: YOUR_API_KEY' \
  --form imageFile=@/path/to/image.jpg \
  --form referenceBox=originalImage \
  --form maxWidth=2000 \
  --form maxHeight=2000 \
  --form removeBackground=false \
  --form lighting.mode=ai.auto \
  --output relighted.png
```

**Pricing:**
| Plan | Monthly Cost | AI Relight Access | Notes |
|------|-------------|-------------------|-------|
| Basic | ~$20/mo | No | Background removal only |
| Plus | ~$100/mo | Yes | Full image editing suite |
| Enterprise | Custom | Yes | Volume pricing |

**Limitation:** Only automatic relight correction (not directional control). Cannot specify "light from left at 45 degrees." Good for correcting exposure, not for creative lighting simulation.

### 4.4 BRIA AI - Relight API (Commercial SaaS)

| Feature | Details |
|---------|---------|
| **Website** | https://bria.ai/ |
| **Pricing page** | https://bria.ai/pricing |
| **Integration** | REST API, MCP, ComfyUI, Embedded iFrame, Figma |
| **Data** | All models trained on fully licensed datasets (commercially safe) |

**Pricing Tiers:**

| Plan | Throughput | Features | Notes |
|------|-----------|----------|-------|
| **Free Trial** | 10 actions/min | 14 days free | All API services included |
| **Development** | 60 actions/min | Pay-as-you-go per API call | Standard indemnification |
| **Business** | 150 actions/min | Volume pricing, live video | Full IP & Privacy indemnity |
| **Enterprise** | Custom | On-prem / private cloud deployment | Source code + model weights available |

**AWS Marketplace:** Also available on AWS Marketplace (~$120K enterprise tier).

**Segmind (third-party):** BRIA models also available via https://www.segmind.com/ with transparent pay-per-call pricing.

**Key advantage over Photoroom:** BRIA's relight API may offer more directional/parameter control. Licensed data means commercially safe for production use.

### 4.5 Render Strategy Recommendation

```
For QUICK PREVIEW (instant feedback):
  --> Three.js real-time PBR rendering (seconds)
  --> Show approximate light positions, shadows, colors

For HIGH-QUALITY PREVIEW (5-15 seconds):
  --> Three.js GPU Path Tracer (progressive refinement)
  --> Near-photorealistic quality in-browser

For FINAL OUTPUT (photography-quality, 10-30 seconds):
  --> IC-Light via ComfyUI (server-side GPU)
  --> AI relight with text/background conditioning
  --> OR: Blender headless render with Cycles path tracing

For EXISTING PHOTO RELIGHTING:
  --> Photoroom API (simple auto-correct, $0.10/image)
  --> OR: BRIA AI API (parameterized relight, pay-per-use)
  --> OR: IC-Light self-hosted (most control, GPU cost only)
```

---

## ComfyUI as Orchestration Layer

### 5.1 Can ComfyUI Be Self-Hosted as a Backend Service?

**Yes.** ComfyUI natively supports headless/API operation.

**GitHub:** https://github.com/comfyanonymous/ComfyUI

**Key API Endpoints (built-in):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Queue a workflow for execution (returns `prompt_id`) |
| `/history/{prompt_id}` | GET | Get execution status and results |
| `/queue` | GET | View current queue |
| `/interrupt` | POST | Cancel current execution |
| `/view` | GET | Retrieve generated output images |
| `/upload/image` | POST | Upload input images |

**How to get workflow JSON:** Design workflow in ComfyUI GUI, then use "Save (API Format)" button to export the JSON.

**Communication pattern:**
- REST for queuing (`POST /prompt`)
- WebSocket for progress/results (real-time updates)
- Poll `/history/{prompt_id}` for completion

**Launch for production:**
```bash
python main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch
```

Sources:
- Official docs: https://docs.comfy.org/development/comfyui-server/comms_routes
- Complete guide: https://www.viewcomfy.com/blog/building-a-production-ready-comfyui-api
- WebSocket guide: https://9elements.com/blog/hosting-a-comfyui-workflow-via-api/

### 5.2 ComfyUI Deployment Platforms

| Platform | Type | Key Feature | URL |
|----------|------|-------------|-----|
| **ComfyDeploy** | Cloud SaaS | One-click production API; "Vercel for AI workflows" | https://www.comfydeploy.com/ |
| **comfy-deploy (open source)** | Self-hosted | Open-source extension for deploying workflows as APIs | https://github.com/ihmily/comfy-deploy |
| **BentoML + ComfyUI** | Framework | Enterprise-grade ML serving with ComfyUI support | https://docs.bentoml.com/en/latest/examples/comfyui.html |
| **RunPod Serverless** | Cloud GPU | Serverless API deployment; pay-per-use GPU | https://www.runpod.io/ |
| **Salad Technologies** | Cloud GPU | ComfyUI API wrapper for scalable deployment | https://github.com/SaladTechnologies/comfyui-api |
| **Docker** | Self-hosted | Containerized ComfyUI with all dependencies | Community Docker images available |

**Recommended for production:** ComfyDeploy (easiest) or RunPod Serverless (most cost-effective for variable load).

### 5.3 ComfyUI Workflow for Our Pipeline

The complete pipeline as a ComfyUI workflow:

```
Step 1: Scene Generation
  [Checkpoint Loader (Juggernaut XL)]
      --> [LoRA Loader (Studio Lighting)]
          --> [CLIP Text Encode: "photography studio, seamless gray backdrop"]
              --> [KSampler] --> [VAE Decode] --> scene_background.png

Step 2: 3D Model Composite (via Three.js, not ComfyUI)
  Three.js renders mannequin with transparent background
  Output: mannequin_alpha.png

Step 3: Lighting Configuration (via Three.js)
  Three.js renders lit mannequin based on parameters
  Output: lit_mannequin.png

Step 4: AI Relight via IC-Light
  [Load Image: lit_mannequin.png]
      --> [IC-Light Relight Node (kijai)]
          --> [Text: "warm studio lighting from left, softbox"]
              --> [KSampler] --> [VAE Decode]
                  --> [Composite over scene_background.png]
                      --> final_output.png
```

**Alternatively, skip Three.js rendering and do everything in ComfyUI:**
```
[Scene Generation] --> [IC-Light Background-Conditioned Relight]
                          --> Subject image relit to match scene lighting
                              --> final_output.png
```

### 5.4 Exposing ComfyUI as an API (Pattern)

```python
# FastAPI wrapper around ComfyUI
from fastapi import FastAPI, UploadFile
import requests, json, websockets, asyncio

app = FastAPI()
COMFYUI_URL = "http://comfyui-server:8188"

@app.post("/api/generate-lighting-preview")
async def generate_lighting_preview(
    scene_prompt: str,
    lighting_preset: str,
    light_angle: float,
    light_intensity: float,
    color_temperature: int,
    subject_image: UploadFile
):
    # 1. Load workflow template
    with open("workflows/lighting_preview.json") as f:
        workflow = json.load(f)

    # 2. Inject parameters
    workflow["6"]["inputs"]["text"] = scene_prompt
    workflow["10"]["inputs"]["lighting_preference"] = lighting_preset
    # ... inject all parameters

    # 3. Queue workflow
    async with websockets.connect(f"ws://{COMFYUI_URL}/ws") as ws:
        response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow}
        )
        prompt_id = response.json()["prompt_id"]

        # 4. Wait for completion via WebSocket
        while True:
            msg = await ws.recv()
            if msg contains completion for prompt_id:
                break

    # 5. Retrieve result
    result = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
    image_url = result.json()["outputs"]["9"]["images"][0]
    return {"image_url": f"{COMFYUI_URL}/view?filename={image_url}"}
```

---

## Recommended Tech Stack Summary

### Per-Step Technology Choices

| Step | Technology | Specific Choice | Cost | Rationale |
|------|-----------|-----------------|------|-----------|
| **Step 1** | AI Scene Gen | Juggernaut XL + ControlNet + LoRA via ComfyUI | Free (GPU infra) | Best SDXL photorealism; Controllable via parameters |
| **Step 2** | 3D Model | SMPL-X (parameter-driven) + pre-made GLB mannequins + Mixamo pose library | Free | Parameter-driven body shape/pose matches our workflow |
| **Step 2** | Avatar (user) | Avaturn API or Avatar SDK | Pay-per-use | If selfie-to-avatar needed; RPM is sunsetting |
| **Step 3** | Lighting Config | Three.js RectAreaLight + IESSpotLight + preset library | Free | Full PBR in browser; IES profiles for real-world lights |
| **Step 4** | Quick Preview | Three.js real-time PBR | Free | Instant feedback on lighting changes |
| **Step 4** | HQ Preview | three-gpu-pathtracer | Free | Progressive photorealistic rendering in browser |
| **Step 4** | AI Relight | IC-Light via ComfyUI | Free (GPU infra) | Best open-source relight; by ControlNet author |
| **Step 4** | Commercial Relight | Photoroom API or BRIA AI API | $0.02-0.10/image | For simple auto-correction fallback |
| **Orchestration** | Pipeline | ComfyUI (self-hosted) + ComfyDeploy or RunPod | GPU cost | Connects all AI steps; production API |

### Architecture Diagram

```
[Web Frontend - React + Three.js]
    |
    |--- Scene parameters (prompt, style)
    |--- Model parameters (body shape, pose)
    |--- Lighting parameters (preset, angle, intensity, color temp)
    |
    v
[API Server - FastAPI/Node.js]
    |
    |--- Quick Preview: Three.js PBR (client-side)
    |--- HQ Preview: three-gpu-pathtracer (client-side)
    |
    |--- AI Pipeline: ComfyUI API
    |       |
    |       |-- Step 1: Scene generation (Juggernaut XL + LoRA)
    |       |-- Step 2: Model composite (pre-rendered from Three.js)
    |       |-- Step 4: IC-Light relight (text/background conditioned)
    |
    |--- Commercial API fallback:
            Photoroom API / BRIA AI API (for simple relighting)
```

### Key npm Packages

```json
{
  "dependencies": {
    "three": "^0.170.0",
    "three-gpu-pathtracer": "^0.0.19",
    "@react-three/fiber": "^8.x",
    "@react-three/drei": "^9.x",
    "@react-three/gpu-pathtracer": "^0.0.4",
    "gltf-transform": "^4.x"
  }
}
```

### Key GitHub Repos

| Repo | Purpose |
|------|---------|
| https://github.com/comfyanonymous/ComfyUI | Orchestration layer |
| https://github.com/lllyasviel/IC-Light | AI relighting |
| https://github.com/kijai/ComfyUI-IC-Light | IC-Light ComfyUI integration |
| https://github.com/huchenlei/ComfyUI-IC-Light-Native | Native IC-Light for ComfyUI |
| https://github.com/gkjohnson/three-gpu-pathtracer | Three.js path tracing |
| https://github.com/vchoutas/smplx | SMPL-X body model |
| https://github.com/ihmily/comfy-deploy | Deploy ComfyUI workflows as APIs |
| https://github.com/Photoroom/api-code-samples | Photoroom API integration examples |

### Key API Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| ComfyUI | `POST http://host:8188/prompt` | Queue workflow for execution |
| ComfyUI | `GET http://host:8188/history/{id}` | Check execution status |
| ComfyUI | `GET http://host:8188/view?filename=X` | Retrieve output image |
| Photoroom | `POST https://image-api.photoroom.com/v2/edit` | AI relight image |
| Avatar SDK | REST API (check docs) | Generate 3D avatar from selfie |
| Avaturn | REST API (check docs) | Generate RPM-compatible avatar |
| BRIA AI | REST API (check docs.bria.ai) | Relight and image editing |

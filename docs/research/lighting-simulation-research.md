# Photography Lighting Simulation & 3D Scene Building Tools - Research Report

Date: 2026-05-26
Context: Photo Studio R&D Workbench - Lighting Simulation Capabilities

---

## Table of Contents

1. [Commercial Desktop Software](#1-commercial-desktop-software)
2. [3D Rendering Engines for Web Integration](#2-3d-rendering-engines-for-web-integration)
3. [Open Source Projects](#3-open-source-projects)
4. [AI-Based Lighting Simulation & Neural Relighting](#4-ai-based-lighting-simulation--neural-relighting)
5. [Commercial APIs / SaaS Services](#5-commercial-apis--saas-services)
6. [Virtual Photography Studio Platforms](#6-virtual-photography-studio-platforms)
7. [Comparison Matrix & Recommendations](#7-comparison-matrix--recommendations)

---

## 1. Commercial Desktop Software

### 1.1 elixxier set.a.light 3D V3

**Website:** https://www.elixxier.com/en/set-a-light-3d/

**What it is:**
The industry-standard photography lighting pre-visualization tool. A physics-based 3D virtual photo studio that lets photographers plan lighting setups, camera angles, and entire scenes before stepping on set. V3 (released late 2025) is a complete rewrite with a new light engine.

**Key Features:**
- 90+ real-world light sources (strobes, speedlights, continuous lights from Arri, Aputure, Nanlite, KinoFlo, etc.)
- 90+ light modifiers (softboxes, reflectors, snoots, umbrellas)
- Realistic camera system with adjustable aperture, ISO, focal length, DOF
- Sun simulation with real-world location/date/time positioning
- HDRI environment maps for outdoor/indoor scenes
- Volumetric fog rendering
- Animation tool (camera moves, light changes, character animation)
- 10,000+ community-shared lighting setups
- Production-ready blueprint export (PDF/JPG with positions, distances, settings)
- 4K rendering output

**Pricing (Lifetime License, No Subscription):**
| Edition | Target | Features | Estimated Price |
|---------|--------|----------|----------------|
| BASIC | Beginners | Up to 5 strobes, Full HD export, essential tools | ~69-89 EUR |
| STUDIO | Photographers | Unlimited strobes, 4K export, light meter, all photo features | ~199-249 EUR |
| CINEMA | Filmmakers | All STUDIO + Animation tool, MP4 export, 3D importer, continuous lights | Higher tier |

**Add-ons (for BASIC/STUDIO):**
- 3D Importer (import OBJ, FBX, DAE files)
- Animation Tool + MP4 export

**License model:** Lifetime license, free updates for 1 year, optional renewal after that. Installable on up to 3 computers (not simultaneous use). Education discount available.

**API/SDK/Integration:** NONE. This is a standalone desktop application (Windows + macOS). No public API, SDK, or developer program. No web integration path. Would require direct contact with elixxier for any partnership/custom integration.

**Integration Feasibility for Web Workbench:** LOW. No API available. Would need to explore:
- Partnership/licensing discussions with elixxier
- Reverse-engineering their file formats for import/export
- Running the desktop app server-side (impractical)

---

## 2. 3D Rendering Engines for Web Integration

### 2.1 Three.js + PBR (Recommended for Web Workbench)

**What it is:** The leading JavaScript library for 3D rendering in the browser using WebGL. Supports Physically Based Rendering (PBR) with `MeshStandardMaterial` and `MeshPhysicalMaterial`.

**Lighting Simulation Capabilities:**
- Multiple light types: DirectionalLight, PointLight, SpotLight, RectAreaLight, AmbientLight, HemisphereLight
- Real-time shadow mapping (PCFSoftShadowMap, VSMShadowMap)
- PBR material system (metalness, roughness, clearcoat, transmission, etc.)
- HDR environment maps for realistic ambient lighting and reflections
- Camera parameters: FOV, aperture (DOF via post-processing), focus distance
- Post-processing: tone mapping, bloom, color grading

**Key Libraries:**
- [three-gpu-pathtracer](https://github.com/gkjohnson/three-gpu-pathtracer) - Modular GPU path tracing extension with BVH acceleration
- [THREE.js-PathTracing-Renderer](https://github.com/erichlof/THREE.js-PathTracing-Renderer) - Real-time path tracing with global illumination, photography-relevant camera controls (FOV, aperture, focus distance)

**Integration Feasibility:** HIGH. Runs natively in the browser. Full JavaScript API. Extensive ecosystem. Can be integrated into any web application (React, Vue, etc.).

**Limitations:** Real-time rendering quality is good but not photorealistic without path tracing (which is GPU-intensive). No built-in photography-specific equipment models.

---

### 2.2 Blender Python API (Headless Rendering Backend)

**Website:** https://docs.blender.org/api/current/

**What it is:** Blender's comprehensive Python API (bpy) allows programmatic control of the entire 3D pipeline - scene creation, lighting setup, material assignment, and rendering. Can run headless (without GUI) on a server.

**Lighting Simulation Capabilities:**
- Full physically-based rendering with Cycles (path tracing)
- Real-world light units (watts, lumens)
- IES light profiles for accurate real-world light fixtures
- PBR materials with full node-based shader system
- Camera simulation with real lens parameters
- HDRI environment lighting
- Volumetric lighting, caustics, SSS

**Integration Approach:**
```
Web Frontend --> API Server --> Blender Python Script --> Render --> Return Image
```
- Run Blender in headless mode (`blender --background --python script.py`)
- Create/modify scenes via Python API
- Render to file or stdout
- Return rendered image via HTTP response

**Example Code Pattern:**
```python
import bpy
# Create light
light_data = bpy.data.lights.new(name="StudioLight", type='AREA')
light_data.energy = 500
light_data.size = 1.0
light_object = bpy.data.objects.new(name="StudioLight", object_data=light_data)
bpy.context.collection.objects.link(light_object)
light_object.location = (2, 2, 3)
# Render
bpy.ops.render.render(write_still=True)
```

**Integration Feasibility:** MEDIUM-HIGH. Requires server-side GPU infrastructure. Python scripting is well-documented. Blender is free and open source. Good for batch rendering and high-quality output.

**Limitations:** Rendering is not real-time (seconds to minutes per frame). Requires server infrastructure with GPU. Licensing is GPL (requires careful consideration for commercial use).

---

### 2.3 Unreal Engine + Pixel Streaming

**Website:** https://dev.epicgames.com/documentation/unreal-engine/getting-started-with-pixel-streaming-in-unreal-engine

**What it is:** Unreal Engine 5's Pixel Streaming technology allows running a UE application on a cloud server and streaming the rendered output to browsers via WebRTC + WebSockets. Two-way communication is supported - web frontends can send data to UE Blueprints.

**Lighting Simulation Capabilities:**
- Lumen global illumination (real-time GI)
- Nanite virtualized geometry
- Physically accurate lighting with real-world units
- Virtual shadow maps
- HDRI environments
- Path tracing mode (for highest quality)

**Integration Approach:**
```
Web Frontend <--WebRTC--> Signaling Server <---> UE5 Application (Cloud GPU)
                 <--> WebSocket <-->
```

**Key Resources:**
- [AWS Deployment Guide](https://aws.amazon.com/blogs/gametech/deploy-unreal-engines-pixel-streaming-at-scale-on-aws/)
- [Docker Container Support](https://unrealcontainers.com/docs/use-cases/pixel-streaming)
- [ZeroLight OmniStream](https://de.zerolight.com/omnistream/unreal-engine-pixel-streaming) - Commercial pixel streaming infrastructure

**Integration Feasibility:** MEDIUM. Highest visual quality. Significant infrastructure requirements. Ongoing cloud GPU costs. Complex setup but well-documented.

---

## 3. Open Source Projects

### 3.1 Mitsuba 3 (Physically Based Renderer)

**Website:** https://www.mitsuba-renderer.org/
**GitHub:** https://github.com/mitsuba-renderer

**What it is:** A research-oriented, retargetable forward and inverse renderer written in C++17 with Python bindings. Built on the Dr.Jit JIT compiler. Supports differentiable rendering.

**Key Features:**
- Physically accurate light transport simulation
- Forward and inverse (differentiable) rendering
- 100+ plugins for materials, integrators, emitters
- Python API for custom rendering pipelines
- XML scene description format
- Can reconstruct physical models from photographs

**Integration Feasibility:** MEDIUM. Excellent for server-side rendering. Python bindings enable web backend integration (Flask/FastAPI). No built-in web UI. Research-focused but production-capable.

---

### 3.2 PBRT (Physically Based Rendering: From Theory to Implementation)

**Website:** https://pbrt.org/
**GitHub:** https://github.com/mmp/pbrt-v4

**What it is:** The gold-standard reference renderer for physically based rendering. Full source code available. Used as the basis for teaching and research.

**Integration Feasibility:** LOW for production use. Primarily a research/educational tool. No Python bindings out of the box. Would need custom wrapping for API integration.

---

### 3.3 Three.js Path Tracing Renderers

#### THREE.js-PathTracing-Renderer
**GitHub:** https://github.com/erichlof/THREE.js-PathTracing-Renderer

Real-time path tracing with global illumination and progressive rendering. Supports photography-relevant camera controls (FOV, aperture, focus distance).

#### three-gpu-pathtracer
**GitHub:** https://github.com/gkjohnson/three-gpu-pathtracer

Modular, BVH-accelerated GPU path tracing extension for Three.js. Actively maintained.

**Integration Feasibility:** HIGH. Runs in the browser. Direct integration with Three.js scenes. Progressive refinement allows interactive use.

---

### 3.4 Blender Addons for Photography Lighting

#### LeoMoon LightStudio
**GitHub:** https://github.com/leomoon-studios/leomoon-lightstudio

Advanced lighting system plugin for Blender. Provides an easy interface for setting up studio lighting.

#### Portrait Studio Lighting
**GitHub:** https://github.com/Rithvik-Kadiresan/Portrait-Studio-Lighting

Blender addon that sets up portrait-style lighting (rim light, key light, fill) with a single hotkey.

**Integration Feasibility:** LOW directly. But can inform the design of lighting preset systems in the workbench.

---

### 3.5 ComfyUI ReLight

**GitHub:** https://github.com/EnragedAntelope/comfyui-relight

ComfyUI custom node for professional-grade image relighting. Can create dramatic shadows, natural window lighting, and more via AI diffusion models.

**Integration Feasibility:** MEDIUM. Can be integrated as a backend service. Requires GPU infrastructure. Produces AI-based relighting of existing photos (not real-time 3D simulation).

---

## 4. AI-Based Lighting Simulation & Neural Relighting

### 4.1 Research Landscape Overview

**Awesome-Relighting (Comprehensive Collection)**
**GitHub:** https://github.com/tandaily/Awesome-Relighting

This is the definitive curated list of neural relighting research, containing 100+ papers organized by category (image, video, 3D face/avatar/human). Updated regularly.

**GitHub Topics - Relighting:** https://github.com/topics/relighting (22+ open source repos)

---

### 4.2 Key Open Source AI Relighting Models

| Project | Paper | Code Available | Focus |
|---------|-------|----------------|-------|
| DPR (Deep Single-Image Portrait Relighting) | ICCV 2019 | https://github.com/zhopper/DPR | Portrait relighting from single image |
| Total Relighting | SIGGRAPH 2021 | Project page only | Portrait relighting + background replacement (Google) |
| SwitchLight | CVPR 2024 | Paper only | Physics-driven architecture for portrait relighting |
| IC-Light | - | https://github.com/lllyasviel/IC-Light | Image relighting via diffusion (by ControlNet author) |
| LBM (Latent Bridge Matching) | ICCV 2025 | https://github.com/gojasper/LBM | Fast image-to-image translation for relighting |
| Neural Gaffer | NeurIPS 2024 | https://github.com/Haian-Jin/Neural_Gaffer | Relighting any object via diffusion |
| PortraitRelighting | CVPR 2024 | https://github.com/GhostCai/PortraitRelighting | Real-time 3D-aware NeRF video relighting |
| DiFaReli | ICCV 2023 | https://github.com/diffusion-face-relighting/difareli_code | Diffusion face relighting |
| RGB-X | SIGGRAPH 2024 | https://github.com/zheng95z/rgbx | Material and lighting-aware diffusion decomposition |

---

### 4.3 Notable Recent Research (2025)

| Paper | Venue | Key Innovation |
|-------|-------|---------------|
| SynthLight | CVPR 2025 | Diffusion-based portrait relighting as re-rendering |
| Physically Controllable Relighting | SIGGRAPH 2025 | Self-supervised in-the-wild relighting with physical control |
| LightLab | SIGGRAPH 2025 | Controlling light sources in images with diffusion models |
| IntrinsicEdit | SIGGRAPH 2025 | Precise generative image manipulation in intrinsic space |
| ROGR | NeurIPS 2025 | Relightable 3D objects using generative relighting |
| DreamLight | NeurIPS 2025 | Harmonious and consistent image relighting |
| SFU 3D Photo Relighting | Aug 2025 | 3D photo relighting with remarkable realism |

---

### 4.4 Practical AI Relighting Software Products

| Tool | Type | URL | Notes |
|------|------|-----|-------|
| IC-Light | Open Source (GitHub) | https://github.com/lllyasviel/IC-Light | By ControlNet author. Diffusion-based. HuggingFace Spaces available. |
| Flux Kontext Relight | Open (HuggingFace) | https://huggingface.co/spaces/kontext-community/kontext-relight | Community implementation |
| FreeLighting | Open (HuggingFace) | https://huggingface.co/spaces/wulongmetac/FreeLighting | Free lighting tool |
| LBM Relighting | Open (HuggingFace) | https://huggingface.co/spaces/jasperai/LBM_relighting | Fast latent bridge matching |
| SwitchLight 2.0 | Commercial (Beeble) | https://app.beeble.ai/ | Professional portrait relighting tool |
| GoStudio AI | Commercial (Free tier) | https://www.gostudio.ai/relighting | Free web-based AI relighting tool |
| StudioLights | iOS App | App Store | 3D photo relighting on mobile |

---

## 5. Commercial APIs / SaaS Services

### 5.1 Photoroom API - AI Relight

**Website:** https://www.photoroom.com/api
**Documentation:** https://docs.photoroom.com/image-editing-api-plus-plan/ai-relight

**Features:**
- Correct over/under-exposure via AI relighting
- Stronger color accuracy mode available
- REST API with OpenAPI specification
- Part of a broader image editing API suite (background removal, generation, etc.)

**Pricing:**
| Plan | Monthly Cost | Cost per Image | AI Relight Access |
|------|-------------|----------------|-------------------|
| Basic | $20/mo | ~$0.02 | No |
| Plus | $100/mo | ~$0.10 | Yes |
| Enterprise | Custom | Custom | Yes |

**Integration Feasibility:** HIGH. Well-documented REST API. Easy web integration. Designed for product/e-commerce photography.

---

### 5.2 BRIA AI - Relight API

**Website:** https://bria.ai
**Documentation:** https://docs.bria.ai/image-editing/v2-endpoints/relight

**Features:**
- Relight images with manual/automatic mask support
- Part of comprehensive visual AI platform
- REST API

**Pricing:** Usage-based (per image). Check https://bria.ai/pricing for current rates.

**Integration Feasibility:** HIGH. REST API designed for developer integration.

---

### 5.3 Claid.ai - Light Correction API

**Website:** https://claid.ai/api-products/correct-light

**Features:**
- AI-powered light and color correction for product photos
- REST API

**Integration Feasibility:** HIGH. Simple API for automated light correction.

---

### 5.4 SwitchLight API (Beeble)

**Website:** https://www.switchlight.beeble.ai/ or https://app.beeble.ai/

**Features:**
- AI portrait relighting
- Depth and normal estimation from single image
- HDRI-based environment lighting
- Available as DaVinci Resolve plugin
- API access for developers

**Integration Feasibility:** MEDIUM-HIGH. API available. Check website for current pricing and documentation.

---

### 5.5 3D AI Studio API

**Website:** https://www.3daistudio.com/Platform

**Features:**
- REST API for 3D model generation, texturing, and image editing
- Developer platform for programmatic access

**Integration Feasibility:** MEDIUM. Newer platform. Worth evaluating for 3D asset generation.

---

## 6. Virtual Photography Studio Platforms

### 6.1 MetaShoot / Atlux (Unreal Engine Plugin)

**Website:** https://atlux.ai (formerly https://metashoot.vinzi.xyz/)
**Marketplace:** https://www.unrealengine.com/marketplace/en-US/product/metashoot

**What it is:** A photo studio digital twin plugin for Unreal Engine. Enables one-click photorealistic rendering of product turntables and visualizations inside UE5. Rebranded as Atlux.

**Integration Feasibility:** LOW as standalone. Requires Unreal Engine. Could be combined with Pixel Streaming for web delivery. Significant infrastructure.

---

### 6.2 Adobe Substance 3D Stager

**Website:** https://www.adobe.com/products/substance3d/discover/virtual-photography.html

**What it is:** Virtual photo studio for staging 3D scenes. Part of Adobe's 3D ecosystem. Desktop application.

**Integration Feasibility:** LOW. No public API. Adobe Creative Cloud subscription required.

---

### 6.3 Modelry

**Website:** https://www.modelry.ai/virtual-photography

**What it is:** 3D virtual product photography platform. Up to 10x cheaper than traditional product photos. Platform for 3D-based virtual photography at scale.

**Integration Feasibility:** MEDIUM. Enterprise-focused. Contact for API availability.

---

### 6.4 Nextech3D.ai

**Website:** https://www.nextechar.com/platform/virtual-product-photography

**What it is:** ARitize3D platform generates packshots, lifestyle scenes, 360-degree spins from 3D models.

**Integration Feasibility:** MEDIUM. Enterprise-focused SaaS.

---

## 7. Comparison Matrix & Recommendations

### 7.1 Integration Feasibility for Web Workbench

| Category | Tool/Service | Visual Quality | Web Integration | Cost | Effort | Recommendation |
|----------|-------------|---------------|----------------|------|--------|---------------|
| **Commercial Desktop** | set.a.light 3D V3 | Excellent | None (no API) | ~200 EUR one-time | N/A | Reference design only |
| **Web 3D Engine** | Three.js + PBR | Good | Excellent (native browser) | Free | Medium | **PRIMARY RECOMMENDATION** |
| **Web 3D Engine** | Three.js + GPU Pathtracer | Very Good | Excellent | Free | Medium-High | For high-quality renders |
| **Server Renderer** | Blender headless | Excellent | Via API wrapper | Free (infrastructure cost) | Medium | For batch/export renders |
| **Server Renderer** | Unreal Engine + Pixel Streaming | Excellent | Good (WebRTC) | Free (high infra cost) | High | Premium tier option |
| **Server Renderer** | Mitsuba 3 | Excellent | Via Python API | Free | High | Research/specialized |
| **AI Relighting** | Photoroom API | Good | Excellent (REST) | $100/mo+ | Low | Quick integration |
| **AI Relighting** | BRIA AI API | Good | Excellent (REST) | Pay-per-use | Low | Quick integration |
| **AI Relighting** | IC-Light (open source) | Good | Self-hosted | Free (GPU cost) | Medium | Best open source AI option |
| **AI Relighting** | SwitchLight (Beeble) | Very Good | API available | Contact | Medium | Professional option |
| **Virtual Studio** | MetaShoot/Atlux | Excellent | Via Pixel Streaming | UE Marketplace | High | UE-based approach |

---

### 7.2 Recommended Architecture for Photo Studio R&D Workbench

Based on this research, a layered approach is recommended:

**Layer 1: Real-Time Preview (Browser)**
- Three.js with PBR materials
- Pre-built photography equipment models (lights, modifiers, stands)
- Real-time shadow and reflection preview
- Interactive camera with photography parameters
- Lighting preset library (inspired by set.a.light 3D's 10,000+ setups)

**Layer 2: High-Quality Rendering (Server)**
- Blender headless rendering for production-quality output
- OR three-gpu-pathtracer for in-browser progressive rendering
- HDR environment map support

**Layer 3: AI Relighting (API)**
- Photoroom API or BRIA AI for quick relighting of uploaded photos
- IC-Light self-hosted for custom AI relighting pipeline
- Integration with diffusion models for creative lighting exploration

**Layer 4: Lighting Knowledge Base**
- Curated lighting setup library (key/fill/rim, butterfly, Rembrandt, split, loop, etc.)
- Equipment database with real-world specifications
- Export production-ready blueprints (PDF with positions and settings)

---

### 7.3 Key Takeaways

1. **No single tool provides everything needed.** set.a.light 3D is the best reference for features but has no API. A custom web solution is necessary.

2. **Three.js is the strongest foundation.** It runs natively in the browser, supports PBR, has path tracing extensions, and has a massive ecosystem. The three-gpu-pathtracer project provides near-photorealistic quality.

3. **AI relighting APIs are mature and affordable.** Photoroom ($0.10/image) and BRIA AI offer ready-to-use REST APIs. IC-Light provides a strong open-source alternative.

4. **The neural relighting field is exploding.** The Awesome-Relighting GitHub repo lists 100+ papers with code. Key models like IC-Light, LBM, and Neural Gaffer are available for self-hosting.

5. **Server-side rendering via Blender** is practical for batch rendering and high-quality output, but requires GPU infrastructure.

6. **Unreal Engine + Pixel Streaming** offers the highest visual quality but has the highest infrastructure complexity and cost. Best reserved for a premium/enterprise tier.

---

## References & Links

### Commercial Software
- [elixxier set.a.light 3D](https://www.elixxier.com/en/set-a-light-3d/)
- [elixxier Pricing](https://www.elixxier.com/en/pricing/)
- [Adobe Substance 3D Stager](https://www.adobe.com/products/substance3d/discover/virtual-photography.html)

### 3D Engines & Libraries
- [Three.js](https://threejs.org/)
- [Three.js PBR Guide](https://discoverthreejs.com/book/first-steps/physically-based-rendering/)
- [three-gpu-pathtracer](https://github.com/gkjohnson/three-gpu-pathtracer)
- [THREE.js-PathTracing-Renderer](https://github.com/erichlof/THREE.js-PathTracing-Renderer)
- [Blender Python API](https://docs.blender.org/api/current/)
- [Unreal Engine Pixel Streaming](https://dev.epicgames.com/documentation/unreal-engine/getting-started-with-pixel-streaming-in-unreal-engine)

### Open Source Renderers
- [Mitsuba 3](https://www.mitsuba-renderer.org/) / [GitHub](https://github.com/mitsuba-renderer)
- [PBRT v4](https://pbrt.org/) / [Book](https://pbr-book.org/)

### AI Relighting
- [Awesome-Relighting](https://github.com/tandaily/Awesome-Relighting) - Comprehensive paper collection
- [IC-Light](https://github.com/lllyasviel/IC-Light) - Open source diffusion-based relighting
- [LBM](https://github.com/gojasper/LBM) - Fast latent bridge matching
- [Neural Gaffer](https://github.com/Haian-Jin/Neural_Gaffer) - Object relighting via diffusion
- [DPR](https://github.com/zhopper/DPR) - Deep portrait relighting
- [SwitchLight (Beeble)](https://www.switchlight.beeble.ai/)
- [Total Relighting (Google)](https://augmentedperception.github.io/total_relighting)

### Commercial APIs
- [Photoroom API](https://www.photoroom.com/api) / [Docs](https://docs.photoroom.com/) / [Pricing](https://www.photoroom.com/api/pricing)
- [BRIA AI](https://bria.ai) / [Docs](https://docs.bria.ai)
- [Claid.ai](https://claid.ai/api-products/correct-light)
- [GoStudio AI](https://www.gostudio.ai/relighting)

### Virtual Studio Platforms
- [MetaShoot / Atlux](https://atlux.ai) / [UE Marketplace](https://www.unrealengine.com/marketplace/en-US/product/metashoot)
- [Modelry](https://www.modelry.ai/virtual-photography)
- [Nextech3D.ai](https://www.nextechar.com/platform/virtual-product-photography)

### Blender Addons
- [LeoMoon LightStudio](https://github.com/leomoon-studios/leomoon-lightstudio)
- [Portrait Studio Lighting](https://github.com/Rithvik-Kadiresan/Portrait-Studio-Lighting)

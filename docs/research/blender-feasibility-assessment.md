# Blender as set.a.light 3D Backend Replacement: Feasibility Assessment

**Date:** 2026-05-26  
**Scope:** Parameter-driven workflow (configure -> render -> view)  
**NOT real-time drag-and-drop**

---

## Executive Summary

Blender CAN serve as a backend replacement for set.a.light 3D for a parameter-driven photography lighting simulation tool. The Python API (`bpy`) provides comprehensive programmatic control over lights, cameras, scene geometry, and the Cycles path tracer produces physically accurate output. There are minor gaps (physical camera ISO/shutter speed is in development, light modifiers require workarounds), but none are blockers.

**Overall verdict: FEASIBLE with minor workarounds.**

---

## 1. Blender Python API (bpy) for Lighting Simulation

### 1.1 Create and position light types programmatically

| Capability | Verdict | API Reference |
|---|---|---|
| Create Area Lights (softboxes) | **YES** | `bpy.types.AreaLight` - `Light.type = 'AREA'` |
| Create Spot Lights | **YES** | `bpy.types.SpotLight` - `Light.type = 'SPOT'` |
| Create Point Lights | **YES** | `bpy.types.PointLight` - `Light.type = 'POINT'` |
| Create Sun Lights | **YES** | `bpy.types.SunLight` - `Light.type = 'SUN'` |
| Position lights in 3D space | **YES** | `bpy.types.Object.location`, `rotation_euler`, `matrix_world` |
| Point lights at target | **YES** | `bpy.ops.object.track_constraint()` or manual rotation |

**Documentation references:**
- https://docs.blender.org/api/current/bpy.types.Light.html
- https://docs.blender.org/api/current/bpy.types.AreaLight.html
- https://docs.blender.org/api/current/bpy.types.SpotLight.html
- https://docs.blender.org/api/current/bpy.types.PointLight.html
- https://docs.blender.org/api/current/bpy.types.SunLight.html

**Key API properties found in documentation:**

```python
# Light base class (bpy.types.Light)
Light.type          # enum: 'POINT', 'SUN', 'SPOT', 'AREA'
Light.color         # mathutils.Color, RGB [0, inf]
Light.temperature   # float [800, 20000] Kelvin
Light.use_temperature  # boolean - use blackbody temperature
Light.exposure      # float [-32, 32] - scales power by 2^exposure
Light.normalize     # boolean - normalize by area for consistent output
Light.diffuse_factor    # float [0, inf]
Light.specular_factor   # float [0, inf]
Light.volume_factor     # float [0, inf]
Light.use_custom_distance  # boolean
Light.cutoff_distance   # float [0, inf]
Light.cycles            # CyclesLightSettings (readonly)

# AreaLight specific
AreaLight.energy    # float - radiant power in Watts
AreaLight.shape     # enum: 'SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE'
AreaLight.size      # float [0, inf] - X dimension
AreaLight.size_y    # float [0, inf] - Y dimension
AreaLight.spread    # float [0, pi] - softbox grid simulation

# SpotLight specific
SpotLight.energy       # float
SpotLight.spot_size    # float [0.017, pi] - cone angle
SpotLight.spot_blend   # float [0, 1] - edge softness
SpotLight.use_square   # boolean - square spot shape

# PointLight specific
PointLight.energy        # float - total radiant power in Watts
PointLight.shadow_soft_size  # float - size for soft shadows

# SunLight specific
SunLight.energy      # float - W/m^2
SunLight.angle       # float [0, pi] - angular diameter
```

### 1.2 Real-world light units

| Capability | Verdict | Notes |
|---|---|---|
| Watts (radiant power) | **YES** | `AreaLight.energy` is in Watts. Point/Spot also use Watts. |
| Lumens/Lux | **PARTIAL** | No direct lumen/lux input, but convertible. Watts are physically based. |
| Color Temperature | **YES** | `Light.temperature` (800K-20000K) + `Light.use_temperature = True` |
| Exposure compensation | **YES** | `Light.exposure` (scales by 2^value) |

**Documentation reference:**  
`Light.temperature`: "Light color temperature in Kelvin" - float in [800, 20000], default 6500.0  
`Light.use_temperature`: "Use blackbody temperature to define a natural light color"

### 1.3 IES light profiles

| Capability | Verdict | API Reference |
|---|---|---|
| Import IES profiles | **YES** | `ShaderNodeTexIES` node in light shader node tree |
| Programmatic IES setup | **YES** | Via `Light.use_nodes = True` + node tree manipulation |
| Pre-built IES libraries | **YES** | 160k+ free IES profiles from community (BlenderArtists) |

**Documentation references:**
- https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/ies.html
- https://docs.blender.org/api/current/bpy.types.ShaderNodeTexIES.html
- https://blendergrid.com/articles/ies-lighting-in-blender

**How to use IES programmatically:**

```python
# Enable node-based light
light_data = bpy.data.lights["MyLight"]
light_data.use_nodes = True
tree = light_data.node_tree

# Add IES texture node
ies_node = tree.nodes.new('ShaderNodeTexIES')
ies_node.ies = "/path/to/light_profile.ies"  # or use .ies file packed

# Connect: IES -> Emission Strength -> Light Output
emission = tree.nodes.get('Emission')
tree.links.new(ies_node.outputs['Fac'], emission.inputs['Strength'])
```

### 1.4 Light modifiers

| Capability | Verdict | Approach |
|---|---|---|
| Grid (honeycomb) | **YES** | `AreaLight.spread` parameter controls beam spread (simulates grid) |
| Snoots/cones | **YES** | `SpotLight` with small `spot_size` + `spot_blend` |
| Barn doors | **WORKAROUND** | Use geometry objects (planes) as light blockers, or shader node masking |
| Gels/color filters | **YES** | `Light.color` or `Light.temperature` + color mixing via node tree |
| Softbox dimensions | **YES** | `AreaLight.size`, `AreaLight.size_y` directly control dimensions |

### 1.5 Light size/shape (softbox simulation)

| Capability | Verdict | API Reference |
|---|---|---|
| Set light dimensions | **YES** | `AreaLight.size` (X), `AreaLight.size_y` (Y) |
| Square softbox | **YES** | `AreaLight.shape = 'SQUARE'` |
| Rectangular softbox | **YES** | `AreaLight.shape = 'RECTANGLE'` |
| Circular (beauty dish) | **YES** | `AreaLight.shape = 'DISK'` |
| Oval (beauty dish) | **YES** | `AreaLight.shape = 'ELLIPSE'` |

---

## 2. Cycles Renderer Capabilities

### 2.1 Physically accurate light falloff

| Capability | Verdict | Notes |
|---|---|---|
| Inverse-square falloff | **YES** | Cycles uses physically correct inverse-square by default |
| Custom falloff | **YES** | `ShaderNodeLightFalloff` node for custom quadratic/linear/constant |
| Real-world intensity | **YES** | Lights use Watt units, physically based in Cycles |

**Documentation references:**
- https://docs.blender.org/manual/en/latest/render/cycles/index.html
- https://blendergrid.com/articles/cycles-physically-correct-brightness
- https://docs.blender.org/api/current/bpy.types.CyclesRenderSettings.html

### 2.2 Volumetric lighting

| Capability | Verdict | Approach |
|---|---|---|
| Fog/haze simulation | **YES** | `ShaderNodeVolumeScatter` + `ShaderNodeVolumeAbsorption` |
| Volumetric light beams | **YES** | Volume scatter in world or mesh volume + spot lights |
| Density control | **YES** | Density parameter on volume scatter node |

### 2.3 Camera parameters

| Capability | Verdict | API Reference |
|---|---|---|
| Focal length | **YES** | `Camera.lens` (mm) |
| Sensor size | **YES** | `Camera.sensor_width`, `Camera.sensor_height` |
| Field of View | **YES** | `Camera.angle` (radians) |
| Depth of Field | **YES** | `CameraDOFSettings.use_dof`, `aperture_fstop`, `focus_distance` |
| Bokeh blades | **YES** | `CameraDOFSettings.aperture_blades` |
| ISO/Shutter Speed | **IN DEVELOPMENT** | PR #154407 adds physical camera; workaround via exposure slider |

**Documentation references:**
- https://docs.blender.org/api/current/bpy.types.Camera.html
- https://docs.blender.org/api/current/bpy.types.CameraDOFSettings.html
- https://blender.stackexchange.com/questions/14745/how-do-i-change-the-focal-length-of-a-camera-with-python

**Physical camera development status:**
- PR #154407 (projects.blender.org): Adds ISO, Shutter Speed, F-Stop, Exposure Compensation natively
- Lukas Stockner talk at Blender Conference 2025: "Bringing Real Cameras to Cycles"
- Currently achievable via Scene exposure (`Scene.render.exposure`) as a workaround

### 2.4 HDRI environment maps

| Capability | Verdict | Approach |
|---|---|---|
| Load HDRI | **YES** | World shader -> `ShaderNodeTexEnvironment` -> Background |
| Ambient lighting | **YES** | HDRI drives world illumination |
| Rotate HDRI | **YES** | `TexMapping` node or `ShaderNodeMapping` rotation |
| Programmatic setup | **YES** | Full node tree API access |

### 2.5 Real-world camera exposure

| Capability | Verdict | Notes |
|---|---|---|
| Exposure control | **YES** | `Scene.render.exposure` (color management) |
| Filmic tone mapping | **YES** | Built-in AgX/Filmic view transform |
| False color view | **YES** | Viewport false color display for luminance analysis |

---

## 3. Headless Rendering (Command Line)

### 3.1 Headless execution

| Capability | Verdict | Notes |
|---|---|---|
| No GUI mode | **YES** | `blender -b` (background mode) |
| Run Python script | **YES** | `blender -b -P script.py` |
| Render specific frame | **YES** | `blender -b file.blend -f 1` |
| Render animation range | **YES** | `blender -b file.blend -s 1 -e 100 -a` |
| Output path | **YES** | `blender -b file.blend -o /path/output_####.png -f 1` |
| Output format | **YES** | `-F PNG`, `-F JPEG`, `-F OPEN_EXR`, etc. |
| Set render engine | **YES** | `-E CYCLES` |

**Key command line arguments:**

```bash
# Complete headless render command
blender -b scene.blend \
  -E CYCLES \
  -P setup_script.py \
  -o /output/frame_####.png \
  -F PNG \
  -f 1

# Render animation frames 1-50
blender -b scene.blend -E CYCLES -s 1 -e 50 -a -o //output/frame_####.png

# Run Python script only (no render)
blender -b -P create_scene.py
```

### 3.2 Docker deployment

| Capability | Verdict | Details |
|---|---|---|
| Docker container | **YES** | `linuxserver/blender`, `nytimes/blender`, custom Ubuntu-based images |
| GPU passthrough | **YES** | `docker run --gpus all --ipc=host` (requires nvidia-container-toolkit) |
| NVIDIA CUDA/OptiX | **YES** | Cycles supports CUDA, OptiX, HIP (AMD), Metal (Apple) |
| CPU-only fallback | **YES** | Works but significantly slower |

**Docker run example:**

```bash
docker run -d \
  --name blender-render \
  --gpus all \
  --ipc=host \
  -v /path/to/projects:/config \
  -v /path/to/output:/output \
  linuxserver/blender \
  blender -b /config/scene.blend -E CYCLES -f 1 \
    -o /output/frame_####.png -F PNG
```

### 3.3 GPU requirements

| GPU Tier | VRAM | Expected Performance (1080p, Cycles) |
|---|---|---|
| NVIDIA RTX 3060 | 12 GB | ~10-30 seconds/frame (simple scene) |
| NVIDIA RTX 4070 | 12 GB | ~5-15 seconds/frame |
| NVIDIA RTX 4090 | 24 GB | ~2-8 seconds/frame |
| NVIDIA A100 | 40/80 GB | ~1-5 seconds/frame |
| CPU only | - | ~60-300 seconds/frame |

### 3.4 Parallel render jobs

| Capability | Verdict | Approach |
|---|---|---|
| Multiple containers | **YES** | Each container renders different frame or different scene |
| Multi-GPU single frame | **YES** | Cycles native multi-GPU tile splitting |
| Render farm manager | **YES** | Flamenco (Blender's own), Royal Render, Deadline |
| Kubernetes orchestration | **YES** | Multiple Blender pods with GPU allocation |

---

## 4. Scene/Camera/Model Control

### 4.1 3D model import

| Format | Verdict | API |
|---|---|---|
| GLB/glTF | **YES** | `bpy.ops.import_scene.gltf(filepath="...")` |
| FBX | **YES** | `bpy.ops.import_scene.fbx(filepath="...")` |
| OBJ | **YES** | `bpy.ops.wm.obj_import(filepath="...")` (Blender 4.0+) |
| STL | **YES** | `bpy.ops.wm.stl_import(filepath="...")` |
| USD | **YES** | `bpy.ops.wm.usd_import(filepath="...")` |

**Documentation reference:**  
https://docs.blender.org/api/current/bpy.ops.import_scene.html

### 4.2 Model positioning and posing

| Capability | Verdict | API |
|---|---|---|
| Position models | **YES** | `Object.location`, `Object.rotation_euler`, `Object.scale` |
| Pose armature (mannequin) | **YES** | `PoseBone.rotation_mode`, `PoseBone.rotation_euler` etc. |
| Apply poses from library | **YES** | `bpy.ops.poselib.apply_pose()` |
| Import posed GLB | **YES** | glTF preserves armature + pose data |

### 4.3 Camera control

| Capability | Verdict | API |
|---|---|---|
| Focal length | **YES** | `Camera.lens = 85.0` (in mm) |
| Sensor size | **YES** | `Camera.sensor_width = 36.0` (full frame) |
| FOV | **YES** | `Camera.angle` (radians) or derived from lens + sensor |
| Depth of field | **YES** | `Camera.dof.use_dof = True`, `.aperture_fstop = 2.8` |
| Focus distance | **YES** | `Camera.dof.focus_distance = 5.0` |
| Camera position | **YES** | `Object.location` on camera object |
| Camera aim | **YES** | Track-to constraint or manual rotation |

### 4.4 Room/scene geometry creation

| Capability | Verdict | Approach |
|---|---|---|
| Create walls | **YES** | `bpy.ops.mesh.primitive_plane_add()` scaled/positioned |
| Create floor | **YES** | Plane with appropriate material |
| Create ceiling | **YES** | Plane positioned above |
| Create backdrops | **YES** | Curved plane (cyclorama) via subdivided + deformed mesh |
| Programmatic mesh | **YES** | Full `bmesh` API for custom geometry |
| Apply materials | **YES** | `bpy.data.materials.new()` with Principled BSDF shader |

---

## 5. IES Light Support (Detailed)

### 5.1 Native support

| Aspect | Status | Details |
|---|---|---|
| IES file parsing | **YES** | Built into Cycles via `ShaderNodeTexIES` |
| .ies format support | **YES** | Standard IESNA LM-63 format |
| Cycles rendering | **YES** | Full IES profile applied to point/spot/area lights |
| Programmatic access | **YES** | Via shader node tree API |

### 5.2 Pre-built IES libraries

| Source | Count | Notes |
|---|---|---|
| BlenderArtists free library | 160,000+ | Community-curated with preview images |
| Manufacturer sites | Varies | Philips, Osram, ERCO, etc. provide free IES files |
| BlenderKit | Integrated | Built-in asset browser with IES lights |

---

## 6. Photography Studio Addons

### 6.1 Existing addons

| Addon | Purpose | Notes |
|---|---|---|
| **Photographer** (blendermarket.com) | Real camera controls (ISO, shutter, aperture, white balance, light metering) | Most relevant addon for this use case |
| **Light Wrangler** (Blender extension) | Point-and-click light placement | Useful for studio setups |
| **Blender Light Studio** | Studio HDRI lighting | HDRI-based workflows |
| **BlenderProc** (DLR-RM) | Programmatic scene generation for computer vision | Used in ML pipelines, very relevant for automated rendering |

### 6.2 Built-in capabilities

| Feature | Status | Location |
|---|---|---|
| AgX tone mapping | **Built-in** | Color management settings |
| False color viewport | **Built-in** | Viewport shading options |
| Light group rendering | **Built-in** | Cycles light groups for separate light passes |
| Shadow catcher | **Built-in** | Material shadow catcher for compositing |

---

## 7. Gaps and Limitations

### 7.1 Where Blender CANNOT fully replicate set.a.light 3D

| Gap | Severity | Workaround |
|---|---|---|
| **No native physical camera (ISO/shutter)** | **MEDIUM** | PR #154407 in development. Use `Scene.render.exposure` as stop control. The "Photographer" addon adds this. |
| **No built-in light meter overlay** | **LOW** | Use false color viewport, or compute EV from light values programmatically |
| **No real-time preview** | **N/A** | By design - this is a parameter-driven workflow, not real-time |
| **No built-in barn door modifier** | **LOW** | Use geometry blockers or shader node masking |
| **No dedicated studio UI** | **N/A** | We build our own UI; Blender is the backend only |
| **No built-in mannequin library** | **LOW** | Import from Mixamo, MakeHuman, or custom GLB models |
| **No lighting diagram export** | **LOW** | Implement in our application layer using scene data |

### 7.2 Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Physical camera PR not merged | Low | Medium | Photographer addon, exposure workaround |
| Render time too slow for UX | Low | High | GPU optimization, lower sample count for previews, denoiser |
| Docker GPU passthrough issues | Medium | Medium | Use NVIDIA container toolkit, test on target hardware |
| Blender API breaking changes | Low | Medium | Pin Blender version, test on upgrade |

---

## 8. Sample Python Script: Complete Workflow

```python
"""
Complete Blender photography lighting simulation script.
Run: blender -b -P studio_render.py
"""
import bpy
import math
import os

def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_studio_room(width=8, depth=10, height=3.5):
    """Create a photography studio room with walls, floor, ceiling."""
    
    # Floor
    bpy.ops.mesh.primitive_plane_add(size=width, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale[1] = depth / width
    floor_mat = bpy.data.materials.new("FloorMat")
    floor_mat.use_nodes = True
    bsdf = floor_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1)  # Dark gray
    bsdf.inputs["Roughness"].default_value = 0.4
    floor.data.materials.append(floor_mat)
    
    # Back wall (cyclorama curve could be added)
    bpy.ops.mesh.primitive_plane_add(size=width, location=(0, -depth/2, height/2))
    back_wall = bpy.context.active_object
    back_wall.name = "BackWall"
    back_wall.rotation_euler[0] = math.pi / 2  # Face forward
    wall_mat = bpy.data.materials.new("WallMat")
    wall_mat.use_nodes = True
    wall_bsdf = wall_mat.node_tree.nodes["Principled BSDF"]
    wall_bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1)  # White
    wall_bsdf.inputs["Roughness"].default_value = 0.8
    back_wall.data.materials.append(wall_mat)

def create_area_light(name, location, rotation, energy, size_x, size_y,
                      color_temp=5500, spread=math.pi):
    """Create an area light simulating a softbox."""
    
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.shape = 'RECTANGLE'
    light_data.size = size_x
    light_data.size_y = size_y
    light_data.energy = energy  # Watts
    light_data.spread = spread  # Grid simulation
    light_data.use_temperature = True
    light_data.temperature = color_temp  # Kelvin
    
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    
    light_obj.location = location
    light_obj.rotation_euler = rotation
    
    return light_obj

def create_spot_light(name, location, rotation, energy, spot_size=math.pi/6,
                      spot_blend=0.3, color_temp=3200):
    """Create a spot light with snoot/honeycomb grid."""
    
    light_data = bpy.data.lights.new(name=name, type='SPOT')
    light_data.energy = energy
    light_data.spot_size = spot_size
    light_data.spot_blend = spot_blend
    light_data.use_temperature = True
    light_data.temperature = color_temp
    
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    
    light_obj.location = location
    light_obj.rotation_euler = rotation
    
    return light_obj

def setup_hdri_env(hdri_path, rotation=0, strength=0.3):
    """Set up HDRI environment lighting."""
    
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("StudioWorld")
        bpy.context.scene.world = world
    
    world.use_nodes = True
    tree = world.node_tree
    nodes = tree.nodes
    links = tree.links
    
    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)
    
    # Add environment texture
    env_tex = nodes.new('ShaderNodeTexEnvironment')
    env_tex.image = bpy.data.images.load(hdri_path)
    
    # Add mapping for rotation
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Rotation'].default_value[2] = rotation
    
    tex_coord = nodes.new('ShaderNodeTexCoord')
    
    background = nodes.new('ShaderNodeBackground')
    background.inputs['Strength'].default_value = strength
    
    output = nodes.new('ShaderNodeOutputWorld')
    
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
    links.new(env_tex.outputs['Color'], background.inputs['Color'])
    links.new(background.outputs['Background'], output.inputs['Surface'])

def setup_camera(location, rotation, focal_length=85, fstop=2.8,
                 focus_distance=5, sensor_width=36):
    """Configure camera with photography parameters."""
    
    cam_data = bpy.data.cameras.new("StudioCamera")
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    
    # Lens
    cam_data.lens = focal_length          # mm
    cam_data.sensor_width = sensor_width   # mm (full frame = 36)
    
    # Depth of field
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = fstop
    cam_data.dof.focus_distance = focus_distance
    cam_data.dof.aperture_blades = 9  # Circular aperture
    
    # Position
    cam_obj.location = location
    cam_obj.rotation_euler = rotation
    
    # Set as scene camera
    bpy.context.scene.camera = cam_obj
    
    return cam_obj

def configure_rendering(resolution_x=1920, resolution_y=1080,
                        samples=256, engine='CYCLES',
                        output_path="/tmp/studio_render.png"):
    """Configure render settings."""
    
    scene = bpy.context.scene
    
    # Engine
    scene.render.engine = engine
    
    # Resolution
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    
    # Cycles settings
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    
    # GPU rendering
    scene.cycles.device = 'GPU'
    
    # Color management (AgX for photographic look)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0.0  # Adjust as needed
    scene.view_settings.gamma = 1.0
    
    # Output
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '16'

def import_model(filepath):
    """Import a 3D model (GLB, FBX, OBJ)."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.obj':
        bpy.ops.wm.obj_import(filepath=filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")

def add_volume_haze(density=0.002):
    """Add volumetric haze to the scene (fog machine simulation)."""
    
    world = bpy.context.scene.world
    world.use_nodes = True
    tree = world.node_tree
    
    # Add volume scatter
    vol_scatter = tree.nodes.new('ShaderNodeVolumeScatter')
    vol_scatter.inputs['Density'].default_value = density
    vol_scatter.inputs['Color'].default_value = (1, 1, 1, 1)  # White fog
    
    # Connect to output
    output = tree.nodes.get('World Output') or tree.nodes.new('ShaderNodeOutputWorld')
    tree.links.new(vol_scatter.outputs['Volume'], output.inputs['Volume'])

# ============================================================
# MAIN: Complete Studio Setup
# ============================================================

def main():
    clear_scene()
    
    # 1. Create studio room
    create_studio_room(width=8, depth=10, height=3.5)
    
    # 2. Set up lights (photography studio setup)
    
    # Key light - large softbox, 45 degrees camera right, high
    key_light = create_area_light(
        name="KeyLight_Softbox",
        location=(2.5, -2, 2.8),
        rotation=(math.radians(45), 0, math.radians(-30)),
        energy=500,        # Watts
        size_x=1.2,        # 120cm wide softbox
        size_y=0.8,        # 80cm tall
        color_temp=5500,   # Daylight balanced
        spread=math.pi     # No grid (full spread)
    )
    
    # Fill light - larger softbox, lower power, opposite side
    fill_light = create_area_light(
        name="FillLight_Softbox",
        location=(-2, -1.5, 2.5),
        rotation=(math.radians(50), 0, math.radians(20)),
        energy=150,
        size_x=1.5,
        size_y=1.0,
        color_temp=5500,
        spread=math.pi
    )
    
    # Hair/rim light - spot from behind
    rim_light = create_spot_light(
        name="RimLight_Spot",
        location=(0, 3, 3),
        rotation=(math.radians(160), 0, 0),
        energy=300,
        spot_size=math.radians(30),
        spot_blend=0.5,
        color_temp=5500
    )
    
    # Background light
    bg_light = create_area_light(
        name="BackgroundLight",
        location=(0, -4.5, 1.5),
        rotation=(math.radians(80), 0, 0),
        energy=200,
        size_x=2.0,
        size_y=1.5,
        color_temp=5500,
        spread=math.pi
    )
    
    # 3. Optional: HDRI ambient fill
    # setup_hdri_env("/path/to/studio_hdri.hdr", rotation=0, strength=0.2)
    
    # 4. Optional: Volume haze (fog machine)
    # add_volume_haze(density=0.003)
    
    # 5. Set up camera (85mm portrait lens, f/2.8)
    setup_camera(
        location=(0, -5, 1.6),          # 5m from subject, eye level
        rotation=(math.radians(85), 0, 0), # Looking slightly up
        focal_length=85,
        fstop=2.8,
        focus_distance=5.0,
        sensor_width=36.0
    )
    
    # 6. Import subject model (mannequin or human)
    # import_model("/path/to/mannequin.glb")
    
    # 7. Configure rendering
    configure_rendering(
        resolution_x=1920,
        resolution_y=1080,
        samples=256,
        output_path="/tmp/studio_render.png"
    )
    
    # 8. Render
    bpy.ops.render.render(write_still=True)
    print("Render complete: /tmp/studio_render.png")

if __name__ == "__main__":
    main()
```

---

## 9. Rendering Time Estimates

### For a single 1920x1080 frame with a typical studio scene:

| Configuration | Samples | Time Estimate | Notes |
|---|---|---|---|
| CPU only (modern 8-core) | 256 | 60-180 seconds | Baseline, not recommended |
| RTX 3060 (12GB) | 256 | 10-30 seconds | With denoiser |
| RTX 4070 (12GB) | 256 | 5-15 seconds | Good balance |
| RTX 4090 (24GB) | 256 | 2-8 seconds | Production-grade |
| RTX 4090 (24GB) | 128 + denoise | 1-4 seconds | Preview quality, acceptable |
| A100 (80GB) | 128 + denoise | 1-3 seconds | Cloud GPU, ideal |

**Recommendation for responsive UX:**
- **Preview mode:** 64-128 samples + OpenImageDenoise = 1-5 seconds on RTX 4070+
- **Final render:** 256-512 samples = 5-30 seconds on RTX 4070+

---

## 10. Architecture Recommendation

```
User Interface (Web)
       |
       v
  API Server (Python/FastAPI)
       |
       v
  Job Queue (Redis/Celery)
       |
       v
  Blender Worker Pool (Docker containers with GPU)
       |
       v
  Object Storage (S3/MinIO) -> Rendered images
```

**Recommended stack:**
- **Render:** Blender 4.5+ in Docker with NVIDIA GPU
- **Queue:** Celery + Redis for job management
- **Farm:** Flamenco (Blender's built-in render farm) or custom Docker Compose
- **Storage:** S3-compatible for rendered outputs
- **Frontend:** Any web framework that displays images

---

## Sources

- [Blender Python API - Light](https://docs.blender.org/api/current/bpy.types.Light.html)
- [Blender Python API - AreaLight](https://docs.blender.org/api/current/bpy.types.AreaLight.html)
- [Blender Python API - SpotLight](https://docs.blender.org/api/current/bpy.types.SpotLight.html)
- [Blender Python API - PointLight](https://docs.blender.org/api/current/bpy.types.PointLight.html)
- [Blender Python API - SunLight](https://docs.blender.org/api/current/bpy.types.SunLight.html)
- [Blender Manual - IES Texture Node](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/ies.html)
- [Blender Python API - Camera](https://docs.blender.org/api/current/bpy.types.Camera.html)
- [Blender Python API - CameraDOFSettings](https://docs.blender.org/api/current/bpy.types.CameraDOFSettings.html)
- [Blender Python API - Import Scene Operators](https://docs.blender.org/api/current/bpy.ops.import_scene.html)
- [Blender Manual - Command Line Arguments](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html)
- [Blender Manual - Cycles Render Engine](https://docs.blender.org/manual/en/latest/render/cycles/index.html)
- [Blender Python API - CyclesRenderSettings](https://docs.blender.org/api/current/bpy.types.CyclesRenderSettings.html)
- [Physically Correct Brightness in Cycles](https://blendergrid.com/articles/cycles-physically-correct-brightness)
- [IES Lighting in Blender](https://blendergrid.com/articles/ies-lighting-in-blender)
- [Physical Camera PR #154407](https://projects.blender.org/blender/blender/pulls/154407)
- [Bringing Real Cameras to Cycles - BlenderCon 2025](https://www.youtube.com/watch?v=FT_AiNSHpDQ)
- [Setting Up Blender Docker Render Node](https://snowgoons.ro/posts/2020-09-08-setting-up-a-blender-rendering-node-using-docker/)
- [Containerized GPU Optimization for Blender](https://medium.com/@maheshwar.ramkrushna/containerized-gpu-optimization-for-enhanced-rendering-and-3d-work-in-blenders-isolated-environment-ffaab013339d)
- [Free IES Light Library (160k+)](https://blenderartists.org/t/free-ies-light-library-available/1233481)

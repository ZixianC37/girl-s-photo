"""
Blender 渲染模块 — 生成 bpy 脚本并执行无头渲染
支持：影棚场景配置、GLB/OBJ 模型导入、灯光模拟
"""
import json
import os
import subprocess
import time
import uuid
import math


PRESETS_PATH = os.path.join(os.path.dirname(__file__), "presets", "lighting.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def load_presets():
    with open(PRESETS_PATH, "r") as f:
        return json.load(f)


def _angle_to_position(h_angle_deg, v_angle_deg, distance):
    h = math.radians(h_angle_deg)
    v = math.radians(v_angle_deg)
    x = distance * math.cos(v) * math.sin(h)
    z = distance * math.sin(v)
    y = -distance * math.cos(v) * math.cos(h)
    return [x, y, z]


def _look_at_rotation(light_pos, target=(0, 1.65, 0)):
    dx = target[0] - light_pos[0]
    dy = target[1] - light_pos[1]
    dz = target[2] - light_pos[2]
    pitch = math.atan2(dz, math.sqrt(dx * dx + dy * dy))
    yaw = math.atan2(dx, dy)
    return [pitch, 0.0, yaw]


def generate_script(params):
    """根据参数生成完整的 Blender Python 渲染脚本。"""
    lights = params.get("lights", [])
    camera = params.get("camera", {})
    scene = params.get("scene", {})
    quality = params.get("quality", "preview")
    model = params.get("model", {})
    output_path = params.get(
        "output_path",
        os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex[:8]}.png"),
    )

    samples = 128 if quality == "preview" else 512
    res_x = scene.get("resolution_x", 1280)
    res_y = scene.get("resolution_y", 720)

    focal_length = camera.get("focal_length", 85)
    f_stop = camera.get("f_stop", 2.8)

    # Studio / scene config
    room_w = scene.get("room_width", 8)
    room_d = scene.get("room_depth", 10)
    room_h = scene.get("room_height", 3.5)
    backdrop_color = scene.get("backdrop_color", "white")
    backdrop_colors = {
        "white": "(0.95, 0.95, 0.95, 1)",
        "light_gray": "(0.78, 0.78, 0.78, 1)",
        "gray": "(0.50, 0.50, 0.50, 1)",
        "dark_gray": "(0.25, 0.25, 0.25, 1)",
        "black": "(0.05, 0.05, 0.05, 1)",
        "warm_white": "(0.95, 0.92, 0.88, 1)",
        "cool_white": "(0.88, 0.92, 0.95, 1)",
        "seamless_blue": "(0.15, 0.35, 0.65, 1)",
        "seamless_red": "(0.70, 0.15, 0.15, 1)",
    }
    bg_color = backdrop_colors.get(backdrop_color, backdrop_colors["white"])
    floor_color = scene.get("floor_color", "dark_gray")
    floor_colors = {
        "dark_gray": "(0.15, 0.15, 0.15, 1)",
        "light_gray": "(0.45, 0.45, 0.45, 1)",
        "wood": "(0.35, 0.22, 0.12, 1)",
        "white": "(0.90, 0.90, 0.90, 1)",
        "black": "(0.03, 0.03, 0.03, 1)",
    }
    fl_color = floor_colors.get(floor_color, floor_colors["dark_gray"])
    use_cyclorama = scene.get("use_cyclorama", True)

    # Model config
    model_type = model.get("type", "mannequin")
    model_path = model.get("path", "")
    model_scale = model.get("scale", 1.0)
    model_rotation = model.get("rotation", 0)

    lines = []
    lines.append('"""\nAuto-generated Blender studio render script.\nRun: blender -b -P this_script.py\n"""')
    lines.append("import bpy")
    lines.append("import math")
    lines.append("import os")
    lines.append("import mathutils")
    lines.append("")
    lines.append("# Clear scene")
    lines.append("bpy.ops.object.select_all(action='SELECT')")
    lines.append("bpy.ops.object.delete(use_global=False)")
    lines.append("")

    # ── Studio Room ──
    lines.append("# === STUDIO ROOM ===")
    lines.append(f"room_w, room_d, room_h = {room_w}, {room_d}, {room_h}")

    # Floor
    lines.append("")
    lines.append("# Floor")
    lines.append("bpy.ops.mesh.primitive_plane_add(size=room_w, location=(0, 0, 0))")
    lines.append("floor = bpy.context.active_object")
    lines.append("floor.scale[1] = room_d / room_w")
    lines.append("floor_mat = bpy.data.materials.new('FloorMat')")
    lines.append("floor_mat.use_nodes = True")
    lines.append(f"floor_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = {fl_color}")
    lines.append("floor_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.4")
    lines.append("floor.data.materials.append(floor_mat)")

    # Cyclorama (seamless backdrop curve)
    if use_cyclorama:
        lines.append("")
        lines.append("# Cyclorama (seamless backdrop)")
        lines.append("curve_r = 1.2  # curve radius")
        lines.append("bpy.ops.mesh.primitive_plane_add(size=room_w, location=(0, -room_d/2 + 0.01, curve_r))")
        lines.append("cyc = bpy.context.active_object")
        lines.append("# Subdivide for smooth bending")
        lines.append("bpy.ops.object.mode_set(mode='EDIT')")
        lines.append("bpy.ops.mesh.subdivide(number_cuts=16)")
        lines.append("bpy.ops.object.mode_set(mode='OBJECT')")
        lines.append("# Apply curve deformation via shape keys")
        lines.append("for i, v in enumerate(cyc.data.vertices):")
        lines.append("    z_local = v.co.z - curve_r")
        lines.append("    if z_local < 0:")
        lines.append("        angle = max(-math.pi/2, z_local / curve_r)")
        lines.append("        v.co.z = curve_r + curve_r * math.sin(angle)")
        lines.append("        v.co.y = v.co.y + curve_r * (1 - math.cos(angle))")
        lines.append("cyc_mat = bpy.data.materials.new('BackdropMat')")
        lines.append("cyc_mat.use_nodes = True")
        lines.append(f"cyc_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = {bg_color}")
        lines.append("cyc_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.85")
        lines.append("cyc.data.materials.append(cyc_mat)")
    else:
        # Simple back wall
        lines.append("")
        lines.append("# Back wall (flat)")
        lines.append("bpy.ops.mesh.primitive_plane_add(size=room_w, location=(0, -room_d/2, room_h/2))")
        lines.append("back_wall = bpy.context.active_object")
        lines.append("back_wall.rotation_euler[0] = math.pi / 2")
        lines.append("wall_mat = bpy.data.materials.new('WallMat')")
        lines.append("wall_mat.use_nodes = True")
        lines.append(f"wall_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = {bg_color}")
        lines.append("wall_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8")
        lines.append("back_wall.data.materials.append(wall_mat)")

    # Side walls
    lines.append("")
    lines.append("# Side walls (dark, non-reflective)")
    lines.append("for side in [-1, 1]:")
    lines.append("    bpy.ops.mesh.primitive_plane_add(size=room_d, location=(side * room_w/2, 0, room_h/2))")
    lines.append("    sw = bpy.context.active_object")
    lines.append("    sw.scale[2] = room_h / room_d")
    lines.append("    sw.rotation_euler[2] = math.pi / 2")
    lines.append("    sw_mat = bpy.data.materials.new(f'SideWall_{{side}}')")
    lines.append("    sw_mat.use_nodes = True")
    lines.append("    sw_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.12, 0.12, 0.12, 1)")
    lines.append("    sw_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95")
    lines.append("    sw.data.materials.append(sw_mat)")

    # Ceiling
    lines.append("")
    lines.append("# Ceiling")
    lines.append("bpy.ops.mesh.primitive_plane_add(size=room_w, location=(0, 0, room_h))")
    lines.append("ceiling = bpy.context.active_object")
    lines.append("ceiling.scale[1] = room_d / room_w")
    lines.append("ceil_mat = bpy.data.materials.new('CeilMat')")
    lines.append("ceil_mat.use_nodes = True")
    lines.append("ceil_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.15, 0.15, 0.15, 1)")
    lines.append("ceil_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9")
    lines.append("ceiling.data.materials.append(ceil_mat)")

    # ── Light stands (visual representation) ──
    lines.append("")
    lines.append("# === LIGHT STANDS ===")
    lines.append("stand_mat = bpy.data.materials.new('StandMat')")
    lines.append("stand_mat.use_nodes = True")
    lines.append("stand_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1)")
    lines.append("stand_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.3")

    for i, light in enumerate(lights):
        if not light.get("enabled", True):
            continue
        h_angle = light.get("h_angle", 0)
        v_angle = light.get("v_angle", 45)
        distance = light.get("distance", 3.0)
        pos = _angle_to_position(h_angle, v_angle, distance)

        lines.append(f"# Stand for {light.get('name', f'Light{i}')}")
        lines.append(f"bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth={pos[2]:.2f}, location=({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]/2:.3f}))")
        lines.append(f"stand_{i} = bpy.context.active_object")
        lines.append(f"stand_{i}.data.materials.append(stand_mat)")

        # Softbox / modifier visual
        light_type = light.get("type", "AREA")
        if light_type == "AREA":
            size_x = light.get("size_x", 1.0)
            size_y = light.get("size_y", 0.8)
            lines.append(f"bpy.ops.mesh.primitive_plane_add(size=1, location=({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}))")
            lines.append(f"sb_{i} = bpy.context.active_object")
            lines.append(f"sb_{i}.scale = ({size_x/2:.3f}, {size_y/2:.3f}, 0.01)")
            lines.append(f"sb_{i}.rotation_euler = {_look_at_rotation(pos)}")
            lines.append(f"sb_mat_{i} = bpy.data.materials.new('SoftboxMat_{i}')")
            lines.append(f"sb_mat_{i}.use_nodes = True")
            lines.append(f"sb_mat_{i}.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1)")
            lines.append(f"sb_mat_{i}.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5")
            lines.append(f"sb_{i}.data.materials.append(sb_mat_{i})")

    # ── Model / Subject ──
    lines.append("")
    lines.append("# === MODEL / SUBJECT ===")

    if model_type == "import" and model_path and os.path.exists(model_path):
        ext = os.path.splitext(model_path)[1].lower()
        lines.append(f"# Import model: {os.path.basename(model_path)}")
        if ext in (".glb", ".gltf"):
            lines.append(f"bpy.ops.import_scene.gltf(filepath=r'{model_path}')")
        elif ext == ".obj":
            lines.append(f"bpy.ops.wm.obj_import(filepath=r'{model_path}')")
        elif ext == ".fbx":
            lines.append(f"bpy.ops.import_scene.fbx(filepath=r'{model_path}')")
        elif ext == ".stl":
            lines.append(f"bpy.ops.wm.stl_import(filepath=r'{model_path}')")
        lines.append("# Auto-center and scale imported model")
        lines.append("imported_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.select_get()]")
        lines.append("if not imported_objs:")
        lines.append("    imported_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name not in ('Floor', 'Back wall', 'Camera', 'Light')]")
        lines.append("if imported_objs:")
        lines.append("    # Center model")
        lines.append("    bpy.ops.object.select_all(action='DESELECT')")
        lines.append("    for obj in imported_objs:")
        lines.append("        obj.select_set(True)")
        lines.append("    bpy.context.view_layer.objects.active = imported_objs[0]")
        lines.append("    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')")
        lines.append("    # Move to standing position (feet on floor)")
        lines.append("    bbox_min_z = min(v.co.z for obj in imported_objs for v in obj.data.vertices)")
        lines.append("    for obj in imported_objs:")
        lines.append(f"        obj.location.z -= bbox_min_z")
        lines.append(f"    # Scale")
        lines.append(f"    for obj in imported_objs:")
        lines.append(f"        obj.scale = ({model_scale}, {model_scale}, {model_scale})")
        lines.append(f"    # Rotate")
        lines.append(f"    for obj in imported_objs:")
        lines.append(f"        obj.rotation_euler[2] = math.radians({model_rotation})")
    else:
        # Default mannequin
        lines.append("# Mannequin (default proxy)")
        _generate_mannequin(lines)

    # ── Lights ──
    lines.append("")
    lines.append("# === LIGHTS ===")
    for i, light in enumerate(lights):
        if not light.get("enabled", True):
            continue

        name = light.get("name", f"Light{i}")
        light_type = light.get("type", "AREA")
        energy = light.get("energy", 500)
        color_temp = light.get("color_temp", 5500)
        h_angle = light.get("h_angle", 0)
        v_angle = light.get("v_angle", 45)
        distance = light.get("distance", 3.0)

        pos = _angle_to_position(h_angle, v_angle, distance)
        rot = _look_at_rotation(pos)

        blender_type = "AREA" if light_type == "AREA" else "SPOT"
        lines.append(f"# {name}")
        lines.append(f"light_data_{i} = bpy.data.lights.new(name='{name}', type='{blender_type}')")

        if light_type == "AREA":
            size_x = light.get("size_x", 1.0)
            size_y = light.get("size_y", 0.8)
            spread = math.radians(light.get("spread", 180))
            lines.append(f"light_data_{i}.shape = 'RECTANGLE'")
            lines.append(f"light_data_{i}.size = {size_x}")
            lines.append(f"light_data_{i}.size_y = {size_y}")
            lines.append(f"light_data_{i}.spread = {spread}")
        else:
            spot_size = math.radians(light.get("spot_size", 30))
            spot_blend = light.get("spot_blend", 0.5)
            lines.append(f"light_data_{i}.spot_size = {spot_size}")
            lines.append(f"light_data_{i}.spot_blend = {spot_blend}")

        lines.append(f"light_data_{i}.energy = {energy}")
        lines.append(f"light_data_{i}.use_temperature = True")
        lines.append(f"light_data_{i}.temperature = {color_temp}")
        lines.append(f"light_obj_{i} = bpy.data.objects.new('{name}', light_data_{i})")
        lines.append(f"bpy.context.scene.collection.objects.link(light_obj_{i})")
        lines.append(f"light_obj_{i}.location = {pos}")
        lines.append(f"light_obj_{i}.rotation_euler = {rot}")
        lines.append("")

    # ── Camera ──
    lines.append("# === CAMERA ===")
    lines.append("cam_data = bpy.data.cameras.new('StudioCamera')")
    lines.append("cam_obj = bpy.data.objects.new('Camera', cam_data)")
    lines.append("bpy.context.scene.collection.objects.link(cam_obj)")
    lines.append(f"cam_data.lens = {focal_length}")
    lines.append("cam_data.sensor_width = 36.0")
    lines.append("cam_data.dof.use_dof = True")
    lines.append(f"cam_data.dof.aperture_fstop = {f_stop}")
    lines.append("cam_data.dof.focus_distance = 5.0")
    lines.append("cam_data.dof.aperture_blades = 9")
    lines.append("cam_obj.location = (0, -5, 1.6)")
    lines.append("cam_obj.rotation_euler = (math.radians(82), 0, 0)")
    lines.append("bpy.context.scene.camera = cam_obj")
    lines.append("")

    # ── Rendering ──
    lines.append("# === RENDERING ===")
    lines.append("scene = bpy.context.scene")
    lines.append("scene.render.engine = 'CYCLES'")
    lines.append(f"scene.render.resolution_x = {res_x}")
    lines.append(f"scene.render.resolution_y = {res_y}")
    lines.append("scene.render.resolution_percentage = 100")
    lines.append(f"scene.cycles.samples = {samples}")
    lines.append("scene.cycles.use_denoising = True")
    lines.append("scene.cycles.denoiser = 'OPENIMAGEDENOISE'")
    lines.append("scene.cycles.device = 'GPU'")
    lines.append("scene.view_settings.view_transform = 'AgX'")
    lines.append(f"scene.render.filepath = r'{output_path}'")
    lines.append("scene.render.image_settings.file_format = 'PNG'")
    lines.append("scene.render.image_settings.color_mode = 'RGBA'")
    lines.append("scene.render.image_settings.color_depth = '16'")
    lines.append("")
    lines.append("print('Starting render...')")
    lines.append("import time")
    lines.append("t0 = time.time()")
    lines.append("bpy.ops.render.render(write_still=True)")
    lines.append("t1 = time.time()")
    lines.append(f"print(f'Render complete in {{t1-t0:.1f}}s: {output_path}')")

    return "\n".join(lines)


def _generate_mannequin(lines):
    """生成默认模特人体代理（几何体组合）。"""
    lines.append("# Body")
    lines.append("bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=1.2, location=(0, 0, 0.85))")
    lines.append("body = bpy.context.active_object")
    lines.append("body.name = 'Body'")
    lines.append("skin_mat = bpy.data.materials.new('SkinMat')")
    lines.append("skin_mat.use_nodes = True")
    lines.append("skin_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.65, 0.5, 0.4, 1)")
    lines.append("skin_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6")
    lines.append("skin_mat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.15")
    lines.append("body.data.materials.append(skin_mat)")
    lines.append("")
    lines.append("# Head")
    lines.append("bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(0, 0, 1.7))")
    lines.append("head = bpy.context.active_object")
    lines.append("head.name = 'Head'")
    lines.append("head.data.materials.append(skin_mat)")
    lines.append("")
    lines.append("# Neck")
    lines.append("bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.2, location=(0, 0, 1.5))")
    lines.append("neck = bpy.context.active_object")
    lines.append("neck.data.materials.append(skin_mat)")
    lines.append("")
    lines.append("# Shoulders")
    lines.append("bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=0.15, location=(0, 0, 1.45))")
    lines.append("shoulders = bpy.context.active_object")
    lines.append("shoulders.data.materials.append(skin_mat)")
    lines.append("")
    lines.append("# Arms")
    lines.append("for side in [-1, 1]:")
    lines.append("    bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=0.7, location=(side*0.4, 0, 1.15))")
    lines.append("    arm = bpy.context.active_object")
    lines.append("    arm.rotation_euler[2] = math.radians(5 * side)")
    lines.append("    arm.data.materials.append(skin_mat)")
    lines.append("")
    lines.append("# Legs")
    lines.append("for side in [-1, 1]:")
    lines.append("    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.8, location=(side*0.15, 0, 0.2))")
    lines.append("    leg = bpy.context.active_object")
    lines.append("    leg.data.materials.append(skin_mat)")


def render(params):
    """生成脚本并执行 Blender 渲染。返回 (image_path, render_time_seconds, error)。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    output_filename = f"{uuid.uuid4().hex[:8]}.png"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    params["output_path"] = output_path

    script = generate_script(params)

    script_path = os.path.join(OUTPUT_DIR, f"render_{uuid.uuid4().hex[:8]}.py")
    with open(script_path, "w") as f:
        f.write(script)

    blender_path = os.environ.get("BLENDER_PATH", "blender")
    cmd = [blender_path, "-b", "-P", script_path]

    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return None, 0, f"Blender not found at '{blender_path}'. Install Blender or set BLENDER_PATH env var."
    except subprocess.TimeoutExpired:
        return None, 0, "Render timed out after 5 minutes."

    render_time = time.time() - t0

    if not os.path.exists(output_path):
        error_lines = result.stderr[-800:] if result.stderr else result.stdout[-800:] if result.stdout else "Unknown error"
        return None, render_time, f"Render failed: {error_lines}"

    try:
        os.remove(script_path)
    except Exception:
        pass

    return output_path, render_time, None


if __name__ == "__main__":
    presets = load_presets()
    preset = presets["presets"][0]
    params = {
        "lights": preset["lights"],
        "camera": presets["camera_defaults"],
        "scene": {**presets["scene_defaults"], "backdrop_color": "white", "floor_color": "dark_gray", "use_cyclorama": True},
        "model": {"type": "mannequin"},
        "quality": "preview",
    }
    path, seconds, error = render(params)
    if error:
        print(f"Error: {error}")
    else:
        print(f"Rendered in {seconds:.1f}s: {path}")

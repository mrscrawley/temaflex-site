# blender -b -P build.py -P render.py -- <outdir> <frames: all | 20,90,...> [w h]
import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
frames = argv[1] if len(argv) > 1 else "all"
w, h = (int(argv[2]), int(argv[3])) if len(argv) > 3 else (1280, 720)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = w, h
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 88
os.makedirs(out, exist_ok=True)
fl = range(sc.frame_start, sc.frame_end + 1) if frames == "all" else [int(x) for x in frames.split(",")]
for f in fl:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(out, f"f{f:04d}.jpg")
    bpy.ops.render.render(write_still=True)

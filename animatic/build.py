# Тема Флекс — серый аниматик главной. Строит всю сцену (3D Jutsu / Blender 5.2).
import bpy, math
from mathutils import Vector

sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    bpy.data.meshes.remove(m)

F_END = 630
sc.frame_start, sc.frame_end = 1, F_END
sc.render.fps = 24

BG = (0.961, 0.933, 0.898)
def lin(c):
    return tuple(((x / 255) ** 2.2) for x in c)

MATS = {}
def mat(name, rgb, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, alpha)
    MATS[name] = m
    return m

CLAY = mat("clay", lin((206, 198, 188)))
FILM = mat("film", lin((216, 206, 192)))
TABLE = mat("table", lin((232, 222, 208)))
ORANGE = mat("orange", lin((238, 125, 28)))
TEAL = mat("teal", lin((31, 95, 92)))
INK = [mat("ink_w", lin((250, 248, 244))), mat("ink_c", lin((0, 160, 210))),
       mat("ink_m", lin((215, 30, 120))), mat("ink_y", lin((250, 210, 20))),
       mat("ink_k", lin((35, 35, 38))), ORANGE]

# печать: процедурная картинка-полосы для рукавов (UV)
def print_image():
    W, H = 256, 64
    img = bpy.data.images.new("print", W, H)
    cols = [(238, 125, 28), (31, 95, 92), (250, 210, 20), (250, 248, 244), (215, 30, 120)]
    px = []
    for y in range(H):
        for x in range(W):
            b = (x // 32 + (1 if y > H * 0.55 else 0)) % len(cols)
            if 0.35 * H < y < 0.45 * H:
                b = 1
            c = cols[b]
            px += [c[0] / 255, c[1] / 255, c[2] / 255, 1.0]
    img.pixels = px
    return img
PIMG = print_image()
PRINT = mat("print", lin((238, 125, 28)))
PRINT.use_nodes = True
nt = PRINT.node_tree
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = PIMG
nt.links.new(tex.outputs[0], nt.nodes["Principled BSDF"].inputs[0])

def obj(name, mesh, m=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, mesh)
    sc.collection.objects.link(o)
    o.location = loc
    if m:
        mesh.materials.append(m)
    return o

def mesh_from(name, verts, faces, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if uvs:
        uv = me.uv_layers.new(name="UV")
        for poly in me.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                uv.data[li].uv = uvs[vi]
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except Exception:
        pass
    return me

def box(name, size, loc, m):
    sx, sy, sz = [s / 2 for s in size]
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me = mesh_from(name, v, f)
    for p in me.polygons:
        p.use_smooth = False
    return obj(name, me, m, loc)

def lathe(name, prof, m, loc, seg=48, cap=True, uv=False):
    """prof: [(r, z)] снизу вверх."""
    v, f, uvs = [], [], []
    n = len(prof)
    for i, (r, z) in enumerate(prof):
        for j in range(seg):
            a = 2 * math.pi * j / seg
            v.append((r * math.cos(a), r * math.sin(a), z))
            uvs.append((j / seg, i / max(1, n - 1)))
    for i in range(n - 1):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            f.append((a, b, b + seg, a + seg))
    if cap:
        v.append((0, 0, prof[0][1])); uvs.append((0, 0)); c0 = len(v) - 1
        v.append((0, 0, prof[-1][1])); uvs.append((0, 0)); c1 = len(v) - 1
        for j in range(seg):
            f.append((c0, (j + 1) % seg, j))
            top = (n - 1) * seg
            f.append((c1, top + j, top + (j + 1) % seg))
    me = mesh_from(name, v, f, uvs if uv else None)
    return obj(name, me, m, loc)

def key(o, path, frame, value, interp="BEZIER"):
    setattr(o, path, value) if not isinstance(value, tuple) else setattr(o, path, value)
    o.keyframe_insert(data_path=path, frame=frame)
    if o.animation_data and o.animation_data.action:
        for fc in _fcurves(o.animation_data.action):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if kp.co[0] == frame:
                        kp.interpolation = interp

def _fcurves(action):
    if hasattr(action, "fcurves") and action.fcurves is not None:
        try:
            return list(action.fcurves)
        except Exception:
            pass
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out

def vis(o, frames):
    """frames: [(frame, visible)] через масштаб, ступенькой."""
    base = tuple(o.scale)
    for fr, on in frames:
        o.scale = base if on else (0.0, 0.0, 0.0)
        o.keyframe_insert("scale", frame=fr)
    for fc in _fcurves(o.animation_data.action):
        if fc.data_path == "scale":
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"
    o.scale = base

# ---------- рулон 1 (первый экран) ----------
R_OUT, R_CORE, R_W = 0.38, 0.08, 0.6
def roll(name, c):
    prof = [(R_CORE, -R_W / 2), (R_OUT, -R_W / 2), (R_OUT, R_W / 2), (R_CORE, R_W / 2)]
    o = lathe(name, prof, FILM, c, seg=64, cap=False)
    o.rotation_mode = "XYZ"
    o.rotation_euler = (math.pi / 2, 0, 0)  # ось вдоль Y
    core = lathe(name + "_core", [(R_CORE * 0.7, -R_W / 2 - 0.02), (R_CORE * 0.7, R_W / 2 + 0.02)], CLAY, (0, 0, 0), seg=32)
    core.parent = o
    # торцевые «витки» — тонкие кольца, чтобы вращение читалось
    for k, rr in enumerate([0.14, 0.22, 0.30]):
        t = lathe(f"{name}_ring{k}", [(rr, -R_W / 2 - 0.001), (rr + 0.006, -R_W / 2 - 0.001)], CLAY, (0, 0, 0), seg=48, cap=False)
        t.parent = o
    mark = box(name + "_mark", (0.05, 0.02, R_W + 0.004), (R_OUT - 0.03, 0, 0), ORANGE)
    mark.parent = o
    return o

R1C = (0.0, 0.0, 0.55)
R1 = roll("R1", R1C)
STRIP_Z = R1C[2] - R_OUT  # 0.17

# лента от рулона до рукава
strip = box("strip", (6.5, R_W, 0.002), (3.25, 0, STRIP_Z), FILM)

# 6 печатных валов
ROLL_X = [1.6 + 0.75 * i for i in range(6)]
for i, x in enumerate(ROLL_X):
    r = lathe(f"press{i}", [(0.11, -0.36), (0.11, 0.36)], CLAY, (x, 0, STRIP_Z + 0.115), seg=40)
    r.rotation_euler = (math.pi / 2, 0, 0)
    band = lathe(f"press{i}_ink", [(0.112, -0.31), (0.112, 0.31)], INK[i], (0, 0, 0), seg=40, cap=False)
    band.parent = r

# ---------- сцена 1: печать по слоям ----------
F1A, F1B = 41, 130
V = 0.06
LAYERS = [  # (dx, dy, sx, sy) в долях панели 0.35 x 0.5
    (0.0, 0.0, 1.0, 1.0), (-0.22, -0.18, 0.5, 0.55), (0.12, 0.2, 0.6, 0.35),
    (0.25, -0.22, 0.3, 0.3), (-0.05, 0.02, 0.9, 0.06), (0.3, 0.28, 0.16, 0.16)]
PL, PW = 0.35, 0.5
x0s = [-3.2 + 0.45 * k for k in range(22)]
for k, x0 in enumerate(x0s):
    for i, (dx, dy, sx, sy) in enumerate(LAYERS):
        lay = box(f"pan{k}_{i}", (PL * sx, PW * sy, 0.0006), (0, 0, 0), INK[i])
        lay.location = (x0 + dx * PL, dy * PW, STRIP_Z + 0.0012 + 0.0007 * i)
        lay.keyframe_insert("location", frame=F1A)
        lay.location = (x0 + V * (F1B - F1A) + dx * PL, dy * PW, STRIP_Z + 0.0012 + 0.0007 * i)
        lay.keyframe_insert("location", frame=F1B)
        for fc in _fcurves(lay.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        ev = [(1, False)]
        t_in = F1A + (ROLL_X[i] - x0) / V if x0 < ROLL_X[i] else None
        t_out = F1A + (6.45 - x0) / V
        if t_in is not None and F1A <= t_in <= F1B:
            ev.append((int(math.ceil(t_in)), True))
            if t_out <= F1B:
                ev.append((int(math.ceil(t_out)), False))
        if len(ev) > 1:
            vis(lay, ev)
        else:
            lay.scale = (0, 0, 0)

# ---------- сцена 2: рукав (лента сворачивается в трубу) ----------
TX0, TX1 = 6.5, 9.5
TR = R_W / (2 * math.pi)            # радиус рукава 0.0955
TZC = STRIP_Z + TR                  # ось трубы
NU, NX = 40, 30
verts, faces, uvs = [], [], []
for ix in range(NX + 1):
    x = TX0 + (TX1 - TX0) * ix / NX
    for iu in range(NU + 1):
        u = iu / NU
        verts.append((x, (u - 0.5) * R_W, STRIP_Z))
        uvs.append((u, ix / NX * 6))
for ix in range(NX):
    for iu in range(NU):
        a = ix * (NU + 1) + iu
        faces.append((a, a + 1, a + NU + 2, a + NU + 1))
tme = mesh_from("tube", verts, faces, uvs)
tube = obj("tube", tme, PRINT)
tube.shape_key_add(name="Basis")
sk = tube.shape_key_add(name="rolled", from_mix=False)
for ix in range(NX + 1):
    x = TX0 + (TX1 - TX0) * ix / NX
    for iu in range(NU + 1):
        phi = (iu / NU - 0.5) * 2 * math.pi
        sk.data[ix * (NU + 1) + iu].co = (x, TR * math.sin(phi), TZC - TR * math.cos(phi))
F2A = 131
sk.value = 0; sk.keyframe_insert("value", frame=F2A + 4)
sk.value = 1; sk.keyframe_insert("value", frame=F2A + 30)

seam = box("seam", (TX1 - TX0, 0.006, 0.003), (TX0, 0, TZC + TR + 0.002), ORANGE)
# масштаб от начала: смещаем меш так, чтобы origin был у x=TX0
for v_ in seam.data.vertices:
    v_.co.x += (TX1 - TX0) / 2
seam.scale = (0, 1, 1); seam.keyframe_insert("scale", frame=F2A + 30)
seam.scale = (1, 1, 1); seam.keyframe_insert("scale", frame=F2A + 45)

insp = lathe("inspect_ring", [(TR * 0.93, -0.004), (TR * 0.93, 0.004)], ORANGE, (TX1, 0, TZC), seg=48, cap=False)
insp.rotation_euler = (0, math.pi / 2, 0)
insp.keyframe_insert("location", frame=178)
insp.location = (TX0 + 0.3, 0, TZC); insp.keyframe_insert("location", frame=198)
vis(insp, [(1, False), (176, True), (199, False)])

# ---------- сцена 3: бутылка и усадка ----------
B1 = (10.3, 0.0, 0.0)
def bottle_prof():
    return [(0.0, 0.0), (0.082, 0.004), (0.085, 0.02), (0.085, 0.16), (0.075, 0.19), (0.05, 0.225),
            (0.031, 0.25), (0.03, 0.29), (0.034, 0.295), (0.034, 0.325)]
def r_at(z):
    p = bottle_prof()
    for (r0, z0), (r1, z1) in zip(p, p[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / max(1e-6, z1 - z0)
            return r0 + (r1 - r0) * t
    return p[-1][0]

def bottle(name, loc):
    return lathe(name, bottle_prof()[1:], CLAY, loc, seg=48)

table = box("table", (6.8, 1.2, 0.04), (13.2, 0, -0.02), TABLE)
b1 = bottle("bottle1", B1)

def sleeve_mesh(name, z0, z1, r_loose, target_r, bands, nz=36, seg=48):
    v, f, uvs = [], [], []
    for i in range(nz + 1):
        z = z0 + (z1 - z0) * i / nz
        for j in range(seg):
            a = 2 * math.pi * j / seg
            v.append((r_loose * math.cos(a), r_loose * math.sin(a), z))
            uvs.append((j / seg, i / nz))
    for i in range(nz):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            f.append((a, b, b + seg, a + seg))
    me = mesh_from(name, v, f, uvs)
    o = obj(name, me, PRINT)
    o.shape_key_add(name="Basis")
    keys = []
    for bk in range(bands):
        k = o.shape_key_add(name=f"band{bk}", from_mix=False)
        for i in range(nz + 1):
            band = min(bands - 1, int(i / (nz + 1) * bands))
            z = z0 + (z1 - z0) * i / nz
            rr = target_r(z) if band == bk else r_loose
            for j in range(seg):
                a = 2 * math.pi * j / seg
                idx = i * seg + j
                k.data[idx].co = (rr * math.cos(a), rr * math.sin(a), z)
        keys.append(k)
    return o, keys

slv, sk_bands = sleeve_mesh("sleeve1", 0.012, 0.255, TR, lambda z: r_at(z) + 0.0025, 8)
# путь: горизонтально у конца трубы -> вертикально над бутылкой -> вниз
slv.rotation_mode = "XYZ"
slv.location = (TX1 + 0.02, 0, TZC); slv.rotation_euler = (0, math.pi / 2, 0)
slv.keyframe_insert("location", frame=200); slv.keyframe_insert("rotation_euler", frame=200)
slv.location = (B1[0], 0, 0.42); slv.rotation_euler = (0, 0, 0)
slv.keyframe_insert("location", frame=226); slv.keyframe_insert("rotation_euler", frame=226)
slv.location = (B1[0], 0, 0.0); slv.keyframe_insert("location", frame=242)
vis(slv, [(1, False), (199, True)])
for bk, k in enumerate(sk_bands):
    k.value = 0; k.keyframe_insert("value", frame=248 + bk * 6)
    k.value = 1; k.keyframe_insert("value", frame=262 + bk * 6)

heat = lathe("heat_ring", [(0.12, -0.003), (0.12, 0.003)], ORANGE, (B1[0], 0, 0.0), seg=48, cap=False)
heat.keyframe_insert("location", frame=246)
heat.location = (B1[0], 0, 0.27); heat.keyframe_insert("location", frame=306)
vis(heat, [(1, False), (245, True), (308, False)])

# повороты бутылки 1 в сцене 4 (вместе с рукавом)
for o in (b1,):
    o.keyframe_insert("rotation_euler", frame=335)
    o.rotation_euler = (0, 0, math.pi); o.keyframe_insert("rotation_euler", frame=352)

# ---------- сцена 4: шесть упаковок ----------
PX = [10.3, 11.4, 12.5, 13.6, 14.7, 15.9]
# 2. колпачок
b2 = bottle("bottle2", (PX[1], 0, 0))
cap_s, cap_k = sleeve_mesh("capsleeve", 0.0, 0.06, 0.045, lambda z: 0.0365, 1, nz=8)
cap_s.location = (PX[1], 0, 0.55); cap_s.keyframe_insert("location", frame=358)
cap_s.location = (PX[1], 0, 0.272); cap_s.keyframe_insert("location", frame=368)
cap_k[0].value = 0; cap_k[0].keyframe_insert("value", frame=369)
cap_k[0].value = 1; cap_k[0].keyframe_insert("value", frame=378)
cap_top = lathe("captop", [(0.0365, 0.0), (0.0365, 0.002)], ORANGE, (0, 0, 0.06), seg=32)
cap_top.parent = cap_s
vis(cap_s, [(1, False), (357, True)])

# 3-4. стаканы
CUP = [(0.0, 0.0), (0.034, 0.0), (0.036, 0.004), (0.05, 0.09), (0.053, 0.092), (0.053, 0.095)]
def cup_r(z):
    return 0.034 + (0.05 - 0.034) * min(1, max(0, z / 0.09))
cup1 = lathe("cup1", CUP[1:], CLAY, (PX[2], 0, 0), seg=48)
cs, ck = sleeve_mesh("cupsleeve", 0.006, 0.086, 0.058, lambda z: cup_r(z) + 0.002, 4, nz=16)
cs.location = (PX[2], 0, 0.3); cs.keyframe_insert("location", frame=386)
cs.location = (PX[2], 0, 0.0); cs.keyframe_insert("location", frame=394)
vis(cs, [(1, False), (385, True)])
for bk, k in enumerate(ck):
    k.value = 0; k.keyframe_insert("value", frame=395 + bk * 3)
    k.value = 1; k.keyframe_insert("value", frame=403 + bk * 3)
for o in (cup1, cs):
    o.keyframe_insert("rotation_euler", frame=395)
    o.rotation_euler = (0, 0, math.pi * 0.8); o.keyframe_insert("rotation_euler", frame=412)

cup2 = lathe("cup2", CUP[1:], CLAY, (PX[3], 0, 0), seg=48)
cs2, ck2 = sleeve_mesh("cupsleeve2", 0.006, 0.086, 0.058, lambda z: cup_r(z) + 0.002, 1, nz=16)
cs2.location = (PX[3], 0, 0); ck2[0].value = 1
lid = lathe("lid", [(0.0, 0.0), (0.058, 0.0), (0.058, 0.002), (0.0, 0.002)], CLAY, (PX[3], 0, 0.32), seg=64, cap=False)
for k, rr in enumerate([0.012, 0.024, 0.036, 0.048]):  # условное тиснение
    e = lathe(f"emb{k}", [(rr, 0.0021), (rr + 0.003, 0.0021)], ORANGE if k % 2 else TEAL, (0, 0, 0), seg=48, cap=False)
    e.parent = lid
lid.keyframe_insert("location", frame=418)
lid.location = (PX[3], 0, 0.0955); lid.keyframe_insert("location", frame=428)

# 5. кашированная фольга: 4 слоя
FOIL_M = [mat("foil0", lin((190, 190, 196))), mat("foil1", lin((236, 236, 240))), ORANGE, mat("foil3", lin((120, 120, 128)))]
foil_root = bpy.data.objects.new("foil", None); sc.collection.objects.link(foil_root)
foil_root.location = (PX[4], 0, 0.04); foil_root.rotation_euler = (math.radians(-18), 0, math.radians(12))
for k in range(4):
    L = box(f"foil_l{k}", (0.24, 0.17, 0.003), (0, 0, k * 0.0035), FOIL_M[k])
    L.parent = foil_root
    L.keyframe_insert("location", frame=446)
    L.location = (0, 0, k * 0.055); L.keyframe_insert("location", frame=458)
    L.keyframe_insert("location", frame=464)
    L.location = (0, 0, k * 0.0035); L.keyframe_insert("location", frame=472)

# 6. групповая упаковка
grp = []
for gi in range(3):
    for gj in range(2):
        b = bottle(f"gb{gi}{gj}", (PX[5] + (gi - 1) * 0.26, (gj - 0.5) * 0.26, 0))
        b.keyframe_insert("location", frame=476)
        b.location = (PX[5] + (gi - 1) * 0.172, (gj - 0.5) * 0.172, 0)
        b.keyframe_insert("location", frame=486)
        grp.append(b)
pack = bpy.data.objects.new("pack", None); sc.collection.objects.link(pack)
pack.location = (PX[5], 0, 0.165)
PW_, PD_, PH_ = 0.53, 0.36, 0.34
walls = [((PW_, 0.004, PD_), (0, 0, 0)), ]
for nm, size, loc in [("top", (PW_, PD_, 0.004), (0, 0, PH_ / 2)), ("bot", (PW_, PD_, 0.004), (0, 0, -PH_ / 2)),
                      ("l", (0.004, PD_, PH_), (-PW_ / 2, 0, 0)), ("r", (0.004, PD_, PH_), (PW_ / 2, 0, 0))]:
    w = box("pack_" + nm, size, loc, mat("packfilm", lin((236, 224, 205))))
    w.parent = pack
pack.scale = (1.25, 1.25, 1.12); pack.keyframe_insert("scale", frame=487)
pack.scale = (1.0, 1.0, 1.0); pack.keyframe_insert("scale", frame=497)
vis(pack, [(1, False), (487, True)])
# масштаб vis перекрывает анимацию — повторно ставим ключи усадки после vis
pack.scale = (1.25, 1.25, 1.12); pack.keyframe_insert("scale", frame=488)
pack.scale = (1.0, 1.0, 1.0); pack.keyframe_insert("scale", frame=497)

# ---------- сцена 5: выдача (вид сверху) ----------
SPL = (19.2, 0.0)
feed = box("feed", (1.4, 0.3, 0.002), (18.5, 0, 0.002), FILM)
targets = [(21.0, -0.85), (21.0, 0.0), (21.0, 0.85)]
branches = []
for bi, (tx, ty) in enumerate(targets):
    dx, dy = tx - 0.45 - SPL[0], ty - SPL[1]
    L = math.hypot(dx, dy)
    br = box(f"branch{bi}", (L, 0.22, 0.002), (SPL[0] + dx / 2, SPL[1] + dy / 2, 0.002), FILM)
    br.rotation_euler = (0, 0, math.atan2(dy, dx))
    branches.append(br)
    for m_ in range(5):  # метки движения
        mk = box(f"flow{bi}_{m_}", (0.08, 0.16, 0.002), (0, 0, 0), ORANGE)
        for fr, t in [(505, m_ / 5), (550, m_ / 5 + 1.6)]:
            tt = t % 1.0 if fr == 505 else t
            p = (SPL[0] + dx * min(tt, 1.0), SPL[1] + dy * min(tt, 1.0), 0.004)
            mk.location = p
            mk.keyframe_insert("location", frame=fr)
        mk.rotation_euler = (0, 0, math.atan2(dy, dx))
        for fc in _fcurves(mk.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        vis(mk, [(1, False), (503, True), (552, False)])
        branches.append(mk)

R2C = (21.0, -0.85, 0.55)
R2 = roll("R2", R2C)
R3 = lathe("R3", [(0.06, -0.12), (0.22, -0.12), (0.22, 0.12), (0.06, 0.12)], FILM, (21.0, 0.0, 0.22), seg=48, cap=False)
R3.rotation_euler = (math.pi / 2, 0, 0)
R3p = lathe("R3_print", [(0.222, -0.11), (0.222, 0.11)], PRINT, (0, 0, 0), seg=48, cap=False)
R3p.parent = R3
stack = []
for s in range(10):
    p = box(f"piece{s}", (0.22, 0.30, 0.012), (21.0, 0.85, 0.006 + s * 0.014), PRINT)
    vis(p, [(1, False), (510 + s * 4, True)])
    stack.append(p)
for o in [R3, feed] + branches + stack:
    pass

# ---------- сцена 6: годовые кольца на торце R2 ----------
FACE_Y = R2C[1] - R_W / 2 - 0.003
for k, (rr, fr) in enumerate([(0.13, 566), (0.20, 576), (0.27, 586), (0.34, 596)]):
    ring = lathe(f"year{k}", [(rr, -0.002), (rr + 0.012, -0.002)], ORANGE, (R2C[0], FACE_Y, R2C[2]), seg=64, cap=False)
    ring.rotation_euler = (math.pi / 2, 0, 0)
    vis(ring, [(1, False), (fr, True), (607, False)])
# прячем лишнее перед финальным ракурсом
for o in [R3, R3p, feed] + [b for b in branches if b.name.startswith("branch")] + stack:
    if o.parent is None:
        vis(o, [(1, True), (604, False)]) if not o.animation_data else None

# ---------- вращение рулонов ----------
def spin(o, f0, f1, turns):
    o.keyframe_insert("rotation_euler", frame=f0)
    e = o.rotation_euler.copy(); e.y += turns * 2 * math.pi
    o.rotation_euler = e; o.keyframe_insert("rotation_euler", frame=f1)
    for fc in _fcurves(o.animation_data.action):
        if fc.data_path == "rotation_euler":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
spin(R1, 1, F1B, -1.6)
spin(R2, 600, F_END, -0.25)

# ---------- камера ----------
cam_d = bpy.data.cameras.new("CAM_main")
cam = bpy.data.objects.new("CAM_main", cam_d); sc.collection.objects.link(cam)
sc.camera = cam
cam_d.lens = 35; cam_d.clip_start = 0.005; cam_d.clip_end = 100
cam_d.shift_x = -0.16
tgt = bpy.data.objects.new("CAM_target", None); sc.collection.objects.link(tgt)
c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"

def hero(cx, cy, cz):
    return ((cx + 1.6, cy - 2.2, cz + 0.25), (cx, cy, cz))
CAM = [
    (1, *hero(*R1C)), (40, *hero(*R1C)),
    (62, (1.4, -1.9, 0.85), (1.4, 0, 0.22)),
    (95, (3.2, -1.55, 0.8), (3.2, 0, 0.2)),
    (128, (5.5, -1.35, 0.7), (5.7, 0, 0.2)),
    (152, (7.4, -1.25, 0.55), (7.9, 0, TZC)),
    (170, (7.6, -0.7, 0.75), (8.1, 0, TZC)),
    (183, (5.95, 0, TZC), (7.0, 0, TZC)),
    (200, (9.3, 0, TZC), (10.3, 0, TZC)),
    (214, (9.85, -0.55, 0.72), (10.3, 0, 0.28)),
    (242, (10.3, -0.85, 0.42), (10.3, 0, 0.16)),
    (300, (10.3 + 0.85 * math.sin(math.radians(30)), -0.85 * math.cos(math.radians(30)), 0.38), (10.3, 0, 0.16)),
    (320, (10.3 + 0.85 * math.sin(math.radians(30)), -0.85 * math.cos(math.radians(30)), 0.38), (10.3, 0, 0.16)),
    (336, (PX[0], -1.0, 0.34), (PX[0], 0, 0.15)), (350, (PX[0], -1.0, 0.34), (PX[0], 0, 0.15)),
    (364, (PX[1], -0.95, 0.38), (PX[1], 0, 0.2)), (380, (PX[1], -0.95, 0.38), (PX[1], 0, 0.2)),
    (393, (PX[2], -0.6, 0.22), (PX[2], 0, 0.05)), (410, (PX[2], -0.6, 0.22), (PX[2], 0, 0.05)),
    (422, (PX[3], -0.6, 0.24), (PX[3], 0, 0.06)), (429, (PX[3], -0.6, 0.24), (PX[3], 0, 0.06)),
    (440, (PX[3], -0.16, 0.24), (PX[3], 0, 0.095)),
    (453, (PX[4], -0.75, 0.38), (PX[4], 0, 0.1)), (472, (PX[4], -0.75, 0.38), (PX[4], 0, 0.1)),
    (484, (PX[5], -1.15, 0.5), (PX[5], 0, 0.15)), (500, (PX[5], -1.15, 0.5), (PX[5], 0, 0.15)),
    (516, (20.0, -0.9, 3.6), (20.25, 0, 0)), (540, (20.0, -0.9, 3.6), (20.25, 0, 0)),
    (566, (21.0, -2.75, 0.55), (21.0, FACE_Y, 0.55)),
    (600, (21.0, -2.35, 0.55), (21.0, FACE_Y, 0.55)),
    (614, *hero(*R2C)), (F_END, *hero(*R2C)),
]
for fr, cl, tl in CAM:
    cam.location = cl; cam.keyframe_insert("location", frame=fr)
    tgt.location = tl; tgt.keyframe_insert("location", frame=fr)
for fr, lens in [(1, 35), (176, 35), (184, 18), (198, 18), (208, 35), (428, 35), (440, 50), (446, 35)]:
    cam_d.lens = lens; cam_d.keyframe_insert("lens", frame=fr)

# ---------- после выхода из рукава лента и труба больше не нужны ----------
for n in ["tube", "seam", "strip", "inspect_ring"] + [o.name for o in bpy.data.objects if o.name.startswith("press") or o.name.startswith("pan")]:
    o = bpy.data.objects.get(n)
    if o is None:
        continue
    o.hide_render = False; o.keyframe_insert("hide_render", frame=232)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=233)
    o.hide_render = False

# текстура печати из файла, если есть (print.png рядом со скриптом)
import os
_pp = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(), "print.png")
if os.path.exists(_pp):
    tex.image = bpy.data.images.load(_pp)

# ---------- прячем всё, кроме рулона R2, перед финальным ракурсом ----------
def in_r2(o):
    while o:
        if o.name == "R2":
            return True
        o = o.parent
    return False
for o in list(bpy.data.objects):
    if o.type != "MESH" or in_r2(o):
        continue
    o.hide_render = False; o.keyframe_insert("hide_render", frame=1)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=607)
    o.hide_render = False

# ---------- рендер: EEVEE, светлая «глина» ----------
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 16
except Exception:
    pass
if sc.world is None:
    sc.world = bpy.data.worlds.new("World")
w = sc.world; w.use_nodes = True
bgn = w.node_tree.nodes.get("Background")
bgn.inputs[0].default_value = (*lin((245, 238, 229)), 1.0)
bgn.inputs[1].default_value = 1.0
wn = w.node_tree.nodes; wl = w.node_tree.links
amb = wn.new("ShaderNodeBackground"); amb.inputs[0].default_value = (1, 1, 1, 1); amb.inputs[1].default_value = 0.55
lp = wn.new("ShaderNodeLightPath"); mix = wn.new("ShaderNodeMixShader")
outn = wn.get("World Output")
wl.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
wl.new(amb.outputs[0], mix.inputs[1]); wl.new(bgn.outputs[0], mix.inputs[2])
wl.new(mix.outputs[0], outn.inputs[0])
for m in bpy.data.materials:
    m.use_nodes = True
    pb = m.node_tree.nodes.get("Principled BSDF")
    if pb is None:
        continue
    if not pb.inputs[0].is_linked:
        pb.inputs[0].default_value = m.diffuse_color
    pb.inputs["Roughness"].default_value = 0.45
sun_d = bpy.data.lights.new("LGT_key", "SUN"); sun_d.energy = 2.8; sun_d.angle = 0.6
sun_d.use_shadow = False
sun = bpy.data.objects.new("LGT_key", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.resolution_percentage = 100

result = {"objects": len(bpy.data.objects), "frames": F_END}

#!/usr/bin/env python3
"""Склейка клипов c01..c13 в кадры главной v2 с наплывом 0,25 с на стыках + петля первого экрана.
Выход: ../../v2/frames/vNNNN.jpg, ../../v2/frames/n.js, ../../v2/hero.mp4, ../../v2/hero.jpg"""
import subprocess, os, shutil, json, glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
OUT = "../../v2"
W, Q, FPS, XF = 1152, 8, 24, 0.25
clips = [f"clips/c{k:02d}.mp4" for k in range(1, 14)]
dur = [float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c],
                            capture_output=True, text=True).stdout) for c in clips]
inputs, parts, starts = [], [], [1]
for i, c in enumerate(clips):
    inputs += ["-i", c]
    parts.append(f"[{i}:v]fps={FPS},scale={W}:-2,setsar=1,settb=AVTB[v{i}]")
chain, prev, off = [], "v0", 0.0
for i in range(1, len(clips)):
    off += dur[i - 1] - XF
    nxt = f"x{i}"
    chain.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[{nxt}]")
    starts.append(int(round((off + XF / 2) * FPS)) + 1)  # середина наплыва = граница клипа
    prev = nxt
fc = ";".join(parts + chain)
shutil.rmtree(f"{OUT}/frames", ignore_errors=True); os.makedirs(f"{OUT}/frames")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", fc, "-map", f"[{prev}]",
                "-q:v", str(Q), f"{OUT}/frames/v%04d.jpg"], check=True)
n = len(glob.glob(f"{OUT}/frames/v*.jpg"))
open(f"{OUT}/frames/n.js", "w").write("window.V2=" + json.dumps({"n": n, "c": [0] + starts + [n]}) + ";")
shutil.copy(f"{OUT}/frames/v0001.jpg", f"{OUT}/hero.jpg")
if os.path.exists("clips/loop.mp4"):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "clips/loop.mp4", "-filter_complex",
                    f"[0:v]fps={FPS},scale={W}:-2,split[a][b];[a]trim=1:10,setpts=PTS-STARTPTS[x];[b]trim=0:1,setpts=PTS-STARTPTS[y];"
                    "[x][y]xfade=transition=fade:duration=1:offset=8,format=yuv420p",
                    "-an", "-c:v", "libx264", "-crf", "24", "-movflags", "+faststart", f"{OUT}/hero.mp4"], check=True)
print(open(f"{OUT}/frames/n.js").read())
print(subprocess.run(["du", "-sh", f"{OUT}/frames"], capture_output=True, text=True).stdout)

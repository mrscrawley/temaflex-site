#!/bin/zsh
# склейка трёх клипов Kling в кадры пробы: t1.mp4 t2.mp4 t3.mp4 -> frames/pNNNN.jpg
set -e
cd "$(dirname "$0")"
rm -rf frames && mkdir -p frames
# последний кадр каждого клипа = первый следующего; дубль выкидываем
ffmpeg -loglevel error -y -i clips/t1.mp4 -i clips/t2.mp4 -i clips/t3.mp4 -filter_complex \
 "[0:v]fps=24,scale=1280:-2,setsar=1[a];[1:v]fps=24,scale=1280:-2,setsar=1,trim=start_frame=1,setpts=PTS-STARTPTS[b];[2:v]fps=24,scale=1280:-2,setsar=1,trim=start_frame=1,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[v]" \
 -map "[v]" -q:v 4 frames/p%04d.jpg
n=$(ls frames | wc -l | tr -d ' ')
echo "window.PROBE_N=$n;" > frames/n.js
echo "frames: $n"; du -sh frames

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
デバッグ強化版:
- .zms / .zip / .lzh の検出ログ
- zmusic / ffmpeg の存在確認
- FFmpeg の出力を抑制せず表示
"""

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile

def extract_archive(path, dest):
    ext = os.path.splitext(path)[1].lower()
    print(f"[DEBUG] extract_archive: {path} -> {dest}")
    if ext == '.zip':
        with zipfile.ZipFile(path, 'r') as z:
            for member in z.namelist():
                normalized = os.path.normpath(member)
                if normalized.startswith('..') or os.path.isabs(normalized):
                    print(f"[WARN] スキップ不正パス: {member}", file=sys.stderr)
                    continue
                target = os.path.join(dest, normalized)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(member) as src, open(target, 'wb') as dst:
                    dst.write(src.read())
    elif ext == '.lzh':
        subprocess.run(['lhasa', 'x', path, dest], check=True)
    else:
        return False
    return True

def convert_file(zms_path: str, mp3_path: str, bitrate: str):
    print(f"[DEBUG] convert_file called on {zms_path}")
    # コマンド存在チェック
    for cmd in ('zmusic','ffmpeg'):
        try:
            which = subprocess.run(['which', cmd], check=True, stdout=subprocess.PIPE).stdout.decode().strip()
            print(f"[DEBUG] {cmd} found at {which}")
        except subprocess.CalledProcessError:
            print(f"[ERROR] {cmd} が見つかりません。", file=sys.stderr)
            return

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name

    try:
        print(f"[INFO] ZMusic → WAV: {zms_path}")
        subprocess.run(['zmusic', '-w', wav_path, zms_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print(f"[INFO] WAV → MP3: {wav_path} → {mp3_path} (bitrate {bitrate})")
        # FFmpeg 出力を表示
        ff = subprocess.run(
            [
                'ffmpeg', '-y',
                '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-b:a', bitrate,
                mp3_path
            ],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(ff.stdout.decode())

        if os.path.exists(mp3_path):
            print(f"[OK] Created {mp3_path}")
        else:
            print(f"[ERROR] {mp3_path} が生成されませんでした。", file=sys.stderr)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 変換失敗: {zms_path} ({e})", file=sys.stderr)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

def process_path(path, out_root, bitrate, src_root):
    abs_out = os.path.abspath(out_root)
    abs_path = os.path.abspath(path)
    # 出力ディレクトリ以下は無限ループ回避のためスキップ
    if abs_path.startswith(abs_out + os.sep):
        return

    if os.path.isdir(path):
        for fn in os.listdir(path):
            process_path(os.path.join(path, fn), out_root, bitrate, src_root)
    else:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.zms':
            print(f"[FOUND] ZMS file: {path}")
            rel = os.path.relpath(path, src_root)
            out_fn = os.path.splitext(rel)[0] + '.mp3'
            out_path = os.path.join(out_root, out_fn)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            convert_file(path, out_path, bitrate)
        elif ext in ('.zip', '.lzh'):
            print(f"[FOUND] Archive: {path}")
            with tempfile.TemporaryDirectory() as td:
                try:
                    extract_archive(path, td)
                    process_path(td, out_root, bitrate, src_root)
                except Exception as e:
                    print(f"[WARN] 展開失敗: {path} ({e})", file=sys.stderr)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ZMusic → MP3 一括変換（デバッグ強化版）'
    )
    parser.add_argument('-s','--src-dir', required=True, help='検索ルートディレクトリ')
    parser.add_argument('-o','--out-dir', required=True, help='出力ディレクトリ')
    parser.add_argument('-b','--bitrate', default='320k', help='MP3 ビットレート')
    args = parser.parse_args()

    print(f"[INFO] src-dir = {args.src_dir}, out-dir = {args.out_dir}, bitrate = {args.bitrate}")
    os.makedirs(args.out_dir, exist_ok=True)
    process_path(args.src_dir, args.out_dir, args.bitrate, args.src_dir)

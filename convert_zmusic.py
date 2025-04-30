#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アーカイブ（.zip/.lzh）と .zms ファイルを再帰的に探し、
ZMusic → WAV → MP3 にまとめて変換するスクリプト。

前提：
  ・システムに zmusic CLI と ffmpeg、lhasa（LZH 展開用）がインストール済み
  ・Python 3.6+ 環境
"""

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile

def extract_archive(path, dest):
    ext = os.path.splitext(path)[1].lower()
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
    print(f"[INFO] Converting {zms_path} → {mp3_path}")
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name

    try:
        subprocess.run(['zmusic', '-w', wav_path, zms_path], check=True)
        subprocess.run(
            ['ffmpeg', '-y', '-i', wav_path,
             '-codec:a', 'libmp3lame', '-b:a', bitrate,
             mp3_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
        print(f"[OK] {os.path.basename(zms_path)} → {os.path.basename(mp3_path)}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 処理失敗: {zms_path} ({e})", file=sys.stderr)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

def process_path(path, out_root, bitrate, src_root):
    # out_root 以下はスキップ
    abs_out = os.path.abspath(out_root)
    abs_path = os.path.abspath(path)
    if abs_path.startswith(abs_out + os.sep):
        return

    if os.path.isdir(path):
        for fn in os.listdir(path):
            process_path(os.path.join(path, fn), out_root, bitrate, src_root)
    else:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.zms':
            rel = os.path.relpath(path, src_root)
            out_fn = os.path.splitext(rel)[0] + '.mp3'
            out_path = os.path.join(out_root, out_fn)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            convert_file(path, out_path, bitrate)
        elif ext in ('.zip', '.lzh'):
            with tempfile.TemporaryDirectory() as td:
                try:
                    extract_archive(path, td)
                    process_path(td, out_root, bitrate, src_root)
                except Exception as e:
                    print(f"[WARN] 展開失敗: {path} ({e})", file=sys.stderr)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ZMusic 専用音源を一括 MP3 変換（アーカイブ展開対応）'
    )
    parser.add_argument('-s', '--src-dir', required=True,
                        help='検索開始ディレクトリ（アーカイブと .zms を再帰探索）')
    parser.add_argument('-o', '--out-dir', required=True,
                        help='変換後 MP3 出力先ディレクトリ')
    parser.add_argument('-b', '--bitrate', default='320k',
                        help='MP3 ビットレート（例: 128k, 192k, 320k）')
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    print(f"[INFO] src-dir = {args.src_dir}")
    print(f"[INFO] out-dir = {args.out_dir}")
    process_path(args.src_dir, args.out_dir, args.bitrate, args.src_dir)

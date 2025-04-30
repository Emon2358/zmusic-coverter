#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アーカイブ（.zip/.lzh）と .zms ファイルを再帰的に探し、
ZMusic → WAV → MP3 にまとめて変換するスクリプト。

前提：
  ・システムに zmusic CLI と ffmpeg、7z（p7zip-full）がインストール済み
  ・Python 3.6+ 環境

使い方例：
  $ python convert_zmusic.py \
      --src-dir ./ \
      --out-dir ./output_mp3 \
      --bitrate 320k
"""

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile

def extract_archive(path, dest):
    """.zip は zipfile、.lzh は 7z で展開"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.zip':
        with zipfile.ZipFile(path, 'r') as z:
            z.extractall(dest)
    elif ext == '.lzh':
        # p7zip の 7z コマンドで LZH 展開
        subprocess.run(['7z', 'x', path, f'-o{dest}', '-y'], check=True)
    else:
        return False
    return True

def convert_file(zms_path: str, mp3_path: str, bitrate: str):
    """ZMusic → WAV → MP3"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name

    try:
        subprocess.run(
            ['zmusic', '-w', wav_path, zms_path],
            check=True
        )
        subprocess.run(
            [
                'ffmpeg', '-y', '-i', wav_path,
                '-codec:a', 'libmp3lame', '-b:a', bitrate,
                mp3_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
        print(f'[OK] {os.path.basename(zms_path)} → {os.path.basename(mp3_path)}')
    except subprocess.CalledProcessError as e:
        print(f'[ERROR] 処理失敗: {zms_path} ({e})', file=sys.stderr)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

def process_path(path, out_root, bitrate, src_root):
    """
    1) ディレクトリなら再帰
    2) .zms → 変換
    3) .zip/.lzh → 展開して中を再帰処理
    """
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
                    print(f'[WARN] 展開失敗: {path} ({e})', file=sys.stderr)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ZMusic 専用音源を一括 MP3 変換（アーカイブ展開対応）'
    )
    parser.add_argument(
        '--src-dir', '-s', required=True,
        help='検索開始ディレクトリ（アーカイブと .zms を再帰探索）'
    )
    parser.add_argument(
        '--out-dir', '-o', required=True,
        help='変換後 MP3 出力先ディレクトリ'
    )
    parser.add_argument(
        '--bitrate', '-b', default='320k',
        help='MP3 ビットレート（例: 128k, 192k, 320k）'
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    process_path(args.src_dir, args.out_dir, args.bitrate, args.src_dir)

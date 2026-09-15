import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', *map(str, args)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--videos', nargs=3, type=Path, required=True)
    parser.add_argument('--photos', nargs=2, type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('public/doomfly'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {'physical_setup': [], 'chess_run': args.run.name,
                'physical_media_note': 'Owner-provided setup footage; web copies are silent and metadata-stripped.',
                'chess_replay_note': 'Recorded selection snapshots, not real-time video or living-fly footage.'}
    for i, source in enumerate(args.videos, 1):
        video = args.out / f'setup-{i}.mp4'
        poster = args.out / f'setup-{i}.jpg'
        ffmpeg('-i', source, '-map', '0:v:0', '-vf', 'scale=478:-2,fps=24', '-c:v', 'libx264',
               '-crf', '26', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-an', '-map_metadata', '-1',
               '-movflags', '+faststart', video)
        ffmpeg('-ss', '1', '-i', video, '-frames:v', '1', '-q:v', '3', poster)
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest['physical_setup'].append({'asset': video.name, 'source_sha256': digest,
                                            'source_filename': source.name})
    for i, source in enumerate(args.photos, 1):
        photo = args.out / f'setup-photo-{i}.jpg'
        ffmpeg('-i', source, '-vf', 'scale=1200:1200:force_original_aspect_ratio=decrease',
               '-q:v', '3', '-map_metadata', '-1', photo)
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest['physical_setup'].append({'asset': photo.name, 'source_sha256': digest,
                                            'source_filename': source.name})
    ffmpeg('-ss', '1', '-i', args.out / 'setup-2.mp4', '-vf', 'crop=478:550:0:100,scale=960:1104',
           '-frames:v', '1', '-q:v', '2', args.out / 'arena.jpg')
    ffmpeg('-i', args.run / 'selection-replay.gif', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
           '-crf', '22', '-movflags', '+faststart', '-an', '-map_metadata', '-1', args.out / 'chess-replay.mp4')
    ffmpeg('-ss', '0', '-i', args.out / 'chess-replay.mp4', '-frames:v', '1', '-q:v', '2', args.out / 'chess-replay.jpg')
    moves = [json.loads(line) for line in (args.run / 'moves.jsonl').read_text().splitlines()]
    summary = json.loads((args.run / 'summary.json').read_text())
    protocol = json.loads((args.run / 'protocol.json').read_text())
    for name in ('match.pgn', 'summary.json', 'protocol.json'):
        with (args.out / name).open('wb') as target:
            target.write((args.run / name).read_bytes())
    with (args.out / 'chess-game.json').open('w', encoding='utf-8') as stream:
        json.dump({'run': args.run.name, 'summary': summary, 'protocol': protocol, 'moves': moves}, stream, indent=2)
    with (args.out / 'media-provenance.json').open('w', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
    print(f'Prepared {len(moves)} recorded chess plies, three setup clips, and two setup photos in {args.out}')


if __name__ == '__main__':
    main()

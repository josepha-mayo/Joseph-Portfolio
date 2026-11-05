"""Reproduce R4 rejection and check R8 admission on three authored 48 MP files."""
from pathlib import Path
import argparse, hashlib, json, resource, subprocess, sys, tempfile, time
from PIL import Image, ImageDraw
import PIL
import views, original_views


def case(fmt):
    with tempfile.TemporaryDirectory(prefix='von-r8-') as temp:
        p = Path(temp) / ('large.' + fmt.lower())
        image = Image.new('RGB', (8000, 6000), (19, 71, 201))
        draw = ImageDraw.Draw(image)
        draw.rectangle((100, 100, 600, 500), fill=(230, 40, 20))
        options = {'compression': 'tiff_deflate'} if fmt == 'TIFF' else ({'quality': 95} if fmt == 'JPEG' else {})
        image.save(p, format=fmt, **options); image.close()
        baseline_rejected = False
        try:
            old = original_views.load_image(p); old.close()
        except ValueError as error:
            baseline_rejected = str(error) == 'Image exceeds configured decode budget'
        assert baseline_rejected, 'Baseline no longer reproduces the expected failure'
        started = time.monotonic()
        new = views.load_image(p)
        elapsed = time.monotonic() - started
        assert new.size == (8000, 6000) and new.mode == 'RGB'
        for position, expected in [((0, 0), (19, 71, 201)), ((400, 300), (230, 40, 20)), ((7999, 5999), (19, 71, 201))]:
            assert max(abs(a-b) for a,b in zip(new.getpixel(position), expected)) <= (4 if fmt == 'JPEG' else 0)
        new.close()
        assert elapsed < 20, 'Decode alone exceeded the integration test allowance'
        return {'format': fmt, 'pixels': 48000000, 'r4_rejected': True,
                'r8_decoded': True, 'mode': 'RGB', 'decode_seconds': elapsed,
                'peak_process_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'rss_scope': 'Whole fixture process including image construction, not decoder delta',
                'file_bytes': p.stat().st_size, 'authored_fixture': True}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--format', choices=['PNG', 'JPEG', 'TIFF']); parser.add_argument('--out', type=Path, default=Path('LARGE_IMAGE_RESULTS.json'))
    args = parser.parse_args()
    if args.format:
        print(json.dumps(case(args.format))); return
    results = []
    for fmt in ('PNG', 'JPEG', 'TIFF'):
        run = subprocess.run([sys.executable, __file__, '--format', fmt], text=True, capture_output=True, timeout=35)
        if run.returncode: raise RuntimeError(run.stderr[-1500:])
        results.append(json.loads(run.stdout))
    report = {'status': 'passed', 'scope': 'Image decoding only; not GPU inference, OCR accuracy, or final-image validation',
              'python': sys.version.split()[0], 'pillow': PIL.__version__, 'pillow_safety_threshold_pixels': Image.MAX_IMAGE_PIXELS,
              'baseline_sha256': hashlib.sha256(Path(original_views.__file__).read_bytes()).hexdigest(),
              'candidate_sha256': hashlib.sha256(Path(views.__file__).read_bytes()).hexdigest(), 'cases': results}
    args.out.write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report, indent=2))

if __name__ == '__main__': main()

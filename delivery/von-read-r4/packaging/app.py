"""Official-shaped per-image command; no model import or download here."""
import sys
from von_read.warm_runtime import main

if __name__ == '__main__':
    raise SystemExit(main(['infer', *sys.argv[1:]]))

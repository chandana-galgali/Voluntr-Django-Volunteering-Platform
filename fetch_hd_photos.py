"""Fetch optional high-resolution stock photography; review suitability and Unsplash terms before publication."""
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image
from io import BytesIO
ROOT = Path(__file__).resolve().parent / 'static' / 'img'
SOURCES = {
    'hero': '1559027615-cd4628902d4a',
    'education': '1503676260728-1c00da094a0b',
    'environment': '1542601906990-b4d3fb778b09',
    'animals': '1548199973-03cce0bbc87b',
    'food-security': '1593113598332-cd288d649433',
    'community': '1511632765486-a01980e01a18',
    'health': '1576091160399-112ba8d25d1d',
    'technology': '1516321318423-f06f85e504b3',
    'sports': '1461896836934-ffe607ba8211',
    'disaster-relief': '1469571486292-0ba58a3f068b',
}
for name, ident in SOURCES.items():
    url = f'https://images.unsplash.com/photo-{ident}?w=3000&q=95&fit=max&fm=jpg'
    try:
        with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=30) as res:
            photo = Image.open(BytesIO(res.read())).convert('RGB')
        if photo.width < 1800 or photo.height < 900:
            raise ValueError(f'Insufficient source resolution: {photo.size}')
        dest = ROOT / (name + '.jpg')
        photo.save(dest, quality=94, subsampling=0)
        print(f'{name}: {photo.size}')
    except Exception as exc:
        print(f'{name}: unchanged ({exc})')

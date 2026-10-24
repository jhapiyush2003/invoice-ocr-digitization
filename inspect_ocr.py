
from pathlib import Path
from invoice_processor import read_image

folder = Path(__file__).resolve().parent / "invoices"

for image_path in sorted(folder.glob("*.png")):
    print("\n" + "=" * 50)
    print("FILE:", image_path.name)
    print("=" * 50)

    try:
        text = read_image(image_path)
        print(text if text else "[NO TEXT DETECTED]")
    except Exception as error:
        print("ERROR:", error)

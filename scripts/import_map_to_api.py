import argparse
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser(description="Upload map assets and geometry to API")
    parser.add_argument("--api", default="http://localhost:8001", help="Base API URL")
    parser.add_argument("--i3d", required=True, help="Path to map i3d file")
    parser.add_argument("--image", required=True, help="Path to map image (png)")
    parser.add_argument("--map-id", default=None, help="Map id string")
    args = parser.parse_args()

    i3d_path = Path(args.i3d)
    image_path = Path(args.image)
    if not i3d_path.exists() or not image_path.exists():
        raise SystemExit("Missing input files")

    with httpx.Client(timeout=120) as client:
        image_resp = client.post(
            f"{args.api.rstrip('/')}/maps/image/upload",
            files={"file": (image_path.name, image_path.read_bytes())},
            data={"map_id": args.map_id} if args.map_id else None,
        )
        image_resp.raise_for_status()
        print("Image uploaded", image_resp.json())

        i3d_resp = client.post(
            f"{args.api.rstrip('/')}/maps/import-i3d",
            files={"file": (i3d_path.name, i3d_path.read_bytes())},
            params={
                "scale": 1,
                "offset_x": 1024,
                "offset_y": 1024,
                "invert_y": True,
            },
        )
        i3d_resp.raise_for_status()
        print("Geometry imported", i3d_resp.json())


if __name__ == "__main__":
    main()

import base64
import binascii
import uuid
from pathlib import Path

from app.conf import IMAGE_MAX_BYTES, UPLOAD_DIR
from app.exceptions import InvalidInputError, NotExistError

# The declared type is not trusted: the file's first bytes have to agree.
SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),
}

EXTENSION_BY_TYPE = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}

MEDIA_TYPE = {extension: media for media, extension in EXTENSION_BY_TYPE.items()}

FOLDER = Path(UPLOAD_DIR) / "images"


def save(data_url: str) -> str:
    header, _, encoded = data_url.partition(",")
    media = header.removeprefix("data:").removesuffix(";base64")
    extension = EXTENSION_BY_TYPE.get(media)
    if not header.endswith(";base64") or not extension:
        raise InvalidInputError("Upload a PNG, JPG, GIF or WebP image")

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InvalidInputError("That image could not be read") from error

    if len(content) > IMAGE_MAX_BYTES:
        raise InvalidInputError(f"The image must be {IMAGE_MAX_BYTES // (1024 * 1024)} MB or smaller")

    if not content.startswith(SIGNATURES[extension]) or (extension == "webp" and content[8:12] != b"WEBP"):
        raise InvalidInputError("That file is not the image type it claims to be")

    FOLDER.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{extension}"
    (FOLDER / name).write_bytes(content)

    return f"/calendar/images/{name}"


# The name is checked against the shape `save` produces, so a path like
# "../../etc/passwd" never reaches the filesystem.
def path_of(name: str) -> tuple[Path, str]:
    stem, _, extension = name.partition(".")
    if len(stem) != 32 or not all(char in "0123456789abcdef" for char in stem) or extension not in MEDIA_TYPE:
        raise NotExistError("Image not found")

    path = FOLDER / name
    if not path.is_file():
        raise NotExistError("Image not found")

    return path, MEDIA_TYPE[extension]

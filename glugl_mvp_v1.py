#!/usr/bin/env python3
import os
import json
import subprocess
import sys
from datetime import datetime


def find_media_json_pairs(directory):
    """
    Devuelve una lista de tuplas (media_path, json_path) para todos los archivos
    que tengan un .json con el mismo nombre en el mismo directorio.
    No recorre subcarpetas.
    """
    pairs = []
    try:
        entries = os.listdir(directory)
    except OSError as e:
        print(f"[ERROR] No se puede listar el directorio {directory}: {e}")
        return pairs

    # Solo archivos (ignoramos subcarpetas)
    files = [f for f in entries if os.path.isfile(os.path.join(directory, f))]

    for name in files:
        # Ignoramos los .json (solo nos interesan como "compañeros")
        if name.endswith(".json"):
            continue

        media_path = os.path.join(directory, name)
        json_path = media_path + ".json"  # mismo nombre, con .json añadido

        if os.path.exists(json_path):
            pairs.append((media_path, json_path))

    return pairs


def apply_metadata_from_json(media_path, json_path):

    """
    Lee el JSON y aplica parte de la metadata al archivo usando exiftool.
    MVP: solo fecha de captura (photoTakenTime.timestamp) y favorito (isFavorite).
    """
    print(
        f"\n[PAIR] {os.path.basename(media_path)}  <->  {os.path.basename(json_path)}"
    )

    # 1. Leer JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [ERROR] No se pudo leer el JSON {json_path}: {e}")
        return

    exiftool_args = []

    # 2. Fecha de captura (estilo Google Photos)
    #    Normalmente viene en data["photoTakenTime"]["timestamp"]
    ts = None
    if isinstance(data.get("photoTakenTime"), dict):
        ts = data["photoTakenTime"].get("timestamp")

    if ts:
        try:
            dt = datetime.fromtimestamp(int(ts))
            dt_str = dt.strftime("%Y:%m:%d %H:%M:%S")
            exiftool_args.extend(
                [
                    f"-DateTimeOriginal={dt_str}",
                    f"-CreateDate={dt_str}",
                ]
            )
            print(f"  [INFO] Fecha de captura → {dt_str}")
        except Exception as e:
            print(
                f"  [WARN] No se pudo interpretar el timestamp '{ts}' en {json_path}: {e}"
            )

    # 3. Favorito (isFavorite)
    is_fav = data.get("isFavorite")
    if is_fav:
        # Convención simple: rating 5 para favoritos
        exiftool_args.append("-Rating=5")
        print("  [INFO] Marcando como favorito (Rating=5)")

    if not exiftool_args:
        print("  [INFO] No hay campos soportados en el JSON; no se escribe metadata.")
        return

    # 4. Construir comando exiftool
    cmd = ["exiftool", "-overwrite_original"]
    cmd.extend(exiftool_args)
    cmd.append(media_path)

    print("  [CMD] " + " ".join(cmd))

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except FileNotFoundError:
        print("  [ERROR] exiftool no está instalado o no se encuentra en el PATH.")
        print(
            "          Instálalo (por ejemplo, con 'brew install exiftool') y vuelve a intentarlo."
        )
        sys.exit(1)

    if result.returncode != 0:
        print("  [ERROR] exiftool devolvió un error:")
        print("          " + result.stderr.strip())
    else:
        print("  [OK] Metadata escrita correctamente.")


def main():
    # Directorio actual
    directory = os.getcwd()
    print(f"glugl (MVP) - Procesando solo el directorio actual:\n  {directory}\n")

    pairs = find_media_json_pairs(directory)

    if not pairs:
        print("No se encontraron parejas media/.json en este directorio.")
        return

    print(f"Encontradas {len(pairs)} parejas media/.json.\n")

    for media_path, json_path in pairs:
        apply_metadata_from_json(media_path, json_path)


if __name__ == "__main__":
    main()

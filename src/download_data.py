from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
from requests.exceptions import RequestException


class NYCTaxiDataDownloader:
    """
    Télécharge les fichiers Parquet Yellow Taxi NYC au format :
    https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
    """

    def __init__(
        self,
        year: Optional[int] = None,
        data_dir: Path | str = "data/raw",
        base_url: str = "https://d37ci6vzurychx.cloudfront.net/trip-data",
        timeout: int = 30,
    ) -> None:
        """
        - Définit BASE_URL, YEAR, DATA_DIR
        - Crée le répertoire si nécessaire
        """
        self.BASE_URL = base_url.rstrip("/")
        self.YEAR = int(year if year is not None else datetime.now().year)
        self.DATA_DIR = Path(data_dir)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._timeout = int(timeout)

    # ------------------------------
    # Helpers chemin / existence
    # ------------------------------
    def get_file_path(self, month: int) -> Path:
        """
        Construit le chemin local :
        <DATA_DIR>/yellow_tripdata_YYYY-MM.parquet
        """
        mm = f"{int(month):02d}"
        filename = f"yellow_tripdata_{self.YEAR}-{mm}.parquet"
        return self.DATA_DIR / filename

    def file_exists(self, month: int) -> bool:
        """
        True si le fichier existe déjà localement.
        """
        return self.get_file_path(month).is_file()

    # ------------------------------
    # Téléchargement d'un mois
    # ------------------------------
    def download_month(self, month: int) -> bool:
        """
        - Vérifie l'existence locale
        - Sinon télécharge en streaming avec requests
        - Affiche une barre de progression simple
        - Gère les erreurs ; supprime le fichier partiel en cas d'échec
        - Retourne True si le fichier est présent à la fin, False sinon
        """
        path = self.get_file_path(month)
        if path.exists():
            print(f"[skip] {path.name} existe déjà.")
            return True

        mm = f"{int(month):02d}"
        url = f"{self.BASE_URL}/yellow_tripdata_{self.YEAR}-{mm}.parquet"
        tmp_path = path.with_suffix(path.suffix + ".part")

        print(f"[get ] Téléchargement {url}")
        try:
            with requests.get(url, stream=True, timeout=self._timeout) as r:
                r.raise_for_status()

                total = int(r.headers.get("Content-Length", "0"))
                downloaded = 0
                chunk_size = 8192

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        # barre de progression simple si on a la taille
                        if total > 0:
                            pct = downloaded * 100 // total
                            bar_len = 30
                            fill = (pct * bar_len) // 100
                            bar = "#" * fill + "-" * (bar_len - fill)
                            print(f"\r[ {bar} ] {pct:3d}% ({downloaded/1_048_576:.1f} MiB)", end="")
                if total > 0:
                    print()  # retour ligne après la barre

            # Téléchargement terminé → renomme le .part
            tmp_path.replace(path)
            print(f"[done] {path.name} ({path.stat().st_size/1_048_576:.1f} MiB)")
            return True

        except RequestException as e:
            print(f"[err ] Requête échouée pour {url} : {e}")
        except Exception as e:
            print(f"[err ] Erreur inattendue pour {url} : {e}")
        finally:
            # Nettoyer le partiel en cas d'échec
            if tmp_path.exists() and not path.exists():
                try:
                    tmp_path.unlink()
                    print(f"[clean] Suppression du fichier partiel: {tmp_path.name}")
                except Exception:
                    pass

        return False

    # ------------------------------
    # Téléchargement multi-mois
    # ------------------------------
    def download_all_available(self) -> list[Path]:
        """
        - Détermine le mois max :
            * si YEAR < année courante → jusqu'à décembre (12)
            * si YEAR == année courante → jusqu'au mois courant
            * si YEAR > année courante → rien
        - Boucle de janvier → mois_max
        - Appelle download_month() pour chaque mois
        - Retourne la liste des chemins présents (créés ou déjà existants)
        - Affiche un petit résumé
        """
        now = datetime.now()
        if self.YEAR < now.year:
            last_month = 12
        elif self.YEAR == now.year:
            last_month = now.month
        else:
            print(f"[info] YEAR={self.YEAR} est dans le futur. Aucun téléchargement.")
            return []

        present_files: List[Path] = []
        created = 0
        skipped = 0
        failed = 0

        print(f"[info] Téléchargement {self.YEAR}-01 → {self.YEAR}-{last_month:02d} vers {self.DATA_DIR}")

        for m in range(1, last_month + 1):
            already = self.file_exists(m)
            ok = self.download_month(m)
            if ok:
                present_files.append(self.get_file_path(m))
                if already:
                    skipped += 1
                else:
                    created += 1
            else:
                failed += 1

        print(
            f"[sum ] Année {self.YEAR} → présents: {len(present_files)} | "
            f"créés: {created} | déjà là: {skipped} | échecs: {failed}"
        )
        return present_files


if __name__ == "__main__":
    # Exemple d'utilisation simple :
    # - année par défaut = année courante
    # - dossier par défaut = data/raw/
    downloader = NYCTaxiDataDownloader(year=datetime.now().year)
    downloader.download_all_available()
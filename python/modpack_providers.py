import os
import requests
from abc import ABC, abstractmethod
from typing import List, Dict

class ModpackProvider(ABC):
    """Abstract base class for a modpack provider."""

    @abstractmethod
    def search_modpacks(self, name: str) -> List[Dict]:
        """Search for modpacks matching a name."""
        pass

    @abstractmethod
    def download_modpack(self, modpack_id: str, dest: str) -> str:
        """Download the modpack and return the path to the file."""
        pass

class CurseForgeProvider(ModpackProvider):
    BASE_URL = "https://api.curseforge.com/v1"
    GAME_ID = 432  # Minecraft

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CURSEFORGE_API_KEY", "")
        self.headers = {"Accept": "application/json"}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    def search_modpacks(self, name: str) -> List[Dict]:
        params = {
            "gameId": self.GAME_ID,
            "searchFilter": name,
            "pageSize": 25,
        }
        url = f"{self.BASE_URL}/mods/search"
        r = requests.get(url, params=params, headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])

    def download_modpack(self, modpack_id: str, dest: str) -> str:
        url = f"{self.BASE_URL}/mods/{modpack_id}/files"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        files = r.json().get("data", [])
        if not files:
            raise ValueError("No files found for modpack")
        # pick the first file (usually latest)
        download_url = files[0].get("downloadUrl")
        if not download_url:
            raise ValueError("No download url available")
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
        path = os.path.join(dest, f"{modpack_id}.zip")
        with open(path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return path

class ModrinthProvider(ModpackProvider):
    BASE_URL = "https://api.modrinth.com/v2"

    def search_modpacks(self, name: str) -> List[Dict]:
        params = {"query": name, "limit": 25, "facets": "[\"project_type:modpack\"]"}
        r = requests.get(f"{self.BASE_URL}/search", params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("hits", [])

    def download_modpack(self, modpack_id: str, dest: str) -> str:
        url = f"{self.BASE_URL}/project/{modpack_id}/version"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        versions = r.json()
        if not versions:
            raise ValueError("No versions found")
        file_url = versions[0]["files"][0]["url"]
        resp = requests.get(file_url, stream=True, timeout=30)
        resp.raise_for_status()
        path = os.path.join(dest, versions[0]["files"][0]["filename"])
        with open(path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return path

class TechnicProvider(ModpackProvider):
    BASE_URL = "https://api.technicpack.net/"
    BUILD = "multimc"

    def search_modpacks(self, name: str) -> List[Dict]:
        if name:
            url = f"{self.BASE_URL}search"
            params = {"build": self.BUILD, "q": name}
        else:
            url = f"{self.BASE_URL}trending"
            params = {"build": self.BUILD}
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("modpacks", [])

    def download_modpack(self, modpack_slug: str, dest: str) -> str:
        url = f"{self.BASE_URL}modpack/{modpack_slug}"
        params = {"build": self.BUILD}
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        info = r.json()
        if "url" in info:
            pack_url = info["url"]
            resp = requests.get(pack_url, stream=True, timeout=30)
            resp.raise_for_status()
            filename = os.path.basename(pack_url)
        elif "solder" in info:
            # Solder packs require another request
            solder = info["solder"]
            manifest_url = f"{solder}modpack/{modpack_slug}/{info['recommended']}"
            r2 = requests.get(manifest_url, timeout=30)
            r2.raise_for_status()
            manifest = r2.json()
            pack_url = manifest.get("url")
            resp = requests.get(pack_url, stream=True, timeout=30)
            resp.raise_for_status()
            filename = os.path.basename(pack_url)
        else:
            raise ValueError("No download information available")
        path = os.path.join(dest, filename)
        with open(path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return path

class ProviderFactory:
    PROVIDERS = {
        "curseforge": CurseForgeProvider,
        "modrinth": ModrinthProvider,
        "technic": TechnicProvider,
    }

    @staticmethod
    def create(provider_name: str, **kwargs) -> ModpackProvider:
        provider_name = provider_name.lower()
        if provider_name not in ProviderFactory.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        return ProviderFactory.PROVIDERS[provider_name](**kwargs)


import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional
from models import GatherRequest


def generate_cache_key(request: GatherRequest) -> str:
    """Generate MD5 hash from the gather request input"""
    cache_input = {
        "transcript": request.transcript,
        "technical_questions": request.technical_questions,
        "key_skill_areas": request.key_skill_areas,
    }

    input_string = json.dumps(cache_input, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(input_string.encode('utf-8')).hexdigest()


def get_cache_path(cache_key: str) -> Path:
    """Get the file path for a cache key"""
    cache_dir = Path("cache/gather")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key}.json"


def load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load cached gather result if it exists"""
    cache_path = get_cache_path(cache_key)

    try:
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            if "llm_output" in cached_data and "cache_key" in cached_data:
                return cached_data
            else:
                print(f"⚠️  Invalid cache file format: {cache_path}")
                cache_path.unlink()

    except Exception as e:
        print(f"⚠️  Error reading cache file {cache_path}: {str(e)}")
        if cache_path.exists():
            try:
                cache_path.unlink()
            except:
                pass

    return None


def save_to_cache(cache_key: str, llm_output: Dict[str, Any], request_metadata: Dict[str, Any]) -> None:
    """Save gather result to cache"""
    cache_path = get_cache_path(cache_key)

    try:
        cache_data = {
            "cache_key": cache_key,
            "timestamp": int(time.time()),
            "request_metadata": request_metadata,
            "llm_output": llm_output
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Result cached to: {cache_path}")

    except Exception as e:
        print(f"⚠️  Failed to save to cache: {str(e)}")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    cache_dir = Path("cache/gather")
    if not cache_dir.exists():
        return {
            "cache_enabled": True,
            "cache_directory": str(cache_dir),
            "total_cached_items": 0,
            "total_cache_size_mb": 0,
            "cached_files": []
        }

    cache_files = list(cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in cache_files)

    cached_items = []
    for cache_file in cache_files:
        try:
            stat = cache_file.stat()
            cached_items.append({
                "cache_key": cache_file.stem,
                "created": stat.st_ctime,
                "size_bytes": stat.st_size,
                "age_hours": (time.time() - stat.st_ctime) / 3600
            })
        except Exception:
            continue

    cached_items.sort(key=lambda x: x["created"], reverse=True)

    return {
        "cache_enabled": True,
        "cache_directory": str(cache_dir),
        "total_cached_items": len(cached_items),
        "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
        "cached_files": cached_items
    }


def clear_cache() -> Dict[str, Any]:
    """Clear all cached gather results"""
    cache_dir = Path("cache/gather")
    if not cache_dir.exists():
        return {"message": "Cache directory does not exist", "files_deleted": 0}

    cache_files = list(cache_dir.glob("*.json"))
    deleted_count = 0

    for cache_file in cache_files:
        try:
            cache_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"Failed to delete {cache_file}: {e}")

    return {
        "message": f"Cache cleared successfully",
        "files_deleted": deleted_count
    }


def delete_cache_item(cache_key: str) -> Dict[str, str]:
    """Delete a specific cached item"""
    cache_path = get_cache_path(cache_key)

    if not cache_path.exists():
        raise FileNotFoundError(f"Cache item not found: {cache_key}")

    cache_path.unlink()
    return {"message": f"Cache item deleted: {cache_key}"}
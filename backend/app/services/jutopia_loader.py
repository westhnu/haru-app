"""jutopia_data 모듈을 파일 단위 allowlist로 로드한다.

sys.path·심볼릭 링크를 쓰지 않는 이유 (sprint-2-log §1):
- jutopia_data 루트의 app.py(Flask 서버)가 Haru `app` 패키지와 이름이 충돌한다.
- 디렉터리 전체가 import 가능해지면 주문 모듈(web_order.py 등)도
  import 경로에 노출된다 (원칙 5).
"""

import importlib.util
import threading
from pathlib import Path
from types import ModuleType
from unittest import mock

from app.config import get_settings

# 원칙 5: 주문·매매 기능이 없는 파일만 등록한다.
ALLOWED_MODULES = frozenset({"dart_client"})
# 주문 메서드가 섞인 파일. load_jutopia_module로는 여전히 거부되고,
# 조회 전용 래퍼(hantu_readonly)가 쓰는 전용 함수로만 로드된다 (KI-002).
HANTU_MODULE = "HantuStock"
HANTU_CLASS = "HantuStock"

_load_lock = threading.Lock()


class JutopiaModuleError(RuntimeError):
    """허용되지 않았거나 찾을 수 없는 jutopia_data 모듈."""


def load_jutopia_module(name: str, jutopia_dir: str | Path) -> ModuleType:
    if name not in ALLOWED_MODULES:
        raise JutopiaModuleError(f"allowlist에 없는 jutopia_data 모듈: {name}")
    return _exec_file_module(name, jutopia_dir)


def load_hantu_stock_class(jutopia_dir: str | Path | None = None) -> type:
    """hantu_readonly 전용. 클래스만 돌려주고 인스턴스화·메서드 노출은 래퍼가 통제한다."""
    if jutopia_dir is None:
        jutopia_dir = get_settings().jutopia_data_dir
    module = _exec_file_module(HANTU_MODULE, jutopia_dir)
    cls: type = getattr(module, HANTU_CLASS)
    return cls


def _exec_file_module(name: str, jutopia_dir: str | Path) -> ModuleType:
    if not str(jutopia_dir):
        raise JutopiaModuleError("JUTOPIA_DATA_DIR 미설정")
    path = Path(jutopia_dir) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"jutopia_data.{name}", path)
    if not path.is_file() or spec is None or spec.loader is None:
        raise JutopiaModuleError(f"jutopia_data 모듈을 읽을 수 없음: {path}")

    module = importlib.util.module_from_spec(spec)
    # dart_client.py는 import 시점에 load_dotenv()로 jutopia_data/.env 전체
    # (KIS PROD 시크릿, OpenAI·Gemini 키 등)를 이 프로세스 환경변수로 올린다.
    # 실측으로 확인했으므로 실행 중에만 load_dotenv를 무력화한다 (KI-004).
    with _load_lock, mock.patch("dotenv.load_dotenv", return_value=False):
        spec.loader.exec_module(module)
    return module

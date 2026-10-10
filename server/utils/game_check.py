"""
Plays generated game code for a moment in an embedded V8 (mini-racer) to find
errors that parse fine but break the game: bad React calls, undefined names,
crashes after a click. The harness is game_check/harness.js, bundled with
React into game_check/bundle.js (rebuild with `npm run build` there).
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from py_mini_racer import JSOOMException, JSTimeoutException, MiniRacer

logger = logging.getLogger(__name__)

BUNDLE = Path(__file__).resolve().parent.parent / "game_check" / "bundle.js"
TIMEOUT_SEC = 5
MEMORY_LIMIT = 256 * 1024 * 1024
MAX_CLICKS = 20


@lru_cache(maxsize=1)
def _bundle() -> str:
    return BUNDLE.read_text(encoding="utf-8")


def find_game_error(code: str) -> Optional[str]:
    """The first error playing the game hits, phrased for the model, or None."""
    # A fresh context per game, so one game can't leave globals behind for the next
    ctx = MiniRacer()
    try:
        ctx.set_hard_memory_limit(MEMORY_LIMIT)
        ctx.eval(_bundle())
        return ctx.call("checkGame", code, MAX_CLICKS, timeout_sec=TIMEOUT_SEC)
    except JSTimeoutException:
        # V8 reports the cancelled call after the timeout; a follow-up eval
        # completes only after that report, so close() won't race it
        ctx.eval("0")
        return (f"The game did not respond within {TIMEOUT_SEC} seconds of starting or being clicked; "
                "a loop never ends.")
    except JSOOMException:
        return "The game ran out of memory while starting or being clicked."
    except Exception:
        # A broken check shouldn't hold back games; the sandbox still reports errors
        logger.exception("Game check failed to run")
        return None
    finally:
        ctx.close()


def react_version() -> str:
    """The React version the check runs, which should match the client sandbox's."""
    ctx = MiniRacer()
    try:
        ctx.eval(_bundle())
        return ctx.eval("REACT_VERSION")
    finally:
        ctx.close()

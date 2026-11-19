"""Cookie-aware HTTP transport used by every model.

The ONT web UI runs on plain HTTP and uses a session cookie. Requests are made
with the system ``curl`` binary; this keeps the dependency list small and
preserves the behaviour of the original single-file tool (including curl exit
code 8 when a radio restart closes the connection).
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import tempfile
import time


class HttpSession:
    def __init__(self, host: str, user: str, password: str) -> None:
        self.host = host.rstrip("/")
        self.user = user
        self.password = password
        self.tmpdir = tempfile.mkdtemp(prefix="vivo-ont-")
        self.jar = os.path.join(self.tmpdir, "cookies.txt")
        atexit.register(shutil.rmtree, self.tmpdir, True)

    # -- low level ---------------------------------------------------------
    def _curl(self, args: list[str], timeout: int = 25) -> subprocess.CompletedProcess:
        cmd = [
            "curl", "-sS", "--connect-timeout", "5", "--max-time", str(timeout),
            "-b", self.jar, "-c", self.jar,
        ] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def get(self, path: str, referer: str | None = None, attempts: int = 5) -> str:
        args = []
        if referer:
            args += ["-e", self.host + referer]
        args.append(self.host + path)
        last = None
        for i in range(attempts):
            last = self._curl(args)
            if last.returncode == 0:
                return last.stdout
            # 7/8/52/56 happen while the router is restarting its web server
            # after a wireless apply.
            if last.returncode in (7, 8, 52, 56) and i < attempts - 1:
                time.sleep(2 + i * 2)
                continue
            break
        raise RuntimeError(f"GET {path} failed (curl {last.returncode}): {last.stderr.strip()}")

    def post(self, path: str, data: dict, referer: str | None = None) -> str:
        """POST form data.

        curl rc 8 means the radio restart killed the connection after the CGI
        had already accepted the request.
        """
        args = ["-H", "X-Requested-With: XMLHttpRequest"]
        if referer:
            args += ["-e", self.host + referer]
        for key, value in data.items():
            args += ["--data-urlencode", f"{key}={value}"]
        args.append(self.host + path)
        result = self._curl(args)
        if result.returncode not in (0, 8):
            raise RuntimeError(f"POST {path} failed (curl {result.returncode}): {result.stderr.strip()}")
        return result.stdout

    def close(self) -> None:
        shutil.rmtree(self.tmpdir, True)

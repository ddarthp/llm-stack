"""Arranca llama-server para un modelo y muestra el panel hasta que se pare.

Sustituye al runner de bash. Lo unico especifico de cada sistema queda en
paths y sysinfo; esto es igual en Linux, macOS y Windows.
"""
from __future__ import annotations

import base64
import os
import signal
import socket
import subprocess
import sys
import time

from . import config, panel, paths, sysinfo


def read_key() -> str:
    """Clave compartida. Si no hay, se genera una aleatoria (opcion segura)."""
    f = paths.key_file()
    if not f.is_file() or f.stat().st_size == 0:
        f.parent.mkdir(parents=True, exist_ok=True)
        k = base64.b64encode(os.urandom(18)).decode().replace("/", "").replace("+", "").replace("=", "")
        f.write_text(k + "\n", encoding="utf-8")
        try:
            f.chmod(0o600)               # no-op efectivo en Windows
        except OSError:
            pass
        print(f"clave generada en {f}", file=sys.stderr)
    return f.read_text(encoding="utf-8").strip().splitlines()[0]


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def clients_connected(port: int) -> str:
    """Quien esta conectado. psutil evita depender de `ss`, que no existe fuera de Linux."""
    try:
        import psutil
    except ImportError:
        return ""
    ips = set()
    try:
        for c in psutil.net_connections(kind="inet"):
            if (c.status == "ESTABLISHED" and c.laddr and c.laddr.port == port
                    and c.raddr and not c.raddr.ip.startswith("127.")):
                ips.add(c.raddr.ip)
    except (psutil.AccessDenied, OSError):
        return ""
    return " ".join(sorted(ips))


def build_command(m: config.Model, port: int, key: str, ctx: int) -> list[str]:
    exe = paths.server_binary(m.runtime_path)
    cmd = [str(exe), "-m", str(m.model_path)]
    if m.mmproj_path and m.mmproj_path.is_file():
        cmd += ["--mmproj", str(m.mmproj_path), "--image-max-tokens",
                os.environ.get("LLM_IMG", "1024")]
    cmd += [
        "--host", "0.0.0.0", "--port", str(port),
        "-c", str(ctx), "-np", "1",
        "-ngl", os.environ.get("LLM_NGL", "99"),
        "-t", os.environ.get("LLM_THREADS", "8"),
        "-ub", os.environ.get("LLM_UBATCH", "512"),
        "-fa", "on",
        *m.sampling,
        "--jinja", "--api-key", key,
        "--metrics", "--no-warmup",
        "--cache-ram", os.environ.get("LLM_CACHE_RAM", "1024"),
        *m.extra,
    ]
    think = os.environ.get("LLM_THINK", m.think)
    if think:
        budget = {"off": "0", "max": "-1"}.get(think, think)
        cmd += ["--reasoning-budget", budget]

    # El sesgo de mean-centering del KV solo existe para Bonsai y solo si se genero.
    bias = m.dir / "kv-bias.gguf"
    if bias.is_file():
        cmd += ["--kv-mean-center", str(bias)]
    ui = paths.repo_root() / "models" / m.key / "webui-config.json"
    if ui.is_file():
        cmd += ["--webui-config-file", str(ui)]
    return cmd


def run(model_key: str) -> int:
    m = config.find(model_key)
    if m is None:
        print(f"modelo desconocido: {model_key}", file=sys.stderr)
        return 1
    paths.ensure_dirs()

    if not m.model_path.is_file():
        print(f"faltan los pesos de {m.name}:\n  {m.model_path}\n"
              f"descargalos con:  python3 install.py {m.key}", file=sys.stderr)
        return 1
    if not m.installed():
        size = m.model_path.stat().st_size
        print(f"el fichero parece incompleto ({size // 1048576} MB, se esperaban al "
              f"menos {m.min_size // 1048576} MB). Reanuda la descarga.", file=sys.stderr)
        return 1
    exe = paths.server_binary(m.runtime_path)
    if not exe.is_file():
        print(f"falta el runtime '{m.runtime}':\n  {exe}\n"
              f"instalalo con:  python3 install.py --runtime {m.runtime}", file=sys.stderr)
        return 1

    port = int(os.environ.get("LLM_PORT", "8090"))
    if port_in_use(port):
        print(f"el puerto {port} ya esta ocupado", file=sys.stderr)
        return 1
    ctx = int(os.environ.get("LLM_CTX", m.ctx))
    key = read_key()

    env = dict(os.environ)
    env.update(m.env)
    var = paths.library_path_var()
    libdir = str(exe.parent)
    env[var] = libdir + (os.pathsep + env[var] if env.get(var) else "")

    m.log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(m.log_path, "wb")
    print(f"\033[?25l\033[38;5;77m▲\033[0m arrancando llama-server ({m.name})…")
    proc = subprocess.Popen(build_command(m, port, key, ctx), env=env,
                            stdout=log, stderr=subprocess.STDOUT)

    met = panel.Metrics(f"http://127.0.0.1:{port}/metrics", key)
    ip = paths.lan_ip()
    hint = os.environ.get("LLM_EXIT_HINT", "Ctrl+C")
    started, ready, tick = time.time(), False, 0
    stop = {"now": False}

    def _sig(_s, _f):
        stop["now"] = True

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _sig)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _sig)

    try:
        while not stop["now"]:
            if proc.poll() is not None:
                sys.stdout.write("\033[?25h\n\033[38;5;203mllama-server termino "
                                 "inesperadamente. Ultimas lineas:\033[0m\n\n")
                print("\n".join(panel.tail_lines(m.log_path, 20)))
                return 1
            if not ready and not port_in_use(port):
                pass
            elif not ready:
                ready = True
            if ready:
                met.poll()
            frame = panel.render(
                name=m.name, tag=m.tag, ctx=ctx, port=port, ip=ip, key=key,
                ready=ready, uptime=time.time() - started, stats=sysinfo.collect(),
                met=met, live=panel.tail_progress(m.log_path),
                clients=clients_connected(port), exit_hint=hint, tick=tick)
            body = "\n".join(f"   \033[38;5;244m{l}\033[0m"
                             for l in panel.tail_lines(m.log_path, 6))
            sys.stdout.write(frame + body +
                             f"\n\n  \033[2m{hint} para apagar el modelo y "
                             f"liberar la memoria\033[0m\033[J")
            sys.stdout.flush()
            tick += 1
            time.sleep(1)
    finally:
        sys.stdout.write("\033[?25h\n")
        if proc.poll() is None:
            print("\033[38;5;221mapagando…\033[0m")
            proc.terminate()
            for _ in range(40):
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        log.close()
        print(f"\033[38;5;244m{m.name} detenido. VRAM y RAM liberadas.\033[0m")
    return 0

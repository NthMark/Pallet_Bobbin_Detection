import sys, time, subprocess, os
from pathlib import Path

SUP_FLAGS = ["--auto-multicam", "--auto-detect"]  # tuỳ bạn

def _child_cmd() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-app", *SUP_FLAGS]
    else:
        # Dev: gọi python để chạy main.py
        main_py = Path(__file__).with_name("main.py")
        return [sys.executable, str(main_py), *SUP_FLAGS]

def run_app_once() -> int:
    try:
        import main
        # nếu main.py có main(), ta gọi thẳng:
        main.main()
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:
        # log ra stderr
        print(f"[Supervisor] app crashed: {e}", flush=True)
        return 1

def run_forever():
    while True:
        try:
            cmd = _child_cmd()
            if getattr(sys, "frozen", False):
                creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
                ret = subprocess.call(cmd, creationflags=creationflags)
            else:
                ret = subprocess.call(cmd)

            if ret == 0:
                print("[Supervisor] App exited normally -> stop loop")
                break
            else:
                print(f"[Supervisor] App exited with code {ret} -> sleep & restart")
                time.sleep(5)
        except Exception as e:
            print("[Supervisor] error:", e, flush=True)
            time.sleep(5)

if __name__ == "__main__":
    # Nếu được gọi với --run-app, nhập và chạy trực tiếp main (tránh lỗi DLL/_MEIPASS)
    if "--run-app" in sys.argv:
        sys.exit(run_app_once())
    else:
        run_forever()

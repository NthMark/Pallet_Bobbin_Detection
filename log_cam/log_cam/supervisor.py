import subprocess,time,sys,os
from pathlib import Path
SUP_FLAGS=["--auto-multicam","--auto-detect"]
def _child_cmd():
    if getattr(sys,"frozen",False):
        return [sys.executable,"--run-app"]
    else:
        main_ppy=Path(__file__).with_name("main.py")
        return [sys.executable,str(main_ppy),*SUP_FLAGS]
def run_app_once():
    try:
        import main
        main.main()
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code,int)else 1
    except Exception as e:
        print("[Supervisor] App crashed: {e}",flush=True)
        return 1
def run_forever():
    # cmd=[sys.executable,os.path.join(os.getcwd(),"main.py"),"--auto-multicam","--auto-detect"]
    while True:
        try:
            cmd=_child_cmd()
            if getattr(sys,"frozen",False):
                creationflags=0x08000000 if os.name=="nt" else 0
                ret=subprocess.call(cmd,creationflags=creationflags)
            else:
                ret=subprocess.call(cmd)
            if ret==0:
                print("[Supervisor] App exited normally -> stop loop")
            else:
                print(f"sleep")
                time.sleep(5)
            # try:
            #     ret=subprocess.call(cmd)
            #     if ret==0:
            #         print("[Supervisor] App exited normally -> stop loop")
            #     else:
            #         print(f"sleep")
            #         time.sleep(5)
        except Exception as e:
            print("[Supervisor] error: ",e,flush=True)
            time.sleep(5)
if __name__ == '__main__':
    if "--run-app" in sys.argv:
        sys.exit(run_app_once())
    else:
        run_forever()

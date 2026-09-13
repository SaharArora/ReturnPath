import sys

from .auth import gmail, print_doctors
from .config import Config, init_config


def main():
    c = Config()
    command = sys.argv[1] if len(sys.argv) > 1 else "doctor"
    try:
        if command == "init-config":
            init_config(c)
        elif command == "auth-gmail":
            gmail(c, consent=True)
            print("Gmail AUTHENTICATED; workflow ACTION_UNVERIFIED")
        elif command == "doctor":
            return print_doctors(c, sys.argv[2:] or ["gmail", "slack", "stripe", "model"])
        elif command in {"seed", "worker", "watchdog"}:
            from .runtime import run, seed
            if c.get("RP_MODE", "local") == "local":
                from .isolation import install
                install()
            if command == "seed":
                seed(c)
            else:
                run(c, command, "--once" in sys.argv)
        else:
            raise ValueError("Unknown command")
    except Exception as exc:
        print("BLOCKED: " + (str(exc) if type(exc) is ValueError else type(exc).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

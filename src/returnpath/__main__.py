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
        elif command == "arm":
            from .runtime import paths
            from pathlib import Path
            boundary = sys.argv[2] if len(sys.argv) > 2 else ""
            if boundary not in {"before-post", "after-provider-success", "after-mail-success"}:
                raise ValueError("Specify a supported named boundary")
            if c.get("RP_MODE", "local") == "connected-test":
                c.writes()
            app, _ = paths(c)
            Path(str(app) + "." + boundary).touch(exist_ok=False)
            print("Armed " + boundary + "; worker SIGSTOPs there. Operator/harness must SIGKILL then restart without seed.")
        elif command == "stripe-oracle":
            from .runtime import paths
            from .storage import connect
            from .oracle import stripe_records
            import json
            db = connect(paths(c)[0])
            row = db.execute("SELECT c.charge,c.id,o.id FROM cases c JOIN operations o ON o.case_id=c.id").fetchone()
            if not row:
                raise ValueError("No operation to independently inspect")
            result = stripe_records(c, row[0], row[2], row[1])
            print(json.dumps(result, indent=2))
            return int(not result['passed'])
        elif command in {"review-check", "submission-check"}:
            from .evidence import check
            return check(command == "submission-check")
        elif command in {"dev", "connected-dev"}:
            from .runtime import dev
            if command == "connected-dev":
                c.writes()
            elif c.get("RP_MODE", "local") != "local":
                raise ValueError("Use connected-dev explicitly")
            from .web import create_app
            create_app(c)  # Fail before starting children when auth is missing.
            dev(c)
        elif command == "web":
            import uvicorn
            from .web import create_app
            if c.get("RP_MODE", "local") == "local":
                from .isolation import install
                install()
            uvicorn.run(create_app(c), host="127.0.0.1", port=int(c.get("RP_WEB_PORT", "8000")), access_log=False)
        elif command == "connected-seed":
            from .runtime import paths
            from .storage import connect
            from .connected import seed
            seed(c, connect(paths(c)[0]))
        elif command == "connected-smoke":
            c.writes()
            from .runtime import run
            run(c, "worker", once=True)
            print("Observe the protected case page. WAITING for real Gmail input/customer confirmation unless already supplied. This is not a submission verification result.")
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

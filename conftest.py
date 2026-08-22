"""Root conftest.

Three jobs, all purely to avoid any packaging/install step and to get
secrets into os.environ before anything else reads them:
1. Being present here makes pytest add the repo root to sys.path, so
   `import core...` / `import api...` resolve from anywhere tests run.
2. Loads .env (gitignored -- see .env.example) into os.environ, before
   core.plugin/core.config/core.auth ever run, so per-environment static
   tokens like DEV_READ_TOKEN are in place for TokenProvider (core/auth.py)
   to find. A missing .env is a silent no-op -- CI sets these as real env
   vars instead.
3. Registers core.plugin as a pytest plugin (ini options, markers, and the
   per-test record + report-render lifecycle hooks).
"""
from dotenv import load_dotenv

load_dotenv()

pytest_plugins = ["core.plugin"]

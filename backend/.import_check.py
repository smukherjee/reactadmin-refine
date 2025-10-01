import sys, traceback

try:
    # Import the app entrypoint to trigger any import-time errors
    import backend.main
    print("imported backend.main OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

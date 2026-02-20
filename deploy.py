import os
import subprocess
import sys
import traceback
import re

def print_separator():
    print("\n" + "=" * 80 + "\n")

print_separator()
print("🚀 SNOWFLAKE DEPLOYMENT STARTED")
print_separator()

try:
    # Ensure WIF authentication
    os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"

    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_WAREHOUSE"
    ]

    print("🔎 Validating required environment variables...")
    print("SNOWFLAKE_ACCOUNT =", os.getenv("SNOWFLAKE_ACCOUNT"))
    print("SNOWFLAKE_ROLE =", os.getenv("SNOWFLAKE_ROLE"))
    print("SNOWFLAKE_WAREHOUSE =", os.getenv("SNOWFLAKE_WAREHOUSE"))
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required environment variable: {var}")
            sys.exit(1)
        else:
            print(f"✅ {var} is set")

    print_separator()

    cmd = [
        "schemachange",
        "-f", "migrations",
        "-c", "schemachange-config.yml"
    ]

    print("📦 Running schemachange...")
    print("Command:", " ".join(cmd))
    print_separator()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    deployed_files = []
    failed_file = None
    error_detected = False

    for line in process.stdout:
        print(line.strip())

        # Detect deployed files
        match_success = re.search(r"Applying change script (.+\.sql)", line)
        if match_success:
            deployed_files.append(match_success.group(1))

        # Detect error line
        if "ERROR" in line or "Failed" in line:
            error_detected = True

        # Capture failed file
        match_fail = re.search(r"Error applying change script (.+\.sql)", line)
        if match_fail:
            failed_file = match_fail.group(1)

    process.wait()

    print_separator()

    if process.returncode != 0 or error_detected:
        print("❌ DEPLOYMENT FAILED")
        if failed_file:
            print(f"❌ Failed Script: {failed_file}")
        print(f"❌ Exit Code: {process.returncode}")
        sys.exit(process.returncode)

    print("✅ DEPLOYMENT SUCCESSFUL")
    print("📋 Successfully Applied Scripts:")

    for f in deployed_files:
        print(f"   ✔ {f}")

    print_separator()
    sys.exit(0)

except Exception:
    print_separator()
    print("💥 UNEXPECTED ERROR OCCURRED")
    traceback.print_exc()
    print_separator()
    sys.exit(1)

import os
import subprocess
import sys

print("Starting Snowflake deployment using Workload Identity")

os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"

cmd = [
    "schemachange",
    "-f", "migrations",
    "-c", "schemachange-config.yml"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print(result.stdout)
print(result.stderr)

if result.returncode != 0:
    sys.exit(1)

print("Deployment successful")

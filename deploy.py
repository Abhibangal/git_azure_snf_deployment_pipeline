import os
import subprocess

print("Starting Snowflake deployment using WIF...")

os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"

result = subprocess.run(
    ["schemachange", "-f", "migrations/to_be_deployed", "-c", "schemachange-config.yml"],
    capture_output=True,
    text=True
)

print(result.stdout)
print(result.stderr)

if result.returncode != 0:
    raise Exception("Deployment failed")

print("Deployment completed successfully")

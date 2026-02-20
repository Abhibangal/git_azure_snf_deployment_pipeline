import os
import subprocess
import sys
import yaml
import traceback

print("\n==============================")
print("🚀 Snowflake Deployment Start")
print("==============================\n")

try:
    # ----------------------------
    # Detect Environment
    # ----------------------------
    environment = os.getenv("ENVIRONMENT")

    if not environment:
        print("❌ ENVIRONMENT variable not set.")
        sys.exit(1)

    print(f"Environment detected: {environment}")

    # ----------------------------
    # Load database config
    # ----------------------------
    if not os.path.exists("deploy-database-map.yml"):
        print("❌ deploy-database-map.yml not found in container.")
        sys.exit(1)

    with open("deploy-database-map.yml", "r") as f:
        config = yaml.safe_load(f)

    databases = config.get("databases", {})
    print(f"database = {databases}")

    if not databases:
        print("❌ No databases defined in deploy-database-map.yml")
        sys.exit(1)

    print("\nResolving databases dynamically...\n")

    for db_key, db_values in databases.items():
        value = db_values.get(environment)

        if not value:
            print(f"❌ Missing mapping for {db_key} in environment {environment}")
            sys.exit(1)

        os.environ[db_key] = value
        print(f"✔ {db_key} = {value}")

    # ----------------------------
    # Validate required Snowflake variables
    # ----------------------------
    required = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_WAREHOUSE"
    ]

    print("\nValidating Snowflake environment variables...\n")

    for r in required:
        if not os.getenv(r):
            print(f"❌ Missing required variable: {r}")
            sys.exit(1)
        print(f"✔ {r} is set")

    # ----------------------------
    # Configure Workload Identity
    # ----------------------------
    os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"
    os.environ["SNOWFLAKE_WORKLOAD_IDENTITY_PROVIDER"] = "AZURE"

    print("\nUsing Azure Workload Identity authentication.")

    # ----------------------------
    # Run schemachange
    # ----------------------------
    print("\nStarting schemachange...\n")

    cmd = [
        "schemachange",
        "-f", "migrations",
        "-c", "schemachange-config.yml",
        "-v"
    ]

    print("Command:", " ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("\n❌ Deployment failed.")
        sys.exit(result.returncode)

    print("\n✅ Deployment successful.")
    sys.exit(0)

except Exception:
    print("\n💥 Unexpected error occurred:")
    traceback.print_exc()
    sys.exit(1)

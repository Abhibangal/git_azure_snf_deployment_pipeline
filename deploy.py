import os
import subprocess
import sys
import yaml
import traceback

print("\n======================================")
print("🚀 Snowflake Deployment Starting")
print("======================================\n")

try:
    # ---------------------------------------------------
    # 1️⃣ Get ENVIRONMENT
    # ---------------------------------------------------
    environment = os.getenv("ENVIRONMENT")

    if not environment:
        print("❌ ENVIRONMENT variable not set.")
        sys.exit(1)

    print(f"✔ Environment detected: {environment}")

    # ---------------------------------------------------
    # 2️⃣ Load database mapping YAML
    # ---------------------------------------------------
    config_file = "deploy-database-map.yml"

    if not os.path.exists(config_file):
        print("❌ deploy-database-map.yml not found.")
        sys.exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    if "databases" not in config:
        print("❌ 'databases' section missing in YAML.")
        sys.exit(1)

    print("\nResolving databases from YAML...\n")

    # ---------------------------------------------------
    # 3️⃣ Explicitly resolve each database
    # ---------------------------------------------------
    for db_name in config["databases"]:

        env_map = config["databases"][db_name]

        if environment not in env_map:
            print(f"❌ No mapping for {db_name} in environment {environment}")
            sys.exit(1)

        resolved_value = env_map[environment]

        if not resolved_value:
            print(f"❌ Empty value for {db_name}")
            sys.exit(1)

        # This is the important line
        os.environ[db_name] = resolved_value

        print(f"✔ {db_name} → {resolved_value}")

    # ---------------------------------------------------
    # 4️⃣ Validate METADATA specifically
    # ---------------------------------------------------
    metadata_db = os.getenv("SNOWFLAKE_DATABASE")

    if not metadata_db:
        print("❌ SNOWFLAKE_DATABASE was not set from YAML.")
        sys.exit(1)

    print(f"\n✔ SNOWFLAKE_DATABASE database resolved to: {metadata_db}")

    # ---------------------------------------------------
    # 5️⃣ Validate Snowflake core variables
    # ---------------------------------------------------
    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_WAREHOUSE"
    ]

    print("\nValidating Snowflake variables...\n")

    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required variable: {var}")
            sys.exit(1)
        print(f"✔ {var} is set")

    # ---------------------------------------------------
    # 6️⃣ Configure Azure Workload Identity
    # ---------------------------------------------------
    os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"
    os.environ["SNOWFLAKE_WORKLOAD_IDENTITY_PROVIDER"] = "AZURE"

    print("\n✔ Using Azure Workload Identity")

    # ---------------------------------------------------
    # 7️⃣ Run schemachange
    # ---------------------------------------------------
    print("\nStarting schemachange...\n")

    cmd = [
        "schemachange",
        "-f", "migrations",
        "-c", "schemachange-config.yml",
        "-v"
    ]

    print("Command:", " ".join(cmd))
    print("\n--------------------------------------\n")

    result = subprocess.run(cmd)

    print("\n--------------------------------------\n")

    if result.returncode != 0:
        print("❌ Deployment failed.")
        sys.exit(result.returncode)

    print("✅ Deployment successful.")
    sys.exit(0)

except Exception:
    print("\n💥 Unexpected error:")
    traceback.print_exc()
    sys.exit(1)

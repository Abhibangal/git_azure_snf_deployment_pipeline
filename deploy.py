"""
deploy.py

Main Snowflake deployment script.

Responsibilities
----------------
1. Detect environment (dev / prod)
2. Resolve databases from YAML config
3. Resolve Key Vault from YAML config
4. Validate Snowflake environment variables
5. Connect to Snowflake using Azure Workload Identity
6. Synchronize Azure Key Vault secrets
7. Run schemachange migrations
"""

import os
import subprocess
import sys
import yaml
import traceback
import json
import snowflake.connector

from add_modify_snf_secret import sync_snowflake_secrets

print("\n======================================")
print("🚀 Snowflake Deployment Starting")
print("======================================")

try:

    # ---------------------------------------------------
    # 1️⃣ Detect deployment environment
    # ---------------------------------------------------
    environment = os.getenv("ENVIRONMENT")

    if not environment:
        print("❌ ENVIRONMENT variable not set.")
        sys.exit(1)

    print(f"✔ Environment detected: {environment}")

    # ---------------------------------------------------
    # 2️⃣ Load database configuration
    # ---------------------------------------------------
    config_file = "deploy-database-map.yml"

    if not os.path.exists(config_file):
        print("❌ deploy-database-map.yml not found.")
        sys.exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    schemachange_vars = {}

    print("\nResolving databases from YAML...\n")

    for db_name in config["databases"]:

        env_map = config["databases"][db_name]

        resolved_value = env_map[environment]

        os.environ[db_name] = resolved_value
        schemachange_vars[db_name] = resolved_value

        print(f"✔ {db_name} → {resolved_value}")

    vars_json_string = json.dumps(schemachange_vars)

    # ---------------------------------------------------
    # 3️⃣ Resolve Key Vault from config
    # ---------------------------------------------------
    keyvault_config_file = "deploy-keyvault-map.yml"

    if not os.path.exists(keyvault_config_file):
        print("❌ deploy-keyvault-map.yml not found.")
        sys.exit(1)

    with open(keyvault_config_file, "r") as f:
        kv_config = yaml.safe_load(f)

    kv_env_map = kv_config["keyvaults"]["SNOWFLAKE_SECRETS"]

    keyvault_name = kv_env_map[environment]

    os.environ["KEYVAULT_NAME"] = keyvault_name

    print(f"\n✔ Key Vault resolved → {keyvault_name}")

    # ---------------------------------------------------
    # 4️⃣ Validate Snowflake environment variables
    # ---------------------------------------------------
    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE"
    ]

    print("\nValidating Snowflake variables...\n")

    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing variable: {var}")
            sys.exit(1)

        print(f"✔ {var} is set")

    # ---------------------------------------------------
    # 5️⃣ Configure Azure Workload Identity
    # ---------------------------------------------------
    os.environ["SNOWFLAKE_AUTHENTICATOR"] = "WORKLOAD_IDENTITY"
    os.environ["SNOWFLAKE_WORKLOAD_IDENTITY_PROVIDER"] = "AZURE"

    print("\n✔ Using Azure Workload Identity")

    # ---------------------------------------------------
    # 6️⃣ Establish Snowflake connection
    # ---------------------------------------------------
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        authenticator="WORKLOAD_IDENTITY",
        workload_identity_provider='AZURE',
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        database=os.getenv("SNOWFLAKE_DATABASE")
    )

    print("✔ Snowflake connection established")

    # ---------------------------------------------------
    # 7️⃣ Synchronize secrets from Azure Key Vault
    # ---------------------------------------------------
    sync_snowflake_secrets(conn)

    # ---------------------------------------------------
    # 8️⃣ Execute schemachange migrations
    # ---------------------------------------------------
    print("\nStarting schemachange...\n")

    cmd = [
        "schemachange",
        "deploy",
        "-f", "migrations",
        "--config-folder", ".",
        "--vars", vars_json_string
    ]

    print("Command:", " ".join(cmd))
    print("\n--------------------------------------\n")

    result = subprocess.run(cmd)

    print("\n--------------------------------------\n")

    if result.returncode != 0:
        print("❌ Deployment failed.")
        sys.exit(result.returncode)

    print("✅ Deployment successful")

    conn.close()

    sys.exit(0)

except Exception:
    print("\n💥 Unexpected error:")
    traceback.print_exc()
    sys.exit(1)
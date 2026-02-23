"""
add_modify_snf_secret.py

Purpose
-------
Synchronize Azure Key Vault secrets with Snowflake SECRET objects.

Functionality
-------------
1. Reads secret mapping from Snowflake metadata table
2. Lists secrets from Azure Key Vault
3. Detects:
      - NEW secrets
      - ROTATED secrets
4. Creates or updates Snowflake SECRET objects
5. Updates metadata mapping table

This module is called by deploy.py during deployment.
"""

import os
import subprocess
from datetime import datetime


def sync_snowflake_secrets(conn):
    """
    Synchronize secrets between Azure Key Vault and Snowflake.

    Parameters
    ----------
    conn : snowflake.connector connection
        Existing Snowflake connection using Workload Identity.
    """

    print("\n🔐 Starting Key Vault → Snowflake secret synchronization\n")

    # ---------------------------------------------------------
    # Get Key Vault name from environment variable
    # (resolved earlier in deploy.py from config file)
    # ---------------------------------------------------------
    keyvault_name = os.getenv("KEYVAULT_NAME")

    if not keyvault_name:
        raise Exception("KEYVAULT_NAME environment variable not set")

    cur = conn.cursor()

    # ---------------------------------------------------------
    # 1️⃣ Load existing mapping table from Snowflake
    # ---------------------------------------------------------
    cur.execute("""
        SELECT KEYVAULT_SECRET_NAME,
               LAST_KV_UPDATED
        FROM CONFIG_DB.SECURITY_SCH.SECRET_SYNC_MAP
    """)

    rows = cur.fetchall()

    # Convert mapping table results to dictionary
    mapping = {}

    for kv_name, last_updated in rows:
        mapping[kv_name] = last_updated

    # ---------------------------------------------------------
    # 2️⃣ List all secrets from Azure Key Vault
    # ---------------------------------------------------------
    list_cmd = [
        "az",
        "keyvault",
        "secret",
        "list",
        "--vault-name",
        keyvault_name,
        "--query",
        "[].name",
        "-o",
        "tsv"
    ]

    secrets = subprocess.check_output(list_cmd).decode().splitlines()

    # ---------------------------------------------------------
    # 3️⃣ Process each secret
    # ---------------------------------------------------------
    for kv_secret in secrets:

        print(f"\nProcessing secret: {kv_secret}")

        # -----------------------------------------------------
        # Retrieve last updated timestamp from Key Vault
        # -----------------------------------------------------
        updated_cmd = [
            "az",
            "keyvault",
            "secret",
            "show",
            "--vault-name",
            keyvault_name,
            "--name",
            kv_secret,
            "--query",
            "attributes.updated",
            "-o",
            "tsv"
        ]

        kv_updated = subprocess.check_output(updated_cmd).decode().strip()

        kv_updated_dt = datetime.fromisoformat(kv_updated.replace("Z", "+00:00"))

        last_kv_updated = mapping.get(kv_secret)

        create_or_update = False

        # -----------------------------------------------------
        # Determine whether to create or update secret
        # -----------------------------------------------------
        if last_kv_updated is None:
            print("🆕 New secret detected → creating Snowflake secret")
            create_or_update = True

        elif kv_updated_dt > last_kv_updated:
            print("🔄 Secret rotated → updating Snowflake secret")
            create_or_update = True

        # -----------------------------------------------------
        # Create or update Snowflake SECRET
        # -----------------------------------------------------
        if create_or_update:
        
            # Fetch secret value from Azure Key Vault
            value_cmd = [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                keyvault_name,
                "--name",
                kv_secret,
                "--query",
                "value",
                "-o",
                "tsv"
            ]

            secret_value = subprocess.check_output(value_cmd).decode().strip()

            # Snowflake secret name
            sf_secret = kv_secret

            # -------------------------------------------------
            # Case 1: Secret does NOT exist → CREATE
            # -------------------------------------------------
            if last_kv_updated is None:
            
                print("Creating Snowflake secret...")

                sql = f"""
                CREATE SECRET CONFIG_DB.SECURITY_SCH.{sf_secret}
                TYPE = GENERIC_STRING
                SECRET_STRING = '{secret_value}'
                """

            # -------------------------------------------------
            # Case 2: Secret exists but rotated → ALTER
            # -------------------------------------------------
            else:
            
                print("Updating Snowflake secret using ALTER...")

                sql = f"""
                ALTER SECRET CONFIG_DB.SECURITY_SCH.{sf_secret}
                SET SECRET_STRING = '{secret_value}'
                """

            cur.execute(sql)

            # -------------------------------------------------
            # Update metadata mapping table
            # -------------------------------------------------
            cur.execute(f"""
                MERGE INTO METADATA.SECRET_SYNC_MAP t
                USING (
                    SELECT '{kv_secret}' AS KEYVAULT_SECRET_NAME
                ) s
                ON t.KEYVAULT_SECRET_NAME = s.KEYVAULT_SECRET_NAME
                WHEN MATCHED THEN
                    UPDATE SET
                        LAST_KV_UPDATED = '{kv_updated}',
                        LAST_SYNCED = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN
                    INSERT (
                        KEYVAULT_SECRET_NAME,
                        SNOWFLAKE_SECRET_NAME,
                        LAST_KV_UPDATED,
                        LAST_SYNCED
                    )
                    VALUES (
                        '{kv_secret}',
                        '{kv_secret}',
                        '{kv_updated}',
                        CURRENT_TIMESTAMP()
                    );
            """)

            print(f"✔ Snowflake secret created/updated: {sf_secret}")

        else:
            print("✔ Secret already synchronized")

    cur.close()

    print("\n✅ Secret synchronization completed\n")
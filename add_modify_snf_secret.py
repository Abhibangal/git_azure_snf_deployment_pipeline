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

Authentication
--------------
Uses Managed Identity via DefaultAzureCredential.
"""

import os
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def sync_snowflake_secrets(conn):

    print("\n🔐 Starting Key Vault → Snowflake secret synchronization\n")

    keyvault_name = os.getenv("KEYVAULT_NAME")

    if not keyvault_name:
        raise Exception("KEYVAULT_NAME environment variable not set")

    vault_url = f"https://{keyvault_name}.vault.azure.net"

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    cur = conn.cursor()

    # ---------------------------------------------------------
    # 1️⃣ Load mapping table from Snowflake
    # ---------------------------------------------------------
    cur.execute("""
        SELECT KEYVAULT_SECRET_NAME,
               LAST_KV_UPDATED
        FROM CONFIG_DB.SECURITY_SCH.SECRET_SYNC_MAP
    """)

    rows = cur.fetchall()

    mapping = {}

    for kv_name, last_updated in rows:
        mapping[kv_name] = last_updated

    # ---------------------------------------------------------
    # 2️⃣ List secrets from Azure Key Vault
    # ---------------------------------------------------------
    secrets = client.list_properties_of_secrets()

    for secret_prop in secrets:

        kv_secret = secret_prop.name
        kv_updated_dt = secret_prop.updated_on

        print(f"\nProcessing secret: {kv_secret}")

        last_kv_updated = mapping.get(kv_secret)

        create_secret = False
        update_secret = False

        # -----------------------------------------------------
        # Detect create vs update
        # -----------------------------------------------------
        if last_kv_updated is None:
            print("🆕 New secret detected")
            create_secret = True

        elif kv_updated_dt > last_kv_updated:
            print("🔄 Secret rotated")
            update_secret = True

        if create_secret or update_secret:

            # Retrieve secret value
            secret = client.get_secret(kv_secret)
            secret_value = secret.value

            sf_secret = kv_secret

            # -------------------------------------------------
            # CREATE SECRET
            # -------------------------------------------------
            if create_secret:

                print("Creating Snowflake secret...")

                sql = f"""
                CREATE SECRET CONFIG_DB.SECURITY_SCH.{sf_secret}
                TYPE = GENERIC_STRING
                SECRET_STRING = '{secret_value}'
                """

            # -------------------------------------------------
            # ALTER SECRET
            # -------------------------------------------------
            else:

                print("Updating Snowflake secret...")

                sql = f"""
                ALTER SECRET CONFIG_DB.SECURITY_SCH.{sf_secret}
                SET SECRET_STRING = '{secret_value}'
                """

            cur.execute(sql)

            # -------------------------------------------------
            # Update mapping table
            # -------------------------------------------------
            cur.execute(f"""
                MERGE INTO METADATA.SECRET_SYNC_MAP t
                USING (
                    SELECT '{kv_secret}' AS KEYVAULT_SECRET_NAME
                ) s
                ON t.KEYVAULT_SECRET_NAME = s.KEYVAULT_SECRET_NAME
                WHEN MATCHED THEN
                    UPDATE SET
                        LAST_KV_UPDATED = '{kv_updated_dt}',
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
                        '{kv_updated_dt}',
                        CURRENT_TIMESTAMP()
                    );
            """)

            print(f"✔ Snowflake secret synchronized: {sf_secret}")

        else:
            print("✔ Secret already up to date")

    cur.close()

    print("\n✅ Secret synchronization completed\n")
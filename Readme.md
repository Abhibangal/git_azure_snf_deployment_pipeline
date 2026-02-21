# 🚀 GitHub → Azure → Snowflake Object Deployment Pipeline

---

## 📌 Overview

This project implements a secure and automated Snowflake object deployment pipeline using:

- GitHub Actions  
- Azure Container Registry (ACR)  
- Azure Container App Jobs (Manual Trigger)  
- Azure Workload Identity Federation (WIF)  
- schemachange  
- Snowflake Service User (TYPE = SERVICE)  

The solution enables automated object deployment into Snowflake based on Git branch (Dev / Prod) without storing any secrets.

---

# ☁️ Azure Setup

---

## 1️⃣ Create Azure Container Registry

1. Go to **Azure Portal**
2. Search for **Container Registries**
3. Click **Create**
4. Select Subscription
5. Resource Group → Create or select:
   ```
   rg_snowflake_deploy
   ```
6. Registry Name:
   ```
   acrsnowflakedeploy123
   ```
7. SKU → Basic (sufficient for this use case)
8. Click **Review + Create**
9. Click **Create**

---

## 2️⃣ Create Azure Container App Job (NOT Container App)

> ⚠️ Important: Select **Container App Job**, not Container App.

1. Search for **Container App Jobs**
2. Click **Create**
3. Select:
   - Subscription
   - Resource Group → `rg_snowflake_deploy`
4. Job Name:
   ```
   job-snowflake-deploy
   ```
5. Trigger Type:
   ```
   Manual
   ```
6. Click **Next → Container**
7. Container Name:
   ```
   job-snowflake-deploy
   ```
8. Image Source:
   ```
   Azure Container Registry
   ```
9. Select Registry:
   ```
   acrsnowflakedeploy123
   ```
10. Temporary Image (initial image before GitHub pushes real image):
    - Image:
      ```
      mcr.microsoft.com/k8se/quickstart
      ```
    - Tag:
      ```
      latest
      ```

11. Authentication Type:
    ```
    Managed Identity
    ```
12. Enable:
    ```
    System Assigned Identity
    ```

13. Leave other settings as default
14. Click **Review + Create**
15. Click **Create**

Wait for deployment to complete.

---

## 3️⃣ Enable and Capture Managed Identity Details

After the Container App Job is created:

1. Open the job → **Identity**
2. Ensure:
   ```
   System Assigned Identity = ON
   ```
3. Click **Save** if needed
4. Go to **Azure Entra ID**
5. Click **Enterprise Applications**
6. Remove default filter (if applied)
7. Search for:
   ```
   job-snowflake-deploy
   ```
8. Open the application
9. Copy and save:
   - **Object ID**
   - **Tenant ID**

These values will be used in Snowflake during Workload Identity configuration.

---

## 4️⃣ Configure Environment Variables (Container App Job)

Go to:

Container App Job → Containers → Click your container → Environment Variables

Add the following variables:

| Variable | Value |
|-----------|--------|
| SNOWFLAKE_ACCOUNT | Your Snowflake account identifier |
| SNOWFLAKE_USERNAME | SVC_SNOWFLAKE_DEPLOY |
| SNOWFLAKE_ROLE | DEPLOY_ROLE |
| SNOWFLAKE_WAREHOUSE | DEPLOYMENT_WH |
| ENVIRONMENT | dev |

Click **Save**.

> ℹ️ Database routing (Dev vs Prod) is handled dynamically inside `deploy.py` using `deploy-database-map.yml`.

---

This completes the **Azure Setup** section.

# 🧭 Architectural Flow

## End-to-End Deployment Flow

1. Developer pushes code to **dev** or **main** branch.
2. If pushing to `main`, PR approval is required before merge.
3. GitHub Action is triggered automatically.
4. GitHub:
   - Builds Docker image containing:
     - schemachange
     - deploy.py
     - migration scripts
   - Authenticates to Azure using **OIDC (OpenID Connect)**.
5. Docker image is pushed to **Azure Container Registry (ACR)**.
6. GitHub updates Azure Container App Job with the new image.
7. GitHub triggers the **Container App Job (Manual Trigger Type)**.
8. Container starts and runs `deploy.py`.
9. `deploy.py`:
   - Detects ENVIRONMENT (dev / prod)
   - Reads `deploy-database-map.yml`
   - Sets correct Snowflake database dynamically
10. Container connects to Snowflake using:
    - Service User
    - Workload Identity Federation (Azure Managed Identity)
11. schemachange:
    - Deploys new/modified objects
    - Skips already executed scripts
    - Maintains a Change History table
12. Execution logs are stored in:
    - Azure Log Analytics
13. You can query logs using KQL for success/failure tracking.

---

# ❄️ Snowflake Setup

---

## 1️⃣ Create Deployment Role

```sql
CREATE ROLE DEPLOY_ROLE;
GRANT ROLE SYSADMIN TO ROLE DEPLOY_ROLE;
```

> Adjust privileges as per your organization’s security standards.

---

## 2️⃣ Create Deployment Warehouse

```sql
CREATE WAREHOUSE DEPLOYMENT_WH;
GRANT USAGE ON WAREHOUSE DEPLOYMENT_WH TO ROLE DEPLOY_ROLE;
```

---

## 3️⃣ Create Service User with Workload Identity Federation

Use the **Tenant ID** and **Object ID** captured from Azure Managed Identity.

```sql
CREATE USER SVC_SNOWFLAKE_DEPLOY
  TYPE = SERVICE
  WORKLOAD_IDENTITY = (
      TYPE = AZURE
      ISSUER = 'https://login.microsoftonline.com/<tenant_id>/v2.0'
      SUBJECT = '<managed_identity_object_id>'
  )
  DEFAULT_ROLE = DEPLOY_ROLE;
```

---

## 4️⃣ Grant Role to Service User

```sql
GRANT ROLE DEPLOY_ROLE TO USER SVC_SNOWFLAKE_DEPLOY;
```

---

## 5️⃣ Create Authentication Policy

```sql
CREATE AUTHENTICATION POLICY DEPLOYMENT_POLICY
  AUTHENTICATION_METHODS = ('WORKLOAD_IDENTITY');
```

Assign policy to the service user:

```sql
ALTER USER SVC_SNOWFLAKE_DEPLOY
  SET AUTHENTICATION_POLICY = DEPLOYMENT_POLICY;
```

⚠️ **IMPORTANT:**  
Do NOT assign this authentication policy at ACCOUNT level.  
Assign it only to the user, otherwise you may lose account access.

---

## 6️⃣ Grant Required Privileges to DEPLOY_ROLE

Grant necessary privileges depending on your deployment needs.

Example:

```sql
GRANT USAGE ON DATABASE DEV_RAW TO ROLE DEPLOY_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE DEV_RAW TO ROLE DEPLOY_ROLE;
GRANT CREATE TABLE ON ALL SCHEMAS IN DATABASE DEV_RAW TO ROLE DEPLOY_ROLE;
```

Repeat for:
- DEV_HARMONIZED
- DEV_CONSUMPTION
- PROD databases

You can manage these via:

- `admin_setup.sql`
- `grants_to_deploy_role.sql`

---

## 7️⃣ Metadata Database for schemachange

schemachange requires a change history table.

Ensure the following exists (or allow schemachange to create it):

```sql
CREATE DATABASE DEV_METADATA;
CREATE SCHEMA DEV_METADATA.SCHEMACHANGE;
```

Your schemachange config will dynamically use:

- DEV_METADATA for dev
- PROD_METADATA for prod

Based on `deploy-database-map.yml`.

---

This completes the Snowflake setup section.

# 🧑‍💻 GitHub Setup

---

## 1️⃣ Repository Structure

Create the following folder structure:

.github/
 └── workflows/
     └── deploy.yml

migrations/
 ├── procedures/
 ├── sql_scripts/
 ├── tables/
 ├── views/
 └── stages/

snowflake/
 ├── admin_setup.sql
 └── grants_to_deploy_role.sql

deploy-database-map.yml
deploy.py
Dockerfile
requirements.txt
schemachange-config.yml
README.md

---

## 2️⃣ Create Azure App Registration for GitHub OIDC

1. Go to **Azure Entra ID**
2. Click **App Registrations**
3. Click **New Registration**
4. Name:
   git-deploy-app
5. Click **Register**

---

## 3️⃣ Add Federated Credential

1. Go to:
   Certificates & Secrets → Federated Credentials → Add Credential
2. Choose Scenario:
   GitHub Actions deploying Azure resources
3. Enter:
   - Organization: <your-org-name>
   - Repository: <your-repo-name>
   - Entity Type: Branch
   - Branch: main
4. Click Add

Repeat the same steps for:
   Branch: dev

---

## 4️⃣ Assign Required Roles to GitHub App

Go to:

Subscription → Access Control (IAM) → Role Assignments → Add Role Assignment

Assign the following roles to:
git-deploy-app

Required roles:
- Contributor
- AcrPush

---

## 5️⃣ GitHub Action Trigger Behavior

- Push to `dev` → Deploys to DEV databases
- Push to `main` → Deploys to PROD databases
- main should require PR approval before merge

---

# 📊 Logs & Monitoring

---

## Viewing Execution History

Go to:

Azure Portal → Container App Jobs → job-snowflake-deploy → Executions

Check:
- Status (Succeeded / Failed)
- Start Time
- Completion Time

---

## Azure Log Analytics Query (KQL)

Use the following query to fetch deployment logs:

```
ContainerAppConsoleLogs_CL
| where ContainerGroupName_s startswith "job-snowflake-deploy"
| order by TimeGenerated desc
| project Log_s
```

To check only failures:

```
ContainerAppConsoleLogs_CL
| where ContainerGroupName_s startswith "job-snowflake-deploy"
| where Log_s contains "error" or Log_s contains "failed"
| order by TimeGenerated desc
| project Log_s
```

To see logs for a specific execution:

```
ContainerAppConsoleLogs_CL
| where ContainerGroupName_s startswith "job-snowflake-deploy-<execution-id>"
| order by TimeGenerated desc
| project Log_s
```

---

# 📁 schemachange File Naming Convention

schemachange follows strict version-based naming rules.

---

## Versioned Scripts (Recommended)

Used for CREATE / ALTER objects.

Format:

V<version_number>__<description>.sql

Example:

V1__create_raw_customers_table.sql  
V2__create_harmonized_sales_view.sql  
V3__alter_orders_table_add_column.sql  

Rules:
- Must start with uppercase V
- Followed by version number
- Double underscore ( __ ) separator
- Description should be meaningful
- Version numbers must be unique
- Cannot be reused

---

## Repeatable Scripts (Optional)

Used for views or objects that may change often.

Format:

R__<description>.sql

Example:

R__refresh_reporting_view.sql  

These run again only if file content changes.

---

## Recommended Folder Organization

migrations/
 ├── tables/
 ├── views/
 ├── procedures/
 ├── stages/
 └── sql_scripts/

---

## Versioning Best Practice

Option 1: Sequential Numbers (Simple)

Tables: 1–500  
Views: 500–1000  
Procedures: 1000–1500  

Example:
V101__create_customer_table.sql  
V520__create_sales_view.sql  

Option 2: Timestamp-based (Safer for multiple developers)

V202402201430__create_customer_table.sql  

---

## Important Rules

- Never modify an already executed V file
- Create a new version for changes
- Version numbers must never duplicate
- File names are case sensitive
- Double underscore is mandatory

---

# ✅ Summary

This pipeline provides:

- Secure authentication using Azure OIDC + Snowflake WIF
- No stored secrets
- Dev/Prod separation
- Automated CI/CD deployment
- Idempotent Snowflake object deployment
- Centralized logging
- Low operational cost (Container App Job model)

---

End of Documentation.
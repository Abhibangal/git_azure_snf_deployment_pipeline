use role securityadmin;
--give grants to role
grant usage on database dev_raw   to role deploy_role;
grant usage on database dev_harmonized   to role deploy_role;
grant usage on database dev_consumption   to role deploy_role;

grant usage on all schemas in database dev_raw  to role deploy_role;
grant usage on all schemas in database dev_harmonized  to role deploy_role;
grant usage on all schemas in database dev_consumption  to role deploy_role;
grant create schema on database dev_consumption  to role deploy_role;;

grant usage on future  schemas in database dev_raw  to role deploy_role;
grant usage on future schemas in database dev_harmonized  to role deploy_role;
grant usage on future schemas in database dev_consumption  to role deploy_role;

grant all privileges  on all schemas in database dev_raw  to role deploy_role;
grant all privileges  on all schemas in database dev_harmonized  to role deploy_role;
grant all privileges  on all schemas in database dev_consumption  to role deploy_role;

grant all privileges  on future schemas in database dev_raw  to role deploy_role;
grant all privileges  on future schemas in database dev_harmonized  to role deploy_role;
grant all privileges  on future schemas in database dev_consumption  to role deploy_role;

grant usage on warehouse deployment_wh to role deploy_role;
--PROD 
grant usage on database PROD_raw   to role deploy_role;
grant usage on database PROD_harmonized   to role deploy_role;
grant usage on database PROD_consumption   to role deploy_role;

grant usage on all schemas in database PROD_raw  to role deploy_role;
grant usage on all schemas in database PROD_harmonized  to role deploy_role;
grant usage on all schemas in database PROD_consumption  to role deploy_role;

grant usage on future  schemas in database PROD_raw  to role deploy_role;
grant usage on future schemas in database PROD_harmonized  to role deploy_role;
grant usage on future schemas in database PROD_consumption  to role deploy_role;

grant all privileges  on all schemas in database PROD_raw  to role deploy_role;
grant all privileges  on all schemas in database PROD_harmonized  to role deploy_role;
grant all privileges  on all schemas in database PROD_consumption  to role deploy_role;

grant all privileges  on future schemas in database PROD_raw  to role deploy_role;
grant all privileges  on future schemas in database PROD_harmonized  to role deploy_role;
grant all privileges  on future schemas in database PROD_consumption  to role deploy_role;
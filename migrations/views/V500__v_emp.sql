
USE DATABASE {{ HARMONIZED }};
create or replace view RESEARCH.V_employees as
select * from {{ RAW }}.RESEARCH.EMPLOYEES;
USE DATABASE IDENTIFIER($RAW);
create or replace table RESEARCH.EMPLOYEES (
    id int,
    name varchar(255) not null,
    dept_id int,
    salary decimal(10, 2),
    hire_date date);
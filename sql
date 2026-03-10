
-- CTE 1: Defect
WITH cte_defect AS (
    SELECT
        d.[RELEASE_ID]
       ,d.[RELEASE]
       ,d.[SPRINT_ID]
       ,d.[DEFECT_SEVERITY]
       ,d.[DEFECT_APPLICATION]
       ,d.[DEFECT_TEST_TYPE]
       ,d.[DEFECT_ENVIRONMENT_DEFECT]
	   ,d.WORKSPACE_ID
       ,COUNT(d.[DEFECT_UNIQUE_ID])                                    AS total_defect_count
       ,SUM(CASE WHEN d.[DEFECT_REOPENS] > 0 THEN 1 ELSE 0 END)       AS reopen_count
       ,AVG(CAST(d.[DEFECT_ESTIMATED_HOUR] AS FLOAT))                  AS avg_estimated_hour
       ,SUM(CASE WHEN d.[DEFECT_JIRA_STATUS] = 'Closed'
                 THEN 1 ELSE 0 END)                                    AS closed_defect_count
       ,MIN(d.[DEFECT_CREATION_TIME])                                  AS first_defect_time
       ,MAX(d.[DEFECT_CREATION_TIME])                                  AS last_defect_time
    FROM [BAQARM_Reporting].[oct].[OCTANE_DEFECT] d
	where RELEASE_ID is not null
    GROUP BY
        d.[RELEASE_ID], d.[RELEASE]
       ,d.[SPRINT_ID],  d.[SPRINT]
       ,d.[DEFECT_SEVERITY]
       ,d.[DEFECT_APPLICATION]
       ,d.[DEFECT_TEST_TYPE]
	   ,d.WORKSPACE_ID
       ,d.[DEFECT_ENVIRONMENT_DEFECT]
),
 
-- CTE 2: Release 
cte_release AS (
    SELECT
        r.[RELEASE_ID]
       ,r.[RELEASE_NAME]
       ,r.[NUM_OF_SPRINTS]
       ,r.[RELEASE_START_DATE]
       ,r.[RELEASE_END_DATE]
	   ,r.workspace_ID
       ,DATEDIFF(DAY, r.[RELEASE_START_DATE],
                      r.[RELEASE_END_DATE])       AS release_duration_days
    FROM [BAQARM_Reporting].[oct].[RELEASE] r
),

-- CTE 3: Run 
cte_run AS (
    SELECT
        [RELEASE_ID]
       ,[SPRINT_ID]
	   ,WORKSPACE_ID
       ,COUNT([RUN_ID])                                              AS total_run_count
       ,SUM(CASE WHEN [RUN_NATIVE_STATUS] = 'Passed'
                 THEN 1 ELSE 0 END)                                  AS passed_run_count
       ,SUM(CASE WHEN [RUN_NATIVE_STATUS] = 'Failed'
                 THEN 1 ELSE 0 END)                                  AS failed_run_count
       ,SUM(CASE WHEN [RUN_AUTOMATED] = 'Y'
                 THEN 1 ELSE 0 END)                                  AS automated_run_count
       ,AVG(CAST([RUN_DURATION] AS FLOAT))                           AS avg_run_duration
       ,ROUND(
           1.0 * SUM(CASE WHEN [RUN_NATIVE_STATUS] = 'Passed'
                          THEN 1 ELSE 0 END)
             / NULLIF(COUNT([RUN_ID]), 0)
        , 4)                                                         AS pass_rate
       ,ROUND(
           1.0 * SUM(CASE WHEN [RUN_AUTOMATED] = 'Y'
                          THEN 1 ELSE 0 END)
             / NULLIF(COUNT([RUN_ID]), 0)
        , 4)                                                         AS automation_rate
    FROM [BAQARM_Reporting].[oct].[OCTANE_RUN]
    GROUP BY [RELEASE_ID], [SPRINT_ID],WORKSPACE_ID
),
 
-- CTE 4: Lag 
cte_lag AS (
    SELECT
        [RELEASE_ID]
       ,[SPRINT_ID]
	   ,WORKSPACE_ID
       ,total_defect_count
       ,LAG(total_defect_count, 1) OVER (
            PARTITION BY [RELEASE_ID]
            ORDER BY [SPRINT_ID]
        )                                        AS prev_sprint_defect_count
       ,AVG(total_defect_count) OVER (
            PARTITION BY [RELEASE_ID]
            ORDER BY [SPRINT_ID]
            ROWS BETWEEN 2 PRECEDING AND 1 PRECEDING
        )                                        AS rolling_avg_2sprint
    FROM cte_defect
),
 

-- CTE 5: 

cte_final AS (
    SELECT
        d.[RELEASE_ID]
       ,d.[RELEASE]
       ,d.[SPRINT_ID]
       ,d.[DEFECT_SEVERITY]
       ,d.[DEFECT_APPLICATION]
       ,d.[DEFECT_TEST_TYPE]
       ,d.[DEFECT_ENVIRONMENT_DEFECT]
	   ,d.WORKSPACE_ID
        -- Release 
       ,r.[NUM_OF_SPRINTS]
       ,r.[release_duration_days]
        -- Run 
       ,ISNULL(ru.[total_run_count],    0)   AS total_run_count
       ,ISNULL(ru.[failed_run_count],   0)   AS failed_run_count
       ,ISNULL(ru.[automated_run_count],0)   AS automated_run_count
       ,ISNULL(ru.[pass_rate],          0)   AS pass_rate
       ,ISNULL(ru.[automation_rate],    0)   AS automation_rate
       ,ISNULL(ru.[avg_run_duration],   0)   AS avg_run_duration
        -- Defect 
       ,d.[reopen_count]
       ,d.[closed_defect_count]
       ,d.[avg_estimated_hour]
       ,d.[first_defect_time]
       ,d.[last_defect_time]
        -- Lag 
       ,l.[prev_sprint_defect_count]
       ,l.[rolling_avg_2sprint]
        -- Target Variable Y
       ,d.[total_defect_count]
    FROM cte_defect        d
    LEFT JOIN cte_release  r   ON d.[RELEASE_ID] = r.[RELEASE_ID] and d.WORKSPACE_ID = r.workspace_id
    LEFT JOIN cte_run      ru  ON d.[RELEASE_ID] = ru.[RELEASE_ID]
                               AND d.[SPRINT_ID] = ru.[SPRINT_ID] and d.WORKSPACE_ID = ru.WORKSPACE_ID
    LEFT JOIN cte_lag      l   ON d.[RELEASE_ID] = l.[RELEASE_ID]
                               AND d.[SPRINT_ID] = l.[SPRINT_ID] and d.WORKSPACE_ID = l.WORKSPACE_ID
)
 
-- Final
SELECT *
FROM cte_final
ORDER BY
    [RELEASE_ID]
   ,[SPRINT_ID]
   ,[DEFECT_APPLICATION]
   ,WORKSPACE_ID

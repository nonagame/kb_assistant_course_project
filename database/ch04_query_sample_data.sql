-- 第四章阶段 A：先为查询接口准备数据。
-- 在项目 .env 中 DB_HOST、DB_PORT、DB_NAME 对应的 MySQL 库、同一个 SQL 控制台连接中分段执行。
-- 已完成 20260823_03 迁移；下面两个用户名必须是不同的、已启用的 public 账号。

-- 1. 只修改这两处用户名。A 对应 publicToken，B 对应 otherToken。
-- 与课程迁移的字符集/排序规则保持一致，避免不同客户端默认值导致比较报错。
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET @ch04_a_name = '用户A';
SET @ch04_b_name = '用户B';
SET @ch04_a_id = (
    SELECT id FROM users
    WHERE username = @ch04_a_name AND role_code = 'public' AND is_active = 1
);
SET @ch04_b_id = (
    SELECT id FROM users
    WHERE username = @ch04_b_name AND role_code = 'public' AND is_active = 1
      AND id <> @ch04_a_id
);

-- 两个 ID 必须非 NULL 且不同；否则停在这里，核对账号后重跑第 1 段。
SELECT DATABASE() AS current_database,
       @ch04_a_name AS account_a, @ch04_a_id AS user_a_id,
       @ch04_b_name AS account_b, @ch04_b_id AS user_b_id;

-- 2. 一次插入三条 PENDING 演示记录：A 两条，B 一条。
-- 确定编号用于去重；重复执行只补缺少的记录，不覆盖已有状态或内容。
-- 即使误跳过账号核对，缺失的 ID 也会触发非空约束错误，不会把空插入当成功。
INSERT INTO leave_requests (
    leave_id, user_id, requester, leave_type, start_time, end_time,
    duration_days, reason, status, approver_user_id, decision_reason,
    decided_at, created_at, updated_at
)
SELECT sample.leave_id, sample.user_id, sample.requester, sample.leave_type,
       sample.start_time, sample.end_time, 1.00, '第四章查询演示数据',
       'PENDING', NULL, NULL, NULL, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)
FROM (
    SELECT CONCAT('CH04-', @ch04_a_id, '-01') AS leave_id,
           @ch04_a_id AS user_id, @ch04_a_name AS requester,
           'annual' AS leave_type,
           '2026-10-12 09:00:00' AS start_time, '2026-10-12 18:00:00' AS end_time
    UNION ALL
    SELECT CONCAT('CH04-', @ch04_a_id, '-02'), @ch04_a_id, @ch04_a_name,
           'personal', '2026-10-13 09:00:00', '2026-10-13 18:00:00'
    UNION ALL
    SELECT CONCAT('CH04-', @ch04_b_id, '-01'), @ch04_b_id, @ch04_b_name,
           'sick', '2026-10-14 09:00:00', '2026-10-14 18:00:00'
) AS sample
LEFT JOIN leave_requests AS existing ON existing.leave_id = sample.leave_id
WHERE existing.id IS NULL;

-- 3. 应得到三条记录，保存这三个 leave_id，用于 A4—A6 的接口核对。
SELECT leave_id, user_id, requester, leave_type, start_time, end_time,
       duration_days, status
FROM leave_requests
WHERE leave_id IN (
    CONCAT('CH04-', @ch04_a_id, '-01'),
    CONCAT('CH04-', @ch04_a_id, '-02'),
    CONCAT('CH04-', @ch04_b_id, '-01')
)
ORDER BY user_id, leave_id;

-- ===================================================
-- 迁移：允许同一openid注册多个审批角色
-- 不影响现有数据（仅修改约束）
--
-- 用法: mysql -u root -p <数据库名> < 002_approver_openid_role.sql
-- ===================================================

-- 1. 查找并删除 openid 上的旧唯一索引
--    先查看索引名: SHOW INDEX FROM approvers WHERE Column_name = 'openid' AND Non_unique = 0;
--    常见名称: openid / openid_2 / ix_approvers_openid
SET @idx_name := (
    SELECT INDEX_NAME FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'approvers'
      AND COLUMN_NAME = 'openid'
      AND NON_UNIQUE = 0
    LIMIT 1
);

SET @drop_sql := IF(@idx_name IS NOT NULL,
    CONCAT('ALTER TABLE approvers DROP INDEX ', @idx_name),
    'SELECT "No unique index on openid found, skipping" AS msg'
);
PREPARE stmt FROM @drop_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 如果已存在 uq_openid_role 索引则先删除（支持重复执行）
SET @uq_idx := (
    SELECT INDEX_NAME FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'approvers'
      AND INDEX_NAME = 'uq_openid_role'
    LIMIT 1
);
SET @drop_uq := IF(@uq_idx IS NOT NULL,
    'ALTER TABLE approvers DROP INDEX uq_openid_role',
    'SELECT "uq_openid_role not exists, skipping" AS msg'
);
PREPARE stmt2 FROM @drop_uq;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 3. 添加 (openid, role) 联合唯一约束
ALTER TABLE approvers ADD UNIQUE KEY uq_openid_role (openid, role);

-- 验证
SELECT 'Migration completed. New indexes on approvers:' AS msg;
SHOW INDEX FROM approvers WHERE Key_name LIKE '%openid%';

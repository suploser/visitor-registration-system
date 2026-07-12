-- ============================================================
-- 微信订阅消息通知系统 - 数据库迁移
-- 执行: mysql -u visitor -p visitor_prod < add_notification_tables.sql
-- 执行: mysql -u root -p visitor_dev < add_notification_tables.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS `notification_subscriptions` (
    `id`          INT AUTO_INCREMENT PRIMARY KEY,
    `openid`      VARCHAR(100)  NOT NULL COMMENT '订阅者微信 openid',
    `template_id` VARCHAR(100)  NOT NULL COMMENT '订阅消息模板 ID',
    `status`      VARCHAR(20)   DEFAULT 'active' COMMENT 'active=可用, used=已消耗',
    `created_at`  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    `used_at`     TIMESTAMP     NULL COMMENT '使用时间',
    INDEX `idx_openid_template_status` (`openid`, `template_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微信订阅消息记录表';

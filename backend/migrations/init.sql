-- ============================================
-- 访客登记系统 - 数据库初始化脚本
-- 使用方法: mysql -u root -p < init.sql
-- ============================================

CREATE DATABASE IF NOT EXISTS visitor_dev
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE visitor_dev;

-- 1. 部门表（接待人部门/一级审批人部门共用）
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 二级审批人部门表
CREATE TABLE IF NOT EXISTS level2_departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 审批人表
CREATE TABLE IF NOT EXISTS approvers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(100) NOT NULL COMMENT '微信openid，同一openid可注册不同角色',
    name VARCHAR(50) NOT NULL,
    department VARCHAR(100) NOT NULL COMMENT '所属部门',
    role ENUM('level1', 'level2') NOT NULL COMMENT '一级/二级审批人',
    register_token VARCHAR(64) UNIQUE COMMENT '录入链接token',
    token_expires DATETIME COMMENT 'token过期时间',
    is_registered TINYINT(1) DEFAULT 0 COMMENT '是否已完成信息录入',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_openid_role (openid, role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 访客登记主表
CREATE TABLE IF NOT EXISTS visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(200) NOT NULL COMMENT 'AES加密存储',
    id_number VARCHAR(200) NOT NULL COMMENT 'AES加密存储',
    host_name VARCHAR(50) NOT NULL COMMENT '接待人',
    host_department VARCHAR(100) NOT NULL COMMENT '接待人部门',
    visit_start DATETIME NOT NULL COMMENT '访问开始时间',
    visit_end DATETIME NOT NULL COMMENT '访问预计结束时间',
    visit_location VARCHAR(200) NOT NULL COMMENT '访问地点',
    visit_purpose VARCHAR(500) NOT NULL COMMENT '访问目的',
    visitor_count INT DEFAULT 1 COMMENT '来访人数',
    has_device TINYINT(1) DEFAULT 0 COMMENT '是否携带信息设备',
    device_info VARCHAR(500) COMMENT '设备名称型号',
    license_plates TEXT COMMENT '车牌号JSON数组',
    openid VARCHAR(100) COMMENT '访客微信openid',
    status ENUM('pending', 'level1_approved', 'approved', 'rejected') DEFAULT 'pending',
    reject_reason VARCHAR(500) COMMENT '拒绝原因',
    session_expires DATETIME COMMENT '会话过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_openid (openid),
    INDEX idx_status (status),
    INDEX idx_session (session_expires)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 同行人表
CREATE TABLE IF NOT EXISTS companions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    id_number VARCHAR(200) NOT NULL COMMENT 'AES加密存储',
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 审批记录表
CREATE TABLE IF NOT EXISTS approval_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id INT NOT NULL,
    approver_id INT NOT NULL,
    approver_name VARCHAR(50) NOT NULL,
    approver_role ENUM('level1', 'level2') NOT NULL,
    result ENUM('approved', 'rejected') NOT NULL,
    comment VARCHAR(500),
    approved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES approvers(id) ON DELETE CASCADE,
    INDEX idx_visitor (visitor_id),
    INDEX idx_approver (approver_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 管理员表
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    failed_attempts INT DEFAULT 0,
    locked_until DATETIME,
    session_token VARCHAR(64),
    last_password_change DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 初始数据
-- ============================================

-- 部门列表（接待人/一级审批人）
INSERT INTO departments (name) VALUES
    ('行政部'), ('财务部'), ('技术部'), ('市场部'),
    ('人力资源部'), ('研发部'), ('生产部'), ('质量管理部'),
    ('采购部'), ('销售部');

-- 二级审批人部门
INSERT INTO level2_departments (name) VALUES ('安全保卫部');

-- 默认管理员 (密码: Admin@123456)
-- bcrypt hash for 'Admin@123456'
INSERT INTO admins (username, password_hash, last_password_change) VALUES
    ('admin', '$2b$12$Na8ed4xy9Q8BmKsI.8osvOVyVfKV9VT0MaFETMghwhTG2idpKKhv6', NOW());

-- 系统默认配置
INSERT INTO system_config (config_key, config_value) VALUES
    ('welcome_message', '各位领导，合作伙伴，访客，您正在使用访客登记系统，请知悉相关管理规定。'),
    ('visitor_notice', '<h3>访客告知书</h3><p>欢迎您来访我单位。为保障单位安全和工作秩序，请您遵守以下规定：</p><ol><li>请如实填写个人信息，不得冒用他人身份。</li><li>进入园区后请佩戴访客标识，在指定区域内活动。</li><li>未经许可不得拍照、录像或录音。</li><li>请遵守单位的保密制度，不得泄露在访问过程中获知的任何信息。</li><li>携带信息设备的，请主动登记并接受检查。</li><li>离开时请交还访客标识并办理离园手续。</li><li>违反以上规定者，单位有权终止其访问并追究相关责任。</li></ol>'),
    ('home_bg_images', '[\"/images/hero-bg.png\"]'),
    ('company_scroll_images', '[\"/images/company-1.png\",\"/images/company-2.png\",\"/images/company-3.png\"]');

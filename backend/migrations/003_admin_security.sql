-- Migration: admin login lockout + single session tracking
-- Adds 3 columns to the admins table
-- Usage: mysql -u root -p visitor_dev < 003_admin_security.sql

ALTER TABLE admins
  ADD COLUMN failed_attempts INT DEFAULT 0 COMMENT 'Consecutive failed login count',
  ADD COLUMN locked_until DATETIME NULL COMMENT 'Account locked until this time',
  ADD COLUMN session_token VARCHAR(64) NULL COMMENT 'Active session UUID, new login overwrites old';

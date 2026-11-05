-- 数据库初始化脚本（可选，FastAPI 启动时会自动建表）
CREATE DATABASE IF NOT EXISTS yolo_safety DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE yolo_safety;

-- 摄像头表
CREATE TABLE IF NOT EXISTS cameras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL COMMENT '摄像头名称',
    location VARCHAR(128) DEFAULT '' COMMENT '安装点位',
    rtsp_url VARCHAR(512) NOT NULL COMMENT 'RTSP地址',
    status VARCHAR(16) DEFAULT 'offline' COMMENT 'online/offline',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='监控摄像头';

-- 违规记录表
CREATE TABLE IF NOT EXISTS violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT COMMENT '摄像头ID',
    camera_name VARCHAR(64) DEFAULT '' COMMENT '摄像头名称',
    violation_type VARCHAR(32) COMMENT '违规类型: no_helmet/no_vest/no_mask',
    confidence FLOAT DEFAULT 0 COMMENT '置信度',
    image_path VARCHAR(512) COMMENT '图片存储路径',
    image_url VARCHAR(512) COMMENT '图片访问地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '抓拍时间',
    INDEX idx_violation_type (violation_type),
    INDEX idx_created_at (created_at),
    INDEX idx_camera_id (camera_id)
) ENGINE=InnoDB COMMENT='违规抓拍记录';

-- 初始管理员（演示账号：admin / admin123，认证逻辑在 config.py）

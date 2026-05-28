CREATE DATABASE IF NOT EXISTS sewa_queue_db;
USE sewa_queue_db;

-- 1. Department Services Table
CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    service_prefix CHAR(1) NOT NULL, -- e.g., 'P' for Passport, 'L' for License
    avg_processing_time_mins INT DEFAULT 15
);

-- 2. Physical Service Counters
CREATE TABLE IF NOT EXISTS counters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    counter_number INT NOT NULL UNIQUE,
    officer_name VARCHAR(100) DEFAULT 'Officer'
);

-- 3. Live Tokens Queue Table
CREATE TABLE IF NOT EXISTS tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_number VARCHAR(10) NOT NULL,
    citizen_phone VARCHAR(15) NOT NULL,
    service_id INT,
    counter_id INT DEFAULT NULL,
    status ENUM('Pending', 'Serving', 'Completed', 'Skipped') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (counter_id) REFERENCES counters(id)
);

-- Seed Initial Government Office Configuration Data
INSERT INTO services (service_name, service_prefix, avg_processing_time_mins) VALUES 
('Passport Biometrics', 'P', 12),
('National ID Verification', 'N', 10),
('Document Attestation', 'D', 5);

INSERT INTO counters (counter_number, officer_name) VALUES 
(1, 'S. Sharma'),
(2, 'A. Adhikari'),
(3, 'R. Basnet');
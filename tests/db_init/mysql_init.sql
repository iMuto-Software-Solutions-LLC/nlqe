-- MySQL Initialization Script
CREATE DATABASE IF NOT EXISTS test_db;
USE test_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0
);

-- Insert Mock Data
INSERT INTO users (name, email, active) VALUES
    ('David Clark', 'david@example.com', true),
    ('Eve Miller', 'eve@example.com', false),
    ('Frank Wilson', 'frank@example.com', true);

INSERT INTO products (name, price, stock_quantity) VALUES
    ('Monitor', 300.00, 30),
    ('Keyboard', 100.00, 150),
    ('Mouse', 50.00, 300);

INSERT INTO orders (user_id, status, total_amount) VALUES
    (1, 'COMPLETED', 300.00),
    (1, 'COMPLETED', 100.00),
    (3, 'PENDING', 50.00);

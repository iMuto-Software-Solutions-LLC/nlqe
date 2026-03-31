-- PostgreSQL Initialization Script
CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE public.users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id),
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0
);

-- Insert Mock Data
INSERT INTO public.users (name, email, active) VALUES
    ('Alice Smith', 'alice@example.com', true),
    ('Bob Jones', 'bob@example.com', false),
    ('Charlie Brown', 'charlie@example.com', true);

INSERT INTO public.products (name, price, stock_quantity) VALUES
    ('Laptop', 1200.00, 50),
    ('Smartphone', 800.00, 100),
    ('Headphones', 150.00, 200);

INSERT INTO public.orders (user_id, status, total_amount) VALUES
    (1, 'COMPLETED', 1200.00),
    (1, 'COMPLETED', 150.00),
    (3, 'PENDING', 800.00);

-- Database Schema for Ticket Auto-Processing System
-- PostgreSQL schema with tables, indexes, and sample data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    cognito_user_id VARCHAR(255) UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create tickets table
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    ticket_type VARCHAR(50) NOT NULL,
    original_price DECIMAL(10,2) NOT NULL,
    purchase_date TIMESTAMP DEFAULT NOW(),
    event_date TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create upgrade_orders table
CREATE TABLE IF NOT EXISTS upgrade_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    upgrade_tier VARCHAR(50) NOT NULL,
    original_tier VARCHAR(50) NOT NULL,
    price_difference DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    payment_intent_id VARCHAR(255),
    confirmation_code VARCHAR(20) UNIQUE,
    selected_date TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_cognito_id ON customers(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_number ON tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_upgrade_orders_ticket_id ON upgrade_orders(ticket_id);
CREATE INDEX IF NOT EXISTS idx_upgrade_orders_customer_id ON upgrade_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_upgrade_orders_status ON upgrade_orders(status);
CREATE INDEX IF NOT EXISTS idx_upgrade_orders_confirmation ON upgrade_orders(confirmation_code);

-- Insert sample customers
INSERT INTO customers (email, first_name, last_name, phone) VALUES
('john.doe@example.com', 'John', 'Doe', '+1-555-0101'),
('jane.smith@example.com', 'Jane', 'Smith', '+1-555-0102'),
('bob.johnson@example.com', 'Bob', 'Johnson', '+1-555-0103'),
('alice.brown@example.com', 'Alice', 'Brown', '+1-555-0104'),
('charlie.wilson@example.com', 'Charlie', 'Wilson', '+1-555-0105')
ON CONFLICT (email) DO NOTHING;

-- Insert sample tickets
WITH customer_data AS (
    SELECT id, email, ROW_NUMBER() OVER (ORDER BY created_at) as rn 
    FROM customers 
    LIMIT 5
)
INSERT INTO tickets (customer_id, ticket_number, ticket_type, original_price, event_date) 
SELECT 
    cd.id,
    'TKT-2024' || LPAD(cd.rn::text, 2, '0') || LPAD(series.n::text, 2, '0'),
    CASE series.n 
        WHEN 1 THEN 'general'
        WHEN 2 THEN 'vip'
        WHEN 3 THEN 'premium'
        ELSE 'standard'
    END,
    50.00 + (series.n * 25.00),
    NOW() + INTERVAL '30 days' + (series.n * INTERVAL '7 days')
FROM customer_data cd
CROSS JOIN generate_series(1, 2) AS series(n)
ON CONFLICT (ticket_number) DO NOTHING;

-- Insert sample upgrade orders
WITH ticket_data AS (
    SELECT 
        t.id as ticket_id, 
        t.customer_id, 
        t.original_price,
        ROW_NUMBER() OVER (ORDER BY t.created_at) as rn
    FROM tickets t 
    LIMIT 3
)
INSERT INTO upgrade_orders (
    ticket_id, customer_id, upgrade_tier, original_tier, 
    price_difference, total_amount, status, confirmation_code, completed_at
)
SELECT 
    td.ticket_id,
    td.customer_id,
    CASE td.rn 
        WHEN 1 THEN 'standard'
        WHEN 2 THEN 'non-stop'
        ELSE 'double-fun'
    END,
    'general',
    CASE td.rn 
        WHEN 1 THEN 25.00
        WHEN 2 THEN 50.00
        ELSE 75.00
    END,
    td.original_price + CASE td.rn 
        WHEN 1 THEN 25.00
        WHEN 2 THEN 50.00
        ELSE 75.00
    END,
    CASE WHEN td.rn <= 2 THEN 'completed' ELSE 'pending' END,
    'CONF' || UPPER(SUBSTRING(uuid_generate_v4()::text, 1, 8)),
    CASE WHEN td.rn <= 2 THEN NOW() ELSE NULL END
FROM ticket_data td;
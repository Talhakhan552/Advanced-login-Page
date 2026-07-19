-- ============================================
-- LOGIN SYSTEM DATABASE SCHEMA
-- Run this in pgAdmin Query Tool
-- ============================================

-- Drop existing types/tables if they exist (for fresh install)
-- Uncomment these if you want to reset the database
-- DROP TABLE IF EXISTS refresh_tokens CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TYPE IF EXISTS user_role CASCADE;

-- ============================================
-- CREATE ENUM TYPE FOR ROLES
-- ============================================
-- This ensures only valid roles can be stored
CREATE TYPE user_role AS ENUM ('user', 'admin', 'moderator');

-- ============================================
-- USERS TABLE
-- ============================================
-- Stores user account information
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,        -- Unique username for login
  email VARCHAR(100) UNIQUE NOT NULL,          -- Unique email address
  password_hash VARCHAR(255) NOT NULL,         -- Bcrypt hashed password (never store raw password!)
  role user_role DEFAULT 'user',               -- User role for authorization
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Account creation time
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- Last update time
);

-- ============================================
-- REFRESH TOKENS TABLE
-- ============================================
-- Stores refresh token hashes for session management
-- When user logs out, we mark token as revoked
-- When access token expires, client uses refresh token to get new one
CREATE TABLE refresh_tokens (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- Which user owns this token
  token_hash VARCHAR(255) NOT NULL UNIQUE,     -- SHA256 hash of the JWT (secure storage)
  expires_at TIMESTAMP NOT NULL,               -- When this token expires
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When token was created
  revoked BOOLEAN DEFAULT FALSE                -- TRUE if user logged out
);

-- ============================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================
-- Indexes speed up SELECT queries
-- Without indexes, PostgreSQL has to scan entire table

-- Index for username lookup (login)
CREATE INDEX idx_users_username ON users(username);

-- Index for email lookup (registration check)
CREATE INDEX idx_users_email ON users(email);

-- Index for finding user's tokens (logout)
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- Index for checking token expiry (cleanup old tokens)
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================
-- INSERT SAMPLE DATA
-- ============================================
-- These demo accounts use password: "password123"
-- Password hash generated using bcrypt with 10 salt rounds

INSERT INTO users (username, email, password_hash, role) VALUES
  ('john_admin', 'john@example.com', '$2b$10$YIjlrPNoS0E1Id60t7VkUOYhMcLz5QVJoWO2nAYSgnTGWJkLw5R4a', 'admin'),
  ('jane_user', 'jane@example.com', '$2b$10$YIjlrPNoS0E1Id60t7VkUOYhMcLz5QVJoWO2nAYSgnTGWJkLw5R4a', 'user'),
  ('bob_mod', 'bob@example.com', '$2b$10$YIjlrPNoS0E1Id60t7VkUOYhMcLz5QVJoWO2nAYSgnTGWJkLw5R4a', 'moderator');
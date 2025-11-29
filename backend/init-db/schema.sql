-- ===========================================
-- Users Table
-- ===========================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    birthday DATE,
    faculty VARCHAR(150)
);

-- ===========================================
-- Groups Table
-- ===========================================
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    group_number INT NOT NULL,
    invite_link VARCHAR(200) NOT NULL
);

-- ===========================================
-- Updated Association Table: user_groups
-- Now includes role: 'admin' or 'member'
-- ===========================================
CREATE TABLE IF NOT EXISTS user_groups (
    user_id VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id INT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    PRIMARY KEY (user_id, group_id)
);

-- ===========================================
-- Tasks Table
-- ===========================================
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    deadline DATE NOT NULL,
    kind VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'todo',
    progress INT NOT NULL DEFAULT 0,
    user_id VARCHAR(50) REFERENCES users(id),
    group_id INT REFERENCES groups(id),
    assignee VARCHAR(100),
    notes TEXT
);

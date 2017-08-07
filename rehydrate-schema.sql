--sqlite3 database.db < rehydrate-schema.sql

PRAGMA foreign_keys = ON;

DROP TABLE if exists users;
CREATE TABLE users (
  id INTEGER PRIMARY KEY autoincrement,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  CHECK (
      length("password") >= 6
  )
);

DROP TABLE if exists water;
CREATE TABLE water (
  id INTEGER PRIMARY KEY autoincrement,
  user_id INTEGER,
  post_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  quantity REAL NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  CHECK(
      typeof("quantity") = "real"
  )
);
#!/usr/bin/env python3
import sqlite3

# Connect to the database
conn = sqlite3.connect('data/personas.db')
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Existing tables:")
for table in tables:
    print(f"  {table[0]}")

# For each table, show its schema
print("\nTable schemas:")
for table in tables:
    table_name = table[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name}:")
    for col in columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")

conn.close()